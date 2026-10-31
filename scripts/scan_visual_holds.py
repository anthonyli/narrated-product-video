#!/usr/bin/env python3
"""Find low-change MAIN-PICTURE spans in a video; advisory, never aesthetic approval.
Uses existing FFmpeg/FFprobe only. Does not install dependencies or alter input.
Default normalized ROI excludes header and subtitle band; inspect/override it for
other layouts. Subtitles, camera drift, cuts and compression can fool metrics.
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path


def finite_positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{label} must be finite and positive')
    return float(value)


def low_change_spans(scores, sample_fps, threshold=0.006, min_hold=3.0):
    """scores[i] compares frames i and i+1; normalized MAE in [0,1]."""
    fps = finite_positive(sample_fps, 'sample_fps')
    finite_positive(min_hold, 'min_hold')
    if not 0 <= threshold <= 1:
        raise ValueError('threshold must be in [0,1]')
    spans, start = [], None
    for i, score in enumerate([*scores, None]):
        if score is not None and (not math.isfinite(score) or not 0 <= score <= 1):
            raise ValueError('scores must be finite values in [0,1]')
        if score is not None and score <= threshold:
            if start is None:
                start = i / fps
        elif start is not None:
            end = i / fps
            if end - start >= min_hold:
                spans.append({'start': round(start, 3), 'end': round(end, 3),
                              'duration': round(end-start, 3), 'status': 'not_checked'})
            start = None
    return spans


def scan(video, ffmpeg='ffmpeg', ffprobe='ffprobe', sample_fps=2.0,
         roi=(0.0, 0.12, 1.0, 0.82), threshold=0.006, min_hold=3.0):
    finite_positive(sample_fps, 'sample_fps')
    if sample_fps > 10:
        raise ValueError('sample_fps must be <= 10 for this advisory scan')
    if len(roi) != 4 or not all(math.isfinite(x) for x in roi):
        raise ValueError('roi must contain four finite numbers')
    x1, y1, x2, y2 = roi
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        raise ValueError('roi requires 0 <= left < right <= 1 and 0 <= top < bottom <= 1')
    info = json.loads(subprocess.check_output([ffprobe, '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height:format=duration', '-of', 'json', str(video)]))
    stream = info['streams'][0]
    w, h = stream['width'], stream['height']
    duration = float(info['format']['duration'])
    finite_positive(duration, 'video duration')
    crop = (max(1, int(w*(x2-x1))), max(1, int(h*(y2-y1))), int(w*x1), int(h*y1))
    filter_arg = f'fps={sample_fps},crop={crop[0]}:{crop[1]}:{crop[2]}:{crop[3]},scale=160:90,format=gray'
    proc = subprocess.Popen([ffmpeg, '-v', 'error', '-i', str(video), '-an', '-vf', filter_arg,
        '-f', 'rawvideo', '-pix_fmt', 'gray', 'pipe:1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    previous, scores, frames = None, [], 0
    size = 160*90
    while True:
        frame = proc.stdout.read(size)
        if not frame:
            break
        if len(frame) != size:
            proc.kill(); proc.wait()
            raise ValueError('incomplete decoded frame')
        frames += 1
        if previous is not None:
            scores.append(sum(abs(a-b) for a,b in zip(frame, previous)) / (size*255))
        previous = frame
    error = proc.stderr.read().decode(errors='replace')
    if proc.wait() != 0:
        raise ValueError(f'FFmpeg scan failed: {error[-2000:]}')
    if frames < 2:
        raise ValueError('video too short or undecodable for sampled change scan')
    return {'schema_version': 1, 'video': str(video),
        'video_sha256': hashlib.sha256(Path(video).read_bytes()).hexdigest(),
        'duration': duration, 'sample_fps': sample_fps, 'sample_count': frames,
        'roi_normalized': list(roi), 'metric': 'normalized grayscale mean absolute difference',
        'threshold': threshold, 'min_hold': min_hold,
        'quality_assessed': False, 'formal_delivery_allowed': False,
        'low_change_spans': low_change_spans(scores, sample_fps, threshold, min_hold),
        'limitations': 'Advisory only. Review full-frame motion, meaning and audio. A low score may be a justified reading hold; movement, cuts or subtitle pixels may conceal poor storytelling. Endpoints are sampled, not exact motion boundaries.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('video', type=Path); p.add_argument('--output', type=Path)
    p.add_argument('--ffmpeg', default='ffmpeg');p.add_argument('--ffprobe',default='ffprobe')
    p.add_argument('--sample-fps',type=float,default=2.0)
    p.add_argument('--roi',type=float,nargs=4,default=(0,.12,1,.82),metavar=('LEFT','TOP','RIGHT','BOTTOM'))
    p.add_argument('--threshold',type=float,default=.006);p.add_argument('--min-hold',type=float,default=3.)
    a=p.parse_args()
    try:
        result=scan(a.video,a.ffmpeg,a.ffprobe,a.sample_fps,a.roi,a.threshold,a.min_hold)
        payload=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        if a.output:
            with a.output.open('x',encoding='utf-8') as f:f.write(payload)
        else:sys.stdout.write(payload)
    except (ValueError,OSError,subprocess.SubprocessError,KeyError,IndexError) as e:p.exit(2,f'scan_visual_holds: {e}\n')

if __name__=='__main__':main()
