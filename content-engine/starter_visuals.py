#!/usr/bin/env python3
"""Build upgraded picture cards for preinstalled KURIO topics.

Run only on the backend, never on user phones. Photos are hosted with the daily feed.
Starter picture improvements are separate from the one-new-ARTICLE-per-day quota.
"""
import argparse, json, os
from pathlib import Path
import requests
from commons_gallery import STORY_VISUALS, gather_gallery
ROOT=Path(__file__).resolve().parent
SITE=ROOT/'site'

def run(limit=2):
    starters=json.loads((ROOT.parent/'app/src/main/assets/seed.json').read_text(encoding='utf8'))['stories']
    path=SITE/'starter-visuals.json'
    feed=SITE/'feed.json'
    site=json.loads(feed.read_text(encoding='utf8')) if feed.exists() else {'stories':[]}
    current=site.get('starterVisuals') or {}
    agent=os.environ.get('WIKIMEDIA_USER_AGENT') or 'KurioDiscovery/1.2 (https://kuriothinkthrough.netlify.app/; support contact through site)'
    session=requests.Session();session.headers['User-Agent']=agent
    completed=0
    attempted=0
    for story in starters:
        slug=story['id']
        if slug in current or slug not in STORY_VISUALS:continue
        if attempted>=3:break
        attempted+=1
        pictures=gather_gallery(session,story['title'],story['category'],slug,SITE/'images')
        if not pictures:continue
        current[slug]={'slides':[{'image':p['image'],'imageSmall':p['imageSmall'],'credit':p['credit']} for p in pictures]}
        completed+=1
        if completed>=limit:break
    site['starterVisuals']=current
    feed.write_text(json.dumps(site,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Upgraded',completed,'starter story galleries; total:',len(current))
    return completed

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int,default=2)
    run(max(1,min(12,parser.parse_args().limit)))
