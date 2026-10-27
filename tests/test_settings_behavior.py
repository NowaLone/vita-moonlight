"""Interpret settings consumers with serial mocks; no C++/PAF/transport execution."""
import unittest
from unittest.mock import patch

from pycparser import c_ast, c_parser
import test_adapter_lifecycle as runtime
from test_host_persistence import function, run
from test_xml_source import ROOT, strip_directives


class SettingsBehavior(unittest.TestCase):
    def test_rfi_capability_is_ready_before_the_first_connection_and_each_toggle(self):
        source = (ROOT / 'src/moonlight/vita_video_renderer.c').read_text()
        setter = function(source, 'moonlight_video_set_stream_options')
        unit = c_parser.CParser().parse('typedef struct {int capabilities;} Callbacks;'
                                       + strip_directives(setter))
        body = unit.ext[-1].body
        base = 0x02000001
        values = dict(fps=60, frame_pacer=1, vblank_wait=0, center_region=0,
                      CAPABILITY_DIRECT_SUBMIT=1, CAPABILITY_REFERENCE_FRAME_INVALIDATION_AVC=2,
                      CAPABILITY_SLICES_PER_FRAME=lambda slices: slices << 24,
                      decoder_callbacks_vita=dict(capabilities=base))
        original = runtime.expression

        def expression(node, scope):
            if isinstance(node, c_ast.BinaryOp) and node.op == '|':
                return expression(node.left, scope) | expression(node.right, scope)
            return original(node, scope)

        snapshots = []
        with patch.object(runtime, 'expression', expression):
            for enabled in (1, 0, 1, 0):
                with self.subTest(enabled=enabled, connection=len(snapshots)):
                    values['ref_frame_invalidation'] = enabled
                    run(body, values)
                    # common-c copies capabilities at entry, before invoking decoder setup.
                    snapshot = values['decoder_callbacks_vita'].copy()
                    snapshots.append(snapshot)
                    self.assertEqual(snapshot['capabilities'], base | (2 if enabled else 0))
        self.assertEqual([s['capabilities'] for s in snapshots], [base | 2, base, base | 2, base])
        self.assertNotIn('decoder_callbacks_vita.capabilities =', function(source, 'vita_video_setup'))


if __name__ == '__main__':
    unittest.main()
