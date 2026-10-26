"""Interpret actual frame XML/publication logic with serial native-call mocks.

No compiler, shell/database access, module loading, PAF or Vita execution.
"""
import ast
import copy
import re
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from pycparser import c_ast, c_parser
import test_adapter_lifecycle as runtime
from test_host_persistence import function, run
from test_xml_source import ROOT, strip_directives


def text(data):
    if isinstance(data, str):
        return data
    return bytes(data[:data.index(0)] if 0 in data else data).decode()


def string(value):
    raw = value.encode() if isinstance(value, str) else value
    return list(raw[:255]) + [0] * (256 - len(raw[:255]))


class LiveArea(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'src/services/livearea_service.cpp').read_text()
        names = ('label_character_length', 'make_frame_xml', 'hex_digit', 'LiveAreaService::ParseTarget', 'LiveAreaService::Connected',
                 'LiveAreaService::Applications', 'LiveAreaService::Poll', 'LiveAreaService::Shutdown')
        code = '\n'.join(function(cls.source, name).replace('LiveAreaService::', '') for name in names)
        app = function((ROOT / 'src/app/moonlight_app.cpp').read_text(), 'MoonlightApp::UpdateLiveArea')
        app = app.replace('MoonlightApp::', '').replace('const MoonlightEvent &event', 'const MoonlightEvent *event')
        app = app.replace('m_livearea.Connected', 'Connected').replace('m_livearea.Applications', 'Applications')
        app = app.replace('const MoonlightHost &selected = m_connection.Host()', 'MoonlightHost *selected = selected_host()')
        app = app.replace('m_hosts.Resolve', 'resolve_host').replace('m_applications.GetAll', 'get_apps')
        code = strip_directives(code + app)
        types = '''typedef int bool; typedef struct { int id; char name[256]; } MoonlightApplication;
        typedef struct { char name[256], internal[256], host_id[33]; int port; } MoonlightHost;
        typedef struct { int type, result; } MoonlightEvent;'''
        tree = c_parser.CParser().parse(types + code)
        cls.functions = {node.decl.name: node for node in tree.ext if isinstance(node, c_ast.FuncDef)}

    def setUp(self):
        self.original_expression, self.original_execute = runtime.expression, runtime.execute
        self.state = dict(m_labels=[string('') for _ in range(7)], m_dirty=0,
                          m_host_key=[0] * 65, m_application_ids=[0] * 6,
                          m_pending_frame=-1, m_module_state=0, m_has_host=0)
        self.calls, self.sent = [], []
        self.status, self.submit_result, self.load_result, self.loaded = 0, 0, 0, False
        self.cache, self.cache_result = [], None

    @staticmethod
    def host(name='PC B', host_id='uuid-B'):
        return dict(name=string(name), internal=string('192.0.2.1'), host_id=string(host_id), port=47989)

    def expression(self, node, scope):
        if isinstance(node, c_ast.Constant):
            if node.type == 'char': return ord(ast.literal_eval(node.value))
            if node.type != 'string': return int(re.sub(r'[uUlL]+$', '', node.value), 0)
        if isinstance(node, c_ast.ArrayRef):
            data, index = self.expression(node.name, scope), self.expression(node.subscript, scope)
            value = 0 if isinstance(data, str) and index >= len(data) else data[index]
            return ord(value) if isinstance(value, str) and len(value) == 1 else value
        if isinstance(node, c_ast.UnaryOp):
            if node.op == '*': return self.expression(node.expr, scope)
            if node.op == 'sizeof': return len(self.expression(node.expr, scope))
            if node.op == '~': return ~self.expression(node.expr, scope)
            if node.op in ('++', 'p++'):
                old = self.expression(node.expr, scope)
                new = old[1:] if isinstance(old, list) else old + 1
                self.assign(node.expr, new, scope)
                return old if node.op == 'p++' else new
        if isinstance(node, c_ast.BinaryOp):
            if node.op in ('&', '|', '<<', '>>', '<=', '*', '/'):
                a, b = self.expression(node.left, scope), self.expression(node.right, scope)
                return {'&': lambda: a & b, '|': lambda: a | b, '<<': lambda: a << b,
                        '>>': lambda: a >> b, '<=': lambda: a <= b, '*': lambda: a * b,
                        '/': lambda: a // b}[node.op]()
            if node.op == '+':
                a, b = self.expression(node.left, scope), self.expression(node.right, scope)
                return a[b:] if isinstance(a, (list, str)) else a + b
        return self.original_expression(node, scope)

    def assign(self, target, value, scope):
        if isinstance(target, c_ast.ID): scope[target.name] = value
        elif isinstance(target, c_ast.UnaryOp) and target.op == '*':
            destination = self.expression(target.expr, scope)
            if isinstance(destination, dict):
                destination.clear()
                destination.update(copy.deepcopy(value))
            else: destination[0] = value
        else: self.expression(target.name, scope)[self.expression(target.subscript, scope)] = value

    def execute(self, node, scope):
        if isinstance(node, c_ast.Assignment):
            value = self.expression(node.rvalue, scope)
            if node.op == '&=': value &= self.expression(node.lvalue, scope)
            elif node.op == '|=': value |= self.expression(node.lvalue, scope)
            elif node.op == '+=':
                previous = self.expression(node.lvalue, scope)
                value = previous[value:] if isinstance(previous, list) else previous + value
            else: self.assertEqual(node.op, '=')
            self.assign(node.lvalue, value, scope)
        elif isinstance(node, c_ast.UnaryOp): self.expression(node, scope)
        elif isinstance(node, c_ast.DeclList):
            for declaration in node.decls: self.execute(declaration, scope)
        elif isinstance(node, c_ast.Decl) and isinstance(node.type, c_ast.ArrayDecl):
            count = self.expression(node.type.dim, scope)
            scope[node.name] = ([dict(id=0, name=string('')) for _ in range(count)]
                                if node.type.type.type.names == ['MoonlightApplication'] else [0] * count)
        elif isinstance(node, c_ast.Decl) and not node.init and isinstance(node.type, c_ast.TypeDecl) and node.type.type.names == ['MoonlightHost']:
            scope[node.name] = self.host('', '')
        elif isinstance(node, (c_ast.For, c_ast.While)):
            if isinstance(node, c_ast.For): self.execute(node.init, scope)
            steps = 0
            while node.cond is None or self.expression(node.cond, scope):
                steps += 1
                self.assertLess(steps, 4096)
                try: self.execute(node.stmt, scope)
                except runtime.BreakSwitch: break
                if isinstance(node, c_ast.For): self.execute(node.next, scope)
        else: self.original_execute(node, scope)

    def invoke(self, name, *args):
        if name == 'Connected' and args and isinstance(args[0], list):
            args = (self.host(text(args[0]), 'uuid-' + text(args[0])),)
        if name == 'make_frame_xml' and len(args) == 4:
            args += (string('7063'), args[2] if args[2] < 7 else 0)
        if name == 'make_frame_xml' and len(args) == 6:
            args += (False,)
        node = self.functions[name]
        scope = dict(self.state, NULL=0, true=1, false=0, SCE_SYSMODULE_LIVEAREA=35,
                     SCE_SYSMODULE_LOADED=0, MOONLIGHT_EVENT_CONNECTION_READY=1,
                     MOONLIGHT_EVENT_APPLICATIONS_READY=2,
                     INT_MAX=2147483647, strncmp=lambda a, b, n: int(text(a)[:n] != text(b)[:n]),
                     sceSysmoduleIsLoaded=lambda module: self.call('is_loaded', 0 if self.loaded else -1),
                     sceSysmoduleLoadModule=lambda module: self.call('load', self.load_result),
                     sceLiveAreaGetStatus=lambda: self.call('status', self.status),
                     sceLiveAreaUpdateFrameAsync=self.submit,
                     vita_debug_log=lambda *args: None, snprintf=self.snprintf,
                     memset=self.zero, strncpy=self.copy,
                     selected_host=self.host, get_apps=self.get_apps)
        def resolve_host(selected, destination):
            scope[destination] = copy.deepcopy(selected)
            return 1
        scope['resolve_host'] = resolve_host
        parameters = node.decl.type.args.params if node.decl.type.args else []
        scope.update(zip((param.name for param in parameters), args))
        for helper in self.functions:
            scope[helper] = lambda *args, helper=helper: self.invoke(helper, *(
                scope[arg] if isinstance(arg, str) and arg in scope else arg for arg in args))
        with patch.object(runtime, 'expression', self.expression), patch.object(runtime, 'execute', self.execute):
            try: return run(node.body, scope)
            finally:
                if name in ('Connected', 'Applications', 'Poll', 'Shutdown'):
                    self.state.update({key: scope[key] for key in self.state})

    def call(self, name, result):
        self.calls.append(name)
        return result

    @staticmethod
    def zero(out, value, size):
        if isinstance(out, dict):
            for key in out:
                if isinstance(out[key], list): LiveArea.zero(out[key], value, len(out[key]))
                else: out[key] = 0
            return
        for i in range(len(out)):
            if isinstance(out[i], list): LiveArea.zero(out[i], value, len(out[i]))
            else: out[i] = 0

    @staticmethod
    def copy(out, source, count):
        for i in range(count): out[i] = source[i]

    @staticmethod
    def snprintf(out, capacity, fmt, *args):
        raw = (fmt % tuple(text(arg) if isinstance(arg, list) else arg for arg in args)).encode()
        if capacity:
            written = raw[:capacity - 1] + b'\0'
            out[:len(written)] = written
        return len(raw)

    def submit(self, version, xml, length, path, flags):
        self.assertEqual((version, path, flags), ('01.00', 'app0:sce_sys/livearea/contents', 0))
        self.assertEqual(len(text(xml).encode()), length)
        self.sent.append(ET.fromstring(text(xml)))
        return self.call('submit', self.submit_result)

    def get_apps(self, out, capacity):
        self.calls.append('cache')
        self.assertEqual(capacity, 6)
        result = min(len(self.cache), capacity) if self.cache_result is None else self.cache_result
        if result >= 0: out[:result] = self.cache[:result]
        return result

    def drain(self):
        for _ in range(40):
            if not self.state['m_dirty'] and self.state['m_pending_frame'] < 0: return
            self.invoke('Poll', True)
        self.fail('Publication failed to drain')

    def test_xml_escaping_unicode_invalid_bytes_bounds_and_populated_frames(self):
        for frame in range(1, 8):
            for label in ('ПК & <Game> "one" \'two\'', 'A' * 255, '"' * 255, '',
                          b'bad\x01\xc0\x80\xed\xa0\x80\xef\xbf\xbe\xf4\x90\x80\x80',
                          b'a' * 254 + b'\xe2'):
                with self.subTest(frame=frame, label=label):
                    out = [0] * 3072
                    length = self.invoke('make_frame_xml', out, len(out), frame, string(label))
                    self.assertGreater(length, 0)
                    root = ET.fromstring(text(out))
                    self.assertEqual(root.attrib['id'], f'frame{frame}')
                    self.assertEqual(root.find('liveitem/text').attrib['origin'], 'background' if label else 'frame')
                    if label:
                        background = root.find('liveitem/background')
                        self.assertEqual(background.text, 'pc_card.png' if frame == 7 else 'app_row.png')
                        self.assertEqual(background.attrib['width'], '280' if frame == 7 else '472')
                        self.assertEqual(root.find('liveitem/text').attrib['text-align'], 'center' if frame == 7 else 'left')
                        if frame == 7:
                            self.assertEqual(root.find('liveitem/image').text, 'pc.png')
                        else:
                            self.assertEqual(root.find('liveitem/image').text, 'app.png')
                            self.assertEqual(root.find('liveitem/image').attrib,
                                             dict(origin='background', width='32', height='32', x='-210', align='center', valign='center'))
                            self.assertEqual(root.find('liveitem/text').attrib['margin-left'], '50')
                    else:
                        for tag in ('background', 'image', 'target'):
                            self.assertIsNone(root.find('liveitem/' + tag))
                    if isinstance(label, str): self.assertEqual(root.find('liveitem/text/str').text or '', label)
        self.assertEqual(self.invoke('make_frame_xml', [0] * 8, 8, 7, string('PC')), -1)
        self.assertEqual(self.invoke('make_frame_xml', [0] * 2048, 2048, 8, string('PC')), -1)

    def test_installation_defaults_use_native_welcome_and_package_dynamic_assets(self):
        contents = ROOT / 'sce_sys/livearea/contents'
        template = ET.parse(contents / 'template.xml')
        for index in range(1, 8):
            with self.subTest(frame=index):
                item = template.find(f"frame[@id='frame{index}']/liveitem")
                self.assertIsNone(item.find('background'))
                self.assertIsNotNone(item.find('text'))
                self.assertEqual(item.find('text/str').text or '',
                                 {2: 'Moonlight', 3: 'Open source game streaming client'}.get(index, ''))
                self.assertEqual(item.find('text').attrib['origin'], 'frame')
                self.assertIsNone(item.find('image'))
                self.assertIsNone(item.find('target'))
                out = [0] * 3072
                self.invoke('make_frame_xml', out, len(out), index, string(''), string('7063'), 0, True)
                dynamic = ET.fromstring(text(out)).find('liveitem')
                self.assertEqual(item.find('text').attrib, dynamic.find('text').attrib)
                self.assertEqual(item.find('text/str').attrib, dynamic.find('text/str').attrib)
                self.assertEqual(item.find('text/str').text, dynamic.find('text/str').text)
        cmake = (ROOT / 'CMakeLists.txt').read_text()
        sources = {target: ROOT / source for source, target in re.findall(
            r'FILE\s+\$\{CMAKE_CURRENT_SOURCE_DIR\}/(\S+)\s+(\S+)', cmake)}
        self.assertNotRegex(cmake, r'frame[1-7]\.png')
        for resource in template.findall('.//image') + template.findall('.//startup-image'):
            self.assertTrue(sources[f'sce_sys/livearea/contents/{resource.text}'].is_file())
        for name, width, height in (('app_row.png', 472, 48), ('pc_card.png', 280, 158), ('pc.png', 80, 80), ('app.png', 128, 128), ('startup.png', 280, 158)):
            data = sources[f'sce_sys/livearea/contents/{name}'].read_bytes()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual((int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')), (width, height))
            self.assertEqual(data[24:26], bytes((8, 3)), name)  # Vita installation requires indexed PNG.
            if name != 'app.png': self.assertIn(b'tRNS', data)
        self.assertEqual(sources['sce_sys/livearea/contents/app.png'], ROOT / 'sce_sys/icon0.png')

    def test_owned_snapshot_first_six_shorter_empty_and_host_switch(self):
        self.invoke('Connected', string('PC A'))
        apps = [dict(id=i, name=string(f'Game {i}')) for i in range(6)]
        self.invoke('Applications', apps, 6)
        apps[0]['name'] = string('changed after capture')
        self.drain()
        self.assertEqual([root.attrib['id'] for root in self.sent], [f'frame{i}' for i in range(1, 8)])
        self.assertEqual(self.sent[0].find('liveitem/text/str').text, 'Game 0')
        self.assertEqual(self.sent[6].find('liveitem/text/str').text, 'PC A')
        for count in (2, 0):
            self.invoke('Applications', apps, count)
            self.drain()
            for index, root in enumerate(self.sent[-7:-1], 1):
                if index <= count: continue
                self.assertEqual(root.find('liveitem/text/str').text or '',
                                 {2: 'Moonlight', 3: 'Open source game streaming client'}.get(index, '') if count == 0 else '')
                for tag in ('background', 'image', 'target'):
                    self.assertIsNone(root.find('liveitem/' + tag))
        self.invoke('Connected', string('PC B'))
        self.drain()
        self.assertTrue(all(not text(label) for label in self.state['m_labels'][:6]))
        self.assertEqual(text(self.state['m_labels'][6]), 'PC B')

    def test_welcome_apps_empty_transition_preserves_pc_card_and_active_rows(self):
        self.invoke('Poll', True)
        self.assertEqual(self.sent, [])  # Opening Moonlight preserves the Shell snapshot.
        self.invoke('Connected', self.host())
        for apps in ([], [dict(id=42, name=string('Game')), dict(id=43, name=string(''))], []):
            self.invoke('Applications', apps, len(apps))
            self.drain()
            rows = self.sent[-7:]
            self.assertEqual(rows[6].find('liveitem/image').text, 'pc.png')
            self.assertEqual(rows[6].find('liveitem/background').attrib,
                             dict(width='280', height='158', align='center', valign='top'))
            self.assertIsNotNone(rows[6].find('liveitem/target'))
            if apps:
                self.assertEqual(rows[0].find('liveitem/text/str').text, 'Game')
                self.assertIsNotNone(rows[0].find('liveitem/background'))
                self.assertIsNotNone(rows[0].find('liveitem/target'))
                self.assertIsNone(rows[1].find('liveitem/target'))  # Empty name, despite valid ID.
                self.assertFalse(any(row.find('liveitem/text/str').text for row in rows[1:6]))
            else:
                self.assertEqual(rows[1].find('liveitem/text/str').text, 'Moonlight')
                self.assertEqual(rows[2].find('liveitem/text/str').text, 'Open source game streaming client')
                self.assertFalse(any(row.find('liveitem/target') is not None for row in rows[:6]))

    def test_busy_pending_and_new_snapshot_never_overlap_or_lose_a_dirty_slot(self):
        self.invoke('Connected', string('PC A'))
        self.invoke('Poll', False)
        self.assertEqual(self.calls, [])
        self.invoke('Poll', True)
        self.status = 1
        self.invoke('Connected', string('PC B'))
        self.invoke('Poll', False)
        self.invoke('Poll', True)
        self.assertEqual(self.calls.count('submit'), 1)
        self.status = 0
        self.invoke('Poll', False)
        self.assertEqual(self.state['m_dirty'], 0x7f)
        self.drain()
        self.assertEqual(self.calls.count('load'), 1)
        self.assertEqual([root.attrib['id'] for root in self.sent[:2]], ['frame1', 'frame1'])
        self.assertEqual(self.sent[-1].find('liveitem/text/str').text, 'PC B')

    def test_older_failure_does_not_discard_new_snapshot(self):
        self.invoke('Connected', string('PC A'))
        self.invoke('Poll', True)
        self.invoke('Connected', string('PC B'))
        self.status = -9
        self.invoke('Poll', True)
        self.assertEqual(self.state['m_dirty'], 0x7f)
        self.status = 0
        self.drain()
        self.assertEqual(self.sent[-1].find('liveitem/text/str').text, 'PC B')

    def test_module_submission_completion_failure_and_shutdown_do_not_spin(self):
        for failure in ('load', 'submit', 'status'):
            with self.subTest(failure=failure):
                self.setUp()
                setattr(self, {'load': 'load_result', 'submit': 'submit_result', 'status': 'status'}[failure], -9)
                self.invoke('Connected', string('PC'))
                self.invoke('Poll', True)
                self.invoke('Poll', True)
                calls = list(self.calls)
                for _ in range(10): self.invoke('Poll', True)
                self.assertEqual(self.calls, calls)
        self.setUp()
        self.loaded = True
        self.invoke('Connected', string('PC'))
        self.invoke('Poll', True)
        self.invoke('Shutdown')
        self.invoke('Poll', False)
        self.assertEqual(self.calls, ['is_loaded', 'submit', 'status'])

    def test_completion_capture_uses_first_six_cached_apps_and_ignores_failures(self):
        self.invoke('UpdateLiveArea', dict(type=1, result=-1))
        self.assertFalse(self.state['m_has_host'])
        self.invoke('UpdateLiveArea', dict(type=1, result=0))
        self.assertEqual(text(self.state['m_labels'][6]), 'PC B')
        self.cache = [dict(id=i, name=string(f'App {i}')) for i in range(12)]
        self.invoke('UpdateLiveArea', dict(type=2, result=12))
        self.assertEqual([text(label) for label in self.state['m_labels'][:6]], [f'App {i}' for i in range(6)])
        self.calls.clear()
        self.invoke('UpdateLiveArea', dict(type=2, result=0))
        self.assertNotIn('cache', self.calls)  # GetAll(NULL, 0) would start networking.
        self.assertTrue(all(not text(label) for label in self.state['m_labels'][:6]))
        self.cache_result = -9
        self.invoke('UpdateLiveArea', dict(type=2, result=3))
        self.assertTrue(all(not text(label) for label in self.state['m_labels'][:6]))

    def test_binding_build_and_native_only_boundary(self):
        binding = (ROOT / 'include/platform/livearea.h').read_text()
        self.assertIn('int32_t frame_xml_length', binding)
        self.assertIn('uint32_t flags', binding)
        cmake = (ROOT / 'CMakeLists.txt').read_text()
        self.assertIn('src/services/livearea_service.cpp', cmake)
        self.assertIn('  SceLiveArea_stub\n', cmake)
        self.assertNotIn('ScePromoterUtil', cmake)
        for forbidden in ('fopen(', 'sceIo', 'appmeta', 'app.db', 'sceSysmoduleUnloadModule', 'sceKernelDelayThread'):
            self.assertNotIn(forbidden, self.source)

    def test_targets_round_trip_host_identity_and_app_id_without_slot_indices(self):
        host = self.host('Same display name', 'server-123')
        self.invoke('Connected', host)
        self.invoke('Applications', [dict(id=438, name=string('Game'))], 1)
        self.drain()
        for frame, expected in ((0, 438), (6, 0)):
            target = self.sent[frame].find('liveitem/target').text
            identity, app_id = self.host('', ''), [-1]
            self.assertEqual(self.invoke('ParseTarget', string(target.removeprefix('psla:')), identity, app_id), 1)
            self.assertEqual(text(identity['host_id']), 'server-123')
            self.assertEqual(app_id, [expected])
        self.assertTrue(all(root.find('liveitem/target') is None for root in self.sent[1:6]))
        self.invoke('Connected', self.host('Unsaved', ''))
        self.drain()
        self.assertTrue(all(root.find('liveitem/target') is None for root in self.sent[-7:]))

    def test_target_parser_rejects_malformed_versions_ids_overflow_and_injection(self):
        for parameter in ('eboot', 'psla:moonlight1/7063/1', 'moonlight2/7063/1',
                          'moonlight1//1', 'moonlight1/0/1', 'moonlight1/gg/1', 'moonlight1/00/1',
                          'moonlight1/' + '61' * 33 + '/1', 'moonlight1/7063/',
                          'moonlight1/7063/-1', 'moonlight1/7063/+1', 'moonlight1/7063/01',
                          'moonlight1/7063/2147483648', 'moonlight1/7063/42&quit=1',
                          'moonlight1/7063/42/trailing', 'moonlight1/7063/ 42'):
            with self.subTest(parameter=parameter):
                self.assertEqual(self.invoke('ParseTarget', string(parameter), self.host('', ''), [0]), 0)
        app_id = [-1]
        self.assertEqual(self.invoke('ParseTarget', string('moonlight1/7063/2147483647'), self.host('', ''), app_id), 1)
        self.assertEqual(app_id, [2147483647])


if __name__ == '__main__':
    unittest.main()
