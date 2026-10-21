// Authoring contract shared by CLI validation, audit reports and preview selection.
// These checks establish renderability and surface editorial risks, not visual quality.
const finite = value => typeof value === 'number' && Number.isFinite(value);
const text = value => typeof value === 'string' && value.trim().length > 0;
const own = (object, key) => Object.hasOwn(object, key);
const fail = (where, message) => { throw new Error(`${where}: ${message}`); };
const common = ['id', 'start', 'end', 'kind', 'title', 'eyebrow', 'summary', 'bg', 'accent', 'sourceLabel'];
const kinds = {
  hero: ['lead', 'focus', 'items', 'image'],
  compare: ['before', 'after', 'revealAt'],
  flow: ['nodes', 'edges', 'levels'],
  bars: ['items', 'maxValue', 'unit', 'note'],
  demo: ['states'],
};

function object(value, where, keys) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) fail(where, 'must be an object');
  for (const key of Object.keys(value)) if (!keys.includes(key)) fail(`${where}.${key}`, 'unsupported field');
}
function requiredText(value, where) { if (!text(value)) fail(where, 'must be nonempty text'); }
function optionalText(value, where, keys) {
  for (const key of keys) if (own(value, key)) requiredText(value[key], `${where}.${key}`);
}
function list(value, where, min, max) {
  if (!Array.isArray(value) || value.length < min || value.length > max) fail(where, `must contain ${min}–${max} items`);
}
function time(value, where, duration) {
  if (!finite(value) || value < 0 || value >= duration) fail(where, 'must be finite scene-local seconds inside the scene');
}
function rect(value, where) {
  if (!Array.isArray(value) || value.length !== 4 || !value.every(finite) ||
      value[0] < 0 || value[1] < 0 || value[2] <= 0 || value[3] <= 0 ||
      value[0] + value[2] > 1 + 1e-9 || value[1] + value[3] > 1 + 1e-9) {
    fail(where, 'must be [x,y,width,height] within normalized 0–1 bounds');
  }
}
function ordered(items, where, duration, strict = false) {
  let previous = -1;
  items.forEach((item, index) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) fail(`${where}[${index}]`, 'must be an object');
    time(item.at, `${where}[${index}].at`, duration);
    if (strict ? item.at <= previous : item.at < previous) fail(where, 'must be ordered by local at time');
    previous = item.at;
  });
}

