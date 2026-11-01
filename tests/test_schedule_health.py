import tempfile
import unittest
from pathlib import Path
from schedule_health import build_report, schedules

class TestScheduleHealth(unittest.TestCase):
    def test_inventory_finds_real_schedules_only(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'a.yml').write_text("on:\n  schedule:\n    - cron: '5 1 * * 1-5'\n      timezone: Asia/Taipei\n")
            Path(d,'b.yml').write_text("on:\n  workflow_dispatch:\n")
            found=schedules(d)
            self.assertEqual(len(found),1)
            self.assertEqual(found[0]['schedules'][0]['timezone'],'Asia/Taipei')
    def test_states_and_failed_queries_are_not_success(self):
        inv=[{'path':'.github/workflows/'+x+'.yml','schedules':[]} for x in ('ok','disabled','none','error','missing')]
        wf=[{'path':i['path'],'id':j,'state':'disabled_manually' if j==1 else 'active'} for j,i in enumerate(inv[:4])]
        def fetch(i):
            if i==2:return []
            if i==3:raise TimeoutError()
            return [{'id':10+i,'status':'completed','conclusion':'success'}]
        got=build_report(inv,wf,fetch,lambda _:[],'now')['workflows']
        self.assertEqual([x['verdict'] for x in got],['RUN_SUCCEEDED','ATTENTION','UNVERIFIED','UNVERIFIED','UNVERIFIED'])
    def test_failure_and_artifact_failure(self):
        inv=[{'path':'x','schedules':[]}];wf=[{'path':'x','id':1,'state':'active'}]
        fail=build_report(inv,wf,lambda _: [{'id':1,'status':'completed','conclusion':'failure'}],lambda _:[],'now')
        self.assertEqual(fail['workflows'][0]['verdict'],'ATTENTION')
        def err(_): raise TimeoutError()
        no_art=build_report(inv,wf,lambda _: [{'id':1,'status':'completed','conclusion':'success'}],err,'now')
        self.assertEqual(no_art['workflows'][0]['verdict'],'UNVERIFIED')

if __name__=='__main__': unittest.main()
