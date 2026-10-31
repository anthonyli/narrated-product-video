"""Original editorial validation designs. No third-party artwork or private data.
All visible product operations are conceptual, not captures of executed software.
"""
from pathlib import Path
import sys, math, json, subprocess, os
from functools import lru_cache
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
W,H=1920,1080
ROOT=Path(__file__).resolve().parents[1]
# Bundled next to shared-motion, or found from a project inside self-media.
_candidates=[Path(__file__).resolve().parent.parent/'shared-motion']+[a/'skills/narrated-product-video/assets/shared-motion' for a in Path(__file__).resolve().parents]
SHARED=next((a for a in _candidates if (a/'transitions.py').is_file()),None)
if SHARED is None:raise RuntimeError('Place renderer beside shared-motion or in a self-media project.')
sys.path.insert(0,str(SHARED))
from transitions import transition
CTX={}
def C(key,default):return CTX.get(key,default)
CREAM='#F2EFE5'; INK='#202820'; ORANGE='#ED623D'; BLUE='#3658C5'; PAPER='#FFFEF8'; MUT='#687266'; GREEN='#B9C8A2'; PINK='#EBCBC1'
@lru_cache(None)
def font(n,b=True,latin=False):
 role='LATIN' if latin else 'BOLD' if b else 'REGULAR'
 default='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if latin else '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc' if b else '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
 path=os.environ.get('VIDEO_FONT_'+role,default)
 if not Path(path).is_file():raise FileNotFoundError('Font missing; set VIDEO_FONT_'+role+' to a compatible font path: '+path)
 return ImageFont.truetype(path,n)
@lru_cache(512)
def _glyph(s,n,c,b,latin):
 f=font(n,b,latin);box=f.getbbox(str(s));out=Image.new('RGBA',(max(1,box[2]-box[0]+4),max(1,box[3]-box[1]+4)))
 ImageDraw.Draw(out).text((2-box[0],2-box[1]),str(s),font=f,fill=c);return out
def text(im,x,y,s,n=40,c=None,b=True,latin=False):
 c=INK if c is None else c
 im.alpha_composite(_glyph(str(s),n,c,b,latin),(round(x),round(y)))
def center(im,x,y,s,n=40,c=None,b=True):
 f=font(n,b);text(im,x-f.getlength(s)/2,y,s,n,c,b)
def ease(t):return 1-(1-max(0,min(1,t)))**3
def mix(a,b,t):return a+(b-a)*t
def rr(im,box,fill,r=20,stroke=None,width=2):ImageDraw.Draw(im).rounded_rectangle(box,r,fill,stroke,width)
def line(im,pts,c=None,w=3):ImageDraw.Draw(im).line(pts,fill=INK if c is None else c,width=w,joint='curve')
def dot(im,x,y,r,c):ImageDraw.Draw(im).ellipse((x-r,y-r,x+r,y+r),fill=c)
@lru_cache(12)
def bg(color=CREAM,grid=False):
 im=Image.new('RGBA',(W,H),color);d=ImageDraw.Draw(im)
 if grid:
  for x in range(0,W,40):d.line((x,0,x,H),fill='#DCDDD0',width=1)
  for y in range(0,H,40):d.line((0,y,W,y),fill='#DCDDD0',width=1)
 # reproducible subtle paper grain, not moving noise
 a=np.array(im);rng=np.random.default_rng(21);noise=rng.integers(-2,3,(H,W,1));a[:,:,:3]=np.clip(a[:,:,:3].astype('int16')+noise,0,255)
 return Image.fromarray(a)
def label(im,num,theme,color=None):
 color=INK if color is None else color
 text(im,84,47,f"{C('section',num)}   /   {C('kicker',theme)}",24,color);line(im,[(84,92),(1836,92)],color,2)
 text(im,84,1013,C('footer_label','无声视觉样片 · 原创图形 / 流程示意'),22,color,False)
 text(im,1510,1013,'NARRATED  /  V4',20,color,True,True)
