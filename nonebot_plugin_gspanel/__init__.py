from typing import List
try:
    from nonebot.adapters.cqhttp import Bot, MessageSegment
    from nonebot.adapters.cqhttp.event import MessageEvent
except ImportError:
    from nonebot.adapters.onebot.v11 import Bot
    from nonebot.adapters.onebot.v11.message import MessageSegment
    from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.exception import FinishedException
from nonebot.log import logger
from nonebot.plugin import on_command
from nonebot.typing import T_State

from .data_source import getFullJson, getUid, uidChecker
from .html_render import getFullImage
from .reliquary_mark import getAllScore

showScore = on_command("panel", aliases={"评分", "面板"}, priority=13)


# 从 get_plaintext() 提取末尾的一串数字作为 UID
def findUid(input: str) -> List[str]:
    # [CQ:at,qq=123456789]
    beforeCQ = input[:input.find("[")] if input.find("[") > 0 else ""
    afterCQ = input[input.find("]") + 1:] if input.find("]") < len(input) - 1 else ""  # noqa
    input = beforeCQ.strip() + afterCQ.strip()
    uid = ""
    for s in input[::-1]:
        tmp = s + uid
        if tmp.isdigit():
            uid = tmp
            continue
        else:
            break
    start = input[:-len(uid)] if len(uid) else input
    return [start.strip(), uid]


@showScore.handle()
async def _(bot: Bot, event: MessageEvent, state: T_State):
    input = [i for i in event.get_plaintext().split(" ") if i]
    qq, uid, char, force = event.get_user_id(), "", "", False
    for msgSeg in event.message:
        if msgSeg.type == "at":
            qq = msgSeg.data["qq"]
            break
    # 识别命令
    if len(input) == 0:
        uid = await getUid(qq)
        if not uid:
            await showScore.finish(
                "首次使用请发送「面板 UID」绑定 UID 与 QQ\n"
                "发送「面板 角色名」查询角色展柜中的角色数据~"
            )
    elif len(input) == 1:
        if "刷新" in input[0]:
            input[0], force = input[0].replace("刷新", ""), True
        if input[0].isdigit():
            uid = input[0]
        else:
            char, uid = findUid(input[0])
            if len(char) > 5:
                raise FinishedException
    elif len(input) == 2:
        if "刷新" in input:
            got = [i for i in input if i != "刷新"][0]
            if got.isdigit():
                uid = got
            else:
                char = got
        elif input[0].isdigit():
            char, uid = input[1], input[0]
        elif input[1].isdigit():
            char, uid = input[0], input[1]
        else:
            await showScore.finish(
                "命令格式不合法，你可能想输入「面板 角色 刷新」或「面板 角色 UID」？"
            )
    elif len(input) == 3:
        char, uid = input[0], input[1]
        force = True if "刷新" in input[2] else False
    else:
        raise FinishedException
    # 处理 UID
    if not uid:
        uid = await getUid(qq)
        if not uid:
            await showScore.finish("面板什么的，派蒙不知道呢 >.<")
    uid, server = uidChecker(uid)
    if not server:
        await showScore.finish("UID 格式不合法！")
    # 开始请求
    jsonData = await getFullJson(uid, force)
    if isinstance(jsonData, str):
        await showScore.finish(MessageSegment.text(jsonData))
    avalChar = [a["name"] for a in jsonData["avatarInfoList"]]
    # 结束未指定角色响应
    if not char and len(input) < 3:
        msg = (
            f"成功{'更新' if force else '获取'}了 {uid} 的"
            f"{'、'.join(avalChar)}等 {len(avalChar)} 位角色数据\n"
        )
        await getUid(qq, uid)
        await showScore.finish(
            MessageSegment.text(msg) + MessageSegment.at(qq) +
            MessageSegment.text("可以发送「面板 角色名」查询详情辣")
        )
    # 开始计算指定角色评分
    if char not in avalChar:
        await showScore.finish(
            f"角色「{char}」未在用户 {uid} 的游戏内展柜公开！"
        )
    avatarInfo = [
        x for x in jsonData["avatarInfoList"] if x["name"] == char
    ][0]
    scores = getAllScore(avatarInfo)
    logger.info(
        f'{len(scores["pos"])} 件圣遗物'
        f'总分：{scores["score"]}({scores["level"]})'
    )
    resImg = await getFullImage(uid, avatarInfo, scores)
    await showScore.finish(
        MessageSegment.image(resImg)
        if "base64" in resImg else
        MessageSegment.text(resImg)
    )
