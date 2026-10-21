// SVG comic panels and dialogue bubbles; no timers or browser dependencies.
export function createComicSvg({fontFamily="sans-serif",palette={}}={}) {
const c={ink:'#102b51',navy:'#112e62',blue:'#2059d8',cyan:'#57e6ff',ice:'#d7f3ff',orange:'#ff934f',cream:'#fff5db',muted:'#426a90',...palette};
const clamp=x=>Math.max(0,Math.min(1,x));
const smooth=x=>{x=clamp(x);return x*x*(3-2*x)};
const ease=(t,a,b)=>smooth((t-a)/(b-a));
const esc=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const txt=(x,y,s,size=36,color=c.ink,weight=400,anchor='start')=>`<text x="${x}" y="${y}" font-family="${fontFamily}" font-size="${size}" font-weight="${weight}" fill="${color}" text-anchor="${anchor}" ${weight>=700?`stroke="${color}" stroke-width=".7" paint-order="stroke"`:''}>${esc(s)}</text>`;
const r=(x,y,w,h,fill,rx=0,stroke='none',sw=0)=>`<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="${rx}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
const line=(d,color=c.ink,sw=4,extra='')=>`<path d="${d}" fill="none" stroke="${color}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round" ${extra}/>`;
function panel(x,y,w,h,fill=c.ice){return r(x+9,y+10,w,h,c.ink,18)+r(x,y,w,h,fill,18,c.ink,4)+`<path d="M${x+w-90} ${y}H${x+w-18}Q${x+w} ${y} ${x+w} ${y+18}V${y+90}Z" fill="${c.cyan}" opacity=".35"/>`;}
function bubble(x,y,w,lines,side='left',fill=c.cream,size=38){
 const h=44+lines.length*53;const tail=side==='left'?x+w*.22:x+w*.78;
 let s=`<path d="M${x+22} ${y}H${x+w-22}Q${x+w} ${y} ${x+w} ${y+22}V${y+h-22}Q${x+w} ${y+h} ${x+w-22} ${y+h}H${tail+20}L${tail-18} ${y+h+36}L${tail-11} ${y+h}H${x+22}Q${x} ${y+h} ${x} ${y+h-22}V${y+22}Q${x} ${y} ${x+22} ${y}Z" fill="${fill}" stroke="${c.ink}" stroke-width="4"/>`;
 lines.forEach((v,i)=>s+=txt(x+w/2,y+53+i*53,v,size,c.ink,700,'middle'));return s;
}

return {c,clamp,smooth,ease,esc,txt,r,line,panel,bubble};
}
