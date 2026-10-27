"""Check project CXML references without compiling resources or rendering PAF."""
import unittest
import xml.etree.ElementTree as ET

from test_xml_source import ROOT


class UiResources(unittest.TestCase):
    def test_all_resource_xml_files_are_well_formed(self):
        for path in (ROOT / 'cxml').rglob('*.xml'):
            with self.subTest(path=path.relative_to(ROOT)):
                ET.parse(path)

    def test_local_resource_references_resolve(self):
        root = ET.parse(ROOT / 'cxml/vita_moonlight_ui.xml').getroot()
        definitions = {
            'style': {node.get('id') for node in root.find('styletable')},
            'template': {node.get('id') for node in root.find('templatetable')},
            'texture': {node.get('id') for node in root.find('texturetable')},
        }
        for node in root.iter():
            for attribute, group in (('style', 'style'), ('template', 'template'),
                                     ('texture', 'texture'), ('texture0', 'texture')):
                name = node.get(attribute)
                if name and not name.startswith('_common_'):
                    with self.subTest(node=node.get('id'), attribute=attribute, resource=name):
                        self.assertIn(name, definitions[group])
        for node in root.find('texturetable'):
            self.assertTrue((ROOT / 'cxml' / node.get('src')).is_file())

    def test_text_styles_bind_their_inner_text_object(self):
        root = ET.parse(ROOT / 'cxml/vita_moonlight_ui.xml').getroot()
        for style in root.findall('./styletable/style_text'):
            with self.subTest(style=style.get('id')):
                self.assertTrue(style.get('textobj'))
                self.assertIn(style.get('textobj'), {node.get('id') for node in style.findall('textobj')})

    def test_license_credits_are_read_only_and_resolve_to_component_notices(self):
        settings = ET.parse(ROOT / 'cxml/moonlight_settings.xml').getroot()
        credits = settings.find("./setting_list/setting_list[@id='licenses_settings']")
        self.assertIsNotNone(credits)
        self.assertEqual(credits.get('style'), 'edit')
        strings = {node.get('id'): node.get('src') for node in
                   ET.parse(ROOT / 'cxml/locale/en.xml').getroot().findall('string')}
        self.assertEqual(strings[credits.get('title')], 'Licenses and credits')
        for node in credits.iter():
            self.assertIsNone(node.get('key'))
            self.assertIsNone(node.get('default_value'))
            if node is not credits:
                self.assertEqual(node.tag, 'label')
                self.assertTrue(strings[node.get('title')])
        text = '\n'.join(strings[node.get('title')] for node in credits)
        for component in ('Vita Moonlight', 'moonlight-common-c', 'ENet', 'inih',
                          'h264bitstream', 'mdnsniff', 'curl', 'Expat', 'OpenSSL',
                          'Opus', 'zlib', 'Zstandard', 'newlib', 'pthread-embedded',
                          'GCC Runtime Library Exception', 'vita-headers',
                          'vitasdk-paf-component', 'ScePaf-RE'):
            self.assertIn(component, text)
        self.assertIn('MIT o similar', text)
        self.assertIn('This product includes cryptographic software written by Eric Young', text)
        self.assertIn('This product includes software developed by the OpenSSL Project', text)
        self.assertIn('https://github.com/NowaLone/vita-moonlight-paf/releases', text)


if __name__ == '__main__':
    unittest.main()
