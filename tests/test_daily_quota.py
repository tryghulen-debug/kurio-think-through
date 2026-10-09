import json, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'content-engine'))
import update_feed as e

class DailyQuotas(unittest.TestCase):
 def test_caps_fixed(self):
  self.assertEqual(e.MAX_NEW_PER_DAY,1)
  self.assertEqual(e.MAX_ATTEMPTS,4)
  self.assertEqual(e.MAX_STORIES,180)
 def test_second_run_same_utc_day_no_requests(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'topics.json').write_text(json.dumps([{'title':'Test','category':'Naturen'}]))
   site=root/'site';site.mkdir();(site/'feed.json').write_text(json.dumps({'stories':[]}))
   today=datetime.now(timezone.utc).date().isoformat()
   (site/'automation-state.json').write_text(json.dumps({'date':today,'published':0}))
   with patch.object(e,'ROOT',root),patch.object(e,'SITE',site),patch('requests.Session',side_effect=AssertionError('Network call not allowed')):
    self.assertEqual(e.run(100),0)
 def test_existing_story_today_prevents_new_one(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'topics.json').write_text(json.dumps([{'title':'Test','category':'Naturen'}]))
   site=root/'site';site.mkdir();today=datetime.now(timezone.utc).date().isoformat()
   (site/'feed.json').write_text(json.dumps({'stories':[{'id':'one','created':today}]}))
   with patch.object(e,'ROOT',root),patch.object(e,'SITE',site),patch('requests.Session',side_effect=AssertionError('Network call not allowed')):
    self.assertEqual(e.run(100),0)
if __name__=='__main__':unittest.main()
