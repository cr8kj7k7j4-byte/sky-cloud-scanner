"""After-cost performance metrics (Validation Protocol: Expectancy, PF, DD, Win rate)."""

from statistics import mean


def summarize(net_returns: list[float]) -> dict:
    n = len(net_returns)
    if n == 0:
        return {"n": 0, "expectancy": None, "profit_factor": None,
                "win_rate": None, "max_drawdown": None}
    wins = [r for r in net_returns if r > 0]
    losses = [r for r in net_returns if r < 0]
    gross_win = sum(wins)
    gross_loss = -sum(losses)
    pf = (gross_win / gross_loss) if gross_loss > 0 else None

    equity, peak, max_dd = 0.0, 0.0, 0.0
    for r in net_returns:
        equity += r
        peak = max(peak, equity)
        max_dd = min(max_dd, equity - peak)

    return {
        "n": n,
        "expectancy": mean(net_returns),
        "profit_factor": pf,
        "win_rate": len(wins) / n,
        "max_drawdown": max_dd,  # cumulative net return units, not TWD
    }
