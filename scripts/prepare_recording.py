#!/usr/bin/env python3
"""Apply a single-source edit decision list to video and audio together."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import tempfile
import wave

from audio_timing import ffmpeg


def run(args):
    subprocess.run([ffmpeg(), '-hide_banner', '-loglevel', 'error', '-nostdin', *args], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('edl')
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    path = Path(args.edl).resolve()
    doc = json.loads(path.read_text())
    source = (path.parent / doc['source']).resolve()
    if not source.is_file():
        raise ValueError(f'Missing source: {source}')
    fps = doc.get('fps', 30)
    if not isinstance(fps, int) or not 12 <= fps <= 60:
        raise ValueError('fps must be an integer from 12 to 60')
    segments = doc.get('segments', [])
    if not segments:
        raise ValueError('Provide at least one kept segment')
    resolved = []
    cursor = 0
    for segment in segments:
        start = float(segment['in'])
        end = float(segment['out'])
        speed = float(segment.get('speed', 1))
        if not all(math.isfinite(x) for x in (start, end, speed)) or not 0 <= start < end or not .85 <= speed <= 1.25:
            raise ValueError('Invalid interval or speed outside 0.85–1.25')
        start, end = round(start * fps) / fps, round(end * fps) / fps
        frames = round((end - start) / speed * fps)
        if frames < 1:
            raise ValueError('A segment must contain at least one output frame')
        resolved.append({'source_in': start, 'source_out': end, 'speed': speed,
                         'output_in': cursor / fps, 'output_out': (cursor + frames) / fps,
                         'frames': frames, 'reason': segment.get('reason', '')})
        cursor += frames
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    targets = [output / x for x in ('master.mov', 'narration.wav', 'edit-map.json')]
    if any(p.exists() for p in targets):
        raise ValueError('Use a new output directory; existing outputs are preserved')
    with tempfile.TemporaryDirectory(dir=output) as temporary:
        root = Path(temporary)
        # Decode the audio once to validate source duration and require a real audio track.
        raw = root / 'source.wav'
        run(['-i', str(source), '-map', '0:a:0', '-vn', '-ar', '48000', '-ac', '2', '-c:a', 'pcm_s16le', str(raw)])
        with wave.open(str(raw)) as audio:
            source_duration = audio.getnframes() / audio.getframerate()
        if any(s['source_out'] > source_duration + .5 / fps for s in resolved):
            raise ValueError('A kept segment extends past the source audio')
        for index, segment in enumerate(resolved):
            start, end, speed = segment['source_in'], segment['source_out'], segment['speed']
            duration = segment['frames'] / fps
            clip = root / f'clip-{index:04d}.mov'
            run(['-ss', str(start), '-i', str(source), '-t', str(duration),
                 '-map', '0:v:0', '-map', '0:a:0',
                 '-vf', f'trim=duration={end-start},setpts=(PTS-STARTPTS)/{speed},fps={fps},scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1',
                 '-af', f'atrim=duration={end-start},asetpts=PTS-STARTPTS,atempo={speed},aresample=48000',
                 '-c:v', 'libx264', '-crf', '17', '-preset', 'fast', '-pix_fmt', 'yuv420p',
                 '-c:a', 'pcm_s16le', '-ar', '48000', '-ac', '2', str(clip)])
        listing = root / 'clips.txt'
        listing.write_text(''.join(f"file 'clip-{i:04d}.mov'\n" for i in range(len(resolved))))
        master = root / 'master.mov'
        run(['-f', 'concat', '-safe', '1', '-i', str(listing), '-map', '0:v:0', '-map', '0:a:0',
             '-c:v', 'copy', '-af', 'loudnorm=I=-16:TP=-1.5:LRA=9', '-ar', '48000', '-c:a', 'pcm_s16le', str(master)])
        narration = root / 'narration.wav'
        run(['-i', str(master), '-map', '0:a:0', '-c:a', 'pcm_s16le', str(narration)])
        with wave.open(str(narration)) as audio:
            actual_duration = audio.getnframes() / audio.getframerate()
        if abs(actual_duration - cursor / fps) > max(1 / fps, .03):
            raise ValueError('Unexpected duration drift; inspect source timestamps before proceeding')
        master.replace(targets[0])
        narration.replace(targets[1])
    result = {'source': str(source), 'fps': fps, 'segments': resolved,
              'expected_video_duration': cursor / fps, 'audio_duration': actual_duration,
              'timing_note': 'Frame-rounded source intervals. Align captions to the final WAV.'}
    targets[2].write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({'master': str(targets[0]), 'audio': str(targets[1]), 'duration': actual_duration}))


if __name__ == '__main__':
    main()
