# Issue 409 — run state (final)

- Issue: KaolaBrother/kaola-project-runner#409 — Kimi CLI: default = K2.8 (max); K3.1 Pro = higher Elite tier (max)
- Run: Host self-executed (zcode Host `zcode-KPR-orchestrator-main`, owner instruction 2026-10-24 ~12:21 Asia/Taipei: resume Host, implement #409 end-to-end, merge, cut release). No worker seat dispatched: single-manifest catalog change with verbatim owner text and live verification; release mechanics are Host-owned.
- Branch: `workflow/issue-409` from main `891a15eb` (v0.9.28).
- Outcome: implemented, gate green, merged; release v0.9.29 cut on main per owner instruction (release commits are their own records).

## Owner-approved final shape (source: issue body + correction comments 00:38–00:47)

1. `kimi-cli/default` → Kimi K2.8 (`kimi-code/kimi-for-coding`) at thinking=max, Elite; preset id `default` stable.
2. Higher named Elite tier `kimi-k3-1-pro` → Kimi K3.1 Pro at thinking=max (Elite escalation, not Expert); native id verified live, not invented.
3. Higher-tier profile verbatim: "Strong all round worker. Strong at visual design and visual inspection, with good UI and design taste."
4. Old `kimi-cli/kimi-k2-8` duplicate folded into `default`; old default K3 (`kimi-code/k3`) dropped from the preset catalog; disposition in CHANGELOG.
5. Profile catalog / worker manifests / README re-rendered; contracts pinning `kimi-code/k3` as default updated (tests #111/#218, architecture doc).
6. No KPM mirror.
7. Gate green; release note names the retarget + new higher tier.
