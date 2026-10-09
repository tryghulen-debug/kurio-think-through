"""Five genuinely different, licensed visual assets per story.

No generative AI and no per-user Wikimedia queries. GitHub Actions downloads and
optimizes all images ONCE; Cloudflare serves tiny WebP copies to the app.
"""
from __future__ import annotations
from pathlib import Path
from io import BytesIO
from html import unescape
import hashlib, re, unicodedata
import requests
from PIL import Image,ImageOps,ImageStat

API='https://commons.wikimedia.org/w/api.php'
LICENSE=re.compile(r'^(?:CC\s*BY(?:-SA)?(?:\s|$)|CC0(?:\s|$)|Public domain(?:\s|$)|PD-)', re.I)
FILE_TYPES=re.compile(r'\.(?:jpg|jpeg|png|webp)$',re.I)
BAD_WORDS=re.compile(r'\b(?:logo|flag|icon|seal|map|coat of arms|cover|cartoon|stamp|portrait|text|screenshot|poster|diagram|drawing)\b', re.I)

STORY_VISUALS={
 'zipper':['zipper metal teeth macro','zipper slider close up','zipper teeth detail fabric','zipper manufacturing sewing','zipper closed jacket detail'],
 'blackhole':['black hole accretion disk simulation','event horizon telescope black hole image','galaxy black hole center','gravitational lensing space','NASA black hole illustration'],
 'brain':['human brain anatomy specimen','neurons microscope image','cerebral cortex close up','synapse neurons micrograph','human brain MRI scan'],
 'jellyfish':['jellyfish underwater closeup','moon jellyfish aquarium','jellyfish tentacles macro','bioluminescent jellyfish','jellyfish swarm sea'],
 'aqueduct':['Pont du Gard Roman aqueduct','Segovia Roman aqueduct arches','Roman aqueduct channel water','Roman aqueduct masonry','ancient Roman aqueduct landscape'],
 'watch':['mechanical watch movement macro','watch escapement balance wheel','mechanical watch gears closeup','watchmaker assembling mechanism','pocket watch mechanism detail'],
 'volcano':['volcano eruption lava fountain','volcano crater aerial','volcanic lava flow close up','volcano ash plume','volcanic rock basalt formation'],
 'bee':['honey bee macro flower','bee pollen baskets hind legs','honeybee honeycomb hive','bees waggle dance honeycomb','beekeeper honeybee hive closeup'],
 'aurora':['aurora borealis northern lights','aurora polar sky Norway','aurora satellite earth atmosphere','aurora green purple curtain','aurora reflected lake'],
 'dna':['DNA molecular model','DNA double helix illustration','DNA gel electrophoresis laboratory','DNA genetics research laboratory','DNA chromosome microscopic image'],
 'anglerfish':['anglerfish deep sea specimen','deep sea anglerfish bioluminescence','anglerfish head teeth deep sea','anglerfish fish specimen museum','deep sea anglerfish underwater'],
 'telescope':['telescope under starry sky','refracting telescope optical tube','reflecting telescope mirror assembly','telescope observatory mount','astronomical telescope observatory'],
}

CATEGORY_HINTS={'Universet':'astronomy space','Naturen':'wildlife nature','Teknologi':'mechanical technology',
                'Mennesket':'biology human anatomy','Historien':'historical archaeology','Jorden':'geology earth science'}

def clean(html):
    return re.sub(r'\s+',' ',unescape(re.sub(r'<[^>]+>',' ',str(html or '')))).strip()

def meta(info,key):
    return clean((info.get('extmetadata') or {}).get(key,{}).get('value',''))

def queries_for(title,category,slug=None):
    if slug in STORY_VISUALS:return STORY_VISUALS[slug]
    keyword=re.sub(r'\s*\([^)]*\)','',title).replace('_',' ').strip()
    # Each search is independently evaluated. No hallucinated tags or prompts.
    return [keyword, keyword+' detail',keyword+' closeup', keyword+' photograph', keyword+' '+CATEGORY_HINTS.get(category,'science')]

