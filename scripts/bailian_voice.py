#!/usr/bin/env python3
"""Bailian reference voice, paragraph TTS and word timestamps. Stdlib only."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
    temp.replace(path)


def request(base, path, payload=None, asynchronous=False):
    key = os.environ.get('DASHSCOPE_API_KEY')
    if not key:
        raise ValueError('Set DASHSCOPE_API_KEY in the process environment; do not put it in the script.')
    headers = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}
    if asynchronous:
        headers['X-DashScope-Async'] = 'enable'
    req = urllib.request.Request(base.rstrip('/') + path,
        data=None if payload is None else json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read())
        except ValueError:
            body = {}
        raise RuntimeError(f"HTTP {exc.code}: {body.get('code', '')} {body.get('message', '')}") from None
    if result.get('code'):
        raise RuntimeError(f"{result['code']}: {result.get('message', '')}")
    return result


def mutation(args, payload, endpoint, asynchronous=False):
    """Cache paid operations; refuse an ambiguous retry instead of silently charging twice."""
    dest = Path(args.output)
    digest = hashlib.sha256(json.dumps([args.base, endpoint, payload], sort_keys=True).encode()).hexdigest()
    pending = dest.with_suffix(dest.suffix + '.pending')
    if dest.exists():
        saved = json.loads(dest.read_text())
        if saved.get('request_hash') != digest:
            raise ValueError('Output exists for different input. Choose a new output path.')
        return saved['response']
    if pending.exists():
        raise ValueError('An earlier request has an uncertain result. Inspect provider status before retrying; do not delete the marker blindly.')
    write_json(pending, {'request_hash': digest, 'operation': args.command})
    result = request(args.base, endpoint, payload, asynchronous)
    write_json(dest, {'request_hash': digest, 'response': result})
    pending.unlink()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', default='https://dashscope.aliyuncs.com/api/v1')
    sub = parser.add_subparsers(dest='command', required=True)
    enroll = sub.add_parser('enroll', help='Create a voice only with speaker authorization; reuse a matching existing voice when available.')
    enroll.add_argument('--reference', required=True)
    enroll.add_argument('--model', default='qwen3-tts-vc-2026-01-22')
    enroll.add_argument('--name', default='tutorial')
    enroll.add_argument('--output', required=True)
    tts = sub.add_parser('synthesize', help='Synthesize one coherent script or paragraph, not individual subtitle lines.')
    tts.add_argument('--text', required=True)
    tts.add_argument('--voice', required=True)
    tts.add_argument('--model', default='qwen3-tts-vc-2026-01-22')
    tts.add_argument('--language', default='Chinese')
    tts.add_argument('--output', required=True, help='Private response JSON cache; contains a temporary audio URL.')
    tts.add_argument('--audio', required=True)
    submit = sub.add_parser('align-submit', help='Request word timestamps for the provider-generated raw audio URL.')
    submit.add_argument('--tts-response', required=True)
    submit.add_argument('--output', required=True)
    fetch = sub.add_parser('align-fetch', help='Poll an existing task once; pending returns exit 3.')
    fetch.add_argument('--task', required=True)
    fetch.add_argument('--output', required=True)
    args = parser.parse_args()
    if args.command == 'enroll':
        ref = Path(args.reference)
        mime = {'.wav': 'audio/wav', '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4'}.get(ref.suffix.lower())
        if not mime:
            raise ValueError('Reference must be WAV, MP3 or M4A.')
        payload = {'model': 'qwen-voice-enrollment', 'input': {'action': 'create', 'target_model': args.model,
            'preferred_name': args.name, 'audio': {'data': f'data:{mime};base64,' + base64.b64encode(ref.read_bytes()).decode()}}}
        result = mutation(args, payload, '/services/audio/tts/customization')
        if not result.get('output', {}).get('voice'):
            raise ValueError('Provider did not return a voice.')
        print('Voice created; ID saved in the private response JSON.')
    elif args.command == 'synthesize':
        text = Path(args.text).read_text().strip()
        if not text or len(text) > 600:
            raise ValueError('Use 1–600 characters per coherent paragraph; split longer scripts at paragraph boundaries before calling.')
        payload = {'model': args.model, 'input': {'text': text, 'voice': args.voice, 'language_type': args.language}}
        result = mutation(args, payload, '/services/aigc/multimodal-generation/generation')
        audio = Path(args.audio)
        if not audio.exists():
            url = result.get('output', {}).get('audio', {}).get('url')
            if not url:
                raise ValueError('No audio URL returned.')
            audio.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url, timeout=120) as response:
                data = response.read()
            audio.write_bytes(data)
        print(f'Synthesized {len(text)} characters; audio saved to {audio}.')
    elif args.command == 'align-submit':
        saved = json.loads(Path(args.tts_response).read_text())['response']
        url = saved['output']['audio']['url']
        payload = {'model': 'qwen3-asr-flash-filetrans', 'input': {'file_url': url},
            'parameters': {'channel_id': [0], 'enable_itn': False, 'enable_words': True}}
        result = mutation(args, payload, '/services/audio/asr/transcription', True)
        print('Alignment task:', result['output']['task_id'])
    else:
        task = json.loads(Path(args.task).read_text())['response']['output']['task_id']
        result = request(args.base, '/tasks/' + task)
        status = result['output']['task_status']
        if status in ('PENDING', 'RUNNING'):
            print(status)
            return 3
        if status != 'SUCCEEDED':
            raise RuntimeError('Alignment failed: ' + json.dumps(result['output'], ensure_ascii=False))
        output = result['output']
        entries = output.get('results', [output.get('result', output)])
        transcripts = []
        for item in entries:
            url = item.get('transcription_url')
            if not url:
                raise ValueError('No transcription_url in successful task output.')
            with urllib.request.urlopen(url, timeout=120) as response:
                transcripts.append(json.load(response))
        write_json(args.output, {'task_id': task, 'transcriptions': transcripts})
        print('Word alignment saved:', args.output)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, RuntimeError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
