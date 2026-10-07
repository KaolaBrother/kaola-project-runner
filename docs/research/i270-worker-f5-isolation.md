# Issue #270 family-5 — isolation, runtime loading, data boundary

Read-only raw files at the SHAs below. No clone, install, or deploy. Every fact is README_MENTIONED or SOURCE_VERIFIED.

## OpenHands agent-server (Docker / K8s)

`OpenHands/software-agent-sdk` main `608a102c637d8d8a999f49d7b04846524bd8bd1c`, tree `5ecbb5c214b2b39976ef7adab41ac93492b6862f`. SOURCE_VERIFIED: root `LICENSE` MIT, Copyright (c) 2026 OpenHands contributors; `clients/typescript/LICENSE` also MIT. No second partition in files read. `openhands-agent-server` and `openhands-workspace` are both `1.53.0`.

Isolation SOURCE_VERIFIED: `DockerWorkspace` (`openhands-workspace/.../docker/workspace.py`) `docker run -d --rm` of `ghcr.io/openhands/agent-server:latest-python`, publish `127.0.0.1:host_port:8000`, optional `--network`, `--gpus all`, and caller `-v`. That argv has no user, cap-drop, or read-only root. `AgentSandboxWorkspace` claims a `SandboxWarmPool` via extra `openhands-workspace[agent-sandbox]` (`k8s-agent-sandbox>=0.5.0`); missing import raises `ImportError`. Docstring: gVisor/Kata `runtimeClass` is a SandboxTemplate choice, not Python (comment only).

Data/secret SOURCE_VERIFIED: `forward_env` copies `OH_SESSION_API_KEYS_0` and `SESSION_API_KEY` in; client prefers V1, V0 only if V1 is absent. `materialize_secrets` (`docker_runtime/mediation.py`) makes `StaticSecret` before the boundary. `RuntimeProvisioningStore` requires `OH_SECRET_KEY`, refuses symlink roots, mode `0o700`, per-conversation `RuntimeIdentity`. `_secret_redaction.py` masks named secret fields and Fernet tokens on JSON/JSONL export.

Module/version SOURCE_VERIFIED: K8s extra fails closed; `DockerDevWorkspace` via `__getattr__`; removed `mount_dir` raises `ValueError` naming `volumes`.

KPR: optional extra plus export redaction fit. No capability/degrade manifest. Host volumes and forwarded session keys cross the boundary. Isolation is Docker/Kubernetes, not an in-process module.

## E2B

`e2b-dev/E2B` main `c0f426ae479806538808c4fa407b7b0ad86c2576`, tree `67fb0bad005456355f487655eec44245854fba99`.

License split SOURCE_VERIFIED: root `LICENSE` Apache-2.0, appendix `Copyright 2023 FoundryLabs, Inc.`; `packages/{cli,js-sdk,python-sdk,code-interpreter-*,desktop-*}/LICENSE` MIT, `Copyright (c) 2025 FOUNDRYLABS, INC.`; `packages/js-sdk/package.json` MIT `2.53.1`. GitHub repo field is Apache-2.0. No proprietary file in this tree.

Cloud runtime is another repo (README self-host link). `e2b-dev/runtime` `47096f195aca4a545a9079b706efb3a18f51cf3f`, tree `e43552c591f930dcce83f03cb8b7192bdb480f59`: sole `LICENSE` Apache-2.0. README_MENTIONED: one codebase for E2B Cloud, enterprise deploy, and Embed; Firecracker microVM, cgroup, netns, nftables. SOURCE_VERIFIED in the SDK only: `Sandbox.create` / `SandboxApi` REST `/sandboxes/{sandboxID}`; `ConnectionConfig` uses `E2B_API_KEY`, default `https://api.${domain}` (`e2b.app`, `e2b.dev`, `e2b.pro`, `e2b-staging.dev`); `debug` uses local envd and skips kill. `buildNetworkBody` sends allow/deny, egress proxy, `allowPublicTraffic`. `buildIamBody` sends workload tokens and omits an empty map. `getSignature` is `v1_` SHA-256 of path, op, user, `envdAccessToken`. `retries` comment excludes create and secret append. `validateApiKey` is a deprecated no-op.

KPR: SDK can ship while the runtime repo is absent; network/IAM is a real boundary. No in-repo manifest. Default is a cloud API key. Root Apache vs package MIT conflicts for reuse. The VM is not in this repo.

## Daytona

Main `ec4c21b2d597091ac09ecc278f3bcc172575a987`, tree `a6d42a80386402376af537c6cc4af333b9de4755`: `README.md` and `assets/` only. README_MENTIONED: unmaintained June 2026; development went private; public license stays tag `v0.190.0`. Source read: commit `01c502bb1f1ff8f2885d0cd490e043736083dca8`, tree `eba3a1f8d5f65a7e0f2a9f25e0adaa8db5506030` (2026-06-23).

Partition SOURCE_VERIFIED: root `LICENSE` AGPL-3.0. `COPYRIGHT`: AGPL unless a directory LICENSE or file notice differs. `.licenserc.yaml` AGPL on `go/sh/js/ts/tsx/py`, ignores `libs/**`, re-includes `libs/computer-use/**`. `.licenserc-clients.yaml` Apache-2.0 on other `libs/**` and `guides/**`. `libs/sdk-python/LICENSE` and `libs/api-client/LICENSE` are the same Apache-2.0 file. `libs/computer-use/main.go` header AGPL-3.0; `libs/sdk-python/.../__init__.py` header Apache-2.0.

Isolation SOURCE_VERIFIED: `DockerClient.Create` pulls a snapshot and `ContainerCreate`s `linux/amd64`. `getContainerHostConfig` sets `Privileged: gpuIndex == nil` (non-GPU still privileged; GPU uses CDI, privileged off), daemon bind `:ro`, optional `daytona-computer-use` bind `:ro`, CPU/memory quotas, and `Runtime` from `GetContainerRuntime()` when set. Main README_MENTIONED "dedicated kernel" is not this config unless that runtime is set.

Data/module/version SOURCE_VERIFIED: create waits on the guest daemon with `AuthToken`. Computer-use is an optional read-only bind. Python `__getattr__` lazy-imports submodules that remain in the package. `ClientRejectsUnknownResponseFields` reads `X-Daytona-Source` and `X-Daytona-SDK-Version`; Go SDK `< 0.188.0` is treated as rejecting unknown JSON fields; other sources stay tolerant.

KPR: license partition and named semver branch fit optional modules and refuse-on-skew. AGPL runner, privileged containers, a frozen tree, and a control-plane service do not fit an in-process module that degrades when absent.
