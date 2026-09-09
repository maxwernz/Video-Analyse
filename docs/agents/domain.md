# Domain Docs

How the engineering skills should consume this repository's domain documentation when exploring the codebase.

## Before exploring, read these

- `CONTEXT.md` at the repository root.
- Relevant ADRs under `docs/adr/`.

If these files do not exist, proceed silently. The `domain-modeling`, `grill-with-docs`, and `improve-codebase-architecture` skills create them when domain terms or decisions are resolved.

## File structure

This is a single-context repository:

```
/
├── CONTEXT.md
├── docs/adr/
└── application source files
```

## Use the glossary's vocabulary

When output names a domain concept, use the term defined in `CONTEXT.md`. Avoid synonyms that the glossary explicitly rejects.

If a needed concept is absent, reconsider whether the project uses another term or note the gap for `domain-modeling`.

## Flag ADR conflicts

If proposed work contradicts an existing ADR, identify the conflict explicitly rather than silently overriding it.
