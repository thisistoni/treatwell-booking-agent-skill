# Treatwell browser workflow

Use this workflow when live script access is not authorized, a helper fails, or a booking is ready for checkout. Labels vary by language and responsive layout, so prefer roles, accessible names, and stable `data-cy` attributes over CSS class names.

## Service and availability

1. Open the salon's canonical Treatwell venue URL.
2. Read the visible service menu. Expand the relevant category and treatment.
3. Resolve every required option. Do not treat a category-level price range as the exact option price.
4. Add the selected service. For multiple services, add all requested items before continuing.
5. Continue to the date/time screen.
6. If requested, select a professional; otherwise retain Treatwell's any-professional choice.
7. Choose a date and read available time buttons. A time shown here is not reserved.

Useful current attributes include:

- menu group: `data-menu-group-id` and `data-cy="menu-group-..."`;
- availability list: `data-cy="TimeSlotList"`;
- time item: `data-cy="TimeSlotListItem"`;
- selected time: `data-cy="SelectedStartTime"`;
- checkout form: `data-cy="Form"`.

Do not depend solely on these attributes; Treatwell can change them.

## Checkout

1. Select the chosen time to open secure checkout.
2. Verify the basket before entering personal data: salon, service option, duration, professional, date, time, and total.
3. Enter only the required customer name, email, and telephone. Add appointment notes only when the customer requested them.
4. Do not opt into salon or Treatwell marketing unless the customer explicitly asked to opt in.
5. Select the customer's chosen payment method. Do not infer consent to prepayment from consent to book.
6. Let the customer complete CAPTCHA, Turnstile, OTP, login, 3-D Secure, wallet approval, or other authentication when presented.
7. Stop before the final booking/payment button.

## Final confirmation boundary

Recheck availability if enough time has passed that the slot could have changed. Present the complete summary required by `SKILL.md` and ask for explicit confirmation to place the booking now.

After confirmation, click the final action once. Wait for a definitive Treatwell result.

## Failure handling

- Slot disappeared: return to availability and offer the nearest alternatives.
- Price or policy changed: stop and ask the customer to accept the new terms.
- Authentication challenge: ask the customer to take over; do not bypass it.
- Page structure changed: use visible labels and accessibility information, not guessed selectors.
- Unknown result after final click: inspect the current page and the customer's Treatwell bookings before any retry.
- Confirmed booking: report the Treatwell reference and relevant management link.
