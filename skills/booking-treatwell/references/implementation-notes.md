# Implementation notes

## Authorization and interface status

No public, self-serve Treatwell developer API was found during the July 2026 research for this skill. Treatwell's partner terms mention APIs and booking widgets, but no unauthenticated developer onboarding or public booking API documentation was available.

Treatwell Austria's website terms prohibit automated systems or software that extract website/app content unless Treatwell has granted a written license. The live-network helper therefore requires `--acknowledge-authorization` (or `TREATWELL_AUTOMATION_AUTHORIZED=1`). The flag is an operator assertion, not permission from Treatwell.

Terms: https://www.treatwell.at/info/nutzungsbedingungen/

Use browser-driven customer interaction as the default for an unlicensed deployment. Before production or high-volume operation, obtain Treatwell's written authorization or an official integration.

## Observed web interfaces

These are undocumented implementation details and can change without notice:

- A venue page embeds `window.__state__` in `<script id="state">`.
- Venue state contains the venue ID, opening hours, employees, menu groups, services, option IDs, durations, and displayed price ranges.
- `GET /datetime-ui/api/availability` accepts `venueId`, JSON `proposedServices`, and `startDate` and returns employee-aware slots.
- `POST /checkout-api/basket` validates the chosen service/date/time and returns the exact basket, total, payment methods, and policies without creating an order.
- `/secure-checkout` accepts the verified selection as query parameters and renders the customer checkout.
- `POST /checkout-api/order` is the committing action. The bundled helper intentionally never calls it.

Do not use these paths to bypass normal controls. On 401, 403, 404, 409, 429, CAPTCHA, schema mismatch, or HTML instead of JSON, stop script use and fall back to the browser.

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
