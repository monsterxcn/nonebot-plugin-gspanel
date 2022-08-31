import json
from base64 import b64encode

# from io import BytesIO
from time import time
from typing import Dict, List, Literal, Tuple

from httpx import AsyncClient, HTTPError
from nonebot.log import logger

from .__utils__ import (
    DMG,
    ELEM,
    EXPIRE_SEC,
    GROW_VALUE,
    LOCAL_DIR,
    MAIN_AFFIXS,
    POS,
    PROP,
    SKILL,
    SUB_AFFIXS,
    download,
    getBrowser,
    kStr,
    vStr,
)

# from PIL import Image
# from utils.browser import get_browser


async def getRawData(
    uid: str,
    charId: str = "000",
    refresh: bool = False,
    name2id: Dict = {},
    source: Literal["enka", "mgg"] = "enka",
) -> Dict:
    """
    Enka.Network API 原神游戏内角色展柜原始数据获取

    * ``param uid: str`` 指定查询用户 UID
    * ``param charId: str = "000"`` 指定查询角色 ID
    * ``param refresh: bool = False`` 指定是否强制刷新数据
    * ``param name2id: Dict = {}`` 角色 ID 与中文名转换所需资源
    * ``param source: Literal["enka", "mgg"] = "enka"`` 指定查询接口
    - ``return: Dict`` 查询结果。出错时返回 ``{"error": "错误信息"}``
    """
    cache = LOCAL_DIR / "cache" / f"{uid}__data.json"
    logger.debug(f"checking cache for {uid}'s {charId}")
    # 缓存文件存在且未过期、未要求刷新、查询角色存在于缓存中，三个条件均满足时才返回缓存
    if cache.exists() and (not refresh):
        cacheData = json.loads(cache.read_text(encoding="utf-8"))
        avalCharIds = [
            str(c["avatarId"]) for c in cacheData["playerInfo"]["showAvatarInfoList"]
        ]
        if int(time()) - cacheData["time"] > EXPIRE_SEC:
            pass
        elif charId in avalCharIds:
            return [
                c for c in cacheData["avatarInfoList"] if str(c["avatarId"]) == charId
            ][0]
        elif charId == "000":
            return {
                "list": [
                    [
                        nameCn
                        for nameCn, cId in name2id.items()
                        if cId == str(x["avatarId"])
                    ][0]
                    for x in cacheData["playerInfo"]["showAvatarInfoList"]
                    if x["avatarId"] not in [10000005, 10000007]
                ]
            }
    # 请求最新数据
    root = "https://enka.network" if source == "enka" else "https://enka.minigg.cn"
    async with AsyncClient() as client:
        try:
            res = await client.get(
                url=f"{root}/u/{uid}/__data.json",
                headers={
                    "Accept": "application/json",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
                    "Cache-Control": "no-cache",
                    "Cookie": "locale=zh-CN",
                    "Referer": "https://enka.network/",
                    "User-Agent": (  # "Miao-Plugin/3.0",
                        "Mozilla/5.0 (Linux; Android 12; Nexus 5) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/102.0.0.0 Mobile Safari/537.36"
                    ),
                },
                timeout=20.0,
            )
            resJson = res.json()
            resJson["time"] = int(time())
            assert list(resJson.keys()) != ["time"]
            (LOCAL_DIR / "cache" / f"{uid}__data.json").write_text(
                json.dumps(resJson, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            # 返回 Enka.Network API 查询结果
            if charId == "000":
                return {
                    "list": [
                        [
                            nameCn
                            for nameCn, cId in name2id.items()
                            if cId == str(x["avatarId"])
                        ][0]
                        for x in resJson["playerInfo"]["showAvatarInfoList"]
                        if x["avatarId"] not in [10000005, 10000007]
                    ]
                }
            elif [x for x in resJson["avatarInfoList"] if str(x["avatarId"]) == charId]:
                return [
                    x for x in resJson["avatarInfoList"] if str(x["avatarId"]) == charId
                ][0]
            else:
                return {"error": "最新数据中未发现该角色！"}
        except (AssertionError or HTTPError or json.decoder.JSONDecodeError):
            return {"error": "暂时无法访问面板数据接口.."}
        except Exception as e:
            # 出错时返回 {"error": "错误信息"}
            logger.error(f"请求 Enka.Network 出错 {type(e)}：{e}")
            return {"error": f"[{e.__class__.__name__}]面板数据处理出错辣.."}


async def getAffixCfg(char: str, base: Dict) -> Tuple[Dict, Dict, Dict]:
    """
    指定角色词条配置获取，包括词条评分权重、词条数值原始权重、各位置圣遗物总分理论最高分和主词条理论最高得分

    * ``param char: str`` 指定角色名
    * ``param base: Dict`` 指定角色的基础数值，可由 Enka 返回直接传入，格式为 ``{"生命值": 1, "攻击力": 1, "防御力": 1}``
    - ``return: Tuple[Dict, Dict, Dict]`` 词条评分权重、词条数值原始权重、各位置圣遗物最高得分
    """
    # 从 calc-rule.json 读取角色圣遗物词条评分权重（来自 @yoimiya-kokomi/miao-plugin）
    allCfg = json.loads((LOCAL_DIR / "calc-rule.json").read_text(encoding="utf-8"))
    assert isinstance(allCfg, Dict)
    affixWeight = allCfg.get(char, {"攻击力百分比": 75, "暴击率": 100, "暴击伤害": 100})
    affixWeight = dict(  # 排序影响最优主词条选择，通过特定排序使同等权重时非百分比的生命攻击防御词条优先级最低
        sorted(
            affixWeight.items(),
            key=lambda item: (
                item[1],
                "暴击" in item[0],
                "加成" in item[0],
                "元素" in item[0],
            ),
            reverse=True,
        )
    )
    # mixAffixWeight = affixWeight  # 用于副词条最高分计算

    # 计算词条数值原始权重（与词条数值的乘积在百位数级别，需后续处理为小数值）
    # 非百分比的生命攻击防御词条也按百分比词条的 affixWeight 权重计算
    pointMark = {k: v / GROW_VALUE[k] for k, v in affixWeight.items()}
    if pointMark.get("攻击力百分比"):
        pointMark["攻击力"] = pointMark["攻击力百分比"] / base.get("攻击力", 1020) * 100
        # mixAffixWeight["攻击力"] = affixWeight["攻击力百分比"]
    if pointMark.get("防御力百分比"):
        pointMark["防御力"] = pointMark["防御力百分比"] / base.get("防御力", 300) * 100
        # mixAffixWeight["防御力"] = affixWeight["防御力百分比"]
    if pointMark.get("生命值百分比"):
        pointMark["生命值"] = pointMark["生命值百分比"] / base.get("生命值", 400) * 100
        # mixAffixWeight["生命值"] = affixWeight["生命值百分比"]
    # 各位置圣遗物的总分理论最高分、主词条理论最高得分
    maxMark = {"1": {}, "2": {}, "3": {}, "4": {}, "5": {}}
    for posIdx in range(1, 5 + 1):
        if posIdx <= 2:
            # 花和羽不计算主词条得分
            mainAffix = "生命值" if posIdx == 1 else "攻击力"
            maxMark[str(posIdx)]["main"] = 0
            maxMark[str(posIdx)]["total"] = 0
        else:
            # 沙杯头计算该位置评分权重最高的词条得分
            avalMainAffix = {
                k: v for k, v in affixWeight.items() if k in MAIN_AFFIXS[str(posIdx)]
            }
            logger.debug(f"posIdx:{posIdx} mainAffix:\n{avalMainAffix}")
            mainAffix = list(avalMainAffix)[0]
            maxMark[str(posIdx)]["main"] = affixWeight[mainAffix]
            maxMark[str(posIdx)]["total"] = affixWeight[mainAffix] * 2
        # sorted([{"k": k, "v": v} for k, v in affixWeight.items() if k in SUB_AFFIXS and k != mainAffix and affixWeight.get(k)], key=lambda x:x["v"], reverse=True)

        maxSubAffixs = {
            # f"{k}{'百分比' if k in ['生命值', '攻击力', '防御力'] else ''}": v
            k: v
            for k, v in affixWeight.items()
            if k in SUB_AFFIXS and k != mainAffix and affixWeight.get(k)
        }
        logger.debug(f"posIdx:{posIdx} subAffix:\n{maxSubAffixs}")
        # 副词条中评分权重最高的词条得分大幅提升
        maxMark[str(posIdx)]["total"] += sum(
            affixWeight[k] * (1 if kIdx else 6)
            for kIdx, k in enumerate(list(maxSubAffixs)[0:4])
        )
    logger.debug(
        f"「{char}」角色词条配置：\naffixWeight:\n {affixWeight}\n"
        f"pointMark:\n {pointMark}\nmaxMark:\n {maxMark}"
    )
    return affixWeight, pointMark, maxMark


async def getPanelMsg(uid: str, char: str = "all", refresh: bool = False) -> Dict:
    """
    原神游戏内角色展柜消息生成，针对原始数据进行文本翻译和结构重排。

    * ``param uid: str`` 指定查询用户 UID
    * ``param char: str = "all"`` 指定查询角色
    * ``param refresh: bool = False`` 指定是否强制刷新数据
    - ``return: Dict`` 查询结果。出错时返回 ``{"error": "错误信息"}``
    """
    # 获取查询角色 ID
    name2id = json.loads((LOCAL_DIR / "name2id.json").read_text(encoding="utf-8"))
    charId = "000" if char == "all" else name2id.get(char, "阿巴")
    if not charId.isdigit():
        return {"error": f"「{char}」是哪个角色？"}
    # 获取面板数据
    raw = await getRawData(uid, charId=charId, refresh=refresh, name2id=name2id)
    if raw.get("error"):
        return raw
    if char == "all":
        return {"msg": f"成功获取{'、'.join(raw['list'])}等 {len(raw['list'])} 位角色数据！"}

    # 加载模板、翻译等资源
    tpl = (LOCAL_DIR / "tpl.html").read_text(encoding="utf-8")
    loc = json.loads((LOCAL_DIR / "TextMapCHS.json").read_text(encoding="utf-8"))
    characters = json.loads((LOCAL_DIR / "characters.json").read_text(encoding="utf-8"))
    propData, equipData = raw["fightPropMap"], raw["equipList"]
    # 加载角色数据（抽卡图片、命座、技能图标配置等）
    charData = characters[str(raw["avatarId"])]
    # 加载角色词条配置
    base = {"生命值": propData["1"], "攻击力": propData["4"], "防御力": propData["7"]}
    affixWeight, pointMark, maxMark = await getAffixCfg(char, base)

    # 准备好了吗，要开始了哦！

    # 元素背景
    tpl = tpl.replace("{{elem_type}}", f"elem_{ELEM[charData['Element']]}")

    # 角色大图
    charImgName = (
        charData["Costumes"][str(raw["costumeId"])]["art"]
        if raw.get("costumeId")
        else charData["SideIconName"].replace("UI_AvatarIcon_Side", "UI_Gacha_AvatarImg")
    )
    charImg = await download(f"https://enka.network/ui/{charImgName}.png", char)
    tpl = tpl.replace("{{char_img}}", str(charImg.resolve()) if charImg else "")

    # 角色信息
    tpl = tpl.replace(
        "<!--char_info-->",
        f"""
        <div class="char-name">{char}</div>
        <div class="char-lv">
            <span class="uid">UID {uid}</span>
            Lv.{raw["propMap"]["4001"]["val"]}
            <span class="fetter">&hearts; {raw["fetterInfo"]["expLevel"]}</span>
        </div>
        """,
    )

    # 命座数据
    consActivated, consHtml = len(raw.get("talentIdList", [])), []
    for cIdx, consImgName in enumerate(charData["Consts"]):
        # 图像下载及模板替换
        consImg = await download(f"https://enka.network/ui/{consImgName}.png", char)
        consHtml.append(
            f"""
            <div class="cons-item">
                <div class="talent-icon {"off" if cIdx + 1 > consActivated else ""}">
                    <div class="talent-icon-img" style="background-image:url({str(consImg.resolve()) if consImg else ""})"></div>
                </div>
            </div>
            """
        )
    tpl = tpl.replace("<!--cons_data-->", "".join(consHtml))

    # 技能数据
    extraLevels = {k[-1]: v for k, v in raw.get("proudSkillExtraLevelMap", {}).items()}
    for idx, skillId in enumerate(charData["SkillOrder"]):
        # 实际技能等级、显示技能等级
        level = raw["skillLevelMap"][str(skillId)]
        currentLvl = level + extraLevels.get(list(SKILL)[idx], 0)
        # 图像下载及模板替换
        skillImgName = charData["Skills"][str(skillId)]
        skillImg = await download(f"https://enka.network/ui/{skillImgName}.png", char)
        tpl = tpl.replace(
            f"<!--skill_{list(SKILL.values())[idx]}-->",
            f"""
            <div class="talent-icon {"talent-plus" if currentLvl > level else ""} {"talent-crown" if level == 10 else ""}">
                <div class="talent-icon-img" style="background-image:url({str(skillImg.resolve()) if skillImg else ""})"></div>
                <span>{currentLvl}</span>
            </div>
            """,
        )

    # 面板数据
    # 显示物理伤害加成或元素伤害加成中数值最高者
    phyDmg = round(propData["30"] * 100, 1)
    elemDmg = sorted(
        [{"type": DMG[d], "value": round(propData[d] * 100, 1)} for d in DMG],
        key=lambda x: x["value"],
        reverse=True,
    )[0]
    if phyDmg > elemDmg["value"]:
        dmgType, dmgValue = "物理伤害加成", phyDmg
    elif elemDmg["value"] == 0:
        dmgType, dmgValue = f"{ELEM[charData['Element']]}元素伤害加成", 0
    else:
        dmgType, dmgValue = f"{elemDmg['type']}元素伤害加成", elemDmg["value"]
    # 模板替换，奶妈角色额外显示治疗加成，元素伤害异常时评分权重显示提醒
    tpl = tpl.replace(
        "<!--fight_prop-->",
        f"""
        <li>生命值
            {("<code>" + str(affixWeight["生命值百分比"]) + "</code>") if affixWeight.get("生命值百分比") else ""}
            <strong>{round(propData["2000"])}</strong>
            <span><font>{round(propData["1"])}</font>+{round(propData["2000"] - propData["1"])}</span>
        </li>
        <li>攻击力
            {("<code>" + str(affixWeight["攻击力百分比"]) + "</code>") if affixWeight.get("攻击力百分比") else ""}
            <strong>{round(propData["2001"])}</strong>
            <span><font>{round(propData["4"])}</font>+{round(propData["2001"] - propData["4"])}</span>
        </li>
        <li>防御力
            {("<code>" + str(affixWeight["防御力百分比"]) + "</code>") if affixWeight.get("防御力百分比") else ""}
            <strong>{round(propData["2002"])}</strong>
            <span><font>{round(propData["7"])}</font>+{round(propData["2002"] - propData["7"])}</span>
        </li>
        <li>暴击率
            {("<code>" + str(affixWeight["暴击率"]) + "</code>") if affixWeight.get("暴击率") else ""}
            <strong>{round(propData["20"] * 100, 1)}%</strong>
        </li>
        <li>暴击伤害
            {("<code>" + str(affixWeight["暴击伤害"]) + "</code>") if affixWeight.get("暴击伤害") else ""}
            <strong>{round(propData["22"] * 100, 1)}%</strong>
        </li>
        <li>元素精通
            {("<code>" + str(affixWeight["元素精通"]) + "</code>") if affixWeight.get("元素精通") else ""}
            <strong>{round(propData["28"])}</strong>
        </li>
        {f'''<li>治疗加成
            {("<code>" + str(affixWeight["治疗加成"]) + "</code>")}
            <strong>{round(propData["26"] * 100, 1)}%</strong>
        </li>''' if affixWeight.get("治疗加成") else ""}
        <li>元素充能效率
            {("<code>" + str(affixWeight["元素充能效率"]) + "</code>") if affixWeight.get("元素充能效率") else ""}
            <strong>{round(propData["23"] * 100, 1)}%</strong>
        </li>
        <li>{dmgType}
            {
                (
                    "<code" +
                    (
                        ' style="background-color: rgba(240, 6, 6, 0.7)"'
                        if dmgType[0] not in ["物", ELEM[charData['Element']]]
                        else ""
                    ) + ">" + str(affixWeight[dmgType[-6:]]) + "</code>"
                )
                if affixWeight.get(dmgType[-6:])
                else ""
            }
            <strong>{dmgValue}%</strong>
        </li>
        """,
    )

    # 装备数据（圣遗物、武器）
    equipsMark, equipsCnt = 0.0, 0
    for equip in equipData:
        if equip["flat"]["itemType"] == "ITEM_WEAPON":
            # 武器精炼等级
            affixCnt = list(equip["weapon"].get("affixMap", {".": 0}).values())[0] + 1
            # 图像下载及模板替换
            weaponImgName = equip["flat"]["icon"]
            weaponImg = await download(
                f"https://enka.network/ui/{weaponImgName}.png", "weapon"
            )
            tpl = tpl.replace(
                "<!--weapon-->",
                f"""
                <img src="{str(weaponImg.resolve()) if weaponImg else ""}" />
                <div class="head">
                    <strong>{loc.get(equip["flat"]["nameTextMapHash"], "缺少翻译")}</strong>
                    <div class="star star-{equip["flat"]["rankLevel"]}"></div>
                    <span>Lv.{equip["weapon"]["level"]} <span class="affix affix-{affixCnt}">精{affixCnt}</span></span>
                </div>
                """,
            )
        elif equip["flat"]["itemType"] == "ITEM_RELIQUARY":
            mainProp = equip["flat"]["reliquaryMainstat"]  # type: Dict
            subProps = equip["flat"].get("reliquarySubstats", [])  # type: List
            posIdx = POS.index(equip["flat"]["equipType"]) + 1
            # 主词条得分（与副词条计算规则一致，但只取 25%），角色元素属性与伤害属性不同时不得分，不影响物理伤害得分
            calcMain = (
                0.0
                if posIdx < 3
                else pointMark.get(
                    PROP[mainProp["mainPropId"]].replace(ELEM[charData["Element"]], ""),
                    0,
                )
                * mainProp["statValue"]
                * 46.6
                / 6
                / 100
                / 4
            )
            # 副词条得分
            calcSubs = [
                # [词条名, 词条数值, 词条得分]
                [
                    PROP[s["appendPropId"]],
                    s["statValue"],
                    pointMark.get(PROP[s["appendPropId"]], 0)
                    * s["statValue"]
                    * 46.6
                    / 6
                    / 100,
                ]
                for s in subProps
            ]
            # 主词条收益系数（百分数），沙杯头位置主词条不正常时对圣遗物总分进行惩罚，最多扣除 50% 总分
            calcMainPct = (
                100
                if posIdx < 3
                else (
                    100
                    - 50
                    * (
                        1
                        - pointMark.get(
                            PROP[mainProp["mainPropId"]].replace(
                                ELEM[charData["Element"]], ""
                            ),
                            0,
                        )
                        * mainProp["statValue"]
                        / maxMark[str(posIdx)]["main"]
                        / 2
                        / 4
                    )
                )
            )
            # 总分对齐系数（百分数），按满分 66 对齐各位置圣遗物的总分
            calcTotalPct = 66 / (maxMark[str(posIdx)]["total"] * 46.6 / 6 / 100) * 100
            # 最终圣遗物总分
            calcTotal = (
                (calcMain + sum(s[2] for s in calcSubs))
                * calcMainPct
                / 100
                * calcTotalPct
                / 100
            )
            # 最终圣遗物评级
            calcRankStr = (
                [
                    r[0]
                    for r in [
                        ["D", 10],
                        ["C", 16.5],
                        ["B", 23.1],
                        ["A", 29.7],
                        ["S", 36.3],
                        ["SS", 42.9],
                        ["SSS", 49.5],
                        ["ACE", 56.1],
                        ["ACE²", 66],
                    ]
                    if calcTotal <= r[1]
                ][0]
                if calcTotal <= 66
                else "E"
            )
            # 累积圣遗物套装评分和计数器
            equipsMark += calcTotal
            equipsCnt += 1
            # 图像下载及模板替换
            artiImgName = equip["flat"]["icon"]
            artiImg = await download(
                f"https://enka.network/ui/{artiImgName}.png", "artifacts"
            )
            tpl = tpl.replace(
                f"<!--arti_{posIdx}-->",
                f"""
                <div class="arti-icon">
                    <img src="{str(artiImg.resolve()) if artiImg else ""}" />
                    <span>+{equip["reliquary"]["level"] - 1}</span>
                </div>
                <div class="head">
                    <strong>{loc.get(equip["flat"]["nameTextMapHash"], "缺少翻译")}</strong>
                    <span class="mark mark-{calcRankStr}"><span>{round(calcTotal, 1)}分</span> - {calcRankStr}</span>
                </div>
                <ul class="detail attr">
                    <li class="arti-main">
                        <span class="title">{kStr(PROP[mainProp["mainPropId"]])}</span>
                        <span class="val">+{vStr(PROP[mainProp["mainPropId"]], mainProp["statValue"])}</span>
                        <span class="{"mark" if calcMain else "val"}"> {round(calcMain, 1) if calcMain else "-"} </span>
                    </li>
                    {"".join(
                    '''<li class="{}"><span class="title">{}</span><span class="val">+{}</span>
                        <span class="mark">{}</span>
                    </li>'''.format(
                        "great" if affixWeight.get(f'{s[0]}百分比' if s[0] in ["生命值", "攻击力", "防御力"] else s[0], 0) > 79.9 else ("useful" if s[2] else "nouse"),
                        kStr(s[0]), vStr(s[0], s[1]), round(s[2], 1)
                    ) for s in calcSubs
                    )}
                </ul>
                <ul class="detail attr mark-calc">
                    {f'''
                    <li class="result">
                        <span class="title">主词条收益系数</span>
                        <span class="val">
                            * {round(calcMainPct, 1)}%
                        </span>
                    </li>''' if posIdx >= 3 else ""}
                    <li class="result">
                        <span class="title">总分对齐系数</span>
                        <span class="val">* {round(calcTotalPct, 1)}%</span>
                    </li>
                </ul>
                """,
            )

    # # 评分时间
    # tpl = tpl.replace("<!--time-->", f"@ {strftime('%m-%d %H:%M', localtime(raw['time']))}")
    # 圣遗物总分
    equipsMarkLevel = (
        [
            r[0]
            for r in [
                ["D", 10],
                ["C", 16.5],
                ["B", 23.1],
                ["A", 29.7],
                ["S", 36.3],
                ["SS", 42.9],
                ["SSS", 49.5],
                ["ACE", 56.1],
                ["ACE²", 66],
            ]
            if equipsMark / equipsCnt <= r[1]
        ][0]
        if equipsCnt and equipsMark <= 66 * equipsCnt
        else "E"
    )
    tpl = tpl.replace("{{total_mark_lvl}}", equipsMarkLevel)
    tpl = tpl.replace("{{total_mark}}", str(round(equipsMark, 1)))

    # 渲染截图
    tmpFile = LOCAL_DIR / f"{uid}-{char}.html"
    tmpFile.write_text(tpl, encoding="utf-8")
    logger.info("启动浏览器截图..")
    browser = await getBrowser()
    if not browser:
        return {"error": "无法生成图片！"}
    try:
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1000, "height": 1500})
        await page.goto("file://" + str(tmpFile.resolve()), timeout=5000)
        card = await page.query_selector("body")
        assert card is not None
        picBytes = await card.screenshot(timeout=5000)
        logger.info(f"图片大小 {len(picBytes)} 字节")
        # _ = Image.open(BytesIO(picBytes)).save(
        #     str(tmpFile.resolve()).replace(".html", ".png")
        # )
        await page.close()
        res = "base64://" + b64encode(picBytes).decode()
        tmpFile.unlink(missing_ok=True)
        return {"pic": res}
    except Exception as e:
        logger.error(f"生成角色圣遗物评分图片失败 {type(e)}：{e}")
        return {"error": "生成角色圣遗物评分总图失败！"}
