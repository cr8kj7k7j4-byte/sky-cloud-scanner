"""Postmarket all-universe observation using the existing Fugle snapshot reader.

Never upgrades stale or post-close data to an intraday execution signal.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from research.sky_full_universe_information import (
    OUTPUT_DIR, main as read_full_universe, project_required_fields, summary,
)


def mark_observation_only(report: dict) -> dict:
    """Preserve raw source dates/prices while revoking all live trade eligibility."""
    report["research_mode"] = "POSTMARKET_RESEARCH_ONLY"
    report["observation_mode"] = "POSTMARKET_RESEARCH_ONLY"
    report["production_eligible"] = False
    report["trade_signal"] = False
    report["trade_decision"] = "禁止交易"
    report["postmarket_live_execution_certified"] = False
    report["snapshot_data_dates"] = {
        market: (report.get("snapshot_integrity", {}).get(market) or {}).get("snapshot_date")
        for market in ("TWSE", "TPEx")
    }
    report["source_status"] = (
        "OBSERVATION_ONLY" if all(
            (report.get("snapshot_status") or {}).get(market) == "RETURNED"
            for market in ("TWSE", "TPEx")
        ) else "HOLD_INCOMPLETE_SNAPSHOT_SOURCES"
    )
    report["fresh_executed_count"] = 0
    report["fresh_executed_pct"] = 0.0
    for market in ("TWSE", "TPEx"):
        entry = (report.get("by_exchange") or {}).get(market)
        if isinstance(entry, dict):
            entry["fresh_executed"] = 0
            entry["fresh_executed_pct"] = 0.0
    for rows_key in ("all_symbols", "ranked_observations"):
        for row in report.get(rows_key) or []:
            if not isinstance(row, dict):
                continue
            row["intraday_source_status_before_postmarket"] = row.get("data_status")
            row["data_status"] = "POSTMARKET_OBSERVATION_ONLY"
            row["research_only"] = True
            row["production_eligible"] = False
            row["trade_signal"] = False
            row["required_fields"] = project_required_fields(row)
    # The inherited intraday classifier checks snapshot date before price
    # presence. On a legitimate prior-session postmarket snapshot this masks
    # missing-price rows as SNAPSHOT_DATE_NOT_TODAY, including zero-volume rows.
    # Reclassify *diagnostics only*, keeping the original status for audit.
    counts = {"TWSE": 0, "TPEx": 0}
    zero_volume_no_price = 0
    for item in report.get("missing_price_diagnostics") or []:
        if not isinstance(item, dict):
            continue
        item["intraday_diagnostic_status_before_postmarket"] = item.get("data_status")
        item["data_status"] = "POSTMARKET_NO_OBSERVED_PRICE"
        item["postmarket_reason"] = (
            "ZERO_REPORTED_VOLUME_NO_OBSERVED_PRICE"
            if item.get("reported_volume") == 0
            else "NO_OBSERVED_PRICE_CAUSE_UNVERIFIED"
        )
        if item["postmarket_reason"] == "ZERO_REPORTED_VOLUME_NO_OBSERVED_PRICE":
            zero_volume_no_price += 1
        if item.get("exchange") in counts:
            counts[item["exchange"]] += 1
    report["postmarket_missing_price_by_exchange"] = counts
    report["postmarket_zero_reported_volume_no_price_count"] = zero_volume_no_price

    # Canonical cross-system observation contract (research only):
    # a returned Fugle symbol row with verified source date and EXPLICIT numeric
    # zero volume + no observed price is a VALID QUERY, not a VALID PRICE.
    # No snapshot row, unknown volume, stale/unverified source date or trial
    # data must never receive this positive query classification.
    by_symbol = {
        (row.get("exchange"), row.get("symbol")): row
        for row in report.get("all_symbols") or [] if isinstance(row, dict)
    }
    checked_at = report.get("checked_at_tpe")
    try:
        observation_date = datetime.fromisoformat(checked_at).date()
    except (TypeError, ValueError):
        observation_date = None

    def verified_snapshot_row(row):
        market = row.get("exchange")
        metadata = (report.get("snapshot_integrity") or {}).get(market) or {}
        source_date = metadata.get("snapshot_date")
        try:
            actual_date = date.fromisoformat(source_date)
        except (TypeError, ValueError):
            return False
        return (
            market in ("TWSE", "TPEx")
            and (report.get("snapshot_status") or {}).get(market) == "RETURNED"
            and metadata.get("api_response_valid") is True
            and observation_date is not None and actual_date <= observation_date
            and row.get("snapshot_source_date") == source_date
            and row.get("source") == "Fugle paid bulk snapshot"
            and row.get("snapshot_is_trial") is False
        )

    valid_price_queries = 0
    valid_zero_volume_queries = 0
    for row in report.get("all_symbols") or []:
        if not isinstance(row, dict):
            continue
        status = "HOLD_UNVERIFIED_POSTMARKET_QUERY"
        if verified_snapshot_row(row):
            if row.get("last_price") is not None:
                status = "VALID_QUERY_WITH_OBSERVED_PRICE"
                valid_price_queries += 1
            elif type(row.get("volume")) in (int, float) and row["volume"] == 0:
                status = "VALID_QUERY_ZERO_REPORTED_VOLUME_NO_PRICE"
                valid_zero_volume_queries += 1
        row["postmarket_query_status"] = status
        row["postmarket_query_valid"] = status.startswith("VALID_QUERY_")
        # A valid QUERY is never sufficient for execution or price certification.
        row["postmarket_price_valid"] = status == "VALID_QUERY_WITH_OBSERVED_PRICE"
        row["postmarket_executed_trade_certified"] = False
        row["production_eligible"] = False
        row["trade_signal"] = False

    for item in report.get("missing_price_diagnostics") or []:
        if not isinstance(item, dict):
            continue
        row = by_symbol.get((item.get("exchange"), item.get("symbol"))) or {}
        item["postmarket_query_status"] = row.get(
            "postmarket_query_status", "HOLD_UNVERIFIED_POSTMARKET_QUERY"
        )
        item["postmarket_query_valid"] = (
            item["postmarket_query_status"] == "VALID_QUERY_ZERO_REPORTED_VOLUME_NO_PRICE"
            and type(item.get("reported_volume")) in (int, float)
            and item["reported_volume"] == 0
        )
        item["postmarket_price_valid"] = False
        item["official_trading_status"] = "UNVERIFIED"

    research_total = report.get("universe_count")
    valid_query_count = valid_price_queries + valid_zero_volume_queries
    report["postmarket_valid_query_with_price_count"] = valid_price_queries
    report["postmarket_valid_query_zero_volume_no_price_count"] = valid_zero_volume_queries
    report["postmarket_valid_query_count"] = valid_query_count
    report["postmarket_valid_query_pct_research"] = (
        round(100 * valid_query_count / research_total, 2)
        if type(research_total) is int and research_total > 0 else None
    )
    report["postmarket_valid_query_research_complete"] = (
        type(research_total) is int
        and research_total > 0
        and len(report.get("all_symbols") or []) == research_total
        and valid_query_count == research_total
        and report["source_status"] == "OBSERVATION_ONLY"
    )
    report["postmarket_zero_volume_interpretation"] = (
        "Provider-reported volume is zero; query response accepted, but actual "
        "absence of all trading, halt status, price and trade time are not "
        "independently certified. Exclude from trade candidates."
    )
    report["postmarket_coverage_denominator_official"] = (
        report.get("official_universe_count_before_research_exclusion")
    )
    # The official denominator includes excluded research symbols. Those
    # symbols are not falsely represented as observed or trade-eligible.
    official = report["postmarket_coverage_denominator_official"]
    observed = report.get("observed_price_count")
    report["postmarket_observed_price_pct_official_denominator"] = (
        round(100 * observed / official, 2)
        if isinstance(official, int) and official > 0
        and isinstance(observed, int) else None
    )
    report["note"] = (
        "Postmarket observational snapshot. Preserve provider date and capture "
        "time separately; price/volume are NOT certified live executions, "
        "final exchange official totals, entry signals or execution prices."
    )
    return report


def main() -> None:
    # Reuse the exact existing TWSE/TPEx universe and Fugle bulk snapshot calls.
    read_full_universe()
    path = OUTPUT_DIR / "full_universe.json"
    report = mark_observation_only(json.loads(path.read_text(encoding="utf-8")))
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    latest = summary(report)
    latest += (
        "\n## 盤後研究查詢有效性（不等於有效成交或有效價格）\n"
        f"- 已完成有效查詢：{report['postmarket_valid_query_count']}/"
        f"{report['universe_count']} 檔（研究範圍）\n"
        f"- 有價格觀察：{report['postmarket_valid_query_with_price_count']} 檔\n"
        f"- 回報成交量 0、無觀察價格、來源已認證："
        f"{report['postmarket_valid_query_zero_volume_no_price_count']} 檔"
        "（有效查詢／非有效價格／禁止交易）\n"
        f"- 正式全市場分母：{report.get('official_universe_count_before_research_exclusion')} 檔；"
        f"研究排除：{report.get('excluded_research_symbol_count')} 檔"
        "（排除股不計為已完成查詢）\n"
    )
    (OUTPUT_DIR / "latest.md").write_text(latest, encoding="utf-8")
    receipt = {
        "schema": "SKY_POSTMARKET_FULL_UNIVERSE_OBSERVATION_V1",
        "research_mode": "POSTMARKET_RESEARCH_ONLY",
        "checked_at_tpe": report.get("checked_at_tpe"),
        "snapshot_data_dates": report["snapshot_data_dates"],
        "source_status": report["source_status"],
        "universe_count": report.get("universe_count"),
        "observed_price_count": report.get("observed_price_count"),
        "missing_price_count": report.get("missing_price_count"),
        "postmarket_valid_query_with_price_count":
            report.get("postmarket_valid_query_with_price_count"),
        "postmarket_valid_query_zero_volume_no_price_count":
            report.get("postmarket_valid_query_zero_volume_no_price_count"),
        "postmarket_valid_query_count": report.get("postmarket_valid_query_count"),
        "postmarket_valid_query_pct_research":
            report.get("postmarket_valid_query_pct_research"),
        "postmarket_valid_query_research_complete":
            report.get("postmarket_valid_query_research_complete"),
        "postmarket_missing_price_by_exchange":
            report.get("postmarket_missing_price_by_exchange"),
        "postmarket_zero_reported_volume_no_price_count":
            report.get("postmarket_zero_reported_volume_no_price_count"),
        "postmarket_observed_price_pct_official_denominator":
            report.get("postmarket_observed_price_pct_official_denominator"),
        "official_universe_count_before_research_exclusion":
            report.get("official_universe_count_before_research_exclusion"),
        "excluded_research_symbol_count": report.get("excluded_research_symbol_count"),
        "production_eligible": False,
        "trade_signal": False,
        "trade_action": "禁止交易",
    }
    (OUTPUT_DIR / "postmarket_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))
    if report["source_status"] != "OBSERVATION_ONLY":
        raise SystemExit("HOLD_INCOMPLETE_SNAPSHOT_SOURCES")


if __name__ == "__main__":
    main()
