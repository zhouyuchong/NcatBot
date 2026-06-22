"""Drive group helper plugin.

Author: zhouyuchong
Date: 2026-06-22 13:01:18
Description:
LastEditors: zhouyuchong
LastEditTime: 2026-06-22 13:47:25
"""

import sys
from pathlib import Path
from typing import Any

from ncatbot.core import registrar
from ncatbot.event.qq import GroupMessageEvent, PrivateMessageEvent
from ncatbot.plugin import NcatBotPlugin

PROJECT_DIR = Path(__file__).resolve().parents[2]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from utils.msg_parser import message_parser  # noqa: E402


def _answer_files(answer: dict[str, Any]) -> list[dict[str, str]]:
    if "files" in answer:
        return list(answer["files"])
    return [{"file_name": answer["file_name"], "file_path": answer["file_path"]}]


def _delete_uploaded_file(file_path: str, logger) -> None:
    try:
        Path(file_path).unlink(missing_ok=True)
        logger.debug("已删除上传后的文件: %s", file_path)
    except Exception as exc:
        logger.warning("删除上传后的文件失败: %s", exc)


class DriveBotPlugin(NcatBotPlugin):
    """Handle QQ group requests that mention the bot."""

    async def on_load(self) -> None:
        self._last_request_time = None
        self.logger.info("%s 已加载", self.name)

    async def on_close(self) -> None:
        self.logger.info("%s 已卸载", self.name)

    @registrar.qq.on_group_message()
    async def on_group_message(self, event: GroupMessageEvent) -> None:
        if not event.message.is_at(event.self_id):
            return

        self.logger.info(event)
        answer = await message_parser(
            msg=event.message.text,
            last_time=self._last_request_time,
            logger=self.logger,
        )
        self.logger.info(answer)
        self._last_request_time = answer["updated_time"]

        if answer["direct_upload"]:
            await event.reply(text=answer["text"], image=answer["file_path"])
            return

        if answer["upload_file"]:
            folder_id = await self.api.qq.file.get_or_create_group_folder(
                event.group_id,
                answer["upload_folder_name"],
            )
            for item in _answer_files(answer):
                await self.api.qq.file.upload_group_file(
                    group_id=event.group_id,
                    file=item["file_path"],
                    name=item["file_name"],
                    folder_id=folder_id,
                )
                _delete_uploaded_file(item["file_path"], self.logger)
            await event.reply(text=answer["text"])
            return

        await event.reply(text=answer["text"])

    @registrar.qq.on_private_message()
    async def on_private_message(self, event: PrivateMessageEvent) -> None:
        """
        Handle private messages sent to the bot.
        """
        """data format :
        private msg: PrivateMessageEvent(data=PrivateMessageEventData(time=1782106570, self_id='1706895031',
        post_type=<PostType.MESSAGE: 'message'>, platform='qq', message_type=<MessageType.PRIVATE: 'private'>,
        sub_type='friend', message_id='1147773616', user_id='1620404337', message=MessageArray([PlainText(text='在')]),
        raw_message='在', sender=QQSender(user_id='1620404337', nickname='DamonZzz', sex='unknown', age=0), font=14, message_seq=1147773616,
        real_id='1147773616', real_seq='70', message_format='array', target_id='1620404337'))
        """
        self.logger.info("private msg: %s", event)
        answer = await message_parser(
            msg=event.raw_message,
            last_time=self._last_request_time,
            logger=self.logger,
        )
        self.logger.info(answer)
        self._last_request_time = answer["updated_time"]

        if answer["direct_upload"]:
            await event.reply(text=answer["text"], image=answer["file_path"])
            return

        if answer["upload_file"]:
            for item in _answer_files(answer):
                await self.api.qq.file.upload_private_file(
                    user_id=event.user_id,
                    file=item["file_path"],
                    name=item["file_name"],
                )
                _delete_uploaded_file(item["file_path"], self.logger)
            await event.reply(text=answer["text"])
            return

        await event.reply(text=answer["text"])
