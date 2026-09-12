# Issue #27 — ACP watch local `follow` stream

设计权威：[GitHub #27](https://github.com/KaolaBrother/kaola-project-runner/issues/27)。  
状态：设计冻结（2026-09-13）；**未实现**。依赖 [#26](list-view.md) 的 `kaola-acp-view/1`。

## 决策

本机 Kaola Terminal（或 CLI）可对短路径 `holder.sock` 做长连接 `follow`：先可选 snapshot，再推 cursor delta。这是 hydra `GET /v1/sessions/:id/history?follow=1` 的**本机 Unix 等价物**，不是 HTTP，不是 SSH exec 流。

iOS 远程 v1 **不用**本命令：Citadel `execute()` 15 秒且等进程退出。

## 行为

- CLI：`kaola-acp <platform> follow --repo … --session … [--since CURSOR]`  
- stdout NDJSON，每行 `{kind:snapshot|delta|heartbeat|eof|error, ...}`。snapshot/delta 的载荷与 `view` 同 schema。  
- 该 Unix 连接在首包 `follow` op 之后**只读**：`prompt` / `permit` / `cancel` / `stop` 必须走另一条短连接。  
- 心跳带全量 `pending_permissions` 与 `mutation_status`，避免丢 delta 就丢权限卡。  
- 慢消费者：该 follower 队列 >256 行则 `follow-dropped` 并断开**这一路**；agent stdio 不停。  
- 可选 `--format text`：把消息/工具标题拼成 tty 文本，**不是**第二套 TUI 引擎。

## 验收

- 双 follower 看到同一 `tool_call`。  
- follow FD 上写 `prompt`/`permit` 为错误；agent stdin 无额外 ACP 帧。  
- 第三条套接字仍可 `permit`（#25 的锁仍然适用）。  
- 杀掉 follow CLI 不停止 holder/agent。  
- `process_exited` 后跟 eof；holder-lost 为 error 行。

## 非本单

iOS/SSH 流式 exec；`ssh -L` 转 socket；hydra `/acp`；Terminal Mac 进程监督器（KaolaTerminal #256）。