def paste(im,layer,x,y,angle=0,scale=1,alpha=1):
 if scale!=1:layer=layer.resize((max(1,int(layer.width*scale)),max(1,int(layer.height*scale))),Image.Resampling.BICUBIC)
 if angle:layer=layer.rotate(angle,Image.Resampling.BICUBIC,expand=True)
 if alpha<1:layer=layer.copy();layer.putalpha(layer.getchannel('A').point(lambda z:int(z*alpha)))
 im.alpha_composite(layer,(round(x),round(y)))
@lru_cache(20)
def _paper(w,h,color=PAPER,r=3):
 im=Image.new('RGBA',(w+60,h+70));sh=Image.new('RGBA',im.size);rr(sh,(20,24,w+20,h+24),'#20282030',r);im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)));rr(im,(10,8,w+10,h+8),color,r);return im
def paper(w,h,color=PAPER,r=3):return _paper(w,h,color,r).copy()
def cache_content(f):
 cache={}
 def wrapped():
  key=json.dumps(CTX,sort_keys=True,ensure_ascii=False)
  if key not in cache:cache[key]=f()
  return cache[key].copy()
 return wrapped
@cache_content
def receipt():
 p=paper(640,600);d=ImageDraw.Draw(p)
 text(p,55,45,C('brand','OPENAI'),28);text(p,55,91,C('receipt_kicker','API CREDIT NOTE'),18,MUT,True,True)
 line(p,[(55,143),(600,143)],'#D2D3C8',2)
 text(p,55,179,C('receipt_label','Pro $200'),35);text(p,55,243,C('receipt_value','$200'),116,BLUE,True,True)
 text(p,57,389,C('receipt_unit','每账期 API 额度'),27,MUT)
 for x in range(55,610,22):line(p,[(x,460),(x+9,460)],MUT,2)
 text(p,55,488,C('receipt_condition','符合资格才可领取'),27);text(p,55,539,C('disclaimer','示意，不是真实账单'),21,MUT,False)
 d.polygon([(584,8),(650,8),(650,74)],fill='#E1E1D4')
 return p

def api_cover(t):
 im=bg(C('background',CREAM)).copy();label(im,'01','SUBSCRIPTION BENEFIT')
 text(im,84,153,C('title_1','订阅之外，'),80);text(im,84,255,C('title_2','还有一份额度。'),80)
 text(im,89,398,C('subtitle','ChatGPT Pro · 符合条件的订阅'),29,MUT,False)
 # Oversized typographic numeral is the subject, not a feature card.
 p=ease(t/.65);text(im,75,int(mix(590,500,p)),C('number','API'),210,BLUE,True,True);text(im,91,799,C('unit','订阅之外的开发额度'),38)
 line(im,[(90,866),(655,866)],ORANGE,7)
 text(im,93,900,C('note','以 Pro $200 档为例'),25,MUT,False)
 # A printed receipt sits on a contrasting geometric desk wedge.
 d=ImageDraw.Draw(im);d.ellipse((960,170,1960,1170),fill=GREEN)
 paste(im,receipt(),1100,int(mix(330,235,p)),angle=-5)
 # Match origin is receipt's stamp, meaning benefit validation, not random sparkle.
 q=ease((t-1.2)/.65);d.arc((1525,690,1770,935),0,int(355*q),fill=ORANGE,width=8)
 if q>.85:center(im,1647,785,C('stamp','核资格'),35,ORANGE)
 return im

def api_ledger(t):
 im=bg(C('background','#E8E9DF')).copy();label(im,'02','READ THE PLAN')
 text(im,84,150,C('title_1','看清套餐，'),76);text(im,84,244,C('title_2','再看对应额度。'),76)
 text(im,90,382,C('subtitle','不是三档相加，也不是人人都能领。'),28,MUT,False)
 # bespoke large report ledger; paper is a semantic comparison surface
 p=paper(985,710);text(p,55,45,C('ledger_title','PRO / API 额度对照'),35)
 line(p,[(55,108),(930,108)],INK,3)
 text(p,58,142,C('column_1','订阅档位'),25,MUT);text(p,595,142,C('column_2','每账期额度'),25,MUT)
 rows=C('rows',[('$100','$100'),('$200','$200'),('$500','$500')])
 active=min(2,max(0,int((t-.4)/.9)))
 for i,(a,b) in enumerate(rows):
  y=205+i*142
  if i==active:rr(p,(36,y-17,950,y+99),'#F5D9CC',8)
  text(p,60,y,a,63,INK,True,True);text(p,593,y,b,63,BLUE,True,True)
  line(p,[(58,y+111),(930,y+111)],'#D1D4C9',2)
  if i==active:
   line(p,[(385,y+35),(522,y+35)],ORANGE,5);ImageDraw.Draw(p).polygon([(522,y+35),(503,y+23),(503,y+47)],fill=ORANGE)
 text(p,55,652,C('footer','资格、有效期与实际到账，以领取页为准。'),23,MUT,False)
 paste(im,p,850,155,angle=1)
 # a large typographic marginal note, not redundant repeated card
 text(im,90,601,'01',112,ORANGE,True,True);text(im,92,749,C('marginal_1','选择一档'),42);text(im,92,819,C('marginal_2','对应一份权益'),30,MUT,False)
 return im

