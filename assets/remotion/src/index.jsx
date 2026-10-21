import React from 'react';
import {AbsoluteFill, Audio, Composition, Img, OffthreadVideo, Sequence, interpolate,
  registerRoot, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {EditorialScenes} from './editorial';

const sizes = {'16:9': [1920, 1080], '4:3': [1440, 1080], '3:4': [1080, 1440]};
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
const baseFont = '"PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
const rectangle = ([x, y, w, h]) => ({position: 'absolute', left: `${x * 100}%`,
  top: `${y * 100}%`, width: `${w * 100}%`, height: `${h * 100}%`});

function defaults(aspect) {
  return aspect === '3:4'
    ? {video: [.06, .22, .88, .46], card: [.06, .72, .88, .22]}
    : {video: [.04, .18, .54, .68], card: [.62, .18, .35, .68]};
}

// ─── Background ──────────────────────────────────────────────────────────────
// Each `progress` overlay can carry a `bg` field to drive per-chapter color.
// The MotionVideo component reads the active progress overlay at each frame
// and uses its bg/accent as the current theme.
function useTheme(doc) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const time = frame / fps;
  const active = doc.scenes?.length
    ? doc.scenes.find(scene => scene.start <= time && time < scene.end)
    : (doc.overlays ?? []).find(o => o.type === 'progress' && o.start <= time && time < o.end);
  return {
    bg: active?.bg ?? doc.bg ?? '#f5f3ee',
    accent: active?.accent ?? doc.accent ?? '#3b82f6',
  };
}

// ─── Footage (left panel video/image/placeholder) ────────────────────────────
function Footage({doc, accent}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const time = frame / fps;
  const motion = doc.motions?.find(m => time >= m.start && time < m.end);
  const zoom = motion
    ? interpolate(time, [motion.start, motion.end], [motion.from ?? 1, motion.to ?? 1.025], clamp)
    : 1;
  const position = doc.videoBox ?? defaults(doc.aspect).video;
  const style = {width: '100%', height: '100%', objectFit: doc.videoFit ?? 'contain',
    objectPosition: doc.videoPosition ?? '50% 50%', transform: `scale(${zoom})`};
  return (
    <div style={{...rectangle(position), overflow: 'hidden', borderRadius: 20,
      background: '#ffffff', border: '1px solid #e5e5e3',
      boxShadow: '0 2px 16px rgba(0,0,0,0.08)'}}>
      {doc.video ? <OffthreadVideo src={staticFile(doc.video)} muted style={style}/> :
        doc.image ? <Img src={staticFile(doc.image)} style={style}/> :
          <AbsoluteFill style={{background: `linear-gradient(135deg, ${accent}18, ${accent}08)`}}/>}
    </div>
  );
}

