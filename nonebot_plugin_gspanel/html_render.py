import os
from base64 import b64encode
from io import BytesIO
from typing import Tuple

from nonebot import get_driver
from nonebot.log import logger
from PIL import Image
from utils.browser import get_browser

resPath = get_driver().config.gspanel_res
if not resPath:
    raise ValueError("请在环境变量中添加 gspanel_res 参数")


# 图片转换为 Base64 编码
async def img2Base64(pic: Image.Image) -> str:
    buf = BytesIO()
    pic.save(buf, format="PNG", quality=100)
    base64_str = b64encode(buf.getbuffer()).decode()
    return "base64://" + base64_str


# 生成角色名称、等级、命座、天赋等 HTML
def getTalentHTML(
    uid: str, name: str, lvl: int, cons: int, skills: dict
) -> Tuple[str, str]:
    talentItemTpl = """
    <div class="talent-item"><div class="talent-icon {} {}">
        <div class="talent-icon-img" style="background-image:url('{}')"></div>
        <span>{}</span>
    </div></div>"""
    talentItemHtml = ""
    for s in skills:
        sLvl = skills[s]
        plusCls = "talent-plus" if sLvl["current"] > sLvl["origin"] else ""
        crownCls = "talent-crown" if sLvl["origin"] == 10 else ""
        iconImg = f"./character/{name}/talent_{s}.png"
        talentItemHtml += talentItemTpl.format(
            plusCls, crownCls, iconImg, sLvl["current"]
        )
    talentHtml = f"""
    <div class="char-name">{name}</div>
    <div class="char-lv">
        UID {uid} - Lv.{lvl}
        <span class="cons cons-{cons}">{cons}命</span>
    </div>
    <div class="char-talents">{talentItemHtml}</div>"""
    consItemTpl = """
    <div class="cons-item"><div class="talent-icon {}">
        <img src="{}"/>
    </div></div>"""
    consItemHtml = ""
    for cnt in range(1, 7):
        offCls = "off" if cnt > cons else ""
        consImg = f"./character/{name}/cons_{cnt}.png"
        consItemHtml += consItemTpl.format(offCls, consImg)
    consHtml = f'<div class="char-cons">{consItemHtml}</div>'
    return talentHtml, consHtml


# 生成角色详细数据等 HTML
def getStatHtml(name: str, stats: dict) -> str:
    display = {
        "hp": "生命值",
        "atk": "攻击力",
        "def": "防御力",
        "cr": "暴击率",
        "cd": "暴击伤害",
        "em": "元素精通",
        "heal": "治疗加成",
        "er": "元素充能效率",
        "dmg": "元素伤害加成",
    } if name in [
        "班尼特", "珊瑚宫心海", "琴", "芭芭拉", "七七", "迪奥娜", "早柚", "久岐忍"
    ] else {
        "hp": "生命值",
        "atk": "攻击力",
        "def": "防御力",
        "cr": "暴击率",
        "cd": "暴击伤害",
        "em": "元素精通",
        "er": "元素充能效率",
        "dmg": "元素伤害加成",
    }
    if stats["phy"] > stats["dmg"]["value"]:
        display.pop("dmg")
        display["phy"] = "物理伤害加成"
    statItem = '<li><!--<i class="i-"></i>-->{}<strong>{}</strong>{}</li>'
    statList = []
    for item in display:
        if item in ["hp", "atk", "def"]:
            extra = stats[item] - stats[f"{item}Base"]
            span = f'<span><font>{stats[f"{item}Base"]}</font>+{extra}</span>'
        else:
            span = ""
        if item == "dmg":
            prop = stats["dmg"]["type"] + display[item]
            data = str(stats["dmg"]["value"]) + "%"
        else:
            prop = display[item]
            data = stats[item] if item not in [
                "cr", "cd", "er", "heal", "phy"
            ] else str(stats[item]) + "%"
        statList.append(statItem.format(prop, data, span))
    statHtml = '<ul class="attr">{}</ul>'.format("".join(statList))
    return statHtml


# 生成基础数据的 HTML，即最终图片的上半部分
def basicHTML(
    uid: str, char: str, level: int, cons: int, skill: dict, stat: dict
) -> str:
    splashImg = f"./character/{char}/gacha_splash.png"
    showHeal = "height: 532px;" if char in [
        "班尼特", "珊瑚宫心海", "琴", "芭芭拉", "七七", "迪奥娜", "早柚", "久岐忍"
    ] else ""
    talentHtml, consHtml = getTalentHTML(uid, char, level, cons, skill)
    statHtml = getStatHtml(char, stat)
    htmlString = f"""
    <div class="basic">
        <div
            class="main-pic"
            style="background-image:url('{splashImg}'); {showHeal}">
        </div>
        <div class="detail">
            {talentHtml}
            {statHtml}
        </div>
        {consHtml}
    </div>"""
    return htmlString


# 生成武器等 HTML
def getWeaponHtml(weapon: dict) -> str:
    tpl = f"""
    <img src="./weapon/{weapon["name"]}.png"/>
    <div class="head">
        <strong>{weapon["name"]}</strong>
        <div class="star star-{weapon["rank"]}"></div>
        <span>
        Lv.{weapon["level"]}
        <span class="affix affix-{weapon["affix"]}">精{weapon["affix"]}</span>
        </span>
    </div>"""
    return tpl