export function validateEditorial(doc) {
  if (!own(doc, 'scenes')) return doc;
  if (doc.aspect !== '16:9') fail('scenes', 'editorial scenes currently support 16:9 only');
  for (const key of ['video', 'image', 'videoBox', 'videoFit', 'videoPosition', 'cardBox']) {
    if (own(doc, key)) fail(key, 'is a legacy layout field and is not rendered in editorial mode');
  }
  for (const key of ['overlays', 'motions']) if (own(doc, key) && (!Array.isArray(doc[key]) || doc[key].length)) fail(key, 'must be absent or empty in editorial mode; author changes in scenes');
  list(doc.scenes, 'scenes', 1, 1000);
  const ids = new Set();
  let previousEnd = 0;
  for (const [index, scene] of doc.scenes.entries()) {
    const where = `scenes[${index}]`;
    if (!scene || !own(kinds, scene.kind)) fail(where, 'unknown scene kind');
    object(scene, where, [...common, ...kinds[scene.kind]]);
    requiredText(scene.id, `${where}.id`);
    if (ids.has(scene.id)) fail(`${where}.id`, 'must be unique');
    ids.add(scene.id);
    requiredText(scene.title, `${where}.title`);
    optionalText(scene, where, ['eyebrow', 'summary', 'bg', 'accent', 'sourceLabel']);
    if (!finite(scene.start) || !finite(scene.end) || scene.start < 0 || scene.end <= scene.start || scene.end > doc.duration + .001) fail(where, 'invalid scene interval');
    if (Math.abs(scene.start - previousEnd) > .001) fail(where, 'scenes must be ordered and cover the timeline without gaps or overlaps');
    if (Math.round(scene.start * doc.fps) !== Math.round(previousEnd * doc.fps)) fail(where, 'rounded frame boundaries must be contiguous');
    if (Math.round(scene.end * doc.fps) <= Math.round(scene.start * doc.fps)) fail(where, 'scene must occupy at least one frame');
    previousEnd = scene.end;
    const duration = scene.end - scene.start;
    if (scene.kind === 'hero') {
      requiredText(scene.focus, `${where}.focus`);
      optionalText(scene, where, ['lead', 'image']);
      if (!!scene.image === own(scene, 'items')) fail(where, 'hero needs exactly one of image or items');
      if (own(scene, 'items')) {
        list(scene.items, `${where}.items`, 1, 3);
        scene.items.forEach((item, i) => {
          object(item, `${where}.items[${i}]`, ['label', 'detail', 'at']);
          requiredText(item.label, `${where}.items[${i}].label`);
          optionalText(item, `${where}.items[${i}]`, ['detail']);
        });
        ordered(scene.items, `${where}.items`, duration);
      }
    } else if (scene.kind === 'compare') {
      time(scene.revealAt, `${where}.revealAt`, duration);
      if (scene.revealAt <= 0) fail(`${where}.revealAt`, 'must leave time to see the before state');
      for (const side of ['before', 'after']) {
        const panel = scene[side];
        object(panel, `${where}.${side}`, ['label', 'title', 'text', 'image', 'items']);
        requiredText(panel.label, `${where}.${side}.label`);
        optionalText(panel, `${where}.${side}`, ['title', 'text', 'image']);
        if (own(panel, 'items')) {
          list(panel.items, `${where}.${side}.items`, 1, 5);
          panel.items.forEach((item, i) => requiredText(item, `${where}.${side}.items[${i}]`));
        }
        if (!!panel.image === own(panel, 'items')) fail(`${where}.${side}`, 'needs exactly one of image or items to make the comparison visible');
      }
    } else if (scene.kind === 'flow') {
      list(scene.nodes, `${where}.nodes`, 2, 6);
      list(scene.edges, `${where}.edges`, 1, 15);
      const nodes = new Map();
      scene.nodes.forEach((node, i) => {
        object(node, `${where}.nodes[${i}]`, ['id', 'label', 'detail', 'at']);
        requiredText(node.id, `${where}.nodes[${i}].id`);
        requiredText(node.label, `${where}.nodes[${i}].label`);
        optionalText(node, `${where}.nodes[${i}]`, ['detail']);
        if (nodes.has(node.id)) fail(`${where}.nodes[${i}].id`, 'duplicate node id');
        nodes.set(node.id, node);
      });
      ordered(scene.nodes, `${where}.nodes`, duration);
      const edgeIds = new Set();
      scene.edges.forEach((edge, i) => {
        const edgeWhere = `${where}.edges[${i}]`;
        object(edge, edgeWhere, ['from', 'to', 'label', 'at']);
        requiredText(edge.from, `${edgeWhere}.from`);
        requiredText(edge.to, `${edgeWhere}.to`);
        optionalText(edge, edgeWhere, ['label']);
        if (!nodes.has(edge.from) || !nodes.has(edge.to)) fail(edgeWhere, 'edge endpoints must reference existing nodes');
        if (edge.from === edge.to) fail(edgeWhere, 'self edges are unsupported');
        const edgeId = JSON.stringify([edge.from, edge.to]);
        if (edgeIds.has(edgeId)) fail(edgeWhere, 'duplicate edge');
        edgeIds.add(edgeId);
        time(edge.at, `${edgeWhere}.at`, duration);
      });
      if (own(scene, 'levels')) {
        list(scene.levels, `${where}.levels`, 1, 4);
        const seen = new Set();
        for (const [levelIndex, level] of scene.levels.entries()) {
          list(level, `${where}.levels[${levelIndex}]`, 1, 3);
          for (const id of level) {
            if (!nodes.has(id) || seen.has(id)) fail(`${where}.levels`, 'must contain every node id exactly once');
            seen.add(id);
          }
        }
        if (seen.size !== nodes.size) fail(`${where}.levels`, 'must contain every node id exactly once');
      }
    } else if (scene.kind === 'bars') {
      requiredText(scene.unit, `${where}.unit`);
      requiredText(scene.sourceLabel, `${where}.sourceLabel`);
      optionalText(scene, where, ['note']);
      list(scene.items, `${where}.items`, 1, 5);
      scene.items.forEach((item, i) => {
        object(item, `${where}.items[${i}]`, ['label', 'value', 'displayValue', 'at', 'color']);
        requiredText(item.label, `${where}.items[${i}].label`);
        optionalText(item, `${where}.items[${i}]`, ['displayValue', 'color']);
        if (!finite(item.value) || item.value < 0) fail(`${where}.items[${i}].value`, 'must be a finite nonnegative number');
      });
      ordered(scene.items, `${where}.items`, duration);
      const largest = Math.max(...scene.items.map(item => item.value));
      if (largest <= 0) fail(where, 'bar chart needs at least one positive value');
      if (own(scene, 'maxValue') && (!finite(scene.maxValue) || scene.maxValue <= 0 || scene.maxValue < largest)) fail(`${where}.maxValue`, 'must be finite, positive and at least the largest value');
    } else if (scene.kind === 'demo') {
      list(scene.states, `${where}.states`, 2, 5);
      ordered(scene.states, `${where}.states`, duration, true);
      if (scene.states[0].at !== 0) fail(`${where}.states[0].at`, 'the initial state must start at zero');
      scene.states.forEach((state, i) => {
        const stateWhere = `${where}.states[${i}]`;
        object(state, stateWhere, ['at', 'label', 'title', 'image', 'fields', 'highlights', 'pointer']);
        requiredText(state.label, `${stateWhere}.label`);
        optionalText(state, stateWhere, ['title', 'image']);
        if (own(state, 'fields')) {
          list(state.fields, `${stateWhere}.fields`, 1, 5);
          state.fields.forEach((field, fieldIndex) => {
            const fieldWhere = `${stateWhere}.fields[${fieldIndex}]`;
            object(field, fieldWhere, ['label', 'value', 'changed']);
            requiredText(field.label, `${fieldWhere}.label`);
            requiredText(field.value, `${fieldWhere}.value`);
            if (own(field, 'changed') && typeof field.changed !== 'boolean') fail(`${fieldWhere}.changed`, 'must be boolean');
          });
        }
        if (!!state.image === own(state, 'fields')) fail(stateWhere, 'needs exactly one of image or fields, not an empty browser placeholder or ignored content');
        if (own(state, 'highlights')) {
          list(state.highlights, `${stateWhere}.highlights`, 1, 6);
          state.highlights.forEach((highlight, highlightIndex) => {
            const highlightWhere = `${stateWhere}.highlights[${highlightIndex}]`;
            object(highlight, highlightWhere, ['box', 'label']);
            rect(highlight.box, `${highlightWhere}.box`);
            optionalText(highlight, highlightWhere, ['label']);
          });
        }
        if (own(state, 'pointer')) {
          object(state.pointer, `${stateWhere}.pointer`, ['x', 'y', 'label']);
          for (const axis of ['x', 'y']) if (!finite(state.pointer[axis]) || state.pointer[axis] < 0 || state.pointer[axis] > 1) fail(`${stateWhere}.pointer.${axis}`, 'must be finite within 0–1');
          optionalText(state.pointer, `${stateWhere}.pointer`, ['label']);
        }
      });
    }
  }
  if (Math.abs(previousEnd - doc.duration) > .001) fail('scenes', 'must cover the complete final-audio duration');
  return doc;
}

