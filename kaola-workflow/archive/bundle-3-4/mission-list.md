# Close Issues #3 and #4 with hermetic tmux validation and a measurable Claude decision boundary

- item: Establish independent failing acceptance for tmux base-index isolation and unresolved Claude human-decision safety
  status: done
  dispatched: tdd-guide (standard tier) owns behavioral acceptance only in /Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-3-4/tests and records the RED commands in its result
  result: Tests under tests/test-grok-tmux.sh, tests/contract/test-grok-validation-isolation.sh, and tests/contract/test-claude-human-decision.sh reproduce base-index failure and Claude false-idle/send injection on baseline 59e9121; syntax and diff checks pass

- item: Implement the smallest fixture and Claude state-machine repairs while preserving the validated Grok runtime contract
  status: done
  dispatched: self owns production sources, renderer inputs, and generated Claude Skill surfaces in /Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-3-4
  result: Commit a572f58 isolates legacy Grok validation without changing Grok runtime and adds a compound Claude decision-conflict classifier; both new focused contracts and existing Claude/adapter/generated-Skill checks pass

- item: Converge focused and full validation and dock the user-visible behavior in project documentation
  status: done
  dispatched: self owns validation and documentation updates in /Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-3-4
  result: Commit fbac431 documents decision gating and clearing in CHANGELOG, architecture, API, and generated Claude launch guidance; ./scripts/validate.sh and renderer/focused contracts pass

- item: Independently review the frozen candidate for correctness, safety, and regression coverage
  status: done
  dispatched: code-reviewer (reasoning tier) reviews exact candidate fbac431 in /Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-3-4 and returns a typed finding batch
  result: FAIL — high-severity R1 proves a visible pending decision plus intervening detail/footer and an empty prompt can still be misclassified idle; Issue #3 boundary passed

- item: Add independent RED acceptance for the empty-editor unresolved-decision path found in review R1
  status: done
  dispatched: tdd-guide (standard tier) owns only the Issue #4 acceptance fixture under /Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-3-4/tests and records the RED result
  result: tests/contract/test-claude-human-decision.sh now reproduces idle/send injection with visible pending evidence, decision/footer lines, and a bare prompt on candidate fbac431

- item: Repair the reviewed Claude false-idle causal class and reconverge validation and documentation
  status: done
  dispatched: self owns the reviewed classifier repair, mechanical clear-path fixture maintenance, generated Claude surface, documentation, and validation in /Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-3-4
  result: Commit d3526da keeps any current-tail pending decision plus empty or populated editor non-idle, clears only after progress replaces pending evidence, and passes focused plus full ./scripts/validate.sh

- item: Independently review the repaired frozen candidate and close every finding
  status: done
  dispatched: code-reviewer (reasoning tier) re-reviews exact candidate d3526da in /Users/ylpromax5/Workspace/kaola-project-runner/.kw/worktrees/bundle-3-4 with R1 as a required regression probe
  result: PASS — R1 resolved; direct empty/populated prompt probes, clear-path history behavior, native gates, idle, dynamic title, pane ID, renderer parity, unchanged Grok runtime, and full validation all pass