// ─── Card ────────────────────────────────────────────────────────────────────
function Card({cue, aspect, accent, box}) {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const duration = Math.round(cue.end * fps) - Math.round(cue.start * fps);
  const enter = spring({frame, fps, config: {damping: 26, stiffness: 180, mass: .7}});
  const fade = interpolate(frame, [Math.max(0, duration - Math.round(fps * .15)), duration], [1, 0], clamp);
  const u = Math.min(1, width / 1440); // scale unit
  const ink = '#17120a';
  const inkMid = '#4a3f32';
  const inkMuted = '#9a8e82';
  const titleStyle = {fontSize: 44 * u, lineHeight: 1.22, fontWeight: 780,
    letterSpacing: '-.03em', overflowWrap: 'anywhere', color: ink};
  const small = {fontSize: 24 * u, color: inkMuted, lineHeight: 1.5};
  const stagger = i => interpolate(frame, [i * 5, i * 5 + 10], [0, 1], clamp);

  // ── chapter-label ──────────────────────────────────────────────────────────
  // Pill at the top-left: colored dot + text. Sits outside the card grid.
  if (cue.type === 'chapter-label') {
    const op = Math.min(enter, fade);
    return (
      <div style={{position: 'absolute',
        left: (cue.box ? `${cue.box[0] * 100}%` : '4%'),
        top:  (cue.box ? `${cue.box[1] * 100}%` : '6%'),
        opacity: op, transform: `translateY(${(1 - enter) * 10}px)`}}>
        <div style={{display: 'inline-flex', alignItems: 'center', gap: 8 * u,
          background: '#ffffff', border: '1.5px solid #e5e5e3',
          borderRadius: 999, padding: `${7 * u}px ${16 * u}px`,
          fontSize: 22 * u, fontWeight: 600, color: ink,
          boxShadow: '0 1px 6px rgba(0,0,0,0.07)'}}>
          <span style={{width: 9 * u, height: 9 * u, borderRadius: '50%',
            background: accent, flexShrink: 0}}/>
          {cue.text}
        </div>
      </div>
    );
  }

  // ── big-title ──────────────────────────────────────────────────────────────
  // Left-aligned, very heavy, no card background — lives directly on canvas.
  if (cue.type === 'big-title') {
    const op = Math.min(enter, fade);
    const pos = cue.box ? rectangle(cue.box) : {
      position: 'absolute', left: '4%', top: '12%', right: '54%'};
    return (
      <div style={{...pos, opacity: op,
        transform: `translateY(${(1 - enter) * 18}px)`}}>
        <div style={{fontSize: 72 * u, fontWeight: 900, color: ink,
          letterSpacing: '-.045em', lineHeight: 1.12,
          overflowWrap: 'anywhere'}}>{cue.text}</div>
        {cue.detail && <div style={{...small, marginTop: 16 * u, fontSize: 26 * u,
          color: inkMid}}>{cue.detail}</div>}
      </div>
    );
  }

  // ── input-bar ─────────────────────────────────────────────────────────────
  // Mimics a chat input bar (used in demo to show a prompt being typed).
  if (cue.type === 'input-bar') {
    const op = Math.min(enter, fade);
    const pos = cue.box ? rectangle(cue.box) : {
      position: 'absolute', left: '58%', top: '10%', right: '3%'};
    return (
      <div style={{...pos, opacity: op,
        transform: `translateY(${(1 - enter) * 12}px)`}}>
        <div style={{display: 'flex', alignItems: 'center', gap: 12 * u,
          background: '#ffffff', border: `1.5px solid ${accent}`,
          borderRadius: 999, padding: `${12 * u}px ${20 * u}px`,
          boxShadow: '0 2px 12px rgba(0,0,0,0.09)'}}>
          <span style={{color: inkMuted, fontSize: 26 * u, fontWeight: 500, flex: 1}}>
            + {cue.text}</span>
          <div style={{width: 40 * u, height: 40 * u, borderRadius: '50%',
            background: ink, display: 'flex', alignItems: 'center',
            justifyContent: 'center', flexShrink: 0}}>
            <span style={{color: '#fff', fontSize: 20 * u, lineHeight: 1}}>↑</span>
          </div>
        </div>
      </div>
    );
  }

  // ── info-card ──────────────────────────────────────────────────────────────
  // White rounded card: optional emoji icon + small label + bold title.
  // Set `active: true` for accent border highlight.
  if (cue.type === 'info-card') {
    const op = Math.min(enter, fade);
    const isActive = cue.active;
    return (
      <div style={{...rectangle(cue.box ?? box ?? defaults(aspect).card),
        boxSizing: 'border-box',
        background: '#ffffff',
        border: `2px solid ${isActive ? accent : '#e5e5e3'}`,
        borderRadius: 18, padding: `${20 * u}px ${24 * u}px`,
        display: 'flex', alignItems: 'center', gap: 18 * u,
        boxShadow: isActive ? `0 0 0 4px ${accent}20` : '0 1px 8px rgba(0,0,0,0.06)',
        opacity: op,
        transform: `translateY(${(1 - enter) * 16}px) scale(${.98 + .02 * enter})`}}>
        {cue.icon && (
          <div style={{width: 52 * u, height: 52 * u, borderRadius: 14,
            background: `${accent}18`, display: 'flex', alignItems: 'center',
            justifyContent: 'center', fontSize: 28 * u, flexShrink: 0}}>
            {cue.icon}
          </div>
        )}
        <div style={{flex: 1, minWidth: 0}}>
          {cue.label && <div style={{...small, fontSize: 21 * u,
            marginBottom: 4 * u}}>{cue.label}</div>}
          <div style={{fontSize: 34 * u, fontWeight: 760, color: ink,
            letterSpacing: '-.025em', overflowWrap: 'anywhere'}}>{cue.text}</div>
        </div>
        {cue.active && (
          <div style={{width: 28 * u, height: 28 * u, borderRadius: '50%',
            background: accent, display: 'flex', alignItems: 'center',
            justifyContent: 'center', flexShrink: 0}}>
            <span style={{color: '#fff', fontSize: 14 * u}}>✓</span>
          </div>
        )}
      </div>
    );
  }

  // ── progress ───────────────────────────────────────────────────────────────
  if (cue.type === 'progress') {
    const progress = interpolate(frame, [0, Math.max(1, duration - 1)], [0, 100], clamp);
    return (
      <div style={{position: 'absolute', left: '4%', right: '4%', bottom: '3.5%', opacity: fade}}>
        <div style={{height: 3, background: 'rgba(0,0,0,0.1)', borderRadius: 4}}>
          <div style={{height: '100%', width: `${progress}%`,
            background: accent, borderRadius: 4}}/>
        </div>
      </div>
    );
  }

  // ── browser ────────────────────────────────────────────────────────────────
  if (cue.type === 'browser') {
    const op = Math.min(enter, fade);
    return (
      <div style={{...rectangle(cue.box ?? box ?? defaults(aspect).card),
        boxSizing: 'border-box', overflow: 'hidden',
        background: '#ffffff', border: '1px solid #e5e5e3', borderRadius: 16,
        boxShadow: '0 4px 24px rgba(0,0,0,0.10)', opacity: op,
        transform: `translateY(${(1 - enter) * 18}px) scale(${.97 + .03 * enter})`}}>
        {/* macOS title bar */}
        <div style={{display: 'flex', alignItems: 'center', gap: 6 * u,
          padding: `${10 * u}px ${16 * u}px`,
          background: '#f5f5f4', borderBottom: '1px solid #e5e5e3', flexShrink: 0}}>
          {['#ff5f57','#febc2e','#28c840'].map((c, i) =>
            <div key={i} style={{width: 12 * u, height: 12 * u,
              borderRadius: '50%', background: c}}/>)}
          <div style={{flex: 1, textAlign: 'center', fontSize: 20 * u,
            fontWeight: 600, color: '#6b6b6b'}}>{cue.text}</div>
        </div>
        {/* content */}
        {cue.image
          ? <Img src={staticFile(cue.image)} style={{width: '100%', height: 'calc(100% - 44px)',
              objectFit: 'cover', display: 'block'}}/>
          : <div style={{flex: 1, background: '#fafaf8',
              height: 'calc(100% - 44px)'}}/>}
      </div>
    );
  }

  // ── Standard card types ────────────────────────────────────────────────────
  let content;
  switch (cue.type) {
    case 'keyword':
      content = <div style={{...titleStyle, fontSize: 64 * u, color: accent}}>{cue.text}</div>;
      break;
    case 'bullet-list':
      content = <>
        {cue.text && <div style={titleStyle}>{cue.text}</div>}
        <div style={{display: 'grid', gap: 18 * u, marginTop: 22 * u}}>
          {cue.items.map((item, i) =>
            <div key={i} style={{display: 'flex', alignItems: 'center', gap: 14,
              opacity: stagger(i), transform: `translateX(${(1 - stagger(i)) * 12}px)`,
              fontSize: 30 * u}}>
              <span style={{color: accent, fontFamily: 'monospace', fontWeight: 700,
                fontSize: 19 * u, background: `${accent}15`,
                borderRadius: 7, padding: '3px 9px'}}>0{i + 1}</span>
              <span style={{color: inkMid}}>{item}</span>
            </div>)}
        </div>
      </>;
      break;
    case 'number':
      content = <>
        <div style={{fontSize: 100 * u, fontWeight: 830, color: accent, lineHeight: 1.1}}>
          {cue.value}<span style={{fontSize: 32 * u, marginLeft: 8, color: inkMuted}}>{cue.unit}</span>
        </div>
        <div style={{...titleStyle, marginTop: 14}}>{cue.text}</div>
      </>;
      break;
    case 'quote':
      content = <>
        <div style={{color: accent, fontSize: 82 * u, lineHeight: .72, fontWeight: 800}}>"</div>
        <div style={{...titleStyle, marginTop: 8}}>{cue.text}</div>
        {cue.attribution && <div style={{...small, marginTop: 20, borderTop: '1px solid #e5e5e3',
          paddingTop: 14}}>{cue.attribution}</div>}
      </>;
      break;
    case 'comparison':
      content = <>
        <div style={titleStyle}>{cue.text}</div>
        <div style={{display: 'flex', gap: 12, marginTop: 20}}>
          {[cue.left, cue.right].map((side, i) =>
            <div key={i} style={{flex: 1, minWidth: 0, padding: '15px 16px', borderRadius: 14,
              background: i ? `${accent}12` : '#f5f3ee',
              border: `1.5px solid ${i ? accent + '55' : '#e5e5e3'}`}}>
              <div style={{...small, color: i ? accent : inkMuted,
                fontWeight: 600, marginBottom: 8}}>{side.title}</div>
              <div style={{fontSize: 26 * u, lineHeight: 1.45, color: inkMid,
                overflowWrap: 'anywhere'}}>{side.text}</div>
            </div>)}
        </div>
      </>;
      break;
    case 'code':
      content = <>
        <div style={{...small, color: accent, marginBottom: 10, fontWeight: 600}}>{cue.text}</div>
        <pre style={{fontFamily: 'ui-monospace, monospace', fontSize: 21 * u,
          whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', lineHeight: 1.55,
          color: ink, margin: 0}}>{cue.code}</pre>
      </>;
      break;
    case 'diagram':
      content = <>
        <div style={titleStyle}>{cue.text}</div>
        <div style={{display: 'grid', gap: 8, marginTop: 16}}>
          {cue.items.map((item, i) =>
            <div key={i} style={{textAlign: 'center', opacity: stagger(i)}}>
              {i > 0 && <div style={{color: accent, fontSize: 20, margin: '2px 0'}}>↓</div>}
              <div style={{fontSize: 26 * u, color: inkMid,
                border: `1.5px solid ${accent}60`, padding: '9px 16px',
                borderRadius: 11, background: `${accent}08`}}>{item}</div>
            </div>)}
        </div>
      </>;
      break;
    default: throw new Error(`Unsupported card type: ${cue.type}`);
  }

  return (
    <div style={{...rectangle(cue.box ?? box ?? defaults(aspect).card),
      boxSizing: 'border-box', padding: 28 * u,
      display: 'flex', flexDirection: 'column', justifyContent: 'center',
      background: '#ffffff', border: '1.5px solid #e5e5e3', borderRadius: 20,
      boxShadow: '0 2px 12px rgba(0,0,0,0.07)',
      opacity: Math.min(1, enter) * fade,
      transform: `translateY(${(1 - enter) * 20}px) scale(${.97 + .03 * enter})`}}>
    {cue.label && <div style={{...small, color: accent, marginBottom: 14,
      fontWeight: 600}}>{cue.label}</div>}
    {content}
    {cue.detail && <div style={{...small, marginTop: 16,
      borderTop: '1px solid #e5e5e3', paddingTop: 14}}>{cue.detail}</div>}
  </div>
  );
}

