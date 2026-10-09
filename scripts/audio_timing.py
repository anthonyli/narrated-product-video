#!/usr/bin/env python3
"""Clean long silent pauses, preserve speech, change tempo without changing pitch."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import wave


def ffmpeg():
    binary = os.environ.get('FFMPEG_BIN') or shutil.which('ffmpeg')
    if binary:
        return binary
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise SystemExit('Install ffmpeg or imageio-ffmpeg, or set FFMPEG_BIN.')


def probe(path):
    result = subprocess.run([ffmpeg(), '-hide_banner', '-i', str(path), '-af',
        'silencedetect=noise=-45dB:d=0.55', '-f', 'null', '-'], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-2000:])
    pauses = []
    start = None
    for line in result.stderr.splitlines():
        found = re.search(r'silence_start: ([0-9.]+)', line)
        if found:
            start = float(found[1])
        found = re.search(r'silence_end: ([0-9.]+)', line)
        if found and start is not None:
            pauses.append([start, float(found[1])])
            start = None
    return pauses


def map_time(seconds, mapping):
    """Map raw ASR timestamps through measured removals and tempo change."""
    removed = 0.0
    for start, end in mapping['cuts']:
        removed += max(0.0, min(seconds, end) - start)
    return max(0.0, (seconds - removed) / mapping['speed'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input')
    parser.add_argument('--output', required=True)
    parser.add_argument('--map', required=True)
    parser.add_argument('--speed', type=float, default=1.12)
    parser.add_argument('--keep-pause', type=float, default=0.28)
    args = parser.parse_args()
    if not 0.85 <= args.speed <= 1.25:
        raise ValueError('Use a modest speed from 0.85 to 1.25; unusually fast speech needs a new script.')
    if not 0.18 <= args.keep_pause <= 0.55:
        raise ValueError('keep-pause must preserve natural breathing: 0.18–0.55 seconds.')
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.resolve() == Path(args.input).resolve():
        raise ValueError('Keep the raw audio; use a new output path.')
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        pcm = Path(tmp) / 'pcm.wav'
        subprocess.run([ffmpeg(), '-y', '-v', 'error', '-i', args.input,
            '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', str(pcm)], check=True)
        with wave.open(str(pcm)) as w:
            sample_rate = w.getframerate()
            samples = w.readframes(w.getnframes())
            duration = len(samples) / (2 * sample_rate)
        pauses = probe(pcm)
        cuts = []
        for start, end in pauses:
            if start <= 0.01:
                cut = [0.0, max(0.0, end - .07)]
            elif end >= duration - .03:
                cut = [min(duration, start + .12), duration]
            else:
                # Only the silent center is removed; keep >100 ms near both speech edges.
                cut = [start + args.keep_pause / 2, end - args.keep_pause / 2]
            cut = [round(t * sample_rate) / sample_rate for t in cut]
            if cut[1] > cut[0]:
                cuts.append(cut)
        blocks = []
        cursor = 0
        for start, end in cuts:
            blocks.append(samples[cursor:round(start * sample_rate) * 2])
            cursor = round(end * sample_rate) * 2
        blocks.append(samples[cursor:])
        cleaned = Path(tmp) / 'cleaned.wav'
        with wave.open(str(cleaned), 'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sample_rate)
            w.writeframes(b''.join(blocks))
        filters = f'atempo={args.speed},afade=t=in:d=0.008,loudnorm=I=-16:TP=-1.5:LRA=9'
        subprocess.run([ffmpeg(), '-y', '-v', 'error', '-i', str(cleaned), '-af', filters,
            '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', str(output)], check=True)
    with wave.open(str(output)) as w:
        final_duration = w.getnframes() / w.getframerate()
    mapping = {'input_duration': duration, 'output_duration': final_duration,
        'speed': args.speed, 'cuts': cuts, 'detected_long_pauses': pauses,
        'post_long_pauses': probe(output)}
    map_path = Path(args.map)
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text(json.dumps(mapping, indent=2))
    print(json.dumps({'before_seconds': duration, 'after_seconds': final_duration,
        'removed_silence_seconds': sum(b-a for a,b in cuts),
        'remaining_long_pauses': len(mapping['post_long_pauses'])}))


if __name__ == '__main__':
    main()
