"""Interpret artwork bounds/ownership with serial mocks; no native decode, TLS or build."""
import ast
import re
import struct
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from pycparser import c_ast, c_parser
import test_adapter_lifecycle as runtime
from test_host_lists import function
from test_pairing_errors import Harness, Memory, Ref
from test_xml_source import ROOT, strip_directives


class Artwork(unittest.TestCase):
    def test_artwork_resources_use_public_paf_accessors(self):
        # Source regression gate only: native compilation remains a maintainer check.
        source = (ROOT / 'src/services/application_service.cpp').read_text()
        self.assertIn('pool(paf::gutil::GetDefaultSurfacePool())', source)
        self.assertIn('heap(paf::memory::GetGlobalHeapAllocator())', source)
        self.assertNotRegex(source, r'Framework::Instance\(\)->(?:surface_pool|decode_heap)')

    def test_session_admission_app_identity_and_late_cancellation_fail_closed(self):
        source = function((ROOT / 'src/moonlight/api.cpp').read_text(),
                          'moonlight_api_get_application_artwork')
        source = source.replace('HostControlRequest request(false);', 'int request = admitted;')
        source = source.replace('request.Acquired()', 'request')
        source = source.replace('for (int i = 0;', 'int i; for (i = 0;').replace('++i', 'i = i + 1')
        preamble = '''typedef int MoonlightCancellation, bool; typedef unsigned int size_t;
        typedef struct {int id;} Application;'''
        body = c_parser.CParser().parse(preamble + strip_directives(source)).ext[-1].body
        for failure in ('none', 'admission', 'unpaired', 'cache', 'unknown_id',
                        'disconnect', 'stream', 'transfer', 'late_cancel'):
            with self.subTest(failure=failure):
                h = Harness()
                out = dict(body=888, length=999)
                cancelled, calls = [False], []
                payload = Memory(4)
                def fetch(server, app_id, cancel, output, length):
                    calls.append(app_id)
                    output.set(payload)
                    length.set(4)
                    cancelled[0] = failure == 'late_cancel'
                    return -1 if failure == 'transfer' else 0
                values = dict(h.values, body=Ref(out, 'body'), length=Ref(out, 'length'),
                              application_id=99 if failure == 'unknown_id' else 7,
                              admitted=failure != 'admission', cancel=0, s_server=1,
                              s_has_current_host=1, s_game_stream_initialized=1,
                              s_applications_valid=failure != 'cache', s_stream_pending=0,
                              s_connection_state=0 if failure == 'unpaired' else 2,
                              MOONLIGHT_CONNECTION_PAIRED=2, s_application_count=1,
                              s_applications=[dict(id=7)],
                              disconnect_pending=lambda: failure == 'disconnect',
                              moonlight_stream_is_running=lambda: failure == 'stream',
                              moonlight_is_cancelled=lambda token: cancelled[0],
                              legacy_gamestream_get_artwork=fetch)
                result = h.run(body, values)
                self.assertEqual(result, 0 if failure == 'none' else -1)
                self.assertEqual(out['length'], 4 if failure == 'none' else 0)
                if failure != 'none': self.assertEqual(out['body'], 0)
                self.assertEqual(calls, [7] if failure in ('none', 'transfer', 'late_cancel') else [])
                if failure in ('transfer', 'late_cancel'):
                    self.assertIn(('free', payload), h.calls)

    def test_chunk_limit_and_size_t_overflow_reject_before_allocating(self):
        h = Harness()
        allocated = []
        class BufferMemory(Memory):
            def __add__(self, offset):
                return self  # memcpy is mocked; only buffer size/ownership are interpreted.
        h.values['realloc'] = lambda ptr, count: allocated.append(count) or BufferMemory(count)
        original_execute = h.execute
        def execute(node, values):
            if isinstance(node, c_ast.Assignment) and node.op == '+=':
                target = h.expression(node.lvalue.name, values)
                target[node.lvalue.field.name] += h.expression(node.rvalue, values)
            else:
                original_execute(node, values)
        h.execute = execute
        buffer = dict(memory=Memory(1), size=0, allocation_failed=0, limit=512 * 1024)
        self.assertEqual(h.invoke('http_write_callback', 1, 1, 512 * 1024, buffer), 512 * 1024)
        self.assertEqual(len(allocated), 1)
        for size, count, current in ((1, 1, 512 * 1024), (0xffffffff, 2, 0),
                                      (1, 2, 0xfffffffe), (1, 1, 0xffffffff)):
            buffer['size'] = current
            self.assertEqual(h.invoke('http_write_callback', 1, size, count, buffer), 0)
        self.assertEqual(len(allocated), 1)
        self.assertEqual(buffer['allocation_failed'], 0)  # Size rejection is not allocation failure.

    def test_limit_survives_http_response_reset_and_does_not_change_xml_policy(self):
        for limit in (0, 512 * 1024):
            h = Harness()
            buffer = dict(memory=Memory(1), size=0, allocation_failed=1, limit=limit)
            h.values['http_write_callback'] = 1
            h.values['curl_easy_perform'] = lambda *args: self.assertEqual(buffer['limit'], limit) or 0
            self.assertEqual(h.invoke('http_request', dict(curl=1, server_certificate=12),
                                     'https://host/appasset', buffer, 5, 0), 0)
            self.assertEqual(buffer['limit'], limit)
            self.assertEqual(buffer['allocation_failed'], 0)

    def test_png_header_and_aspect_fit_from_actual_helpers(self):
        source = (ROOT / 'include/moonlight/app_artwork.h').read_text()
        source = source[source.index('static inline int moonlight_artwork_extent'):source.index('#endif')]
        source = source.replace('static inline ', '')
        for name in ('width', 'height', 'w', 'h'):
            source = re.sub(r'(?<![\w*])\*' + name + r'\b', name + '[0]', source)
        # Restore pointer parameters after adapting output assignments to mutable arrays.
        source = source.replace('int width[0]', 'int *width').replace('int height[0]', 'int *height')
        source = source.replace('int w[0]', 'int *w').replace('int h[0]', 'int *h')
        source = source.replace('MOONLIGHT_ARTWORK_MAX_BYTES', str(512 * 1024))
        source = source.replace('MOONLIGHT_ARTWORK_THUMB_SIZE', '90')
        unit = c_parser.CParser().parse('typedef unsigned int size_t, uint32_t;' + strip_directives(source))
        functions = {n.decl.name: n for n in unit.ext if isinstance(n, c_ast.FuncDef)}
        original_expression, original_execute = runtime.expression, runtime.execute

        def expression(node, values):
            if isinstance(node, c_ast.Constant) and node.type == 'string':
                return ast.literal_eval(node.value).encode('latin1')
            if isinstance(node, c_ast.BinaryOp) and node.op in ('*', '/', '<<', '|'):
                a, b = expression(node.left, values), expression(node.right, values)
                return {'*': lambda: a * b, '/': lambda: a // b,
                        '<<': lambda: a << b, '|': lambda: a | b}[node.op]()
            return original_expression(node, values)

        def execute(node, values):
            if isinstance(node, c_ast.Assignment) and isinstance(node.lvalue, c_ast.ArrayRef):
                expression(node.lvalue.name, values)[expression(node.lvalue.subscript, values)] = expression(node.rvalue, values)
            else: original_execute(node, values)

        def invoke(name, **values):
            values['memcmp'] = lambda data, expected, count: int(bytes(data[:count]) != expected[:count])
            with patch.object(runtime, 'expression', expression), patch.object(runtime, 'execute', execute):
                try: runtime.execute(functions[name].body, values)
                except runtime.Returned as result: return result.value

        def png(w, h):
            return b'\x89PNG\r\n\x1a\n\0\0\0\rIHDR' + struct.pack('>II', w, h) + b'\x08\x06\0\0\0' + b'\0' * 4

        for data, size, expected in ((png(300, 400), 33, 1), (png(1024, 1024), 33, 1),
                                     (png(0, 20), 33, 0), (png(20, 0), 33, 0),
                                     (png(1025, 10), 33, 0), (png(1, 0xffffffff), 33, 0),
                                     (b'x' * 33, 33, 0), (png(30, 40), 32, 0),
                                     (png(30, 40), 512 * 1024 + 1, 0)):
            width, height = [-1], [-1]
            self.assertEqual(invoke('moonlight_artwork_extent', data=data, size=size,
                                    width=width, height=height), expected)
            if not expected: self.assertEqual((width[0], height[0]), (-1, -1))
        for width, height, expected in ((300, 400, (67, 90)), (600, 300, (90, 45)),
                                        (90, 90, (90, 90)), (1, 1024, (1, 90))):
            w, h = [0], [0]
            invoke('moonlight_artwork_fit', width=width, height=height, w=w, h=h)
            self.assertEqual((w[0], h[0]), expected)

    def test_cancelled_or_unfinished_job_never_publishes_artwork_and_releases_queue_surface(self):
        source = (ROOT / 'src/services/application_service.cpp').read_text()
        code = function(source, 'ApplicationService::TakeArtwork')
        code = code.replace('ApplicationService::TakeArtwork', 'take')
        code = code.replace('paf::intrusive_ptr<paf::graph::Surface> *surface', 'int *surface')
        code = code.replace('ArtworkJob *job = static_cast<ArtworkJob *>(m_artwork_job.get());', 'Job *job = get_job();')
        code = code.replace('__atomic_load_n(&job->done, __ATOMIC_ACQUIRE)', 'job->done')
        for name in ('application_id', 'surface', 'width', 'height'):
            code = code.replace('*' + name, 'out->' + name)
        code = code[code.index('{'):]
        code = code.replace('job->surface.clear()', 'job->surface = 0')
        code = code.replace('surface->clear()', 'out->surface = 0')
        code = code.replace('m_artwork_job.reset()', 'reset_job()')
        preamble = '''typedef int bool; typedef struct {int done, cancel, id, surface, width, height;} Job;
        typedef struct {int application_id, surface, width, height;} Output;
        bool take(Output *out)'''
        body = c_parser.CParser().parse(preamble + strip_directives(code)).ext[-1].body
        for done, cancelled in ((0, 0), (1, 0), (1, 1)):
            job = dict(done=done, cancel=cancelled, id=7, surface=99, width=67, height=90)
            out = dict(application_id=-1, surface=-1, width=0, height=0)
            resets = []
            values = dict(out=out, false=0, true=1, get_job=lambda: job,
                          moonlight_is_cancelled=lambda token: job[token],
                          reset_job=lambda: resets.append(job['surface']))
            with patch.object(runtime, 'expression', Harness.original_expression):
                # Model &job->cancel as its field name; no native atomics or refcounts.
                original = runtime.expression
                def expression(node, scope):
                    if isinstance(node, c_ast.UnaryOp) and node.op == '&': return node.expr.field.name
                    return original(node, scope)
                with patch.object(runtime, 'expression', expression):
                    try: runtime.execute(body, values)
                    except runtime.Returned as result: self.assertEqual(bool(result.value), bool(done))
            if done:
                self.assertEqual(out['application_id'], 0 if cancelled else 7)
                self.assertEqual(out['surface'], 0 if cancelled else 99)
                self.assertEqual(resets, [0])
            else:
                self.assertEqual(resets, [])
                self.assertEqual(out['surface'], -1)

    def test_music_row_geometry_and_fallback_use_native_list_controls(self):
        root = ET.parse(ROOT / 'cxml/vita_moonlight_ui.xml').getroot()
        row = root.find("./templatetable/template[@id='template_app_list_item']/list_item")
        self.assertEqual(row.find('layout_hint').get('size'), '730, 90')
        button = row.find('image_button')
        self.assertEqual(button.find('focus_hint').get('focus_shape'), '3')
        self.assertEqual(button.find('focus_hint').get('focus_size'), '730, 90')
        self.assertEqual(button.get('enable_long_press_text_auto_scroll'), '1')
        cover = button.find("plane[@id='plane_app_cover']/layout_hint")
        self.assertEqual((cover.get('size'), cover.get('pos')), ('90, 90', '77, 0'))
        self.assertIsNotNone(button.find("plane[@id='plane_app_fallback']"))
        style = root.find("./styletable/style_image_button[@id='style_image_button_app']")
        self.assertEqual(style.get('left_margin'), '137')  # x=115+137=252, 15 after the cover.
        self.assertEqual(style.find('textobj').get('font_size'), '32')
        for name in ('music_row', 'music_row_glow', 'application'):
            texture = root.find(f"./texturetable/texture[@id='tex_{name}']")
            self.assertEqual(texture.get('type'), 'texture/png')
        for name in ('music_row', 'music_row_glow'):
            data = (ROOT / f'cxml/texture/{name}.png').read_bytes()
            self.assertEqual(struct.unpack('>II', data[16:24]), (680, 92))


if __name__ == '__main__':
    unittest.main()
