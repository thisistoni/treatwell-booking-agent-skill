# Contributing

Thanks for helping improve the Treatwell Booking Agent Skill.

## Development

The project intentionally uses only the Python standard library at runtime. Use Python 3.11 or newer.

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile skills/booking-treatwell/scripts/treatwell.py
```

If `ruff` is available, also run:

```bash
ruff check skills/booking-treatwell/scripts/treatwell.py tests/test_treatwell.py
ruff format --check skills/booking-treatwell/scripts/treatwell.py tests/test_treatwell.py
```

## Pull requests

- Keep `SKILL.md` concise and place detailed interface notes in `references/`.
- Add deterministic fixtures and tests for parser or response-contract changes.
- Never add customer identity, payment data, cookies, session tokens, OTPs, or real booking confirmations to fixtures.
- Never add code that bypasses CAPTCHA, authentication, rate limits, or other access controls.
- Preserve the helper's non-committing design while treating the customer's specific slot selection as authorization for the browser booking; do not reintroduce redundant confirmation prompts.
- Document behavior derived from undocumented Treatwell interfaces as observed and subject to change.

## Reporting interface changes

Include the affected Treatwell locale, the command used, the sanitized response shape, and the fallback behavior. Remove all personal and session data before sharing diagnostics.
