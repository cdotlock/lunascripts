# Contract consumer preparation

## Boundary

`contractctl` prepares two open consumer pull requests and publishes evidence.
It does not integrate source or operate production. The three repositories keep
their ordinary branch protections and human release procedures.

The only commands are:

```bash
node scripts/contractctl.mjs rollout validate --base <sha> --head <sha>
node scripts/contractctl.mjs rollout consumers prepare <upstream-pr-url> [--backend-pr <url> --ide-pr <url>] [--audit-report <bound.json>]
node scripts/contractctl.mjs rollout consumers sync <upstream-pr-url> [--audit-report <bound.json>]
node scripts/contractctl.mjs rollout status <upstream-pr-url> --json
```

`prepare` requires an open, mergeable `cdotlock/lunascripts` PR targeting
`main` and a local checkout at that exact candidate SHA. It creates or updates
deterministic `contract-rollout/v<version>-<candidate>` branches, runs each
consumer updater and focused tests, waits for CI, and publishes one identical
report on the upstream, Backend, and IDE PRs.

`sync` is valid only after that same upstream PR is merged into `main`. It
requires the recorded candidate head to remain unchanged, resolves the PR's
exact canonical merge SHA, proves that SHA is reachable from upstream `main`,
and updates the original Backend and IDE PRs. A missing or closed consumer PR
is an error; sync never creates a replacement.

## Full diff evidence

Each consumer report binds:

- exact base SHA, head SHA, and merge-base;
- head tree and an independently regenerated clean-checkout tree;
- every file from a NUL-safe raw Git diff, including status, prior path, old and
  new mode, object type, and base/head blob hashes;
- the SHA-256 of a `--binary --full-index` patch and the independently
  regenerated patch SHA-256;
- all paginated GitHub file records, their digest, and a before/after head check.

Before push or PR edits, preparation rejects unknown paths, rename, copy, type
changes, symlinks, submodules, unapproved workflow changes, divergence,
incomplete regeneration, and concurrent head movement. Deletion is rejected
everywhere except the updater-owned exact mirror trees
`contracts/lunascripts/**` and `vendor/lunascripts/**`; a mirror deletion still
has to match the independently regenerated tree and patch, the complete local
diff, and the paginated GitHub diff.

## Read-only production audit

An audit envelope is accepted only when its digest and provenance bind the
upstream candidate, Backend head, IDE head, contract version, and authoritative
Backend audit implementation. The report must prove `readOnly: true`.

All findings are recursively sanitized before publication. Blockers and manual
repair recommendations are separate arrays; recommendations include episode,
path, and suggested human action. The complete sanitized findings and their
digest are displayed on all three PRs. No R2 object, Supabase row, release
manifest, pointer, or Episode JSON is modified.

## Human sequence

1. Review and merge the upstream authority PR.
2. Wait for automatic sync of the same consumer PRs to the canonical merge SHA.
3. Review and merge Backend manually.
4. Run the normal manual Backend release and production verification process.
5. Review and merge IDE manually.

Preparation reports are evidence only and confer no permission for these steps.

## Contract 4.0.0 inner-thought rollout

The IDE consumer now lives at `MobAI-Inc/lunaverse-ide`. Backend remains
`cdotlock/lunaverse-backend`; IDE Cloud is an additional publication consumer,
not a Backend replacement. Its compatibility change is reviewed separately
because Cloud does not use either existing contract updater.

For this output discriminator migration, prepare/adopt the Backend and IDE
implementation PRs, including their exact reviewed paths, instead of creating
duplicate pin PRs. `inner-thought-consumer-paths.json` lists those additional
paths; updater-owned write/delete scopes are unchanged.

Before enabling v4 compiler output and publishing new content, deploy dual-read
compatibility in Backend and IDE Cloud and deliver compatible player clients.
The external Cocos client reads CDN JSON directly, so server-side compatibility
is insufficient. See [the Cocos handoff](handoffs/2026-09-11-cocos-inner-thought.md).
Main changes still require the exact-revision Compiler release and semantic
verification; an open source PR or consumer preparation alone is not a release.