def api_guide(t):
 im=bg(C('background','#263B30')).copy();label(im,'03','CLAIM / CHECK',CREAM)
 text(im,84,159,C('title_1','先找领取入口，'),76,CREAM);text(im,84,254,C('title_2','再关联 API 组织。'),76,CREAM)
 p=paper(1490,455);d=ImageDraw.Draw(p)
 text(p,55,47,C('process_title','PRO 领取路径'),25,MUT)
 stages=C('steps',[('01','登录 ChatGPT'),('02','设置 → 账单'),('03','关联 API 组织')])
 for i,(n,s) in enumerate(stages):
  x=70+i*480;q=ease((t-.25-i*.65)/.3)
  text(p,x,117,n,70,BLUE,True,True);text(p,x,222,s,36)
  if i<2:line(p,[(x+285,151),(x+405,151)],'#B6BCAE',4)
  if q>0:
   line(p,[(x,294),(x+int(340*q),294)],ORANGE,7)
 text(p,70,365,C('footer','Business：由工作区所有者进入工作区账单'),27,MUT,False)
 paste(im,p,200,450,angle=-1)
 return im

@cache_content
def notebook():
 im=paper(1110,730);d=ImageDraw.Draw(im)
 for x in range(50,1080,32):line(im,[(x,55),(x,700)],'#DEE2D4',1)
 for y in range(55,705,32):line(im,[(45,y),(1080,y)],'#DEE2D4',1)
 line(im,[(120,35),(120,700)],'#E4A99A',3)
 for y in range(60,690,68):
  d.ellipse((25,y,67,y+30),fill='#AEB5A5');d.arc((5,y-14,75,y+31),65,300,fill='#343F34',width=8)
 text(im,158,62,C('notebook_title','项目记忆手册'),44);text(im,160,124,C('notebook_subtitle','今天留下，明天找回。'),25,MUT,False)
 return im

def memory_cover(t):
 im=bg(C('background','#EEDDD0')).copy();label(im,'01','CLAUDE-MEM / PROJECT MEMORY')
 text(im,83,148,C('title_1','换个会话，'),80);text(im,83,249,C('title_2','又得从头讲？'),80)
 text(im,88,382,C('subtitle','把项目背景留成可检索的记录。'),29,MUT,False)
 d=ImageDraw.Draw(im);d.ellipse((1510,120,2030,640),fill=ORANGE)
 p=notebook().copy();q=ease(t/.55)
 # each original note is specific content, no generic label-only boxes
 notes=C('notes',[('01 · 工具观察','读取配置 / 修改参数','#D9E2F0'),('02 · 修复原因','为什么这样改？','#F1D6A3'),('03 · 语义摘要','为后续会话留下线索','#D7DFC9')])
 for i,(a,b,c) in enumerate(notes):
  n=paper(705,120,c);text(n,32,25,a,28);text(n,32,71,b,24,MUT,False)
  y=210+i*150+int((1-ease((t-i*.25)/.4))*80)
  paste(p,n,162,y,angle=(-1)**i*1.5)
 paste(im,p,770,185,angle=-3,scale=.9)
 # orange pencil drawn as a real recognizable object along foreground
 pp=Image.new('RGBA',(820,75));dd=ImageDraw.Draw(pp);dd.polygon([(10,20),(715,20),(790,38),(715,56),(10,56)],fill='#E0A85D');dd.rectangle((15,20,715,56),fill=ORANGE);dd.polygon([(750,28),(790,38),(750,48)],fill=INK);paste(im,pp,520,900,angle=4)
 text(im,145,640,C('aside_1','不是把整段聊天'),38);text(im,145,707,C('aside_2','重新粘贴一遍。'),38)
 if t>1.4:
  pr=ease((t-1.4)/.7);ImageDraw.Draw(im).arc((61,602,665,802),0,int(350*pr),fill=ORANGE,width=6)
 return im

