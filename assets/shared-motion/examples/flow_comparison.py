"""Different explanation structure: the same objects change route topology.

This is a structural illustration, not a performance simulation or benchmark.
"""
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from core import Scene


CREAM, INK, BLUE, ORANGE = '#F5F2EA', '#17181B', '#3458DF', '#F15B35'


def create_scenes(config, config_dir):
    if config.get('canvas', [1920, 1080]) != [1920, 1080]:
        raise ValueError('This comparison adapter currently supports 1920x1080')
    content = config['content']
    candidates = [os.environ.get('VIDEO_FONT_REGULAR', ''),
                  '/System/Library/Fonts/PingFang.ttc',
                  '/System/Library/Fonts/STHeiti Medium.ttc',
                  '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    path = next((p for p in candidates if p and Path(p).is_file()), None)
    if not path:
        raise ValueError('Set VIDEO_FONT_REGULAR to an installed CJK font')
    fonts = {size: ImageFont.truetype(path, size) for size in (23, 27, 34, 46, 62)}
    names = content['objects']
    if len(names) != 3 or any(not isinstance(n, str) or len(n) > 3 for n in names):
        raise ValueError('Use exactly three short object labels')

    def ease(value):
        value = min(1.0, max(0.0, value))
        return value * value * (3 - 2 * value)

    def frame(time):
        image = Image.new('RGB', (1920, 1080), CREAM)
        draw = ImageDraw.Draw(image)
        draw.text((82, 44), content['eyebrow'], font=fonts[27], fill=INK)
        draw.text((82, 122), content['title'], font=fonts[62], fill=INK)
        spread = ease((time - 1.35) / .7)
        state = content['initial_label'] if time < 1.7 else content['final_label']
        draw.rounded_rectangle((82, 238, 545, 310), radius=36, fill=BLUE if time < 1.7 else ORANGE)
        draw.text((112, 251), state, font=fonts[34], fill='white')
        # The hub identities and packet identities survive the topology change.
        start, finish, middle = 295, 1625, 588
        offsets = (-205, 0, 205)
        colors = (BLUE, INK, ORANGE)

        def point(progress, lane):
            return (start + (finish - start) * progress,
                    middle + offsets[lane] * spread * math.sin(math.pi * progress))

        # At the opening, all paths coincide; the same paths then separate.
        for lane in (1, 0, 2):
            points = [point(index / 120, lane) for index in range(121)]
            draw.line(points, fill=colors[lane] if spread > .01 else '#C8C8C0', width=7)
        for x, label in ((start, content['source']), (finish, content['destination'])):
            draw.ellipse((x - 38, middle - 38, x + 38, middle + 38), fill=INK)
            draw.ellipse((x - 13, middle - 13, x + 13, middle + 13), fill=CREAM)
            draw.text((x, middle + 80), label, font=fonts[34], fill=INK, anchor='mt')
        for lane, name in enumerate(names):
            # No looping, reset or invented throughput metric: each object moves once.
            progress = .19 + lane * .17 + time * .065
            x, y = point(progress, lane)
            draw.ellipse((x - 44, y - 44, x + 44, y + 44), fill=CREAM,
                         outline=colors[lane], width=6)
            draw.text((x, y - 3), name, font=fonts[34], fill=colors[lane], anchor='mm')
        draw.text((82, 885), content['explanation'], font=fonts[34], fill=INK)
        draw.text((1838, 1019), content['disclaimer'], font=fonts[23],
                  fill='#61625C', anchor='ra')
        return image

    return [Scene('route-topology', 4.0, frame)]
