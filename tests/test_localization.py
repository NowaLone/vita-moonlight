"""Check locale resources and interpret UTF-8/pairing paths; no builds or Vita."""
import ast
import re
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from pycparser import c_ast, c_parser
import test_adapter_lifecycle as runtime
from test_host_persistence import function, run
from test_xml_source import ROOT


def dictionary(locale):
    return {node.get('id'): node.get('src') for node in
            ET.parse(ROOT / f'cxml/locale/{locale}.xml').getroot()}


class Localization(unittest.TestCase):
    def test_complete_unique_dictionaries_cover_resource_and_code_references(self):
        en = dictionary('en')
        self.assertEqual(en.keys(), dictionary('ru').keys())
        for locale in ('en', 'ru'):
            nodes = list(ET.parse(ROOT / f'cxml/locale/{locale}.xml').getroot())
            self.assertEqual(len(nodes), len({n.get('id') for n in nodes}))
            self.assertTrue(all(n.get('src') for n in nodes))
        references = set()
        for path in (ROOT / 'cxml').glob('*.xml'):
            references.update(v for n in ET.parse(path).iter() for v in n.attrib.values()
                              if v.startswith('msg_'))
        for path in (ROOT / 'src').rglob('*.cpp'):
            references.update(re.findall(r'"(msg_\w+)"', path.read_text()))
        # This ID is supplied dynamically by AppSettings' existing callback.
        references.discard('msg_about_build_info')
        self.assertFalse(references - en.keys())
        locales = ET.parse(ROOT / 'cxml/vita_moonlight_ui.xml').findall('stringtable/locale')
        self.assertEqual({n.get('id') for n in locales}, {'en', 'ru'})
        for node in locales:
            self.assertTrue((ROOT / 'cxml' / node.get('src')).is_file())

    def test_printf_contracts_match_and_fixed_dialog_messages_fit_utf8_buffers(self):
        en, ru = dictionary('en'), dictionary('ru')
        for key in en:
            with self.subTest(key=key):
                self.assertEqual(re.findall(r'%(?:\.[0-9]+)?[%sduf]', en[key]),
                                 re.findall(r'%(?:\.[0-9]+)?[%sduf]', ru[key]))
                # No unrecognised conversions, positional parameters or %n.
                if key.startswith('msg_stats_') or key in ('msg_about_build_format', 'msg_pairing_server_error'):
                    self.assertNotIn('%', re.sub(r'%(?:\.[0-9]+)?[%sduf]', '', ru[key]))
        for key in ru:
            if key == 'msg_delete_confirmation' or key.startswith(('msg_error_', 'msg_pairing_', 'msg_confirm_', 'msg_enter_',
                               'msg_invalid_', 'msg_needs_', 'msg_app_unavailable', 'msg_pc_no_')):
                for locale in (en, ru):
                    self.assertLess(len((locale[key] + ' (0xFFFFFFFF)').encode('utf-8')), 512, key)

    def test_native_locale_selection_uses_russian_and_english_fallback(self):
        source = (ROOT / 'src/app/paf_runtime.cpp').read_text()
        code = source[source.index('static Locale interface_locale'):source.index('\nint paf_runtime_main')]
        body = c_parser.CParser().parse('typedef int Locale;' + code).ext[-1].body
        for language in range(-1, 25):
            self.assertEqual(run(body, dict(system_locale=language, Locale_RU=8, Locale_EN=1)),
                             8 if language == 8 else 1)
        self.assertIn('pluginParam.locale = interface_locale(paf_fw->GetLocale());', source)

    def test_utf8_truncation_retains_complete_characters_at_every_byte_boundary(self):
        source = function((ROOT / 'src/common.cpp').read_text(), 'trim_incomplete_utf8')
        body = c_parser.CParser().parse('typedef unsigned int size_t;' + source).ext[-1].body
        original_expression, original_execute = runtime.expression, runtime.execute

        def expression(node, values):
            if isinstance(node, c_ast.Constant):
                return ord(ast.literal_eval(node.value)) if node.type == 'char' else int(node.value, 0)
            if isinstance(node, c_ast.BinaryOp) and node.op == '&':
                return expression(node.left, values) & expression(node.right, values)
            return original_expression(node, values)

        def execute(node, values):
            if isinstance(node, c_ast.UnaryOp) and node.op == '--':
                values[node.expr.name] -= 1
            elif isinstance(node, c_ast.Assignment) and isinstance(node.lvalue, c_ast.ArrayRef):
                expression(node.lvalue.name, values)[expression(node.lvalue.subscript, values)] = expression(node.rvalue, values)
            else:
                original_execute(node, values)

        for raw in (b'', b'ASCII', 'AРусский € 漢字 😀'.encode(), ('Я' * 300 + '😀').encode()):
            for boundary in range(len(raw) + 1):
                prefix = raw[:boundary]
                data = bytearray(prefix + b'\0')
                with patch.object(runtime, 'expression', expression), patch.object(runtime, 'execute', execute):
                    run(body, dict(text=data, strlen=lambda value: value.index(0)))
                self.assertEqual(data[:data.index(0)].decode(), prefix.decode(errors='ignore'))

    def test_native_utf16_conversion_preserves_russian_and_clears_failed_output(self):
        source = (ROOT / 'src/common.cpp').read_text()
        code = source[source.index('paf::string ui_text'):source.index('\nvoid trim_incomplete_utf8')]
        code = code.replace('paf::string ui_text', 'char *ui_text').replace('paf::string text;', 'char *text;')
        code = code.replace('paf::common::Utf16ToUtf8', 'convert').replace('text.clear()', 'clear()')
        body = c_parser.CParser().parse(code).ext[-1].body
        for result in (0, -1):
            values = dict(id='msg_computers', ui_string=lambda key: dictionary('ru')[key])

            def convert(text, destination):
                values[destination] = text.encode('utf-8')
                return result

            values.update(convert=convert, clear=lambda: values.update(text=b''))
            self.assertEqual(run(body, values), b'' if result < 0 else 'Компьютеры'.encode())

    def test_pairing_errors_preserve_typed_categories_and_server_text_in_both_locales(self):
        code = function((ROOT / 'src/pages/page_pairing.cpp').read_text(), 'Pairing::ShowPairingError')
        code = code.replace('Pairing::', '').replace('paf::string message', 'const char *message')
        code = re.sub(r'(ui_text\("msg_\w+"\)|message)\.c_str\(\)', r'\1', code)
        code = code.replace("m_dialog_message[sizeof(m_dialog_message) - 1] = '\\0';", '')
        body = c_parser.CParser().parse(code).ext[-1].body
        categories = ('INTERNAL', 'INCORRECT_PIN', 'NETWORK', 'SECURITY', 'PROTOCOL')
        keys = ('failed', 'incorrect_pin', 'network', 'security', 'rejected')
        for locale in ('en', 'ru'):
            strings = dictionary(locale)
            for result, key in [*enumerate(keys), (99, 'failed')]:
                shown = []
                values = dict(result=result, server_status_code=0, server_status_message='', m_dialog_open=0,
                              m_dialog_message='buffer', ui_text=lambda key: strings[key],
                              strncpy=lambda dst, text, size: shown.append(text),
                              trim_incomplete_utf8=lambda text: None, ShowSystemError=lambda text: None)
                values.update({'MOONLIGHT_PAIRING_ERROR_' + name: i for i, name in enumerate(categories)})
                # Buffer ownership/capacity is handled by the separate truncation check.
                run(body, values)
                self.assertEqual(shown, [strings['msg_pairing_' + key]])
                if key == 'rejected':
                    shown.clear()
                    values.update(server_status_code=409, server_status_message='Sunshine: busy 100%',
                                  snprintf=lambda dst, size, fmt, *args: shown.append(fmt % args))
                    run(body, values)
                    self.assertEqual(shown, [strings['msg_pairing_server_error'] % ('Sunshine: busy 100%', 409)])

    def test_livearea_russian_welcome_matches_packaged_language_variant(self):
        import test_livearea as frames
        frames.LiveArea.setUpClass()
        harness = frames.LiveArea()
        harness.setUp()
        harness.strings = dictionary('ru')
        output = [0] * 2048
        self.assertGreater(harness.invoke('make_frame_xml', output, len(output), 3, frames.string(''), None, 0, True), 0)
        generated = ET.fromstring(frames.text(output)).find('liveitem/text/str').text
        template = ET.parse(ROOT / 'sce_sys/livearea/contents/template.xml')
        packaged = template.find("frame[@id='frame3']/liveitem[lang='ru']/text/str").text
        self.assertEqual(generated, packaged)
        self.assertEqual(generated, dictionary('ru')['msg_livearea_welcome'])


if __name__ == '__main__':
    unittest.main()
