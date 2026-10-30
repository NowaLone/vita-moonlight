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
        self.assertNotIn('option.decode_heap =', source)  # Load selects the native decode heap.
        self.assertNotIn('Surface::DecodeImage(', source)
        self.assertNotIn('image::Image::Open(', source)
        self.assertNotRegex(source, r'Framework::Instance\(\)->(?:surface_pool|decode_heap)')

    def test_system_pool_has_headroom_for_reported_sources_and_full_thumbnail_cache(self):
        runtime_source = (ROOT / 'src/app/paf_runtime.cpp').read_text()
        capacity = int(re.search(r'fwParam.surface_pool_size = (\d+) \* 1024 \* 1024;',
                                 runtime_source).group(1)) * 1024 * 1024
        header = (ROOT / 'include/pages/page_apps.h').read_text()
        cache_count = int(re.search(r'ArtworkCacheSize = (\d+)', header).group(1))
        # Captured UI occupancy with the old 4 MiB pool, before any cover loaded.
        # Padding is a conservative arithmetic allowance, not native allocation proof.
        ui_used = 4 * 1024 * 1024 - 1223672
        cache_bytes = cache_count * 128 * 128 * 4  # 90px slots padded to 64px blocks.
        free_with_cache = capacity - ui_used - cache_bytes
        for w, h, required in ((528, 704, 1687552), (600, 800, 2195456),
                                (1024, 1024, 4259840)):
            with self.subTest(source=(w, h)):
                self.assertGreaterEqual(free_with_cache, required)

    def test_bounded_thumbnail_pixels_padding_upscale_and_invalid_storage(self):
        code = function((ROOT / 'include/moonlight/app_artwork.h').read_text().replace('static inline ', ''),
                        'moonlight_artwork_reduce')
        code = code.replace('MOONLIGHT_ARTWORK_THUMB_SIZE', '90')
        node = c_parser.CParser().parse('typedef unsigned int size_t;' + strip_directives(code)).ext[-1]
        original_expression, original_execute = runtime.expression, runtime.execute

        def expression(node, values):
            if isinstance(node, c_ast.InitList):
                return [expression(n, values) for n in node.exprs]
            if isinstance(node, c_ast.BinaryOp) and node.op in ('*', '/', '<='):
                a, b = expression(node.left, values), expression(node.right, values)
                return {'*': lambda: a * b, '/': lambda: a // b,
                        '<=': lambda: int(a <= b)}[node.op]()
            return original_expression(node, values)

        def execute(node, values):
            if isinstance(node, c_ast.DeclList):
                for decl in node.decls: execute(decl, values)
            elif isinstance(node, c_ast.UnaryOp) and node.op == '++':
                values[node.expr.name] += 1
            elif isinstance(node, c_ast.Assignment) and isinstance(node.lvalue, c_ast.ArrayRef):
                expression(node.lvalue.name, values)[expression(node.lvalue.subscript, values)] = expression(node.rvalue, values)
            else: original_execute(node, values)

        def invoke(src, sw, sh, stride, dw, dh, size=None):
            dst = [222] * (max(1, dw * dh) * 4)
            values = dict(src=src, size=len(src) if size is None else size, sw=sw, sh=sh,
                          stride=stride, dst=dst, dw=dw, dh=dh)
            with patch.object(runtime, 'expression', expression), patch.object(runtime, 'execute', execute):
                try: runtime.execute(node.body, values)
                except runtime.Returned as result: return result.value, dst

        # Two rows, non-pixel padding, distinct channels and alpha; average 2x2 blocks.
        src = [0, 10, 20, 30, 100, 110, 120, 130, 200, 210, 220, 230, 0, 0, 0, 0, 255] * 2
        result, dst = invoke(src, 4, 2, 17, 2, 1)
        self.assertEqual((result, dst), (1, [50, 60, 70, 80, 100, 105, 110, 115]))
        self.assertEqual(invoke([1, 2, 3, 4], 1, 1, 4, 3, 2), (1, [1, 2, 3, 4] * 6))
        self.assertEqual(invoke(src, 4, 2, 17, 4, 2)[1], src[:16] + src[17:33])
        for sw, sh, stride, dw, dh, size in ((0, 2, 17, 2, 1, 34),
                (4, 0, 17, 2, 1, 34), (1025, 1, 4100, 1, 1, 4100),
                (4, 2, 15, 2, 1, 34), (4, 2, 2147483647, 2, 1, 34),
                (4, 2, 17, 0, 1, 34),
                (4, 2, 17, 91, 1, 34), (4, 2, 17, 2, 91, 34),
                (4, 2, 17, 2, 1, 32)):
            result, dst = invoke(src, sw, sh, stride, dw, dh, size)
            self.assertEqual(result, 0)
            self.assertTrue(all(value == 222 for value in dst))

    def test_loader_failures_cancellation_and_release_before_thumbnail_copy(self):
        source = (ROOT / 'src/services/application_service.cpp').read_text()
        source = source[source.index('class ApplicationService::ArtworkJob'):]
        code = source[source.index('        char *body = NULL;'):source.index('        __atomic_store_n')]
        replacements = {
            'paf::graph::Surface::LoadOption option;': 'Option option = make_option();',
            'paf::intrusive_ptr<paf::graph::Surface> source': 'int source',
            'paf::graph::Surface::Load(': 'load_source(',
            'new paf::graph::Surface(': 'new_thumbnail(',
            'surface.get()': 'surface', 'source.get()': 'source',
            'source.clear()': 'release_source(source)',
            'surface.clear()': 'surface = 0',
            'backend.GetApplicationArtwork(': 'fetch(',
            'pool->GetFreeSize()': 'free_size()',
            'source->GetWidth()': 'sw', 'source->GetHeight()': 'sh',
            'source->GetRawTexture()': 'source',
            'sceGxmTextureGetFormat(source)': 'format',
            'source->Lock()': 'lock_source()',
            'source->GetPageSize()': 'page_size', 'source->GetStride()': 'stride',
            'source->Unlock()': 'unlock_source()',
            'surface->GetPagePtr(0)': 'texture_data',
            'surface->Copy(': 'copy_thumbnail(',
            'surface->GetWidth()': 'width', 'surface->GetHeight()': 'height',
            '&cancel': 'cancel', '&body': 'body', '&length': 'length',
            '&w': 'w', '&h': 'h', '&option': 'option',
        }
        for before, after in replacements.items(): code = code.replace(before, after)
        types = 'typedef int SceInt64, ImageMode, uint32_t, bool; typedef unsigned int size_t;'
        types += 'typedef struct {int image_order, error;} Option;'
        node = c_parser.CParser().parse(types + 'void run(){' + strip_directives(code) + '}').ext[-1]
        original = runtime.expression
        def expression(node, values):
            if isinstance(node, c_ast.UnaryOp) and node.op == '~':
                return ~expression(node.expr, values)
            if isinstance(node, c_ast.BinaryOp) and node.op in ('*', '&'):
                a, b = expression(node.left, values), expression(node.right, values)
                return a * b if node.op == '*' else a & b
            return original(node, values)

        for failure in ('none', 'bgra', 'strided', 'fetch', 'cancel_before', 'pool', 'load', 'cancel_load',
                        'dimensions', 'layout', 'format', 'malloc', 'lock', 'reduce',
                        'cancel_reduce', 'new', 'texture', 'copy'):
            with self.subTest(failure=failure):
                calls, cancelled = [], [failure == 'cancel_before']
                def load(*args):
                    calls.append('load')
                    if failure == 'cancel_load': cancelled[0] = True
                    return 0 if failure == 'load' else 1
                def reduce(*args):
                    calls.append('reduce')
                    if failure == 'cancel_reduce': cancelled[0] = True
                    return failure not in ('lock', 'reduce')
                values = dict(NULL=0, false=0, cancel=0, id=7, pool=1,
                    surface=0, width=67, height=90, sw=0 if failure == 'dimensions' else 528,
                    sh=704, page_size=528 * 704 * 4, stride=528 * 4,
                    format=9 if failure == 'format' else 2 if failure == 'bgra' else 1,
                    texture_data=failure != 'texture',
                    ImageMode_RGBA8888=1, ImageMode_BGRA8888=2, ImageOrder_Linear=1,
                    SCE_GXM_TEXTURE_LINEAR=1, SCE_GXM_TEXTURE_LINEAR_STRIDED=3,
                    SCE_GXM_TEXTURE_FORMAT_A8B8G8R8=1,
                    SCE_GXM_TEXTURE_FORMAT_A8R8G8B8=2,
                    fetch=lambda *args: -1 if failure == 'fetch' else 0,
                    moonlight_artwork_extent=lambda *args: 1,
                    moonlight_artwork_fit=lambda *args: None,
                    moonlight_is_cancelled=lambda *args: cancelled[0],
                    make_option=lambda: dict(image_order=0, error=0),
                    free_size=lambda: 0 if failure == 'pool' else 4 * 1024 * 1024,
                    load_source=load,
                    sceGxmTextureGetType=lambda source: 9 if failure == 'layout' else 3 if failure == 'strided' else 1,
                    malloc=lambda *args: 0 if failure == 'malloc' else 2,
                    lock_source=lambda: calls.append('lock') or (failure != 'lock'),
                    unlock_source=lambda: calls.append('unlock'),
                    moonlight_artwork_reduce=reduce,
                    release_source=lambda source: calls.append('release'),
                    new_thumbnail=lambda *args: calls.append('new') or (failure != 'new'),
                    copy_thumbnail=lambda *args: calls.append('copy') or (-1 if failure == 'copy' else 0),
                    free=lambda *args: calls.append('free'), vita_debug_log=lambda *args: None)
                # Fetch/header output writes are mocked, not native pointer/RAII behavior.
                def execute(node, scope):
                    if isinstance(node, c_ast.Decl) and node.name in ('w', 'h'):
                        scope[node.name] = 528 if node.name == 'w' else 704
                    else: original_execute(node, scope)
                original_execute = runtime.execute
                with patch.object(runtime, 'expression', expression), patch.object(runtime, 'execute', execute):
                    runtime.execute(node.body, values)
                self.assertEqual(bool(values['surface']), failure in ('none', 'bgra', 'strided'))
                if 'new' in calls: self.assertLess(calls.index('release'), calls.index('new'))
                if 'load' in calls: self.assertIn('release', calls)
                if 'lock' in calls and failure != 'lock': self.assertIn('unlock', calls)
                if failure in ('cancel_before', 'pool', 'fetch'): self.assertNotIn('load', calls)
                if failure not in ('none', 'bgra', 'strided', 'copy'): self.assertNotIn('copy', calls)

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

    def test_native_bind_failure_keeps_fallback_and_success_shows_cover_in_order(self):
        source = function((ROOT / 'src/pages/page_apps.cpp').read_text(), 'Apps::UpdateArtwork')
        source = source.replace('Apps::UpdateArtwork', 'update_artwork')
        source = source.replace('paf::ui::Widget *', 'int ')
        source = source.replace('item->FindChild(', 'find_child(item, ')
        source = source.replace('m_artwork[cached].surface.get()', 'm_artwork[cached].surface')
        source = source.replace('cover->SetTexture(', 'set_texture(cover, ')
        source = source.replace('cover->SetSize(', 'set_size(cover, ')
        source = source.replace('paf::math::v4(', 'make_size(')
        source = source.replace('cover->Show(paf::common::transition::Type_Reset)', 'show_cover(cover)')
        source = source.replace('fallback->Hide()', 'hide_fallback(fallback)')
        preamble = '''typedef struct {int id;} App;
        typedef struct {int surface, width, height;} Artwork;'''
        body = c_parser.CParser().parse(preamble + strip_directives(source)).ext[-1].body
        for bind_result, cached, plane in ((0, 0, 11), (-1, 0, 11), (0, -1, 11), (0, 0, 0)):
            with self.subTest(bind_result=bind_result, cached=cached, plane=plane):
                calls = []
                values = dict(item=1, index=0, m_app_count=1, m_apps=[dict(id=7)],
                              m_artwork=[dict(surface=99, width=67, height=90)],
                              FindArtwork=lambda app_id: cached,
                              find_child=lambda item, name: plane if name == 'plane_app_cover' else 12,
                              set_texture=lambda cover, texture: calls.append(('bind', cover, texture)) or bind_result,
                              set_size=lambda cover, size: calls.append(('size', cover, size)),
                              make_size=lambda w, h: (w, h),
                              show_cover=lambda cover: calls.append(('show', cover)),
                              hide_fallback=lambda fallback: calls.append(('hide', fallback)),
                              vita_debug_log=lambda *args: None)
                try: runtime.execute(body, values)
                except runtime.Returned: pass
                if not plane or cached < 0:
                    self.assertEqual(calls, [])
                elif bind_result < 0:
                    self.assertEqual(calls, [('bind', 11, 99)])
                else:
                    self.assertEqual(calls, [('bind', 11, 99), ('size', 11, (67, 90)),
                                             ('show', 11), ('hide', 12)])

    def test_music_row_geometry_and_fallback_use_native_list_controls(self):
        root = ET.parse(ROOT / 'cxml/vita_moonlight_ui.xml').getroot()
        row = root.find("./templatetable/template[@id='template_app_list_item']/list_item")
        self.assertEqual(row.find('layout_hint').get('size'), '730, 90')
        button = row.find('image_button')
        self.assertEqual(button.find('focus_hint').get('focus_shape'), '3')
        self.assertEqual(button.find('focus_hint').get('focus_size'), '730, 90')
        self.assertEqual(button.get('enable_long_press_text_auto_scroll'), '1')
        plane = row.find("plane[@id='plane_app_cover']")
        self.assertIsNotNone(plane)
        self.assertEqual(plane.get('texture'), 'tex_application')
        self.assertIsNone(button.find("plane[@id='plane_app_cover']"))
        cover = plane.find('layout_hint')
        self.assertEqual((cover.get('size'), cover.get('pos')), ('90, 90', '77, 0'))
        self.assertIsNotNone(row.find("plane[@id='plane_app_fallback']"))
        self.assertIsNone(button.find("plane[@id='plane_app_fallback']"))
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
