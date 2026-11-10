"""Read-only inventory of GitHub schedules and their most recent scheduled runs."""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path

import yaml

API = 'https://api.github.com'


def schedules(root):
    found = []
    for path in sorted(Path(root).glob('*.y*ml')):
        doc = yaml.load(path.read_text(encoding='utf-8'), Loader=yaml.BaseLoader) or {}
        triggers = doc.get('on') or {}
        if not isinstance(triggers, dict) or 'schedule' not in triggers:
            continue
        entries = triggers['schedule'] or []
        found.append({'path': '.github/workflows/' + path.name,
                      'schedules': [{'cron': x.get('cron'), 'timezone': x.get('timezone', 'UTC')}
                                    for x in entries if isinstance(x, dict)]})
    return found


def get_json(path):
    repo = os.environ['GITHUB_REPOSITORY']
    token = os.environ['GH_TOKEN']
    req = urllib.request.Request(API + '/repos/' + repo + path,
        headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'sky-schedule-audit'})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def build_report(inventory, workflows, fetch_run, fetch_artifacts, generated_at):
    by_path = {x['path']: x for x in workflows}
    rows = []
    for item in inventory:
        entry = dict(item)
        wf = by_path.get(item['path'])
        if not wf:
            entry.update(state='NOT_REGISTERED', verdict='UNVERIFIED', reason='workflow absent from API')
            rows.append(entry)
            continue
        entry['state'] = wf.get('state', 'unknown')
        entry['workflow_url'] = wf.get('html_url')
        if entry['state'] != 'active':
            entry.update(verdict='ATTENTION', reason='workflow not active')
        try:
            runs = fetch_run(wf['id'])
            if not runs:
                entry.setdefault('verdict', 'UNVERIFIED')
                entry.setdefault('reason', 'no scheduled run found')
            else:
                run = runs[0]
                entry['latest_run'] = {k: run.get(k) for k in ('id', 'status', 'conclusion', 'created_at', 'html_url', 'head_sha')}
                if run.get('status') != 'completed':
                    entry.setdefault('verdict', 'UNVERIFIED')
                    entry.setdefault('reason', 'latest scheduled run not completed')
                elif run.get('conclusion') != 'success':
                    entry.update(verdict='ATTENTION', reason='latest scheduled run not successful')
                else:
                    entry.setdefault('verdict', 'RUN_SUCCEEDED')
                    entry.setdefault('reason', 'execution only; data quality, delivery and timeliness unverified')
                try:
                    artifacts = fetch_artifacts(run['id'])
                    entry['artifacts'] = [{'name': a.get('name'), 'expired': a.get('expired'),
                                           'size_in_bytes': a.get('size_in_bytes')} for a in artifacts]
                except Exception as exc:
                    entry.update(verdict='UNVERIFIED', reason='artifact query failed: ' + type(exc).__name__)
        except Exception as exc:
            entry.update(verdict='UNVERIFIED', reason='run query failed: ' + type(exc).__name__)
        rows.append(entry)
    return {'generated_at_utc': generated_at, 'scope': 'default branch scheduled workflow files',
            'note': 'Success is process status only. Artifacts may be stale, incomplete, empty, expired or not required; inspect contents and delivery separately. No timetable SLA or holiday inference.',
            'workflows': rows}



