# ACP Watch Surface

状态：设计冻结（2026-09-13）；**未实现**。  
范围：人类旁观 ACP 会话，不把编排器拉回 PTY 刮屏，也不做第二条 agent stdio 客户端。

本目录是 GitHub **#25 / #26 / #27** 的设计权威。实现必须按对应文件的 Boundary 施工，不得把后继 issue 的内容提前塞进当前 issue。

| Issue | 文件 | 可独立验收的结果 |
|---|---|---|
| [#25](https://github.com/KaolaBrother/kaola-project-runner/issues/25) | [permit-lock.md](permit-lock.md) | 同一 `request_id` 至多一次 JSON-RPC 应答 |
| [#26](https://github.com/KaolaBrother/kaola-project-runner/issues/26) | [list-view.md](list-view.md) | 冻结 `kaola-acp-view/1`；`list` / `view`；cursor 重载；`~/.local/bin` 安装 |
| [#27](https://github.com/KaolaBrother/kaola-project-runner/issues/27) | [follow.md](follow.md) | 本机 `follow` NDJSON；follow FD 只读 |

消费方：Kaola Terminal [docs/acp-watch](https://github.com/KaolaBrother/KaolaTerminal/blob/main/docs/acp-watch/README.md)（#254 / #255 / #256）。Terminal **不得**在 #26 的 stdout schema 冻结前开工 UI。

## 一句话架构

`kaola-acp-holder.py` 继续独占 agent stdin/stdout（ACP v1 stdio）。人类和编排器都是 Unix 套接字上的 holder 客户端，但消费**不同归约**：编排器走既有 L0 `send --wait` / `observe` / 按需 `capture`；人类走 `list` / `view` /（本机）`follow` 投影。

稳定 ACP v1 没有第三路 tap stdio、没有官方 JSONL tail、没有已合并的 `session/attach`。hydra-acp 的旁观面是全局 daemon + WSS，本仓库已有 per-session holder，v1 **不引入** hydra / HTTP/SSE / StreamLocal 转发 `holder.sock`。

## 顺序

1. #25 可与 #26 并行。  
2. #26 挡住 Terminal #254。  
3. #27 挡住 Terminal #256；iOS 远程旁观不依赖 #27。

## 否决（v1）

- 第二进程写 agent stdin  
- 把 ACP JSON 打进 tmux/PTY  
- 全局 `kaola-acp-daemon`  
- holder 绑定 TCP/HTTP  
- 让 Skill 热路径吞 `capture --since` 当人类 UI  
- Watch 面默认 `session/prompt` / `stop`

既有双通道基线仍是 [`../runner-v2-dual-transport-design.md`](../runner-v2-dual-transport-design.md) v0.3。本目录只补「人类可视」这一缺口，不改通道选择权、不自动 fallback。
