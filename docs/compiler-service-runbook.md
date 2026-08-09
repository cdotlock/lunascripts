# Luna Script Compiler service runbook

> **IRON RULE — REMOTE PARITY IS PART OF EVERY MAIN CHANGE**
>
> Every commit merged into this repository's canonical `main` branch must be
> followed by a production Compiler release from that exact SHA. There are no
> path exceptions: compiler code, schemas, fixtures, docs, Skills, workflows,
> and runbooks all affect the authority served to runtime consumers or Agents.
> A repository change is not operationally complete until production reports
> that exact SHA from `/version`, passes semantic `/ready`, and serves the same
> authority resources from `/spec`.

This runbook covers the public service at
`https://moonshort-script-production.up.railway.app`.

## Authority and permission boundaries

- This repository remains the only authority for LS grammar, compiler
  semantics, Episode JSON, compatibility, fixtures, and agent writing rules.
- The production service is a read-only mirror of canonical `main`: it bundles
  the compiler and the agent-readable authority resources listed by `/spec`.
- Production release is human-operated through the manual Railway workflow.
  `contractctl` must not gain deploy, merge, verification, rollback, or recovery
  capabilities.
- Local tests, a Git push, a successful image build, a Railway deployment, and
  live semantic verification are separate claims. Record them separately.
- Never change canonical authoring rules to accommodate a stale remote binary.
  Restore remote parity from the bottom of the authority chain.

## Agent discovery API

Agents should begin with these calls instead of relying on remembered syntax:

| Endpoint | Purpose |
|---|---|
| `GET /version` | Exact deployed repository revision and LS contract version |
| `GET /ready` | Canonical `@bg <name> fade` compile probe plus spec availability |
| `GET /spec` | Discoverable index of authority resources, sizes, and SHA-256 digests |
| `GET /spec/ls-spec` | Canonical Luna Script grammar and semantics |
| `GET /spec/json-output` | Canonical compiler JSON output field reference |

The public spec API is deliberately limited to the two documents an Agent
needs to write LS and consume compiler output. Repository governance, Skills,
schemas, changelogs, and operator runbooks remain repository-local.

Each individual resource response carries `ETag`, `X-Source-Revision`, and
`X-LS-Contract-Version` headers. An Agent should reject mixed revisions rather
than combining rules from different deployments.

## Normal release after every `main` change

### 1. Establish the exact source

```bash
git fetch origin
git switch main
git pull --ff-only origin main
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

The two SHAs must match. Preserve unrelated untracked files. Do not deploy a
detached HEAD, feature branch, tag, dirty tracked worktree, or an older main.

### 2. Run local gates

```bash
go test ./...
node --test scripts/contractctl.test.mjs scripts/contract-rollout/*.test.mjs
go build -o bin/lsc ./cmd/lsc
python -m pip install -r requirements.txt
python -m unittest discover -s tests
```

For contract-impacting work, the separate consumer preparation and human merge
sequence in `docs/contract-consumer-preparation.md` still applies. Passing these
service gates does not grant downstream merge or Backend release permission.

### 3. Run the manual production workflow

```bash
gh workflow run deploy-railway.yml --repo cdotlock/lunascripts --ref main
gh run list --repo cdotlock/lunascripts --workflow deploy-railway.yml --limit 1
gh run watch <run-id> --repo cdotlock/lunascripts --exit-status
```

The workflow fails closed unless the dispatched revision is the current remote
`main`. It writes the SHA into an immutable `build-info.json` bundled with the
image, runs the compiler/API tests, deploys as a non-root container, rechecks
`main` before and after release, waits for the exact revision, and performs live
compile and authority-digest assertions. A protected production environment
may still require its normal human approval.

### 4. Independently verify production

```bash
BASE=https://moonshort-script-production.up.railway.app
EXPECTED_SHA=$(git rev-parse origin/main)

curl -fsS "$BASE/version"
curl -fsS "$BASE/ready"
curl -fsS "$BASE/spec"
curl -fsS -X POST "$BASE/compile" -F "script=@testdata/minimal.ls"
```

Acceptance requires all of the following:

- `/version.source_revision == EXPECTED_SHA`;
- `/version.ls_contract_version` equals `contract/contract.json`;
- `/ready.status == "ready"`;
- `/spec.source_revision == EXPECTED_SHA` and every listed resource is present;
- the compile result retains `name="classroom_morning"`,
  `transition="fade"`, and the current `ls_contract_version`.

## Drift monitoring

The read-only remote-parity workflow runs for every push to `main`, with no path
filter. It waits for the human-operated release and fails if production does not
converge to that exact revision or if the spec resource digests differ. A red
parity check means the repository change is not operationally complete; it is
not permission for automation to deploy or repair production.

## Incident routing

### `/health` is 200 but compile output is wrong

Treat this as possible version drift. Compare `/version.source_revision` with
`origin/main`, then compile the same fixture locally and remotely. `/health`
proves only liveness; `/validate` may also miss lossy parser behavior.

### `/ready` is 503

Read the response reason, then inspect the latest Railway build and deployment
logs. The readiness gate distinguishes a missing manifest/spec resource, an
unavailable binary, a compiler error, and a semantic contract mismatch.

### `/spec` is 503 or a resource digest differs

Do not let Agents mix local and remote rule fragments. Confirm the Docker image
contains every allowlisted authority file, rebuild from exact `main`, and
redeploy. Do not copy rules into consumer repositories as a workaround.

### A newly released `main` is defective

Prefer a reviewed fix-forward commit on `main`, then repeat this runbook. Any
temporary Railway redeploy of an older image is an explicit human incident
action and leaves remote parity broken until canonical `main` is corrected and
released. `contractctl` is not a recovery tool.

## Release record

For each release, record:

- canonical `main` SHA;
- LS contract version;
- local Go, Node, and API test results;
- Git push result;
- GitHub workflow run URL;
- Railway deployment ID/status;
- live `/version`, `/ready`, `/spec`, and compile-smoke results;
- any remaining warning or temporary incident exception.
