"""Deterministic, source-free editorial panel illustrations for KURIO.
Five genuinely different diagrammatic paintings per story, no AI inference or APIs.
They're aesthetic concept art, not precise scientific schematics.
"""
from pathlib import Path
from io import BytesIO
import colorsys, hashlib, math, random, re
from PIL import Image
import cairosvg

PALETTES={
 'Teknologi':('#081725','#102e42','#ffc879','#47c9e6'),
 'Universet':('#110e29','#252061','#fda764','#8d8cff'),
 'Mennesket':('#071a2b','#173b5a','#ff9b76','#63bdf6'),
 'Naturen':('#09232a','#114f50','#ffe29e','#51d9c4'),
 'Historien':('#241323','#55332c','#e6b36f','#9e83fb'),
 'Jorden':('#261019','#602b28','#ffb36c','#fc6e6a'),
}

def f(v):return f'{v:.2f}'
def line(x1,y1,x2,y2,c,w=6,opacity=1):return f'<path d="M {f(x1)} {f(y1)} L {f(x2)} {f(y2)}" fill="none" stroke="{c}" stroke-width="{w}" opacity="{opacity}" stroke-linecap="round"/>'
def circle(x,y,r,color,op=1,fill=True,width=6):return f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{color if fill else "none"}" stroke="{color if not fill else "none"}" stroke-width="{width}" opacity="{op}"/>'
def ellipse(x,y,rx,ry,color,w=8,rot=0,op=1):return f'<ellipse cx="{f(x)}" cy="{f(y)}" rx="{f(rx)}" ry="{f(ry)}" fill="none" stroke="{color}" stroke-width="{w}" transform="rotate({rot} {f(x)} {f(y)})" opacity="{op}"/>'
def path(d,color,width=7,fill='none',opacity=1):return f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{width}" opacity="{opacity}" stroke-linecap="round" stroke-linejoin="round"/>'
def rect(x,y,w,h,fill,rx=8,opacity=1,stroke='none',sw=0):return f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{opacity}"/>'

