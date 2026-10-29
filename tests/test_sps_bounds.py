"""Interpret SPS/assembly boundaries with mocked h264 calls; no native parser/build."""
import re
import unittest
from unittest.mock import patch

from pycparser import c_ast, c_parser
import test_adapter_lifecycle as runtime
import test_event_queue as queue_runtime
from test_host_persistence import run
from test_host_storage_paths import extract
from test_xml_source import ROOT, strip_directives


class Memory:
    def __init__(self, data, offset=0):
        self.data = data
        self.offset = offset

    def __add__(self, offset):
        return Memory(self.data, self.offset + offset)

    def __getitem__(self, index):
        assert 0 <= self.offset + index < len(self.data), 'read past buffer'
        return self.data[self.offset + index]

    def __setitem__(self, index, value):
        assert 0 <= self.offset + index < len(self.data), 'write past buffer'
        self.data[self.offset + index] = value


class SpsBounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (ROOT / 'src/moonlight/sps.c').read_text()
        code = extract(source, 'gs_sps_fix')
        preamble = 'typedef unsigned int size_t; typedef unsigned char uint8_t; typedef int PLENTRY;'
        cls.fix = c_parser.CParser().parse(preamble + re.sub(r'//[^\n]*', '', strip_directives(code))).ext[-1].body
        video = (ROOT / 'src/moonlight/vita_video_renderer.c').read_text()
        start = video.index('    if (!decode_unit ||', video.index('static int vita_video_submit('))
        end = video.index('    memset(&au,', start)
        code = video[start:end] + 'return 0;'
        cls.assemble = c_parser.CParser().parse(preamble + 'void assemble(void) {' + code + '}').ext[-1].body

    def setUp(self):
        self.harness = queue_runtime.EventQueue()
        self.harness.base_expression, self.harness.base_execute = runtime.expression, runtime.execute
        self.calls = []
        self.stream = dict(sps=dict(vui=dict(bitstream_restriction_flag=0)))
        self.library = dict(NULL=0, GS_SPS_MAX_SIZE=128, GS_SPS_BITSTREAM_FIXUP=1,
                            GS_SPS_REMOVE_VST_FIXUP=2, GS_SPS_REMOVE_CLI_FIXUP=4, NAL_UNIT_TYPE_SPS=7,
                            initial_width=1280, initial_height=720, h264_stream=self.stream,
                            memcpy=self.copy, vita_debug_log=lambda *args: None)

    def expression(self, node, values):
        if isinstance(node, c_ast.Constant) and node.type == 'int':
            return int(node.value, 0)
        if isinstance(node, c_ast.BinaryOp) and node.op in ('&', '<='):
            a, b = self.expression(node.left, values), self.expression(node.right, values)
            return a & b if node.op == '&' else int(a <= b)
        return self.harness.expression(node, values)

    def execute(self, node, values):
        if isinstance(node, c_ast.Assignment) and node.op == '+=':
            self.harness.assign(node.lvalue, self.expression(node.lvalue, values) +
                                self.expression(node.rvalue, values), values)
        else:
            self.harness.execute(node, values)

    @staticmethod
    def copy(destination, source, count):
        for i in range(count):
            destination[i] = source[i]

    def invoke(self, body, **arguments):
        values = dict(self.library, **arguments)
        with patch.object(runtime, 'expression', self.expression), patch.object(runtime, 'execute', self.execute):
            result = run(body, values)
        return result, values

    def rewrite(self, data=b'\0\0\1\x67\x42', *, capacity=300, read=2, write=8, active=True):
        output = Memory([99] * 300)
        def reader(stream, source, count):
            self.calls.append(('read', bytes(source[i] for i in range(count))))
            return read
        def writer(stream, destination, size):
            self.calls.append(('write', size))
            for i in range(max(0, min(write, size))):
                destination[i] = 55
            return write
        entry = dict(data=Memory(list(data)), length=len(data)) if data is not None else None
        result, _ = self.invoke(self.fix, sps=entry, flags=1, out_buf=output, out_size=capacity,
                                h264_stream=self.stream if active else None,
                                read_nal_unit=reader, write_nal_unit=writer)
        return result, output.data

    def test_short_invalid_prefix_and_wrong_nal_never_enter_parser(self):
        for data in (None, b'', b'\0', b'\0\0', b'\0\0\1', b'\0\0\0\1',
                     b'\1\0\1\x67', b'\0\0\1\x65', b'\0\0\1\xe7'):
            with self.subTest(data=data):
                self.calls.clear()
                result, output = self.rewrite(data)
                self.assertEqual(result, -1)
                self.assertEqual(output, [99] * 300)
                self.assertEqual(self.calls, [])
        self.assertEqual(self.rewrite(active=False)[0], -1)

    def test_parser_writer_and_capacity_errors_leave_output_unchanged(self):
        for read, write, capacity in ((-1, 8, 300), (0, 8, 300), (2, -1, 300),
                                      (2, 0, 300), (2, 129, 300), (2, 8, 10), (2, 8, 3)):
            with self.subTest(read=read, write=write, capacity=capacity):
                self.calls.clear()
                result, output = self.rewrite(read=read, write=write, capacity=capacity)
                self.assertEqual(result, -1)
                self.assertEqual(output, [99] * 300)
                if read <= 0 or capacity <= 3:
                    self.assertFalse(any(call[0] == 'write' for call in self.calls))

    def test_success_preserves_prefix_and_fits_exact_capacity(self):
        for prefix in (b'\0\0\1', b'\0\0\0\1'):
            for written in (1, 8, 128):
                with self.subTest(prefix=prefix, written=written):
                    result, output = self.rewrite(prefix + b'\x67\x42', write=written,
                                                  capacity=len(prefix) + written)
                    self.assertEqual(result, len(prefix) + written)
                    self.assertEqual(output[:result], list(prefix) + [55] * written)
                    self.assertEqual(output[result:], [99] * (300 - result))
                    self.assertEqual(self.stream['sps']['level_idc'], 32)
                    self.assertEqual(self.stream['sps']['num_ref_frames'], 1)
                    self.assertEqual(self.stream['sps']['vui']['max_dec_frame_buffering'], 1)

    def test_assembly_rejects_bad_lengths_and_sps_errors_before_decode(self):
        for total, chunks, fixed, expected in (
                (4, [(4, 0)], 0, 0), (4, [(133, 0)], 0, 1),
                (4, [(0, 0)], 0, 1), (4, [(-1, 0)], 0, 1),
                (4, [(4, 7)], -1, 1), (4, [(4, 7), (121, 0)], 12, 1),
                (4, [(4, 7), (4, 0)], 12, 0), (0, [], 0, 1),
                (-1, [], 0, 1), (2**31 - 1, [], 0, 1)):
            with self.subTest(total=total, chunks=chunks, fixed=fixed):
                linked = None
                for size, kind in reversed(chunks):
                    linked = dict(length=size, bufferType=kind, data=Memory([42] * max(1, size)), next=linked)
                copies = []
                def copy(destination, source, size):
                    copies.append(size)
                    self.copy(destination, source, size)
                result, values = self.invoke(self.assemble,
                    decode_unit=dict(fullLength=total, bufferList=linked), s_decoder=1,
                    s_frame_buffers=[1], s_frame_index=0, generation=1, INT_MAX=2**31 - 1,
                    s_decoder_buffer=Memory([99] * 132), s_decoder_buffer_size=132,
                    entry=None, length=0, required=0, result=0, BUFFER_TYPE_SPS=7,
                    realloc=lambda *args: self.fail('Unexpected allocation'), memcpy=copy,
                    gs_sps_fix=lambda *args: fixed, vita_video_need_idr=lambda generation: 1)
                self.assertEqual(result, expected)
                if expected:
                    self.assertEqual(copies, [])
                else:
                    self.assertEqual(values['length'], 16 if fixed else 4)


if __name__ == '__main__':
    unittest.main()
