#!/usr/bin/env python3
"""Maintainer/CI release helpers. Never build or modify the installed application."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
TITLE_ID = 'VLMP00001'
CONTENT_ID = 'EP9000-VLMP00001_00-0000000000000000'
PAYLOADS = tuple(f'vita_moonlight_paf-system.{ext}' for ext in ('vpk', 'self', 'elf'))
ARCHIVES = ('vita-moonlight-paf-source.tar.gz', 'vita-moonlight-paf-build-evidence.tar.gz')
ASSETS = (*PAYLOADS, *ARCHIVES, f'{TITLE_ID}-ver.xml', f'{TITLE_ID}-changeinfo.xml', 'SHA256SUMS')


def version_number(version):
    if not re.fullmatch(r'[0-9]{2}\.[0-9]{2}', version):
        raise ValueError('Version must use Vita NN.NN, for example 01.01')
    return tuple(map(int, version.split('.')))


def release_tag(version):
    major, minor = version_number(version)
    return f'v{major}.{minor:02d}'


def pushed_version():
    match = re.fullmatch(r'refs/tags/v(0|[1-9][0-9]?)\.([0-9]{2})', os.environ['GITHUB_REF'])
    if os.environ['GITHUB_EVENT_NAME'] != 'push' or not match:
        raise ValueError('Release requires a pushed tag such as v1.01 (Vita version 01.01)')
    return f'{int(match[1]):02d}.{match[2]}'


def api(repo, endpoint, payload=None, missing=False):
    command = ['gh', 'api', '--hostname', 'github.com', '--include', f'repos/{repo}/{endpoint}']
    if payload is not None:
        command += ['--method', 'POST', '--input', '-']
    result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                            capture_output=True, text=True, check=False)
    headers, _, body = result.stdout.replace('\r\n', '\n').partition('\n\n')
    status = re.match(r'HTTP/\S+ (\d{3})', headers)
    if result.returncode:
        if missing and status and status[1] == '404':
            return None
        raise RuntimeError(f'GitHub request failed: {endpoint}: {result.stderr.strip()}')
    if not status or not 200 <= int(status[1]) < 300:
        raise RuntimeError(f'Unexpected GitHub response: {endpoint}')
    return json.loads(body) if body.strip() else None


def ensure_newer(repo, version):
    latest = api(repo, 'releases/latest', missing=True)
    if latest is not None:
        match = re.fullmatch(r'v([0-9]{1,2})\.([0-9]{2})', latest['tag_name'])
        if not match or version_number(version) <= tuple(map(int, match.groups())):
            raise ValueError('Release version must be newer than the latest stable release')


def verify_tag(repo, tag):
    sha = os.environ['SOURCE_SHA']
    if not re.fullmatch(r'[0-9a-f]{40}', sha):
        raise ValueError('Release requires the exact built source commit')
    reference = api(repo, f'git/ref/tags/{tag}')
    if reference['ref'] != f'refs/tags/{tag}':
        raise ValueError('Unexpected Git tag reference')
    obj = reference['object']
    seen = set()
    while obj['type'] == 'tag':
        if not re.fullmatch(r'[0-9a-f]{40}', obj['sha']) or obj['sha'] in seen or len(seen) >= 16:
            raise ValueError('Invalid annotated tag chain')
        seen.add(obj['sha'])
        obj = api(repo, f'git/tags/{obj["sha"]}')['object']
    if obj['type'] != 'commit' or obj['sha'] != sha:
        raise ValueError('Pushed tag no longer points to the built source commit')
    return sha


def preflight(repo, version):
    tag = release_tag(version)
    if version != pushed_version():
        raise ValueError('Release version must match the pushed tag')
    verify_tag(repo, tag)
    if api(repo, f'releases/tags/{tag}', missing=True) is not None:
        raise ValueError(f'Release {tag} already exists; choose a new version')
    ensure_newer(repo, version)
    return tag


def sfo_strings(data):
    if len(data) < 20:
        raise ValueError('Truncated param.sfo')
    magic, _, keys, values, count = struct.unpack_from('<5I', data)
    if magic != 0x46535000 or count > 128 or not 20 + count * 16 <= keys <= values <= len(data):
        raise ValueError('Invalid param.sfo header')
    result = {}
    for index in range(count):
        key, fmt, length, capacity, offset = struct.unpack_from('<HHIII', data, 20 + index * 16)
        start = keys + key
        end = data.find(b'\0', start, values)
        if not keys <= start < end < values or length > capacity or values + offset + capacity > len(data):
            raise ValueError('Invalid param.sfo entry')
        name = data[start:end].decode('ascii')
        if name in result:
            raise ValueError('Duplicate param.sfo key')
        if fmt == 0x0204:
            raw = data[values + offset:values + offset + length]
            if not raw.endswith(b'\0') or b'\0' in raw[:-1]:
                raise ValueError('Invalid param.sfo string')
            result[name] = raw[:-1].decode('utf-8')
    return result


def verify_vpk(path, version):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise ValueError('Duplicate or corrupt VPK entries')
        if archive.getinfo('eboot.bin').file_size == 0:
            raise ValueError('Empty executable')
        expected = {'TITLE_ID': TITLE_ID, 'APP_VER': version, 'VERSION': version,
                    'CONTENT_ID': CONTENT_ID, 'CATEGORY': 'gdc'}
        actual = sfo_strings(archive.read('sce_sys/param.sfo'))
        if any(actual.get(key) != value for key, value in expected.items()):
            raise ValueError('VPK title, version, Content ID or system profile does not match')
        if archive.read('sce_sys/homebrew_update.ini') != (ROOT / 'sce_sys/homebrew_update.ini').read_bytes():
            raise ValueError('VPK update configuration does not match the source')


def prepare(repo, version, build_dir, output):
    tag = release_tag(version)
    output.mkdir(parents=True, exist_ok=True)
    if set(path.name for path in output.iterdir()) != set(ARCHIVES):
        raise ValueError('Release directory must initially contain only source and evidence archives')
    verify_vpk(build_dir / PAYLOADS[0], version)
    for name in PAYLOADS:
        source = build_dir / name
        if not source.is_file() or source.stat().st_size == 0:
            raise ValueError(f'Missing or empty payload: {name}')
        shutil.copyfile(source, output / name)
    for name in ARCHIVES:
        if (output / name).stat().st_size == 0:
            raise ValueError(f'Empty archive: {name}')
    vpk = (output / PAYLOADS[0]).read_bytes()
    base = f'https://github.com/{repo}/releases/download/{tag}'
    patch = ET.Element('titlepatch', status='alive', titleid=TITLE_ID)
    release = ET.SubElement(patch, 'tag', name=TITLE_ID + '_T0', signoff='true')
    package = ET.SubElement(release, 'package', version=version, size=str(len(vpk)),
                            sha1sum=hashlib.sha1(vpk).hexdigest(), url=f'{base}/{PAYLOADS[0]}',
                            psp2_system_ver='56623104', content_id=CONTENT_ID)
    ET.SubElement(ET.SubElement(package, 'paramsfo'), 'title').text = 'Moonlight'
    ET.SubElement(package, 'changeinfo', url=f'{base}/{TITLE_ID}-changeinfo.xml')
    ET.ElementTree(patch).write(output / f'{TITLE_ID}-ver.xml', encoding='utf-8', xml_declaration=True)
    # VitaHomebrewUpdate's parser requires these exact CDATA delimiters.
    changes = f'Moonlight {tag} (system).\nRelease notes: https://github.com/{repo}/releases/tag/{tag}'
    (output / f'{TITLE_ID}-changeinfo.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<changeinfo><changes><![CDATA['
        + changes.replace(']]>', '] ]>') + ']]></changes></changeinfo>\n', encoding='utf-8')
    checksums = ''.join(f'{hashlib.sha256((output / name).read_bytes()).hexdigest()}  {name}\n'
                        for name in ASSETS if name != 'SHA256SUMS')
    (output / 'SHA256SUMS').write_text(checksums, encoding='ascii')


def verify_assets(directory):
    if set(path.name for path in directory.iterdir()) != set(ASSETS):
        raise ValueError('Release asset set is incomplete or contains unexpected files')
    expected = ''.join(f'{hashlib.sha256((directory / name).read_bytes()).hexdigest()}  {name}\n'
                       for name in ASSETS if name != 'SHA256SUMS')
    if any((directory / name).stat().st_size == 0 for name in ASSETS) or (directory / 'SHA256SUMS').read_text() != expected:
        raise ValueError('Release assets are empty or their checksums do not match')


def publish(repo, version, directory):
    tag = preflight(repo, version)
    verify_assets(directory)
    verify_vpk(directory / PAYLOADS[0], version)
    sha = os.environ['SOURCE_SHA']
    body = (f'System profile only; Title ID `{TITLE_ID}`, Vita APP_VER `{version}`.\n\n'
            f'Source commit: `{sha}`\n\n'
            f'Build: https://github.com/{repo}/actions/runs/{os.environ["GITHUB_RUN_ID"]}\n\n'
            'See docs/INSTALL.md and docs/RELEASE.md in the source bundle for installation, '
            'release checks and known limits. Build success alone is not Vita hardware validation.')
    release = api(repo, 'releases', {'tag_name': tag, 'target_commitish': sha, 'name': f'Moonlight {tag}',
                                   'body': body, 'draft': True, 'prerelease': False, 'make_latest': 'false'})
    subprocess.run(['gh', 'release', 'upload', tag, *(str(directory / name) for name in ASSETS),
                    '--repo', repo], check=True)
    uploaded = api(repo, f'releases/{release["id"]}/assets?per_page=100')
    if {asset['name'] for asset in uploaded} != set(ASSETS):
        raise ValueError('Uploaded asset set differs; leaving the release as a draft')
    for asset in uploaded:
        path = directory / asset['name']
        digest = 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()
        if asset['size'] != path.stat().st_size or asset.get('digest') not in (None, digest):
            raise ValueError('Uploaded asset size/digest differs; leaving the release as a draft')
    verify_tag(repo, tag)
    ensure_newer(repo, version)
    # Publish only after verifying every download and rechecking the pushed tag.
    subprocess.run(['gh', 'api', '--silent', '--method', 'PATCH', f'repos/{repo}/releases/{release["id"]}',
                    '--input', '-'], input=json.dumps({'draft': False, 'make_latest': 'true'}),
                   text=True, check=True)
    print(release['html_url'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('resolve', 'check', 'prepare', 'publish'))
    parser.add_argument('--build-dir', type=Path, default=ROOT / 'build')
    parser.add_argument('--directory', type=Path)
    args = parser.parse_args()
    repo = os.environ['GITHUB_REPOSITORY']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        parser.error('Invalid GitHub repository')
    try:
        version = pushed_version()
        if args.command == 'resolve':
            print(f'APP_VERSION={version}')
        elif args.command == 'check':
            print(preflight(repo, version))
        elif args.directory is None:
            parser.error('--directory is required')
        elif args.command == 'prepare':
            prepare(repo, version, args.build_dir, args.directory)
        else:
            publish(repo, version, args.directory)
    except (ValueError, RuntimeError, KeyError, OSError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        parser.exit(1, f'Release failed: {error}\n')


if __name__ == '__main__':
    main()
