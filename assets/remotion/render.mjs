import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
import {auditEditorial, editorialStillPoints, mapEditorialAssets, validateEditorial} from './editorial-contract.mjs';

const types = new Set(['big-title', 'keyword', 'bullet-list', 'number', 'quote', 'comparison', 'browser', 'code', 'diagram', 'progress', 'chapter-label', 'info-card', 'input-bar']);
const fail = message => {throw new Error(message);};
const finite = x => typeof x === 'number' && Number.isFinite(x);
const hasText = x => typeof x === 'string' && x.trim().length > 0;
const rect = box => Array.isArray(box) && box.length === 4 && box.every(finite) &&
  box[0] >= 0 && box[1] >= 0 && box[2] > 0 && box[3] > 0 && box[0] + box[2] <= 1 && box[1] + box[3] <= 1;

export function validate(doc) {
  // New scene timelines do not need legacy overlays. Preserve the old contract
  // for overlay-only documents, and normalize only an omitted editorial field.
  if (Object.hasOwn(doc, 'scenes') && !Object.hasOwn(doc, 'overlays')) doc = {...doc, overlays: []};
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
    if (cue.type === 'browser' && cue.image && !hasText(cue.image)) fail('browser image path must be a non-empty string');
    if (doc.scenes && cue.type === 'browser' && !hasText(cue.image)) fail('Editorial browser overlays require a real image; empty placeholders are unsupported');
    if (cue.type === 'code' && (!hasText(cue.code) || cue.code.split('\n').length > 8)) fail('code needs at most eight lines');
    if (['diagram', 'bullet-list'].includes(cue.type) && (!Array.isArray(cue.items) || cue.items.length < 1 || cue.items.length > 3 || !cue.items.every(hasText))) fail('Use one to three short items');
    if (cue.type === 'number' && !(hasText(cue.value) || finite(cue.value))) fail('number needs a value');
    if (cue.type === 'comparison' && ![cue.left, cue.right].every(s => s && hasText(s.title) && hasText(s.text))) fail('comparison needs left/right title and text');
  }
  for (const cue of doc.motions ?? []) {
    interval(cue);
    if (![cue.from ?? 1, cue.to ?? 1.025].every(n => finite(n) && n >= 1 && n <= 1.08)) fail('Use subtle zoom from 1 to at most 1.08');
  }
  return validateEditorial(doc);
}

function stamp(t) {
  const ms = Math.round(t * 1000);
  return `${String(Math.floor(ms/3600000)).padStart(2,'0')}:${String(Math.floor(ms/60000)%60).padStart(2,'0')}:${String(Math.floor(ms/1000)%60).padStart(2,'0')},${String(ms%1000).padStart(3,'0')}`;
}

async function main() {
  const [timeline, output, ...flags] = process.argv.slice(2);
  const usage = 'Usage: node render.mjs timeline.json output.mp4 [--validate-only | --audit-only | --stills directory]';
  if (!timeline || !output) fail(usage);
  let mode = 'render';
  let stillDirectory;
  for (let i = 0; i < flags.length; i++) {
    if (mode !== 'render') fail(usage);
    if (flags[i] === '--validate-only') mode = 'validate';
    else if (flags[i] === '--audit-only') mode = 'audit';
    else if (flags[i] === '--stills' && flags[i + 1] && !flags[i + 1].startsWith('--')) {
      mode = 'stills';
      stillDirectory = path.resolve(flags[++i]);
    } else fail(usage);
  }
  if (!output.endsWith('.mp4')) fail('Use an .mp4 output path');
  const input = path.resolve(timeline);
  const target = path.resolve(output);
  const subtitle = target.slice(0, -4) + '.srt';
  let doc;
  let warnings;
  const assets = new Map();
  async function resolveAsset(value) {
    if (!hasText(value) || /^(?:[a-z][a-z\d+.-]*:|\/\/)/i.test(value)) fail('Stage media locally before rendering');
    const source = path.resolve(path.dirname(input), value);
    const stat = await fs.stat(source);
    if (!stat.isFile() || stat.size === 0) fail(`Not a nonempty media file: ${source}`);
    if (!assets.has(source)) assets.set(source, `asset-${assets.size}${path.extname(source)}`);
    return assets.get(source);
  }
  try {
    doc = validate(JSON.parse(await fs.readFile(input, 'utf8')));
    warnings = auditEditorial(doc);
    for (const key of ['audio', 'video', 'image', 'fontFile']) if (doc[key]) doc[key] = await resolveAsset(doc[key]);
    for (const cue of doc.overlays) if (cue.image) cue.image = await resolveAsset(cue.image);
    await mapEditorialAssets(doc, resolveAsset);
  } catch (error) {
    if (mode !== 'audit') throw error;
    console.log(JSON.stringify({valid: false, errors: [error.message], warnings: warnings ?? [], qualityAssessed: false}, null, 2));
    process.exitCode = 1;
    return;
  }
  if (doc.fontFile) doc.fontFamily = 'VideoFont, sans-serif';
  if (mode === 'validate') { console.log('Timeline and local assets validated'); return; }
  if (mode === 'audit') {
    console.log(JSON.stringify({valid: true, errors: [], warnings, qualityAssessed: false,
      localAssets: assets.size, stillPoints: editorialStillPoints(doc)}, null, 2));
    return;
  }
  if (mode === 'render') {
    for (const name of [target, subtitle]) {
      const exists = await fs.access(name).then(() => true, () => false);
      if (exists) fail(`Output already exists: ${name}`);
    }
    await fs.mkdir(path.dirname(target), {recursive: true});
  } else {
    // Reserve a fresh directory, so a preview can never overwrite previous evidence.
    await fs.mkdir(path.dirname(stillDirectory), {recursive: true});
    await fs.mkdir(stillDirectory);
  }
  const tmp = await fs.mkdtemp(path.join(os.tmpdir(), 'narrated-motion-'));
  try {
    const [{bundle}, {renderMedia, renderStill, selectComposition}] = await Promise.all([
      import('@remotion/bundler'), import('@remotion/renderer'),
    ]);
    const publicDir = path.join(tmp, 'public');
    await fs.mkdir(publicDir);
    for (const [source, name] of assets) await fs.copyFile(source, path.join(publicDir, name));
    const root = path.dirname(fileURLToPath(import.meta.url));
    const serveUrl = await bundle({entryPoint: path.join(root, 'src/index.jsx'), publicDir, outDir: path.join(tmp, 'bundle')});
    const browserExecutable = process.env.REMOTION_BROWSER_EXECUTABLE || undefined;
    const composition = await selectComposition({serveUrl, id: 'NarratedVideo', inputProps: doc, browserExecutable});
    if (mode === 'stills') {
      const points = editorialStillPoints(doc);
      const manifest = [];
      for (const [index, point] of points.entries()) {
        const name = `${String(index + 1).padStart(3, '0')}-frame-${String(point.frame).padStart(6, '0')}.png`;
        const outputLocation = path.join(stillDirectory, name);
        await renderStill({serveUrl, composition, inputProps: doc, frame: point.frame,
          imageFormat: 'png', output: outputLocation, overwrite: false, browserExecutable});
        manifest.push({...point, file: name});
      }
      await fs.writeFile(path.join(stillDirectory, 'manifest.json'), JSON.stringify({timeline: input,
        fps: doc.fps, width: composition.width, height: composition.height, qualityAssessed: false,
        warnings, frames: manifest}, null, 2) + '\n', {flag: 'wx'});
      console.log(JSON.stringify({stills: stillDirectory, frames: manifest.length, warnings}));
      return;
    }
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
