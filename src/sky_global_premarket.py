"""Research-only global premarket report. Missing data must remain visible."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Taipei')
OUTPUT = Path('output/global_premarket')
FIELDS = (('sp500', '標普500'), ('nasdaq', '那斯達克'),
          ('vix', 'VIX'), ('us10y', '美國10年公債殖利率'),
          ('ntdusd', '新台幣匯率'), ('wti', 'WTI原油'))


def render(calendar, context, now):
    lines = [f'Sky 全球盤前掃描｜{now:%Y-%m-%d %H:%M:%S %Z}',
             '用途：市場背景觀察；未經驗證的交易濾網，不構成買賣訊號。',
             f"交易日曆：{calendar.get('status', 'UNKNOWN')}｜來源狀態：{calendar.get('source_status', 'UNKNOWN')}"]
    if calendar.get('source_status') != 'PASS':
        lines.append('交易日曆來源異常，無法確認開市；停止行情判讀。')
        return '\n'.join(lines) + '\n'
    if not calendar.get('market_open'):
        lines.append('台股休市，無盤前交易判讀。')
        return '\n'.join(lines) + '\n'
    for key, label in FIELDS:
        item = context.get(key) or {}
        value, date, source = item.get('value'), item.get('as_of'), item.get('source')
        if value is None or not date or not source:
            lines.append(f'{label}：待確認（未取得完整數值、日期與來源）')
        else:
            lines.append(f"{label}：{value} {item.get('unit', '')}｜資料日期 {date}｜來源 {source}｜即時性待確認｜{item.get('source_url', '')}")
    for key, label, itemkey in [('adr_context', '台積電ADR', 'quotes'), ('gold_context', '黃金', 'quote')]:
        data = context.get(key) or {}
        item = data.get(itemkey)
        if key == 'adr_context' and isinstance(item, list):
            item = next((q for q in item if str(q.get('symbol', '')).upper() in ('TSM', '2330')), None)
        if data.get('status') != 'CONNECTED' or not isinstance(item, dict) or item.get('value') is None or not item.get('as_of'):
            lines.append(f'{label}：待確認（未取得完整報價與時間）')
        else:
            lines.append(f"{label}：{item['value']} {item.get('unit', '')}｜{item['as_of']}｜來源 {item.get('source', data.get('provider', '待確認'))}｜延遲待確認")
    lines.extend(['台指期夜盤：待確認（尚無經驗證的夜盤資料來源）',
                  '費城半導體指數：待確認（尚無經驗證的資料來源）',
                  '判讀：資料不足時，市場方向與新進場條件均待確認；09:05 仍須由正式當沖流程獨立判斷。',
                  '不得將資料缺漏視為利多或低風險；不自動下單。'])
    return '\n'.join(lines) + '\n'


def main():
    from .trading_calendar import check_trading_day
    from .global_market_context import build_global_context
    now = datetime.now(TZ)
    calendar = check_trading_day(now.date())
    context = {}
    if calendar.get('source_status') == 'PASS' and calendar.get('market_open'):
        try:
            context = build_global_context(now=now)
        except Exception as exc:
            context = {'error': type(exc).__name__}
    report = render(calendar, context, now)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'report.txt').write_text(report, encoding='utf-8')
    (OUTPUT / 'snapshot.json').write_text(json.dumps({'generated_at': now.isoformat(), 'calendar': calendar, 'context': context, 'trade_signal': False}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(report)


if __name__ == '__main__':
    main()
