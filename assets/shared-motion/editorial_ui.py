"""Reviewed v3 UI geometry, with episode text externalized in JSON. No TTS or network."""
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import math, os
from core import Scene, Hold, Rest
from pathlib import Path
C = {}
CAPTION_SAFE = False
S=1.5; W,H=1920,1080
CREAM='#F5F2EA'; INK='#17181B'; ORANGE='#F15B35'; BLUE='#3458DF'; YELLOW='#F2CA4E'; GRAY='#DCDCD5'; MUT='#61625C'; WHITE='#FFFFFF'
def resolve_font(bold=False):
    key = 'VIDEO_FONT_BOLD' if bold else 'VIDEO_FONT_REGULAR'
    candidates = [os.environ.get(key, '')]
    if bold:
        candidates += ['/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc']
    candidates += ['/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/System/Library/Fonts/PingFang.ttc', '/System/Library/Fonts/STHeiti Medium.ttc', '/Library/Fonts/Arial Unicode.ttf']
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise RuntimeError('CJK font not found. Set VIDEO_FONT_REGULAR and VIDEO_FONT_BOLD to local licensed font files.')
REG = BOLD = None
F={}
def font(n,b=False):
 k=n,b
 if k not in F:F[k]=ImageFont.truetype(BOLD if b else REG,round(n*S))
 return F[k]
def xy(p):return tuple(round(v*S) for v in p)
def clamp(t):return max(0,min(1,t))
def smooth(t):t=clamp(t);return t*t*(3-2*t)
def out(t):return 1-(1-clamp(t))**4
def ease(t):t=clamp(t);return .5-.5*math.cos(math.pi*t)
def back(t):t=clamp(t);return 1+2.70158*(t-1)**3+1.70158*(t-1)**2
def lerp(a,b,t):return a+(b-a)*t
def mix(a,b,t):return tuple(lerp(x,y,t) for x,y in zip(a,b))
def rect(d,r,fill=WHITE,outline=None,w=1,rad=12): d.rounded_rectangle(xy(r),radius=round(rad*S),fill=fill,outline=outline,width=max(1,round(w*S)))
def ellipse(d,r,fill=None,outline=None,w=1):d.ellipse(xy(r),fill=fill,outline=outline,width=max(1,round(w*S)))
def line(d,pts,fill=INK,w=1):d.line([xy(p) for p in pts],fill=fill,width=round(w*S))
def text(d,p,s,n=25,c=INK,b=False,anchor=None):d.text(xy(p),s,font=font(n,b),fill=c,anchor=anchor)
def poly(d,p,fill):d.polygon([xy(q) for q in p],fill=fill)
def surface(w,h,color=None):return Image.new('RGBA',(round(w*S),round(h*S)),color or (0,0,0,0))
def paste(im,asset,cx,cy,scale=1,angle=0,alpha=1):
 if scale<=.001 or alpha<=0:return
 if scale!=1:asset=asset.resize((max(1,round(asset.width*scale)),max(1,round(asset.height*scale))),Image.Resampling.BICUBIC)
 if angle:asset=asset.rotate(angle,Image.Resampling.BICUBIC,expand=True)
 if alpha<.999:asset=asset.copy();asset.putalpha(asset.getchannel('A').point(lambda v:round(v*alpha)))
 im.alpha_composite(asset,(round(cx*S-asset.width/2),round(cy*S-asset.height/2)))
def base():return Image.new('RGBA',(W,H),CREAM)
def label(im,num=1,chapter=None):
 d=ImageDraw.Draw(im);text(d,(43,30),C['brand'],21,INK,True);text(d,(1237,690),C['disclaimer'],11,MUT,anchor='ra')
def star(d,cx,cy,r,rot=0,col=ORANGE):
 points=[]
 for i in range(24):
  a=i*math.pi/12+rot;rr=r if i%2==0 else r*.6;points.append((cx+math.cos(a)*rr,cy+math.sin(a)*rr))
 poly(d,points,col)
def pill(s,w=185,color=BLUE,fg=WHITE):
 im=surface(w,55);d=ImageDraw.Draw(im);rect(d,(0,0,w,55),color,rad=27);text(d,(w/2,26),s,23,fg,True,'mm');return im
