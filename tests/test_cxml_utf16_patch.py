"""Apply the pinned tool patch to a source fixture and interpret it; no builds."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from pycparser import c_ast, c_parser
import test_adapter_lifecycle as runtime
from test_host_persistence import run
from test_xml_source import ROOT

PATCH = ROOT / 'scripts/patches/psp2cxml-utf16-length.patch'
# Original pinned compiler block; the UTF-8-based length is the regression.
ORIGINAL = ('\t\t\t\t}\n\n'
            '\t\t\t\t*(int *)((uintptr_t)ptr + 0x8) = offset >> 1;\n'
            '\t\t\t\t*(int *)((uintptr_t)ptr + 0xC) = strlen(attr->Value()) << 1;\n'
            '\t\t\t}\n\t\t\tbreak;\n\t\tcase attr_type_hash:\n')


class CxmlUtf16Patch(unittest.TestCase):
    def patched_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'src/cxml/cxml.cpp'
            source.parent.mkdir(parents=True)
            source.write_text('\n' * 586 + ORIGINAL)
            applied = subprocess.run(['git', 'apply', str(PATCH)], cwd=directory,
                                     capture_output=True, text=True)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            return source.read_text()

    def test_patch_applies_to_pinned_block_and_ci_applies_it_before_tool_build(self):
        corrected = self.patched_source()
        self.assertNotIn('strlen(attr->Value()) << 1', corrected)
        setup = (ROOT / 'scripts/ci_setup.sh').read_text()
        self.assertLess(setup.index('git -C "$cxml" apply'),
                        setup.index('(cd "$cxml" && bash -e build_linux_macos.sh)'))
        self.assertIn('scripts/patches/psp2cxml-utf16-length.patch', setup)

    def test_corrected_loop_counts_utf16_bytes_for_both_dictionaries(self):
        source = self.patched_source()
        code = source[source.index('uint32_t length = 0;'):source.index('*(int *)((uintptr_t)ptr + 0xC)')]
        code = code.replace('length++;', 'length = length + 1;')
        code = 'typedef unsigned int uint32_t; uint32_t length_bytes(void) {' + code + 'return length << 1;}'
        body = c_parser.CParser().parse(code).ext[-1].body
        original_expression = runtime.expression

        def expression(node, values):
            if isinstance(node, c_ast.BinaryOp) and node.op == '<<':
                return expression(node.left, values) << expression(node.right, values)
            return original_expression(node, values)

        for value in ('', 'Settings', 'Настройки', 'Удалить', 'Трансляция',
                      'Компьютеры', 'Подключение к компьютеру…', 'código', '漢字', '😀'):
            raw = value.encode('utf-16-le')
            units = [int.from_bytes(raw[i:i + 2], 'little') for i in range(0, len(raw), 2)] + [0]
            with self.subTest(text=value), patch.object(runtime, 'expression', expression):
                self.assertEqual(run(body, dict(text=units)), len(raw))
                if any(ord(char) > 127 for char in value):
                    self.assertNotEqual(len(value.encode('utf-8')) * 2, len(raw))


if __name__ == '__main__':
    unittest.main()
