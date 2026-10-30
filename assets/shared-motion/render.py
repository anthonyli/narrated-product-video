#!/usr/bin/env python3
"""Render trusted local Python adapters (including during --validate-only).

Does not install or download. Only use adapter source you have reviewed.
"""
import argparse
import json
import os
from core import load_episode, render, validate_render


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config')
    parser.add_argument('output')
    parser.add_argument('--fps', type=int, choices=[30, 60])
    parser.add_argument('--ffmpeg', default=os.environ.get('FFMPEG_BIN', 'ffmpeg'))
    parser.add_argument('--audio', help='Continuous local PCM WAV with the same length as the full timeline')
    parser.add_argument('--start', type=float, default=0)
    parser.add_argument('--end', type=float)
    parser.add_argument('--preview-at', type=float)
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    try:
        episode, config = load_episode(args.config, args.fps)
        result = {'valid': True, 'duration': episode.duration, 'fps': episode.fps,
                  'scene_ids': [s.id for s in episode.scenes], 'quality_assessed': False}
        validate_render(episode, args.output, audio=args.audio, start=args.start, end=args.end, preview_at=args.preview_at)
        if not args.validate_only:
            result = render(episode, args.output, ffmpeg=args.ffmpeg, audio=args.audio,
                            start=args.start, end=args.end, preview_at=args.preview_at)
        print(json.dumps(result, ensure_ascii=False))
    except (ValueError, OSError, RuntimeError, KeyError, TypeError) as error:
        parser.exit(1, f'{type(error).__name__}: {error}\n')


if __name__ == '__main__':
    main()
