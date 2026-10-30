"""Interpret real cache/store/API code with mocked files/time; no build or Vita I/O."""
import ast
import re
import struct
import unittest
import zlib
from pycparser import c_ast, c_parser
from test_pairing_errors import Harness, Memory, Ref
from test_xml_source import ROOT, strip_directives


def function(source, name):
    start = re.search(r'^(?:static )?(?:int|uint32_t) ' + name + r'\(', source, re.M).start()
    return source[start:source.index('\n}', start) + 2]


class Bytes(Memory):
    def __init__(self, data=b''):
        self.data = list(data)

    def __add__(self, offset):
        return Bytes(bytes(self.data[offset:]))


def png():
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\0\x10\x20\x30\xff')) + chunk(b'IEND', b''))


class ArtworkDiskCache(unittest.TestCase):
    path = 'ux0:data/moonlight/Original PC/app_7.png'

    def cache(self, failure=''):
        h = Harness()
        original_expression = h.expression
        def expression(node, values):
            if isinstance(node, c_ast.Constant) and node.type == 'char':
                return ord(ast.literal_eval(node.value))
            if isinstance(node, c_ast.BinaryOp) and node.op in ('<=', '<<', '|'):
                a, b = expression(node.left, values), expression(node.right, values)
                return {'<=': lambda: int(a <= b), '<<': lambda: a << b, '|': lambda: a | b}[node.op]()
            return original_expression(node, values)
        h.expression = expression
        store = (ROOT / 'src/backend/legacy_device_store.cpp').read_text()
        source = '\n'.join(function(store, name) for name in (
            'artwork_path', 'artwork_u32', 'artwork_png_valid',
            'legacy_device_store_read_artwork', 'legacy_device_store_write_artwork'))
        source += '\n' + function((ROOT / 'include/moonlight/app_artwork.h').read_text().replace('static inline ', ''),
                                  'moonlight_artwork_extent')
        types = '''typedef unsigned int size_t, uint32_t; typedef long time_t; typedef int FILE;
        typedef struct {char host_id[33], storage_name[256], name[256]; int paired;} MoonlightHost, device_info_t;
        struct stat {long st_size, st_mtime;};'''
        unit = c_parser.CParser().parse(strip_directives(types + source))
        h.functions = {n.decl.name: n for n in unit.ext if isinstance(n, c_ast.FuncDef)}
        h.files, h.io = {}, []
        h.record = dict(host_id=Bytes(b'uuid\0'), storage_name=Bytes(b'Original PC\0'),
                        name=Bytes(b'Renamed PC\0'), paired=1)
        def text(value): return value.text() if isinstance(value, Memory) else value
        def snprintf(out, size, fmt, *args):
            value = fmt % tuple(text(v) for v in args)
            out.write(value[:max(0, size - 1)])
            return len(value)
        def stat(path, info):
            key = text(path)
            if key not in h.files: return -1
            size = len(h.files[key])
            if failure == 'oversize': size = 512 * 1024 + 1
            if failure == 'short': size += 1
            if failure == 'extra': size -= 1
            info.set(dict(st_size=size, st_mtime=100000 - 86400 if failure == 'expired'
                          else 100001 if failure == 'future' else 99999))
            return 0
        def fopen(path, mode):
            key = text(path); h.io.append(('open', key, mode))
            if failure == 'open': return 0
            if mode == 'wb': h.files[key] = b''
            if key not in h.files: return 0
            return dict(key=key, mode=mode, pos=0)
        def fread(data, one, count, file):
            payload = h.files[file['key']][:count]
            data.data[:len(payload)] = payload
            file['pos'] = len(payload)
            return len(payload)
        def fgetc(file):
            return -1 if file['pos'] == len(h.files[file['key']]) else 0
        def fwrite(data, one, count, file):
            count = count - 1 if failure == 'write' else count
            h.files[file['key']] = bytes(data.data[:count])
            return count
        def remove(path):
            key = text(path); h.io.append(('remove', key)); h.files.pop(key, None); return 0
        def rename(src, dst):
            src, dst = text(src), text(dst); h.io.append(('rename', src, dst))
            if failure == 'rename': return -1
            h.files[dst] = h.files.pop(src); return 0
        def memcmp(a, b, count):
            a = bytes(a.data[:count]) if isinstance(a, Memory) else a.encode('latin1')[:count]
            b = bytes(b.data[:count]) if isinstance(b, Memory) else b.encode('latin1')[:count]
            return int(a != b)
        h.values.update(s_initialized=1, config=dict(key_dir='ux0:data/moonlight/'),
            MOONLIGHT_ARTWORK_MAX_BYTES=512 * 1024, EOF=-1,
            find_device_by_host_id=lambda uuid: h.record if uuid.text() == h.record['host_id'].text() else 0,
            device_storage_name_valid=lambda name: bool(name.text()) and '/' not in name.text(),
            snprintf=snprintf, stat=stat, time=lambda unused: -1 if failure == 'clock' else 100000,
            fopen=fopen, fread=fread, fgetc=fgetc, ferror=lambda file: failure == 'read',
            fclose=lambda file: h.io.append(('close', file['key'])) or (-1 if failure == 'close' else 0),
            fwrite=fwrite, fflush=lambda file: -1 if failure == 'flush' else 0,
            remove=remove, rename=rename, malloc=lambda size: 0 if failure == 'malloc' else Bytes(bytes(size)),
            memcmp=memcmp, crc32=lambda seed, data, count: zlib.crc32(bytes(data.data[:count]), seed),
            vita_debug_log=lambda *args: None)
        for name in h.functions:
            h.values[name] = lambda *args, name=name: h.invoke(name, *args)
        return h

    def test_png_complete_chunks_and_crc_are_required(self):
        h = self.cache(); valid = png()
        self.assertEqual(h.invoke('artwork_png_valid', Bytes(valid), len(valid)), 1)
        corrupt = bytearray(valid); corrupt[45] ^= 1
        for data in (b'', valid[:33], valid[:-1], valid + b'extra', bytes(corrupt),
                     valid[:33] + b'\xff\xff\xff\xff' + valid[37:], bytes(512 * 1024 + 1)):
            with self.subTest(length=len(data)):
                self.assertEqual(h.invoke('artwork_png_valid', Bytes(data), len(data)), 0)

    def test_path_uses_saved_uuid_and_storage_name_not_display_name(self):
        h = self.cache(); host = dict(host_id=Bytes(b'uuid\0')); out = Memory(512)
        self.assertEqual(h.invoke('artwork_path', host, 7, out, 512), 0)
        self.assertEqual(out.text(), self.path)
        for uuid, paired, storage, app_id, size in ((b'other\0', 1, b'Original PC\0', 7, 512),
                (b'\0', 1, b'Original PC\0', 7, 512), (b'uuid\0', 0, b'Original PC\0', 7, 512),
                (b'uuid\0', 1, b'../client\0', 7, 512), (b'uuid\0', 1, b'Original PC\0', 0, 512),
                (b'uuid\0', 1, b'Original PC\0', 7, 8)):
            h.record['paired'] = paired; h.record['storage_name'] = Bytes(storage)
            self.assertEqual(h.invoke('artwork_path', dict(host_id=Bytes(uuid)), app_id, out, size), -1)

    def test_read_hits_only_complete_fresh_bounded_files(self):
        for failure in ('', 'missing', 'expired', 'future', 'clock', 'oversize', 'open',
                        'short', 'extra', 'read', 'close', 'malloc', 'crc'):
            with self.subTest(failure=failure):
                h = self.cache(failure); payload = png()
                if failure == 'crc': payload = payload[:-1] + b'\0'
                if failure != 'missing': h.files[self.path] = payload
                out = dict(body=9, length=99)
                result = h.invoke('legacy_device_store_read_artwork', dict(host_id=Bytes(b'uuid\0')), 7,
                                  Ref(out, 'body'), Ref(out, 'length'))
                self.assertEqual(result, 0 if not failure else -1)
                if failure: self.assertEqual(out, dict(body=0, length=0))
                else: self.assertEqual((bytes(out['body'].data), out['length']), (payload, len(payload)))
                if failure in ('missing', 'expired', 'future', 'clock', 'oversize'):
                    self.assertFalse(h.io)

    def test_write_publishes_only_after_successful_write_flush_close(self):
        for failure in ('', 'open', 'write', 'flush', 'close', 'rename', 'crc'):
            with self.subTest(failure=failure):
                h = self.cache(failure); payload = png()
                h.files[self.path] = b'old'
                if failure == 'crc': payload = payload[:-1]
                result = h.invoke('legacy_device_store_write_artwork', dict(host_id=Bytes(b'uuid\0')),
                                  7, Bytes(payload), len(payload))
                self.assertEqual(result, 0 if not failure else -1)
                self.assertNotIn(self.path + '.tmp', h.files)
                if not failure: self.assertEqual(h.files[self.path], payload)
                elif failure != 'rename': self.assertEqual(h.files[self.path], b'old')
                if failure in ('open', 'write', 'flush', 'close', 'crc'):
                    self.assertFalse(any(call[0] == 'rename' for call in h.io))
                if not failure:
                    self.assertLess(h.io.index(('close', self.path + '.tmp')),
                                    h.io.index(('rename', self.path + '.tmp', self.path)))

    def test_api_uses_disk_before_network_and_cache_write_failure_is_optional(self):
        source = function((ROOT / 'src/moonlight/api.cpp').read_text(), 'moonlight_api_get_application_artwork')
        source = source.replace('HostControlRequest request(false);', 'int request = 1;').replace('request.Acquired()', 'request')
        source = source.replace('for (int i = 0;', 'int i; for (i = 0;').replace('++i', 'i = i + 1')
        unit = c_parser.CParser().parse('typedef int bool, MoonlightCancellation; typedef unsigned int size_t;' + strip_directives(source))
        body = unit.ext[-1].body
        for hit, cancelled in ((True, False), (False, False), (True, True), (False, True)):
            h = Harness(); calls = []; out = dict(body=0, length=0); stopped = [False]
            def read(host, app, output, size):
                calls.append('read')
                if hit:
                    output.set(Bytes(png())); size.set(len(png())); stopped[0] = cancelled
                return 0 if hit else -1
            def fetch(server, app, token, output, size):
                calls.append('fetch'); output.set(Bytes(png())); size.set(len(png())); stopped[0] = cancelled; return 0
            def write(*args): calls.append('write'); return -1
            values = dict(h.values, body=Ref(out, 'body'), length=Ref(out, 'length'),
                application_id=7, cancel=0, s_current_host=1, s_server=1, s_has_current_host=1,
                s_game_stream_initialized=1, s_applications_valid=1, s_stream_pending=0,
                s_connection_state=2, MOONLIGHT_CONNECTION_PAIRED=2, s_application_count=1,
                s_applications=[dict(id=7)], disconnect_pending=lambda: False,
                moonlight_stream_is_running=lambda: False, moonlight_is_cancelled=lambda token: stopped[0],
                legacy_device_store_read_artwork=read, legacy_device_store_write_artwork=write,
                legacy_gamestream_get_artwork=fetch)
            self.assertEqual(h.run(body, values), -1 if cancelled else 0)
            self.assertEqual(calls, ['read'] if hit else ['read', 'fetch'] if cancelled else ['read', 'fetch', 'write'])
            if cancelled: self.assertEqual(out, dict(body=0, length=0))


if __name__ == '__main__':
    unittest.main()
