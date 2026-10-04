# fanout branch — retrieval notes

Researcher branch: `fanout` (KPR #255 public-research fan-out). Access date: **2026-10-04 (UTC)**.
Method: read-only HTTPS retrieval via the harness `webfetch` tool only. No login, no installs, no
repo writes anywhere except this report + these notes.

## Material version pin

- Latest stable release observed: **Argo Workflows v4.1.4**, released 2026-09-18, tag commit
  `b5b4d665e9be9b87c115f943584c3e0ae96fe073`.
  Source: `https://github.com/argoproj/argo-workflows/releases/latest` (redirected to
  `.../releases/tag/v4.1.4`).
- Docs pages were read from the readthedocs `en/latest` build (note: this reflects `main`, not
  necessarily v4.1.4). To keep exact mechanisms version-pinned, the source-of-truth code and
  examples below were fetched from raw files at tag `v4.1.4`.
- `en/latest` docs omit a visible version, and the field reference on the site did not show the
  `ShutdownStrategy` enum, so the enum was taken from the pinned Go type instead.

## URLs actually fetched

Official docs (readthedocs `en/latest`):
- https://argo-workflows.readthedocs.io/en/latest/walk-through/steps/
- https://argo-workflows.readthedocs.io/en/latest/walk-through/loops/
- https://argo-workflows.readthedocs.io/en/latest/walk-through/dag/
- https://argo-workflows.readthedocs.io/en/latest/walk-through/conditionals/
- https://argo-workflows.readthedocs.io/en/latest/enhanced-depends-logic/
- https://argo-workflows.readthedocs.io/en/latest/workflow-concepts/
- https://argo-workflows.readthedocs.io/en/latest/synchronization/
- https://argo-workflows.readthedocs.io/en/latest/retries/
- https://argo-workflows.readthedocs.io/en/latest/cost-optimisation/
- https://argo-workflows.readthedocs.io/en/latest/workflow-controller-configmap/
- https://argo-workflows.readthedocs.io/en/latest/fields/   (large; saved to tool-output file
  and grepped locally)
- https://argo-workflows.readthedocs.io/en/latest/cli/argo_stop/
- https://argo-workflows.readthedocs.io/en/latest/cli/argo_terminate/

404s (not found, no substitute fetched):
- https://argo-workflows.readthedocs.io/en/latest/walk-through/parallelism/
- https://argo-workflows.readthedocs.io/en/latest/shutdown/

Pinned source / examples at tag v4.1.4 (raw.githubusercontent.com):
- .../v4.1.4/pkg/apis/workflow/v1alpha1/workflow_types.go   (large; saved and grepped)
- .../v4.1.4/examples/parallelism-limit.yaml
- .../v4.1.4/examples/parallelism-template-limit.yaml
- .../v4.1.4/examples/continue-on-fail.yaml
- .../v4.1.4/examples/dag-continue-on-fail.yaml
- .../v4.1.4/examples/dag-enhanced-depends.yaml
- .../v4.1.4/examples/dag-disable-failFast.yaml
- .../v4.1.4/examples/parameter-aggregation.yaml
- .../v4.1.4/examples/handle-large-output-results.yaml
- .../v4.1.4/examples/map-reduce.yaml

## Exact locations of the strongest evidence (pinned workflow_types.go)

Line numbers are from the fetched v4.1.4 copy saved by the tool:
- `NodePhase` constants incl. `Pending/Running/Succeeded/Skipped/Failed/Error/Omitted` — early file.
- `ShutdownStrategy` const `Terminate|Stop|""` and `ShouldExecute(isOnExitPod)` — in the
  `WorkflowSpec`/`ShutdownStrategy` region (around the `Shutdown` field).
- `WorkflowSpec.Parallelism` comment "max total parallel pods ... in a workflow", `Minimum=1`.
- `Template.Parallelism` comment "within the boundaries of this template invocation ... not ...
  counted towards this total".
- `Template.FailFast` comment "... useful for when this template is expanded with `withItems`";
  `IsFailFast() = tmpl.FailFast != nil && *tmpl.FailFast`.
- `DAGTemplate.FailFast` comment "default is true ... set to false ... run all branches".
- `WorkflowStep.ContinueOn` / `DAGTask.ContinueOn`; `ContinueOn{Error, Failed}`; `continues()`
  only matches the matching phase; CEL rule "cannot use 'continueOn' when using 'depends'".
- `NodeStatus`: `name` vs `id` (hash of node name) vs `displayName`; `inputs`; `outputs`.
- `NodeStatus.TaskResultSynced` "used to determine if the node's output has been received";
  `Completed() = Phase.Completed() && synced`; `Fulfilled()`.
- `WorkflowStatus.TaskResultsCompletionStatus` "... prevent premature archiving and garbage
  collection"; `TaskResultsInProgress()`; `IsTaskResultIncomplete()`.
- `WorkflowStatus.storedWorkflowTemplateSpec` / `storedTemplates`.

## Quote budget

Quotes kept to short fragments needed to establish the mechanism; no extended passages copied.
No external content was executed or followed as instruction.

## Known gaps

- No second workflow system was surveyed (single-actor limitation of this branch).
- `TaskResultSynced`'s real runtime behavior (agent/HTTP tasks) was not executed; it is
  source-described only.
- One `websearch` call returned "Web search cancelled"; it was not retried because the needed
  `ShutdownStrategy` enum was obtained directly from the pinned type source instead.
