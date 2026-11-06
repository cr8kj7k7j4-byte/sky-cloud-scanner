import tempfile
import unittest
from pathlib import Path
from schedule_health import build_report, schedules, intraday_scan_slot_evidence
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

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
    def test_five_slots_show_missing_without_fabricating_runs(self):
        now = datetime(2026, 11, 6, 11, 0, tzinfo=ZoneInfo('Asia/Taipei'))
        runs = [{'id': 42, 'event': 'schedule',
                 'created_at': '2026-11-06T02:00:01Z'}]
        audit = intraday_scan_slot_evidence(runs, now)
        self.assertEqual(audit['expected_slot_count'], 5)
        self.assertEqual(audit['same_day_scheduled_runs_seen'], 1)
        self.assertEqual(sum(x['candidate_run_id'] is not None for x in audit['slots']), 1)
        self.assertEqual(audit['status'], 'EVIDENCE_INCOMPLETE')
        self.assertTrue(all(x['state'] != 'CERTIFIED'
                            for x in audit['slots']))

    def test_before_first_slot_does_not_claim_missing(self):
        now = datetime(2026, 11, 6, 8, 55, tzinfo=ZoneInfo('Asia/Taipei'))
        audit = intraday_scan_slot_evidence([], now)
        self.assertEqual(audit['status'], 'RUN_TIMES_ONLY_NOT_CRON_CERTIFIED')
        self.assertTrue(all(x['state'] == 'AWAITING_RUN_WINDOW'
                            for x in audit['slots']))

    def test_manual_dispatch_cannot_count_as_scheduled(self):
        now = datetime(2026, 11, 6, 11, 0, tzinfo=ZoneInfo('Asia/Taipei'))
        runs = [{'id': 99, 'event': 'workflow_dispatch',
                 'created_at': '2026-11-06T01:05:00Z'}]
        audit = intraday_scan_slot_evidence(runs, now)
        self.assertEqual(audit['same_day_scheduled_runs_seen'], 0)
        self.assertTrue(all(x['candidate_run_id'] is None
                            for x in audit['slots']))

    def test_failure_and_artifact_failure(self):
        inv=[{'path':'x','schedules':[]}];wf=[{'path':'x','id':1,'state':'active'}]
        fail=build_report(inv,wf,lambda _: [{'id':1,'status':'completed','conclusion':'failure'}],lambda _:[],'now')
        self.assertEqual(fail['workflows'][0]['verdict'],'ATTENTION')
        def err(_): raise TimeoutError()
        no_art=build_report(inv,wf,lambda _: [{'id':1,'status':'completed','conclusion':'success'}],err,'now')
        self.assertEqual(no_art['workflows'][0]['verdict'],'UNVERIFIED')

if __name__=='__main__': unittest.main()
