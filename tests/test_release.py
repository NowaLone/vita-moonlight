"""Release checks use synthetic ZIP/SFO bytes and mocked gh calls; no build or publication."""
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('moonlight_release', ROOT / 'scripts/release.py')
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)
REPO = 'NowaLone/vita-moonlight'
ENV = {'GITHUB_REF': 'refs/tags/v1.01', 'GITHUB_EVENT_NAME': 'push',
       'SOURCE_SHA': 'a' * 40, 'GITHUB_RUN_ID': '123'}


def tag_reference(tag='v1.01', sha=ENV['SOURCE_SHA'], kind='commit'):
    return {'ref': f'refs/tags/{tag}', 'object': {'type': kind, 'sha': sha}}


def fake_sfo(**overrides):
    values = {'TITLE_ID': release.TITLE_ID, 'APP_VER': '01.01', 'VERSION': '01.01',
              'CONTENT_ID': release.CONTENT_ID, 'CATEGORY': 'gdc'}
    values.update(overrides)
    keys = bytearray()
    data = bytearray()
    entries = bytearray()
    for name, value in values.items():
        raw = value.encode() + b'\0'
        entries += struct.pack('<HHIII', len(keys), 0x0204, len(raw), len(raw), len(data))
        keys += name.encode() + b'\0'
        data += raw
    key_offset = 20 + len(entries)
    return struct.pack('<5I', 0x46535000, 0x101, key_offset, key_offset + len(keys), len(values)) + entries + keys + data


def fixture(directory, ini=None, **overrides):
    build = directory / 'build'
    output = directory / 'release'
    build.mkdir()
    output.mkdir()
    for name in release.ARCHIVES:
        (output / name).write_bytes(b'synthetic archive fixture')
    for name in release.PAYLOADS[1:]:
        (build / name).write_bytes(b'synthetic debug fixture')
    with zipfile.ZipFile(build / release.PAYLOADS[0], 'w') as archive:
        archive.writestr('eboot.bin', b'synthetic executable fixture')
        archive.writestr('sce_sys/param.sfo', fake_sfo(**overrides))
        archive.writestr('sce_sys/homebrew_update.ini', ini if ini is not None else (ROOT / 'sce_sys/homebrew_update.ini').read_bytes())
    return build, output