// ─── Captions ─────────────────────────────────────────────────────────────────
function Captions({captions, accent}) {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const time = frame / fps;
  const cue = captions.find(c => c.start <= time && time < c.end);
  if (!cue) return null;
  return (
    <div style={{position: 'absolute', left: '7%', right: '7%', bottom: '7%',
      textAlign: 'center'}}>
      <span style={{display: 'inline-block', maxWidth: '72%', padding: '14px 28px',
        borderRadius: 12, background: '#17120aee', color: '#fdfaf3',
        fontSize: width < 1500 ? 34 : 40, fontWeight: 600, lineHeight: 1.5,
        whiteSpace: 'pre-wrap', letterSpacing: '-.01em'}}>
        {cue.tokens
          ? cue.tokens.map((token, i) =>
              <span key={i} style={{
                color: token.highlight && token.start <= time && time < token.end
                  ? accent : undefined,
                background: token.highlight && token.start <= time && time < token.end
                  ? `${accent}33` : undefined,
                borderRadius: 4}}>{token.text}</span>)
          : cue.text}
      </span>
    </div>
  );
}

// ─── Root component ───────────────────────────────────────────────────────────
function MotionVideo(doc) {
  const {fps} = useVideoConfig();
  const {bg, accent} = useTheme(doc);
  const editorial = Boolean(doc.scenes?.length);
  return (
    <AbsoluteFill style={{background: bg, color: '#17120a',
      fontFamily: doc.fontFamily ?? baseFont}}>
      {doc.fontFile && <style>{`@font-face{font-family:"VideoFont";src:url("${staticFile(doc.fontFile)}")}`}</style>}
      <Audio src={staticFile(doc.audio)}/>
      {editorial ? <EditorialScenes doc={doc}/> : <>
      {(doc.video || doc.image) && <Footage doc={doc} accent={accent}/>}
      {(doc.overlays ?? []).map((cue, i) =>
        <Sequence key={i} from={Math.round(cue.start * fps)}
          durationInFrames={Math.max(1, Math.round(cue.end * fps) - Math.round(cue.start * fps))}>
          <Card cue={cue} aspect={doc.aspect} accent={accent} box={doc.cardBox}/>
        </Sequence>)}
      </>}
      <Captions captions={doc.captions ?? []} accent={accent}/>
    </AbsoluteFill>
  );
}

const Root = () =>
  <Composition id="NarratedVideo" component={MotionVideo}
    durationInFrames={30} fps={30} width={1920} height={1080}
    calculateMetadata={({props}) => ({
      durationInFrames: Math.ceil(props.duration * props.fps),
      fps: props.fps,
      width: sizes[props.aspect][0],
      height: sizes[props.aspect][1],
    })}/>;

registerRoot(Root);
