"""Mock resource lookups with the English dictionary in serial source interpreters."""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

STRINGS = {node.get('id'): node.get('src') for node in
           ET.parse(Path(__file__).resolve().parents[1] / 'cxml/locale/en.xml').getroot()}


def mock_ui_text(code):
    return re.sub(r'ui_text\("(msg_\w+)"\)\.c_str\(\)',
                  lambda match: json.dumps(STRINGS[match[1]]), code)
