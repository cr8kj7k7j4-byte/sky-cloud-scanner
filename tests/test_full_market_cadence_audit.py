"""Offline fail-closed contracts for the research five-minute schedule audit."""
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from schedule_health import full_market_cadence_evidence

TPE = ZoneInfo('Asia/Taipei')


def run(identifier, local_time, event='schedule', conclusion='success'):
    stamp = datetime(2026, 11, 10, *local_time, tzinfo=TPE)
    return {
        'id': identifier,
        'event': event,
        'created_at': stamp.isoformat(),
        'status': 'completed',
        'conclusion': conclusion,
    }


class FullMarketCadenceTests(unittest.TestCase):
    def test_55_slots_and_no_runs_means_missing_after_maturity(self):
        now = datetime(2026, 11, 10, 11, 20, tzinfo=TPE)
        evidence = full_market_cadence_evidence([], [], now)
        self.assertEqual(evidence['expected_daily_slots'], 55)
        self.assertGreater(evidence['missing_slot_count_after_15m'], 0)
        self.assertLess(evidence['elapsed_slot_count'], 55)
        self.assertEqual(evidence['status'], 'EVIDENCE_INCOMPLETE')

    def test_valid_dispatch_and_private_time_match_not_approval(self):
        now = datetime(2026, 11, 10, 9, 20, tzinfo=TPE)
        evidence = full_market_cadence_evidence(
            [run(42, (9, 1))],
            [run(55, (9, 2), event='workflow_dispatch')],
            now)
        first = evidence['slots'][0]
        self.assertEqual(first['dispatch_run_id'], 42)
        self.assertEqual(first['private_run_id'], 55)
        self.assertEqual(first['state'], 'SCHEDULE_RUN_SUCCEEDED_TIME_ONLY')
        self.assertEqual(first['downstream_state'],
                         'POSSIBLE_PRIVATE_RUN_TIME_MATCH_NOT_CAUSAL')
        self.assertNotIn('CERTIFIED', first['state'])
        self.assertNotIn('ELIGIBLE', evidence['status'])

    def test_manual_dispatch_cannot_forge_scheduled_success(self):
        now = datetime(2026, 11, 10, 9, 20, tzinfo=TPE)
        evidence = full_market_cadence_evidence(
            [run(99, (9, 1), event='workflow_dispatch')], [], now)
        self.assertEqual(evidence['observed_schedule_run_count'], 0)
        self.assertEqual(evidence['slots'][0]['state'],
                         'NO_SCHEDULE_RUN_SEEN_WITHIN_15M')

    def test_failed_dispatch_and_private_are_not_success(self):
        now = datetime(2026, 11, 10, 9, 20, tzinfo=TPE)
        evidence = full_market_cadence_evidence(
            [run(42, (9, 1), conclusion='failure')],
            [run(55, (9, 2), event='workflow_dispatch', conclusion='failure')],
            now)
        self.assertEqual(evidence['slots'][0]['state'],
                         'SCHEDULE_RUN_UNSUCCESSFUL_OR_PENDING')
        self.assertEqual(evidence['slots'][0]['downstream_state'],
                         'POSSIBLE_PRIVATE_RUN_FAILED_OR_PENDING')

    def test_duplicate_dispatch_and_unlinked_private_are_distinct(self):
        now = datetime(2026, 11, 10, 9, 20, tzinfo=TPE)
        evidence = full_market_cadence_evidence(
            [run(41, (9, 1)), run(42, (9, 2))],
            [run(77, (9, 19), event='workflow_dispatch')],
            now)
        self.assertEqual(evidence['observed_schedule_run_count'], 2)
        self.assertEqual(evidence['provisionally_matched_slot_count'], 1)
        self.assertEqual(evidence['slots'][0]['other_runs_same_provisional_slot'], [42])
        self.assertEqual(evidence['slots'][0]['downstream_state'],
                         'NO_PRIVATE_RUN_MATCH_WITHIN_10M')

    def test_other_day_and_invalid_timestamp_excluded(self):
        now = datetime(2026, 11, 10, 9, 20, tzinfo=TPE)
        yesterday = run(91, (9, 1))
        yesterday['created_at'] = '2026-11-09T09:01:00+08:00'
        evidence = full_market_cadence_evidence(
            [yesterday, {'id': 92, 'event': 'schedule', 'created_at': 'bad'}],
            [], now)
        self.assertEqual(evidence['observed_schedule_run_count'], 0)


if __name__ == '__main__':
    unittest.main()
