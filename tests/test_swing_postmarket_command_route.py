import unittest
from src.sky_command_router import route_command


class SwingPostmarketCommandRouteTests(unittest.TestCase):
    def test_swing_postmarket_review_route(self):
        for command in ("Sky 盤後複盤｜波段", "Sky 盤後複盤|波段", "Sky 盤後複盤 波段"):
            with self.subTest(command=command):
                route = route_command(command)
                self.assertEqual(route.command_family, "SKY_SWING_POSTMARKET_REVIEW")
                self.assertEqual(route.data_mode, "POSTMARKET_DAILY_AND_SIGNAL_LEDGER")
                self.assertFalse(route.realtime_required)
                self.assertTrue(route.whole_market_required)
                self.assertIn("swing-postmarket-research.yml", route.execution_target)
                self.assertIn("UNKNOWN", route.notes)


if __name__ == "__main__":
    unittest.main()
