import assert from 'node:assert/strict';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';

const file = process.argv[2];
if (!file) throw new Error('Usage: node check-scene.mjs scene.mjs');
const s = await import(pathToFileURL(resolve(file)).href);
const hash = text => createHash('sha256').update(text).digest('hex');
const samples = Array.from({ length: 41 }, (_, i) => s.duration * i / 41);
const frames = samples.map(t => {
  const svg = s.renderFrame(t);
  assert.match(svg, /^<svg\b/);
  assert(!/NaN|Infinity|undefined/.test(svg), `Invalid geometry at ${t}`);
  return hash(svg);
});
for (const i of samples.map((_, i) => i).reverse()) {
  assert.equal(hash(s.renderFrame(samples[i])), frames[i], `Stateful rendering at ${samples[i]}`);
}
assert(new Set(frames).size > 1, 'No visible changes across time');
console.log(JSON.stringify({ status: 'passed', samples: samples.length, reverseSeek: true, finiteGeometry: true, uniqueFrames: new Set(frames).size }));
