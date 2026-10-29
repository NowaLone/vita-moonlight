"""Compare source settings reads to XML choices with serial AppSettings/module mocks."""
import re
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from pycparser import c_ast, c_parser
import test_adapter_lifecycle as runtime
import test_event_queue as queue_runtime
from test_host_persistence import run
from test_host_storage_paths import extract
from test_xml_source import ROOT, strip_directives


class SettingsValues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / 'src/moonlight/settings.cpp').read_text()
        types = (ROOT / 'include/moonlight/types.h').read_text()
        enum = re.search(r'typedef enum MoonlightSettingKey.*?} MoonlightSettingKey;', types, re.S).group()
        cls.unit = c_parser.CParser().parse(enum)
        cls.keys = {}
        value = -1
        for member in cls.unit.ext[0].type.type.values.enumerators:
            value = int(member.value.value) if member.value else value + 1
            cls.keys[member.name] = value
        cls.functions = {}
        for name in ('key_name', 'default_value', 'valid_value', 'moonlight_settings_get_value'):
            code = extract(source, name).replace('s_settings->GetInt', 'get_int').replace('*out_value', 'out_value[0]')
            cls.functions[name] = c_parser.CParser().parse('typedef int bool;' + enum + strip_directives(code)).ext[-1]
        load = extract(source, 'load_plugin').split('    paf::Plugin::InitParam')[0] + '    return 0;\n}'
        cls.modules = c_parser.CParser().parse('typedef unsigned int size_t;' + load).ext[-1].body
        cls.xml = {node.get('key'): node for node in ET.parse(ROOT / 'cxml/moonlight_settings.xml').iter()
                   if node.get('key') is not None}

    def setUp(self):
        self.harness = queue_runtime.EventQueue()
        self.harness.base_expression, self.harness.base_execute = runtime.expression, runtime.execute

    def expression(self, node, values):
        if isinstance(node, c_ast.UnaryOp) and node.op == 'sizeof':
            value = runtime.expression(node.expr, values)
            return 4 * len(value) if isinstance(value, list) else 4
        if isinstance(node, c_ast.InitList):
            return [runtime.expression(item, values) for item in node.exprs]
        if isinstance(node, c_ast.BinaryOp) and node.op in ('<=', '/'):
            a, b = runtime.expression(node.left, values), runtime.expression(node.right, values)
            return int(a <= b) if node.op == '<=' else a // b
        return self.harness.expression(node, values)

    def invoke(self, name, *arguments, **extra):
        node = self.functions[name]
        values = dict(self.keys, s_initialized=1, s_settings=1, NULL=0)
        values.update(extra)
        values.update(zip((param.name for param in node.decl.type.args.params), arguments))
        for helper in ('key_name', 'default_value', 'valid_value'):
            values[helper] = lambda *args, name=helper: self.invoke(name, *args)
        with patch.object(runtime, 'expression', self.expression), patch.object(runtime, 'execute', self.harness.execute):
            return run(node.body, values)

    def test_defaults_and_accepted_values_match_every_xml_setting(self):
        seen = set()
        for key in range(self.keys['MOONLIGHT_SETTING_COUNT']):
            name = self.invoke('key_name', key)
            seen.add(name)
            node = self.xml[name]
            fallback = int(node.get('default_value'))
            self.assertEqual(self.invoke('default_value', key), fallback, name)
            choices = {int(child.get('value')) for child in node.findall('list_item')} or {0, 1}
            values = set(choices) | {-2**31, -1, 2**31 - 1, 0, 1, 2, fallback}
            ordered = sorted(choices)
            for left, right in zip(ordered, ordered[1:]):
                values.update((left + 1, right - 1))
            values.update((min(choices) - 1, max(choices) + 1))
            for value in values:
                with self.subTest(name=name, value=value):
                    self.assertEqual(bool(self.invoke('valid_value', key, value)), value in choices)
        self.assertEqual(seen, self.xml.keys())

    def test_reads_return_safe_defaults_on_missing_invalid_or_failed_values(self):
        for key in range(self.keys['MOONLIGHT_SETTING_COUNT']):
            name = self.invoke('key_name', key)
            node = self.xml[name]
            fallback = int(node.get('default_value'))
            valid = {int(child.get('value')) for child in node.findall('list_item')} or {0, 1}
            for stored, status in ((None, 0), (None, -7), (fallback, -7), (-1, 0), (2**31 - 1, 0),
                                   *((value, 0) for value in valid)):
                with self.subTest(name=name, stored=stored, status=status):
                    output = [999]
                    def read(read_name, out, default):
                        self.assertEqual((read_name, default), (name, fallback))
                        out[0] = default if stored is None else stored
                        return status
                    self.assertEqual(self.invoke('moonlight_settings_get_value', key, output, get_int=read,
                                                  vita_debug_log=lambda *args: None), 0)
                    self.assertEqual(output[0], stored if status >= 0 and stored in valid else fallback)
        for key, output, ready in ((-1, [999], 1), (999, [999], 1), (0, None, 1), (0, [999], 0)):
            self.assertEqual(self.invoke('moonlight_settings_get_value', key, output, s_initialized=ready,
                                        get_int=lambda *args: self.fail('Unexpected GetInt')), -1)
        source = extract((ROOT / 'src/moonlight/settings.cpp').read_text(), 'moonlight_settings_get_value')
        self.assertNotIn('SetInt', source)

    def test_module_loader_reuses_loaded_modules_and_preserves_failures(self):
        for loaded in (set(), {1, 2, 3}):
            for failure in (None, 1, 2, 3):
                with self.subTest(loaded=loaded, failure=failure):
                    calls = []
                    values = dict(SCE_SYSMODULE_INTERNAL_BXCE=1, SCE_SYSMODULE_INTERNAL_INI_FILE_PROCESSOR=2,
                                  SCE_SYSMODULE_INTERNAL_COMMON_GUI_DIALOG=3, SCE_SYSMODULE_LOADED=0,
                                  sceSysmoduleIsLoadedInternal=lambda module: 0 if module in loaded else -1,
                                  sceSysmoduleLoadModuleInternal=lambda module: calls.append(module) or
                                      (-9 if module == failure else 0))
                    with patch.object(runtime, 'expression', self.expression), patch.object(runtime, 'execute', self.harness.execute):
                        result = run(self.modules, values)
                    expected = [] if loaded else list(range(1, (failure or 3) + 1))
                    self.assertEqual(calls, expected)
                    self.assertEqual(result, -9 if failure and not loaded else 0)


if __name__ == '__main__':
    unittest.main()
