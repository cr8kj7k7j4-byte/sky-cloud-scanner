"""Read-only inventory of GitHub schedules and their most recent scheduled runs."""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
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
