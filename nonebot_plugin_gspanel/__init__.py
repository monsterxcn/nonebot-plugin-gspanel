from nonebot import get_driver
from nonebot.log import logger
from nonebot.adapters import Message
from nonebot.params import CommandArg
from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import Bot
from nonebot.adapters.onebot.v11.event import MessageEvent
from nonebot.adapters.onebot.v11.message import MessageSegment
from nonebot.plugin import PluginMetadata

from .data_updater import updateCache
from .data_source import getTeam, getPanel
from .__utils__ import GSPANEL_ALIAS, uidHelper, formatTeam, formatInput, fetchInitRes

driver = get_driver()
driver.on_startup(fetchInitRes)
driver.on_bot_connect(updateCache)

showPanel = on_command("panel", aliases=GSPANEL_ALIAS, priority=13, block=True)
showTeam = on_command("teamdmg", aliases={"队伍伤害"}, priority=13, block=True)

uidStart = ["1", "2", "5", "6", "7", "8", "9"]

sample=list(GSPANEL_ALIAS)[0]

__plugin_meta__ = PluginMetadata(
    name="GsPanel",
    description="展示原神游戏内角色展柜数据",
    usage=(
        "用于展示原神游戏内角色展柜数据的 NoneBot2 插件，支持队伍伤害计算。\n所有指令都可以用空格将关键词分割开来，如果你喜欢的话。\n队伍伤害为 实验性功能，计算结果可能存在问题。欢迎附带详细日志提交 issue 帮助改进此功能。\n项目地址：https://github.com/monsterxcn/nonebot-plugin-gspanel"
    ),
    extra={
        "menu_template": "default",
        "menu_data": [
            {
                "func": "绑定UID",
                "trigger_method": "指令",
                "trigger_condition": sample+'绑定123456789',
                "brief_des": "绑定原神UID",
                "detail_des": (
                    "绑定原神UID 100123456 至发送此指令的 QQ，QQ 已被绑定过则会更新绑定的 UID。\nBot 管理员可以通过在此指令后紧跟2334556789 或附带 @某人 的方式将 UID 100123456 绑定至指定的 QQ。指令示例：\n- <ft color=(238,120,0)>"+sample+"绑定100123456</ft>\n- <ft color=(238,120,0)>"+sample+"绑定100123456 @某人</ft>\n- <ft color=(238,120,0)>"+sample+"绑定2334556789 100123456</ft>"
                ),
            },
            {
                "func": "全部角色面板",
                "trigger_method": "指令",
                "trigger_condition": sample,
                "brief_des": "展示角色展柜中所有角色",
                "detail_des": (
                    "查找 QQ 绑定的 UID / UID 100123456 角色展柜中展示的所有角色（图片）。\n指令示例：\n- <ft color=(238,120,0)>"+sample+"</ft>\n- <ft color=(238,120,0)>"+sample+"@某人</ft>\n- <ft color=(238,120,0)>"+sample+"100123456</ft>"
                ),
            },
            {
                "func": "单个角色面板",
                "trigger_method": "指令",
                "trigger_condition": sample+"夜兰",
                "brief_des": "展示指定角色面板",
                "detail_des": (
                    "查找 QQ 绑定的 UID / UID 100123456 的夜兰面板（图片）。\n指令示例：\n- <ft color=(238,120,0)>"+sample+"夜兰</ft>\n- <ft color=(238,120,0)>"+sample+"夜兰@某人</ft>\n- <ft color=(238,120,0)>"+sample+"夜兰100123456</ft>\n- <ft color=(238,120,0)>"+sample+"100123456夜兰</ft>"
                ),
            },
            {
                "func": "队伍伤害(前四人)",
                "trigger_method": "指令",
                "trigger_condition": "队伍伤害",
                "brief_des": "展柜第一排角色组成的队伍伤害。",
                "detail_des": (
                    "查找指定 UID 角色展柜中前四个角色组成的队伍伤害。\n当仅发送 队伍伤害 时将尝试使用发送此指令的 QQ 绑定的 UID；附带 9 位数字时尝试使用该 UID；附带 @某人 时将尝试使用指定 QQ 绑定的 UID。\n指令示例：\n- <ft color=(238,120,0)>队伍伤害</ft>\n- <ft color=(238,120,0)>队伍伤害100123456</ft>\n- <ft color=(238,120,0)>队伍伤害@某人</ft>"
                ),
            },
            {
                "func": "队伍伤害(详情)",
                "trigger_method": "指令",
                "trigger_condition": "队伍伤害详情",
                "brief_des": "带伤害过程的队伍伤害图",
                "detail_des": (
                    "显示伤害过程表格，查看具体伤害过程。\n指令示例：\n- <ft color=(238,120,0)>队伍伤害详情</ft>\n- <ft color=(238,120,0)>队伍伤害过程</ft>\n- <ft color=(238,120,0)>队伍伤害全图</ft>"
                ),
            },
            {
                "func": "队伍伤害(指定队伍)",
                "trigger_method": "指令",
                "trigger_condition": "队伍伤害雷九万班",
                "brief_des": "计算指定队伍的队伍伤害",
                "detail_des": (
                    "查找雷电将军、九条裟罗、枫原万叶、班尼特组成的队伍伤害。注意角色名之间必须使用空格分开。含有 旅行者 的配队暂时无法查询。队伍角色只要使用 面板 指令查询过或者正在展柜中摆放即可配队（即所有查询过的角色都有缓存，使用 面板 指令查看所有可用的角色）。\n为此形式的命令指定 UID 方式与上面相同。\n指令示例：\n- <ft color=(238,120,0)>队伍伤害雷九万班</ft>\n- <ft color=(238,120,0)>队伍伤害 雷神 九条 万叶 班尼特</ft>\n- <ft color=(238,120,0)>队伍伤害雷神 九条 万叶 班尼特@某人</ft>"
                ),
            },
        ],
    },
)


