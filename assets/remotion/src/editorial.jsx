import React from 'react';
import {AbsoluteFill, Img, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

// Editorial scenes use semantic content and a scene-local clock. The first
// release deliberately supports 16:9 only; legacy overlays retain every aspect.
const INK = '#182922';
const MUTED = '#67736c';
const LINE = '#dbe1d9';
const ease = x => 1 - Math.pow(1 - Math.max(0, Math.min(1, x)), 3);
const reveal = (time, at = 0, duration = .6) => ease((time - at) / duration);
// Persistent idle motion: a tiny, slow vertical float. Pure function of scene
// time, so renders stay deterministic across frames and machines.
const drift = (time, phase = 0, amplitude = 2.5, period = 7.5) =>
  Math.sin(((time + phase) * Math.PI * 2) / period) * amplitude;
const entry = (time, at = 0, distance = 28) => {
  const p = reveal(time, at);
  return {opacity: p,
    transform: `translateY(${(1 - p) * distance}px) scale(${.985 + .015 * p})`};
};
const tint = (color, opacity) => /^#[0-9a-f]{6}$/i.test(color)
  ? `${color}${Math.round(opacity * 255).toString(16).padStart(2, '0')}` : color;
const imageStyle = {width: '100%', height: '100%', objectFit: 'contain', display: 'block'};
const cap = {fontSize: 20, letterSpacing: '.12em', fontWeight: 700};

function Pill({children, accent, filled = false}) {
  return <span style={{display: 'inline-flex', alignItems: 'center', gap: 10,
    padding: '10px 17px', borderRadius: 100, fontSize: 20, fontWeight: 650,
    background: filled ? accent : tint(accent, .085), color: filled ? '#fff' : accent,
    border: `1px solid ${filled ? accent : tint(accent, .15)}`}}>{children}</span>;
}

function WindowChrome({label, accent}) {
  return <div style={{height: 53, display: 'flex', alignItems: 'center', gap: 9,
    padding: '0 22px', borderBottom: `1px solid ${LINE}`, background: '#fbfcfa', flexShrink: 0}}>
    {[0, 1, 2].map(i => <span key={i} style={{width: 10, height: 10, borderRadius: '50%',
      background: i === 2 ? tint(accent, .6) : '#d4dbd3'}}/>)}
    <div style={{fontSize: 18, color: MUTED, marginLeft: 12, whiteSpace: 'nowrap',
      textOverflow: 'ellipsis', overflow: 'hidden'}}>{label}</div>
  </div>;
}

function Pointer({pointer, time, at, accent}) {
  if (!pointer) return null;
  const p = reveal(time, at, .45);
  const ring = Math.max(0, Math.min(1, (time - at - .4) / .65));
  return <div style={{position: 'absolute', left: `${pointer.x * 100}%`,
    top: `${pointer.y * 100}%`, transform: `translate(${(1 - p) * 32}px, ${(1 - p) * 24}px)`,
    opacity: p, zIndex: 4, pointerEvents: 'none'}}>
    <div style={{position: 'absolute', left: -30, top: -30, width: 60, height: 60,
      border: `3px solid ${accent}`, borderRadius: '50%',
      transform: `scale(${.3 + ring * 1.7})`, opacity: (1 - ring) * .7}}/>
    <svg width="36" height="44" viewBox="0 0 36 44" style={{filter: 'drop-shadow(0 2px 3px #0003)'}}>
      <path d="M3 2L31 27L18 29L13 41Z" fill={accent} stroke="#fff" strokeWidth="3" strokeLinejoin="round"/>
    </svg>
    {pointer.label && <span style={{position: 'absolute', top: 31, left: 27,
      whiteSpace: 'nowrap', background: accent, color: 'white', borderRadius: '0 12px 12px 12px',
      padding: '8px 14px', fontSize: 18, fontWeight: 700}}>{pointer.label}</span>}
  </div>;
}

function Hero({scene, time, accent}) {
  return <>
    <div style={{position: 'absolute', left: 110, top: 226, width: 860}}>
      {scene.lead && <div style={{...entry(time, .08), color: MUTED, fontSize: 28,
        marginBottom: 25, fontWeight: 550}}>{scene.lead}</div>}
      <div style={{...entry(time, .12), fontSize: scene.title.length > 20 ? 72 : 88,
        fontWeight: 820, lineHeight: 1.14, letterSpacing: '-.045em', overflowWrap: 'anywhere'}}>{scene.title}</div>
      <div style={{...entry(time, .34), marginTop: 15, fontSize: scene.focus.length > 12 ? 78 : scene.focus.length < 8 ? 142 : 96,
        lineHeight: 1.17, letterSpacing: '-.05em', fontWeight: 850, color: accent,
        overflowWrap: 'anywhere'}}>{scene.focus}</div>
      <div style={{height: 6, width: 122 * reveal(time, .6), background: accent,
        borderRadius: 3, marginTop: 36}}/>
      {scene.summary && <div style={{...entry(time, .58), marginTop: 29, width: 785,
        fontSize: 34, color: MUTED, lineHeight: 1.5}}>{scene.summary}</div>}
    </div>
    <div style={{position: 'absolute', left: 1060, top: 212, width: 748, height: 626,
      opacity: reveal(time, .28), borderRadius: 32, background: '#fff', border: `1px solid ${LINE}`,
      transform: `translateY(${(1 - reveal(time, .28)) * 28 + drift(time, 1.4)}px) scale(${.985 + .015 * reveal(time, .28)})`,
      boxShadow: '0 22px 80px #24372c0c', overflow: 'hidden'}}>
      <WindowChrome label={scene.eyebrow || scene.focus} accent={accent}/>
      {scene.image
        ? <div style={{height: 573, padding: 20, boxSizing: 'border-box'}}>
            <Img src={staticFile(scene.image)} style={imageStyle}/>
          </div>
        : <div style={{padding: '38px 40px'}}>
            <div style={{...cap, color: MUTED, marginBottom: 28}}>01 — {(scene.lead || scene.focus)}</div>
            {(scene.items ?? []).map((item, i) => <div key={i} style={{...entry(time, item.at),
              display: 'flex', alignItems: 'center', gap: 22, marginBottom: 16,
              padding: '18px 22px', borderRadius: 18, border: `1px solid ${i === (scene.items.length - 1) ? tint(accent, .3) : LINE}`,
              background: i === (scene.items.length - 1) ? tint(accent, .065) : '#f9faf7'}}>
              <div style={{height: 48, width: 48, borderRadius: 14, flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: i === (scene.items.length - 1) ? accent : '#e7ece4',
                color: i === (scene.items.length - 1) ? '#fff' : MUTED, fontSize: 24,
                fontWeight: 750}}>{String(i + 1).padStart(2, '0')}</div>
              <div style={{minWidth: 0}}>
                <div style={{fontSize: 36, fontWeight: 750, lineHeight: 1.2}}>{item.label}</div>
                {item.detail && <div style={{fontSize: 26, color: MUTED,
                  lineHeight: 1.4, marginTop: 8}}>{item.detail}</div>}
              </div>
            </div>)}
          </div>}
    </div>
    <svg style={{position: 'absolute', left: 944, top: 495, width: 137, height: 100,
      opacity: reveal(time, .72)}} viewBox="0 0 137 100">
      <path d="M8 52H115M94 29L117 52L94 75" fill="none" stroke={accent}
        strokeWidth="5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  </>;
}

function ComparisonPanel({side, time, at, accent, after}) {
  const p = reveal(time, at);
  return <div style={{opacity: p, height: 505, flex: 1, minWidth: 0,
    background: '#fff', borderRadius: 28, border: `1px solid ${after ? tint(accent, .4) : LINE}`,
    transform: `translateY(${(1 - p) * 28 + drift(time, at + (after ? 2.1 : .7))}px) scale(${.985 + .015 * p})`,
    boxShadow: after ? `0 12px 40px ${tint(accent, .08)}` : 'none', overflow: 'hidden'}}>
    <div style={{height: 74, padding: '0 30px', display: 'flex', alignItems: 'center', gap: 15,
      background: after ? tint(accent, .07) : '#ecefe9', borderBottom: `1px solid ${LINE}`}}>
      <span style={{fontSize: 20, fontWeight: 800, color: after ? accent : MUTED,
        letterSpacing: '.09em'}}>{after ? '02' : '01'}</span>
      <div style={{fontSize: 25, fontWeight: 730, color: after ? accent : MUTED}}>{side.label}</div>
      <div style={{marginLeft: 'auto', width: 26, height: 26, borderRadius: '50%',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: after ? accent : '#d8dfd5', color: after ? 'white' : MUTED, fontSize: 17}}>{after ? '✓' : '−'}</div>
    </div>
    <div style={{padding: '25px 30px', height: 430, boxSizing: 'border-box'}}>
      {side.title && <div style={{fontSize: 34, lineHeight: 1.25, letterSpacing: '-.035em', fontWeight: 780,
        marginBottom: 17}}>{side.title}</div>}
      {side.image ? <div style={{height: side.title ? 280 : 333, background: '#f5f7f2',
        borderRadius: 12, overflow: 'hidden', border: `1px solid ${LINE}`}}>
        <Img src={staticFile(side.image)} style={imageStyle}/>
      </div> : <div style={{display: 'flex', gap: 12, alignItems: 'stretch',
        height: side.title ? 273 : 313}}>
        <div style={{width: 33, flexShrink: 0, position: 'relative'}}>
          <div style={{position: 'absolute', top: 24, bottom: 24, left: 16,
            borderLeft: `2px ${after ? 'solid' : 'dashed'} ${after ? tint(accent, .45) : '#c8d0c5'}`}}/>
        </div>
        <div style={{display: 'grid', gap: 10, flex: 1}}>
          {(side.items ?? []).map((item, i) => <div key={i} style={{...entry(time, at + .16 + i * .12, 12),
            position: 'relative', padding: (side.items?.length ?? 0) <= 3 ? '10px 17px' : '7px 17px', display: 'flex', alignItems: 'center',
            fontSize: (side.items?.length ?? 0) <= 3 ? 33 : (side.items?.length ?? 0) === 4 ? 28 : 24,
            fontWeight: after ? 680 : 500, lineHeight: 1.25,
            borderRadius: 12, border: `1px solid ${after ? tint(accent, .2) : '#e1e5dd'}`,
            background: after ? tint(accent, .045) : '#f4f5f1',
            color: after ? INK : '#80877e', transform: `translateX(${after ? 0 : i % 2 * 16}px)`}}>
            <span style={{position: 'absolute', left: -40, top: '50%', width: 16, height: 16,
              borderRadius: '50%', transform: 'translateY(-50%)', background: after ? accent : '#c9d1c4',
              border: '4px solid white'}}/>
            {item}
          </div>)}
        </div>
      </div>}
      {side.text && <div style={{color: MUTED, fontSize: 26, marginTop: 16, lineHeight: 1.3}}>{side.text}</div>}
    </div>
  </div>;
}

function Compare({scene, time, accent}) {
  return <div style={{position: 'absolute', left: 110, right: 110, top: 345,
    display: 'flex', gap: 112, alignItems: 'center'}}>
    <ComparisonPanel side={scene.before} time={time} at={.15} accent={accent}/>
    <div style={{position: 'absolute', left: '50%', top: 223, transform: 'translateX(-50%)',
      opacity: reveal(time, scene.revealAt), width: 60, height: 60, borderRadius: '50%',
      display: 'flex', justifyContent: 'center', alignItems: 'center',
      background: accent, color: 'white', fontSize: 32}}>→</div>
    <ComparisonPanel side={scene.after} time={time} at={scene.revealAt} accent={accent} after/>
  </div>;
}

function Flow({scene, time, accent}) {
  const levels = scene.levels ?? scene.nodes.map(node => [node.id]);
  const rows = Math.max(...levels.map(level => level.length));
  const nodeWidth = Math.min(420, (1700 - (levels.length - 1) * 75) / levels.length);
  const nodeHeight = rows >= 3 ? 148 : rows === 2 ? 210 : 260;
  const dense = rows >= 3 || nodeWidth < 280;
  const positions = Object.fromEntries(levels.flatMap((level, col) => level.map((id, row) => [id, {
    x: levels.length === 1 ? 850 : nodeWidth / 2 + col * (1700 - nodeWidth) / (levels.length - 1),
    y: 258 + (row - (level.length - 1) / 2) * (nodeHeight + 30),
  }])));
  const markerId = `arrow-${scene.id.replace(/[^a-zA-Z0-9_-]/g, '-')}`;
  return <div style={{position: 'absolute', top: 324, left: 110, width: 1700, height: 530}}>
    <svg viewBox="0 0 1700 530" style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
      <defs><marker id={markerId} markerWidth="10" markerHeight="10" refX="7" refY="4" orient="auto">
        <path d="M0 0L8 4L0 8" fill="none" stroke={accent} strokeWidth="1.7"/>
      </marker></defs>
      {(scene.edges ?? []).map((edge, i) => {
        const from = positions[edge.from]; const to = positions[edge.to];
        if (!from || !to) return null;
        const forward = to.x >= from.x;
        const x1 = from.x + (forward ? 1 : -1) * (nodeWidth / 2 + 3);
        const x2 = to.x - (forward ? 1 : -1) * (nodeWidth / 2 + 14);
        const middle = (x1 + x2) / 2;
        const d = `M${x1} ${from.y}C${middle} ${from.y},${middle} ${to.y},${x2} ${to.y}`;
        const p = reveal(time, edge.at, .7);
        return <g key={i} opacity={p}>
          <path d={d} fill="none" stroke={tint(accent, .7)} strokeWidth="3" pathLength="1"
            strokeDasharray="1" strokeDashoffset={1 - p} markerEnd={p > .95 ? `url(#${markerId})` : undefined}/>
          {edge.label && <g transform={`translate(${middle},${(from.y + to.y) / 2 - 27})`}>
            <rect x={-edge.label.length * 13 - 12} y="-20" width={edge.label.length * 26 + 24}
              height="40" rx="8" fill={scene.bg ?? '#f5f6f0'}/>
            <text textAnchor="middle" dominantBaseline="middle" fill={MUTED} fontSize={dense ? 20 : 25} fontWeight="600">{edge.label}</text>
          </g>}
        </g>;
      })}
    </svg>
    {scene.nodes.map((node, i) => {
      const pos = positions[node.id]; if (!pos) return null;
      const p = reveal(time, node.at);
      const isLast = levels[levels.length - 1].includes(node.id);
      return <div key={node.id} style={{position: 'absolute', left: pos.x - nodeWidth / 2,
        top: pos.y - nodeHeight / 2, width: nodeWidth, height: nodeHeight, boxSizing: 'border-box',
        padding: dense ? '18px 23px' : rows === 2 ? '23px 28px' : '30px 31px',
        display: 'flex', flexDirection: 'column', justifyContent: 'center',
        background: isLast ? accent : '#fff', borderRadius: 24,
        border: `1.5px solid ${isLast ? accent : LINE}`, color: isLast ? '#fff' : INK,
        boxShadow: isLast ? `0 12px 35px ${tint(accent, .13)}` : '0 6px 20px #21352805',
        opacity: p, transform: `translateY(${(1 - p) * 22 + drift(time, i * .8)}px) scale(${.97 + .03 * p})`}}>
        <div style={{width: 34, height: 4, borderRadius: 2, flexShrink: 0,
          background: isLast ? '#ffffffa3' : tint(accent, .45), marginBottom: dense ? 10 : 22}}/>
        <div style={{fontSize: dense ? 29 : rows === 2 ? 36 : 42, lineHeight: 1.2,
          letterSpacing: '-.025em', fontWeight: 780}}>{node.label}</div>
        {node.detail && <div style={{fontSize: dense ? 20 : rows === 2 ? 24 : 27, lineHeight: 1.4,
          color: isLast ? '#ffffffe0' : MUTED, marginTop: dense ? 9 : 17}}>{node.detail}</div>}
      </div>;
    })}
  </div>;
}

function Bars({scene, time, accent}) {
  const max = scene.maxValue ?? Math.max(...scene.items.map(item => item.value));
  const rowHeight = Math.min(109, (515 - 64 - 42 - (scene.note ? 63 : 0)) / scene.items.length);
  const graphWidth = 1120;
  return <div style={{position: 'absolute', left: 110, right: 110, top: 343,
    padding: '32px 43px 30px', background: '#fff', border: `1px solid ${LINE}`, borderRadius: 28}}>
    <div style={{marginLeft: 253, marginBottom: 16, height: 26, fontSize: 20,
      color: MUTED, fontVariantNumeric: 'tabular-nums'}}>
      共同尺度 <span style={{marginLeft: 12}}>0 — {Number(max.toPrecision(6)).toLocaleString('en-US')}{scene.unit ? ` ${scene.unit}` : ''}</span>
    </div>
    <div style={{position: 'absolute', left: 296, top: 74, bottom: scene.note ? 75 : 36,
      width: graphWidth, display: 'flex', justifyContent: 'space-between', pointerEvents: 'none'}}>
      {[0, 1, 2, 3, 4].map(i => <div key={i} style={{borderLeft: `1px ${i ? 'dashed' : 'solid'} ${LINE}`}}/>)}
    </div>
    {scene.items.map((item, i) => {
      const p = reveal(time, item.at, .9);
      const color = item.color ?? (i === scene.items.length - 1 ? accent : '#b9c7b6');
      return <div key={i} style={{position: 'relative', height: rowHeight, display: 'flex', alignItems: 'center', gap: 24,
        opacity: reveal(time, item.at, .2)}}>
        <div style={{width: 229, flexShrink: 0, fontSize: 27, lineHeight: 1.3,
          fontWeight: 650}}>{item.label}</div>
        <div style={{position: 'relative', width: graphWidth, height: 44,
          display: 'flex', alignItems: 'center'}}>
          <div style={{position: 'absolute', inset: 0, background: '#eef2eb', borderRadius: '0 9px 9px 0'}}/>
          <div style={{position: 'relative', height: 44, width: Math.max(0, item.value / max) * graphWidth * p,
            background: color, borderRadius: '0 9px 9px 0'}}/>
          <div style={{position: 'absolute', left: item.value / max * graphWidth * p + 22,
            color: i === scene.items.length - 1 ? accent : INK, fontSize: 35, fontWeight: 780,
            fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap'}}>{item.displayValue ?? `${item.value}${scene.unit ?? ''}`}</div>
        </div>
      </div>;
    })}
    {scene.note && <div style={{borderTop: `1px solid ${LINE}`, marginTop: 20,
      paddingTop: 18, fontSize: 21, lineHeight: 1.4, color: MUTED}}>{scene.note}</div>}
  </div>;
}

function Demo({scene, time, accent}) {
  const index = Math.max(0, scene.states.findLastIndex(state => state.at <= time));
  const state = scene.states[index];
  const at = state.at;
  return <div style={{position: 'absolute', top: 340, left: 110, right: 110, height: 515,
    display: 'flex', gap: 58}}>
    <div style={{width: 365, paddingTop: 12, flexShrink: 0}}>
      {scene.states.map((step, i) => {
        const active = i === index;
        const complete = i < index;
        return <div key={i} style={{display: 'flex', alignItems: 'flex-start', gap: 20,
          marginBottom: 30, opacity: i > index ? .4 : 1}}>
          <div style={{width: 43, height: 43, borderRadius: '50%', flexShrink: 0,
            background: active ? accent : complete ? tint(accent, .12) : '#e4e9df',
            color: active ? 'white' : accent, fontSize: 20, fontWeight: 750,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: active ? `0 0 0 7px ${tint(accent, .07)}` : 'none'}}>{complete ? '✓' : String(i + 1).padStart(2, '0')}</div>
          <div style={{paddingTop: 5, fontSize: 27, fontWeight: active ? 780 : 600,
            lineHeight: 1.3, color: active ? INK : MUTED}}>{step.label}</div>
        </div>;
      })}
    </div>
    <div style={{flex: 1, minWidth: 0, background: '#fff', borderRadius: 25,
      border: `1px solid ${LINE}`, boxShadow: '0 16px 60px #24372c0b', overflow: 'hidden',
      transform: `translateY(${drift(time, 1.1)}px)`}}>
      <WindowChrome label={state.title || state.label} accent={accent}/>
      <div style={{position: 'relative', height: 461, background: '#fafbf8', overflow: 'hidden'}}>
        {state.image ? <Img key={state.image} src={staticFile(state.image)} style={imageStyle}/> :
          <div key={index} style={{padding: '30px 38px', ...entry(time, at, 10)}}>
            <div style={{display: 'flex', alignItems: 'center', gap: 12, marginBottom: 23}}>
              <div style={{width: 8, height: 30, background: accent, borderRadius: 4}}/>
              <span style={{fontSize: 28, fontWeight: 760}}>{state.title || state.label}</span>
            </div>
            <div style={{display: 'grid', gap: 11}}>
              {(state.fields ?? []).map((field, i) => <div key={i} style={{display: 'flex', alignItems: 'center',
                minHeight: (state.fields?.length ?? 0) <= 3 ? 83 : 52, boxSizing: 'border-box', padding: '9px 22px', border: `1px solid ${field.changed ? tint(accent, .45) : LINE}`,
                borderRadius: 11, background: field.changed ? tint(accent, .07) : '#fff'}}>
                <div style={{fontSize: (state.fields?.length ?? 0) <= 3 ? 24 : 20, width: 190, flexShrink: 0, color: MUTED}}>{field.label}</div>
                <div style={{fontSize: (state.fields?.length ?? 0) <= 3 ? 36 : 25, fontWeight: field.changed ? 740 : 560,
                  color: field.changed ? accent : INK, lineHeight: 1.25}}>{field.value}</div>
                {field.changed && <span style={{marginLeft: 'auto', paddingLeft: 14,
                  color: accent, fontSize: 23}}>✓</span>}
              </div>)}
            </div>
          </div>}
        {(state.highlights ?? []).map((highlight, i) => <div key={`${index}-${i}`} style={{
          position: 'absolute', left: `${highlight.box[0] * 100}%`, top: `${highlight.box[1] * 100}%`,
          width: `${highlight.box[2] * 100}%`, height: `${highlight.box[3] * 100}%`, boxSizing: 'border-box',
          border: `3px solid ${accent}`, borderRadius: 12, background: tint(accent, .055),
          opacity: reveal(time, at + .18), pointerEvents: 'none'}}>
          {highlight.label && <span style={{position: 'absolute', right: 0, top: -30,
            borderRadius: '6px 6px 0 0', background: accent, color: '#fff', padding: '4px 10px',
            fontSize: 17, fontWeight: 650, whiteSpace: 'nowrap'}}>{highlight.label}</span>}
        </div>)}
        <Pointer pointer={state.pointer} time={time} at={at + .18} accent={accent}/>
      </div>
    </div>
  </div>;
}

function EditorialScene({scene, doc, index, count}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const time = frame / fps;
  const accent = scene.accent ?? doc.accent ?? '#257755';
  const bg = scene.bg ?? doc.bg ?? '#f5f6f0';
  const Component = {hero: Hero, compare: Compare, flow: Flow, bars: Bars, demo: Demo}[scene.kind];
  if (!Component) throw new Error(`Unsupported editorial scene kind: ${scene.kind}`);
  // Slow scene-wide push-in on the body: keeps every frame subtly alive like
  // the reference explainers, while header, page number and progress stay fixed.
  const sceneDuration = scene.end - scene.start;
  const zoom = 1 + .018 * ease(Math.min(1, time / Math.max(sceneDuration, 1)));
  return <AbsoluteFill style={{background: bg, color: INK, overflow: 'hidden'}}>
    <AbsoluteFill style={{background: `radial-gradient(ellipse at 94% 0%, ${tint(accent, .08)}, transparent 49%)`}}/>
    <div style={{position: 'absolute', left: 110, right: 110, top: 65,
      display: 'flex', alignItems: 'center', justifyContent: 'space-between', ...entry(time, 0, 10)}}>
      <Pill accent={accent}><span style={{width: 7, height: 7, borderRadius: '50%', background: accent}}/>
        {scene.eyebrow || scene.title}</Pill>
      <span style={{...cap, color: MUTED, fontVariantNumeric: 'tabular-nums'}}>
        <span style={{color: accent}}>{String(index + 1).padStart(2, '0')}</span>
        <span style={{padding: '0 16px', color: '#b8c1b6'}}> / </span>{String(count).padStart(2, '0')}
      </span>
    </div>
    <div style={{position: 'absolute', inset: 0, transform: `scale(${zoom})`}}>
      {scene.kind !== 'hero' && <div style={{position: 'absolute', left: 110, top: 143, right: 110,
        ...entry(time, .07, 20)}}>
        <div style={{fontSize: scene.title.length > 22 ? 62 : 76, lineHeight: 1.18,
          letterSpacing: '-.04em', fontWeight: 820}}>{scene.title}</div>
        {scene.summary && <div style={{marginTop: 24, color: MUTED, fontSize: 29,
          lineHeight: 1.4, maxWidth: 1550}}>{scene.summary}</div>}
      </div>}
      <Component scene={scene} time={time} accent={accent}/>
    </div>
    <div style={{position: 'absolute', left: 110, right: 110, bottom: 35,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: MUTED, fontSize: 18}}>
      <span>{scene.sourceLabel}</span>
      <div style={{display: 'flex', gap: 7}}>{Array.from({length: count}, (_, i) =>
        <div key={i} style={{height: 3, width: i === index ? 56 : 23, borderRadius: 4,
          background: i <= index ? accent : '#d1d9cc', opacity: i < index ? .4 : 1}}/>)}</div>
    </div>
  </AbsoluteFill>;
}

export function EditorialScenes({doc}) {
  const {fps} = useVideoConfig();
  if (doc.aspect !== '16:9') throw new Error('Editorial scenes currently support 16:9 only.');
  return <>{doc.scenes.map((scene, index) => <Sequence key={scene.id}
    from={Math.round(scene.start * fps)}
    durationInFrames={Math.max(1,
      (index === doc.scenes.length - 1 ? Math.ceil(doc.duration * fps) : Math.round(scene.end * fps))
        - Math.round(scene.start * fps))}>
    <EditorialScene scene={scene} doc={doc} index={index} count={doc.scenes.length}/>
  </Sequence>)}</>;
}
