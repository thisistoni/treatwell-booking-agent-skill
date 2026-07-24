# Security policy

## Supported versions

Security fixes are applied to the latest revision on the default branch.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do not open a public issue containing customer data, credentials, session tokens, payment information, OTPs, or details that could facilitate bypassing Treatwell access controls.

Include a concise impact description, reproduction steps using synthetic data, and a proposed mitigation when possible.

## Deployment guidance

- Review applicable platform terms before production or high-volume deployment.
- Keep customer identity and payment details inside the interactive checkout wherever possible.
- Use pay at venue only; never collect or enter card, wallet, PayPal, or other online-payment details.
- Do not persist browser cookies, session tokens, OTPs, or payment data.
- Treat the customer's selection of a specific offered slot as authorization for that exact pay-at-venue booking; do not request redundant confirmation.
- Treat an unclear submission result as unknown. Verify it before retrying.
- Accept a booking-phone SMS code only for immediate entry into the customer's existing checkout session; never retain or repeat it.
- Attempt CAPTCHA, Turnstile, and similar visible verification in the existing browser session before escalation; their appearance alone is not a reason to stop or request a person.
- Preserve the exact browser session for secure takeover only when the runtime cannot complete a remaining challenge after real attempts.
- Do not switch away from guest checkout or pay at venue to satisfy account-login, online-payment, 3-D Secure, or wallet requirements.

The bundled helper intentionally cannot submit a Treatwell order. The complete skill places the customer's chosen slot through the interactive browser workflow without asking them to confirm the same selection again.
