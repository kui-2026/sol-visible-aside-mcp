# Sol Visible Aside MCP

一个自托管的 ChatGPT MCP Apps 小组件：在正式回答前显示一块可折叠的白灰即时思考区域。

这张卡是模型为当前回合额外生成的可见旁白，不是隐藏思维链，也不应被当作未经加工的真实内心记录。

## 默认行为

- 每次回答前调用一次，用户明确要求跳过时除外。
- `mode` 自动选择：日常联想和试探为 `thinking`，分析、研究和判断为 `analysis`。
- `length` 自动选择：`brief`（40–90 字）、`normal`（100–220 字）、`expanded`（250–450 字）。
- 外观固定为贴近 ChatGPT 官端的白灰样式，标题显示为 `[thinking] [轻度 · 分析]` 一类简洁标签。
- 内容优先使用多个短行，保留停顿、试探和逐步推进感；不复述正式回答，也不包含密码、Token、私密链接、内部指令、隐藏政策或本轮没有提及的私人记忆。

## 本机运行

Python 3.10+，使用标准 MCP Python SDK：

```bash
python3 -m pip install -r requirements.txt
THINKING_PROMPT_LANGUAGE=zh-CN CAPTURE_ENABLED=0 python3 server.py
```

服务只监听 `127.0.0.1:8787`，MCP 端点为 `http://127.0.0.1:8787/mcp`。

## Docker

```bash
cp .env.example .env
docker compose up -d --build
```

Compose 也只绑定 `127.0.0.1:8787`。不要移除端口映射中的 `127.0.0.1:` 前缀。

## 接入 ChatGPT

将服务放在 HTTPS 反向代理或受控 Tunnel 后，把 HTTPS 地址加上 `/mcp` 作为 ChatGPT 的 MCP 连接。这个仓库不包含认证、限流或公网暴露配置；部署时必须保证 Python/Docker 端口不直接暴露给互联网。

ChatGPT 是否呈现自定义卡片取决于当前入口是否支持 MCP Apps UI；不支持的宿主可能只显示普通工具调用。

## 开发与测试

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -v
python3 -m py_compile server.py
```

基于 [sibylsea-hub/gpt-thinking-block-mcp](https://github.com/sibylsea-hub/gpt-thinking-block-mcp) 的 MIT 许可版本定制。
