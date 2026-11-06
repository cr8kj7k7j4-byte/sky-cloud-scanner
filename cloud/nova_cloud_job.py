"""Cloud Run Job dry-run entrypoint; no broker SDK, credentials or trading endpoints."""
import json
import os
from datetime import datetime, timezone

def main():
    if os.getenv("NOVA_CLOUD_MODE", "DRY_RUN") != "DRY_RUN":
        raise SystemExit("NOVA_CLOUD_LIVE_DISABLED: vendor permissions and secret gating required")
    report = {
        "schema": "SKY_NOVA_CLOUD_DRY_RUN_V1",
        "mode": "DRY_RUN",
        "status": "HOLD",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "real_market_data": False,
        "orders_enabled": False,
        "live_provider_auth_enabled": False,
        "message": "Cloud container and logging only; not market-data proof."
    }
    print(json.dumps(report, ensure_ascii=False))

if __name__ == "__main__":
    main()
