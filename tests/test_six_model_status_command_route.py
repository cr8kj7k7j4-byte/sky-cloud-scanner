import unittest

from src.sky_command_router import route_command


class SixModelStatusRouteTests(unittest.TestCase):
    def test_status_audit_route(self):
        for command in ("Sky 六模型狀態盤點", "Sky 六模型盤點"):
            with self.subTest(command=command):
                route = route_command(command)
                self.assertEqual(route.command_family, "SKY_SIX_MODEL_STATUS_AUDIT")
                self.assertEqual(route.data_mode, "GOVERNED_MODEL_INVENTORY")
                self.assertFalse(route.realtime_required)
                self.assertFalse(route.whole_market_required)
                self.assertIn("UNKNOWN", route.notes)

    def test_unified_presentation(self):
        from src.sky_command_router import presentation_for_command
        for command in ("Sky 六模型狀態盤點", "Sky 當沖現在掃一次",
                        "Sky 快掃", "Sky 警戒", "Sky 當沖更新 1569"):
            with self.subTest(command=command):
                self.assertEqual(presentation_for_command(command),
                                 "SKY_MOBILE_TABLE_V2_13_COLUMN")

    def test_live_research_route_unmodified(self):
        route = route_command("Sky 查詢六模型研究訊號")
        self.assertEqual(route.command_family, "SKY_SIX_MODEL_RESEARCH_VISIBILITY")
        self.assertTrue(route.realtime_required)
        self.assertTrue(route.whole_market_required)


if __name__ == "__main__":
    unittest.main()
