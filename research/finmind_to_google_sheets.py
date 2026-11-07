#!/usr/bin/env python3
"""Publish a validated FinMind query snapshot to a private Google Sheet.

Requires Google Workload Identity Federation via GitHub OIDC; no JSON keys.
Idempotent per (date, symbol): uses Sheets values read and update, no duplicated rows.
Never sends API tokens or trading instructions to Google.
"""
import argparse
import json
from pathlib import Path
import sys

SHEET = "股票日資料樣本"
HEADER = ["資料日期", "代碼", "股票", "開盤", "最高", "最低", "收盤",
          "成交量（股）", "融資餘額API值", "融券餘額API值", "資料來源", "GitHub Run"]


def build_row(payload, run_id):
    if payload.get("overall") != "PASS" or not payload.get("research_only"):
        raise ValueError("data_query_not_accepted")
    symbol = str(payload["symbol"])
    datasets = payload["datasets"]
    price = datasets["price"]["latest_rows"][0]
    margin = datasets["margin"]["latest_rows"][0]
    date = price["date"]
    if margin["date"] != date or price["stock_id"] != symbol or margin["stock_id"] != symbol:
        raise ValueError("cross_dataset_symbol_or_date_mismatch")
    return [date, symbol, "", price["open"], price["max"], price["min"],
            price["close"], price["Trading_Volume"],
            margin["MarginPurchaseTodayBalance"], margin["ShortSaleTodayBalance"],
            "FinMind API v4", str(run_id)]


def publish(credentials, spreadsheet_id, payload, run_id):
    from google.auth.transport.requests import AuthorizedSession
    session = AuthorizedSession(credentials)
    root = "https://sheets.googleapis.com/v4/spreadsheets/" + spreadsheet_id + "/values/"
    target = "'" + SHEET + "'"
    resp = session.get(root + target + "!A1:L2000", timeout=30)
    resp.raise_for_status()
    data = resp.json().get("values", [])
    if not data or data[0] != HEADER:
        raise ValueError("sheet_header_mismatch; refusing_to_write")
    row = build_row(payload, run_id)
    matches = [i+1 for i, existing in enumerate(data) if len(existing) > 1
               and existing[0] == row[0] and existing[1] == row[1]]
    if len(matches) > 1:
        raise ValueError("duplicate_existing_date_symbol; manual_reconciliation_required")
    if matches:
        row_no = matches[0]
        method = "put"
        uri = root + target + "!A" + str(row_no) + ":L" + str(row_no) + "?valueInputOption=RAW"
        action = "updated"
    else:
        method = "post"
        uri = root + target + "!A:L:append?valueInputOption=RAW&insertDataOption=INSERT_ROWS"
        action = "appended"
    response = getattr(session, method)(uri, json={"values": [row]}, timeout=30)
    response.raise_for_status()
    return {"status": "PASS", "action": action, "symbol": row[1], "date": row[0],
            "row_count": 1, "source_run_id": str(run_id)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="research_output/finmind_query_result.json")
    p.add_argument("--sheet-id", required=True)
    p.add_argument("--run-id", required=True)
    args = p.parse_args()
    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    import google.auth
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/spreadsheets"])
    print(json.dumps(publish(credentials, args.sheet_id, data, args.run_id),
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