def memory_index(t):
 im=bg(C('background','#FAF8EF'),True).copy();label(im,'02','FIND / EXPAND')
 text(im,84,145,C('title_1','先找线索，'),78);text(im,84,247,C('title_2','再展开需要的细节。'),78)
 # index cabinet with visible dividers, printed paper, and one pullout memo
 for i in range(3):
  x=105+i*35;y=475+i*28
  rr(im,(x,y,x+780,y+375),['#C3CDB7','#D5DBC7','#E4E7D7'][i],5,INK,2)
  rr(im,(x+45,y-36,x+240,y+24),['#C3CDB7','#D5DBC7','#E4E7D7'][i],6,INK,2)
 text(im,240,557,C('index_title','项目历史 / 登录问题'),32)
 for i,s in enumerate(C('index_rows',['读取登录配置','修改回调参数','保留修复原因'])):
  y=610+i*75;text(im,240,y,s,28,BLUE if i==1 else MUT);line(im,[(240,y+46),(760,y+46)],'#B6C1AA',2)
 q=ease((t-.55)/.8)
 note=paper(755,580);text(note,50,45,C('detail_kicker','相关记录'),29,ORANGE);text(note,50,111,C('detail_title','为什么改这项配置？'),43)
 line(note,[(50,183),(700,183)],INK,3)
 for i,s in enumerate(C('detail_rows',['先查看前后时间线','再读取对应的完整观察','回到原始上下文核对'])):text(note,55,235+i*90,s,31)
 text(note,55,510,C('disclaimer','假设场景 · 非真实运行记录'),22,MUT,False)
 paste(im,note,int(mix(650,1050,q)),int(mix(470,360,q)),angle=mix(-7,2,q),scale=mix(.55,1,q))
 # single highlighted selected row drives expansion, not arbitrary decoration
 if t>1.4:line(im,[(250,732),(250+int(480*ease((t-1.4)/.45)),732)],ORANGE,6)
 return im

def memory_timeline(t):
 im=bg(C('background','#23362D')).copy();label(im,'03','CONTEXT / NOT GUARANTEE',CREAM)
 text(im,84,149,C('title_1','记忆接上了，'),82,CREAM);text(im,84,255,C('title_2','判断还要自己做。'),82,CREAM)
 # distinct horizontal timeline system, not notebook again
 nodes=[(x,*row) for x,row in zip([230,950,1650],C('nodes',[['今天','留下观察'],['下一次会话','检索上下文'],['开发者','核对与验证']]))]
 q=ease(t/.9);line(im,[(230,598),(230+1420*q,598)],'#91A68F',6)
 for i,(x,a,b) in enumerate(nodes):
  p=ease((t-.3*i)/.4)
  if p>0:
   dot(im,x,598,18*p,ORANGE if i==2 else '#D8DFBA');center(im,x,464,a,32,CREAM);center(im,x,689,b,36,CREAM)
 # large fraction-like equation makes the boundary visible
 text(im,390,834,C('equation_left','历史信息'),40,GREEN);text(im,774,810,'≠',88,ORANGE);text(im,1010,834,C('equation_right','代码一定正确'),40,GREEN)
 return im
LAYOUTS={'report_hero':api_cover,'ledger':api_ledger,'process_note':api_guide,'notebook':memory_cover,'index_detail':memory_index,'timeline':memory_timeline}
def render_layout(layout,content,t):
 global CTX,CREAM,INK,ORANGE,BLUE,PAPER,MUT,GREEN,PINK
 if layout not in LAYOUTS:raise ValueError('Unknown layout: '+str(layout))
 if not isinstance(content,dict):raise ValueError('content must be an object')
 if isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t):raise ValueError('t must be finite seconds')
 names=['CREAM','INK','ORANGE','BLUE','PAPER','MUT','GREEN','PINK'];old={k:globals()[k] for k in names}
 palette=content.get('palette',{})
 if not isinstance(palette,dict) or any(k not in names for k in palette):raise ValueError('Invalid palette roles')
 for k,v in palette.items():globals()[k]=v
 CTX=content
 try:return LAYOUTS[layout](max(0,float(t)))
 finally:
  CTX={}
  for k,v in old.items():globals()[k]=v

