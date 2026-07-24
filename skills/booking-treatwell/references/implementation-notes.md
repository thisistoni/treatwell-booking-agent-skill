# Implementation notes

## Interface status

No public, self-serve Treatwell developer API was found during the July 2026 research for this skill. Treatwell's partner terms mention APIs and booking widgets, but no unauthenticated developer onboarding or public booking API documentation was available.

The helper uses the observed structured web interfaces by default because they are the cleanest way to retrieve services, availability, and basket details. No unlock flag or environment variable is required.

Terms: https://www.treatwell.at/info/nutzungsbedingungen/

These interfaces are undocumented and can change. Operators remain responsible for reviewing applicable terms for their deployment. Treat access failures and interface changes as fallback signals, not as reasons to disable the structured path preemptively.

## Observed web interfaces

These are undocumented implementation details and can change without notice:

- A venue page embeds `window.__state__` in `<script id="state">`.
- Venue state contains the venue ID, opening hours, employees, menu groups, services, option IDs, durations, and displayed price ranges.
- `GET /datetime-ui/api/availability` accepts `venueId`, JSON `proposedServices`, and `startDate` and returns employee-aware slots.
- `POST /checkout-api/basket` validates the chosen service/date/time and returns the exact basket, total, payment methods, and policies without creating an order.
- `/secure-checkout` accepts the verified selection as query parameters and renders the customer checkout.
- `POST /checkout-api/order` is the committing action. The bundled helper intentionally never calls it.

On 401, 403, 404, 409, 429, browser verification, schema mismatch, or HTML instead of JSON, stop script use and fall back to the interactive browser. A CAPTCHA or Turnstile screen is not a terminal failure: follow the browser-verification workflow in the same checkout session.

## Helper output

Every successful command prints JSON with `ok: true`. Failures print JSON with `ok: false` and exit non-zero.

`services` returns salon metadata and `services[]`. Each service contains stable IDs only for the current Treatwell implementation; retain both `service_id` and chosen `option_id` for later commands.

`availability` returns:

```json
{
  "ok": true,
  "selection": {
    "service_id": "TR123",
    "option_ids": ["456"]
  },
  "timezone": "Europe/Vienna",
  "slots": [
    {
      "date": "2026-07-16",
      "time": "09:00",
      "eligible_employee_ids": [1],
      "eligible_employee_names": ["Example"],
      "sale_price": "10 €",
      "full_price": "10 €",
      "discount_percentage": 0
    }
  ]
}
```

`prepare-booking` returns `submission_status: "not_submitted"`, a minimized verified basket summary, and `secure_checkout_url`. It checks that Treatwell's basket still matches the requested service, date, and time. Opening the URL is non-committing; submitting its final form is committing.

## Service matching

Prefer IDs returned by `services`. Name matching is case- and accent-insensitive, but duplicate names remain ambiguous by design. When a treatment has multiple options, pass one or more `--option-id` values; never guess based on position.

## Data handling

The helper accepts no customer identity or payment arguments and does not persist cookies. Keep customer PII inside the interactive checkout session and the agent's minimum necessary conversation context.