# 生成圣遗物套装总评分等 HTML
def getScoreHtml(slevel: str, score: str) -> str:
    tpl = f"""
    <div>
        <strong class="mark-{slevel}">{slevel}</strong>
        <span>圣遗物评级</span>
    </div>
    <div><strong>{score}</strong><span>圣遗物总分</span></div>"""
    return tpl


# 生成单件圣遗物评分等 HTML
def getArtisHtml(artisData: dict, scores: dict) -> str:
    subAffix = []
    subTpl = (
        '<li class="{}"><span class="title">{}</span>'
        '<span class="val">+{}{}</span></li>'
    )
    for sub in artisData["sub"]:
        use = scores["use"][sub["prop"].replace("百分比", "")]
        useCls = "great" if use > 79.9 else ("useful" if use > 0 else "nouse")
        subPct = "" if sub["prop"] in ["元素精通", "生命值", "攻击力", "防御力"] else "%"
        subAffix.append(
            subTpl.format(
                useCls, sub["prop"].replace("百分比", ""), sub["value"], subPct
            )
        )
    subHtml = "".join(subAffix)
    mainPropRaw = artisData["main"]["prop"]
    mainProp = mainPropRaw.replace("百分比", "").replace("元素伤害", "伤")
    mainPct = "%" if artisData["pos"] >= 3 and mainProp != "元素精通" else ""
    artiScore = scores["pos"][str(artisData["pos"])]
    itemTpl = f"""
    <div class="item arti">
    <div class="arti-icon">
        <img src="./reliquaries/{artisData["name"]}.png"/>
        <span>+{artisData["level"]}</span>
    </div>
    <div class="head">
        <strong>{artisData["name"]}</strong>
        <span class="mark mark-{artiScore["level"]}">
            <span>{artiScore["score"]}分</span> - {artiScore["level"]}
        </span>
    </div>
    <ul class="detail">
        <li class="arti-main">
            <span class="title">
                {mainProp}
            </span>
            <span class="val">+{artisData["main"]["value"]}{mainPct}</span>
        </li>
        {subHtml}
    </ul>
    </div>"""
    logger.info(artisData["main"]["prop"])
    return itemTpl


# 生成装备数据的 HTML，即最终图片的下半部分
def equipHtml(
    weapon: dict, artifacts: list, scores: dict
) -> str:
    wHtml = getWeaponHtml(weapon)
    sHtml = getScoreHtml(scores["level"], scores["score"])
    aHtml = [
        getArtisHtml(artifact, scores)
        for artifact in artifacts
    ]
    htmlString = f"""<div class="artis">
    <div>
        <div class="item weapon">{wHtml}</div>
        <div class="item stat">{sHtml}</div>
    </div>
    {"".join(aHtml)}
    </div>"""
    return htmlString


# 生成角色卡片整体 HTML
async def getFullImage(uid: str, avatarInfo: dict, scores: dict) -> str:
    name, elem, level, cons, skill, stat, weapon, artifacts = (
        avatarInfo["name"], avatarInfo["elem"], avatarInfo["level"],
        avatarInfo["cons"], avatarInfo["skill"], avatarInfo["stat"],
        avatarInfo["weapon"], avatarInfo["artifacts"]
    )
    bodyCls = f'elem-{elem} profile-mode char-{name}'
    basicHtmlStr = basicHTML(uid, name, level, cons, skill, stat)
    equipHtmlStr = equipHtml(weapon, artifacts, scores)
    with open(f"{resPath}html/tpl.html", encoding="utf-8") as f:
        template = str(f.read())
    template = template.replace("{{bodyCls}}", bodyCls)
    template = template.replace("{{basic}}", basicHtmlStr)
    template = template.replace("{{equip}}", equipHtmlStr)
    tmpFile = f"{resPath}html/{uid}-{name}.html"
    with open(tmpFile, "w", encoding="utf-8") as f:
        f.write(template)
    # 运行 Playwright 截图
    browser = await get_browser()
    if not browser:
        return "无法生成图片！"
    try:
        page = await browser.new_page(
            # device_scale_factor=1,
            viewport={"width": 960, "height": 1500}
        )
        await page.goto("file://" + tmpFile)
        card = await page.query_selector("body")
        assert card is not None
        picBytes = await card.screenshot()
        # 不知道为什么偶尔底部有白边，所以再裁剪一下
        picImage = Image.open(BytesIO(picBytes))
        logger.info(f"截取图片 ({picImage.size[0]}×{picImage.size[1]})")
        picImage = picImage.crop(
            (0, 0, picImage.size[0], picImage.size[1] - 3)
        )
        res = await img2Base64(picImage)
        await page.close()
    except Exception as e:
        logger.error(f"生成角色圣遗物评分图片失败 {type(e)}：{e}")
        res = "生成角色圣遗物评分总图失败！"
    try:
        os.remove(tmpFile)
    except Exception:
        pass
    return res
