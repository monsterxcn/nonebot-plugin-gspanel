from nonebot import get_driver
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.plugin import on_command

from .__utils__ import GSPANEL_ALIAS, fetchInitRes, formatInput, uidHelper
from .data_source import getPanel
from .data_updater import updateCache

driver = get_driver()
uidStart = ["1", "2", "5", "6", "7", "8", "9"]
showPanel = on_command("panel", aliases=GSPANEL_ALIAS, priority=13, block=True)

driver.on_startup(fetchInitRes)
driver.on_bot_connect(updateCache)


@showPanel.handle()
async def giveMePower(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    qq = str(event.get_user_id())
    argsMsg = str(arg)
    # 提取消息中的 at 作为操作目标 QQ
    opqq = event.message["at"][0].data["qq"] if event.message.get("at") else ""
    # 输入以「绑定」开头，识别为绑定操作
    if argsMsg.startswith("绑定"):
        args = [a.strip() for a in argsMsg[2:].split(" ") if a.strip().isdigit()]
        if len(args) == 1:
            uid, opqq = args[0], opqq or qq
        elif len(args) == 2:
            uid, opqq = args[0], (opqq or args[1])
        else:
            await showPanel.finish("面板绑定参数格式错误！")
        if opqq != qq and qq not in bot.config.superusers:
            await showPanel.finish(f"没有权限操作 QQ{qq} 的绑定状态！")
        elif uid[0] not in uidStart or len(uid) > 9:
            await showPanel.finish(f"UID 是「{uid}」吗？好像不对劲呢..")
        await showPanel.finish(await uidHelper(opqq, uid))
    # 尝试从输入中理解 UID、角色名
    uid, char = await formatInput(argsMsg, qq, opqq)
    logger.info(f"可能需要查找 UID{uid} 的「{char}」角色面板..")
    if not uid.isdigit() or uid[0] not in uidStart or len(uid) > 9:
        await showPanel.finish(f"UID 是「{uid}」吗？好像不对劲呢..")
    rt = await getPanel(uid, char)
    if isinstance(rt, str):
        await showPanel.finish(MessageSegment.text(rt))
    elif isinstance(rt, bytes):
        await showPanel.finish(MessageSegment.image(rt))
