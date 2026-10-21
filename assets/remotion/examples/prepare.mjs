// Stage the public visual examples with an explicitly silent preview soundtrack.
// This is not speech synthesis or a test of narration alignment.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const examples = path.dirname(fileURLToPath(import.meta.url));
const [destination, ...requested] = process.argv.slice(2);
if (!destination || requested.some(name => !['meeting', 'fractions'].includes(name))) {
  throw new Error('Usage: node examples/prepare.mjs output-directory [meeting fractions]');
}
for (const name of requested.length ? requested : ['meeting', 'fractions']) {
  const doc = JSON.parse(await fs.readFile(path.join(examples, `${name}.json`), 'utf8'));
  const dir = path.resolve(destination, name);
  const samples = Math.ceil(doc.duration * 48000);
  const bytes = samples * 2;
  const header = Buffer.alloc(44);
  header.write('RIFF', 0); header.writeUInt32LE(bytes + 36, 4); header.write('WAVEfmt ', 8);
  header.writeUInt32LE(16, 16); header.writeUInt16LE(1, 20); header.writeUInt16LE(1, 22);
  header.writeUInt32LE(48000, 24); header.writeUInt32LE(96000, 28);
  header.writeUInt16LE(2, 32); header.writeUInt16LE(16, 34);
  header.write('data', 36); header.writeUInt32LE(bytes, 40);
  await fs.mkdir(dir, {recursive: true});
  await fs.writeFile(path.join(dir, 'preview-silence.wav'), Buffer.concat([header, Buffer.alloc(bytes)]), {flag: 'wx'});
  await fs.writeFile(path.join(dir, 'motion.json'), JSON.stringify(doc, null, 2) + '\n', {flag: 'wx'});
  console.log(`${name}: ${path.join(dir, 'motion.json')} (silent visual prototype)`);
}
