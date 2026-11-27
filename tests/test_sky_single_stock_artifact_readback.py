"""Offline regression for W0 same-run single-stock artifact integrity."""
import json
from pathlib import Path

from scripts.sky_single_stock_artifact_readback import receipt, PASS, HOLD

SHA = "a" * 40


def fixtures(tmp_path, *, unified=True):
    src, dst = tmp_path / "local", tmp_path / "downloaded"
    src.mkdir()
    dst.mkdir()
    audit = {
        "schema": "SKY_5M_TRADES_BOUND_SOURCE_V1", "symbol": "3717",
        "five_minute_status": "HOLD", "trades_status": "HOLD",
        "production_eligible": False, "automatic_order": False,
        "execution_authorized": False,
    }
    files = {
        "3717-5m-source.json": json.dumps(audit),
        "3717-5m-source.md": "HOLD: 5m and VWAP are not certified\n",
    }
    if unified:
        files["3717.json"] = json.dumps({
            "schema": "SKY_UNIFIED_SINGLE_STOCK_RESEARCH_V1",
            "symbol": "3717", "source_audit": audit,
            "observation": {"execution_authorized": False},
            "execution_authorized": False,
        })
        files["3717.md"] = "Sky 分析 3717｜NO_TRADE\n"
    for name, content in files.items():
        (src / name).write_text(content, encoding="utf-8")
        (dst / name).write_text(content, encoding="utf-8")
    return src, dst


def verify(src, dst, **kwargs):
    return receipt(local=src, downloaded=dst, symbol="3717",
                   run_id="123456789", attempt="1", head_sha=SHA,
                   artifact_id=1234, unified=True, **kwargs)


def test_same_run_integrity_pass_does_not_promote_source_certification(tmp_path):
    src, dst = fixtures(tmp_path)
    out = verify(src, dst)
    assert out["status"] == PASS
    assert out["source_status"] == "HOLD"
    assert out["production_eligible"] is False
    assert out["execution_authorized"] is False
    assert len(out["file_sha256"]) == 4


def test_download_mutation_missing_and_wrong_symbol_rejected(tmp_path):
    for change in ("bad_hash", "missing", "wrong_symbol", "order", "source_mismatch"):
        folder = tmp_path / change
        src, dst = fixtures(folder)
        if change == "bad_hash":
            (dst / "3717.md").write_text("modified", encoding="utf-8")
        if change == "missing":
            (dst / "3717-5m-source.json").unlink()
        if change == "wrong_symbol":
            audit = json.loads((dst / "3717-5m-source.json").read_text())
            audit["symbol"] = "2330"
            new = json.dumps(audit)
            for d in (src, dst):
                (d / "3717-5m-source.json").write_text(new)
        if change == "order":
            for d in (src, dst):
                wrapper = json.loads((d / "3717.json").read_text())
                wrapper["execution_authorized"] = True
                (d / "3717.json").write_text(json.dumps(wrapper))
        if change == "source_mismatch":
            for d in (src, dst):
                wrapper = json.loads((d / "3717.json").read_text())
                wrapper["source_audit"]["symbol"] = "9999"
                (d / "3717.json").write_text(json.dumps(wrapper))
        assert verify(src, dst)["status"] == HOLD, change


def test_wrong_sha_and_run_identity_cannot_pass(tmp_path):
    src, dst = fixtures(tmp_path)
    assert receipt(local=src, downloaded=dst, symbol="3717",
                   run_id="123", attempt="1", head_sha="bad",
                   artifact_id=2, unified=True)["status"] == HOLD
    assert receipt(local=src, downloaded=dst, symbol="3717",
                   run_id="123", attempt="1", head_sha=SHA,
                   artifact_id=0, unified=True)["status"] == HOLD


def test_plain_quote_mode_verifies_own_json_and_markdown(tmp_path):
    src, dst = fixtures(tmp_path, unified=False)
    for d in (src, dst):
        (d / "3717-5m-source.json").unlink()
        (d / "3717-5m-source.md").unlink()
        (d / "3717.json").write_text(json.dumps({
            "symbol": "3717", "status": "STALE_QUOTE",
            "execution_authorized": False, "production_eligible": False,
        }))
        (d / "3717.md").write_text("僅供研究\n")
    result = receipt(local=src, downloaded=dst, symbol="3717",
                     run_id="123456789", attempt="1", head_sha=SHA,
                     artifact_id=1234, unified=False)
    assert result["status"] == PASS
    assert result["source_status"] == "STALE_QUOTE"
    assert result["file_count"] == 2
