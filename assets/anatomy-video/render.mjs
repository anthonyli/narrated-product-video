import { writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { Resvg } from '@resvg/resvg-js';

const [scenePath, outputPath, ...args] = process.argv.slice(2);
if (!scenePath || !outputPath) throw new Error('Usage: node render.mjs scene.mjs out.mp4|stills [--start=0 --end=5 --audio=voice.wav --times=0,2]');
const opts = Object.fromEntries(args.map(a => a.replace(/^--/, '').split('=')));
const scene = await import(pathToFileURL(resolve(scenePath)).href);
const { width, height, fps, duration, renderFrame } = scene;
if (![width, height, fps, duration].every(x => Number.isFinite(x) && x > 0) || typeof renderFrame !== 'function') throw new Error('Invalid scene metadata');
if (width % 2 || height % 2) throw new Error('H.264 dimensions must be even');
const start = Number(opts.start ?? 0), end = Number(opts.end ?? duration);
if (!(start >= 0 && end > start && end <= duration + 1e-6)) throw new Error('Invalid time range');
const fontFiles = (scene.fontFiles ?? []).map(p => resolve(dirname(resolve(scenePath)), p));
const raster = t => new Resvg(renderFrame(t), { font: { fontFiles, loadSystemFonts: fontFiles.length === 0, defaultFontFamily: scene.fontFamily ?? 'sans-serif' } }).render().asPng();
if (opts.times) {
  mkdirSync(outputPath, { recursive: true });
  for (const t of opts.times.split(',').map(Number)) {
    if (!Number.isFinite(t) || t < 0 || t >= duration) throw new Error(`Invalid still time ${t}`);
    writeFileSync(join(outputPath, `${t.toFixed(3)}.png`), raster(t));
  }
  console.log('STILLS_OK', outputPath);
} else {
  mkdirSync(dirname(resolve(outputPath)), { recursive: true });
  const frames = Math.ceil((end - start) * fps - 1e-8);
  const ffargs = ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(fps), '-vcodec', 'png', '-i', 'pipe:0'];
  if (opts.audio) ffargs.push('-ss', String(start), '-i', resolve(opts.audio), '-map', '0:v:0', '-map', '1:a:0');
  ffargs.push('-c:v', 'libx264', '-preset', 'fast', '-crf', '19', '-pix_fmt', 'yuv420p', '-threads', '2');
  if (opts.audio) ffargs.push('-c:a', 'aac', '-ar', '48000', '-b:a', '192k');
  ffargs.push('-t', String(frames / fps), '-movflags', '+faststart', outputPath);
  const ff = spawn(process.env.FFMPEG_BIN || 'ffmpeg', ffargs, { stdio: ['pipe', 'inherit', 'inherit'] });
  const completion = once(ff, 'close');
  let pipeError;
  ff.stdin.on('error', error => { pipeError = error; });
  for (let i = 0; i < frames; i++) {
    if (pipeError) throw pipeError;
    if (!ff.stdin.write(raster(Math.min(start + i / fps, duration - 1e-9)))) await once(ff.stdin, 'drain');
    if (i % (fps * 5) === 0) console.log(`FRAME ${i}/${frames} t=${(start + i / fps).toFixed(2)}`);
  }
  ff.stdin.end();
  const [code] = await completion;
  if (code !== 0) throw new Error(`FFmpeg exited ${code}`);
  console.log('VIDEO_OK', outputPath, `${frames} frames`);
}
