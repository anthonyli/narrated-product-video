import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {auditEditorial, editorialAssetPaths, editorialStillPoints, mapEditorialAssets, validateEditorial} from '../editorial-contract.mjs';
import {validate} from '../render.mjs';

const hero = () => ({id: 'intro', kind: 'hero', start: 0, end: 8, title: 'A specific question', focus: 'A visible answer', items: [{label: 'Evidence', at: 0}]});
const docFor = scene => ({aspect: '16:9', fps: 30, duration: scene.end, audio: 'narration.wav', captions: [], overlays: [], scenes: [scene]});
const compare = () => ({id: 'comparison', kind: 'compare', start: 0, end: 8, title: 'Show the difference', revealAt: 3,
  before: {label: 'Before', image: 'before.png'}, after: {label: 'After', image: 'after.png'}});
const flow = () => ({id: 'process', kind: 'flow', start: 0, end: 8, title: 'Explain the connection',
  nodes: [{id: 'a', label: 'Input', at: .5}, {id: 'b', label: 'Result', at: 2}],
  edges: [{from: 'a', to: 'b', at: 1.2}], levels: [['a'], ['b']]});
const bars = () => ({id: 'amounts', kind: 'bars', start: 0, end: 8, title: 'Measure the difference', unit: 'seconds', sourceLabel: 'Synthetic example',
  maxValue: 20, items: [{label: 'A', value: 0, at: 0}, {label: 'B', value: 20, at: 2}]});
const demo = () => ({id: 'operation', kind: 'demo', start: 0, end: 8, title: 'Follow the operation',
  states: [{at: 0, label: 'Before', image: 'before.png'}, {at: 3, label: 'After', image: 'after.png',
    pointer: {x: .5, y: .5}, highlights: [{box: [.1, .2, .4, .3]}]}]});
const rejectsChange = (factory, change, pattern) => {
  const doc = docFor(factory());
  change(doc.scenes[0], doc);
  assert.throws(() => validateEditorial(doc), pattern);
};

test('cross-topic fixture timelines use the same contract without topic branches', async () => {
  for (const name of ['meeting', 'fractions']) {
    const doc = JSON.parse(await fs.readFile(new URL(`../examples/${name}.json`, import.meta.url), 'utf8'));
    assert.equal(validateEditorial(doc), doc);
    assert.ok(editorialStillPoints(doc).length > doc.scenes.length);
  }
});

test('legacy documents are unchanged; editorial does not silently discard legacy content', () => {
  const legacy = {aspect: '3:4', overlays: [{type: 'browser'}]};
  assert.equal(validateEditorial(legacy), legacy);
  rejectsChange(hero, (scene, doc) => {doc.aspect = '3:4';}, /16:9/);
  rejectsChange(hero, (scene, doc) => {doc.image = 'ignored.png';}, /legacy layout/);
  rejectsChange(hero, (scene, doc) => {doc.overlays = [{type: 'browser'}];}, /overlays/);
  rejectsChange(hero, (scene, doc) => {doc.motions = [{from: 1, to: 1.02}];}, /motions/);
});

test('the actual render entrypoint accepts editorial timelines without legacy overlays', () => {
  const doc = docFor(hero());
  delete doc.overlays;
  const normalized = validate(doc);
  assert.deepEqual(normalized.overlays, []);
  assert.deepEqual(normalized.scenes, doc.scenes);
  assert.throws(() => validate({...doc, overlays: null}), /must be arrays/);
  const legacy = {...doc}; delete legacy.scenes;
  assert.throws(() => validate(legacy), /must be arrays/);
});

test('scene boundaries cover the final audio without gaps, overlap or invisible intervals', () => {
  const first = hero(); first.end = 4;
  const last = {...hero(), id: 'closing', start: 4, end: 8};
  const doc = {...docFor(last), scenes: [first, last]};
  assert.doesNotThrow(() => validateEditorial(doc));
  for (const start of [3.5, 4.5]) {
    const changed = structuredClone(doc); changed.scenes[1].start = start;
    assert.throws(() => validateEditorial(changed), /gaps or overlaps/);
  }
  rejectsChange(hero, scene => {scene.start = 1;}, /gaps or overlaps/);
  rejectsChange(hero, (scene, doc) => {doc.duration = 9;}, /complete final-audio duration/);
  rejectsChange(hero, (scene, doc) => {scene.end = .001; doc.duration = .001;}, /at least one frame/);
  rejectsChange(hero, scene => {scene.end = Infinity;}, /interval/);
  const duplicate = structuredClone(doc); duplicate.scenes[1].id = first.id;
  assert.throws(() => validateEditorial(duplicate), /unique/);
  const frameGap = structuredClone(doc); frameGap.scenes[0].end = 4 + 1 / 60 - .0001; frameGap.scenes[1].start = 4 + 1 / 60 + .0001;
  assert.throws(() => validateEditorial(frameGap), /rounded frame boundaries/);
});

test('invented animation and misspelled state properties cannot pass as implemented motion', () => {
  rejectsChange(hero, scene => {scene.animation = {type: 'zoom'};}, /unsupported field/);
  rejectsChange(demo, scene => {scene.states[1].cursor = {x: .2, y: .3};}, /unsupported field/);
  rejectsChange(flow, scene => {scene.edges[0].animated = true;}, /unsupported field/);
});

test('local reveal times cannot leak into later scenes', () => {
  rejectsChange(compare, scene => {scene.revealAt = 8;}, /scene-local/);
  rejectsChange(compare, scene => {scene.revealAt = 0;}, /before state/);
  rejectsChange(demo, scene => {scene.states[0].at = 1;}, /zero/);
  rejectsChange(demo, scene => {scene.states[1].at = 0;}, /ordered/);
  rejectsChange(demo, scene => {scene.states[1].at = NaN;}, /scene-local/);
  rejectsChange(hero, scene => {scene.items = [{label: 'B', at: 3}, {label: 'A', at: 2}];}, /ordered/);
  rejectsChange(flow, scene => {scene.edges[0].at = -1;}, /scene-local/);
});

