from datetime import date

from research.probe_fugle_pit_intraday_coverage import historical_probe_windows


def test_historical_probe_windows_respect_provider_and_listing_bounds():
    windows = historical_probe_windows(
        date(2011, 9, 29),
        date(2023, 6, 27),
    )
    assert windows
    assert windows[0] == ("2023-05-28", "2023-06-27")
    assert all(start >= "2023-05-23" for start, _ in windows)
    assert all(start <= end for start, end in windows)


def test_historical_probe_windows_step_back_for_longer_lived_symbol():
    windows = historical_probe_windows(
        date(2014, 7, 23),
        date(2024, 7, 2),
    )
    assert len(windows) >= 3
    assert windows[0] == ("2024-06-02", "2024-07-02")
    assert windows[1] == ("2024-04-03", "2024-05-03")
    assert windows[2] == ("2024-02-03", "2024-03-04")
