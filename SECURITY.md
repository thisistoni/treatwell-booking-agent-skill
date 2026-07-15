# Security policy

## Supported versions

Security fixes are applied to the latest revision on the default branch.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository. Do not open a public issue containing customer data, credentials, session tokens, payment information, OTPs, or details that could facilitate bypassing Treatwell access controls.

Include a concise impact description, reproduction steps using synthetic data, and a proposed mitigation when possible.

## Deployment guidance

- Review applicable platform terms before production or high-volume deployment.
- Keep customer identity and payment details inside the interactive checkout wherever possible.
- Do not persist browser cookies, session tokens, OTPs, or payment data.
- Require a fresh, exact confirmation immediately before the committing booking or payment action.
- Treat an unclear submission result as unknown. Verify it before retrying.
- Hand CAPTCHA, OTP, login, 3-D Secure, wallet approval, and similar challenges back to the customer.

The bundled helper intentionally cannot submit a Treatwell order. The complete skill can place a booking through the interactive browser workflow after explicit final confirmation.