def intraday_scan_slot_evidence(runs, now):
    """Conservative five-slot diagnostic, never proof of cron identity.

    GitHub's run listing lacks the original schedule expression. Arrival
    timestamps can suggest a slot, but only the schedule_trigger artifact
    can verify exact cron identity, punctuality and missing triggers.
    """
    taipei = ZoneInfo('Asia/Taipei')
    local_now = now.astimezone(taipei)
    day = local_now.date()
    clock_slots = ((9, 5), (9, 15), (9, 30), (9, 50), (10, 15))
    slots = []
    eligible = []
    for record in runs:
        if record.get('event') != 'schedule':
            continue
        try:
            timestamp = datetime.fromisoformat(record['created_at'].replace('Z', '+00:00')).astimezone(taipei)
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if timestamp.date() == day:
            eligible.append((timestamp, record))
    # A run is evidence of execution, not of its actual cron expression.
    # Assign each run to the closest preceding plausible slot only once.
    expected_times = [datetime(day.year, day.month, day.day, hour, minute,
                               tzinfo=taipei) for hour, minute in clock_slots]
    tentative = {}
    for timestamp, run in sorted(eligible, key=lambda pair: pair[0]):
        valid = [(index, expected) for index, expected in enumerate(expected_times)
                 if expected <= timestamp <= expected + timedelta(minutes=30)]
        if not valid:
            continue
        index, expected = max(valid, key=lambda pair: pair[1])
        previous = tentative.get(index)
        if previous is None or timestamp < previous[0]:
            tentative[index] = (timestamp, run)
    for index, expected in enumerate(expected_times):
        picked = tentative.get(index)
        if picked:
            timestamp, run = picked
            state = 'RUN_TIME_MATCH_ONLY_CRON_UNVERIFIED'
            run_id = run.get('id')
            late_seconds = int((timestamp - expected).total_seconds())
        elif local_now < expected + timedelta(minutes=30):
            state, run_id, late_seconds = 'AWAITING_RUN_WINDOW', None, None
        else:
            state, run_id, late_seconds = 'NO_RUN_IN_30M_WINDOW', None, None
        slots.append({'scheduled_at_tpe': expected.isoformat(), 'state': state,
                      'candidate_run_id': run_id, 'start_lag_seconds': late_seconds})
    return {
        'date_tpe': day.isoformat(),
        'expected_slot_count': len(slots),
        'same_day_scheduled_runs_seen': len(eligible),
        'slots': slots,
        'status': 'EVIDENCE_INCOMPLETE' if any(
            x['state'] == 'NO_RUN_IN_30M_WINDOW' for x in slots)
            else 'RUN_TIMES_ONLY_NOT_CRON_CERTIFIED',
        'note': ('Run start-time matching is provisional. Runner creation can be '
                 'delayed or overlap slots; inspect each schedule_trigger.json '
                 'artifact for exact event_schedule_cron_utc and runner time. '
                 'Never treat a workflow success as valid quote coverage.')
    }



