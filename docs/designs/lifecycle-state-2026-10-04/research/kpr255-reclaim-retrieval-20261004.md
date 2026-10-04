# KPR #255 reclaim research retrieval notes

Access date: 2026-10-04 (UTC). Public web retrieval only. I read `/tmp/kpr-lifecycle-implementation-20261004/public-research-brief.md`, `/tmp/kpr-lifecycle-implementation-20261004/lifecycle-closure-consolidation.md`, and `reclaim-prompt.txt` before research. No repository file, installed skill, shared record, or infrastructure was written. No tests or native actors were run.

## Version anchors

- Kubernetes documentation site showed current v1.37 docs on access date. The generated OwnerReference reference says it was updated 2026-08-26 for v1.37 (`e3028857f9`). Other current docs were checked at their canonical live URLs; therefore docs pages and source code are version-related, not a byte-for-byte docs build from the code commit below.
- Kubernetes source was pinned by read-only `git ls-remote https://github.com/kubernetes/kubernetes.git` lookup: tag `v1.37.0` resolves to commit `f54c212e3a2f75d674b717a9b29052b20b60aefc` (the tag object was `157e582fcc3ebba3c22b16721f49d6890f784c1f`). All GitHub source URLs below use that immutable commit.
- Primary research: Sieve appeared in USENIX OSDI 2022 (proceedings pages 143–159); Anvil appeared in USENIX OSDI 2024. The linked publisher PDFs are the original papers. Findings from papers are research results and assumptions, not Kubernetes API guarantees or KPR validation.

## Retrieved source map and evidence

| Source | URL | Evidence used |
|---|---|---|
| Kubernetes Garbage Collection | https://kubernetes.io/docs/concepts/architecture/garbage-collection/ | Foreground/background cascading deletion, owner finalizer, orphaned dependents. Current docs identify default background cleanup and explicit orphan policy. |
| Kubernetes Owners and Dependents | https://kubernetes.io/docs/concepts/overview/working-with-objects/owners-dependents/ | Owner reference includes name and UID; foreground/orphan finalizers; owner relationships differ from labels/selectors. |
| Kubernetes OwnerReference API | https://kubernetes.io/docs/reference/kubernetes-api/definitions/owner-reference-v1-meta/ | Owner UID field; `controller` and `blockOwnerDeletion` meaning. Generated page updated for v1.37. |
| Kubernetes Object Names and IDs | https://kubernetes.io/docs/concepts/overview/working-with-objects/names/#uids | UIDs distinguish every historical object in cluster lifetime, including same-name incarnations. |
| Kubernetes Finalizers | https://kubernetes.io/docs/concepts/overview/working-with-objects/finalizers/ | Deletion timestamp/202 response and object retention until responsible finalizer removal; deletion cannot be undone by resurrecting object. |
| Kubernetes Job docs | https://kubernetes.io/docs/concepts/workloads/controllers/job/ | Job deletion/Pod relationship; unmanaged Job orphan-policy note; Job tracking finalizer only removed after Pod accounted in Job status. |
| Kubernetes Pod lifecycle | https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination | Kubelet/runtime termination is asynchronous; forced deletion does not wait for node confirmation. |
| kubectl delete reference | https://kubernetes.io/docs/reference/kubectl/generated/kubectl_delete/ | Force delete may leave processes running, particularly if node is unreachable. |
| ControllerRefManager, v1.37.0 | https://github.com/kubernetes/kubernetes/blob/f54c212e3a2f75d674b717a9b29052b20b60aefc/pkg/controller/controller_ref_manager.go | `ClaimObject`: skip another controller UID; release owned object when selector stops matching; only adopt nonterminating matching orphans; patch includes dependent UID and owner UID. |
| Deployment controller, v1.37.0 | https://github.com/kubernetes/kubernetes/blob/f54c212e3a2f75d674b717a9b29052b20b60aefc/pkg/controller/deployment/deployment_controller.go | Rechecks parent deletion timestamp with uncached read after listing; checks fresh UID; periodic resync comment; 15-retry cutoff and Forget path. |
| Job controller, v1.37.0 | https://github.com/kubernetes/kubernetes/blob/f54c212e3a2f75d674b717a9b29052b20b60aefc/pkg/controller/job/job_controller.go | Rechecks fresh Job UID before adopting; Job tracking finalizer registration and orphan cleanup; separate rate-limited orphan queue. |
| client-go workqueue limiter, v1.37.0 | https://github.com/kubernetes/kubernetes/blob/f54c212e3a2f75d674b717a9b29052b20b60aefc/staging/src/k8s.io/client-go/util/workqueue/default_rate_limiters.go | Per-item exponential retry delay with cap plus aggregate token bucket. |
| Sieve, USENIX OSDI 2022 | https://www.usenix.org/system/files/osdi22-sun.pdf | Primary study/tool systematically perturbs controller views; paper reports serious safety/liveness bugs. Publisher copy, 18 pages. |
| Anvil, USENIX OSDI 2024 | https://www.usenix.org/system/files/osdi24-sun-xudong.pdf | Primary study formalizes eventual stable reconciliation; progress proof includes asynchronous requests, interleavings, faults, fairness, and eventual fault quiescence assumptions. Publisher copy, 19 pages. |

## Limits recorded

- Documentation describes public API semantics; it does not guarantee a node process has stopped whenever an API object disappears. Kubelet/runtime evidence is asynchronous, and force deletion can free an API name while a process remains.
- ControllerRef adoption is a Kubernetes-specific mutable object graph. It is not a general transfer of operator responsibility, authorization, task ownership, or semantic result acceptance.
- Kubernetes uses persistent API objects and informer queues; KPR uses ACP sessions and existing local receipts/index/Workflow sources. Timing, durability, race boundaries, and authority differ.
- Public research reveals patterns and known failure classes. It cannot prove KPR candidate correctness. No implementation QA was performed for this branch.