def motif(kind, idx, a, b, rnd):
    """Create distinct illustrations by varying subject, composition, and diagram type per page."""
    s=[];cx=325+(idx-2)*19;cy=445+(idx%3-1)*18
    if 'zipper' in kind or 'lynlaas' in kind:
        gap=[100,58,33,68,95][idx]
        for side in (-1,1):
            x=cx+side*gap
            s.append(path(f'M {x:.0f} 130 L {x+side*20:.0f} 740', b,20,opacity=.78))
            for j in range(16):
                y=165+j*35;direction=-side
                s.append(rect(x+(-18 if side==1 else -14),y,45,17,a,4,.95))
                s.append(rect(x+direction*32-12,y+1,31,13,b,3,.94))
        s.append(path(f'M {cx-gap-12} 285 Q {cx} 340 {cx} 475 Q {cx} 340 {cx+gap+12} 285', a,15))
        s.append(rect(cx-38,345,76,124,'#172636',22,1,a,6))
        s.append(rect(cx-21,360,42,74,a,12))
    elif 'black' in kind or 'hul' in kind or 'galak' in kind:
        for j in range(9):
            s.append(ellipse(cx,cy,87+j*21,46+j*14,a if j%3==0 else b,7,j*8+idx*17,.16+.065*j))
        s.append(circle(cx,cy,118,'#01040e'))
        s.append(circle(cx,cy,122,a,.9,False,7))
        for j in range(22):
            ang=j*2*math.pi/22+idx/6;r=185+(j%5)*12
            s.append(circle(cx+math.cos(ang)*r,cy+math.sin(ang)*r*.66,1+(j%4)*1.4,b,.7))
    elif 'brain' in kind or 'hjerne' in kind or 'neuro' in kind:
        for j in range(16):
            ang=(j/16)*math.pi*2;r=135+22*math.sin(j*3+idx)
            x=cx+math.cos(ang)*r;y=cy+math.sin(ang)*r
            s.append(line(cx,cy,x,y,b if j%2 else a,3,.7))
            for k in range(3):
                t=ang+(k-1)*.42
                s.append(line(x,y,x+math.cos(t)*48,y+math.sin(t)*51,a if j%3 else b,4,.65))
                s.append(circle(x+math.cos(t)*48,y+math.sin(t)*51,7,a))
        s.append(circle(cx,cy,43,a))
    elif 'jelly' in kind or 'gople' in kind:
        s.append(path(f'M {cx-150} {cy} C {cx-150} {cy-260} {cx+150} {cy-260} {cx+150} {cy} Q {cx} {cy+75} {cx-150} {cy}',a,9,'#10334f',.9))
        for j in range(11):
            x=cx-132+j*27
            s.append(path(f'M {x} {cy+10} C {x+45*math.sin(j+idx):.0f} {cy+190} {x-40*math.sin(j):.0f} {cy+245} {x+15*math.cos(j):.0f} {cy+370}',a if j%2 else b,4,opacity=.8))
        s.append(ellipse(cx,cy-7,149,55,b,3,0,.8))
    elif 'aqueduct' in kind or 'akvæ' in kind or 'roma' in kind:
        for j in range(5):
            x=70+j*111
            s.append(rect(x,cy-160,24,378,a,4))
            s.append(rect(x+79,cy-160,24,378,a,4))
            s.append(path(f'M {x+18} {cy-150} Q {x+54} {cy-236} {x+87} {cy-150}',b,10))
        s.append(rect(47,cy-224,574,39,a,5))
        for j in range(6):s.append(path(f'M {50+j*100} {cy-219} q 36 -13 70 0',b,3))
    elif 'watch' in kind or 'gear' in kind or 'urv' in kind:
        for j,(x,y,r) in enumerate([(cx-95,cy-85,123),(cx+110,cy+85,107),(cx+140,cy-180,52)]):
            s.append(circle(x,y,r,a,.9,False,10))
            s.append(circle(x,y,r*.57,b,.8,False,6))
            for k in range(12):
                t=k*2*math.pi/12+idx*.15
                s.append(line(x+math.cos(t)*r*.9,y+math.sin(t)*r*.9,x+math.cos(t)*r*1.13,y+math.sin(t)*r*1.13,a,8))
            s.append(circle(x,y,15,b))
        s.append(line(cx-95,cy-85,cx-20,cy-160,b,8))
    elif 'volcano' in kind or 'vulkan' in kind:
        s.append(path(f'M 80 740 L {cx-60} 260 L {cx+15} 270 L 575 740 Z',a,12,'#3a2327'))
        for j in range(7):
            y=285+j*64;s.append(path(f'M {cx-22+j*5} {y} q {120 if j%2 else -120} 30 {65 if j%2 else -75} 72',b,12,opacity=.9))
        for j in range(11):
            y=230-j*28;x=cx+math.sin(j*.87+idx)*80
            s.append(circle(x,y,max(9,34-j*2),a,.12+j*.045))
    elif 'bee' in kind or 'bi' in kind:
        for j in range(7):
            for k in range(6):
                x=75+j*75+(k%2)*37;y=190+k*83
                points=' '.join(f'{x+31*math.cos(t*math.pi/3):.1f},{y+31*math.sin(t*math.pi/3):.1f}' for t in range(6))
                s.append(f'<polygon points="{points}" fill="none" stroke="{a if (j+k+idx)%3==0 else b}" stroke-width="5" opacity="{.44+(j%3)*.15}"/>')
        s.append(ellipse(cx,cy,150,80,a,12,-20))
        for j in range(3):s.append(line(cx-75+j*63,cy-68,cx-75+j*63,cy+72,b,15,.85))
    elif 'aurora' in kind or 'nordlys' in kind:
        for j in range(8):
            x=30+j*65
            s.append(path(f'M {x} 120 Q {x+70*math.cos(j+idx):.0f} 340 {x+18} 580 Q {x+85*math.sin(j):.0f} 720 {x-8} 860', a if j%2 else b, 12+j*2,opacity=.48+.06*(j%3)))
        s.append(path('M 0 815 Q 180 690 345 830 T 650 815',b,11))
    elif 'dna' in kind or 'gen' in kind:
        for y in range(120,820,23):
            t=y/76+idx*.4;x1=cx+math.sin(t)*150;x2=cx-math.sin(t)*150
            s.append(line(x1,y,x2,y,b,5,.65))
        s.append(path('M '+' '.join(f'{cx+math.sin(y/76+idx*.4)*150:.1f} {y}' for y in range(110,830,10)),a,12))
        s.append(path('M '+' '.join(f'{cx-math.sin(y/76+idx*.4)*150:.1f} {y}' for y in range(110,830,10)),b,12))
    elif 'angler' in kind or 'havtaske' in kind or 'dyb' in kind:
        s.append(path(f'M 130 {cy} Q 310 {cy-200} 520 {cy-80} L 610 {cy} L 520 {cy+80} Q 310 {cy+200} 130 {cy} Z',a,10,'#173b54'))
        s.append(circle(500,cy-28,18,b))
        s.append(path(f'M 385 {cy-119} Q 380 {cy-280} 485 {cy-335}',b,7))
        s.append(circle(485,cy-335,27,a))
        for j in range(8):s.append(path(f'M {135+j*40} {cy+55} l 20 26 l 11 -25',b,4))
    elif 'telescope' in kind or 'stjernekig' in kind:
        for j in range(5):
            x=120+j*76
            s.append(rect(x,cy-80+j*14,88,160-j*28,'#1b3d4f',15,.93,a if j%2 else b,7))
            s.append(ellipse(x+45,cy,32,66,b,5))
        for j in range(21):
            x=rnd.randrange(40,610);y=rnd.randrange(70,800)
            s.append(circle(x,y,2+j%5,a,.8))
    else:
        for j in range(11):
            angle=j*32+idx*29
            s.append(ellipse(cx,cy,55+j*23,82+j*13,a if j%2 else b,3,angle,.21+.054*(j%4)))
        for j in range(6):
            s.append(circle(cx+math.cos(j)*158,cy+math.sin(j)*196,17+j*4,a if j%2 else b,.85))
    return ''.join(s)

