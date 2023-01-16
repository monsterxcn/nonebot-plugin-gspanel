from nonebot import get_driver
from nonebot.log import logger
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.message import MessageSegment

from .data_updater import updateCache
from .data_source import getTeam, getPanel
from .__utils__ import GSPANEL_ALIAS, uidHelper, formatTeam, formatInput, fetchInitRes

driver = get_driver()
driver.on_startup(fetchInitRes)
driver.on_bot_connect(updateCache)

showPanel = on_command("panel", aliases=GSPANEL_ALIAS, priority=13, block=True)
showTeam = on_command("teamdmg", aliases={"队伍伤害"}, priority=13, block=True)

uidStart = ["1", "2", "5", "6", "7", "8", "9"]


@showPanel.handle()
async def giveMePower(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    qq = str(event.get_user_id())
    argsMsg = " ".join(seg.data["text"] for seg in arg["text"])
    # 提取消息中的 at 作为操作目标 QQ
    opqq = event.message["at"][0].data["qq"] if event.message.get("at") else ""
    # 输入以「绑定」开头，识别为绑定操作
    if argsMsg.startswith("绑定"):
        args = [a for a in argsMsg[2:].split() if a.isdigit()]
        if len(args) == 1:
            uid, opqq = args[0], opqq or qq
        elif len(args) == 2:
            uid, opqq = args[0], (opqq or args[1])
        else:
            await showPanel.finish("绑定参数格式错误！", at_sender=True)
        if opqq != qq and qq not in bot.config.superusers:
            await showPanel.finish(f"没有权限操作 QQ{qq} 的绑定状态！", at_sender=True)
        elif uid[0] not in uidStart or len(uid) != 9:
            await showPanel.finish(f"UID 是「{uid}」吗？好像不对劲呢..", at_sender=True)
        await showPanel.finish(await uidHelper(opqq, uid))
    # 尝试从输入中理解 UID、角色名
    uid, char = await formatInput(argsMsg, qq, opqq)
    if not uid:
        await showTeam.finish("要查询角色面板的 UID 捏？", at_sender=True)
    elif not uid.isdigit() or uid[0] not in uidStart or len(uid) != 9:
        await showPanel.finish(f"UID 是「{uid}」吗？好像不对劲呢..", at_sender=True)
    logger.info(f"正在查找 UID{uid} 的「{char}」角色面板..")
    rt = await getPanel(uid, char)
    if isinstance(rt, str):
        await showPanel.finish(MessageSegment.text(rt))
    elif isinstance(rt, bytes):
        await showPanel.finish(MessageSegment.image(rt))


@showTeam.handle()
async def x_x(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    qq = str(event.get_user_id())
    argsMsg = " ".join(seg.data["text"] for seg in arg["text"])
    # 提取消息中的 at 作为操作目标 QQ
    opqq = event.message["at"][0].data["qq"] if event.message.get("at") else ""
    # 尝试从输入中理解 UID、角色名
    uid, chars = await formatTeam(argsMsg, qq, opqq)
    if not uid:
        await showTeam.finish("要查询队伍伤害的 UID 捏？", at_sender=True)
    elif not uid.isdigit() or uid[0] not in uidStart or len(uid) != 9:
        await showPanel.finish(f"UID 是「{uid}」吗？好像不对劲呢..", at_sender=True)
    if not chars:
        logger.info(f"QQ{qq} 的输入「{argsMsg}」似乎未指定队伍角色！")
    logger.info(f"正在查找 UID{uid} 的「{'/'.join(chars) or '展柜前 4 角色'}」队伍伤害面板..")
    rt = await getTeam(uid, chars)
    if isinstance(rt, str):
        await showTeam.finish(MessageSegment.text(rt))
    elif isinstance(rt, bytes):
        await showTeam.finish(MessageSegment.image(rt))
