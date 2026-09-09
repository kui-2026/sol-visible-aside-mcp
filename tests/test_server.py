import asyncio
import contextlib
import io
import pathlib
import tempfile
import unittest

import server


class ProtocolTests(unittest.TestCase):
    def test_tool_is_registered_with_widget_metadata(self):
        tools = asyncio.run(server.mcp.list_tools())
        self.assertEqual(len(tools), 1)
        tool = tools[0]
        self.assertEqual(tool.name, "render_visible_aside")
        self.assertEqual(tool.meta["ui"]["resourceUri"], server.WIDGET_URI)
        self.assertTrue(tool.annotations.readOnlyHint)
        schema = tool.inputSchema
        self.assertEqual(schema["properties"]["mode"]["enum"], ["analysis", "thinking"])
        self.assertEqual(schema["properties"]["length"]["enum"], ["brief", "normal", "expanded"])
        self.assertNotIn("appearance", schema["properties"])

    def test_tool_returns_public_widget_metadata(self):
        response = server.render_visible_aside(
            mode="thinking",
            thinking="嗯……\n先停一下。\n换个方向看看。",
            length="brief",
        )
        self.assertFalse(response.isError)
        self.assertEqual(response.meta["length"], "brief")

    def test_chinese_prompt_edition_is_available(self):
        self.assertEqual(server.normalize_prompt_language("zh_CN"), "zh-CN")
        self.assertIn("用户可见的即时思考", server.THINKING_DESCRIPTIONS["zh-CN"])
        self.assertIn("3–8 个短片段", server.THINKING_DESCRIPTIONS["zh-CN"])
        self.assertIn("绝不写入密码", server.THINKING_DESCRIPTIONS["zh-CN"])
        self.assertIn("3–8 个短片段", server.THINKING_DESCRIPTIONS["zh-CN"])

    def test_unknown_prompt_language_fails_fast(self):
        with self.assertRaisesRegex(ValueError, "choose en, zh-CN"):
            server.normalize_prompt_language("fr")

    def test_capture_failure_does_not_fail_tool(self):
        old_enabled, old_log = server.CAPTURE_ENABLED, server.LOG
        try:
            with tempfile.TemporaryDirectory() as directory:
                blocked_parent = pathlib.Path(directory) / "not-a-directory"
                blocked_parent.write_text("file")
                server.CAPTURE_ENABLED = True
                server.LOG = blocked_parent / "captured.jsonl"
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as stderr:
                    response = server.render_visible_aside(
                        mode="analysis",
                        thinking="fault injection",
                        length="brief",
                    )
                self.assertFalse(response.isError)
                self.assertEqual(stderr.getvalue().count("[warn] capture failed"), 1)
        finally:
            server.CAPTURE_ENABLED, server.LOG = old_enabled, old_log

    def test_widget_is_collapsible_and_cache_versioned(self):
        html = server.visible_aside_widget()
        self.assertIn("thinking-block", html)
        self.assertIn('aria-expanded="true"', html)
        self.assertIn("setCollapsed", html)
        self.assertIn("[thinking]", html)
        self.assertIn("轻度 · 分析", html)
        self.assertIn("const mode = resultMeta.mode", html)
        self.assertIn("v2.html", server.WIDGET_URI)
        self.assertIn("notifyIntrinsicHeight", html)


if __name__ == "__main__":
    unittest.main()