def artwork_svg(topic,category,slide):
    slug=str(topic).lower()
    h=hashlib.sha256((slug+str(slide)).encode('utf8')).digest();rng=random.Random(int.from_bytes(h[:8],'big'))
    bg,secondary,hot,cool=PALETTES.get(category,PALETTES['Universet'])
    stars=''.join(circle(rng.randint(25,625),rng.randint(30,850),rng.uniform(.7,2.7),cool if i%2 else hot,rng.uniform(.2,.8)) for i in range(90))
    grids=''.join(path(f'M {j*75} 0 L {j*75} 900',cool,1,opacity=.10) for j in range(10))
    key='blackhole' if slug in {'blackhole','sort-hul'} else slug
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="650" height="900" viewBox="0 0 650 900">
<defs>
<radialGradient id="bg" cx="{40+slide*12}%" cy="{28+slide*11}%" r="81%"><stop stop-color="{secondary}"/><stop offset="1" stop-color="{bg}"/></radialGradient>
<radialGradient id="glow"><stop stop-color="{hot}" stop-opacity=".25"/><stop offset="1" stop-color="{hot}" stop-opacity="0"/></radialGradient>
<linearGradient id="rim" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{hot}"/><stop offset="1" stop-color="{cool}"/></linearGradient>
</defs>
<rect width="650" height="900" fill="url(#bg)"/>
{stars}{grids}
<circle cx="{295+slide*19}" cy="{385+slide*23}" r="345" fill="url(#glow)"/>
<g filter="none" transform="{["translate(0 0)","translate(-235 -165) scale(1.72)","translate(305 85) scale(.57)","translate(-125 105) rotate(-12 325 445) scale(1.12)","translate(95 -110) rotate(18 325 445) scale(1.08)"][slide]}">{motif(key,slide,hot,cool,rng)}</g>
{("<g opacity=\".6\">"+ellipse(165,655,125,115,cool,6,25,.72)+circle(165,655,64,hot,.21)+"</g>" if slide==2 else "")}
{("<g opacity=\".65\">"+path("M 56 725 Q 265 665 395 770 T 630 710",hot,12)+line(48,270,595,270,cool,4)+"</g>" if slide==3 else "")}
{("<g opacity=\".5\">"+ellipse(338,448,230,335,cool,5,70,.4)+line(60,820,590,140,hot,4,.5)+"</g>" if slide==4 else "")}

<circle cx="325" cy="440" r="290" fill="none" stroke="url(#rim)" stroke-width="2" opacity=".32"/>
<path d="M 44 809 L 113 809 M 44 809 L 44 739 M 536 108 L 603 108 M 603 108 L 603 175" stroke="{hot}" stroke-width="5" opacity=".72" fill="none"/>
<g opacity=".65"><circle cx="80" cy="91" r="7" fill="{hot}"/><circle cx="568" cy="817" r="7" fill="{cool}"/></g>
</svg>'''

def create_panels(slug,category,folder,quality=73):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    output=[]
    for i in range(5):
        file=folder/f'{slug}-panel-{i+1}.webp'
        if not file.exists():
            raw=cairosvg.svg2png(bytestring=artwork_svg(slug,category,i).encode('utf-8'), output_width=560,output_height=775)
            im=Image.open(BytesIO(raw)).convert('RGB')
            im.save(file,format='WEBP',quality=quality,method=5)
        output.append(file)
    return output

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('folder');p=parser.parse_args()
    for slug in ['zipper','blackhole','brain','jellyfish','aqueduct','watch','volcano','bee','aurora','dna','anglerfish','telescope']:
        cat={'zipper':'Teknologi','blackhole':'Universet','brain':'Mennesket','jellyfish':'Naturen','aqueduct':'Historien','watch':'Teknologi','volcano':'Jorden','bee':'Naturen','aurora':'Universet','dna':'Mennesket','anglerfish':'Naturen','telescope':'Universet'}[slug]
        out=create_panels(slug,cat,p.folder)
        print(slug,sum(x.stat().st_size for x in out)//1024,'KB')
