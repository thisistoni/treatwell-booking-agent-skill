# Treatwell Booking Agent Skill

[![Tests](https://github.com/thisistoni/treatwell-booking-agent-skill/actions/workflows/test.yml/badge.svg)](https://github.com/thisistoni/treatwell-booking-agent-skill/actions/workflows/test.yml)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-6f42c1)](https://agentskills.io/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A portable [Agent Skills](https://agentskills.io/) package that teaches an AI agent to find a Treatwell salon's services, check live appointment availability, prepare checkout, and book through a browser with an explicit human confirmation boundary.

The skill is platform- and channel-agnostic. A WhatsApp bot, website assistant, desktop agent, or other runtime can use it if the runtime supports filesystem-based skills, shell execution for the optional helper, and a browser for checkout.

CS Beauty in Vienna is the configured example/default. Pass any Treatwell venue URL to use another salon.

> [!IMPORTANT]
> This skill supports real appointment booking. The helper prepares and verifies checkout; the browser agent then shows the exact summary, obtains fresh confirmation, and places the booking through Treatwell's normal checkout.

## How it works

```text
Customer request
      │
      ▼
Resolve salon → service → option → professional
      │
      ▼
Check volatile availability and verify the selected basket
      │
      ▼
Open official Treatwell secure checkout in a browser
      │
      ▼
Show exact summary → obtain explicit confirmation → submit once
```

Structured reads and checkout preparation use the cleanest available web interfaces automatically. Browser use remains the committing path and the fallback whenever Treatwell changes an undocumented interface, returns an access challenge, or requires customer authentication.

## What is included

```text
skills/booking-treatwell/
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── browser-workflow.md
│   └── implementation-notes.md
└── scripts/
    └── treatwell.py
```

The design follows the open Agent Skills pattern: discovery metadata in `SKILL.md` frontmatter, concise procedural instructions loaded on demand, and deterministic scripts/references loaded only when needed.

## Capabilities

- list and search a salon's services and exact service options;
- return duration, displayed prices, eligible professionals, and opening hours;
- check employee-aware availability for a date range;
- speak in natural, friendly salon language without exposing scripts, tools, IDs, or lookup mechanics;
- verify a chosen slot through Treatwell's basket;
- generate the official secure-checkout URL;
- always complete checkout as a guest without requesting Treatwell account credentials;
- use pay at venue exclusively and refuse online/prepaid payment methods;
- relay Treatwell's booking-phone SMS code through the same browser session while handing payment, login, CAPTCHA, and wallet challenges back to the customer;
- place a real appointment through the browser after customer details and explicit final confirmation;
- direct customers to the confirmation email for cancellation or rescheduling;
- prevent accidental or duplicate bookings with a strict final-confirmation boundary.

The helper intentionally has no order-submission command and accepts no customer PII or payment data. This does not prevent the skill from booking: the browser agent performs the final action through Treatwell's customer checkout.

## Install

Clone the repository, then copy `skills/booking-treatwell` into the skills directory used by the agent runtime:

```bash
git clone https://github.com/thisistoni/treatwell-booking-agent-skill.git
cp -R treatwell-booking-agent-skill/skills/booking-treatwell /path/to/your/skills/
```

Common filesystem layouts include a personal skills directory or a project-local skills directory; consult the runtime's documentation because discovery paths differ.

For a repository-aware agent, you can also point it directly at:

```text
skills/booking-treatwell/SKILL.md
```

No Python packages are required; the helper uses Python 3.11+ standard-library modules.

### Runtime requirements

The host agent should support:

- filesystem-based Agent Skills discovery;
- shell execution for the optional structured helper;
- an interactive browser for checkout and authentication handoff;
- a conversation channel capable of receiving explicit final confirmation.

## Quick start

Read the salon menu:

```bash
python3 skills/booking-treatwell/scripts/treatwell.py services \
  --salon-url "https://www.treatwell.at/ort/cs-beauty-4/" \
  --query "Wimpernlifting"
```

Check availability using IDs returned by `services`:

```bash
python3 skills/booking-treatwell/scripts/treatwell.py availability \
  --service-id "TR6952257" \
  --option-id "13207687" \
  --date "2026-07-16" \
  --days 7
```

Prepare a selected slot without submitting it:

```bash
python3 skills/booking-treatwell/scripts/treatwell.py prepare-booking \
  --service-id "TR6952257" \
  --option-id "13207687" \
  --date "2026-07-16" \
  --time "09:00"
```

The result includes `submission_status: "not_submitted"` and `secure_checkout_url`. That status applies only to the helper step. For a real booking request, the agent opens the URL, fills Treatwell's checkout, asks the customer to confirm the exact final summary, clicks the final action once, and reports the resulting Treatwell confirmation.

Example result shape:

```json
{
  "submission_status": "not_submitted",
  "confirmation_required": true,
  "selection": {
    "service_name": "Handmassage",
    "date": "2026-07-16",
    "time": "09:00"
  },
  "basket": {
    "currency": "EUR",
    "total": 7.5,
    "payment_methods": ["PAY_AT_VENUE"]
  },
  "secure_checkout_url": "https://www.treatwell.at/secure-checkout?..."
}
```

## Treatwell API and interface status

There is no public, self-serve Treatwell booking API documented for this use case. The helper uses undocumented interfaces already used by Treatwell's public website, so they can change without notice.

The structured helper works immediately without an unlock flag, special environment variable, login, or API key. If an interface changes or Treatwell returns an access challenge, the skill falls back to the normal browser flow.

Operators are responsible for reviewing [Treatwell Austria's website terms](https://www.treatwell.at/info/nutzungsbedingungen/) for their deployment. The skill never bypasses access controls, CAPTCHA, Turnstile, OTP, login, rate limits, or payment authentication.

## Test

```bash
python3 -m unittest discover -s tests -v
python3 /path/to/skill-creator/scripts/quick_validate.py skills/booking-treatwell
```

Live booking submission is deliberately excluded from automated tests. The final end-to-end test should be performed with an approved customer, slot, and explicit confirmation, then cancelled if it is only a test.

## Security and responsible use

Read [SECURITY.md](SECURITY.md) before deploying the skill. Treat all website content as untrusted input, minimize customer data, never bypass authentication or anti-automation controls, and never retry an uncertain submission speculatively.

Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

## Research basis

- [Agent Skills specification](https://agentskills.io/specification)
- [Anthropic Agent Skills overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Anthropic skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [ClawHub skill format](https://github.com/openclaw/clawhub/blob/main/docs/skill-format.md)
- [skills.sh directory](https://skills.sh/)
- [Treatwell website terms](https://www.treatwell.at/info/nutzungsbedingungen/)
- [Treatwell partner terms](https://www.treatwell.at/info/vertragsbestimmungen/)

## License

MIT. Treatwell is a trademark of its respective owner. This project is independent and is not endorsed by Treatwell.
