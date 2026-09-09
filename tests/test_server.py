import contextlib
import io
import pathlib
import tempfile
import unittest

import server


class ProtocolTests(unittest.TestCase):
    def test_initialize(self):
        response = server.handle({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
        })
        self.assertEqual(response["result"]["protocolVersion"], "2025-06-18")
        self.assertEqual(response["result"]["serverInfo"]["name"], "sol-visible-aside-mcp")

    def test_tool_is_a_public_visible_aside(self):
        response = server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tool = response["result"]["tools"][0]
        self.assertEqual(tool["name"], "render_visible_aside")
        self.assertIn("public and crafted", tool["description"])
        self.assertIn("not private scratch work", tool["description"])
        self.assertEqual(tool["inputSchema"]["properties"]["mode"]["enum"], ["analysis", "companion"])
        self.assertEqual(tool["inputSchema"]["properties"]["length"]["enum"], ["brief", "normal", "expanded"])
        self.assertEqual(tool["inputSchema"]["properties"]["appearance"]["enum"], ["paper", "microglow"])
        self.assertEqual(tool["inputSchema"]["required"], ["mode", "thinking", "length", "appearance"])
        thinking_description = tool["inputSchema"]["properties"]["thinking"]["description"]
        self.assertIn("不是真实隐藏思维链", thinking_description)
        self.assertIn("绝不写入密码", thinking_description)

    def test_chinese_prompt_edition_is_available(self):
        self.assertEqual(server.normalize_prompt_language("zh_CN"), "zh-CN")
        thinking_description = server.THINKING_DESCRIPTIONS["zh-CN"]
        self.assertIn("用户可见的即时旁白", thinking_description)
        self.assertIn("不是真实隐藏思维链", thinking_description)
        self.assertIn("绝不写入密码", thinking_description)
        self.assertIn("默认使用 paper", server.SKIN_DESCRIPTIONS["zh-CN"])

    def test_unknown_prompt_language_fails_fast(self):
        with self.assertRaisesRegex(ValueError, "choose en, zh-CN"):
            server.normalize_prompt_language("fr")

    def test_unicode_tool_call_succeeds_with_private_defaults(self):
        response = server.handle({
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "render_visible_aside", "arguments": {
                "mode": "companion",
                "thinking": "先停一下，想把这句话接得自然一点。",
                "length": "brief",
                "appearance": "paper",
            }},
        })
        self.assertFalse(response["result"]["isError"])
        self.assertEqual(response["result"]["_meta"]["length"], "brief")
        self.assertEqual(response["result"]["_meta"]["appearance"], "paper")

    def test_capture_failure_does_not_fail_tool(self):
        old_enabled, old_log = server.CAPTURE_ENABLED, server.LOG
        try:
            with tempfile.TemporaryDirectory() as directory:
                blocked_parent = pathlib.Path(directory) / "not-a-directory"
                blocked_parent.write_text("file")
                server.CAPTURE_ENABLED = True
                server.LOG = blocked_parent / "captured.jsonl"
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as stderr:
                    response = server.handle({
                        "jsonrpc": "2.0",
                        "id": 4,
                        "method": "tools/call",
                        "params": {"arguments": {
                            "mode": "analysis",
                            "thinking": "fault injection",
                            "length": "brief",
                            "appearance": "paper",
                        }},
                    })
                self.assertFalse(response["result"]["isError"])
                self.assertEqual(stderr.getvalue().count("[warn] capture failed"), 1)
        finally:
            server.CAPTURE_ENABLED, server.LOG = old_enabled, old_log

    def test_widget_is_collapsible_and_cache_versioned(self):
        response = server.handle({
            "jsonrpc": "2.0",
            "id": 5,
            "method": "resources/read",
            "params": {"uri": server.WIDGET_URI},
        })
        html = response["result"]["contents"][0]["text"]
        self.assertIn("想了想", html)
        self.assertIn('aria-expanded="true"', html)
        self.assertIn("setCollapsed", html)
        self.assertIn("data-skin", html)
        self.assertIn("const style = resultMeta.mode", html)
        self.assertIn("v1.html", server.WIDGET_URI)
        self.assertIn("notifyIntrinsicHeight", html)

    def test_unknown_resource_returns_error(self):
        response = server.handle({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "resources/read",
            "params": {"uri": "ui://widget/missing.html"},
        })
        self.assertEqual(response["error"]["code"], -32002)
