# Treatwell browser workflow

Use this workflow when a helper fails or a booking is ready for checkout. Labels vary by language and responsive layout, so prefer roles, accessible names, and stable `data-cy` attributes over CSS class names.

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
3. Always choose guest checkout or continue without an account. Do not sign in, create an account, or request Treatwell credentials.
4. Enter only the required customer name, email, and telephone. Add appointment notes only when the customer requested them.
5. Do not opt into salon or Treatwell marketing unless the customer explicitly asked to opt in.
6. Select pay at venue. Never choose card, PayPal, Apple Pay, Google Pay, a wallet, or any online/prepaid method. If pay at venue is not offered, stop without booking.
7. Handle ordinary booking-phone SMS verification using the workflow below. Let the customer take over for CAPTCHA, Turnstile, account login, 3-D Secure, wallet approval, payment authentication, or other higher-risk challenges.
8. Internally verify that the checkout still matches the slot the customer chose, then submit it once without asking the customer to confirm the same appointment again.

## Booking-phone SMS verification

1. After submitting the customer's phone number, keep the exact browser tab, context, cookies, and checkout session open on the verification screen. Do not restart checkout or create a second session.
2. Tell the customer that a verification code was sent to their phone. If the page shows a masked destination, include only that masked value.
3. Ask the customer to send the current SMS code in the chat. Keep the request natural, for example: `I’ve sent a verification code to your phone. Please send me the code when it arrives.`
4. When the customer replies, treat the value only as the current booking verification code. Enter it promptly into the open verification form and continue.
5. Do not quote the code back, include it in summaries, write it to files, persist it in memory, or expose it in logs or tool output.
6. If the code is rejected, ask the customer to check the latest SMS and try once more. If it expired, use the page's resend action once and ask for the new code. Do not loop resends or guess codes.
7. After successful verification, continue the checkout and submit the already-authorized appointment once. Do not ask for another confirmation.

## Submission after slot selection

The customer's choice of a specific offered service/date/time authorizes that exact booking. Do not run a separate customer-visible availability check, repeat the same summary, or ask `Are you sure?` / `Shall I book it?`.

Use the normal checkout attempt to detect whether the slot is still available. If it succeeds, click the final action once and wait for a definitive result. If the slot disappeared, return to availability and offer nearby alternatives. Ask a new question only when the customer must make a genuinely new choice, such as a changed time, professional, service, or price.

## Successful booking response

After a definitive confirmation, tell the customer naturally:

- the appointment is booked;
- the salon, service, professional, date, time, and final price;
- a confirmation email should arrive at the email address they provided;
- the email contains buttons or links for cancelling or rescheduling the appointment.

Mask the email address when repeating it. If the email does not arrive shortly, suggest checking the spam folder before contacting the salon.

## Failure handling

- Slot disappeared: return to availability and offer the nearest alternatives.
- Price or policy changed: stop and ask the customer to accept the new terms.
- Pay at venue unavailable: explain that the agent cannot complete bookings requiring online payment and do not choose another payment method.
- Booking SMS code rejected or expired: request the latest code or resend once without abandoning the current session.
- Payment, login, CAPTCHA, 3-D Secure, or wallet challenge: ask the customer to take over; do not bypass it.
- Page structure changed: use visible labels and accessibility information, not guessed selectors.
- Unknown result after final click: inspect the current page and the customer's Treatwell bookings before any retry.
- Confirmed booking: report the Treatwell reference and relevant management link.
- Confirmation email missing: suggest checking spam, then contacting the salon; do not create a duplicate booking.
