// Two small silent engineering fixtures, not polished marketing deliverables.
// Set ANATOMY_KIT to an installed Anatomy kit/iso-kit.mjs file.
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
if (!process.env.ANATOMY_KIT) throw new Error('Set ANATOMY_KIT');
const k = await import(pathToFileURL(resolve(process.env.ANATOMY_KIT)).href);
export const width=640,height=480,fps=24,duration=6;
const P=k.fitProjection(k.boxCorners({x:-80,y:-60,w:160,d:120,r:2},0,30),600,350,{pad:25});
const clamp=x=>Math.max(0,Math.min(1,x));
const ease=x=>{x=clamp(x);return x*x*(3-2*x)};
function box(x,y,w,d,z,h,accent=false){
 const p=k.slabOf({x,y,w,d,r:1},z,h,P,3,.4);
 return `<path d="${p.fill}" fill="#9cadba"/>`+p.shades.map((d,i)=>`<path d="${d}" fill="${['#6a8091','#8498a7','#a7b7c1','#c3ced4'][i]}"/>`).join('')+`<path d="${p.top}" fill="${accent?'#ec8648':'#e6ecee'}"/><path d="${p.outline}" fill="none" stroke="#294258" stroke-width="1"/>`;
}
export function renderFrame(t){
 let s=box(-80,-60,160,120,-4,4),label;
 if(t<3){
  label='SERIAL vs PARALLEL / illustrative queues';
  for(let row=0;row<4;row++){
   const y=-48+row*29;s+=box(-72,y,144,16,0,2);
   s+=box(61,y,5,16,2,17);
   for(let j=0;j<3;j++){
    const progress=row===0?ease((t-j*.7)/.7):ease((t-.3)/1.4);
    s+=box(-65+j*14+progress*(92-j*14),y+3,10,10,2,7,true);
   }
  }
 }else{
  label='CACHE KEY / matching pins release the gate';
  const match=ease((t-3.5)/1),slide=45*ease((t-4.5)/.8);
  s+=box(-65,-40,130,70,0,5);
  for(let i=0;i<5;i++){
   s+=box(-50+i*23,-31,8,50,5,3);
   s+=box(-50+i*23,-30+match*(8+i*4),8,10,8,12,true);
  }
  s+=box(-65,25+slide,130,6,5,22,true);
 }
 return `<svg xmlns="http://www.w3.org/2000/svg" width="640" height="480"><rect width="640" height="480" fill="#dce8ef"/><text x="25" y="37" font-size="19" font-family="sans-serif" fill="#17324b">${label}</text><g transform="translate(20 65)">${s}</g></svg>`;
}