// Deliberately visit only media fields defined above; arbitrary nested "image" keys are invalid.
function imageEntries(doc) {
  return (doc.scenes ?? []).flatMap((scene, i) => {
    const entries = [];
    const add = (holder, key, where) => { if (holder?.[key]) entries.push({holder, key, path: where, value: holder[key], sceneId: scene.id}); };
    add(scene, 'image', `scenes[${i}].image`);
    for (const side of ['before', 'after']) add(scene[side], 'image', `scenes[${i}].${side}.image`);
    scene.states?.forEach((state, j) => add(state, 'image', `scenes[${i}].states[${j}].image`));
    return entries;
  });
}
export function editorialAssetPaths(doc) {
  return imageEntries(doc).map(({path, value, sceneId}) => ({path, value, sceneId}));
}
export async function mapEditorialAssets(doc, mapper) {
  for (const {holder, key, path, value} of imageEntries(doc)) holder[key] = await mapper(value, path);
  return doc;
}

function eventTimes(scene) {
  if (scene.kind === 'compare') return [0, scene.revealAt];
  if (scene.kind === 'flow') return [0, ...scene.nodes.map(node => node.at), ...scene.edges.map(edge => edge.at)];
  if (scene.kind === 'demo') return scene.states.map(state => state.at);
  return [0, ...(scene.items ?? []).map(item => item.at)];
}
export function editorialStillPoints(doc) {
  const scenes = doc.scenes ?? [{id: 'legacy', start: 0, end: doc.duration, kind: 'legacy'}];
  const seen = new Set();
  const points = [];
  for (const [sceneIndex, scene] of scenes.entries()) {
    const length = scene.end - scene.start;
    const times = [...new Set(eventTimes(scene))].sort((a, b) => a - b);
    const picks = times.map((at, i) => ({at: Math.min(at + .8, at + ((times[i + 1] ?? length) - at) / 2), reason: i === 0 ? 'first-content' : 'state-change'}));
    picks.push({at: Math.max(0, length - .5), reason: 'settled-end'});
    for (const pick of picks) {
      const first = Math.round(scene.start * doc.fps);
      const last = Math.max(first, (sceneIndex === scenes.length - 1 ? Math.ceil(doc.duration * doc.fps) : Math.round(scene.end * doc.fps)) - 1);
      const frame = Math.max(first, Math.min(last, Math.round((scene.start + pick.at) * doc.fps), Math.ceil(doc.duration * doc.fps) - 1));
      if (seen.has(frame)) continue;
      seen.add(frame);
      points.push({sceneId: scene.id, frame, time: frame / doc.fps, reason: pick.reason});
    }
  }
  return points.sort((a, b) => a.frame - b.frame);
}