def full_market_cadence_evidence(dispatch_runs, private_runs, now):
    """Conservative dispatcher-to-private-run *time* audit, not cron SLA proof.

    GitHub REST run timestamps do not expose original cron fire time or
    dispatch linkage. Approximate time matching must never certify either.
    No provider requests or trade decision logic is executed here.
    """
    taipei = ZoneInfo('Asia/Taipei')
    local_now = now.astimezone(taipei)
    day = local_now.date()

    def same_day(items, expected_event):
        valid = []
        for item in items:
            if item.get('event') != expected_event:
                continue
            try:
                stamped = datetime.fromisoformat(
                    item['created_at'].replace('Z', '+00:00')).astimezone(taipei)
            except (KeyError, AttributeError, TypeError, ValueError):
                continue
            if stamped.date() == day:
                valid.append((stamped, item))
        return sorted(valid, key=lambda entry: entry[0])

    dispatches = same_day(dispatch_runs, 'schedule')
    downstream = same_day(private_runs, 'workflow_dispatch')
    starts = [datetime(day.year, day.month, day.day, h, m, tzinfo=taipei)
              for h in range(9, 14) for m in range(0, 60, 5)
              if (h < 13 or m <= 30)]
    observed = {}
    unassigned = []
    for stamped, run in dispatches:
        possible = [idx for idx, start in enumerate(starts)
                    if start <= stamped <= start + timedelta(minutes=15)]
        if not possible:
            unassigned.append(run.get('id'))
            continue
        # Provisional: a delayed previous cron could be misattributed.
        idx = possible[-1]
        observed.setdefault(idx, []).append((stamped, run))

    private_taken = set()
    slots = []
    for idx, scheduled in enumerate(starts):
        recorded = observed.get(idx, [])
        pending = local_now < scheduled + timedelta(minutes=15)
        if recorded:
            stamped, dispatch = recorded[0]
            state = ('SCHEDULE_RUN_SUCCEEDED_TIME_ONLY'
                     if dispatch.get('status') == 'completed'
                     and dispatch.get('conclusion') == 'success'
                     else 'SCHEDULE_RUN_UNSUCCESSFUL_OR_PENDING')
            private_match = next((
                (stamp, record) for stamp, record in downstream
                if record.get('id') not in private_taken
                and stamped <= stamp <= stamped + timedelta(minutes=10)
            ), None)
            if private_match:
                private_taken.add(private_match[1].get('id'))
            downstream_state = (
                'POSSIBLE_PRIVATE_RUN_TIME_MATCH_NOT_CAUSAL'
                if private_match and private_match[1].get('status') == 'completed'
                and private_match[1].get('conclusion') == 'success'
                else 'POSSIBLE_PRIVATE_RUN_FAILED_OR_PENDING'
                if private_match else 'NO_PRIVATE_RUN_MATCH_WITHIN_10M')
            slots.append({
                'scheduled_at_tpe': scheduled.isoformat(),
                'state': state,
                'dispatch_run_id': dispatch.get('id'),
                'dispatch_created_at_tpe': stamped.isoformat(),
                'delay_seconds_provisional': int((stamped-scheduled).total_seconds()),
                'other_runs_same_provisional_slot': [p.get('id') for _, p in recorded[1:]],
                'downstream_state': downstream_state,
                'private_run_id': private_match[1].get('id') if private_match else None,
            })
        else:
            slots.append({
                'scheduled_at_tpe': scheduled.isoformat(),
                'state': 'AWAITING_15M_WINDOW' if pending else 'NO_SCHEDULE_RUN_SEEN_WITHIN_15M',
                'dispatch_run_id': None, 'private_run_id': None,
                'downstream_state': 'NOT_CHECKED_NO_DISPATCH'
            })

    eligible = [s for s in slots if s['state'] != 'AWAITING_15M_WINDOW']
    missing = sum(s['state'] == 'NO_SCHEDULE_RUN_SEEN_WITHIN_15M' for s in eligible)
    possible_missing_downstream = sum(
        s['state'] == 'SCHEDULE_RUN_SUCCEEDED_TIME_ONLY'
        and s['downstream_state'] == 'NO_PRIVATE_RUN_MATCH_WITHIN_10M'
        for s in eligible)
    return {
        'date_tpe': day.isoformat(),
        'scope': 'Sky paid full-market research dispatcher and private snapshot only',
        'expected_daily_slots': len(starts),
        'elapsed_slot_count': len(eligible),
        'observed_schedule_run_count': len(dispatches),
        'provisionally_matched_slot_count': len(observed),
        'missing_slot_count_after_15m': missing,
        'possible_missing_private_runs': possible_missing_downstream,
        'unassigned_dispatch_run_ids': unassigned,
        'slots': slots,
        'status': 'EVIDENCE_INCOMPLETE' if missing or possible_missing_downstream
                  else 'RUN_TIMES_ONLY_NOT_CRON_CERTIFIED',
        'note': ('GitHub created_at is not original cron fire time; slots are '
                 'provisional, not proof of exact cron identity or SLA. '
                 'Private-run association is by time only, not a causal link. '
                 'A successful workflow cannot certify GCS contents, '
                 'quote freshness, delivery, or trading eligibility.')
    }


