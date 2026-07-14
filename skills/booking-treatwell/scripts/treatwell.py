#!/usr/bin/env python3
"""Read Treatwell menus/availability and prepare, but never submit, bookings."""

from __future__ import annotations

import argparse
import datetime as dt
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

DEFAULT_SALON_URL = "https://www.treatwell.at/ort/cs-beauty-4/"
TERMS_URL = "https://www.treatwell.at/info/nutzungsbedingungen/"
USER_AGENT = "booking-treatwell-skill/0.1"
DEFAULT_TIMEOUT = 20
TREATWELL_DOMAINS = {
    "treatwell.at",
    "treatwell.be",
    "treatwell.ch",
    "treatwell.co.uk",
    "treatwell.com",
    "treatwell.de",
    "treatwell.es",
    "treatwell.fr",
    "treatwell.gr",
    "treatwell.ie",
    "treatwell.it",
    "treatwell.lt",
    "treatwell.nl",
    "treatwell.pt",
}


class SkillError(Exception):
    def __init__(self, code: str, message: str, details: object | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class StateScriptParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.capture = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag.lower() == "script" and values.get("id") in {"state", "global-state"}:
            self.capture = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self.capture:
            self.capture = False

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.parts.append(data)


def fail(code: str, message: str, details: object | None = None) -> None:
    raise SkillError(code, message, details)


def canonical_salon_url(value: str) -> str:
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    official_host = any(
        host == domain or host.endswith(f".{domain}") for domain in TREATWELL_DOMAINS
    )
    if parsed.scheme != "https" or not official_host:
        fail("invalid_salon_url", "Use an HTTPS Treatwell venue URL.")
    return urlunparse(("https", parsed.netloc, parsed.path or "/", "", "", ""))


def require_authorization(args: argparse.Namespace, needs_network: bool) -> None:
    acknowledged = (
        args.acknowledge_authorization
        or os.getenv("TREATWELL_AUTOMATION_AUTHORIZED") == "1"
    )
    if needs_network and not acknowledged:
        fail(
            "authorization_required",
            "Live automated access requires operator-confirmed authorization. "
            "Use --acknowledge-authorization only when authorized, or use a browser.",
            {"terms": TERMS_URL},
        )


def request_bytes(
    url: str,
    *,
    language: str,
    timeout: int,
    body: object | None = None,
) -> bytes:
    headers = {
        "Accept": "application/json,text/html;q=0.9",
        "Accept-Language": language,
        "User-Agent": USER_AGENT,
        "X-Language-Code": language[:2],
    }
    data = None
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    try:
        with urlopen(
            Request(url, data=data, headers=headers), timeout=timeout
        ) as response:
            return response.read()
    except HTTPError as exc:
        retry = (
            " Fall back to the browser."
            if exc.code in {401, 403, 404, 409, 429}
            else ""
        )
        fail("http_error", f"Treatwell returned HTTP {exc.code}.{retry}", {"url": url})
    except (URLError, TimeoutError) as exc:
        fail("network_error", f"Could not reach Treatwell: {exc}", {"url": url})


def read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        fail("file_error", f"Could not read {path}: {exc}")


def read_json(path: str) -> dict:
    try:
        value = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        fail("invalid_json", f"Could not parse {path}: {exc}")
    if not isinstance(value, dict):
        fail("invalid_json", f"Expected a JSON object in {path}.")
    return value


def parse_state(document: str) -> dict:
    parser = StateScriptParser()
    parser.feed(document)
    raw = "".join(parser.parts).strip()
    if not raw:
        fail(
            "state_not_found",
            "Treatwell state script was not found; use the browser fallback.",
        )
    prefix = "window.__state__ = "
    if raw.startswith(prefix):
        raw = raw[len(prefix) :].rstrip("; ")
    try:
        state = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail("state_schema_changed", f"Treatwell state could not be parsed: {exc}")
    if not isinstance(state, dict):
        fail("state_schema_changed", "Treatwell state was not a JSON object.")
    return state


def load_venue_state(args: argparse.Namespace) -> dict:
    if args.html_file:
        return parse_state(read_text(args.html_file))
    raw = request_bytes(
        canonical_salon_url(args.salon_url),
        language=args.language,
        timeout=args.timeout,
    )
    return parse_state(raw.decode("utf-8", errors="replace"))


def venue_data(state: dict) -> tuple[dict, dict]:
    wrapper = state.get("venue")
    if not isinstance(wrapper, dict):
        fail("state_schema_changed", "Venue data was missing from Treatwell state.")
    venue = wrapper.get("venue", wrapper)
    if not isinstance(venue, dict) or not venue.get("id"):
        fail("state_schema_changed", "Venue identity was missing from Treatwell state.")
    channel = state.get("channel") if isinstance(state.get("channel"), dict) else {}
    return venue, channel


TAG_RE = re.compile(r"<[^>]+>")


def clean_text(value: object) -> str:
    text = html.unescape(str(value or ""))
    return " ".join(TAG_RE.sub(" ", text).split())


def normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", clean_text(value).casefold())
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


def price_summary(price: object) -> dict:
    value = price if isinstance(price, dict) else {}
    return {
        "min_sale": value.get("minSalePriceAmount"),
        "max_sale": value.get("maxSalePriceAmount"),
        "min_full": value.get("minFullPriceAmount"),
        "max_full": value.get("maxFullPriceAmount"),
        "currency": value.get("priceCurrency"),
        "range": bool(value.get("range")),
    }


def flatten_services(venue: dict, include_descriptions: bool = False) -> list[dict]:
    menu = venue.get("menu") if isinstance(venue.get("menu"), dict) else {}
    groups = menu.get("menuGroups") if isinstance(menu.get("menuGroups"), list) else []
    result: list[dict] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        for item in group.get("menuItems", []):
            if not isinstance(item, dict) or not isinstance(item.get("data"), dict):
                continue
            data = item["data"]
            options: list[dict] = []
            for option_group in data.get("optionGroups", []) or []:
                if not isinstance(option_group, dict):
                    continue
                for option in option_group.get("options", []) or []:
                    if not isinstance(option, dict):
                        continue
                    options.append(
                        {
                            "option_id": str(option.get("id")),
                            "option_group": clean_text(option_group.get("name")),
                            "name": clean_text(option.get("name")),
                            "duration_minutes": option.get("durationMinutes"),
                            "price": price_summary(option.get("priceRange")),
                            "employees": option.get("employees", []),
                        }
                    )
            service = {
                "group": clean_text(group.get("name")),
                "service_id": str(data.get("id")),
                "name": clean_text(data.get("name")),
                "duration": data.get("durationRange"),
                "price": price_summary(data.get("priceRange")),
                "multi_option_selection": bool(data.get("multiOptionSelection")),
                "options": options,
            }
            if include_descriptions:
                service["description"] = clean_text(data.get("description"))
            result.append(service)
    if not result:
        fail(
            "state_schema_changed",
            "No services were found in the Treatwell venue state.",
        )
    return result


def salon_summary(venue: dict, channel: dict, salon_url: str) -> dict:
    location = venue.get("location") if isinstance(venue.get("location"), dict) else {}
    address = (
        location.get("address") if isinstance(location.get("address"), dict) else {}
    )
    return {
        "venue_id": venue.get("id"),
        "name": venue.get("name"),
        "url": salon_url,
        "timezone": channel.get("timezone"),
        "currency": channel.get("currencyCode"),
        "address": address.get("addressLines", []),
        "opening_hours": venue.get("openingHours", []),
        "employees": [
            {
                "id": value.get("id"),
                "name": value.get("name"),
                "title": value.get("title"),
            }
            for value in venue.get("employees", [])
            if isinstance(value, dict)
        ],
    }


def matching_services(services: list[dict], query: str | None) -> list[dict]:
    if not query:
        return services
    needle = normalize(query)
    matches = [
        service
        for service in services
        if needle in normalize(service["name"])
        or needle in normalize(service["group"])
        or any(needle in normalize(option["name"]) for option in service["options"])
    ]
    if not matches:
        fail("service_not_found", f"No service matched {query!r}.")
    return matches


def resolve_service(
    services: list[dict], service_id: str | None, name: str | None
) -> dict:
    if service_id:
        matches = [value for value in services if value["service_id"] == service_id]
    elif name:
        exact = [
            value for value in services if normalize(value["name"]) == normalize(name)
        ]
        matches = exact or [
            value for value in services if normalize(name) in normalize(value["name"])
        ]
    else:
        fail("service_required", "Pass --service-id or --service.")
    if not matches:
        fail("service_not_found", "The requested service was not found.")
    if len(matches) > 1:
        fail(
            "ambiguous_service",
            "The service name is ambiguous; choose a service_id.",
            [
                {"service_id": v["service_id"], "group": v["group"], "name": v["name"]}
                for v in matches
            ],
        )
    return matches[0]


def resolve_options(service: dict, option_ids: list[str] | None) -> list[dict]:
    options = service["options"]
    if option_ids:
        selected = [value for value in options if value["option_id"] in option_ids]
        missing = [
            value
            for value in option_ids
            if value not in {v["option_id"] for v in selected}
        ]
        if missing:
            fail("option_not_found", "Some option IDs were not found.", missing)
        return selected
    if len(options) == 1 and not service["multi_option_selection"]:
        return options
    fail(
        "option_required",
        "Choose the exact option ID; the service has multiple options.",
        options,
    )


def selection_payload(
    service: dict, options: list[dict], employee_id: int | None = None
) -> list[dict]:
    selection: dict = {
        "menuItemId": service["service_id"],
        "optionIds": [value["option_id"] for value in options],
    }
    if employee_id is not None:
        selection["employeeId"] = employee_id
    return [selection]


def load_availability(
    args: argparse.Namespace,
    venue: dict,
    channel: dict,
    selection: list[dict],
) -> dict:
    if args.availability_file:
        value = read_json(args.availability_file)
        return value.get("availability", value)
    base = urlparse(canonical_salon_url(args.salon_url))
    query = urlencode(
        {
            "venueId": str(venue["id"]),
            "proposedServices": json.dumps(selection, separators=(",", ":")),
            "startDate": args.date,
        }
    )
    url = urlunparse(
        (base.scheme, base.netloc, "/datetime-ui/api/availability", "", query, "")
    )
    raw = request_bytes(url, language=args.language, timeout=args.timeout)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        fail(
            "availability_schema_changed",
            "Availability did not return JSON; use the browser.",
        )
    if not isinstance(value, dict) or not isinstance(value.get("days"), dict):
        fail(
            "availability_schema_changed",
            "Availability response shape changed; use the browser.",
        )
    return value


def employee_map(availability: dict) -> dict[int, str]:
    values = (
        availability.get("employees")
        if isinstance(availability.get("employees"), dict)
        else {}
    )
    return {
        int(key): str(value.get("name"))
        for key, value in values.items()
        if isinstance(value, dict) and str(key).isdigit()
    }


def resolve_employee(availability: dict, requested: str | None) -> int | None:
    if not requested:
        return None
    employees = employee_map(availability)
    if requested.isdigit() and int(requested) in employees:
        return int(requested)
    matches = [
        key
        for key, value in employees.items()
        if normalize(value) == normalize(requested)
    ]
    if not matches:
        fail(
            "employee_not_found",
            f"No eligible professional matched {requested!r}.",
            employees,
        )
    if len(matches) > 1:
        fail(
            "ambiguous_employee",
            "Professional name is ambiguous; use an employee ID.",
            matches,
        )
    return matches[0]


def parse_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        fail("invalid_date", "Use date format YYYY-MM-DD.")


def parse_time(value: str) -> dt.time:
    try:
        parsed = dt.time.fromisoformat(value)
    except ValueError:
        fail("invalid_time", "Use time format HH:MM.")
    if parsed.second or parsed.microsecond:
        fail("invalid_time", "Use time format HH:MM without seconds.")
    return parsed


def slots_from_availability(
    availability: dict,
    *,
    start: dt.date,
    days: int,
    employee_id: int | None,
    limit: int,
) -> list[dict]:
    names = employee_map(availability)
    end = start + dt.timedelta(days=days)
    result: list[dict] = []
    for date_key, day in sorted(availability.get("days", {}).items()):
        current = parse_date(date_key)
        if current < start or current >= end or not isinstance(day, dict):
            continue
        for slot in day.get("times", []):
            if not isinstance(slot, dict):
                continue
            ids = [int(value) for value in slot.get("employeeIds", [])]
            if employee_id is not None and employee_id not in ids:
                continue
            result.append(
                {
                    "date": date_key,
                    "time": slot.get("startTime"),
                    "eligible_employee_ids": ids,
                    "eligible_employee_names": [
                        names.get(value, str(value)) for value in ids
                    ],
                    "sale_price": slot.get("salePriceAmount"),
                    "full_price": slot.get("fullPriceAmount"),
                    "discount_percentage": slot.get("discountPercentage", 0),
                }
            )
            if len(result) >= limit:
                return result
    return result


def minutes_since_midnight(value: str) -> int:
    parsed = parse_time(value)
    return parsed.hour * 60 + parsed.minute


def checkout_offer(
    service: dict, options: list[dict], employee_id: int | None
) -> list[dict]:
    numeric_id = re.sub(r"^[A-Z]+", "", service["service_id"])
    if not numeric_id.isdigit():
        fail(
            "invalid_service_id",
            "Treatwell service ID was not numeric after its prefix.",
        )
    offer: dict = {
        "offerId": int(numeric_id),
        "fulfillment": "APPOINTMENT",
        "skus": [{"skuId": int(value["option_id"])} for value in options],
    }
    if employee_id is not None:
        offer["employeeId"] = employee_id
    return [offer]


def checkout_url(
    salon_url: str,
    venue_id: int,
    offers: list[dict],
    date: str,
    time: str,
) -> str:
    base = urlparse(canonical_salon_url(salon_url))
    query = urlencode(
        {
            "venueId": venue_id,
            "offers": json.dumps(offers, separators=(",", ":")),
            "date": date,
            "time": minutes_since_midnight(time),
        }
    )
    return urlunparse((base.scheme, base.netloc, "/secure-checkout", "", query, ""))


def load_basket(
    args: argparse.Namespace,
    venue: dict,
    offers: list[dict],
    date: str,
    time: str,
) -> dict:
    if args.basket_file:
        return read_json(args.basket_file)
    base = urlparse(canonical_salon_url(args.salon_url))
    url = urlunparse((base.scheme, base.netloc, "/checkout-api/basket", "", "", ""))
    items = [
        {
            "offerId": offer["offerId"],
            "options": [{"optionId": value["skuId"]} for value in offer["skus"]],
            "fulfillmentType": offer["fulfillment"],
            **({"employeeId": offer["employeeId"]} if offer.get("employeeId") else {}),
        }
        for offer in offers
    ]
    raw = request_bytes(
        url,
        language=args.language,
        timeout=args.timeout,
        body={
            "date": date,
            "time": minutes_since_midnight(time),
            "items": items,
            "venueId": venue["id"],
        },
    )
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        fail(
            "basket_schema_changed",
            "Basket validation did not return JSON; use the browser.",
        )
    if not isinstance(value, dict) or value.get("type") != "local-appointment":
        fail(
            "basket_schema_changed",
            "Basket validation response shape changed; use the browser.",
        )
    return value


def basket_summary(basket: dict, service_id: str, date: str, time: str) -> dict:
    if basket.get("type") != "local-appointment":
        fail(
            "basket_schema_changed",
            "Basket validation response shape changed; use the browser.",
        )

    expected_start = f"{date}T{time}"
    actual_start = str(basket.get("startDateTime") or "")
    if not actual_start.startswith(expected_start):
        fail(
            "basket_mismatch",
            "Treatwell returned a basket for a different appointment time; use the browser.",
            {"expected": expected_start, "actual": actual_start or None},
        )

    offers = basket.get("offers")
    if not isinstance(offers, list) or not any(
        isinstance(offer, dict) and str(offer.get("menuItemId")) == service_id
        for offer in offers
    ):
        fail(
            "basket_mismatch",
            "Treatwell returned a basket for a different service; use the browser.",
            {"expected_service_id": service_id},
        )

    payment_methods = basket.get("paymentMethods")
    if not isinstance(payment_methods, list):
        payment_methods = []
    cancellation = basket.get("cancellationPolicy")
    reschedule = basket.get("reschedulePolicy")
    return {
        "type": basket.get("type"),
        "currency": basket.get("currencyCode"),
        "total": basket.get("outstandingAmount"),
        "start": actual_start,
        "duration_minutes": basket.get("totalDurationInMinutes"),
        "payment_methods": [
            value.get("name")
            for value in payment_methods
            if isinstance(value, dict) and value.get("name")
        ],
        "offers": [
            {
                "service_id": offer.get("menuItemId"),
                "name": offer.get("name"),
                "duration_minutes": offer.get("durationInMinutes"),
                "employee": (
                    offer.get("employee", {}).get("name")
                    if isinstance(offer.get("employee"), dict)
                    else None
                ),
                "original_price": offer.get("originalPrice"),
                "discounted_price": offer.get("discountedPrice"),
            }
            for offer in offers
            if isinstance(offer, dict)
        ],
        "cancellation_notice_hours": (
            cancellation.get("refundPeriodDurationInHours")
            if isinstance(cancellation, dict)
            else None
        ),
        "reschedule_notice_hours": (
            reschedule.get("noticePeriodDurationInHours")
            if isinstance(reschedule, dict)
            else None
        ),
        "requires_user_consent": bool(basket.get("requiresUserConsent")),
    }


def command_services(args: argparse.Namespace) -> dict:
    require_authorization(args, needs_network=not bool(args.html_file))
    state = load_venue_state(args)
    venue, channel = venue_data(state)
    services = flatten_services(venue, include_descriptions=args.include_descriptions)
    return {
        "ok": True,
        "salon": salon_summary(venue, channel, canonical_salon_url(args.salon_url)),
        "services": matching_services(services, args.query),
        "source": "captured_html" if args.html_file else "treatwell_web",
    }


def resolve_context(args: argparse.Namespace) -> tuple[dict, dict, dict, list[dict]]:
    state = load_venue_state(args)
    venue, channel = venue_data(state)
    service = resolve_service(flatten_services(venue), args.service_id, args.service)
    options = resolve_options(service, args.option_id)
    return venue, channel, service, options


def command_availability(args: argparse.Namespace) -> dict:
    needs_network = not (args.html_file and args.availability_file)
    require_authorization(args, needs_network=needs_network)
    venue, channel, service, options = resolve_context(args)
    selection = selection_payload(service, options)
    availability = load_availability(args, venue, channel, selection)
    employee_id = resolve_employee(availability, args.employee)
    slots = slots_from_availability(
        availability,
        start=parse_date(args.date),
        days=args.days,
        employee_id=employee_id,
        limit=args.limit,
    )
    return {
        "ok": True,
        "salon": {"venue_id": venue["id"], "name": venue.get("name")},
        "selection": {
            "service_id": service["service_id"],
            "service_name": service["name"],
            "option_ids": [value["option_id"] for value in options],
            "option_names": [value["name"] for value in options],
            "employee_id": employee_id,
            "employee_name": employee_map(availability).get(employee_id)
            if employee_id
            else None,
        },
        "timezone": channel.get("timezone"),
        "first_included_date": availability.get("firstIncludedDate"),
        "last_included_date": availability.get("lastIncludedDate"),
        "slots": slots,
        "slot_count": len(slots),
        "volatile": True,
    }


def command_prepare_booking(args: argparse.Namespace) -> dict:
    needs_network = not (args.html_file and args.availability_file and args.basket_file)
    require_authorization(args, needs_network=needs_network)
    venue, channel, service, options = resolve_context(args)
    availability = load_availability(
        args, venue, channel, selection_payload(service, options)
    )
    employee_id = resolve_employee(availability, args.employee)
    chosen = slots_from_availability(
        availability,
        start=parse_date(args.date),
        days=1,
        employee_id=employee_id,
        limit=10000,
    )
    matching = [value for value in chosen if value["time"] == args.time]
    if not matching:
        fail(
            "slot_unavailable",
            "The requested slot is not currently available.",
            chosen[:20],
        )
    offers = checkout_offer(service, options, employee_id)
    basket = basket_summary(
        load_basket(args, venue, offers, args.date, args.time),
        service["service_id"],
        args.date,
        args.time,
    )
    return {
        "ok": True,
        "submission_status": "not_submitted",
        "confirmation_required": True,
        "salon": {
            "venue_id": venue["id"],
            "name": venue.get("name"),
            "timezone": channel.get("timezone"),
        },
        "selection": {
            "service_id": service["service_id"],
            "service_name": service["name"],
            "option_ids": [value["option_id"] for value in options],
            "option_names": [value["name"] for value in options],
            "date": args.date,
            "time": args.time,
            "employee_id": employee_id,
            "employee_name": employee_map(availability).get(employee_id)
            if employee_id
            else None,
        },
        "verified_slot": matching[0],
        "basket": basket,
        "secure_checkout_url": checkout_url(
            args.salon_url, int(venue["id"]), offers, args.date, args.time
        ),
    }


def default_date() -> str:
    try:
        return dt.datetime.now(ZoneInfo("Europe/Vienna")).date().isoformat()
    except Exception:
        return dt.date.today().isoformat()


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--salon-url", default=os.getenv("TREATWELL_SALON_URL", DEFAULT_SALON_URL)
    )
    parser.add_argument(
        "--html-file", help="Parse a captured venue HTML file instead of fetching it."
    )
    parser.add_argument(
        "--language", default="de", help="Treatwell language code (default: de)."
    )
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        "--acknowledge-authorization",
        action="store_true",
        help="Assert authorization for live automated Treatwell access.",
    )


