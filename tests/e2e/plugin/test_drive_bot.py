"""
drive_bot 插件离线测试

规范:
  PL-54: 私聊每日新闻 → 私聊图片回复
  PL-55: 私聊文件结果 → upload_private_file + 私聊文本回复
  PL-56: 私聊询问使用方法 → 返回使用说明
  PL-57: JM 下载失败 → 返回错误提示
  PL-58: JM 下载完成但 PDF 缺失 → 抛出明确错误
  PL-59: JM 多章节 PDF → 逐个上传并删除
  PL-60: JM crawler 返回多个 PDF 文件
  PL-61: JM 章节 PDF 命名包含 album id / 漫画名 / 章节序号
  PL-62: 群聊 at 机器人询问使用方法 → 去掉 at 段后返回使用说明
  PL-63: 未知私聊消息 → AI 兜底回复
  PL-64: 已有关键词命中 → 不调用 AI 兜底
  PL-65: AI 兜底依赖声明包含 litellm
  PL-66: AI 兜底 system prompt 接入 neko-on-everything skill
"""

from __future__ import annotations

import importlib
import tomllib
from pathlib import Path

import pytest

from ncatbot.plugin.manifest import PluginManifest
from ncatbot.testing import PluginTestHarness
from ncatbot.testing.factories.qq import group_message, private_message


PLUGIN_NAME = "drive_bot"
USER_ID = "1620404337"


@pytest.fixture
def drive_plugins_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "code" / "plugins"


def _patch_message_parser(plugin, monkeypatch, answer):
    module = importlib.import_module(plugin.__class__.__module__)

    async def fake_message_parser(msg, last_time, logger):
        return dict(answer)

    monkeypatch.setattr(module, "message_parser", fake_message_parser)


def test_drive_bot_declares_litellm_dependency(drive_plugins_dir):
    """PL-65: manifest.toml 和 code/requirements.txt 均声明 AI 兜底所需 litellm"""
    plugin_dir = drive_plugins_dir / PLUGIN_NAME
    manifest = tomllib.loads((plugin_dir / "manifest.toml").read_text(encoding="utf-8"))
    assert manifest["pip_dependencies"]["litellm"] == ">=1.83.0"

    parsed_manifest = PluginManifest.from_toml(plugin_dir / "manifest.toml")
    assert parsed_manifest.pip_dependencies["litellm"] == ">=1.83.0"

    requirements = (
        Path(__file__).resolve().parents[3] / "code" / "requirements.txt"
    ).read_text(encoding="utf-8")
    assert "litellm" in requirements


async def test_private_daily_news_replies_with_image(drive_plugins_dir, monkeypatch):
    """PL-54: 私聊每日新闻结果 direct_upload → send_private_msg 带图片"""
    async with PluginTestHarness(
        plugin_names=[PLUGIN_NAME], plugins_dir=drive_plugins_dir
    ) as h:
        plugin = h.get_plugin(PLUGIN_NAME)
        _patch_message_parser(
            plugin,
            monkeypatch,
            {
                "text": "请查收",
                "file_path": "/tmp/moyu_image.jpg",
                "file_name": "",
                "upload_file": True,
                "direct_upload": True,
                "updated_time": 123,
            },
        )

        await h.inject(private_message("每日新闻", user_id=USER_ID))
        await h.settle(0.1)

        h.assert_api("send_private_msg").called().with_params(
            user_id=USER_ID
        ).with_text("请查收").where(
            lambda call: any(
                seg.get("type") == "image"
                and seg.get("data", {}).get("file") == "/tmp/moyu_image.jpg"
                for seg in call.params["message"]
            )
        )
        h.assert_api("upload_private_file").not_called()


async def test_private_file_result_uploads_private_file(drive_plugins_dir, monkeypatch):
    """PL-55: 私聊文件结果 upload_file → upload_private_file，不走群文件夹"""
    async with PluginTestHarness(
        plugin_names=[PLUGIN_NAME], plugins_dir=drive_plugins_dir
    ) as h:
        plugin = h.get_plugin(PLUGIN_NAME)
        _patch_message_parser(
            plugin,
            monkeypatch,
            {
                "text": "文件已上传",
                "file_path": "/tmp/book.zip",
                "file_name": "book.zip",
                "upload_file": True,
                "direct_upload": False,
                "upload_folder_name": "本子",
                "updated_time": 456,
            },
        )

        await h.inject(private_message("jm 123", user_id=USER_ID))
        await h.settle(0.1)

        h.assert_api("upload_private_file").called().with_params(
            user_id=USER_ID,
            file="/tmp/book.zip",
            name="book.zip",
        )
        h.assert_api("send_private_msg").called().with_params(
            user_id=USER_ID
        ).with_text("文件已上传")
        h.assert_api("get_group_root_files").not_called()
        h.assert_api("upload_group_file").not_called()


