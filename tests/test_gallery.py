from pathlib import Path
import sys,tempfile,unittest,random
from unittest.mock import patch
from PIL import Image
ROOT=Path(__file__).parents[1]
sys.path.insert(0,str(ROOT/'content-engine'))
import commons_gallery as cg
class GalleryTest(unittest.TestCase):
 def test_rejects_uncleared_rights(self):
  self.assertFalse(cg.eligible({'title':'File:Volcano.jpg','imageinfo':[{'width':1800,'height':900,'thumburl':'https://upload.wikimedia.org/xx.jpg','extmetadata':{'LicenseShortName':{'value':'CC BY-NC 4.0'}}}]}))
 def test_rejects_search_results_not_linked_from_article(self):
  unrelated={'title':'File:Unrelated.jpg'}
  with tempfile.TemporaryDirectory() as d,patch.object(cg,'article_files',return_value={'File:Real tornado.jpg'}),patch.object(cg,'candidates',return_value=[unrelated]),patch.object(cg,'get_picture',side_effect=AssertionError('Unrelated picture must never download')):
   self.assertIsNone(cg.gather_gallery(None,'Tornado','Jorden','tornado',d))
 def test_chooses_five_unique_photos(self):
  files=[{'title':f'File:Volcano photo {i}.jpg','imageinfo':[{'width':1400,'height':900,'thumburl':'https://upload.wikimedia.org/img'+str(i),'descriptionurl':'https://commons.wikimedia.org/wiki/File:'+str(i),'extmetadata':{'LicenseShortName':{'value':'CC BY-SA 4.0'},'Artist':{'value':'Artist '+str(i)}}}]} for i in range(5)]
  def search(_,query):
   i=min(4,search.n);search.n+=1;return [files[i]]
  search.n=0
  def photo(_,info):
   idx=int(info['thumburl'][-1]);rng=random.Random(idx+345)
   # Distinct detailed images, not the same motif with a different crop.
   im=Image.new('RGB',(600,840));im.putdata([(rng.randrange(255),rng.randrange(255),rng.randrange(255)) for _ in range(600*840)])
   return im
  with tempfile.TemporaryDirectory() as d,patch.object(cg,'candidates',new=search),patch.object(cg,'get_picture',new=photo),patch.object(cg,'article_files',return_value={f['title'] for f in files}):
   gallery=cg.gather_gallery(None,'Vulkan','Jorden','volcano',d)
   self.assertIsNotNone(gallery)
   self.assertEqual(5,len({x['image'] for x in gallery}))
   self.assertTrue(all((Path(d)/Path(x['image']).name).exists() for x in gallery))
   self.assertTrue(all((Path(d)/Path(x['imageSmall']).name).exists() for x in gallery))
if __name__=='__main__':unittest.main()
