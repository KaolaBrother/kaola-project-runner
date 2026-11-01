# Devin Sideagent session origin (#450)

The Runner record directory is `<root>/devin/<session>/<sha256(repo)[:16]>`.
The digest describes the canonical repository path, so equal digests across
seats in the same project are expected; the session-name component separates
those record directories. Devin's own `sessions.db` is under
`$XDG_DATA_HOME/devin/cli`, not under that Runner record directory. Runner
`--continue` asks `session/list` for the repository, chooses the latest
unambiguous timestamp, and uses `session/resume` or `session/load`. The CLI
advertises `loadSession: true`. Devin's documented `-c/--continue` chooses
its most recent conversation and `-r/--resume` chooses a session; `devin acp`
accepts neither option in its help. A sandbox probe of Devin 3000.11.92 verified that `DEVIN_SESSIONS_DIR` moves the
database to `<value>/cli/sessions.db`. The holder sets it to the Sideagent
seat record directory plus `devin-sessions`, isolating its native inventory
from other seats; other roles keep their existing configuration. The internal mechanism reported by Studio
that connected a purported fresh start to an old ID is not established here.

In a clean, unauthenticated sandbox with Devin 3000.11.92, `session/new`
returned `quark-tumble` and `precious-naranja`; both prompt attempts returned
login-required and `session/list` returned no persisted rows. A subsequent KPR
Sideagent start returned a third ID `road-hound` with `session/new`, followed
by an exact stop. After the guard change, another sandbox start returned
`attractive-glue` and was exact-stopped. With per-seat DB isolation applied,
`ribbon-avocado` reached ready and the DB appeared under the Sideagent record
directory; exact stop returned no residual PIDs. In the same Sideagent DB
directory, two further `session/new` calls returned `honorable-paint` and
`tide-ethernet`; inventory remained empty, and the next KPR Sideagent start
returned `harsh-catboat` and exact-stopped without residual PIDs. This is partial evidence: it does not
reproduce a persisted prior-session inventory or Studio's foreign load.

The guard refuses explicit and inherited Sideagent resume/continue, snapshots
recorded Devin seat IDs, lists Devin's session inventory before `session/new`,
and refuses a missing or already-known new ID. It buffers session-scoped
startup notifications until the response identifies the new session; a
mismatched ID is refused without projecting its content. A later foreign ID
stops the holder and refuses further work. The check cannot prove that a CLI
has not reused an unlisted, unrecorded ID while labeling it a new session;
the Studio origin vector remains unverified. The existing Runner record-directory digest by itself does not isolate native
storage; the Sideagent-specific environment setting supplies that isolation.

## Validation and timing evidence

On the final implementation, controlled `validate.sh --suite` ran the Devin
regressions (36/36), #255 lifecycle suite (178/178), and Grok Bot pin contract
(45/45) under Python 3.13 and Bash 5. `render-skills.py --write` and `--check`
passed; `--check --require-pinned` refused the post-release delta, as intended.

Earlier direct #255 diagnostics had node-activity timeouts. With Python 3.13,
the recovery-batch case timed out on both candidate and clean baseline
`9ce17666` (at different points in the batch). The checkpoint case that failed
in a full diagnostic passed on individual reruns on both trees. The earlier
build-skew case likewise passed individual reruns on both. An initial diagnostic
used Python 3.9, below the project minimum, and is not counted as acceptance.
The later controlled run above passed the full selected #255 suite without an
exception. These observations do not establish a root cause for the timeouts.
