import importlib

def main():
    mod = importlib.import_module("src.main")
    policy = mod._execution_policy()
    assert policy is not None
    assert hasattr(policy, "buy_commission_rate")
    assert hasattr(policy, "sell_tax_rate")
    print("PASS P0-X runtime import smoke test")

if __name__ == "__main__":
    main()