@showPanel.handle()
async def panel_handle(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
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
        await showPanel.finish("要查询角色面板的 UID 捏？", at_sender=True)
    elif not uid.isdigit() or uid[0] not in uidStart or len(uid) != 9:
        await showPanel.finish(f"UID 是「{uid}」吗？好像不对劲呢..", at_sender=True)
    logger.info(f"正在查找 UID{uid} 的「{char}」角色面板..")
    rt = await getPanel(uid, char)
    if isinstance(rt, str):
        await showPanel.finish(MessageSegment.text(rt))
    elif isinstance(rt, bytes):
        await showPanel.finish(MessageSegment.image(rt))


@showTeam.handle()
async def team_handle(bot: Bot, event: MessageEvent, arg: Message = CommandArg()):
    qq = str(event.get_user_id())
    argsMsg = " ".join(seg.data["text"] for seg in arg["text"])
    # 提取消息中的 at 作为操作目标 QQ
    opqq = event.message["at"][0].data["qq"] if event.message.get("at") else ""
    # 是否展示伤害过程，默认不显示
    showDetail, keywords = False, ["详情", "过程", "全部", "全图"]
    if any(argsMsg.startswith(word) for word in keywords):
        showDetail = True
        for word in keywords:
            argsMsg = argsMsg.lstrip(word).strip()
    # 尝试从输入中理解 UID、角色名
    uid, chars = await formatTeam(argsMsg, qq, opqq)
    if not uid:
        await showTeam.finish("要查询队伍伤害的 UID 捏？", at_sender=True)
    elif not uid.isdigit() or uid[0] not in uidStart or len(uid) != 9:
        await showTeam.finish(f"UID 是「{uid}」吗？好像不对劲呢..", at_sender=True)
    if not chars:
        logger.info(f"QQ{qq} 的输入「{argsMsg}」似乎未指定队伍角色！")
    logger.info(f"正在查找 UID{uid} 的「{'/'.join(chars) or '展柜前 4 角色'}」队伍伤害面板..")
    rt = await getTeam(uid, chars, showDetail)
    if isinstance(rt, str):
        await showTeam.finish(MessageSegment.text(rt))
    elif isinstance(rt, bytes):
        await showTeam.finish(MessageSegment.image(rt))
