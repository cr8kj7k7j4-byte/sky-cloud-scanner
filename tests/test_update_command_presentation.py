from src.sky_command_router import presentation_for_command, UPDATE_PRESENTATION


def test_all_update_commands_use_mobile_table():
    commands = [
        "Sky 快掃更新",
        "Sky 當沖更新 6770",
        "Sky 波段更新 2409",
        "Sky Swing 5D 更新 9914",
        "Sky 當沖持倉更新 6770，成本 69.1，1 張",
        "Sky 波段持倉更新 2409，成本 37.05，1 張",
        "Sky 持倉更新 6221，成本 39，1 張",
    ]
    for command in commands:
        assert presentation_for_command(command) == UPDATE_PRESENTATION


def test_non_update_command_does_not_force_update_presentation():
    assert presentation_for_command("Sky 回測目前模型") is None
