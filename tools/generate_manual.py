#!/usr/bin/env python3
"""Author the offline LiveArea manual from the existing EN/RU dictionaries.

Requires Pillow and Open Sans Regular/Semibold. This authors PNG artwork only;
it does not compile CXML, configure/build the application or package a VPK.
"""
import argparse
import hashlib
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont, PngImagePlugin


ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path('/usr/share/fonts/open-sans')
PAGE_COUNT = 12
LOCALES = {'en': '', 'ru': '08'}
BACKGROUND = '#091622'
WHITE = '#f3f6f8'
TEXT = '#dce5eb'
MUTED = '#9fb3c2'
ACCENT = '#83d7df'
RULE = '#2d4353'


def strings(locale):
    return {node.get('id'): node.get('src') for node in
            ET.parse(ROOT / f'cxml/locale/{locale}.xml').getroot()}


def wrapped(text, font, width, limit):
    lines = []
    for paragraph in text.split('\n'):
        line = ''
        for word in paragraph.split():
            if font.getlength(word) > width:
                raise ValueError(f'Word exceeds manual column: {word}')
            candidate = f'{line} {word}'.strip()
            if font.getlength(candidate) > width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    if len(lines) > limit:
        raise ValueError(f'Manual text needs {len(lines)} lines, maximum {limit}: {text}')
    return lines


def render_page(locale, page, font_dir=FONT_DIR):
    if locale not in LOCALES or not 1 <= page <= PAGE_COUNT:
        raise ValueError('Unknown manual locale or page')
    dictionary = strings(locale)
    regular = font_dir / 'OpenSans-Regular.ttf'
    semibold = font_dir / 'OpenSans-Semibold.ttf'
    fonts = {size: ImageFont.truetype(str(regular), size) for size in (17, 21, 23)}
    bold = {size: ImageFont.truetype(str(semibold), size) for size in (20, 23, 36)}
    image = Image.new('RGB', (960, 544), BACKGROUND)
    draw = ImageDraw.Draw(image)

    def label(position, text, font, color, width):
        if font.getlength(text) > width:
            raise ValueError(f'Manual label exceeds {width}px: {text}')
        draw.text(position, text, font=font, fill=color, anchor='lt')

    label((48, 24), dictionary['msg_moonlight_title'], bold[23], WHITE, 420)
    guide = dictionary['msg_manual_guide']
    label((912 - fonts[17].getlength(guide), 29), guide, fonts[17], MUTED, 420)
    prefix = f'msg_manual_{page:02}'
    label((48, 71), dictionary[prefix + '_title'], bold[36], WHITE, 864)
    draw.line((48, 124, 912, 124), fill=RULE)
    draw.line((48, 124, 112, 124), fill=ACCENT, width=3)

    for section in range(1, 4):
        top = 148 + (section - 1) * 100
        label((48, top + 1), str(section), bold[20], ACCENT, 32)
        label((96, top), dictionary[f'{prefix}_head{section}'], bold[23], ACCENT, 816)
        body = dictionary[f'{prefix}_body{section}']
        for index, line in enumerate(wrapped(body, fonts[23], 816, 2)):
            draw.text((96, top + 33 + index * 29), line, font=fonts[23], fill=TEXT, anchor='lt')

    draw.line((48, 445, 912, 445), fill=RULE)
    for index, line in enumerate(wrapped(dictionary[prefix + '_note'], fonts[21], 864, 2)):
        draw.text((48, 460 + index * 27), line, font=fonts[21], fill=MUTED, anchor='lt')
    label((48, 521), dictionary['msg_manual_navigation'], fonts[17], MUTED, 740)
    folio = f'{page:02} / {PAGE_COUNT:02}'
    label((912 - fonts[17].getlength(folio), 521), folio, fonts[17], ACCENT, 110)

    output = BytesIO()
    # Let source checks detect stale translated artwork without Pillow/fonts.
    keys = ['msg_moonlight_title', 'msg_manual_guide', 'msg_manual_navigation']
    keys += [prefix + '_' + suffix for suffix in
             ('title', 'head1', 'body1', 'head2', 'body2', 'head3', 'body3', 'note')]
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text('SourceTextSHA256', hashlib.sha256(
        '\0'.join(dictionary[key] for key in keys).encode('utf-8')).hexdigest())
    image.quantize(colors=96, dither=Image.Dither.NONE).save(
        output, format='PNG', bits=8, pnginfo=metadata)
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--font-dir', type=Path, default=FONT_DIR,
                        help='Directory containing OpenSans-Regular.ttf and OpenSans-Semibold.ttf')
    parser.add_argument('--check', action='store_true', help='Compare authored pages without writing files')
    args = parser.parse_args()
    base = ROOT / 'sce_sys/manual'
    for locale, directory in LOCALES.items():
        destination = base / directory
        if not args.check:
            destination.mkdir(parents=True, exist_ok=True)
        expected = {f'{page:03}.png' for page in range(1, PAGE_COUNT + 1)}
        existing = {path.name for path in destination.glob('*.png')}
        if existing - expected:
            raise ValueError(f'Obsolete manual pages: {sorted(existing - expected)}')
        for page in range(1, PAGE_COUNT + 1):
            path = destination / f'{page:03}.png'
            data = render_page(locale, page, args.font_dir)
            if args.check:
                if not path.is_file() or path.read_bytes() != data:
                    raise ValueError(f'Manual artwork differs: {path}')
            else:
                path.write_bytes(data)
        print(f'{locale}: {PAGE_COUNT} manual pages {"checked" if args.check else "authored"}')


if __name__ == '__main__':
    main()
