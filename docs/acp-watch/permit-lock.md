# Issue #25 — ACP holder permit/cancel at-most-once

设计权威：[GitHub #25](https://github.com/KaolaBrother/kaola-project-runner/issues/25)。  
状态：设计冻结（2026-09-13）；**未实现**。

## 决策

`op_permit` / `op_cancel` / `op_stop` 对 pending permission 的结算必须与 `op_prompt` 的准入落在同一把锁上。每个 ACP `request_id` 对 agent stdin **至多一次** JSON-RPC 结果。第二位结算者得到结构化事实，不得再写 agent。

编排器与人类谁先写完谁赢，v1 不加租约。这与 hydra / RFD #533 的 first-writer-wins 一致，但实现点是 holder，不是网络 mux。

## 当前代码事实

- `scripts/kaola-acp-holder.py`：`op_prompt` 使用 `self.lock`（约 746–806）；`op_permit`（约 850–878）与 `op_cancel`（约 880–902）不持该锁。
- `listen(16)`，每条 Unix 连接一个 daemon 线程。
- 合同测试覆盖三个**不同** pending id，以及 `request-id-required`；不覆盖同一 id 的双 permit。
- Issue #22 / 默认 skip-all 只降低 `request_permission` 出现频率，不序列化应答。`permit` 在 agent 仍发权限请求时必须安全。

## 必须改的行为

1. 在锁内：查找 pending → 发送恰好一条 JSON-RPC result → `pop`。  
2. 锁外不得再 `send_message` 该 id。  
3. 已结算 id：返回既有 `unknown-request` **或** 新增并冻结 `already-answered`（实现时二选一，合同测试钉死）。  
4. `op_cancel` 把仍 pending 的项标 cancelled 也走同一 at-most-once；不得对同一 id 写两次 cancelled。  
5. 不改变 skip-all / `mode=yolo` 等平台 knobs，不改变 L0 回执键。

## 验收

- 两线程对同一 `request_id` `permit`：agent stdin 恰好一条 result；败者得事实。  
- 既有 13 支合同 + #22 skip-all 合同保持绿。  
- `render-skills.py --write && --check`；`./scripts/validate.sh`。

## 非本单

Watch UI、`list`/`view`/`follow`、HTTP、hydra、改 skip-all 默认值。
