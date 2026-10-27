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

    def keyboard_send(self, text, conversion_result=0, send_result=0):
        source = (ROOT / 'src/pages/page_stream.cpp').read_text()
        code = function(source, 'send_keyboard_text')
        code = code.replace('paf::string utf8;', 'int utf8 = new_utf8();')
        code = code.replace('paf::common::Utf16ToUtf8', 'convert_utf16')
        code = code.replace('reinterpret_cast<const wchar_t *>(text)', 'text')
        for method in ('empty', 'c_str', 'size'):
            code = code.replace('utf8.' + method + '()', 'utf8_' + method + '(utf8)')
        body = c_parser.CParser().parse('typedef unsigned short SceWChar16;' + code).ext[-1].body
        calls, logs = [], []
        values = dict(text=text, NULL=0, KEY_ACTION_DOWN=3, KEY_ACTION_UP=4,
                      new_utf8=lambda: dict(data=b''),
                      utf8_empty=lambda value: not value['data'],
                      utf8_c_str=lambda value: value['data'], utf8_size=lambda value: len(value['data']),
                      vita_debug_log=lambda *args: logs.append(args),
                      LiSendKeyboardEvent=lambda *args: calls.append(('key', args)))

        def convert(data, destination):
            if conversion_result < 0:
                return conversion_result
            raw = b''.join(unit.to_bytes(2, 'little') for unit in data[:data.index(0)])
            values[destination]['data'] = raw.decode('utf-16-le').encode('utf-8')
            return conversion_result

        def send(data, length):
            calls.append(('text', data, length))
            return send_result

        values.update(convert_utf16=convert, LiSendUtf8TextEvent=send)
        original = runtime.expression

        def expression(node, scope):
            if isinstance(node, c_ast.Constant) and node.type == 'int':
                return int(node.value, 0)
            if isinstance(node, c_ast.BinaryOp) and node.op == '<=':
                return expression(node.left, scope) <= expression(node.right, scope)
            if isinstance(node, c_ast.UnaryOp) and node.op in ('++', 'p++'):
                value = scope[node.expr.name]
                scope[node.expr.name] += 1
                return value if node.op == 'p++' else value + 1
            return original(node, scope)

        # The old ASCII key loop requires only this increment/statement support.
        original_execute = runtime.execute

        def execute(node, scope):
            if isinstance(node, c_ast.UnaryOp):
                expression(node, scope)
            else:
                original_execute(node, scope)

        with patch.object(runtime, 'expression', expression), patch.object(runtime, 'execute', execute):
            run(body, values)
        return calls, logs

    def test_keyboard_sends_one_utf8_text_packet_for_each_supported_ime_language(self):
        for text in ('Hello, World! 123 @#', 'Привет, мир!', 'Français déjà', 'Grüße', 'Español', '🙂', 'я' * 120):
            with self.subTest(text=text):
                raw = text.encode('utf-16-le')
                units = [int.from_bytes(raw[i:i + 2], 'little') for i in range(0, len(raw), 2)] + [0]
                calls, logs = self.keyboard_send(units)
                encoded = text.encode('utf-8')
                self.assertEqual(calls, [('text', encoded, len(encoded))])
                self.assertEqual(logs, [])

    def test_keyboard_empty_conversion_and_send_failures_never_fall_back_to_keycodes(self):
        for text in (0, [0]):
            self.assertEqual(self.keyboard_send(text), ([], []))
        calls, logs = self.keyboard_send([65, 0], conversion_result=-1)
        self.assertEqual(calls, [])
        self.assertEqual(len(logs), 1)
        for result in (-2, 2):  # Uninitialized transport and a full common-c queue.
            calls, logs = self.keyboard_send([65, 0], send_result=result)
            self.assertEqual(calls, [('text', b'A', 1)])
            self.assertEqual(len(logs), 1)


if __name__ == '__main__':
    unittest.main()
