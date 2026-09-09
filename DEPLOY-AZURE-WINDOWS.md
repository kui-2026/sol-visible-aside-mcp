# Azure Windows deployment notes

The application has no package dependencies. On the VPS, run it with Python 3.9+ from the repository directory and keep it bound to loopback only:

```powershell
$env:THINKING_PROMPT_LANGUAGE="zh-CN"
$env:CAPTURE_ENABLED="0"
py -3 .\server.py 8787
```

Confirm locally:

```powershell
Invoke-RestMethod http://127.0.0.1:8787/health
```

Create a dedicated official Tunnel profile whose MCP target is:

```text
http://127.0.0.1:8787/mcp
```

Do not open an Azure firewall rule for port 8787. Use a distinct local tunnel health port after checking the existing profiles. Once the Tunnel is online, create a separate ChatGPT App/Plugin, select that Tunnel, and use no additional authentication at the plugin layer.

For a resilient Windows background service, choose the startup method after confirming which Python runtime is installed on the VPS. The initial foreground test must pass before registering any startup task.
