"""Drive group helper plugin."""

from ncatbot.core import registrar
from ncatbot.event.qq import GroupMessageEvent, PrivateMessageEvent
from ncatbot.plugin import NcatBotPlugin

from utils.msg_parser import message_parser


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
            folder_id = await self.api.qq.file.get_or_create_group_folder(
                event.group_id,
                answer["upload_folder_name"],
            )
            await self.api.qq.file.upload_group_file(
                group_id=event.group_id,
                file=answer["file_path"],
                name=answer["file_name"],
                folder_id=folder_id,
            )
            await event.reply(text=answer["text"])
            return

        await event.reply(text=answer["text"])

    @registrar.qq.on_private_message()
    async def on_private_message(self, event: PrivateMessageEvent) -> None:
        self.logger.info("private msg: %s", event)
