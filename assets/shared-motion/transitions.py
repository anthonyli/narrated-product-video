"""Deterministic editorial transitions on two equally sized PIL frames.

No animation clock, network, font, or renderer side effects. The caller supplies
normalized progress and a semantic origin. Effects do not certify design quality.
Pillow + NumPy are required. Flip is a perspective-like card turn, not page curl.
"""
from functools import lru_cache
import math
import numpy as np
from PIL import Image, ImageColor, ImageDraw

KINDS = ('ripple', 'radial', 'flip')


def _number(v, name, low, high):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not low <= v <= high:
        raise ValueError(f'{name} must be finite in [{low}, {high}]')
    return float(v)


@lru_cache(maxsize=4)
def _distance(size, origin):
    w, h = size
    x, y = origin[0] * (w - 1), origin[1] * (h - 1)
    yy, xx = np.ogrid[:h, :w]
    radius = np.sqrt((xx - x) ** 2 + (yy - y) ** 2).astype(np.float32)
    far = max(math.hypot(cx-x, cy-y) for cx, cy in ((0,0),(w-1,0),(0,h-1),(w-1,h-1)))
    return radius, max(1., far)


def _wave(frame, p, origin, strength, rings):
    """Localized radial refraction using a bounded, continuous inverse mesh."""
    w, h = frame.size
    ox, oy = origin[0] * (w-1), origin[1] * (h-1)
    far = max(math.hypot(x-ox,y-oy) for x,y in ((0,0),(w-1,0),(0,h-1),(w-1,h-1)))
    front = p * far
    width = max(1., far * .16)
    amplitude = min(w,h) * strength * math.sin(math.pi*p)
    def source(x,y):
        dx,dy=x-ox,y-oy; r=math.hypot(dx,dy)
        if r < 1e-8:return x,y
        phase=(r-front)/width
        displacement=amplitude*math.exp(-phase*phase*2)*math.sin(phase*math.pi*rings)
        return min(w-1,max(0,x+dx/r*displacement)), min(h-1,max(0,y+dy/r*displacement))
    step=max(12,round(min(w,h)/24)); mesh=[]
    for y in range(0,h,step):
        for x in range(0,w,step):
            x1,y1=min(w,x+step),min(h,y+step)
            quad=source(x,y)+source(x,y1)+source(x1,y1)+source(x1,y)
            mesh.append(((x,y,x1,y1),quad))
    return frame.transform((w,h),Image.Transform.MESH,mesh,Image.Resampling.BICUBIC)


def _radial(a, b, p, origin, feather, ripple=False, strength=.018, rings=3):
    distance, far = _distance(a.size, origin)
    soft=max(1.,far*feather)
    # Start outside the canvas; finish beyond farthest corner. No edge remnants.
    radius=p*(far+2*soft)-soft
    mask=Image.fromarray(np.uint8(np.clip((radius-distance)/soft+.5,0,1)*255),'L')
    merged=Image.composite(b,a,mask)
    if ripple:
        merged=_wave(merged,p,origin,strength,rings)
        # Subtle rings visualize the wavefront without changing story labels.
        overlay=Image.new('RGBA',a.size);d=ImageDraw.Draw(overlay)
        x,y=origin[0]*(a.width-1),origin[1]*(a.height-1)
        for k in range(3):
            rr=radius-k*soft*2.2
            if rr>0:d.ellipse((x-rr,y-rr,x+rr,y+rr),outline=(255,255,255,round(42*math.sin(math.pi*p)/(k+1))),width=max(1,round(min(a.size)/540)))
        merged=Image.alpha_composite(merged,overlay)
    return merged


def _perspective(source, corners):
    w,h=source.size
    src=((0,0),(w,0),(w,h),(0,h)); matrix=[]; target=[]
    # Pillow maps destination coordinates to source coordinates.
    for (x,y),(u,v) in zip(corners,src):
        matrix += [[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]
        target += [u,v]
    coeff=np.linalg.solve(np.asarray(matrix,dtype=float),np.asarray(target,dtype=float))
    return source.transform((w,h),Image.Transform.PERSPECTIVE,coeff.tolist(),Image.Resampling.BICUBIC)


def _flip(a,b,p,axis,background):
    w,h=a.size
    canvas=Image.new('RGBA',(w,h),ImageColor.getcolor(background,'RGBA'))
    stretch=abs(math.cos(math.pi*p)); turn=math.sin(math.pi*p)
    if stretch<.002:return canvas
    if axis=='x':
        half=w*.5*stretch; squeeze=h*.12*turn; x0,x1=w/2-half,w/2+half
        corners=((x0,squeeze),(x1,0),(x1,h),(x0,h-squeeze)) if p<.5 else ((x0,0),(x1,squeeze),(x1,h-squeeze),(x0,h))
    else:
        half=h*.5*stretch;squeeze=w*.12*turn;y0,y1=h/2-half,h/2+half
        corners=((squeeze,y0),(w-squeeze,y0),(w,y1),(0,y1)) if p<.5 else ((0,y0),(w,y0),(w-squeeze,y1),(squeeze,y1))
    projected=_perspective(a if p<.5 else b,corners)
    shade=Image.new('RGBA',(w,h),(0,0,0,round(72*turn)))
    shade.putalpha(projected.getchannel('A').point(lambda v:round(v*.28*turn)))
    projected=Image.alpha_composite(projected,shade)
    return Image.alpha_composite(canvas,projected)


def transition(a,b,progress,*,kind='ripple',origin=(.5,.5),feather=.015,strength=.018,rings=3,axis='x',background='#f5f2ea'):
    """Return an RGBA transition frame. Progress endpoints are exact frame copies.

    origin is normalized x/y in the image (e.g. the actual clicked object),
    feather/strength are fractions; no random state is used. Unknown kinds and
    malformed values fail rather than silently falling back to a dissolve.
    """
    if not isinstance(a,Image.Image) or not isinstance(b,Image.Image) or a.size!=b.size or min(a.size)<2:
        raise ValueError('a and b must be equally sized PIL images, each dimension >= 2')
    p=_number(progress,'progress',0,1)
    if kind not in KINDS:raise ValueError(f'kind must be one of {KINDS}')
    if not isinstance(origin,(list,tuple)) or len(origin)!=2:raise ValueError('origin must have two normalized coordinates')
    origin=tuple(_number(v,'origin',0,1) for v in origin)
    feather=_number(feather,'feather',.001,.1);strength=_number(strength,'strength',0,.06)
    rings=_number(rings,'rings',1,8)
    if axis not in ('x','y'):raise ValueError('axis must be x or y')
    ImageColor.getcolor(background,'RGBA')
    a,b=a.convert('RGBA'),b.convert('RGBA')
    if p==0:return a.copy()
    if p==1:return b.copy()
    if kind=='flip':return _flip(a,b,p,axis,background)
    return _radial(a,b,p,origin,feather,kind=='ripple',strength,rings)