# Animated editorial UI assets: schematic shapes, not actual product screenshots.
def browser():
 im=surface(990,550);d=ImageDraw.Draw(im);rect(d,(0,0,990,550),WHITE,'#D8D8D0',1,18);line(d,[(0,43),(990,43)],'#E8E8E1',1)
 for i,c in enumerate([ORANGE,YELLOW,'#8FB49D']):ellipse(d,(18+i*17,17,26+i*17,25),c)
 rect(d,(357,12,633,31),'#F1F1EC',rad=9);return im
BROWSER = None
def content_asset(kind,w,h):
 im=surface(w,h);d=ImageDraw.Draw(im)
 if kind=='title':
  text(d,(0,0),C['ui']['title'][0],61,INK,True);text(d,(0,74),C['ui']['title'][1],51,INK,True)
 elif kind=='body':
  text(d,(0,0),C['ui']['body'][0],16,'#555750');text(d,(0,26),C['ui']['body'][1],16,'#555750')
 elif kind=='cta':
  rect(d,(0,0,w,h),BLUE,rad=25);text(d,(w/2,h/2-1),C['ui']['cta'],19,WHITE,True,'mm')
 elif kind=='art':
  rect(d,(0,0,w,h),YELLOW,rad=14)
  # abstract sculptural arch collage
  ellipse(d,(w*.08,h*.06,w*.86,h*.95),ORANGE)
  rect(d,(w*.42,h*.25,w*.8,h*1.2),BLUE,rad=w*.18)
  ellipse(d,(w*.38,h*.2,w*.84,h*.75),CREAM)
  rect(d,(w*.39,h*.48,w*.83,h),CREAM,rad=0)
  star(d,w*.23,h*.71,min(w,h)*.15,.2,INK)
 elif kind=='nav':
  text(d,(0,0),C['ui']['brand'],17,INK,True);text(d,(w,1),C['ui']['navigation'],13,INK,False,'ra')
 elif kind=='mini':
  rect(d,(0,0,w,h),'#E6E8DF',rad=12);ellipse(d,(18,18,48,48),BLUE);text(d,(65,15),C['ui']['note'][0],16,INK,True);text(d,(65,39),C['ui']['note'][1],13,MUT)
 return im
ASSETS = {}
# Positions relative to main canvas, layout ranges from disordered to deliberately structured.
BAD={'title':(635,333,.73,-7),'body':(734,470,1.2,7),'cta':(320,403,1.15,10),'art':(862,337,.7,-11),'nav':(627,208,1,-2),'mini':(428,511,1.1,-8)}
GOOD={'title':(486,337,.85,0),'body':(446,446,1,0),'cta':(356,521,1,0),'art':(906,404,.92,0),'nav':(640,194,1,0),'mini':(907,607,.9,0)}
def ui_layout_point(x,y):
 return (640+(x-640)*.9,360+(y-389)*.9) if CAPTION_SAFE else (x,y)
