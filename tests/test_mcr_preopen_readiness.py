import unittest
from research.mcr_preopen_readiness import run

class PreopenReadinessTests(unittest.TestCase):
    def test_both_markets_reachable_is_not_live_certification(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            with patch("research.mcr_preopen_readiness.OUT",Path(td)/"receipt.json"):
                r=run(probe=lambda m: {"date":"2026-11-09","data":[{"lastTrade":{"time":None}}]},sleep=lambda _:None)
        self.assertTrue(r["source_reachable"])
        self.assertFalse(r["trade_eligible"])
        self.assertFalse(r["is_live_trade_certified"])
        self.assertFalse(r["maintenance_below_130_verified"])
    def test_transient_failure_retries_then_recovers(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        attempts={"TSE":0,"OTC":0}
        def probe(m):
            attempts[m]+=1
            if attempts[m]==1: raise RuntimeError("secret-not-to-be-logged")
            return {"date":"2026-11-09","data":[{"symbol":"1101"}]}
        with tempfile.TemporaryDirectory() as td:
            with patch("research.mcr_preopen_readiness.OUT",Path(td)/"receipt.json"):
                r=run(probe=probe,sleep=lambda _:None)
        self.assertTrue(r["source_reachable"])
        self.assertEqual(attempts,{"TSE":2,"OTC":2})
    def test_permanent_failure_is_blocked(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            with patch("research.mcr_preopen_readiness.OUT",Path(td)/"receipt.json"):
                r=run(probe=lambda m: (_ for _ in ()).throw(PermissionError("secret")),sleep=lambda _:None)
        self.assertEqual(r["result"],"DATA_BLOCKED")
        self.assertNotIn("secret",str(r))
if __name__=="__main__":unittest.main()
