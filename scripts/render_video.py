#!/usr/bin/env python3
"""Render a timed image storyboard with ONE continuous narration track."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import wave
from PIL import Image, ImageDraw, ImageFont
from audio_timing import ffmpeg

PRESETS = {'16:9': (1920, 1080), '4:3': (1440, 1080), '3:4': (1080, 1440)}


def stamp(t):
    n = round(t * 1000)
    return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('timeline', help='JSON: aspect, fps, audio, font, shots, captions; paths relative to JSON.')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    root = Path(args.timeline).resolve().parent
    doc = json.loads(Path(args.timeline).read_text())
    width, height = PRESETS[doc.get('aspect', '16:9')]
    fps = int(doc.get('fps', 24))
    if not 12 <= fps <= 60:
        raise ValueError('fps must be from 12 to 60')
    audio = (root / doc['audio']).resolve()
    with wave.open(str(audio)) as w:
        duration = w.getnframes() / w.getframerate()
    font = ImageFont.truetype(str(root / doc['font']), int(doc.get('font_size', min(width, height) * .034)))
    shots = doc['shots']
    captions = doc.get('captions', [])
    cursor = 0
    images = []
    for shot in shots:
        if abs(shot['start'] - cursor) > .05 or shot['end'] <= shot['start']:
            raise ValueError('Shots must be ordered and contiguous; no inserted silent scene padding.')
        im = Image.open(root / shot['image']).convert('RGB')
        if abs(im.width / im.height - width / height) > .015:
            raise ValueError('Recompose the visual for the requested aspect ratio; do not stretch or crop text.')
        images.append(im.resize((width, height), Image.Resampling.LANCZOS))
        cursor = shot['end']
    if not shots or abs(cursor - duration) > .05:
        raise ValueError('The final shot must end at the continuous audio duration.')
    previous_end = 0
    for cue in captions:
        if cue['start'] < previous_end - .01 or not cue['start'] < cue['end'] <= duration + .05:
            raise ValueError('Invalid or overlapping caption timestamps.')
        previous_end = cue['end']
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix('.srt').write_text('\n\n'.join(
        f'{i+1}\n{stamp(c["start"])} --> {stamp(c["end"])}\n{c["text"]}' for i,c in enumerate(captions)))
    cmd = [ffmpeg(), '-y', '-v', 'warning', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{width}x{height}',
        '-r', str(fps), '-i', '-', '-i', str(audio), '-c:v', 'libx264', '-preset', 'fast', '-crf', '19',
        '-threads', '4', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
        '-ac', '2', '-movflags', '+faststart', '-shortest', str(output)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    shot_index = 0
    try:
        for frame_index in range(math.ceil(duration * fps)):
            t = frame_index / fps
            while shot_index < len(shots)-1 and t >= shots[shot_index]['end']:
                shot_index += 1
            image = images[shot_index].copy()
            local = t - shots[shot_index]['start']
            transition = min(.20, (shots[shot_index]['end']-shots[shot_index]['start'])/3)
            if shot_index and local < transition:
                image = Image.blend(images[shot_index-1], image, local/transition)
            cue = next((c for c in captions if c['start'] <= t < c['end']), None)
            if cue:
                draw = ImageDraw.Draw(image)
                # Word/character wrapping keeps Chinese captions within a 90% safe width.
                lines = ['']
                for char in cue['text']:
                    if draw.textlength(lines[-1] + char, font=font) > width*.88:
                        lines.append('')
                    lines[-1] += char
                if len(lines) > 2:
                    raise ValueError('Caption exceeds two lines; split it using word timestamps.')
                line_h = int(font.size * 1.45)
                y = height*.945 - len(lines)*line_h
                for line in lines:
                    length = draw.textlength(line, font=font)
                    x = (width-length)/2
                    draw.rounded_rectangle((x-18,y-6,x+length+18,y+line_h-3),radius=10,fill='#102c30')
                    draw.text((x,y),line,font=font,fill='white')
                    y += line_h
            proc.stdin.write(image.tobytes())
    except BaseException:
        proc.kill(); proc.wait()
        raise
    finally:
        proc.stdin.close()
    if proc.wait():
        raise RuntimeError('Video encoding failed')
    print(json.dumps({'output': str(output), 'width': width, 'height': height, 'duration': duration, 'fps': fps}))


if __name__ == '__main__':
    main()
