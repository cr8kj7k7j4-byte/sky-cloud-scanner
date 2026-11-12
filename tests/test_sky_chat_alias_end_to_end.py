"""Five Sky aliases through the real Chat Bridge entrypoint, without paid APIs.

This is a deterministic offline integration contract, not actual ChatGPT UI E2E
or proof of remotely downloadable GitHub Actions artifacts.
"""
import contextlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import src.sky_chat_bridge as bridge
from src.sky_scan_readback import COMMANDS, validate_scan_readback


class ChatBridgeFiveAliasIntegrationTests(unittest.TestCase):
    def test_each_alias_runs_the_existing_bridge_entrypoint(self):
        for alias in sorted(COMMANDS):
            with self.subTest(alias=alias), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                request = root / "request.json"
                output = root / "output/chat_bridge"
                work = root / "output/sky_quickscan_information"
                work.mkdir(parents=True)
                request_id = "five-alias-integration-20261111"
                request.write_text(json.dumps({
                    "command": alias, "request_id": request_id,
                    "read_only_no_orders": True,
                }, ensure_ascii=False), encoding="utf-8")
                row = {key: "待確認" for key in bridge.COLUMNS}
                row.update({"股票代碼": "1101", "現在動作": "等待",
                            "正式交易資格": False})
                observed = datetime.now(timezone.utc).isoformat()
                report = {
                    "schema": "SKY_DAYTRADE_13COL_RESEARCH_V2",
                    "row_count": 1, "universe_count": 1,
                    "rows": [row], "checked_at_tpe": observed,
                    "production_eligible": False,
                }
                universe = {
                    "universe_count": 1,
                    "all_symbols": [{"symbol": "1101"}],
                    "observed_price_count": 1,
                    "by_exchange": {
                        "TWSE": {"snapshot_rows": 1},
                        "TPEx": {"snapshot_rows": 1},
                    },
                }
                (work / "latest_13col.json").write_text(
                    json.dumps(report, ensure_ascii=False), encoding="utf-8")
                (work / "full_universe.json").write_text(
                    json.dumps(universe), encoding="utf-8")
                prior_cwd = Path.cwd()
                try:
                    os.chdir(root)
                    with patch.object(bridge, "REQUEST", request), \
                         patch.object(bridge, "OUTPUT", output), \
                         patch.dict(os.environ, {
                             "GITHUB_RUN_ID": "1234567",
                             "GITHUB_REPOSITORY": "cr8kj7k7j4-byte/sky-cloud-scanner",
                             "GITHUB_SHA": "a" * 40,
                         }), \
                         patch.object(bridge.subprocess, "run",
                                      return_value=SimpleNamespace(returncode=0)), \
                         patch.object(bridge, "screen_stage1",
                                      return_value={"candidate_count": 0}), \
                         patch.object(bridge, "verify_stage2",
                                      return_value={"attempted_count": 0, "verified_executed_count": 0}), \
                         patch.object(bridge, "probe_v14_candles",
                                      return_value={"samples": []}), \
                         patch.object(bridge, "write_candidate_chain", return_value={}):
                        with contextlib.redirect_stdout(__import__("io").StringIO()):
                            bridge.main()
                finally:
                    os.chdir(prior_cwd)
                status = json.loads((output / "latest.json").read_text(encoding="utf-8"))
                self.assertEqual(status["request_id"], request_id)
                self.assertEqual(status["scan_id"], "1234567")
                self.assertEqual(status["status"], "REPORT_READY_RESEARCH_ONLY")
                self.assertEqual(status["row_count"], 1)
                self.assertFalse(status["production_eligible"])
                self.assertFalse(status["automatic_order"])
                self.assertEqual(status["readback"]["trade_action"], "禁止交易")
                attested = validate_scan_readback(
                    status, expected_run_id="1234567", expected_request_id=request_id)
                self.assertEqual(attested["status"],
                                 "RESEARCH_REPORT_READABLE_NOT_TRADE_CERTIFIED")


if __name__ == "__main__":
    unittest.main()
