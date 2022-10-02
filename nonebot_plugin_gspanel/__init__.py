from re import findall, sub
from typing import Tuple

from nonebot import get_driver
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot.log import logger
from nonebot.params import CommandArg
from nonebot.plugin import on_command

from .__utils__ import fetchInitRes, uidHelper
from .data_source import getPanelMsg

driver = get_driver()
uidStart = ["1", "2", "5", "6", "7", "8", "9"]
showPanel = on_command("panel", aliases={"评分", "面板"}, priority=13)


async def formatInput(msg: str, qq: str, atqq: str = "") -> Tuple[str, str]:
    """
    输入消息中的 UID 与角色名格式化，应具备处理 ``msg`` 为空、包含中文或数字的能力。
    - 首个中文字符串捕获为角色名，若不包含则返回 ``all`` 请求角色面板列表数据
    - 首个数字字符串捕获为 UID，若不包含则返回 ``uidHelper()`` 根据绑定配置查找的 UID

    * ``param msg: str`` 输入消息，由 ``state["_prefix"]["command_arg"]`` 或 ``event.get_plaintext()`` 生成，可能包含 CQ 码
    * ``param qq: str`` 输入消息触发 QQ
    * ``param atqq: str = ""`` 输入消息中首个 at 的 QQ
    - ``return: Tuple[str, str]``  UID、角色名
    """
    uid, char = "", ""
    group = findall(r"[0-9]+|[\u4e00-\u9fa5]+", sub(r"\[CQ:.*\]", "", msg))
    for s in group:
        if str(s).isdigit() and not uid:
            uid = str(s)
        elif not str(s).isdigit() and not char:
            char = str(s)
    uid = uid or await uidHelper(atqq or qq)
    char = char or "all"
    return uid, char


@driver.on_startup
async def exStartup() -> None:
    await fetchInitRes()


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
    rt = await getPanelMsg(uid, char)
    if rt.get("error") or rt.get("msg"):
        await showPanel.finish(rt.get("error") or rt.get("msg"))
    if rt.get("pic"):
        await showPanel.finish(MessageSegment.image(rt["pic"]))
