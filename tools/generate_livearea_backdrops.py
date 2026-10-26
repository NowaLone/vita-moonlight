#!/usr/bin/env python3
"""Author the PC card and optionally import Browser's row.

No fonts or artwork are rasterized. Requires Pillow; Browser import also uses
7z. No resources are compiled.
"""
import argparse
from io import BytesIO
from pathlib import Path
import subprocess
from PIL import Image


CONTENTS = Path(__file__).resolve().parents[1] / 'sce_sys/livearea/contents'


def import_browser_row(archive):
    raw = subprocess.check_output(['7z', 'x', '-so', archive, 'sce_sys/livearea/contents/LA_window.png'])
    with Image.open(BytesIO(raw)) as source:
        rgba = source.convert('RGBA')
    colors = list(dict.fromkeys(rgba.getdata()))
    if rgba.size != (472, 48) or len(colors) > 256:
        raise ValueError('Expected the 472x48 Browser row with at most 256 RGBA colors')
    palette = {color: index for index, color in enumerate(colors)}
    indexed = Image.new('P', rgba.size)
    indexed.putpalette([value for color in colors for value in color[:3]] + [0] * (768 - len(colors) * 3))
    indexed.putdata([palette[color] for color in rgba.getdata()])
    output = BytesIO()
    indexed.save(output, format='PNG', bits=8, transparency=bytes(color[3] for color in colors))
    encoded = output.getvalue()
    with Image.open(BytesIO(encoded)) as decoded:
        if decoded.convert('RGBA').tobytes() != rgba.tobytes():
            raise ValueError('Indexed conversion changed Browser row pixels')
    (CONTENTS / 'app_row.png').write_bytes(encoded)


def make_pc_card():
    with Image.open(CONTENTS / 'app_row.png') as row:
        if row.mode != 'P' or row.size != (472, 48) or 'transparency' not in row.info:
            raise ValueError('Expected the indexed 472x48 Browser row with palette alpha')
        card = Image.new('P', (280, 158))
        card.putpalette(row.getpalette())
        # Nine-slice with 8 px caps: keep corners and border thickness intact.
        source_x, source_y = (0, 8, 464, 472), (0, 8, 40, 48)
        target_x, target_y = (0, 8, 272, 280), (0, 8, 150, 158)
        for y in range(3):
            for x in range(3):
                part = row.crop((source_x[x], source_y[y], source_x[x + 1], source_y[y + 1]))
                part = part.resize((target_x[x + 1] - target_x[x], target_y[y + 1] - target_y[y]),
                                   Image.Resampling.NEAREST)
                card.paste(part, (target_x[x], target_y[y]))
        output = BytesIO()
        card.save(output, format='PNG', bits=8, transparency=row.info['transparency'])
        return output.getvalue()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-archive', help='Import LA_window.png losslessly from the supplied sce_sys.7z')
    args = parser.parse_args()
    if args.browser_archive:
        import_browser_row(args.browser_archive)
    (CONTENTS / 'pc_card.png').write_bytes(make_pc_card())
