import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition} from '@remotion/renderer';

const types = new Set(['big-title', 'keyword', 'bullet-list', 'number', 'quote', 'comparison', 'browser', 'code', 'diagram', 'progress']);
const fail = message => {throw new Error(message);};
const finite = x => typeof x === 'number' && Number.isFinite(x);
const hasText = x => typeof x === 'string' && x.trim().length > 0;
const rect = box => Array.isArray(box) && box.length === 4 && box.every(finite) &&
  box[0] >= 0 && box[1] >= 0 && box[2] > 0 && box[3] > 0 && box[0] + box[2] <= 1 && box[1] + box[3] <= 1;

export function validate(doc) {
  if (!['16:9', '4:3', '3:4'].includes(doc.aspect)) fail('Choose aspect 16:9, 4:3 or 3:4');
  if (!Number.isInteger(doc.fps) || doc.fps < 12 || doc.fps > 60) fail('fps must be 12–60');
  if (!finite(doc.duration) || doc.duration <= 0) fail('duration must be measured from the final audio');
  if (!hasText(doc.audio)) fail('A continuous audio file is required');
  if (doc.video && doc.image) fail('Choose a video or an image base, not both');
  if (doc.videoFit && !['contain', 'cover'].includes(doc.videoFit)) fail('videoFit must be contain or cover');
  for (const key of ['videoBox', 'cardBox']) if (doc[key] && !rect(doc[key])) fail(`Invalid ${key}`);
  if (!Array.isArray(doc.captions) || !Array.isArray(doc.overlays)) fail('captions and overlays must be arrays');
  const interval = c => {
    if (!finite(c.start) || !finite(c.end) || c.start < 0 || c.end <= c.start || c.end > doc.duration + .001) fail('Invalid final-audio interval');
  };
  let lastEnd = 0;
  for (const cue of doc.captions) {
    interval(cue);
    if (cue.start < lastEnd || !hasText(cue.text)) fail('Captions must be ordered, non-overlapping and nonempty');
    if (cue.text.split('\n').length > 2 || [...cue.text].length > 44) fail('Split long captions into at most two short lines');
    lastEnd = cue.end;
    if (cue.tokens) {
      if (!Array.isArray(cue.tokens) || cue.tokens.map(t => t.text).join('') !== cue.text) fail('Tokens must preserve exact caption text including punctuation');
      let tokenEnd = cue.start;
      for (const token of cue.tokens) {
        interval(token);
        if (typeof token.text !== 'string' || !token.text.length || token.start < tokenEnd - .001 || token.end > cue.end + .001) fail('Tokens must be ordered within their caption');
        tokenEnd = token.end;
      }
    }
  }
  for (const cue of doc.overlays) {
    interval(cue);
    if (!types.has(cue.type)) fail(`Unknown overlay type: ${cue.type}`);
    if (!hasText(cue.text)) fail('Each overlay needs a short text/title');
    if (cue.box && !rect(cue.box)) fail('Invalid overlay box');
    if (cue.type === 'browser' && !hasText(cue.image)) fail('browser needs a local screenshot');
    if (cue.type === 'code' && (!hasText(cue.code) || cue.code.split('\n').length > 8)) fail('code needs at most eight lines');
    if (['diagram', 'bullet-list'].includes(cue.type) && (!Array.isArray(cue.items) || cue.items.length < 1 || cue.items.length > 3 || !cue.items.every(hasText))) fail('Use one to three short items');
    if (cue.type === 'number' && !(hasText(cue.value) || finite(cue.value))) fail('number needs a value');
    if (cue.type === 'comparison' && ![cue.left, cue.right].every(s => s && hasText(s.title) && hasText(s.text))) fail('comparison needs left/right title and text');
  }
  for (const cue of doc.motions ?? []) {
    interval(cue);
    if (![cue.from ?? 1, cue.to ?? 1.025].every(n => finite(n) && n >= 1 && n <= 1.08)) fail('Use subtle zoom from 1 to at most 1.08');
  }
  return doc;
}

function stamp(t) {
  const ms = Math.round(t * 1000);
  return `${String(Math.floor(ms/3600000)).padStart(2,'0')}:${String(Math.floor(ms/60000)%60).padStart(2,'0')}:${String(Math.floor(ms/1000)%60).padStart(2,'0')},${String(ms%1000).padStart(3,'0')}`;
}

async function main() {
  const [timeline, output, ...flags] = process.argv.slice(2);
  if (!timeline || !output || flags.some(x => x !== '--validate-only')) fail('Usage: node render.mjs timeline.json output.mp4 [--validate-only]');
  if (!output.endsWith('.mp4')) fail('Use an .mp4 output path');
  const input = path.resolve(timeline);
  const target = path.resolve(output);
  const subtitle = target.slice(0, -4) + '.srt';
  const doc = validate(JSON.parse(await fs.readFile(input, 'utf8')));
  for (const name of [target, subtitle]) {
    const exists = await fs.access(name).then(() => true, () => false);
    if (exists) fail(`Output already exists: ${name}`);
  }
  const assets = new Map();
  async function resolveAsset(value) {
    if (!hasText(value) || /^(https?:|data:)/i.test(value)) fail('Stage media locally before rendering');
    const source = path.resolve(path.dirname(input), value);
    if (!(await fs.stat(source)).isFile()) fail(`Not a media file: ${source}`);
    if (!assets.has(source)) assets.set(source, `asset-${assets.size}${path.extname(source)}`);
    return assets.get(source);
  }
  for (const key of ['audio', 'video', 'image', 'fontFile']) if (doc[key]) doc[key] = await resolveAsset(doc[key]);
  for (const cue of doc.overlays) if (cue.image) cue.image = await resolveAsset(cue.image);
  if (doc.fontFile) doc.fontFamily = 'VideoFont, sans-serif';
  if (flags.includes('--validate-only')) { console.log('Timeline and local assets validated'); return; }
  await fs.mkdir(path.dirname(target), {recursive: true});
  const tmp = await fs.mkdtemp(path.join(os.tmpdir(), 'narrated-motion-'));
  try {
    const publicDir = path.join(tmp, 'public');
    await fs.mkdir(publicDir);
    for (const [source, name] of assets) await fs.copyFile(source, path.join(publicDir, name));
    const root = path.dirname(fileURLToPath(import.meta.url));
    const serveUrl = await bundle({entryPoint: path.join(root, 'src/index.jsx'), publicDir, outDir: path.join(tmp, 'bundle')});
    const browserExecutable = process.env.REMOTION_BROWSER_EXECUTABLE || undefined;
    const composition = await selectComposition({serveUrl, id: 'NarratedVideo', inputProps: doc, browserExecutable});
    await renderMedia({serveUrl, composition, inputProps: doc, codec: 'h264', audioCodec: 'aac',
      pixelFormat: 'yuv420p', colorSpace: 'bt709', imageFormat: 'png', audioBitrate: '192k', crf: 18, sampleRate: 48000,
      outputLocation: target, overwrite: false, concurrency: 2, browserExecutable});
    await fs.writeFile(subtitle, doc.captions.map((c,i) => `${i+1}\n${stamp(c.start)} --> ${stamp(c.end)}\n${c.text}\n`).join('\n'), {flag: 'wx'});
    console.log(JSON.stringify({output: target, subtitles: subtitle, duration: composition.durationInFrames / doc.fps,
      width: composition.width, height: composition.height, fps: doc.fps}));
  } finally { await fs.rm(tmp, {recursive: true, force: true}); }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(error => {console.error(error.message); process.exitCode = 1;});
}