test('workflow relationships must reference unique displayed nodes', () => {
  assert.doesNotThrow(() => validateEditorial(docFor(flow())), 'connector may draw before its target appears');
  rejectsChange(flow, scene => {scene.edges[0].to = 'missing';}, /endpoints/);
  rejectsChange(flow, scene => {scene.nodes[1].id = 'a';}, /duplicate node/);
  rejectsChange(flow, scene => {scene.edges[0].to = 'a';}, /self edges/);
  rejectsChange(flow, scene => {scene.levels = [['a'], ['a']];}, /every node/);
  rejectsChange(flow, scene => {scene.levels = [['a']];}, /every node/);
});

test('bars retain numeric scale meaning and provenance rather than decorative percentages', () => {
  assert.doesNotThrow(() => validateEditorial(docFor(bars())));
  rejectsChange(bars, scene => {scene.items[1].value = '20';}, /finite nonnegative/);
  rejectsChange(bars, scene => {scene.items[1].value = -2;}, /finite nonnegative/);
  rejectsChange(bars, scene => {scene.items[1].value = Infinity;}, /finite nonnegative/);
  rejectsChange(bars, scene => {scene.maxValue = 10;}, /largest value/);
  rejectsChange(bars, scene => {scene.items[1].value = 0;}, /positive value/);
  rejectsChange(bars, scene => {delete scene.sourceLabel;}, /sourceLabel/);
  rejectsChange(bars, scene => {delete scene.unit;}, /unit/);
});

test('empty product evidence and nonfinite or out-of-bounds annotations fail', () => {
  rejectsChange(compare, scene => {scene.after = {label: 'After', text: 'Trust us'};}, /image or items/);
  rejectsChange(demo, scene => {delete scene.states[1].image;}, /empty browser placeholder/);
  rejectsChange(demo, scene => {scene.states[1].pointer.x = Infinity;}, /within 0–1/);
  rejectsChange(demo, scene => {scene.states[1].highlights[0].box = [.8, 0, .3, .2];}, /normalized/);
  rejectsChange(demo, scene => {scene.states[1].highlights[0].box[2] = 0;}, /normalized/);
  rejectsChange(hero, scene => {delete scene.items;}, /exactly one/);
  rejectsChange(hero, scene => {scene.image = 'ignored.png';}, /exactly one/);
  rejectsChange(compare, scene => {scene.after.items = ['ignored'];}, /exactly one/);
  rejectsChange(demo, scene => {scene.states[1].fields = [{label: 'Ignored', value: 'Value'}];}, /exactly one/);
  const modeled = demo(); modeled.states[1] = {at: 3, label: 'Done', fields: [{label: 'Status', value: 'Complete', changed: true}]};
  assert.doesNotThrow(() => validateEditorial(docFor(modeled)));
});

test('all supported nested images are staged, retaining repeated sources and exact paths', async () => {
  const a = {...hero(), image: 'hero.png'};
  delete a.items;
  const b = {...compare(), start: 8, end: 16};
  const c = {...demo(), start: 16, end: 24};
  const doc = {...docFor(c), scenes: [a, b, c]};
  const original = editorialAssetPaths(doc);
  assert.deepEqual(original.map(entry => entry.value), ['hero.png', 'before.png', 'after.png', 'before.png', 'after.png']);
  const visited = [];
  const names = new Map();
  await mapEditorialAssets(doc, async (value, where) => {
    await Promise.resolve();
    visited.push(where);
    if (!names.has(value)) names.set(value, `asset-${names.size}.png`);
    return names.get(value);
  });
  assert.deepEqual(visited, original.map(entry => entry.path));
  assert.deepEqual(editorialAssetPaths(doc).map(entry => entry.value), ['asset-0.png', 'asset-1.png', 'asset-2.png', 'asset-1.png', 'asset-2.png']);
  await assert.rejects(mapEditorialAssets(doc, async () => {throw new Error('missing media');}), /missing media/);
});

test('contact frames include every meaningful state within the composition', () => {
  const doc = docFor(demo());
  const points = editorialStillPoints(doc);
  assert.ok(points.some(point => point.time > 0 && point.time < 3));
  assert.ok(points.some(point => point.time > 3 && point.time < 7));
  assert.ok(points.some(point => point.time >= 7));
  assert.equal(new Set(points.map(point => point.frame)).size, points.length);
  assert.ok(points.every(point => Number.isInteger(point.frame) && point.frame >= 0 && point.frame < doc.duration * doc.fps));
  const tiny = docFor({...hero(), end: 1 / 30});
  assert.deepEqual(editorialStillPoints(tiny).map(point => point.frame), [0]);
});

test('audit reports qualitative risks without confusing them with structural failure', () => {
  const doc = docFor(demo());
  doc.scenes[0].states[1].image = 'before.png';
  assert.doesNotThrow(() => validateEditorial(doc));
  assert.ok(auditEditorial(doc).some(warning => warning.code === 'NO_DEMO_CONTENT_CHANGE'));
  const stillHero = docFor(hero());
  assert.ok(auditEditorial(stillHero).some(warning => warning.code === 'LONG_STATIC_HOLD'));
  assert.ok(auditEditorial(docFor(bars())).some(warning => warning.code === 'VERIFY_CHART_SOURCE'));
  assert.equal(auditEditorial({})[0].code, 'LEGACY_LAYOUT');
});
