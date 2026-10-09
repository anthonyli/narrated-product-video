import React from 'react';
import {AbsoluteFill, Audio, Composition, Img, OffthreadVideo, Sequence, interpolate,
  registerRoot, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

const sizes = {'16:9': [1920, 1080], '4:3': [1440, 1080], '3:4': [1080, 1440]};
const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};
const baseFont = '"PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif';
const rectangle = ([x, y, w, h]) => ({position: 'absolute', left: `${x * 100}%`,
  top: `${y * 100}%`, width: `${w * 100}%`, height: `${h * 100}%`});

function defaults(aspect) {
  return aspect === '3:4'
    ? {video: [.06, .1, .88, .42], card: [.06, .55, .88, .26]}
    : {video: [.045, .14, .5, .64], card: [.59, .2, .365, .52]};
}

function Footage({doc, accent}) {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const time = frame / fps;
  const motion = doc.motions?.find(m => time >= m.start && time < m.end);
  const zoom = motion ? interpolate(time, [motion.start, motion.end], [motion.from ?? 1, motion.to ?? 1.025], clamp) : 1;
  const position = doc.videoBox ?? defaults(doc.aspect).video;
  const style = {width: '100%', height: '100%', objectFit: doc.videoFit ?? 'contain',
    objectPosition: doc.videoPosition ?? '50% 50%', transform: `scale(${zoom})`};
  return <div style={{...rectangle(position), overflow: 'hidden', borderRadius: 28,
    background: '#050b13', border: '1px solid #ffffff24', boxShadow: '0 20px 80px #0007'}}>
    {doc.video ? <OffthreadVideo src={staticFile(doc.video)} muted style={style}/> :
      doc.image ? <Img src={staticFile(doc.image)} style={style}/> :
        <AbsoluteFill style={{background: `radial-gradient(ellipse at 30% 30%, ${accent}33, #0a1428)`}}/>}
  </div>;
}

function Card({cue, aspect, accent, box}) {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const duration = Math.round(cue.end * fps) - Math.round(cue.start * fps);
  const enter = spring({frame, fps, config: {damping: 22, stiffness: 170, mass: .75}});
  const fade = interpolate(frame, [Math.max(0, duration - Math.round(fps * .18)), duration], [1, 0], clamp);
  const unit = Math.min(1, width / 1440);
  const titleStyle = {fontSize: 44 * unit, lineHeight: 1.24, fontWeight: 750,
    letterSpacing: '-.035em', overflowWrap: 'anywhere'};
  const small = {fontSize: 25 * unit, color: '#aabace', lineHeight: 1.5};
  const stagger = i => interpolate(frame, [i * 5, i * 5 + 10], [0, 1], clamp);
  let content;
  switch (cue.type) {
    case 'big-title':
    case 'keyword':
      content = <div style={{...titleStyle, fontSize: (cue.type === 'big-title' ? 76 : 64) * unit,
        color: cue.type === 'keyword' ? accent : '#f3f7ff'}}>{cue.text}</div>;
      break;
    case 'bullet-list':
      content = <>{cue.text && <div style={titleStyle}>{cue.text}</div>}
        <div style={{display: 'grid', gap: 22 * unit, marginTop: 26 * unit}}>{cue.items.map((item, i) =>
          <div key={i} style={{display: 'flex', alignItems: 'center', gap: 18, opacity: stagger(i),
            transform: `translateY(${(1-stagger(i))*12}px)`, fontSize: 31 * unit}}>
            <span style={{color: accent, fontFamily: 'monospace'}}>0{i+1}</span><span>{item}</span></div>)}</div></>;
      break;
    case 'number':
      content = <><div style={{fontSize: 104 * unit, fontWeight: 800, color: accent, lineHeight: 1.12}}>
        {cue.value}<span style={{fontSize: 34 * unit, marginLeft: 10}}>{cue.unit}</span></div>
        <div style={{...titleStyle, marginTop: 18}}>{cue.text}</div></>;
      break;
    case 'quote':
      content = <><div style={{color: accent, fontSize: 84 * unit, lineHeight: .8}}>"</div>
        <div style={{...titleStyle, marginTop: 12}}>{cue.text}</div>
        {cue.attribution && <div style={{...small, marginTop: 24}}>{cue.attribution}</div>}</>;
      break;
    case 'comparison':
      content = <><div style={titleStyle}>{cue.text}</div><div style={{display: 'flex', gap: 16, marginTop: 24}}>
        {[cue.left, cue.right].map((side, i) => <div key={i} style={{flex: 1, minWidth: 0, padding: 18,
          borderRadius: 16, background: i ? `${accent}20` : '#ffffff09', border: `1px solid ${i ? accent : '#ffffff24'}`}}>
          <div style={{...small, color: i ? accent : '#aabace'}}>{side.title}</div>
          <div style={{fontSize: 29 * unit, lineHeight: 1.4, marginTop: 12, overflowWrap: 'anywhere'}}>{side.text}</div>
        </div>)}</div></>;
      break;
    case 'browser':
      content = <><div style={{...small, marginBottom: 14}}>● ● ●　{cue.text}</div>
        <Img src={staticFile(cue.image)} style={{width: '100%', height: '70%', objectFit: 'contain', borderRadius: 12}}/></>;
      break;
    case 'code':
      content = <><div style={{...small, color: accent}}>{cue.text}</div>
        <pre style={{fontFamily: 'ui-monospace, monospace', fontSize: 22 * unit, whiteSpace: 'pre-wrap',
          overflowWrap: 'anywhere', lineHeight: 1.5, marginBottom: 0}}>{cue.code}</pre></>;
      break;
    case 'diagram':
      content = <><div style={titleStyle}>{cue.text}</div><div style={{display: 'grid', gap: 9, marginTop: 18}}>
        {cue.items.map((item, i) => <div key={i} style={{textAlign: 'center', opacity: stagger(i)}}>
          {i > 0 && <div style={{color: accent, fontSize: 22}}>↓</div>}
          <div style={{fontSize: 27 * unit, border: `1px solid ${accent}77`, padding: '10px 18px', borderRadius: 12}}>{item}</div>
        </div>)}</div></>;
      break;
    case 'progress': {
      const progress = interpolate(frame, [0, Math.max(1, duration - 1)], [0, 100], clamp);
      return <div style={{position: 'absolute', left: '5%', right: '5%', top: '5%', opacity: fade}}>
        <div style={{fontSize: 23 * unit, color: '#c7d4e7', marginBottom: 12}}>{cue.text}</div>
        <div style={{height: 4, background: '#ffffff20', borderRadius: 4}}>
          <div style={{height: '100%', width: `${progress}%`, background: accent}}/></div></div>;
    }
    default: throw new Error(`Unsupported card type: ${cue.type}`);
  }
  return <div style={{...rectangle(cue.box ?? box ?? defaults(aspect).card),
    boxSizing: 'border-box', padding: 30 * unit, display: 'flex', flexDirection: 'column', justifyContent: 'center',
    background: 'linear-gradient(145deg, #17243aef, #0e192ced)', border: '1px solid #ffffff24', borderRadius: 28,
    boxShadow: '0 24px 70px #0004', opacity: Math.min(1, enter) * fade,
    transform: `translateY(${(1-enter)*25}px) scale(${.97 + .03*enter})`}}>
    {cue.label && <div style={{...small, color: accent, marginBottom: 16}}>{cue.label}</div>}
    {content}
    {cue.detail && <div style={{...small, marginTop: 20}}>{cue.detail}</div>}
  </div>;
}

