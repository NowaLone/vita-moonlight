"""Interpret host-path admission and side effects; no Vita file I/O or compilation."""
import re
import unittest
from unittest.mock import patch

from pycparser import c_ast, c_parser
import test_adapter_lifecycle as runtime
import test_event_queue as queue_runtime
from test_host_persistence import run
from test_xml_source import ROOT, strip_directives


def extract(source, name):
    start = re.search(r'^(?:static )?[\w *]+\b' + name + r'\(', source, re.M).start()
    return source[start:source.index('\n}', start) + 2]


class HostStoragePaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        device = (ROOT / 'src/backend/legacy/device.c').read_text()
        store = (ROOT / 'src/backend/legacy_device_store.cpp').read_text()
        names = ('device_storage_name_valid', 'device_file_path', 'ensure_host_identity',
                 'load_device_info', 'remove_device_index')
        cls.source = {name: extract(device, name) for name in names}
        # Run the actual rejection paths, stopping before unrelated I/O/INI/array compaction.
        cls.source['load_device_info'] = cls.source['load_device_info'].split('  vita_debug_log(')[0] + '  return true;\n}'
        cls.source['remove_device_index'] = cls.source['remove_device_index'].split('  // Remove from the in-memory array.')[0] + '  return true;\n}'
        for name in ('ensure_device_directory', 'legacy_device_store_get_server_certificate_path'):
            cls.source[name] = extract(store, name)
        cls.functions = {}
        preamble = '''typedef int bool; typedef unsigned int size_t;
            typedef struct {char name[256], storage_name[256], host_id[33];} device_info_t, MoonlightHost;'''
        for name, code in cls.source.items():
            code = code.replace('char path[512] = {0};', 'char path[512];')
            unit = c_parser.CParser().parse(preamble + re.sub(r'//[^\n]*', '', strip_directives(code)))
            cls.functions[name] = unit.ext[-1]

    def setUp(self):
        self.harness = queue_runtime.EventQueue()
        self.harness.base_expression, self.harness.base_execute = runtime.expression, runtime.execute
        self.calls = []
        self.base = '/moonlight/'
        self.library = dict(NULL=0, true=1, false=0, DEVICE_FILE='device.ini',
                            config=dict(key_dir=queue_runtime.Buffer(self.base)), s_initialized=1,
                            strlen=lambda value: len(self.text(value).encode()),
                            strcasecmp=lambda a, b: int(self.text(a).lower() != b.lower()),
                            strchr=lambda text, char: int(chr(char) in text),
                            strncpy=queue_runtime.EventQueue.strncpy,
                            snprintf=self.snprintf,
                            ensure_directory=lambda path: self.calls.append(('mkdir', self.text(path))) or True,
                            vita_debug_log=lambda *args: None)
        self.library.update({name: lambda *args, name=name: self.invoke(name, *args)
                             for name in self.functions})

    @staticmethod
    def text(value):
        return value.text() if isinstance(value, queue_runtime.Buffer) else value

    def snprintf(self, out, size, fmt, *args):
        text = fmt % tuple(self.text(arg) for arg in args)
        encoded = text.encode()
        for i, char in enumerate(encoded[:size - 1] + b'\0'):
            out[i] = char
        return len(encoded)

    def execute(self, node, values):
        if isinstance(node, c_ast.For):
            self.harness.execute(node.init, values)
            steps = 0
            while runtime.expression(node.cond, values):
                steps += 1
                self.assertLessEqual(steps, 256)
                self.harness.execute(node.stmt, values)
                self.harness.execute(node.next, values)
        else:
            self.harness.execute(node, values)

    def invoke(self, name, *args, **extra):
        node = self.functions[name]
        values = dict(self.library, **extra)
        values.update(zip((param.name for param in node.decl.type.args.params), args))
        with patch.object(runtime, 'expression', self.harness.expression), patch.object(runtime, 'execute', self.execute):
            return run(node.body, values)

    def test_components_reject_traversal_client_aliases_and_preserve_unicode(self):
        invalid = ('', '.', '..', '../PC', 'PC/../client', 'PC\\client', 'ux0:other',
                   'client', 'CLIENT', 'Client', 'client.', 'client ', 'PC\nname',
                   'PC\x7f', 'PC?', 'PC*', 'PC"', 'PC<', 'PC>', 'PC|', 'x' * 256)
        for name in invalid:
            with self.subTest(name=name):
                self.assertFalse(self.invoke('device_storage_name_valid', queue_runtime.Buffer(name, 600)))
        self.assertFalse(self.invoke('device_storage_name_valid', None))
        for name in ('PC', 'My PC', 'ПК Ивана', 'PC.local', '.PC', 'a..b', 'x' * 255):
            with self.subTest(name=name):
                self.assertTrue(self.invoke('device_storage_name_valid', queue_runtime.Buffer(name)))

    def test_new_unsafe_display_names_use_uuid_but_existing_paths_stay(self):
        for name, storage, expected in (('../PC', '', 'uuid'), ('client', '', 'uuid'),
                                        ('ПК Ивана', '', 'ПК Ивана'), ('renamed', 'old PC', 'old PC')):
            info = dict(name=queue_runtime.Buffer(name), storage_name=queue_runtime.Buffer(storage),
                        host_id=queue_runtime.Buffer('uuid'))
            self.invoke('ensure_host_identity', info)
            self.assertEqual(info['name'].text(), name)
            self.assertEqual(info['storage_name'].text(), expected)

    def test_paths_reject_invalid_components_and_truncation(self):
        for name in ('../PC', 'client', 'CLIENT', '.', '..'):
            out = queue_runtime.Buffer('poison', 512)
            self.assertFalse(self.invoke('device_file_path', out, queue_runtime.Buffer(name)))
            self.assertEqual(out.text(), '')
        out = queue_runtime.Buffer(size=512)
        self.assertTrue(self.invoke('device_file_path', out, queue_runtime.Buffer('ПК Ивана')))
        self.assertEqual(out.text(), self.base + 'ПК Ивана/device.ini')
        self.library['config']['key_dir'] = queue_runtime.Buffer('x' * 510, 512)
        self.assertFalse(self.invoke('device_file_path', out, queue_runtime.Buffer('PC')))
        self.assertEqual(out.text(), '')

    def test_create_read_delete_and_pin_reject_before_side_effects(self):
        for name in ('../PC', 'client', 'CLIENT', 'PC/other'):
            with self.subTest(name=name):
                info = dict(name=queue_runtime.Buffer('PC'), storage_name=queue_runtime.Buffer(name))
                self.assertFalse(self.invoke('ensure_device_directory', info['storage_name']))
                self.assertFalse(self.invoke('load_device_info', info))
                self.assertFalse(self.invoke('remove_device_index', 0,
                                             known_devices=dict(count=1, devices=[info])))
                out = queue_runtime.Buffer('poison', 512)
                self.assertEqual(self.invoke('legacy_device_store_get_server_certificate_path', info, out, 512,
                                             find_stored_host=lambda host: info), -1)
                self.assertEqual(out.text(), '')
                self.assertEqual(self.calls, [])
        self.assertTrue(self.invoke('ensure_device_directory', queue_runtime.Buffer('PC')))
        self.assertEqual(self.calls, [('mkdir', self.base + 'PC')])

    def test_writer_loader_and_append_use_the_shared_gate(self):
        source = (ROOT / 'src/backend/legacy/device.c').read_text()
        writer = extract(source, 'save_device_info')
        self.assertIn('if (!device_file_path(path, storage_name)) return -1;', writer)
        self.assertLess(writer.index('device_file_path('), writer.index('fopen('))
        append = extract(source, 'append_device')
        self.assertLess(append.index('!device_storage_name_valid(info->storage_name)'), append.index('malloc('))
        loader = extract(source, 'load_all_known_devices')
        self.assertLess(loader.index('!device_storage_name_valid(ent.d_name)'), loader.index('load_device_info('))
        client = extract((ROOT / 'src/backend/legacy_device_store.cpp').read_text(), 'legacy_device_store_get_client_directory')
        self.assertIn('return ensure_directory(out) ? 0 : -1;', client)


if __name__ == '__main__':
    unittest.main()
