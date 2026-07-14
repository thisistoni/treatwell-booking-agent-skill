# Treatwell Booking Agent Skill

[![Tests](https://github.com/thisistoni/treatwell-booking-agent-skill/actions/workflows/test.yml/badge.svg)](https://github.com/thisistoni/treatwell-booking-agent-skill/actions/workflows/test.yml)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-6f42c1)](https://agentskills.io/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776ab?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A portable [Agent Skills](https://agentskills.io/) package that teaches an AI agent to find a Treatwell salon's services, check live appointment availability, prepare checkout, and book through a browser with an explicit human confirmation boundary.

The skill is platform- and channel-agnostic. A WhatsApp bot, website assistant, desktop agent, or other runtime can use it if the runtime supports filesystem-based skills, shell execution for the optional helper, and a browser for checkout.

CS Beauty in Vienna is the configured example/default. Pass any Treatwell venue URL to use another salon.

> [!IMPORTANT]
> The included helper can prepare checkout but cannot submit an order. A browser agent must show the exact booking summary and obtain fresh customer confirmation immediately before the final Treatwell action.

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

Structured reads and checkout preparation are deterministic when authorized. Browser use remains the committing path and the fallback whenever Treatwell changes an undocumented interface, returns an access challenge, or requires customer authentication.

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
- verify a chosen slot through Treatwell's basket;
- generate the official secure-checkout URL;
- guide a browser agent through customer details, OTP/CAPTCHA/payment handoff, confirmation, and result verification;
- prevent accidental or duplicate bookings with a strict final-confirmation boundary.

The helper intentionally has no order-submission command and accepts no customer PII or payment data.

## Install

Copy `skills/booking-treatwell` into the skills directory used by the agent runtime. Common filesystem layouts include a personal skills directory or a project-local skills directory; consult the runtime's documentation because discovery paths differ.

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
  --query "Wimpernlifting" \
  --acknowledge-authorization
```

Check availability using IDs returned by `services`:

```bash
python3 skills/booking-treatwell/scripts/treatwell.py availability \
  --service-id "TR6952257" \
  --option-id "13207687" \
  --date "2026-07-16" \
  --days 7 \
  --acknowledge-authorization
```

Prepare a selected slot without submitting it:

```bash
python3 skills/booking-treatwell/scripts/treatwell.py prepare-booking \
  --service-id "TR6952257" \
  --option-id "13207687" \
  --date "2026-07-16" \
  --time "09:00" \
  --acknowledge-authorization
```

The result includes `submission_status: "not_submitted"` and `secure_checkout_url`. The agent opens that URL in a browser, fills the normal Treatwell checkout, stops before the final button, and asks the customer to confirm the exact booking summary.

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
    "payment_methods": ["PAY_AT_VENUE", "CARD"]
  },
  "secure_checkout_url": "https://www.treatwell.at/secure-checkout?..."
}
```

## Authorization and Treatwell API status

There is no public, self-serve Treatwell booking API documented for this use case. The helper uses undocumented interfaces already used by Treatwell's public website, so they can change without notice.

More importantly, [Treatwell Austria's website terms](https://www.treatwell.at/info/nutzungsbedingungen/) prohibit automated screen scraping unless Treatwell has granted a written license. Live helper commands therefore require `--acknowledge-authorization` or `TREATWELL_AUTOMATION_AUTHORIZED=1`. This is an operator assertion, not a way to obtain permission.

For an unlicensed deployment, use the skill's browser workflow. Before production or high-volume deployment, obtain written Treatwell authorization or an official integration. The skill never bypasses access controls, CAPTCHA, Turnstile, OTP, login, rate limits, or payment authentication.

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
