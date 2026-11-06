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
    # A run is evidence of execution, not of the cron expression that caused it.
    # Never count one run toward two slots. Keep attribution explicitly tentative.
    unused = eligible[:]
    for hour, minute in clock_slots:
        expected = datetime(day.year, day.month, day.day, hour, minute, tzinfo=taipei)
        candidates = [(timestamp, run) for timestamp, run in unused
                      if expected <= timestamp <= expected + timedelta(minutes=30)]
        picked = min(candidates, key=lambda item: item[0] - expected) if candidates else None
        if picked:
            unused.remove(picked)
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
