"""Interpret both decoder ownership branches; no compiler, GPU or native allocator."""
import re
import unittest

from pycparser import c_parser
from test_host_persistence import run
from test_host_storage_paths import extract
from test_xml_source import ROOT, strip_directives


def profile(source, system):
    active = [True]
    output = []
    for line in source.splitlines():
        if line in ('#ifdef MOONLIGHT_SYSTEM_APP', '#ifndef MOONLIGHT_SYSTEM_APP'):
            active.append(active[-1] and (system if line.startswith('#ifdef') else not system))
        elif line == '#else':
            active[-1] = active[-2] and not active[-1]
        elif line == '#endif':
            active.pop()
        elif active[-1]:
            output.append(line)
    return '\n'.join(output)


class VideoCleanup(unittest.TestCase):
    def test_normal_frees_owned_control_once_and_system_preserves_its_owner(self):
        source = extract((ROOT / 'src/moonlight/vita_video_renderer.c').read_text(), 'vita_video_cleanup')
        for system in (False, True):
            with self.subTest(system=system):
                code = re.sub(r'//[^\n]*', '', strip_directives(profile(source, system)))
                body = c_parser.CParser().parse(code).ext[-1].body
                calls, freed = [], set()
                def free(pointer):
                    if pointer:
                        self.assertNotIn(pointer, freed, 'double free')
                        freed.add(pointer)
                        calls.append(('free', pointer))
                values = dict(s_decoder=11, s_active=1, s_decoder_memblock=7, s_decoder_info=22,
                              s_init_info=33, s_decoder_buffer=44, s_decoder_buffer_size=999,
                              s_frame_pool_pending_release=0, s_decoded_frames=3, NULL=0,
                              SCE_VIDEODEC_TYPE_HW_AVCDEC=1,
                              moonlight_video_invalidate=lambda: calls.append('invalidate'),
                              sceAvcdecDeleteDecoder=lambda pointer: calls.append(('delete', pointer)),
                              vita_system_video_destroy=lambda: calls.append('destroy') or -1,
                              gs_sps_stop=lambda: calls.append('sps-stop'), free=free,
                              sceKernelFreeMemBlock=lambda block: calls.append(('block', block)),
                              sceVideodecTermLibrary=lambda kind: calls.append('term'))
                if system:
                    run(body, values)
                    self.assertEqual(calls, ['invalidate', 'destroy'])
                    self.assertEqual((values['s_decoder'], values['s_init_info'],
                                      values['s_decoder_buffer'], values['s_frame_pool_pending_release']), (11, 33, 44, 0))
                    calls.clear()
                    values['vita_system_video_destroy'] = lambda: calls.append('destroy') or 0
                run(body, values)
                self.assertEqual(values['s_decoder'], 0)
                self.assertEqual(values['s_frame_pool_pending_release'], 1)
                if system:
                    self.assertNotIn(11, freed)
                    self.assertNotIn(('delete', 11), calls)
                else:
                    self.assertIn(11, freed)
                    self.assertLess(calls.index(('delete', 11)), calls.index(('free', 11)))
                self.assertEqual(values['s_decoder_buffer_size'], 0)
                run(body, values)
                self.assertEqual(calls.count('destroy'), 1 if system else 0)
                self.assertEqual(calls.count(('delete', 11)), 0 if system else 1)
                self.assertEqual(calls.count(('free', 11)), 0 if system else 1)


if __name__ == '__main__':
    unittest.main()