export function auditEditorial(doc) {
  const warnings = [];
  const add = (code, sceneId, message) => warnings.push({code, ...(sceneId ? {sceneId} : {}), message});
  if (!doc.scenes) {
    add('LEGACY_LAYOUT', null, 'Legacy overlays are valid; this audit does not establish a varied editorial sequence. Review rendered frames.');
    return warnings;
  }
  const kindDuration = new Map();
  const imageDuration = new Map();
  for (const scene of doc.scenes) {
    const duration = scene.end - scene.start;
    kindDuration.set(scene.kind, (kindDuration.get(scene.kind) ?? 0) + duration);
    const times = [...new Set([...eventTimes(scene), duration])].sort((a, b) => a - b);
    let largestHold = 0;
    for (let i = 1; i < times.length; i++) largestHold = Math.max(largestHold, times[i] - times[i - 1]);
    if (largestHold > 6) add('LONG_STATIC_HOLD', scene.id, `Content has a ${largestHold.toFixed(1)}s interval without an authored state change; check it against the narration.`);
    if (scene.kind === 'compare' && (!scene.before.image || !scene.after.image)) add('TEXT_COMPARISON', scene.id, 'One or both comparison panels use text lists. Confirm these make the actual difference observable.');
    if (scene.kind === 'demo') {
      const signatures = scene.states.map(state => JSON.stringify({image: state.image, fields: state.fields?.map(({label, value}) => ({label, value}))}));
      if (new Set(signatures).size < 2) add('NO_DEMO_CONTENT_CHANGE', scene.id, 'Demo states repeat the same image/field values; labels, pointers or highlights alone do not show a completed operation.');
      if (scene.states.every(state => !state.image)) add('SCHEMATIC_DEMO', scene.id, 'This demo uses modeled fields. Label it as a schematic/prototype and do not present it as recorded product evidence.');
      scene.states.forEach((state, i) => {
        if (!state.image) return;
        const hold = (scene.states[i + 1]?.at ?? duration) - state.at;
        imageDuration.set(state.image, (imageDuration.get(state.image) ?? 0) + hold);
      });
    } else if (scene.kind === 'compare') {
      if (scene.before.image) imageDuration.set(scene.before.image, (imageDuration.get(scene.before.image) ?? 0) + duration);
      if (scene.after.image && scene.after.image !== scene.before.image) imageDuration.set(scene.after.image, (imageDuration.get(scene.after.image) ?? 0) + duration - scene.revealAt);
    } else {
      const images = new Set(editorialAssetPaths({scenes: [scene]}).map(entry => entry.value));
      for (const value of images) imageDuration.set(value, (imageDuration.get(value) ?? 0) + duration);
    }
    if (scene.kind === 'bars') add('VERIFY_CHART_SOURCE', scene.id, 'Check the numeric values, units, displayed labels and source against the underlying evidence; the validator verifies structure, not truth.');
  }
  if (doc.scenes.length >= 3) for (const [kind, duration] of kindDuration) if (duration / doc.duration > .6) add('DOMINANT_SCENE_KIND', null, `${kind} occupies ${Math.round(duration / doc.duration * 100)}% of the video; confirm the repeated composition serves the explanation.`);
  for (const [value, duration] of imageDuration) if (duration > 8 && duration / doc.duration > .5) add('REPEATED_MEDIA', null, `The same image (${value}) is visible during about ${Math.round(Math.min(1, duration / doc.duration) * 100)}% of the video; check for narration that requires different evidence.`);
  return warnings;
}
