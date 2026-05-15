# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root.
- **`docs/adr/`** — read ADRs that touch the area you're about to work in.

If any of these files don't exist for a topic, **proceed silently**. Don't flag absences or suggest creating them upfront. The producer skill (`/grill-with-docs`) creates them lazily when terms or decisions actually get resolved.

## File structure

Single-context layout:

```
/
├── CONTEXT.md
├── docs/adr/
│   └── 0001-tagged-long-format.md
└── thaifin/
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

Examples for this repo:
- Use **Filing** (not "report" or "submission") for one regulatory zip.
- Use **Concept** (not "field" or "metric") for a curated line-item ID.
- Use **Tagged long-format** (not "normalized" or "long-form") for the schema shape.
- Use **Revision** (not "snapshot" or "release") for a published dataset version on HuggingFace.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/grill-with-docs`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0001 (tagged long-format) — but worth reopening because…_