class Release(unittest.TestCase):
    def test_vita_versions_and_tags_reject_semver_and_shell_input(self):
        for version, tag in (('01.01', 'v1.01'), ('01.99', 'v1.99'), ('02.00', 'v2.00'), ('99.99', 'v99.99')):
            self.assertEqual(release.release_tag(version), tag)
        for version in ('1.01', '01.1', '01.001', '1.0.1', 'v1.01', '01.01-rc.1', '100.00', '01.01\n', '$(id)'):
            with self.subTest(version=version), self.assertRaises(ValueError):
                release.release_tag(version)

    @patch.dict(os.environ, ENV)
    def test_only_canonical_tag_pushes_supply_the_package_version(self):
        for tag, version in (('v1.01', '01.01'), ('v1.99', '01.99'), ('v2.00', '02.00'), ('v99.99', '99.99')):
            with patch.dict(os.environ, {'GITHUB_REF': 'refs/tags/' + tag}):
                self.assertEqual(release.pushed_version(), version)
        for ref in ('refs/heads/master', 'refs/tags/v01.01', 'refs/tags/v1.0.1',
                    'refs/tags/v1.01-rc.1', 'refs/tags/v100.00', 'refs/tags/$(id)', 'refs/tags/v1.1'):
            with self.subTest(ref=ref), patch.dict(os.environ, {'GITHUB_REF': ref}), self.assertRaises(ValueError):
                release.pushed_version()
        with patch.dict(os.environ, {'GITHUB_EVENT_NAME': 'workflow_dispatch'}), self.assertRaises(ValueError):
            release.pushed_version()

    @patch.dict(os.environ, ENV)
    def test_release_admission_rejects_releases_and_nonincreasing_versions(self):
        reference = tag_reference()
        for responses in ((reference, {}), (reference, None, {'tag_name': 'v1.01'}),
                          (reference, None, {'tag_name': 'v2.00'}), (reference, None, {'tag_name': 'v1.0.1'})):
            with patch.object(release, 'api', side_effect=responses), self.assertRaises(ValueError):
                release.preflight(REPO, '01.01')
        with patch.object(release, 'api', side_effect=(reference, None, None)):
            self.assertEqual(release.preflight(REPO, '01.01'), 'v1.01')
        with patch.dict(os.environ, {'GITHUB_REF': 'refs/tags/v2.00'}), patch.object(release, 'api', side_effect=(tag_reference('v2.00'), None, {'tag_name': 'v1.99'})):
            self.assertEqual(release.preflight(REPO, '02.00'), 'v2.00')
        with patch.dict(os.environ, {'GITHUB_REF': 'refs/heads/feature'}), patch.object(release, 'api') as api:
            with self.assertRaises(ValueError):
                release.preflight(REPO, '01.01')
            api.assert_not_called()
        with patch.object(release, 'api') as api:
            with self.assertRaises(ValueError):
                release.preflight(REPO, '02.00')
            api.assert_not_called()

    @patch.dict(os.environ, ENV)
    def test_lightweight_and_annotated_tags_must_resolve_to_the_built_commit(self):
        for chain in ((tag_reference(),),
                      (tag_reference(sha='b' * 40, kind='tag'), {'object': {'type': 'commit', 'sha': ENV['SOURCE_SHA']}}),
                      (tag_reference(sha='b' * 40, kind='tag'), {'object': {'type': 'tag', 'sha': 'c' * 40}},
                       {'object': {'type': 'commit', 'sha': ENV['SOURCE_SHA']}})):
            with patch.object(release, 'api', side_effect=chain):
                self.assertEqual(release.verify_tag(REPO, 'v1.01'), ENV['SOURCE_SHA'])
        for reference in (tag_reference(sha='b' * 40), tag_reference(kind='tree'), tag_reference(tag='v1.02')):
            with patch.object(release, 'api', return_value=reference), self.assertRaises(ValueError):
                release.verify_tag(REPO, 'v1.01')
        cyclic = tag_reference(sha='b' * 40, kind='tag')
        with patch.object(release, 'api', return_value=cyclic), self.assertRaises(ValueError):
            release.verify_tag(REPO, 'v1.01')
        with patch.dict(os.environ, {'SOURCE_SHA': 'HEAD'}), patch.object(release, 'api') as api:
            with self.assertRaises(ValueError):
                release.verify_tag(REPO, 'v1.01')
            api.assert_not_called()

    def test_only_real_404_is_treated_as_missing(self):
        for status, code, body in ((404, 1, '{}'), (403, 1, '{}'), (500, 1, '{}'), (200, 0, '{"id": 7}')):
            response = subprocess.CompletedProcess([], code, f'HTTP/2.0 {status} status\n\n{body}', 'test failure')
            with patch.object(release.subprocess, 'run', return_value=response):
                if status in (403, 500):
                    with self.assertRaises(RuntimeError):
                        release.api(REPO, 'releases/latest', missing=True)
                else:
                    self.assertEqual(release.api(REPO, 'releases/latest', missing=True), None if status == 404 else {'id': 7})
                    if status == 404:
                        with self.assertRaises(RuntimeError):
                            release.api(REPO, 'git/ref/tags/v1.01')
        response = subprocess.CompletedProcess([], 1, '', 'network error')
        with patch.object(release.subprocess, 'run', return_value=response), self.assertRaises(RuntimeError):
            release.api(REPO, 'releases/latest', missing=True)

    def test_feed_has_exact_vpk_hash_identity_and_versioned_urls(self):
        with tempfile.TemporaryDirectory() as temporary:
            build, output = fixture(Path(temporary))
            release.prepare(REPO, '01.01', build, output)
            release.verify_assets(output)
            package = ET.parse(output / 'VLMP00001-ver.xml').find('./tag/package')
            payload = (output / release.PAYLOADS[0]).read_bytes()
            self.assertEqual(package.attrib['sha1sum'], hashlib.sha1(payload).hexdigest())
            self.assertEqual(package.attrib['size'], str(len(payload)))
            self.assertEqual(package.attrib['version'], '01.01')
            self.assertEqual(package.attrib['content_id'], release.CONTENT_ID)
            self.assertEqual(package.attrib['url'], f'https://github.com/{REPO}/releases/download/v1.01/vita_moonlight_paf-system.vpk')
            self.assertIn('/v1.01/', package.find('changeinfo').attrib['url'])
            changeinfo = (output / 'VLMP00001-changeinfo.xml').read_text()
            self.assertIn('<changes><![CDATA[', changeinfo)
            self.assertIn(']]></changes>', changeinfo)
            self.assertTrue(ET.parse(output / 'VLMP00001-changeinfo.xml').findtext('changes'))
            self.assertEqual(set(path.name for path in output.iterdir()), set(release.ASSETS))
            self.assertEqual(len((output / 'SHA256SUMS').read_text().splitlines()), len(release.ASSETS) - 1)

    def test_mismatched_sfo_profile_identity_version_and_ini_are_rejected(self):
        for overrides in ({'CATEGORY': 'gd'}, {'TITLE_ID': 'OTHER0001'}, {'APP_VER': '01.00'},
                          {'VERSION': '00.00'}, {'CONTENT_ID': ''}):
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory() as temporary:
                build, output = fixture(Path(temporary), **overrides)
                with self.assertRaises(ValueError):
                    release.prepare(REPO, '01.01', build, output)
        with tempfile.TemporaryDirectory() as temporary:
            build, _ = fixture(Path(temporary), ini=b'title_id=OTHER0001\n')
            with self.assertRaises(ValueError):
                release.verify_vpk(build / release.PAYLOADS[0], '01.01')

    def test_truncated_and_malformed_sfo_are_rejected(self):
        data = fake_sfo()
        for contents in (data[:10], b'BAD!' + data[4:], data[:20], data[:-1]):
            with self.subTest(length=len(contents)), self.assertRaises(ValueError):
                release.sfo_strings(contents)

    @patch.dict(os.environ, ENV)
    def test_tag_publication_waits_for_every_asset_and_never_changes_refs(self):
        with tempfile.TemporaryDirectory() as temporary:
            build, output = fixture(Path(temporary))
            release.prepare(REPO, '01.01', build, output)
            calls = []
            def api(repo, endpoint, payload=None, missing=False):
                calls.append(endpoint)
                if endpoint == 'git/ref/tags/v1.01':
                    self.assertIsNone(payload)
                    return tag_reference()
                if endpoint == 'releases':
                    self.assertTrue(payload['draft'])
                    self.assertEqual(payload['target_commitish'], ENV['SOURCE_SHA'])
                    return {'id': 7, 'html_url': 'https://example.test/release'}
                if '/assets?' in endpoint:
                    return [{'name': name, 'size': (output / name).stat().st_size} for name in release.ASSETS]
                return None
            def command(args, **kwargs):
                calls.append('upload' if args[1] == 'release' else 'publish')
                if args[1] == 'release':
                    self.assertNotIn('--clobber', args)
                return subprocess.CompletedProcess(args, 0)
            with patch.object(release, 'api', side_effect=api), patch.object(release.subprocess, 'run', side_effect=command):
                release.publish(REPO, '01.01', output)
            self.assertNotIn('git/refs', calls)
            self.assertLess(calls.index('releases'), calls.index('upload'))
            self.assertLess(calls.index('upload'), calls.index('releases/7/assets?per_page=100'))
            self.assertEqual(calls[-3:], ['git/ref/tags/v1.01', 'releases/latest', 'publish'])

    @patch.dict(os.environ, ENV)
    def test_a_tag_moved_during_upload_cannot_be_published(self):
        with tempfile.TemporaryDirectory() as temporary:
            build, output = fixture(Path(temporary))
            release.prepare(REPO, '01.01', build, output)
            references = iter((tag_reference(), tag_reference(sha='b' * 40)))
            def api(repo, endpoint, payload=None, missing=False):
                if endpoint == 'git/ref/tags/v1.01':
                    return next(references)
                if endpoint == 'releases':
                    return {'id': 7, 'html_url': 'test'}
                if '/assets?' in endpoint:
                    return [{'name': name, 'size': (output / name).stat().st_size} for name in release.ASSETS]
                return None
            with patch.object(release, 'api', side_effect=api), patch.object(release.subprocess, 'run') as run:
                with self.assertRaises(ValueError):
                    release.publish(REPO, '01.01', output)
                self.assertEqual(run.call_count, 1)  # upload, never publish

    @patch.dict(os.environ, ENV)
    def test_upload_failure_or_incomplete_assets_never_publish(self):
        with tempfile.TemporaryDirectory() as temporary:
            build, output = fixture(Path(temporary))
            release.prepare(REPO, '01.01', build, output)
            def api(repo, endpoint, payload=None, missing=False):
                if endpoint == 'git/ref/tags/v1.01':
                    return tag_reference()
                return {'id': 7, 'html_url': 'test'} if endpoint == 'releases' else None
            with patch.object(release, 'api', side_effect=api), patch.object(release.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'gh')) as run:
                with self.assertRaises(subprocess.CalledProcessError):
                    release.publish(REPO, '01.01', output)
                self.assertEqual(run.call_count, 1)
            for failure in ('missing', 'size', 'digest'):
                uploaded = [{'name': name, 'size': (output / name).stat().st_size}
                            for name in release.ASSETS]
                if failure == 'missing':
                    uploaded.pop()
                elif failure == 'size':
                    uploaded[0]['size'] += 1
                else:
                    uploaded[0]['digest'] = 'sha256:wrong'
                def incomplete(repo, endpoint, payload=None, missing=False):
                    return uploaded if '/assets?' in endpoint else api(repo, endpoint, payload, missing)
                with self.subTest(failure=failure), patch.object(release, 'api', side_effect=incomplete), patch.object(release.subprocess, 'run') as run:
                    with self.assertRaises(ValueError):
                        release.publish(REPO, '01.01', output)
                    self.assertEqual(run.call_count, 1)
            (output / release.PAYLOADS[0]).write_bytes(b'corrupt')
            with patch.object(release, 'api', side_effect=api) as mocked_api, self.assertRaises(ValueError):
                release.publish(REPO, '01.01', output)
            self.assertNotIn('releases', [call.args[1] for call in mocked_api.call_args_list])

    def test_cmake_and_packaged_config_use_the_release_identity(self):
        cmake = (ROOT / 'CMakeLists.txt').read_text()
        self.assertIn(f'set(MOONLIGHT_CONTENT_ID "{release.CONTENT_ID}")', cmake)
        self.assertIn('VERSION "${MOONLIGHT_APP_VERSION}"', cmake)
        self.assertIn('-s VERSION=${MOONLIGHT_APP_VERSION}', cmake)
        ini = (ROOT / 'sce_sys/homebrew_update.ini').read_text()
        self.assertIn(f'title_id={release.TITLE_ID}\n', ini)
        self.assertIn(f'https://github.com/{REPO}/releases/latest/download/{release.TITLE_ID}-ver.xml\n', ini)


if __name__ == '__main__':
    unittest.main()