def validate_config(config):
 if not isinstance(config,dict):raise ValueError('config must be object')
 if config.get('width',1920)!=1920 or config.get('height',1080)!=1080:raise ValueError('Layouts currently support 1920x1080 only; re-layout other ratios.')
 scenes=config.get('scenes')
 if not isinstance(scenes,list) or not scenes:raise ValueError('At least one scene required')
 for s in scenes:
  if not isinstance(s,dict):raise ValueError('scene must be object')
  if s.get('layout') not in LAYOUTS:raise ValueError('Unknown layout')
  if not isinstance(s.get('content',{}),dict):raise ValueError('content must be object')
  if isinstance(s.get('duration',4),bool) or not 1<=float(s.get('duration',4))<=30:raise ValueError('Scene duration must be 1..30 seconds')
  for key in ['rows','steps','notes','index_rows','detail_rows','nodes']:
   if key in s.get('content',{}):
    value=s['content'][key]
    if not isinstance(value,list) or len(value)!=3:raise ValueError(key+' requires exactly three list entries')
    if key in ('index_rows','detail_rows'):
     if not all(isinstance(x,str) for x in value):raise ValueError(key+' entries must be strings')
    else:
     n=3 if key=='notes' else 2
     if not all(isinstance(x,(list,tuple)) and len(x)==n and all(isinstance(v,str) for v in x) for x in value):raise ValueError(key+' row shape invalid')
  tr=s.get('transition',{})
  if not isinstance(tr,dict):raise ValueError('transition must be object')
  if tr and tr.get('kind') not in ['ripple','radial','flip']:raise ValueError('Unsupported transition')
  if tr and s is scenes[-1]:raise ValueError('Last scene cannot transition without destination')
  if tr and not .15<=float(tr.get('duration',.6))<=1:raise ValueError('Transition duration must be .15..1')
 return sum(float(s.get('duration',4)) for s in scenes)

def config_frame(config,t):
 scenes=config['scenes'];start=0
 for i,s in enumerate(scenes):
  dur=float(s.get('duration',4));local=t-start;end=start+dur
  if t<end or i==len(scenes)-1:
   a=render_layout(s['layout'],s.get('content',{}),min(local,dur))
   tr=s.get('transition',{});td=float(tr.get('duration',.6))
   if tr and i<len(scenes)-1 and local>=dur-td:
    nxt=scenes[i+1];b=render_layout(nxt['layout'],nxt.get('content',{}),0)
    return transition(a,b,max(0,min(1,(local-dur+td)/td)),kind=tr['kind'],origin=tuple(tr.get('origin',[.5,.5])),background=tr.get('background','#F2EFE5'),axis=tr.get('axis','x')).convert('RGB')
   return a.convert('RGB')
  start=end

def render_config(config,out):
 duration=validate_config(config);fps=config.get('fps',60)
 if isinstance(fps,bool) or fps not in [24,30,60]:raise ValueError('fps must be24,30or60')
 out=Path(out)
 if out.exists():raise FileExistsError('Refusing to overwrite existing output; choose a new version.')
 out.parent.mkdir(parents=True,exist_ok=True)
 cmd=['ffmpeg','-n','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
 proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
 try:
  for f in range(round(duration*fps)):proc.stdin.write(config_frame(config,f/fps).tobytes())
 except BaseException:
  proc.stdin.close();proc.wait()
  raise
 else:
  proc.stdin.close()
  if proc.wait()!=0:raise RuntimeError('FFmpeg render failed')
 return out

if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser(description='Render original 1080p editorial layouts; silent concept sample only.')
 parser.add_argument('--config',required=True,type=Path);parser.add_argument('output',type=Path)
 args=parser.parse_args()
 print(render_config(json.loads(args.config.read_text()),args.output))
