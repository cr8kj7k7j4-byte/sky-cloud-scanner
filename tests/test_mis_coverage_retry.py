"""MIS quote coverage safety: distinguish omitted responses from z='-'."""
import unittest
from unittest.mock import patch

from src.official import fetch_mis_quotes


def stock(code):
    return {
        "symbol": code, "name": code, "exchange": "TWSE",
        "market": "TSE", "mis_prefix": "tse",
    }


def quote(code, last):
    return {
        "c": code, "n": code, "z": last, "y": "10",
        "v": "100", "t": "10:00:00", "d": "20261106",
        "b": "10", "a": "10.1",
    }


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, rows, *, omit_in_multi=None):
        self.headers = {}
        self.rows = rows
        self.omit_in_multi = omit_in_multi or set()
        self.calls = []

    def get(self, url, params=None, timeout=None):
        if params is None:
            return Response({})
        symbols = [
            part.split("_")[1].split(".")[0]
            for part in params["ex_ch"].split("|")
        ]
        self.calls.append(symbols)
        returned = [
            self.rows[x] for x in symbols if x in self.rows
            and not (len(symbols) > 1 and x in self.omit_in_multi)
        ]
        return Response({"msgArray": returned})


class MisCoverageRetryTests(unittest.TestCase):
    def fetch(self, fake, symbols):
        with patch("src.official.session", return_value=fake), patch(
            "src.official.time.sleep", return_value=None
        ):
            return fetch_mis_quotes(
                [stock(x) for x in symbols], batch_size=55, sleep_s=0
            )

    def test_present_missing_last_retried_but_never_fabricated(self):
        codes = ["1101", "1102", "1103"]
        fake = FakeSession({
            "1101": quote("1101", "-"),
            "1102": quote("1102", "-"),
            "1103": quote("1103", "12"),
        })
        rows, warnings = self.fetch(fake, codes)
        self.assertEqual(fake.calls, [codes, ["1101", "1102"]])
        self.assertEqual([r["symbol"] for r in rows], ["1103"])
        diagnostics = " ".join(warnings)
        self.assertIn("initial_present_without_executed_price=2", diagnostics)
        self.assertIn("initial_missing_response=0", diagnostics)
        self.assertIn("recovery_requested=2", diagnostics)
        self.assertIn("recovery_valid_quotes=0", diagnostics)
        self.assertIn("missing_after_recovery=2", diagnostics)

    def test_only_omitted_symbol_is_requeried_and_can_recover(self):
        codes = ["1101", "1102", "1103"]
        fake = FakeSession(
            {x: quote(x, "12") for x in codes},
            omit_in_multi={"1102"},
        )
        rows, warnings = self.fetch(fake, codes)
        self.assertEqual(fake.calls, [codes, ["1102"]])
        self.assertEqual({r["symbol"] for r in rows}, set(codes))
        diagnostics = " ".join(warnings)
        self.assertIn("initial_missing_response=1", diagnostics)
        self.assertIn("recovery_requested=1", diagnostics)
        self.assertIn("recovery_valid_quotes=1", diagnostics)
        self.assertIn("missing_after_recovery=0", diagnostics)

    def test_missing_last_is_not_replaced_with_reference_price(self):
        fake = FakeSession({"1101": quote("1101", "-")})
        rows, _ = self.fetch(fake, ["1101"])
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