def add_selection(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--service-id")
    parser.add_argument(
        "--service", help="Service name; IDs are safer when names are ambiguous."
    )
    parser.add_argument(
        "--option-id", action="append", help="Exact option ID; repeat if required."
    )


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)

    services = sub.add_parser("services", help="List or search salon services.")
    add_common(services)
    services.add_argument("--query")
    services.add_argument("--include-descriptions", action="store_true")
    services.set_defaults(handler=command_services)

    availability = sub.add_parser(
        "availability", help="Return current appointment slots."
    )
    add_common(availability)
    add_selection(availability)
    availability.add_argument(
        "--availability-file", help="Use a captured availability JSON response."
    )
    availability.add_argument("--date", default=default_date())
    availability.add_argument(
        "--days", type=int, default=14, choices=range(1, 91), metavar="1..90"
    )
    availability.add_argument("--employee", help="Eligible professional name or ID.")
    availability.add_argument("--limit", type=int, default=50)
    availability.set_defaults(handler=command_availability)

    prepare = sub.add_parser(
        "prepare-booking", help="Verify a slot and prepare secure checkout."
    )
    add_common(prepare)
    add_selection(prepare)
    prepare.add_argument("--availability-file", help="Use captured availability JSON.")
    prepare.add_argument("--basket-file", help="Use captured basket JSON.")
    prepare.add_argument("--date", required=True)
    prepare.add_argument("--time", required=True)
    prepare.add_argument("--employee", help="Eligible professional name or ID.")
    prepare.set_defaults(handler=command_prepare_booking)
    return root


def main() -> int:
    try:
        args = parser().parse_args()
        if args.timeout < 1 or args.timeout > 120:
            fail("invalid_timeout", "Timeout must be between 1 and 120 seconds.")
        result = args.handler(args)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except SkillError as exc:
        error = {"ok": False, "error": {"code": exc.code, "message": exc.message}}
        if exc.details is not None:
            error["error"]["details"] = exc.details
        print(json.dumps(error, ensure_ascii=False, indent=2))
        return 2
    except KeyboardInterrupt:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": {"code": "interrupted", "message": "Interrupted."},
                }
            )
        )
        return 130


if __name__ == "__main__":
    sys.exit(main())
