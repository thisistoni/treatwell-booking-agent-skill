import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "booking-treatwell" / "scripts" / "treatwell.py"
FIXTURES = ROOT / "tests" / "fixtures"

spec = importlib.util.spec_from_file_location("treatwell_skill", SCRIPT)
tw = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(tw)


class TreatwellHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = tw.parse_state((FIXTURES / "venue.html").read_text())
        cls.venue, cls.channel = tw.venue_data(cls.state)
        cls.services = tw.flatten_services(cls.venue, include_descriptions=True)
        cls.availability = json.loads((FIXTURES / "availability.json").read_text())

    def test_parses_service_and_option(self):
        self.assertEqual(self.venue["id"], 521537)
        self.assertEqual(len(self.services), 1)
        service = self.services[0]
        self.assertEqual(service["service_id"], "TR123")
        self.assertEqual(service["description"], "A & B")
        self.assertEqual(service["options"][0]["option_id"], "456")

    def test_matches_service_case_and_accent_insensitively(self):
        matches = tw.matching_services(self.services, "HANDMASSAGE")
        self.assertEqual(matches[0]["service_id"], "TR123")

    def test_filters_availability_by_employee(self):
        employee_id = tw.resolve_employee(self.availability, "Simal")
        slots = tw.slots_from_availability(
            self.availability,
            start=tw.parse_date("2026-07-16"),
            days=2,
            employee_id=employee_id,
            limit=50,
        )
        self.assertEqual(employee_id, 10)
        self.assertEqual([slot["time"] for slot in slots], ["09:00"])
        self.assertEqual(slots[0]["eligible_employee_names"], ["Simal", "Betül"])

    def test_builds_non_committing_checkout_url(self):
        service = self.services[0]
        options = tw.resolve_options(service, None)
        offers = tw.checkout_offer(service, options, 10)
        url = tw.checkout_url(
            tw.DEFAULT_SALON_URL, self.venue["id"], offers, "2026-07-16", "09:00"
        )
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.path, "/secure-checkout")
        self.assertEqual(query["time"], ["540"])
        self.assertEqual(json.loads(query["offers"][0])[0]["employeeId"], 10)
        self.assertNotIn("order", parsed.path)

    def test_live_commands_have_no_unlock_flag(self):
        args = tw.parser().parse_args(["services"])
        self.assertFalse(hasattr(args, "acknowledge_authorization"))

    def test_rejects_non_treatwell_hostname(self):
        with self.assertRaises(tw.SkillError) as raised:
            tw.canonical_salon_url("https://treatwell.example/ort/fake/")
        self.assertEqual(raised.exception.code, "invalid_salon_url")

    def test_basket_summary_validates_and_minimizes_output(self):
        basket = json.loads((FIXTURES / "basket.json").read_text())
        basket["stripePublicApiKey"] = "not-needed"
        summary = tw.basket_summary(basket, "TR123", "2026-07-16", "09:00")
        self.assertEqual(summary["total"], 7.5)
        self.assertEqual(summary["payment_methods"], ["PAY_AT_VENUE"])
        self.assertNotIn("stripePublicApiKey", summary)

        with self.assertRaises(tw.SkillError) as raised:
            tw.basket_summary(basket, "TR999", "2026-07-16", "09:00")
        self.assertEqual(raised.exception.code, "basket_mismatch")

    def test_requires_pay_at_venue(self):
        basket = json.loads((FIXTURES / "basket.json").read_text())
        summary = tw.basket_summary(basket, "TR123", "2026-07-16", "09:00")
        self.assertIs(tw.require_pay_at_venue(summary), summary)

        summary["payment_methods"] = ["CARD", "PAYPAL"]
        with self.assertRaises(tw.SkillError) as raised:
            tw.require_pay_at_venue(summary)
        self.assertEqual(raised.exception.code, "pay_at_venue_unavailable")

    def test_prepare_booking_offline_cli(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "prepare-booking",
                "--html-file",
                str(FIXTURES / "venue.html"),
                "--basket-file",
                str(FIXTURES / "basket.json"),
                "--service-id",
                "TR123",
                "--date",
                "2026-07-16",
                "--time",
                "09:00",
                "--employee",
                "Simal",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["submission_status"], "not_submitted")
        self.assertFalse(payload["confirmation_required"])
        self.assertTrue(payload["booking_authorized_by_slot_selection"])
        self.assertEqual(payload["checkout_attempt"]["validation"], "checkout_basket")
        self.assertEqual(payload["selection"]["employee_name"], "Simal")
        self.assertEqual(payload["basket"]["type"], "local-appointment")
        self.assertEqual(payload["basket"]["payment_methods"], ["PAY_AT_VENUE"])


if __name__ == "__main__":
    unittest.main()
