"""Validate offline manual copies, PNGs and packaging without fonts or builds."""
import ast
import hashlib
import re
import struct
import unittest
import xml.etree.ElementTree as ET
import zlib

from test_xml_source import ROOT


class Manual(unittest.TestCase):
    def test_translated_pages_are_complete_and_packaged_at_native_paths(self):
        expected = {f'sce_sys/manual/{directory}{page:03}.png'
                    for directory in ('', '08/') for page in range(1, 13)}
        actual = {str(path.relative_to(ROOT)) for path in (ROOT / 'sce_sys/manual').rglob('*.png')}
        self.assertEqual(actual, expected)
        cmake = (ROOT / 'CMakeLists.txt').read_text()
        files = re.findall(r'FILE\s+\$\{CMAKE_CURRENT_SOURCE_DIR\}/(sce_sys/manual/\S+)\s+(\S+)', cmake)
        self.assertEqual(len(files), len(expected))
        self.assertEqual(set(files), {(path, path) for path in expected})
        required = {'msg_manual_guide', 'msg_manual_navigation'}
        required.update(f'msg_manual_{page:02}_{suffix}' for page in range(1, 13) for suffix in
                        ('title', 'head1', 'body1', 'head2', 'body2', 'head3', 'body3', 'note'))
        for locale in ('en', 'ru'):
            dictionary = {node.get('id'): node.get('src') for node in
                          ET.parse(ROOT / f'cxml/locale/{locale}.xml').getroot()}
            self.assertEqual({key for key in dictionary if key.startswith('msg_manual_')}, required)
            self.assertTrue(all(dictionary[key] for key in required))

    def test_pngs_are_valid_and_match_the_current_translated_copy(self):
        for locale, directory in (('en', ''), ('ru', '08/')):
            dictionary = {node.get('id'): node.get('src') for node in
                          ET.parse(ROOT / f'cxml/locale/{locale}.xml').getroot()}
            for page in range(1, 13):
                with self.subTest(locale=locale, page=page):
                    raw = (ROOT / f'sce_sys/manual/{directory}{page:03}.png').read_bytes()
                    self.assertEqual(raw[:8], b'\x89PNG\r\n\x1a\n')
                    offset, chunks, image, metadata = 8, [], b'', {}
                    while offset < len(raw):
                        size = struct.unpack_from('>I', raw, offset)[0]
                        kind = raw[offset + 4:offset + 8]
                        data = raw[offset + 8:offset + 8 + size]
                        crc = struct.unpack_from('>I', raw, offset + 8 + size)[0]
                        self.assertEqual(zlib.crc32(kind + data) & 0xffffffff, crc)
                        chunks.append(kind)
                        if kind == b'IHDR':
                            self.assertEqual(struct.unpack('>IIBBBBB', data), (960, 544, 8, 3, 0, 0, 0))
                        elif kind == b'IDAT':
                            image += data
                        elif kind == b'tEXt':
                            key, value = data.split(b'\0', 1)
                            metadata[key.decode('ascii')] = value.decode('ascii')
                        offset += size + 12
                    self.assertEqual(offset, len(raw))
                    self.assertEqual(chunks[0], b'IHDR')
                    self.assertEqual(chunks[-1], b'IEND')
                    self.assertIn(b'PLTE', chunks)
                    pixels = zlib.decompress(image)
                    self.assertEqual(len(pixels), 961 * 544)
                    self.assertTrue(all(filter_type <= 4 for filter_type in pixels[::961]))
                    keys = ['msg_moonlight_title', 'msg_manual_guide', 'msg_manual_navigation']
                    keys += [f'msg_manual_{page:02}_{suffix}' for suffix in
                             ('title', 'head1', 'body1', 'head2', 'body2', 'head3', 'body3', 'note')]
                    digest = hashlib.sha256('\0'.join(dictionary[key] for key in keys).encode()).hexdigest()
                    self.assertEqual(metadata['SourceTextSHA256'], digest, 'Regenerate the translated manual')

    def test_wrapping_preserves_unicode_and_rejects_overflow_instead_of_clipping(self):
        tree = ast.parse((ROOT / 'tools/generate_manual.py').read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'wrapped')
        scope = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), '<manual wrapping>', 'exec'), scope)
        font = type('Font', (), {'getlength': staticmethod(len)})()
        wrap = scope['wrapped']
        self.assertEqual(wrap('один два три', font, 8, 2), ['один два', 'три'])
        self.assertEqual(wrap('exact\nnext', font, 5, 2), ['exact', 'next'])
        with self.assertRaises(ValueError):
            wrap('oversized', font, 5, 2)
        with self.assertRaises(ValueError):
            wrap('one two three', font, 5, 2)


if __name__ == '__main__':
    unittest.main()
