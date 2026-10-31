#!/usr/bin/env python3
"""Offline CPU narration in paragraph-sized resumable pieces (no ASR/API/upload)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from local_voice import prepare_plan, load_cpu_backend, wav_info


def split_paragraphs(text):
    parts = [p.strip() for p in text.split('\n\n') if p.strip()]
    if not parts or any(len(p) > 120 for p in parts):
        raise ValueError('Use complete semantic paragraphs of at most 120 characters; do not split by subtitles')
    return parts


def fingerprint(plan, text):
    h = hashlib.sha256()
    for value in (str(plan.model), plan.reference_text, plan.language, text):
        h.update(value.encode()); h.update(b'\0')
    h.update(plan.reference_audio.read_bytes())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', required=True); ap.add_argument('--text', required=True)
    ap.add_argument('--output-dir', required=True); ap.add_argument('--resume', action='store_true')
    args = ap.parse_args(); dest = Path(args.output_dir).resolve()
    # Validate consent, local model, reference and text before creating outputs/imports.
    plan = prepare_plan(args.config, args.text, dest / 'reserved-unused.wav')
    if plan.engine != 'qwen-pytorch-cpu':
        raise ValueError('This bounded runner requires engine=qwen-pytorch-cpu')
    parts = split_paragraphs(plan.text)
    dest.mkdir(parents=True, exist_ok=True)
    lock = dest / '.generation.lock'
    fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    try:
        os.environ['HF_HUB_OFFLINE'] = '1'; os.environ['TRANSFORMERS_OFFLINE'] = '1'
        load, _ = load_cpu_backend(); model = load(str(plan.model))
        import soundfile as sf
        prompt = model.create_voice_clone_prompt(ref_audio=str(plan.reference_audio), ref_text=plan.reference_text)
        for i, text in enumerate(parts, 1):
            output, meta = dest / f'{i:02}.wav', dest / f'{i:02}.json'
            sig = fingerprint(plan, text)
            if output.exists() or meta.exists():
                if not args.resume or not output.exists() or not meta.exists():
                    raise FileExistsError('Existing/incomplete segment; preserve it and choose a new directory')
                saved = json.loads(meta.read_text())
                if saved.get('fingerprint') != sig:
                    raise ValueError('Resume input changed; choose a new directory')
                wav_info(output); print(f'SKIP segment {i}', flush=True); continue
            cap = min(384, max(192, len(text) * 5))
            start = time.monotonic(); print(f'START segment {i}/{len(parts)} cap={cap}', flush=True)
            # Preserve official model sampling defaults. Greedy long-form generation
            # showed pathological wall time in the cloud experiment.
            wavs, rate = model.generate_voice_clone(text=text, language=plan.language,
                voice_clone_prompt=prompt, max_new_tokens=cap)
            with tempfile.TemporaryDirectory(prefix='.segment-', dir=dest) as tmp:
                temp = Path(tmp) / 'audio.wav'; sf.write(temp, wavs[0], rate, subtype='PCM_16')
                info = wav_info(temp); os.link(temp, output)
            report = {'fingerprint': sig, 'segment': i, 'max_new_tokens': cap,
                'elapsed_seconds': time.monotonic()-start, **info,
                'quality_assessed': False, 'asr_and_listening_required': True}
            with meta.open('x', encoding='utf-8') as f: json.dump(report, f, indent=2)
            print(f'DONE segment {i}: {info["duration_seconds"]:.2f}s audio', flush=True)
    finally:
        lock.unlink()


if __name__ == '__main__':
    main()
