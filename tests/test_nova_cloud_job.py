import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "cloud" / "nova_cloud_job.py"

class CloudJobSafetyTests(unittest.TestCase):
    def test_dry_run_only(self):
        env = dict(os.environ, NOVA_CLOUD_MODE="DRY_RUN")
        p = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, env=env)
        self.assertEqual(p.returncode, 0, p.stderr)
        data = json.loads(p.stdout)
        self.assertEqual(data["status"], "HOLD")
        self.assertFalse(data["orders_enabled"])
        self.assertFalse(data["real_market_data"])

    def test_live_mode_fail_closed(self):
        env = dict(os.environ, NOVA_CLOUD_MODE="LIVE")
        p = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, env=env)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("NOVA_CLOUD_LIVE_DISABLED", p.stderr)
if __name__ == "__main__":
    unittest.main()
