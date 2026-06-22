"""
drive_bot 插件离线测试

规范:
  PL-54: 私聊每日新闻 → 私聊图片回复
  PL-55: 私聊文件结果 → upload_private_file + 私聊文本回复
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from ncatbot.testing import PluginTestHarness
from ncatbot.testing.factories.qq import private_message


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
