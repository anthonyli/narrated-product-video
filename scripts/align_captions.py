#!/usr/bin/env python3
"""Check authored text against ASR and map word timing to processed narration."""
import argparse
import difflib
import json
from pathlib import Path
import re
from audio_timing import map_time


def normalized(text):
    return ''.join(c.lower() for c in text if c.isalnum())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--alignment', required=True)
    parser.add_argument('--text', required=True)
    parser.add_argument('--map', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    document = json.loads(Path(args.alignment).read_text())
    mapping = json.loads(Path(args.map).read_text())
    authored = Path(args.text).read_text().strip()
    timed = []
    for transcription in document['transcriptions']:
        for transcript in transcription['transcripts']:
            for sentence in transcript['sentences']:
                for word in sentence['words']:
                    chars = normalized(word['text'])
                    a, b = word['begin_time']/1000, word['end_time']/1000
                    for i, char in enumerate(chars):
                        timed.append({'char': char,
                            'start': map_time(a+(b-a)*i/len(chars), mapping),
                            'end': min(mapping['output_duration'], map_time(a+(b-a)*(i+1)/len(chars), mapping))})
    expected = normalized(authored)
    recognized = ''.join(c['char'] for c in timed)
    if expected != recognized:
        changes = [f'{tag}: script={expected[a:b]!r}, ASR={recognized[c:d]!r}'
            for tag,a,b,c,d in difflib.SequenceMatcher(None, expected, recognized, autojunk=False).get_opcodes()
            if tag != 'equal']
        raise ValueError('Transcript differs; review audio and correct confirmed ASR errors before retrying. ' + '; '.join(changes))
    # Split at punctuation first; keep English tokens intact when splitting long clauses.
    pieces = []
    for clause in re.findall(r'[^，。！？；、,!?;\n]+[，。！？；、,!?;]?', authored):
        current = ''
        for token in re.findall(r'[A-Za-z0-9]+|.', clause):
            if len(current + token) > 22 and current.strip():
                pieces.append(current.strip()); current = ''
            current += token
        if current.strip():
            pieces.append(current.strip())
    cues = []
    cursor = 0
    for piece in pieces:
        size = len(normalized(piece))
        if not size:
            continue
        cues.append({'start': timed[cursor]['start'], 'end': timed[cursor+size-1]['end'], 'text': piece})
        cursor += size
    if cursor != len(timed):
        raise ValueError('Caption splitting did not cover the entire script.')
    for i, cue in enumerate(cues):
        limit = cues[i+1]['start']-.02 if i+1 < len(cues) else mapping['output_duration']
        cue['end'] = min(limit, cue['end']+.10)
        if cue['end'] <= cue['start'] or cue['start'] < 0:
            raise ValueError('Invalid ASR word timing.')
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'captions': cues, 'characters': timed,
        'timing_provenance': {'source': 'ASR word timestamps',
                             'characters': 'estimated by interpolation within each word; not character forced alignment'},
        'verification': {'normalized_text_exact_match': True, 'characters': len(timed)}}, ensure_ascii=False, indent=2))
    print(f'Verified {len(timed)} characters; created {len(cues)} captions.')


if __name__ == '__main__':
    main()