def main():
    inv = schedules('.github/workflows')
    workflows = []
    page = 1
    while True:
        batch = get_json('/actions/workflows?per_page=100&page=' + str(page)).get('workflows', [])
        workflows.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    report = build_report(inv, workflows,
        lambda wid: get_json('/actions/workflows/' + str(wid) + '/runs?event=schedule&per_page=1').get('workflow_runs', []),
        lambda rid: get_json('/actions/runs/' + str(rid) + '/artifacts?per_page=100').get('artifacts', []),
        datetime.now(timezone.utc).isoformat())
    scan_wf = next((wf for wf in workflows if wf.get('path') == '.github/workflows/scan.yml'), None)
    if scan_wf is not None:
        try:
            scan_runs = get_json('/actions/workflows/' + str(scan_wf['id']) +
                                 '/runs?event=schedule&per_page=100').get('workflow_runs', [])
            report['intraday_scan_slots'] = intraday_scan_slot_evidence(
                scan_runs, datetime.now(timezone.utc))
        except Exception as exc:
            report['intraday_scan_slots'] = {
                'status': 'UNVERIFIED',
                'reason': 'scheduled scan run listing failed: ' + type(exc).__name__
            }
    dispatcher = next((wf for wf in workflows if wf.get('path') ==
        '.github/workflows/sky-full-market-five-minute-dispatch.yml'), None)
    private_snapshot = next((wf for wf in workflows if wf.get('path') ==
        '.github/workflows/sky-full-market-private.yml'), None)
    if dispatcher is not None and private_snapshot is not None:
        try:
            dispatcher_runs = get_json('/actions/workflows/' +
                str(dispatcher['id']) +
                '/runs?event=schedule&per_page=100').get('workflow_runs', [])
            private_runs = get_json('/actions/workflows/' +
                str(private_snapshot['id']) +
                '/runs?event=workflow_dispatch&per_page=100').get('workflow_runs', [])
            report['full_market_cadence'] = full_market_cadence_evidence(
                dispatcher_runs, private_runs, datetime.now(timezone.utc))
        except Exception as exc:
            report['full_market_cadence'] = {
                'status': 'UNVERIFIED', 'reason': 'run read failed: ' + type(exc).__name__
            }
    else:
        report['full_market_cadence'] = {
            'status': 'UNVERIFIED', 'reason': 'dispatcher or private workflow absent'
        }
    out = Path('output/schedule_health'); out.mkdir(parents=True, exist_ok=True)
    (out / 'latest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# Sky GitHub 排程健檢', '', '檢查時間（UTC）：' + report['generated_at_utc'], '',
             '成功僅表示工作流程執行成功；資料新鮮度、內容、通知送達及準時性仍須各自查核。', '',
             '| 排程 | 狀態 | 最近一次排程觸發 UTC | 執行結論 | 產出數量 |', '| --- | --- | --- | --- | --- |']
    for x in report['workflows']:
        run=x.get('latest_run') or {}
        name=x['path'].rsplit('/', 1)[-1]
        link='['+name+']('+run['html_url']+')' if run.get('html_url') else name
        lines.append('| '+link+' | '+x['verdict']+' | '+str(run.get('created_at') or '無紀錄')+' | '+str(run.get('conclusion') or run.get('status') or '待確認')+' | '+str(len(x.get('artifacts', [])))+' |')
    slot_audit = report.get('intraday_scan_slots', {})
    if slot_audit:
        lines += ['', '## 正式當沖五時段核對（只按 Run 開始時間推測）',
                  '狀態：' + slot_audit.get('status', 'UNVERIFIED')]
        for slot in slot_audit.get('slots', []):
            lines.append('- ' + slot['scheduled_at_tpe'] + '：' + slot['state'] +
                         '；Run=' + str(slot['candidate_run_id']) +
                         '；延遲秒數=' + str(slot['start_lag_seconds']))
        lines += ['**此表不是 cron 觸發證明**；必須核對各 Run 的 schedule_trigger.json artifact。']
    cadence = report.get('full_market_cadence', {})
    lines += ['', '## 全市場研究五分鐘派送驗收（時間匹配，非 cron 準時保證）',
              '狀態：' + cadence.get('status', 'UNVERIFIED'),
              '本交易日預設時段：' + str(cadence.get('expected_daily_slots', '待確認')),
              '已過驗收視窗時段：' + str(cadence.get('elapsed_slot_count', '待確認')),
              '暫未觀察到定時執行（15分鐘窗）：' +
              str(cadence.get('missing_slot_count_after_15m', '待確認')),
              '下游私有掃描未匹配（10分鐘窗）：' +
              str(cadence.get('possible_missing_private_runs', '待確認'))]
    for row in cadence.get('slots', []):
        if row['state'] != 'SCHEDULE_RUN_SUCCEEDED_TIME_ONLY' or row.get(
                'downstream_state') != 'POSSIBLE_PRIVATE_RUN_TIME_MATCH_NOT_CAUSAL':
            lines.append('- ' + row['scheduled_at_tpe'] + ' ' + row['state'] +
                         '；dispatcher=' + str(row.get('dispatch_run_id')) +
                         '；private=' + str(row.get('private_run_id')))
    lines += ['**派送與下游僅依時間暫時匹配，非同次呼叫因果驗證**；'
              '必須另行核對執行時點、GCS 真實產物和資料時間。']
    lines += ['', '無產出檔不一定異常：部分工作流程將結果寫入儲存庫或 GitHub 工作摘要。',
              'NOT_REGISTERED／UNVERIFIED 應檢查是否剛新增、停用、休市、月排程尚未到期或 GitHub API 權限不足。']
    text='\n'.join(lines)+'\n'
    (out/'latest.md').write_text(text, encoding='utf-8')
    print(text)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as f:
            f.write(text)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Schedule audit failed:', type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(1)
