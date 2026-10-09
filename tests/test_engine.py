import io,sys,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'content-engine'))
import update_feed as engine
class Resp:
 def __init__(self,json=None,raw=None):self.j=json;self.raw=raw
 def json(self):return self.j
 def raise_for_status(self):return None
 def iter_content(self,size):yield self.raw
class Session:
 def __init__(self,license_name):self.license=license_name
 def get(self,url,params=None,**kw):
  if url==engine.API:
   subjects=['lysets bølgelængder','dråbernes størrelse','solens højde','skygger i atmosfæren',
   'vinklen mellem lys og regn','molekylers optiske brydning','farvernes indbyrdes rækkefølge',
   'tågens små vandpartikler','observatørens placering','polariseret lys','sekundære regnbuer',
   'jordens skiftende vejr','opdagelser inden for optik','sollys og spredning','fysiske målinger',
   'prismers geometri','regnbuernes cirkelform','farvespektret','luftens fugtighed',
   'dobbeltrefleksion','højere luftlag','geografiske variationer','regndråbers bevægelse',
   'særlige observationsforhold','forskernes målemetoder','naturligt modlys','lysstrålens bane',
   'billeddannelse i øjet','videnskabelig historie','udforskning i laboratorier',
   'meteorologiske modeller','en regnskys udvikling','naturfænomener i bjergene',
   'forskellige klimazoner','solens lysfordeling','spektrometres funktion','havets vanddamp',
   'oplevelsen fra fly','lysets hastighed','menneskers farvesyn','optik i glas',
   'kameralinsernes virkemåde','refleksion fra overflader','observationskunst',
   'vejrstationers registrering','følger af lufttemperatur','himlens synlige farver',
   'naturen om morgenen','energi i elektromagnetiske bølger','større fysikforsøg',
   'sæsonernes forandring','måling af regnintensitet','belysning i landskaber',
   'forskellen mellem skyer','atmosfærens sammensætning']
   extract=' '.join(f'Det interessante forhold omkring {subject} kan forklares ved en særlig fysisk proces, hvor man observerer resultatet fra forskellige vinkler nummer {i+1}.' for i,subject in enumerate(subjects))
   return Resp({'query':{'pages':{'1':{'title':'Regnbue','extract':extract,'lastrevid':1234,'pageimage':'Rainbow.jpg'}}}})

  if url==engine.COMMONS_API:
   return Resp({'query':{'pages':{'1':{'imageinfo':[{'thumburl':'https://upload.wikimedia.org/mock.webp','extmetadata':{'LicenseShortName':{'value':self.license},'Artist':{'value':'Photo Author'}},'descriptionurl':'https://commons.wikimedia.org/wiki/File:Rainbow.jpg'}]}}}})
  img=Image.new('RGB',(550,800),'#ff9e7e');b=io.BytesIO();img.save(b,format='WEBP');return Resp(raw=b.getvalue())
class SmokeEngine(unittest.TestCase):
 def test_slug(self):self.assertEqual(engine.safe_slug('Øje og blåbær'),'oeje-og-blaabaer')
 def gallery_stub(self,session,title,category,slug,folder):
  folder.mkdir(parents=True,exist_ok=True)
  arr=[]
  for i in range(5):
   photo=folder/f'{slug}-photo-{i+1}.webp';Image.new('RGB',(550,800),(i*38,85,165)).save(photo,'WEBP');arr.append({'image':'images/'+photo.name, 'imageSmall':'images/'+photo.name,'credit':'Example photographer / CC BY-SA 4.0'})
  return arr
 def test_scientific_excerpts(self):
  with patch.object(engine,'IMAGES',ROOT/'tests'/'tmp_images'),patch.object(engine,'gather_gallery',side_effect=self.gallery_stub):
   story=engine.build_story(Session('CC BY-SA 4.0'),{'title':'Regnbue','category':'Jorden'})
   self.assertEqual(story['id'],'wiki-regnbue')
   self.assertEqual(story['source']['url'],'https://da.wikipedia.org/w/index.php?oldid=1234')
   self.assertTrue(story['image_credit'].startswith('Photo Author'))
   self.assertEqual(len(story['slides']),5)
   self.assertEqual(len(story['facts']),10)
   self.assertEqual(len(story['didYouKnow']),10)
   self.assertEqual(len(story['articleSections']),5)
   self.assertEqual(len({x['image'] for x in story['slides']}),5)
   self.assertFalse(set(story['facts']) & set(story['didYouKnow']))
   self.assertFalse(set(x['body'] for x in story['slides']) & set(story['facts']))
   for slide in story['slides']: self.assertTrue((engine.IMAGES/Path(slide['image']).name).exists())
   for temporary in engine.IMAGES.iterdir():temporary.unlink()
   engine.IMAGES.rmdir()
 def test_no_noncommercial_image(self):
  with patch.object(engine,'IMAGES',ROOT/'tests'/'tmp_images'):
   path,credit=engine.fetch_verified_photo(Session('CC BY-NC 4.0'),'Rainbow.jpg','bad')
   self.assertIsNone(path)
if __name__=='__main__':unittest.main()
