#!/usr/bin/env python3
"""Add reviewed captions to a local MP4, preserving audio and the full picture.

Burn mode overlays the original skill's rounded dark caption box on the full
picture. Scene layouts must leave room for captions; no scale, crop or pad is used.
Sidecar mode copies the original MP4 unchanged and writes only separate SRT.
This validates timing structure, not ASR accuracy, pronunciation or listening.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from decimal import Decimal, ROUND_HALF_UP
import html
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unicodedata


def finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f'{label} must be a finite number')
    try:
        valid = math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f'{label} must be finite and nonnegative')
    return value


def ticks(seconds, precision):
    return int((Decimal(str(seconds)) * precision).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def timestamp(seconds, *, ass=False):
    precision = 100 if ass else 1000
    value = ticks(seconds, precision)
    hours, value = divmod(value, 3600 * precision)
    minutes, value = divmod(value, 60 * precision)
    whole, fraction = divmod(value, precision)
    return (f'{hours}:{minutes:02d}:{whole:02d}.{fraction:02d}' if ass else
            f'{hours:02d}:{minutes:02d}:{whole:02d},{fraction:03d}')


def validate_captions(document):
    if not isinstance(document, dict) or not isinstance(document.get('captions'), list) or not document['captions']:
        raise ValueError('Expected a nonempty captions array')
    result = []
    previous_end = 0
    duration = document.get('duration')
    if duration is not None:
        finite(duration, 'duration')
        if duration <= 0:
            raise ValueError('duration must be positive')
    for index, cue in enumerate(document['captions']):
        if not isinstance(cue, dict):
            raise ValueError(f'Caption {index} must be an object')
        start, end = finite(cue.get('start'), 'start'), finite(cue.get('end'), 'end')
        if end <= start or start < previous_end or (duration is not None and end > duration):
            raise ValueError('Captions must be ordered, nonoverlapping and within duration')
        if ticks(end, 100) <= ticks(start, 100):
            raise ValueError('Caption is too short for ASS centisecond timing')
        value = cue.get('text')
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Caption text must be nonempty')
        if any(ord(c) < 32 and c != '\n' for c in value):
            raise ValueError('Caption text has unsupported control characters')
        lines = value.split('\n')
        if len(lines) > 2 or any(not line.strip() for line in lines) or len(value.replace('\n', '')) > 44:
            raise ValueError('Use at most two nonempty lines and 44 characters')
        # Keep all authored characters. Automatic wrap is layout, not ASR repair.
        if len(lines) == 1 and len(value) > 22:
            split = min(22, max(1, len(value) // 2))
            lines = [value[:split], value[split:]]
        result.append({'start': start, 'end': end, 'text': '\n'.join(lines)})
        previous_end = end
    return result


def ass_escape(value):
    # ASS has no reliable literal escape for every override syntax. Use visible
    # full-width glyphs for these three characters; SRT retains the original text.
    value = value.replace('\\', '＼').replace('{', '｛').replace('}', '｝')
    return value.replace('\n', r'\N')


def srt_text(captions):
    return '\n'.join(f'{i}\n{timestamp(cue["start"])} --> {timestamp(cue["end"])}\n'
                     f'{html.escape(cue["text"], quote=False)}\n'
                     for i, cue in enumerate(captions, 1))


def text_width(text, font_size, font_file=None):
    """Measure the selected font, or conservatively estimate full/half-width glyphs."""
    if font_file is not None:
        if not Path(font_file).is_file():
            raise ValueError('Font file must be an existing local file')
        try:
            from PIL import ImageFont
        except ImportError as error:
            raise ValueError('Measuring --font-file requires the existing Pillow dependency') from error
        font = ImageFont.truetype(str(font_file), font_size)
        # Leave a little slack for weight 600 and shaping differences in libass.
        return math.ceil(font.getlength(text) * 1.04)
    units = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        if unicodedata.east_asian_width(char) in {'W', 'F', 'A'} or not char.isascii():
            units += 1
        elif char in 'MW@#%&':
            units += 1
        elif char in ' il.,:;!|\'`':
            units += .45
        else:
            units += .8
    return math.ceil(units * font_size)


def rounded_box(width, height, radius=12):
    """ASS vector path in local coordinates; cubic arcs avoid square ASS borders."""
    r, k = radius, radius * .55228475
    return (f'm {r} 0 l {width-r} 0 '
            f'b {width-r+k:.2f} 0 {width} {r-k:.2f} {width} {r} '
            f'l {width} {height-r} '
            f'b {width} {height-r+k:.2f} {width-r+k:.2f} {height} {width-r} {height} '
            f'l {r} {height} '
            f'b {r-k:.2f} {height} 0 {height-r+k:.2f} 0 {height-r} '
            f'l 0 {r} b 0 {r-k:.2f} {r-k:.2f} 0 {r} 0')


def ass_text(captions, font_name='PingFang SC', font_size=40, font_file=None):
    if not isinstance(font_name, str) or not font_name.strip() or any(c in font_name for c in ',\r\n{}\\'):
        raise ValueError('Font name must be plain text without ASS delimiters')
    if isinstance(font_size, bool) or not isinstance(font_size, int) or not 20 <= font_size <= 48:
        raise ValueError('Font size must be an integer from 20 to 48')
    captions = validate_captions({'captions': captions})
    header = ('[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\n'
              'WrapStyle: 2\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\n'
              'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, '
              'Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, '
              'Alignment, MarginL, MarginR, MarginV, Encoding\n'
              f'Style: Default,{font_name},{font_size},&H00F3FAFD,&H00F3FAFD,&H000A1217,&H000A1217,'
              '0,0,0,0,100,100,-0.4,0,1,0,0,5,0,0,0,1\n\n[Events]\n'
              'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n')
    events = []
    for cue in captions:
        lines = cue['text'].split('\n')
        # Match Captions in assets/remotion/src/index.jsx: 60px line boxes,
        # 14/28px padding, 12px corner radius and 7% (~76px) bottom margin.
        width = max(text_width(ass_escape(line), font_size, font_file) for line in lines) + 56
        if width > 1920 * .86 * .72:
            raise ValueError('Caption is wider than the original skill safe width; split at word timestamps')
        height = len(lines) * 60 + 28
        x, y = (1920 - width) / 2, 1080 - 76 - height
        interval = f'{timestamp(cue["start"], ass=True)},{timestamp(cue["end"], ass=True)}'
        background = (rf'{{\an7\pos({x:.1f},{y})\p1\bord0\shad0'
                      r'\1c&H0A1217&\1a&H11&}' + rounded_box(width, height) + r'{\p0}')
        events.append(f'Dialogue: 0,{interval},Default,,0,0,0,,{background}\n')
        for index, line in enumerate(lines):
            tags = rf'{{\an5\pos(960,{y+14+30+60*index})\b600\bord0\shad0}}'
            events.append(f'Dialogue: 1,{interval},Default,,0,0,0,,{tags}{ass_escape(line)}\n')
    return header + ''.join(events)


def build_command(ffmpeg, video, output):
    # The fixed local ASS basename is resolved in the temporary working directory;
    # arbitrary user paths never enter filter syntax. Preserve every source pixel
    # position, frame dimension and sample aspect ratio; ASS only adds captions.
    filters = 'ass=filename=captions.ass:fontsdir=fonts'
    return [str(ffmpeg), '-hide_banner', '-v', 'error', '-n', '-i', str(Path(video).resolve()),
            '-map', '0:v:0', '-map', '0:a?', '-vf', filters, '-c:v', 'libx264', '-preset', 'fast',
            '-crf', '18', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', str(output)]


def validate_paths(video, output, srt):
    video = Path(video).resolve()
    output, srt = Path(output).absolute(), Path(srt).absolute()
    if not video.is_file() or video.stat().st_size <= 0 or video.suffix.lower() != '.mp4':
        raise ValueError('Input must be a nonempty local MP4')
    if output.suffix.lower() != '.mp4' or srt.suffix.lower() != '.srt':
        raise ValueError('Use .mp4 video output and .srt subtitle output')
    if len({video, output.resolve(), srt.resolve()}) != 3:
        raise ValueError('Input and output paths must be distinct')
    for path in [output, srt]:
        if path.exists() or path.is_symlink():
            raise FileExistsError(f'Preserve existing output: {path}')
    return video, output, srt


def render(video, captions, output, srt, *, mode='burn', ffmpeg='ffmpeg', font_name='PingFang SC', font_size=40, font_file=None):
    if mode not in {'burn', 'sidecar'}:
        raise ValueError('Choose burn or sidecar')
    video, output, srt = validate_paths(video, output, srt)
    captions = validate_captions({'captions': captions})
    ass = ass_text(captions, font_name, font_size, font_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    srt.parent.mkdir(parents=True, exist_ok=True)
    with ExitStack() as stack:
        video_dir = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='.captions-', dir=output.parent)))
        srt_dir = Path(stack.enter_context(tempfile.TemporaryDirectory(prefix='.captions-', dir=srt.parent)))
        temporary_video, temporary_srt = video_dir/'video.mp4', srt_dir/'captions.srt'
        temporary_srt.write_text(srt_text(captions), encoding='utf-8')
        if mode == 'sidecar':
            shutil.copyfile(video, temporary_video)
        else:
            (video_dir/'captions.ass').write_text(ass, encoding='utf-8')
            (video_dir/'fonts').mkdir()
            if font_file is not None:
                shutil.copyfile(font_file, video_dir/'fonts'/Path(font_file).name)
            result = subprocess.run(build_command(ffmpeg, video, temporary_video), cwd=video_dir,
                                    capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError('FFmpeg caption render failed: ' + result.stderr[-2000:])
            if not temporary_video.is_file() or temporary_video.stat().st_size == 0:
                raise RuntimeError('FFmpeg produced no video')
        # Each target is published exclusively. A concurrent writer is never replaced.
        os.link(temporary_video, output)
        os.link(temporary_srt, srt)
    return {'output': str(output), 'srt': str(srt), 'mode': mode,
            'burned_narration_subtitles': mode == 'burn', 'captions': len(captions),
            'audio_changed': False, 'quality_assessed': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--video', required=True)
    parser.add_argument('--captions', required=True, help='Reviewed captions JSON; timestamps in seconds')
    parser.add_argument('--output', required=True)
    parser.add_argument('--srt', required=True)
    parser.add_argument('--mode', choices=['burn', 'sidecar'], default='burn')
    parser.add_argument('--ffmpeg', default=os.environ.get('FFMPEG_BIN', 'ffmpeg'))
    parser.add_argument('--font-name', default='PingFang SC')
    parser.add_argument('--font-size', type=int, default=40)
    parser.add_argument('--font-file', help='Optional local font for measurement and libass; name must match --font-name')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        captions = validate_captions(json.loads(Path(args.captions).read_text(encoding='utf-8')))
        validate_paths(args.video, args.output, args.srt)
        ass_text(captions, args.font_name, args.font_size, args.font_file)
        result = {'valid': True, 'captions': len(captions), 'quality_assessed': False}
        if not args.validate_only:
            result = render(args.video, captions, args.output, args.srt, mode=args.mode,
                            ffmpeg=args.ffmpeg, font_name=args.font_name, font_size=args.font_size,
                            font_file=args.font_file)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (ValueError, OSError, RuntimeError, UnicodeError) as error:
        parser.exit(1, f'{type(error).__name__}: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
