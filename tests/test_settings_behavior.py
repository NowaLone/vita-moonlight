"""Interpret settings consumers with serial mocks; no C++/PAF/transport execution."""
import re
import unittest
from itertools import product
from unittest.mock import patch

from pycparser import c_ast, c_parser
import test_adapter_lifecycle as runtime
from test_host_persistence import function, run
from test_xml_source import ROOT, strip_directives


class SettingsBehavior(unittest.TestCase):
    def test_stream_keyboard_uses_system_languages_with_existing_open_and_failure_gates(self):
        source = function((ROOT / 'src/pages/page_stream.cpp').read_text(), 'Stream::OpenKeyboardIfRequested')
        code = source[source.index('    if (!dialog_open &&'):source.index('    if (!dialog_open ||')]
        code = code.replace('reinterpret_cast<const SceWChar16 *>(ui_string("msg_keyboard"))', 'keyboard_title()')
        code = re.sub(r'//[^\n]*', '', code)
        body = c_parser.CParser().parse('void open_keyboard(void) {' + code + '}').ext[-1].body
        for requested, opened, loaded, load_result, init_result in product((0, 1), (0, 1), (0, 1), (-1, 0), (-1, 0)):
            with self.subTest(requested=requested, opened=opened, loaded=loaded, load=load_result, init=init_result):
                shown, calls = [], []
                values = dict(dialog_open=opened, module_loaded=loaded, param={}, buffer=[99] * 128,
                              SCE_SYSMODULE_IME=1, SCE_FALSE=0, SCE_IME_TYPE_DEFAULT=0,
                              SCE_IME_OPTION_NO_AUTO_CAPITALIZATION=1, SCE_IME_DIALOG_DIALOG_MODE_WITH_CANCEL=1,
                              SCE_IME_DIALOG_TEXTBOX_MODE_DEFAULT=0, SCE_IME_ENTER_LABEL_GO=2,
                              vita_input_consume_keyboard_request=lambda: requested,
                              sceSysmoduleLoadModule=lambda module: calls.append('load') or load_result,
                              keyboard_title=lambda: 'Клавиатура',
                              memset=lambda buffer, *args: buffer.__setitem__(slice(None), [0] * 128))

                def initialize(pointer):
                    # Poison these defaults so the actual assignments must select system behavior.
                    values[pointer] = dict(supportedLanguages=999, languagesForced=1)

                def show(pointer):
                    shown.append(values[pointer].copy())
                    return init_result

                values.update(sceImeDialogParamInit=initialize, sceImeDialogInit=show)
                run(body, values)
                admitted = requested and not opened
                can_open = admitted and (loaded or load_result >= 0)
                self.assertEqual(calls, ['load'] if admitted and not loaded else [])
                self.assertEqual(bool(shown), bool(can_open))
                self.assertEqual(values['dialog_open'], bool(opened or (can_open and init_result >= 0)))
                if shown:
                    self.assertEqual(shown[0]['supportedLanguages'], 0)
                    self.assertEqual(shown[0]['languagesForced'], 0)
                    self.assertEqual(shown[0]['type'], 0)
                    self.assertEqual(shown[0]['dialogMode'], 1)
                    self.assertEqual(shown[0]['title'], 'Клавиатура')
                    self.assertEqual(shown[0]['maxTextLength'], 120)
                    self.assertEqual(shown[0]['inputTextBuffer'], [0] * 128)

    def test_special_keys_stop_without_ps_capture_and_preserve_other_zones(self):
        source = (ROOT / 'src/moonlight/vita_input.c').read_text()
        process = function(source, 'vita_input_process')
        start = process.index('    if (s_front_touchzones &&')
        end = process.index('\n    /*', start)
        # Isolate the actual touch block. Its goto only skips a latched touch;
        # return is equivalent here because no later controller logic is interpreted.
        code = process[start:end].replace('goto front_done;', 'return;')
        code = re.sub(r'front_done:\s*;', '', code)
        preamble = ('typedef int SceTouchData;'
                    'void touch_poll(void) {')
        body = c_parser.CParser().parse(preamble + code + ' forward_input(); }').ext[-1].body
        original = runtime.expression

        def expression(node, values):
            if isinstance(node, c_ast.BinaryOp) and node.op in ('*', '/'):
                a, b = expression(node.left, values), expression(node.right, values)
                return a * b if node.op == '*' else a // b
            return original(node, values)

        for capture in (0, 1):
            for enabled, mode, x, y, action in (
                    (1, 0, 900, 50, 'stop'), (1, 0, 50, 50, 'keyboard'),
                    (1, 0, 50, 500, 'L3'), (1, 0, 900, 500, 'R3'),
                    (1, 0, 480, 272, None), (0, 0, 900, 50, None),
                    (1, 1, 900, 50, None), (1, 2, 900, 50, None),
                    (1, 3, 900, 50, None)):
                with self.subTest(capture=capture, enabled=enabled, mode=mode, x=x, y=y):
                    calls = []
                    front = dict(reportNum=1, report=[dict(x=x * 2, y=y * 2)])
                    values = dict(s_front_touchzones=enabled, s_touchscreen_mode=mode,
                                  s_ps_button_capture=capture, s_zone_latched=0,
                                  s_keyboard_request=0, SCE_TOUCH_PORT_FRONT=0,
                                  LS_CLK_FLAG=64, RS_CLK_FLAG=128,
                                  BUTTON_ACTION_PRESS=1, BUTTON_ACTION_RELEASE=2, BUTTON_RIGHT=3,
                                  memset=lambda *args: None,
                                  moonlight_stream_stop=lambda: calls.append('stop'),
                                  LiSendMouseButtonEvent=lambda *args: calls.append('mouse'),
                                  LiSendMultiControllerEvent=lambda *args: calls.append(
                                      'L3' if args[2] == 64 else 'R3'),
                                  forward_input=lambda: calls.append('forward'))

                    def peek(port, destination, count):
                        values[destination] = front
                        return 1

                    values['sceTouchPeek'] = peek
                    with patch.object(runtime, 'expression', expression):
                        run(body, values)
                        self.assertEqual(calls, ['stop'] if action == 'stop' else
                                         ([action] if action in ('L3', 'R3') else []) + ['forward'])
                        self.assertEqual(values['s_keyboard_request'], int(action == 'keyboard'))
                        if action == 'stop':
                            run(body, values)  # Holding does not request a second stop.
                            self.assertEqual(calls, ['stop'])
                            front['reportNum'] = 0
                            run(body, values)
                            self.assertEqual(values['s_zone_latched'], 0)
                            front['reportNum'] = 1
                            run(body, values)
                            self.assertEqual(calls, ['stop', 'forward', 'stop'])

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

    def test_keyboard_sends_one_utf8_text_packet_for_system_input_languages(self):
        for text in ('Hello, World! 123 @#', 'Привет, мир!', 'Français déjà', 'Grüße', 'Español',
                     '日本語', '한국어', '中文', 'Türkçe', '🙂', 'я' * 120):
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
