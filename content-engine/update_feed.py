#!/usr/bin/env python3
"""KURIO's zero-AI-cost static content updater.

Uses Danish Wikipedia text with CC BY-SA attribution, and downloads only
license-verified Commons images. Never hotlinks full images, never publishes
images with unclear rights. See LICENSES.md for license/credit details.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import quote

import requests
from PIL import Image, ImageOps, UnidentifiedImageError
from commons_gallery import gather_gallery

ROOT = Path(__file__).resolve().parent
SITE = ROOT / 'site'
IMAGES = SITE / 'images'
API = 'https://da.wikipedia.org/w/api.php'
COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
MAX_STORIES = 180
MAX_ATTEMPTS = 4  # absolute cap on candidate lookups per scheduled run
MAX_NEW_PER_DAY = 1  # at most one full story in any UTC day
MAX_PHOTOS_PER_STORY = 6
MAX_SLIDES_PER_STORY = 5
LICENSE_URL = 'https://creativecommons.org/licenses/by-sa/4.0/'
ACCENTS = {'Naturen':'#a1e6c6','Universet':'#c6a8fe','Teknologi':'#f3d199',
           'Historien':'#ffd3a4','Jorden':'#ff9e7e','Mennesket':'#90cef5'}

class HTMLStrip(HTMLParser):
    def __init__(self): super().__init__(); self.result=[]
    def handle_data(self, data): self.result.append(data)

def strip_html(value):
    s=HTMLStrip();s.feed(str(value));return re.sub(r'\s+',' ',unescape(''.join(s.result))).strip()

def metadata_value(ext,key):return strip_html(ext.get(key,{}).get('value',''))

def safe_slug(title):
    out=re.sub('[^a-z0-9]+','-',title.lower().replace('æ','ae').replace('ø','oe').replace('å','aa'))
    return out.strip('-')[:70]

def split_text(extract):
    """Separate readable, non-repeated sourced statements, never invent facts.

    References, link-list fragments and templates are not a premium story.
    """
    parts = re.split(r'(?<=[.!?])\s+(?=[A-ZÆØÅÉ0-9])', extract)
    results = []
    seen = set()
    fingerprints = []
    for sentence in parts:
        line = re.sub(r'\s+', ' ', sentence).strip()
        if not 42 <= len(line) <= 470:
            continue
        if re.search(r'(?:se også|eksterne links|kilder og noter|ISBN|https?://|redigér|\[\d+\])',line,re.I):
            continue
        key = re.sub(r'[^a-zæøå0-9]+','',line.lower())[:130]
        if key in seen:continue
        # Near-identical items with changed numbers are not interesting facts.
        words=set(re.findall(r'[a-zæøå]{4,}',line.lower()))
        if any(len(words & previous)/max(1,len(words | previous))>.85 for previous in fingerprints):continue
        fingerprints.append(words)
        seen.add(key)
        results.append(line)
    return results

CURIOSITY = re.compile(r'\b(?:første|sidste|størst|mindst|hurtig|langsomm|sjælden|opdag|overrask|forsk|million|milliard|tusind|grader|meter|kilometer|dage|år|måne|jord|sol|verden|særligt|eksempel)\b|\d',re.I)

def select_editorial_content(sentences):
    """Source-only editorial layout; article is rejected if it cannot be filled cleanly.

    We deliberately avoid calling this AI rewriting or fact checking. It is
    deterministic selection from Wikipedia sentences with duplicate suppression.
    """
    if len(sentences) < 40:
        return None
    # Reserve the most introductory sentences for meaningful 5-card progression.
    # Different card headings are a layout convention; the actual claims are quoted
    # by paraphrase-free extraction to avoid hallucinated facts.
    # Five readable hooks selected from the first portion of the article, not
    # blindly the first five sentences. Keep original order for narrative flow.
    opening=sentences[:min(20,len(sentences))]
    def hook_score(sentence):
        return (2 if CURIOSITY.search(sentence) else 0) + (2 if 75<=len(sentence)<=240 else 0) + (1 if '?' in sentence else 0)
    selected_indices=sorted(sorted(range(len(opening)),key=lambda i:(-hook_score(opening[i]),i))[:5])
    if len(selected_indices)!=5:return None
    slides=[opening[i] for i in selected_indices]
    slide_set=set(slides)
    remaining=[sentence for sentence in sentences if sentence not in slide_set]
    trivia=[v for v in remaining if CURIOSITY.search(v)]
    # Protect the difference between facts and curiosity by giving these
    # priority in the most striking passages; never reuse an exact sentence.
    if len(trivia)<10:return None
    trivia=sorted(trivia,key=lambda x:(-int(bool(re.search(r'\d',x))),-min(len(x),220)))[:10]
    trivia_ids=set(trivia)
    facts=[v for v in remaining if v not in trivia_ids][:10]
    if len(facts)!=10:return None
    used=set(slides+trivia+facts)
    extra=[v for v in sentences if v not in used]
    # At least three substantial different source statements per chapter.
    if len(extra)<15:return None
    sections=[' '.join(extra[i*3:i*3+3])[:2000] for i in range(5)]
    if any(len(ch)<200 for ch in sections):return None
    return slides,facts,trivia,sections

def get_page(session,title):
    response=session.get(API,params={'action':'query','format':'json','redirects':1,
             'prop':'extracts|pageimages|info','explaintext':1,'piprop':'name',
             'titles':title},timeout=16)
    response.raise_for_status()
    pages=response.json().get('query',{}).get('pages',{})
    return next(iter(pages.values()),{})

def fetch_verified_photo(session,pageimage,slug):
    """Returns (relative_path, credit) or (None,None). Only files with recognized licenses."""
    if not pageimage or not re.match(r'^[^\r\n]{3,180}$',pageimage):return None,None
    try:
        res=session.get(COMMONS_API,params={'action':'query','format':'json','titles':'File:'+pageimage,
            'prop':'imageinfo','iiprop':'extmetadata|url','iiurlwidth':820},timeout=18)
        res.raise_for_status()
        pages=res.json().get('query',{}).get('pages',{})
        file=next(iter(pages.values()),{})
        info=(file.get('imageinfo') or [None])[0]
        if not info:return None,None
        ext=info.get('extmetadata') or {}
        license_name=metadata_value(ext,'LicenseShortName')
        allowed=bool(re.search(r'^(?:CC\s*BY(?:-SA)?(?:\s|$)|CC0(?:\s|$)|Public domain(?:\s|$)|PD-)',license_name,re.I))
        if not allowed:return None,None
        picture=info.get('thumburl') or info.get('url','')
        if not picture.startswith('https://'):return None,None
        d=session.get(picture,timeout=25,stream=True)
        d.raise_for_status()
        size=0; pieces=[]
        for chunk in d.iter_content(48_000):
            size+=len(chunk)
            if size>3_000_000:return None,None
            pieces.append(chunk)
        pil=Image.open(BytesIO(b''.join(pieces)))
        if pil.width<320 or pil.height<220:return None,None
        # Keep the licensed composition; don't crop or obscure image content on disk.
        pil=ImageOps.exif_transpose(pil).convert('RGB')
        pil.thumbnail((820,1100),Image.Resampling.LANCZOS)
        IMAGES.mkdir(parents=True,exist_ok=True)
        target=IMAGES/(slug+'.webp')
        pil.save(target,format='WEBP',quality=77,method=5)
        pil_small=pil.copy();pil_small.thumbnail((360,504),Image.Resampling.LANCZOS)
        pil_small.save(IMAGES/(slug+'-small.webp'),format='WEBP',quality=65,method=6)
        license_url=metadata_value(ext,'LicenseUrl')
        credit=metadata_value(ext,'Artist')[:180] or 'Wikimedia Commons'
        description=metadata_value(ext,'Credit')[:120]
        credit_text=f'{credit} · {license_name} · {info.get("descriptionurl", "https://commons.wikimedia.org/wiki/File:"+quote(pageimage))}'
        if license_url:credit_text+=f' · {license_url}'
        return 'images/'+target.name,credit_text
    except (requests.RequestException,ValueError,OSError,UnidentifiedImageError) as err:
        print('  photo skipped:',str(err)[:110]);return None,None

def build_story(session,topic):
    p=get_page(session,topic['title'])
    if 'missing' in p or 'invalid' in p:return None
    extract=re.sub(r'\s+',' ',p.get('extract','')).strip()[:28000]
    sentences=split_text(extract)
    if len(extract)<2800:return None
    selected=select_editorial_content(sentences)
    if selected is None:return None
    slide_bodies,facts,trivia,chapter_bodies=selected
    title=p.get('title') or topic['title']
    category=topic['category']; slug=safe_slug(title)
    src=f'https://da.wikipedia.org/w/index.php?oldid={p["lastrevid"]}' if p.get('lastrevid') else 'https://da.wikipedia.org/wiki/'+quote(title.replace(' ','_'))
    short_headings=['Det første du skal vide','Sådan hænger det sammen','Det afgørende princip','Det overraskende perspektiv','Det sidste du bør huske']
    slides=[{'title':name,'body':slide_bodies[i]} for i,name in enumerate(short_headings)]
    section_titles=['Den store sammenhæng','Et nærmere kig','Mere end man tror','Hvad kilderne fortæller','Det større perspektiv']
    sections=[{'title':section_titles[i],'body':ch} for i,ch in enumerate(chapter_bodies)]
    article=[' '.join(sentences[:3])[:800]]
    # Only generate assets for stories that satisfy the mandatory document schema.
    image,credit=fetch_verified_photo(session,p.get('pageimage'),slug)
    # Hero quality gate: do not publish abstract category placeholders as new
    # "premium" stories. No suitably licensed hero image means skip today.
    if not image: return None
    photos=gather_gallery(session,title,category,slug,IMAGES)
    if not photos:
        # Never keep photos of stories we did not publish.
        (IMAGES/(slug+'.webp')).unlink(missing_ok=True)
        (IMAGES/(slug+'-small.webp')).unlink(missing_ok=True)
        return None
    for index,slide in enumerate(slides):
        slide['image']=photos[index]['image']
        slide['imageSmall']=photos[index]['imageSmall']
        slide['image_credit']=photos[index]['credit']
    return {
      'id':'wiki-'+slug,'title':title,'kicker':category.upper(),
      'subtitle':sentences[0][:210],'category':category,'minutes':'7–9 min',
      'accent':ACCENTS.get(category,'#ebcb9f'),
      'image':image, 'imageSmall':'images/'+slug+'-small.webp',
      'slides':slides,'article':article,
      'facts':facts,'didYouKnow':trivia,'articleSections':sections,
      'source':{'title':'Dansk Wikipedia, kilde og bidragydere','url':src,
                 'license':'Bearbejdede tekstuddrag fra Wikipedia, CC BY-SA 4.0: '+LICENSE_URL},
      'image_credit':credit or 'Konceptillustration genereret lokalt med SVG (ingen foto).',
      'illustration_credit':'Fem selvstændige Commons-billeder er udvalgt og beskåret til KURIO. Fotokrediteringer og licenser fremgår nedenfor.',
      'created':datetime.now(timezone.utc).date().isoformat()
    }

def make_svg(category):
    """Pretty abstract illustrations; never fabricate a technical explanation."""
    palette={
      'Naturen':('#0a343b','#32c5ba','#ebd69d'),'Universet':('#171431','#a393ff','#ffad60'),
      'Teknologi':('#28201d','#ecbf6c','#78c4e5'),'Historien':('#29211f','#cd966d','#fed2a2'),
      'Jorden':('#31151c','#e9805d','#f9cf7c'),'Mennesket':('#16253a','#83c1ea','#f5b27d')}
    a,b,c=palette.get(category,('#161e2c','#d1ae8a','#abc'))
    circles=''.join(f'<circle cx="{(i*79+80)%650}" cy="{(i*133+80)%900}" r="{2+i%3}" fill="{c}" opacity=".55"/>' for i in range(100))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 650 940">
    <defs><radialGradient id="rad"><stop stop-color="{b}" stop-opacity=".66"/><stop offset="1" stop-color="{a}"/></radialGradient>
    <linearGradient id="shine" x1="0" y1="0" x2="1" y2="1"><stop stop-color="{c}"/><stop offset="1" stop-color="{b}"/></linearGradient></defs>
    <rect width="650" height="940" fill="{a}"/>{circles}
    <circle cx="330" cy="420" r="260" fill="url(#rad)" opacity=".7"/>
    <g fill="none" stroke="url(#shine)" stroke-width="3" opacity=".82">
    <ellipse cx="325" cy="420" rx="236" ry="110" transform="rotate(-35 325 420)"/>
    <ellipse cx="325" cy="420" rx="210" ry="180" transform="rotate(38 325 420)"/>
    <ellipse cx="325" cy="420" rx="270" ry="210" transform="rotate(88 325 420)"/>
    </g><circle cx="325" cy="420" r="115" fill="url(#shine)" opacity=".83"/>
    <circle cx="289" cy="367" r="70" fill="#ffffff" opacity=".15"/>
    <circle cx="491" cy="555" r="22" fill="{c}"/>
    <circle cx="140" cy="320" r="12" fill="{b}"/></svg>'''

def run(limit,seed_today=False):
    SITE.mkdir(exist_ok=True)
    items=json.loads((ROOT/'topics.json').read_text(encoding='utf-8'))
    output=SITE/'feed.json'
    feed=json.loads(output.read_text(encoding='utf-8')) if output.exists() else {'stories':[]}
    existing={s['id'] for s in feed['stories']}
    # Hard UTC-day quotas persist through re-runs and manual workflow launches.
    # A failed or unsatisfactory run is NOT retried automatically that day.
    now=datetime.now(timezone.utc)
    date=now.date().isoformat()
    state_path=SITE/'automation-state.json'
    try:
        state=json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    except (ValueError,OSError):
        state={}
    todays_published=sum(1 for story in feed['stories'] if story.get('created')==date)
    if state.get('date')==date or todays_published>=MAX_NEW_PER_DAY:
        print('Daily safeguard: already attempted or published today; no extra Wikimedia calls.')
        return 0
    limit=min(int(limit),MAX_NEW_PER_DAY-todays_published)
    if limit<=0:
        print('Daily quota exhausted.')
        return 0
    # Write the guard BEFORE the first external API call. CI saves it in git.
    state={'date':date,'searched':0,'published':0,'max_new_per_day':MAX_NEW_PER_DAY,
           'max_candidate_lookups':MAX_ATTEMPTS,'mode':'licensed-commons-five-real-photos-no-paid-ai'}
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    offset=0 if seed_today else now.toordinal()%len(items)
    repo=os.getenv('GITHUB_REPOSITORY','local/KURIO')
    agent=os.getenv('WIKIMEDIA_USER_AGENT') or f'KurioDiscovery/1.0 (https://github.com/{repo}; informational educational tool)'
    session=requests.Session();session.headers.update({'User-Agent':agent,'Accept':'application/json'})
    count=0
    for j in range(min(len(items),MAX_ATTEMPTS)):
        if count>=limit:break
        topic=items[(offset+j)%len(items)];slug=safe_slug(topic['title'])
        if 'wiki-'+slug in existing:continue
        state['searched']+=1
        print('checking:',topic['title'],flush=True)
        try:story=build_story(session,topic)
        except (requests.RequestException,ValueError,KeyError) as ex:
            print('  skipped:',str(ex)[:125]);continue
        if story is None:
            print('  not enough text');continue
        if story['id'] in existing:continue
        feed['stories'].insert(0,story)
        existing.add(story['id']);count+=1
        print('  added:',story['title'],'photo:',bool(story.get('image_credit') and 'Wikimedia' not in story.get('image_credit','')))
        time.sleep(.5)
    state['published']=count
    state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if count:
        feed['stories']=feed['stories'][:MAX_STORIES]
        # Keep the online file archive bounded as old stories age out.
        keep=set()
        for story in feed['stories']:
            for key in ('image','imageSmall'):
                if str(story.get(key,'')).startswith('images/'):
                    keep.add(Path(story[key]).name)
            for slide in story.get('slides',[]):
                for key in ('image','imageSmall'):
                    if str(slide.get(key,'')).startswith('images/'):
                        keep.add(Path(slide[key]).name)
        for visual in (feed.get('starterVisuals') or {}).values():
            for slide in visual.get('slides',[]):
                for key in ('image','imageSmall'):
                    if str(slide.get(key,'')).startswith('images/'):
                        keep.add(Path(slide[key]).name)
        if IMAGES.exists():
            for img in IMAGES.iterdir():
                if img.is_file() and img.name.endswith('.webp') and img.name not in keep:
                    img.unlink()
        feed['updated']=now.isoformat()
        output.write_text(json.dumps(feed,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    else:print('No new articles; feed unchanged.')
    # Keep the free static site bounded; delete images of expired cards.
    used={Path(story.get(key,'')).name for story in feed['stories'] for key in ('image','imageSmall')}
    used.update(Path(slide.get(key,'')).name for story in feed['stories'] for slide in story.get('slides',[]) for key in ('image','imageSmall'))
    used.update(Path(slide.get(key,'')).name for story in (feed.get('starterVisuals') or {}).values() for slide in story.get('slides',[]) for key in ('image','imageSmall'))
    for old in IMAGES.glob('*.webp'):
        if old.name not in used: old.unlink(missing_ok=True)
    IMAGES.mkdir(parents=True,exist_ok=True)
    for cat in ACCENTS:
        name=IMAGES/('abstract-'+cat.lower()+'.svg');name.write_text(make_svg(cat),encoding='utf-8')
    print(f'Feed: {len(feed["stories"])} articles. {count} added.')
    return count

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int,default=1);parser.add_argument('--start-at-first',action='store_true')
    args=parser.parse_args();run(min(max(args.limit,1),MAX_NEW_PER_DAY),args.start_at_first)