async def test_private_multi_pdf_uploads_each_file_and_deletes(
    drive_plugins_dir, monkeypatch, tmp_path
):
    """PL-59: 多个章节 PDF → 私聊逐个上传，上传成功一个删除一个"""
    files = []
    for index in range(2):
        path = tmp_path / f"chapter-{index + 1}.pdf"
        path.write_bytes(b"%PDF-1.4")
        files.append({"file_name": path.name, "file_path": str(path)})

    async with PluginTestHarness(
        plugin_names=[PLUGIN_NAME], plugins_dir=drive_plugins_dir
    ) as h:
        plugin = h.get_plugin(PLUGIN_NAME)
        _patch_message_parser(
            plugin,
            monkeypatch,
            {
                "text": "文件已上传",
                "upload_file": True,
                "direct_upload": False,
                "upload_folder_name": "本子",
                "files": files,
                "updated_time": 789,
            },
        )

        await h.inject(private_message("/jm 1194365", user_id=USER_ID))
        await h.settle(0.1)

        upload_calls = h.assert_api("upload_private_file").calls
        assert [call.params["name"] for call in upload_calls] == [
            "chapter-1.pdf",
            "chapter-2.pdf",
        ]
        assert all(not Path(item["file_path"]).exists() for item in files)
        h.assert_api("send_private_msg").called().with_params(
            user_id=USER_ID
        ).with_text("文件已上传")


async def test_private_usage_question_returns_usage_text(drive_plugins_dir):
    """PL-56: 私聊发送 '使用方法。' → 返回 drive_bot 使用说明"""
    async with PluginTestHarness(
        plugin_names=[PLUGIN_NAME], plugins_dir=drive_plugins_dir
    ) as h:
        await h.inject(private_message("使用方法。", user_id=USER_ID))
        await h.settle(0.1)

        h.assert_api("send_private_msg").called().with_params(
            user_id=USER_ID
        ).with_text("Drive Bot 使用方法", "/jm 关键词", "/jm 数字ID", "每日新闻")


async def test_group_usage_question_after_at_returns_usage_text(drive_plugins_dir):
    """PL-62: 群聊 at 机器人发送 '使用方法' → 返回 drive_bot 使用说明"""
    self_id = "10001"
    async with PluginTestHarness(
        plugin_names=[PLUGIN_NAME], plugins_dir=drive_plugins_dir
    ) as h:
        await h.inject(
            group_message(
                "使用方法",
                group_id="1019587647",
                user_id=USER_ID,
                self_id=self_id,
                raw_message=f"[CQ:at,qq={self_id}] 使用方法",
                message=[
                    {"type": "at", "data": {"qq": self_id}},
                    {"type": "text", "data": {"text": " 使用方法"}},
                ],
            )
        )
        await h.settle(0.1)

        h.assert_api("send_group_msg").called().with_params(
            group_id="1019587647"
        ).with_text("Drive Bot 使用方法", "/jm 关键词", "/jm 数字ID", "每日新闻")


async def test_private_unknown_message_uses_ai_fallback(drive_plugins_dir, monkeypatch):
    """PL-63: 未知私聊消息命中 AI 兜底，而不是返回固定无法理解文本"""
    ai_module = importlib.import_module("ncatbot.adapter.ai.api.bot_api")
    monkeypatch.setenv("DRIVE_BOT_AI_API_KEY", "env-test-key")

    async def fake_chat_text(self, content_or_messages, **kwargs):
        assert content_or_messages[0]["role"] == "system"
        system_prompt = content_or_messages[0]["content"]
        assert "Drive Bot roleplay skill" in system_prompt
        assert "neko-on-everything" in system_prompt
        assert "references/persona.md" in system_prompt
        assert content_or_messages[-1] == {
            "role": "user",
            "content": "今天适合干什么",
        }
        assert kwargs["api_base"] == "https://api.deepseek.com"
        assert kwargs["api_key"] == "env-test-key"
        assert kwargs["model"] == "openai/deepseek-v4-flash"
        return "可以先喝水，再写一点代码。"

    monkeypatch.setattr(ai_module.AIBotAPI, "chat_text", fake_chat_text)

    async with PluginTestHarness(
        plugin_names=[PLUGIN_NAME], plugins_dir=drive_plugins_dir
    ) as h:
        await h.inject(private_message("今天适合干什么", user_id=USER_ID))
        await h.settle(0.1)

        h.assert_api("send_private_msg").called().with_params(
            user_id=USER_ID
        ).with_text("可以先喝水，再写一点代码。")