function Captions({captions, accent}) {
  const frame = useCurrentFrame();
  const {fps, width} = useVideoConfig();
  const time = frame / fps;
  const cue = captions.find(c => c.start <= time && time < c.end);
  if (!cue) return null;
  return <div style={{position: 'absolute', left: '7%', right: '7%', bottom: '8%', textAlign: 'center'}}>
    <span style={{display: 'inline-block', maxWidth: '100%', padding: '15px 26px', borderRadius: 16,
      background: '#040b15e8', color: '#f8fafc', fontSize: width < 1500 ? 36 : 44,
      fontWeight: 600, lineHeight: 1.45, whiteSpace: 'pre-wrap', textShadow: '0 2px 4px #000'}}>
      {cue.tokens ? cue.tokens.map((token, i) => <span key={i} style={{
        color: token.highlight && token.start <= time && time < token.end ? accent : undefined,
        background: token.highlight && token.start <= time && time < token.end ? `${accent}22` : undefined,
        borderRadius: 5}}>{token.text}</span>) : cue.text}
    </span>
  </div>;
}

function MotionVideo(doc) {
  const {fps} = useVideoConfig();
  const accent = doc.accent ?? '#77efca';
  return <AbsoluteFill style={{background: 'radial-gradient(ellipse at 75% 25%, #15243b, #080e1b 80%)',
    color: '#f3f7ff', fontFamily: doc.fontFamily ?? baseFont}}>
    {doc.fontFile && <style>{`@font-face {font-family: "VideoFont"; src: url("${staticFile(doc.fontFile)}");}`}</style>}
    <Audio src={staticFile(doc.audio)}/>
    <Footage doc={doc} accent={accent}/>
    {doc.overlays.map((cue, i) => <Sequence key={i} from={Math.round(cue.start * fps)}
      durationInFrames={Math.max(1, Math.round(cue.end * fps) - Math.round(cue.start * fps))}>
      <Card cue={cue} aspect={doc.aspect} accent={accent} box={doc.cardBox}/>
    </Sequence>)}
    <Captions captions={doc.captions} accent={accent}/>
  </AbsoluteFill>;
}

const Root = () => <Composition id="NarratedVideo" component={MotionVideo}
  durationInFrames={30} fps={30} width={1920} height={1080}
  calculateMetadata={({props}) => ({durationInFrames: Math.ceil(props.duration * props.fps),
    fps: props.fps, width: sizes[props.aspect][0], height: sizes[props.aspect][1]})}/>;
registerRoot(Root);