def ui_scene(t):
 im=base();d=ImageDraw.Draw(im);label(im,1,'FROM NOISE TO HIERARCHY')
 # Browser enters from below; title lives in upper breathing space.
 intro=out(t/.55);bx,by=ui_layout_point(640,lerp(950,389,intro));paste(im,BROWSER,bx,by,.864 if CAPTION_SAFE else .96)
 for k,a in ASSETS.items():
  i=list(ASSETS).index(k);p=ease((t-1.65-i*.055)/1.15);v=mix(BAD[k],GOOD[k],p)
  drift=(1-p)*math.sin(t*1.6+i)*5
  ax,ay=ui_layout_point(v[0],v[1]+(1-intro)*550+drift)
  paste(im,a,ax,ay,v[2]*(.9 if CAPTION_SAFE else 1),v[3]*(1-p*.1))
 # highlighted check sweeps over the composition
 if .65<t<2.1:
  scan=clamp((t-.65)/1.45);x=180+scan*920
  overlay=surface(1280,720);od=ImageDraw.Draw(overlay);rect(od,(x-25,177,x+1,605),(52,88,223,18),rad=0);line(od,[(x,177),(x,605)],BLUE,2)
  if CAPTION_SAFE:paste(im,overlay,640,333.9,.9)
  else:im.alpha_composite(overlay)
 # command appears and stays attached to reflow action
 p=out((t-.7)/.45);paste(im,pill(C['reflow_tag'],245),1001,lerp(-70,111,p),1,lerp(9,0,out((t-.7)/.55)))
 # Graphic corner anchors expand then dissolve as layout settles
 if 1.35<t<3.55:
  a=1-smooth((t-3.0)/.55);ol=surface(1280,720);od=ImageDraw.Draw(ol)
  for x,y in [(251,254),(1090,254),(251,565),(1090,565)]:
   line(od,[(x,y+20),(x,y),(x+20,y)],ORANGE,3)
  paste(im,ol,640,333.9 if CAPTION_SAFE else 360,.9 if CAPTION_SAFE else 1,0,a)
 # Camera push from the accepted reference; inserted narration holds freeze time.
 z=1+.045*smooth((t-3.8)/1.1)
 if t>3.8:
  scaled=im.resize((round(W*z),round(H*z)),Image.Resampling.BICUBIC);im=scaled.crop(((scaled.width-W)//2,(scaled.height-H)//2,(scaled.width+W)//2,(scaled.height+H)//2))
 # large orange disc match-wipes into next segment
 if t>5.2:
  r=lerp(0,1550,ease((t-5.2)/.8));d=ImageDraw.Draw(im);ellipse(d,(1120-r,620-r,1120+r,620+r),ORANGE)
  a=out((t-6.05)/.45)
  if a>0:text(d,(640,360),C['command_title'],int(lerp(30,61,a)),INK,True,'mm')
 return im.convert('RGB')
def reveal_text(im,position,s,n,c=INK,b=True,progress=1):
 # horizontal clipping mask, anchored at its real baseline area
 temp=surface(1280,160);d=ImageDraw.Draw(temp);text(d,(0,0),s,n,c,b)
 tw=round(min(1280,ImageDraw.Draw(temp).textlength(s,font=font(n,b))/S+8)*S)
 temp=temp.crop((0,0,max(1,int(tw*clamp(progress))),temp.height));im.alpha_composite(temp,xy(position))

def clean_ui():
 im=surface(1280,720);paste(im,BROWSER,640,389,.96)
 for k,a in ASSETS.items():
  v=GOOD[k];paste(im,a,v[0],v[1],v[2],v[3])
 return im
CLEAN_UI = None

def commands(t):
 im=Image.new('RGBA',(W,H),ORANGE);d=ImageDraw.Draw(im)
 # opening matches the orange circle wipe and title from previous shot
 p=out(t/.5);text(d,(640,lerp(360,115,p)),C['command_title'],int(lerp(61,32,p)),INK,True,'mm')
 names=C['command_names'];desc=C['command_details']
 for i,s in enumerate(names):
  e=out((t-.4-i*.07)/.55);y=224+i*91
  current=min(3,int(max(0,t-.95)/.95))
  if current==i:
   width=780*out((t-(.95+i*.95))/.35)
   rect(d,(232,y-7,232+width,y+72),INK,rad=0)
  col=CREAM if current==i else INK
  x=lerp(-520,263,e);text(d,(x,y),s,52,col,True)
  text(d,(995,y+33),desc[i],24,col,False,'ra')
 # selected command becomes the shared entry point to the following docs
 if t>5.0:
  u=out((t-5.0)/.5);r=lerp(0,1280,u);rect(d,(1280-r,0,1280,720),CREAM,rad=0)
  if t>5.55:reveal_text(im,(90,280),C['context_title'],61,INK,True,out((t-5.55)/.45))
 text(ImageDraw.Draw(im),(1237,690),C['disclaimer'],11,INK,False,'ra')
 return im.convert('RGB')

def document_asset(title,items,color):
 im=surface(350,390);d=ImageDraw.Draw(im);rect(d,(0,0,350,390),color,rad=8)
 text(d,(25,24),title,28,INK,True);line(d,[(26,82),(325,82)],INK,1)
 for i,(a,b) in enumerate(items):
  text(d,(26,109+i*82),a,15,MUT);text(d,(26,137+i*82),b,24,INK,True)
 return im
DOC1 = DOC2 = None

def context_scene(t):
 im=base();d=ImageDraw.Draw(im);label(im)
 p=out(t/.5);text(d,(90,lerp(280,91,p)),C['context_title'],int(lerp(61,48,p)),INK,True)
 a=out((t-.35)/.6);b=out((t-.85)/.6)
 # asymmetric document pairing, shared pages move into the final composition
 u=ease((t-3.5)/.85)
 paste(im,DOC1,lerp(390,235,u),lerp(950,400 if CAPTION_SAFE else 427,a),lerp(1,.72,u),lerp(-6,0,a))
 paste(im,DOC2,lerp(867,560,u),lerp(950,400 if CAPTION_SAFE else 427,b),lerp(1,.72,u),lerp(5,0,b))
 if t>1.6:
  q=out((t-1.6)/.4);start=lerp(572,372,u);end=lerp(664,418,u);line(d,[(start,406),(lerp(start,end,q),406)],BLUE,3)
  poly(d,[(end,406),(end-14,398),(end-14,414)],BLUE)
 if t>3.5:
  z=out((t-3.5)/.85);mini=CLEAN_UI;paste(im,mini,lerp(1600,1020,z),420,.38)
  # intentional flowing bridge, not a fake command output
  for j in range(4):
   q=((t-3.5)*1.1+j*.25)%1;cx=700+q*125;cy=410+math.sin(q*math.pi)*-40
   ellipse(d,(cx-4,cy-4,cx+4,cy+4),BLUE)
 if t>6.35:
  v=out((t-6.35)/.65);rect(d,(0,0,1280*v,720),BLUE,rad=0)
 return im.convert('RGB')

def source_panel():
 im=surface(470,350);d=ImageDraw.Draw(im);rect(d,(0,0,470,350),'#F7F6EF',rad=8);text(d,(28,22),C['code_label'],17,INK,True)
 for i,code in enumerate(C['code_lines']):text(d,(30,90+i*41),code,19,BLUE if i==0 else INK)
 return im
SOURCE = None
def detector(t):
 im=Image.new('RGBA',(W,H),BLUE);d=ImageDraw.Draw(im)
 reveal_text(im,(72,67),C['detector_title'],48,CREAM,True,out(t/.5))
 p=out((t-.3)/.55);paste(im,SOURCE,lerp(-300,340,p),375,.95)
 # scanning line moves along source in a readable bounded region
 y=250+(t*83)%235;line(d,[(123,y),(553,y)],ORANGE,3)
 # 62 small rule positions, highlighted with a traveling band rather than fake pass results
 start=out((t-.9)/.55);count=C['rule_count']
 for i in range(count):
  col=i%8;row=i//8;x=737+col*48;y=240+row*31
  active=(i/8-t*1.8)%8<1.2
  rr=6 if active else 3
  ellipse(d,(x-rr,y-rr,x+rr,y+rr),YELLOW if active else '#8EA4F2')
 text(d,(734,185),C['rule_label'],24,CREAM,True)
 if t>1.4:
  q=out((t-1.4)/.45);line(d,[(593,375),(593+q*90,375)],CREAM,3);poly(d,[(683,375),(669,367),(669,383)],CREAM)
 text(d,(730,534),C['detector_detail'],21,CREAM)
 text(d,(73,565 if CAPTION_SAFE else 625),C['detector_limit'],24,CREAM)
 text(d,(1237,690),C['disclaimer'],11,CREAM,False,'ra')
 # zoom through one rule dot into the next shot
 if t>7.1:
  q=ease((t-7.1)/.9);r=1500*q;ellipse(d,(930-r,350-r,930+r,350+r),CREAM)
 return im.convert('RGB')

def inspection(t):
 im=base();d=ImageDraw.Draw(im);label(im)
 reveal_text(im,(72,80),C['inspection_title'],42,INK,True,out(t/.5))
 # board remains the same page, now its bounds and spacing are examined
 board=CLEAN_UI
 foreground=surface(1280,720) if CAPTION_SAFE else im
 fd=ImageDraw.Draw(foreground)
 paste(foreground,board,640,423,.77)
 # a focus rectangle travels across three meaningful regions
 targets=[(521,405,314,101),(491,489,254,40),(845,457,244,244)]
 i=0 if t<2.0 else (1 if t<3.8 else 2)
 start=[0,2.0,3.8][i];f=ease((t-start)/.55);a=targets[max(0,i-1)];b=targets[i]
 x,y,ww,hh=mix(a,b,f)
 # dim unrelated area with clean focus cutout
 if .65<t<6.25:
  overlay=surface(1280,720);od=ImageDraw.Draw(overlay);rect(od,(170,200,1110,644),(23,24,27,38),rad=8);rect(od,(x-ww/2-10,y-hh/2-10,x+ww/2+10,y+hh/2+10),(0,0,0,0),rad=6);foreground.alpha_composite(overlay)
  fd=ImageDraw.Draw(foreground);rect(fd,(x-ww/2-12,y-hh/2-12,x+ww/2+12,y+hh/2+12),None,BLUE,2,6)
  tag=C['inspection_labels'][i];paste(foreground,pill(tag,210,BLUE,WHITE),x,y-hh/2-48,.85)
 # movable measuring line makes spatial purpose visible
 if 5.1<t<6.25:
  q=out((t-5.1)/.4);line(fd,[(528,539),(528+q*213,539)],ORANGE,3)
  line(fd,[(528,530),(528,548)],ORANGE,2);line(fd,[(741,530),(741,548)],ORANGE,2)
 if CAPTION_SAFE:paste(im,foreground,640,320,.95)
 if t>6.7:
  q=ease((t-6.7)/1.3);# shared page shrinks into local boundary, covered by next shot
  overlay=Image.new('RGBA',(W,H),CREAM);paste(overlay,board,640,lerp(379.85,300,q) if CAPTION_SAFE else lerp(423,345,q),lerp(.7315,.70,q) if CAPTION_SAFE else lerp(.77,.70,q));im=overlay
 return im.convert('RGB')

def boundaries(t):
 im=base();d=ImageDraw.Draw(im);label(im)
 board=CLEAN_UI;offset=-45 if CAPTION_SAFE else 0
 paste(im,board,640,345+offset,.70)
 # laptop edge is drawn around the same page: scope is the story, not a warning slide
 q=out(t/.5);rect(d,(278,155+offset,1002,570+offset),None,INK,2,14)
 poly(d,[(278,570+offset),(1002,570+offset),(1065,603+offset),(215,603+offset)],INK);rect(d,(551,570+offset,729,584+offset),CREAM,rad=0)
 text(d,(640,65 if CAPTION_SAFE else 93),C['boundary_title'],32,INK,True,'mm')
 if t>.6:
  tag=out((t-.6)/.4);paste(im,pill(C['boundary_tag'],110,BLUE),640,162+offset,tag)
 # short statements arrive with meaning, not three cards
 for i,s in enumerate(C['boundaries']):
  x=246+i*329;p=out((t-1.4-i*.3)/.45)
  if p>0:
   sy=580 if CAPTION_SAFE else 635
   line(d,[(x,sy+15),(x+30*p,sy+15)],ORANGE,3);text(d,(x+43,sy),s,19,INK)
 if t>5.9:
  u=out((t-5.9)/1.1);rect(d,(0,720-720*u,1280,720),INK,rad=0)
 return im.convert('RGB')

def outro(t, include_mark=True):
 im=Image.new('RGBA',(W,H),INK);d=ImageDraw.Draw(im)
 # title mask reveal with the same orange shape as opening transition
 reveal_text(im,(95,155),C['brand'],111,CREAM,True,out(t/.8))
 if t>.4:reveal_text(im,(103,334),C['outro_title'],38,CREAM,True,out((t-.4)/.65))
 if t>1.2:reveal_text(im,(104,440),C['outro_detail'],25,'#D4D4C9',False,out((t-1.2)/.6))
 u=out((t-2.0)/.5)
 if u>0:
  rect(d,(104,490 if CAPTION_SAFE else 523,104+220*u,541 if CAPTION_SAFE else 574),BLUE,rad=0)
  if u>.8:text(d,(214,516 if CAPTION_SAFE else 549),C['license'],21,CREAM,True,'mm')
 if t>2.7:reveal_text(im,(104,575 if CAPTION_SAFE else 621),C['source_label'],24,CREAM,False,out((t-2.7)/.6))
 # the artifact's own geometric mark, restrained movement and purposeful close
 if include_mark:
  r=105+10*math.sin(t*.5);star(d,1100,300,r,t*.08,ORANGE)
 text(d,(1228,690),C['disclaimer'],11,'#D4D4C9',False,'ra')
 # last two seconds settle rather than fade to an empty frame
 return im.convert('RGB')


def engagement(t):
 """A final spoken invitation, with a shared mark and a settled readable end."""
 content=C['engagement']
 im=Image.new('RGBA',(W,H),INK)
 # Fade outgoing copy in place while the orange mark stays a shared object.
 fade=1-out(t/.32)
 if fade>0:paste(im,outro(8,include_mark=False).convert('RGBA'),640,360,alpha=fade)
 d=ImageDraw.Draw(im);u=out(t/.5)
 star(d,1100,lerp(300,154,u),lerp(105+10*math.sin(4),64,u),lerp(.64,0,u),ORANGE)
 for i,value in enumerate(content['lines']):
  progress=out((t-.15-i*.12)/.4)
  if progress>0:reveal_text(im,(104,227+i*85),value,48,CREAM,True,progress)
 d=ImageDraw.Draw(im)
 for i,value in enumerate(content['actions']):
  progress=out((t-.55-i*.1)/.35)
  if progress<=0:continue
  x=104+i*288;y=lerp(510,492,progress)
  rect(d,(x,y,x+242,y+72),BLUE if i!=2 else ORANGE,rad=12)
  text(d,(x+121,y+36),value,30,CREAM,True,'mm')
 text(d,(1228,690),C['disclaimer'],11,'#D4D4C9',False,'ra')
 return im.convert('RGB')


# This adapter preserves the reviewed reference geometry and source motion times.
# A different explanation can supply another local adapter to the same core.
SOURCE_SCENES = {
    'ui_reflow': (7, ui_scene), 'commands': (7, commands),
    'context': (7, context_scene), 'detector': (8, detector),
    'inspection': (8, inspection), 'local_boundary': (7, boundaries),
    'outro': (8, outro), 'engagement': (5, engagement),
}

def create_scenes(config, config_dir):
    global C, CAPTION_SAFE, REG, BOLD, F, BROWSER, ASSETS, CLEAN_UI, DOC1, DOC2, SOURCE
    C = config['content']
    CAPTION_SAFE = config.get('caption_safe', False)
    if not isinstance(CAPTION_SAFE, bool):
        raise ValueError('caption_safe must be a boolean')
    if config.get('canvas', [1920, 1080]) != [1920, 1080]:
        raise ValueError('Reference UI adapter requires 1920x1080; adapt layout for another ratio')
    for key, count in [('command_names',4), ('command_details',4), ('inspection_labels',3), ('boundaries',3), ('documents',2)]:
        if len(C[key]) != count:
            raise ValueError(f'Reference layout needs {count} {key}; use a different adapter for another structure')
    if not isinstance(C['rule_count'], int) or isinstance(C['rule_count'], bool) or not 1 <= C['rule_count'] <= 64:
        raise ValueError('Reference rule grid supports 1–64 rules')
    if not C.get('disclaimer', '').strip():
        raise ValueError('Conceptual UI adapter requires a visible non-measured disclaimer')
    REG, BOLD = resolve_font(False), resolve_font(True)
    F = {}
    BROWSER = browser()
    ASSETS={
     'title':content_asset('title',480,153),'body':content_asset('body',330,50),'cta':content_asset('cta',151,49),
     'art':content_asset('art',345,345),'nav':content_asset('nav',866,28),'mini':content_asset('mini',264,69)}
    CLEAN_UI = clean_ui()
    DOC1, DOC2 = [document_asset(doc['title'], doc['items'], doc['color']) for doc in C['documents']]
    SOURCE = source_panel()
    result = []
    for item in config['scenes']:
        name = item['source']
        if name not in SOURCE_SCENES:
            raise ValueError(f'Unknown reference scene: {name}')
        duration, fn = SOURCE_SCENES[name]
        if name == 'engagement':
            content=C.get('engagement', {})
            for key, count in [('lines',2), ('actions',3)]:
                if not isinstance(content.get(key), list) or len(content[key]) != count or not all(isinstance(v,str) and v.strip() for v in content[key]):
                    raise ValueError(f'Engagement needs {count} nonempty {key}')
            duration=item.get('duration', duration)
        elif 'duration' in item:
            raise ValueError('Override duration only on engagement; use semantic holds/rests for source scenes')
        holds = tuple(Hold(**hold) for hold in item.get('holds', []))
        rests = tuple(Rest(**rest) for rest in item.get('rests', []))
        result.append(Scene(item['id'], duration, fn, holds, rests))
    return result
