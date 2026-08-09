import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import test from "node:test";

const read = (path) => readFileSync(new URL(path, import.meta.url), "utf8");

test("controller exposes preparation only and has no execution state machine", () => {
  for (const file of ["./execution.mjs", "./execution.test.mjs", "./runtime.mjs", "./runtime.test.mjs", "./deploy-workflow.test.mjs"]) {
    assert.equal(existsSync(new URL(file, import.meta.url)), false, `${file} must be removed`);
  }
  const cli = read("../contractctl.mjs");
  for (const forbidden of ["continue", "resume", "approval", "confirm", "dry-run", "no-wait-audit"]) {
    assert.doesNotMatch(cli, new RegExp(`\\b${forbidden.replace("-", "[-]")}\\b`, "i"));
  }
  assert.match(cli, /consumers\s+<prepare\|sync>/);
});

test("GitHub client cannot merge pull requests or dispatch production workflows", () => {
  const source = read("./github.mjs");
  assert.doesNotMatch(source, /mergePullRequest|\[\s*["']pr["']\s*,\s*["']merge["']/);
  assert.doesNotMatch(source, /dispatchWorkflow|watchWorkflowRun|deploy|smoke/i);
});

test("post-merge workflow only synchronizes existing consumer pull requests", () => {
  const workflow = read("../../.github/workflows/contract-rollout.yml");
  assert.match(workflow, /consumers sync/);
  assert.doesNotMatch(workflow, /continue|resume|confirm|deploy|smoke|rollback/i);
});

test("manual upstream deploy workflow is disconnected from contract automation", () => {
  const workflow = read("../../.github/workflows/deploy-railway.yml");
  const operationalWorkflow = workflow.replace(/^.*node --test.*$/gm, "");
  assert.match(workflow, /MANUAL ONLY/);
  assert.doesNotMatch(operationalWorkflow, /contractctl|controller|rollback|recovery|push:/i);
});

test("remote compiler parity covers every main change without production write authority", () => {
  const workflow = read("../../.github/workflows/compiler-remote-parity.yml");
  assert.match(workflow, /push:\s*\n\s*branches:\s*\[main\]/);
  assert.doesNotMatch(workflow, /paths-ignore|paths:/);
  assert.match(workflow, /\/version/);
  assert.match(workflow, /\/ready/);
  assert.match(workflow, /\/spec/);
  assert.match(workflow, /\/compile/);
  assert.match(workflow, /GITHUB_SHA/);
  assert.doesNotMatch(workflow, /RAILWAY_API_TOKEN|railway\s+up|secrets\./i);
});

test("production provenance is baked into the image instead of relabeled at runtime", () => {
  const api = read("../../api_server.py");
  const dockerfile = read("../../Dockerfile");
  const workflow = read("../../.github/workflows/deploy-railway.yml");
  assert.match(api, /BUILD_INFO.*build-info\.json/);
  assert.doesNotMatch(api, /environ\.get\(["']SOURCE_REVISION/);
  assert.match(dockerfile, /COPY build-info\.json/);
  assert.match(workflow, /Path\(["']build-info\.json["']\)\.write_text/);
  assert.doesNotMatch(workflow, /railway variable set.*SOURCE_REVISION/);
});