def candidates(session,query):
    try:
        res=session.get(API,params={'action':'query','format':'json','formatversion':2,
          'generator':'search','gsrnamespace':6,'gsrsearch':query,'gsrlimit':18,
          'prop':'imageinfo','iiprop':'url|extmetadata|size','iiurlwidth':1100},timeout=20)
        res.raise_for_status()
        return (res.json().get('query') or {}).get('pages',[])
    except (requests.RequestException,ValueError):return []

def phash(im):
    small=im.convert('L').resize((9,8))
    xs=list(small.get_flattened_data() if hasattr(small,'get_flattened_data') else small.getdata());return sum((1<<(row*8+col)) for row in range(8) for col in range(8) if xs[row*9+col]>xs[row*9+col+1])

def eligible(file):
    if not isinstance(file,dict):return False
    title=str(file.get('title',''))
    if not FILE_TYPES.search(title) or BAD_WORDS.search(title):return False
    infos=file.get('imageinfo') or []
    if not infos:return False
    info=infos[0]
    lic=meta(info,'LicenseShortName')
    if not LICENSE.search(lic):return False
    w,h=info.get('width',0),info.get('height',0)
    if min(w,h)<650 or max(w,h)/max(1,min(w,h))>2.55:return False
    url=info.get('thumburl') or info.get('url') or ''
    return url.startswith('https://') and 'wikimedia.org' in url.split('/')[2]

def get_picture(session,info):
    url=info.get('thumburl') or info.get('url','')
    try:
        r=session.get(url,timeout=25,stream=True);r.raise_for_status()
        content=bytearray()
        for chunk in r.iter_content(65536):
            content.extend(chunk)
            if len(content)>3_200_000:return None
        image=ImageOps.exif_transpose(Image.open(BytesIO(content))).convert('RGB')
        if min(image.size)<550:return None
        # Tiny/blank thumbnails are not suitable for a cinematic story.
        if ImageStat.Stat(image.resize((12,12))).stddev[0]<12:return None
        return image
    except (requests.RequestException,OSError,ValueError):return None

def gather_gallery(session,title,category,slug,image_dir,limit_queries=5):
    image_dir=Path(image_dir);image_dir.mkdir(parents=True,exist_ok=True)
    choices=[];seen=set();hashes=[];created=[]
    # Wikimedia is a free public resource, not an unlimited private image API.
    # Hard-stop downloads per story rather than hammering the service.
    downloads=0
    max_downloads=15
    searches=queries_for(title,category,slug)[:limit_queries]
    for i,search in enumerate(searches):
        selected=False
        for candidate in candidates(session,search):
            if downloads>=max_downloads:break
            if not eligible(candidate):continue
            key=candidate.get('title','')
            if key in seen:continue
            info=candidate['imageinfo'][0]
            downloads+=1
            pil=get_picture(session,info)
            if pil is None:continue
            ph=phash(pil)
            if any((ph^other).bit_count()<12 for other in hashes):continue
            # Fitted vertical artwork for full-bleed story cards, not a distorted thumbnail.
            # The original file and licensing details remain credited in each article.
            pil=ImageOps.fit(pil,(600,840),method=Image.Resampling.LANCZOS,centering=(.5,.43))
            path=image_dir/f'{slug}-photo-{i+1}.webp'
            pil.save(path,format='WEBP',quality=77,method=6)
            # Separate lightweight version for mobile-data saving.
            small=image_dir/f'{slug}-photo-{i+1}-small.webp'
            pil.resize((360,504),Image.Resampling.LANCZOS).save(small,format='WEBP',quality=65,method=6)
            src=info.get('descriptionurl') or ''
            credit=' / '.join(filter(None,[meta(info,'Artist')[:100] or 'Wikimedia Commons',meta(info,'LicenseShortName'),src]))
            created.extend([path,small]);choices.append({'image':'images/'+path.name, 'imageSmall':'images/'+small.name, 'credit':credit, 'source':src})
            seen.add(key);hashes.append(ph);selected=True;break
        if not selected:break
    if len(choices)!=5:
        for path in created:path.unlink(missing_ok=True)
        return None
    return choices