async def test_private_keyword_match_skips_ai_fallback(drive_plugins_dir, monkeypatch):
    """PL-64: 使用方法等已有关键词命中时不调用 AI 兜底"""
    async with PluginTestHarness(
        plugin_names=[PLUGIN_NAME], plugins_dir=drive_plugins_dir
    ) as h:
        plugin = h.get_plugin(PLUGIN_NAME)

        async def fail_if_called(prompt: str) -> str:
            raise AssertionError(f"AI fallback should not be called: {prompt}")

        monkeypatch.setattr(plugin, "_ask_ai", fail_if_called, raising=False)

        await h.inject(private_message("使用方法", user_id=USER_ID))
        await h.settle(0.1)

        h.assert_api("send_private_msg").called().with_params(
            user_id=USER_ID
        ).with_text("Drive Bot 使用方法", "/jm 关键词", "/jm 数字ID", "每日新闻")


async def test_private_jm_download_failure_returns_error_text(
    drive_plugins_dir, monkeypatch
):
    """PL-57: JM PDF 未生成等下载失败 → 回复错误文本，不抛出 handler 异常"""
    async with PluginTestHarness(
        plugin_names=[PLUGIN_NAME], plugins_dir=drive_plugins_dir
    ) as h:
        module = importlib.import_module("utils.msg_parser")

        def fake_jmcomic_crawler(jm_number, logger):
            raise RuntimeError("JM 下载完成，但未生成 PDF 文件，请检查 img2pdf 依赖")

        monkeypatch.setattr(module, "jmcomic_crawler", fake_jmcomic_crawler)

        await h.inject(private_message("/jm 1429682", user_id=USER_ID))
        await h.settle(0.1)

        h.assert_api("send_private_msg").called().with_params(
            user_id=USER_ID
        ).with_text("JM 下载失败", "img2pdf")
        h.assert_api("upload_private_file").not_called()


def test_jmcomic_crawler_raises_when_pdf_missing(tmp_path, monkeypatch):
    """PL-58: JM 下载完成但未生成 PDF → 抛 RuntimeError 而不是 UnboundLocalError"""
    project_code_dir = Path(__file__).resolve().parents[3] / "code"
    monkeypatch.syspath_prepend(str(project_code_dir))
    module = importlib.import_module("utils.jmcomic_crawler")

    class FakeLogger:
        def info(self, *args):
            pass

        def debug(self, *args):
            pass

        def warning(self, *args):
            pass

    monkeypatch.setattr(module, "PDF_DIR", str(tmp_path))
    monkeypatch.setattr(module.jmcomic, "create_option_by_str", lambda *args, **kw: {})
    monkeypatch.setattr(module.jmcomic, "download_album", lambda *args, **kw: None)

    with pytest.raises(RuntimeError, match="未生成 PDF"):
        module.jmcomic_crawler(1429682, FakeLogger())


def test_jmcomic_crawler_returns_multiple_pdf_files(tmp_path, monkeypatch):
    """PL-60: JM 下载生成多个章节 PDF → 返回 files 列表"""
    project_code_dir = Path(__file__).resolve().parents[3] / "code"
    monkeypatch.syspath_prepend(str(project_code_dir))
    module = importlib.import_module("utils.jmcomic_crawler")

    class FakeLogger:
        def info(self, *args):
            pass

        def debug(self, *args):
            pass

        def warning(self, *args):
            pass

    def fake_download_album(*args, **kwargs):
        (tmp_path / "002.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "001.pdf").write_bytes(b"%PDF-1.4")

    monkeypatch.setattr(module, "PDF_DIR", str(tmp_path))
    monkeypatch.setattr(module.jmcomic, "create_option_by_str", lambda *args, **kw: {})
    monkeypatch.setattr(module.jmcomic, "download_album", fake_download_album)

    result = module.jmcomic_crawler(1194365, FakeLogger())

    assert result == [
        {"file_name": "001.pdf", "file_path": str(tmp_path / "001.pdf")},
        {"file_name": "002.pdf", "file_path": str(tmp_path / "002.pdf")},
    ]


def test_jmcomic_pdf_filename_rule_contains_album_title_and_chapter():
    """PL-61: JM 章节 PDF 文件名规则为 id-名称-章节.pdf"""
    project_code_dir = Path(__file__).resolve().parents[3] / "code"
    import sys

    if str(project_code_dir) not in sys.path:
        sys.path.insert(0, str(project_code_dir))
    constants = importlib.import_module("utils.constants")

    rule = constants.JMCOMIC_OPTION["plugins"]["after_photo"][0]["kwargs"][
        "filename_rule"
    ]
    assert rule == "{Aalbum_id}-{Aname}-{Psort}"
