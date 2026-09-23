# Contributing

Thanks for helping improve Worx Vision Cloud PLUS.

## Local Checks

Before opening a pull request:

1. Make sure Home Assistant starts with the integration installed.
2. Add or update translations when entity names change.
3. Do not commit `__pycache__`, dashboard backups, raw API dumps or Home Assistant storage files.
4. Remove private data from logs and screenshots.

## The card

The Lovelace card is `custom_components/worx_vision_cloud/worx-vision-card.js`: one file, no build step, served by the integration. Edit it there, then run its tests with Node 22 or later:

```bash
node --check custom_components/worx_vision_cloud/worx-vision-card.js
node tests/card/run.mjs
```

The tests render the card for a fake Home Assistant state and check the markup. Add one for every change, and make sure it fails when the change is undone. Every string goes into all eleven languages, which the tests check.

## Coding Style

- Keep entities stable once published.
- Prefer small, readable helpers over large ad-hoc parsing blocks.
- Treat private Worx API fields defensively because they can disappear or change shape.
- Do not expose large raw payloads as entity attributes by default.
