import asyncio
import json
from time import time
from traceback import format_exc
from typing import Dict, List, Literal, Tuple, Union

from httpx import AsyncClient, HTTPError, NetworkError
from nonebot.log import logger
from nonebot_plugin_htmlrender import template_to_pic

from .__utils__ import (
    DMG,
    ELEM,
    EXPIRE_SEC,
    GROW_VALUE,
    LOCAL_DIR,
    MAIN_AFFIXS,
    POS,
    POSCN,
    PROP,
    RANK_MAP,
    SKILL,
    SUB_AFFIXS,
    download,
    kStr,
    vStr,
)


async def getRawData(
    uid: str,
    charId: str = "000",
    refresh: bool = False,
    characters: Dict = {},
    source: Literal["enka", "mgg"] = "enka",
) -> Dict:
    """
    Enka.Network API 原神游戏内角色展柜原始数据获取

    * ``param uid: str`` 指定查询用户 UID
    * ``param charId: str = "000"`` 指定查询角色 ID
    * ``param refresh: bool = False`` 指定是否强制刷新数据
    * ``param characters: Dict = {}`` 角色 ID 与中文名转换所需资源
    * ``param source: Literal["enka", "mgg"] = "enka"`` 指定查询接口
    - ``return: Dict`` 查询结果。出错时返回 ``{"error": "错误信息"}``
    """
    cache = LOCAL_DIR / "cache" / f"{uid}__data.json"
    # 缓存文件存在且未过期、未要求刷新、查询角色存在于缓存中，三个条件均满足时才返回缓存
    if cache.exists() and (not refresh):
        logger.debug(f"检查 UID{uid} 角色 ID 为 {charId} 的缓存..")
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
                    characters.get(str(x["avatarId"]), {}).get("NameCN", "未知角色")
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
                    "User-Agent": (
                        "Mozilla/5.0 (Linux; Android 12; Nexus 5) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/102.0.0.0 Mobile Safari/537.36"
                    ),
                },
                timeout=20.0,
            )
            resJson = res.json()
            resJson["time"] = int(time())
            if not resJson.get("playerInfo"):
                raise HTTPError("返回信息不全")
            if not resJson["playerInfo"].get("showAvatarInfoList"):
                return {"error": f"UID{uid} 的角色展柜内还没有角色哦！"}
            if not resJson.get("avatarInfoList"):
                return {"error": f"UID{uid} 的角色展柜详细数据已隐藏！"}
            (LOCAL_DIR / "cache" / f"{uid}__data.json").write_text(
                json.dumps(resJson, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            # 返回 Enka.Network API 查询结果
            if charId == "000":
                return {
                    "list": [
                        characters.get(str(x["avatarId"]), {}).get("NameCN", "未知角色")
                        for x in resJson["playerInfo"]["showAvatarInfoList"]
                        if x["avatarId"] not in [10000005, 10000007]
                    ]
                }
            elif charId in [str(x["avatarId"]) for x in resJson["avatarInfoList"]]:
                return [
                    x for x in resJson["avatarInfoList"] if str(x["avatarId"]) == charId
                ][0]
            else:
                return {"error": f"UID{uid} 的最新数据中未发现该角色！"}
        except (HTTPError or json.decoder.JSONDecodeError):
            return {"error": "暂时无法访问面板数据接口.."}
        except Exception as e:
            # 出错时返回 {"error": "错误信息"}
            logger.error(f"请求 Enka.Network 出错 {type(e)}：{e}")
            return {"error": f"[{e.__class__.__name__}]面板数据处理出错辣.."}


async def getTeyvatData(body: Dict) -> Dict:
    """
    提瓦特小助手伤害计算接口请求。

    * ``param body: Dict`` 指定查询角色数据
    - ``return: Dict`` 查询结果。出错时返回 ``{}``
    """
    async with AsyncClient() as client:
        try:
            res = await client.post(
                "https://api.lelaer.com/ys/getDamageResult.php",
                json=body,
                headers={
                    "referer": "https://servicewechat.com/",
                    "user-agent": (
                        "Mozilla/5.0 (Linux; Android 12; SM-G977N Build/SP1A.210812.016; wv) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/86.0.4240.99 "
                        "XWEB/4317 MMWEBSDK/20220709 Mobile Safari/537.36 MMWEBID/4357 "
                        "MicroMessenger/8.0.25.2200(0x28001955) WeChat/arm64 Weixin NetType/WIFI "
                        "Language/zh_CN ABI/arm64 MiniProgramEnv/android"
                    ),
                },
            )
            return res.json()
        except (NetworkError, json.JSONDecodeError):
            logger.error(f"提瓦特小助手接口无法访问或返回错误\n{format_exc()}")
            return {}
        except Exception:
            logger.error(f"提瓦特小助手接口错误\n{format_exc()}")
            return {}


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


async def getPanelMsg(
    uid: str, char: str = "all", refresh: bool = False
) -> Union[bytes, str]:
    """
    原神游戏内角色展柜消息生成，针对原始数据进行文本翻译和结构重排。

    * ``param uid: str`` 指定查询用户 UID
    * ``param char: str = "all"`` 指定查询角色
    * ``param refresh: bool = False`` 指定是否强制刷新数据
    - ``return: Dict`` 查询结果。出错时返回 ``{"error": "错误信息"}``
    """
    # 获取查询角色 ID
    characters: Dict = json.loads(
        (LOCAL_DIR / "characters.json").read_text(encoding="utf-8")
    )
    charId = (
        "000"
        if char == "all"
        else {characters[cId]["NameCN"]: cId for cId in characters}.get(char, "notdigit")
    )
    if not charId.isdigit():
        return f"「{char}」是哪个角色？"
    # 获取面板数据
    raw = await getRawData(uid, charId=charId, refresh=refresh, characters=characters)
    if raw.get("error"):
        return raw["error"]
    if char == "all":
        return f"成功获取了 UID{uid} 的{'、'.join(raw['list'])}等 {len(raw['list'])} 位角色数据！"

    charData = characters[str(raw["avatarId"])]
    propData, equipData = raw["fightPropMap"], raw["equipList"]
    trans: Dict = json.loads((LOCAL_DIR / "trans.json").read_text(encoding="utf-8"))
    base = {"生命值": propData["1"], "攻击力": propData["4"], "防御力": propData["7"]}
    affixWeight, pointMark, maxMark = await getAffixCfg(char, base)

    # 下载任务
    charImgName = (  # 角色大图
        charData["Costumes"][str(raw["costumeId"])]["art"]
        if raw.get("costumeId")
        else charData["SideIconName"].replace("UI_AvatarIcon_Side", "UI_Gacha_AvatarImg")
    )
    dlTasks = [download(charImgName, local=LOCAL_DIR / char / f"{charImgName}.png")]

    # 伤害计算请求数据
    teyvatBody = {
        "uid": uid,
        "role_data": [
            {
                "uid": uid,
                "role": char,
                "role_class": len(raw.get("talentIdList", [])),
                "level": raw["propMap"]["4001"]["val"],
                "weapon": "",
                "weapon_level": 1,
                "weapon_class": "精炼1阶",
                "hp": int(propData["2000"]),
                "base_hp": int(propData["1"]),
                # "attack": int(propData["2001"]),
                "attack": int(
                    propData["4"] * (1 + propData.get("6", 0)) + propData.get("5", 0)
                ),
                "base_attack": int(propData["4"]),
                "defend": int(propData["2002"]),
                "base_defend": int(propData["7"]),
                "element": round(propData["28"]),
                "crit": f"{round(propData['20'] * 100, 1)}%",
                "crit_dmg": f"{round(propData['22'] * 100, 1)}%",
                "heal": f"{round(propData['26'] * 100, 1)}%",
                "recharge": f"{round(propData['23'] * 100, 1)}%",
                "fire_dmg": f"{round(propData['40'] * 100, 1)}%",
                "water_dmg": f"{round(propData['42'] * 100, 1)}%",
                "thunder_dmg": f"{round(propData['41'] * 100, 1)}%",
                "wind_dmg": f"{round(propData['44'] * 100, 1)}%",
                "ice_dmg": f"{round(propData['46'] * 100, 1)}%",
                "rock_dmg": f"{round(propData['45'] * 100, 1)}%",
                "grass_dmg": f"{round(propData['43'] * 100, 1)}%",
                "physical_dmg": f"{round(propData['30'] * 100, 1)}%",
                "artifacts": "",
                "ability1": 1,
                "ability2": 1,
                "ability3": 1,
                "artifacts_detail": [],
            }
        ],
    }
    # dataFix from https://github.com/yoimiya-kokomi/miao-plugin/blob/ac27075276154ef5a87a458697f6e5492bd323bd/components/profile-data/enka-data.js#L186
    if char == "雷电将军":
        teyvatBody["role_data"][0]["thunder_dmg"] = "{}%".format(
            round(
                max(
                    0,
                    float(teyvatBody["role_data"][0]["thunder_dmg"].replace("%", ""))
                    - (
                        float(teyvatBody["role_data"][0]["recharge"].replace("%", ""))
                        - 100
                    )
                    * 0.4,
                ),
                1,
            )
        )
    elif char == "莫娜":
        teyvatBody["role_data"][0]["water_dmg"] = "{}%".format(
            round(
                max(
                    0,
                    float(teyvatBody["role_data"][0]["water_dmg"].replace("%", ""))
                    - float(teyvatBody["role_data"][0]["recharge"].replace("%", ""))
                    * 0.2,
                ),
                1,
            )
        )

    # 技能数据
    tplSkills = {"a": {}, "e": {}, "q": {}}
    extraLevels = {k[-1]: v for k, v in raw.get("proudSkillExtraLevelMap", {}).items()}
    for idx, skillId in enumerate(charData["SkillOrder"]):
        # 实际技能等级、显示技能等级
        level = raw["skillLevelMap"][str(skillId)]
        currentLvl = level + extraLevels.get(list(SKILL)[idx], 0)
        skillImgName = charData["Skills"][str(skillId)]
        dlTasks.append(
            download(skillImgName, local=LOCAL_DIR / char / f"{skillImgName}.png")
        )
        # 模板渲染所需数据
        tplSkills[list(SKILL.values())[idx]] = {
            "plus": "talent-plus" if currentLvl > level else "",
            "img": f"./{char}/{skillImgName}.png",
            "lvl": currentLvl,
        }
        teyvatBody["role_data"][0][f"ability{idx + 1}"] = currentLvl

    # 面板数据
    # 显示物理伤害加成或元素伤害加成中数值最高者
    phyDmg = round(propData["30"] * 100, 1)
    elemDmg = sorted(
        [{"type": DMG[d], "value": round(propData[d] * 100, 1)} for d in DMG],
        key=lambda x: (x["value"], x["type"] == ELEM[charData["Element"]]),
        reverse=True,
    )[0]
    if phyDmg > elemDmg["value"]:
        dmgType, dmgValue = "物理伤害加成", phyDmg
    else:
        dmgType, dmgValue = f"{elemDmg['type']}元素伤害加成", elemDmg["value"]
    # 模板渲染所需数据
    tplProps = [
        {
            "name": "生命值",
            "weight": affixWeight.get("生命值百分比", 0),
            "value": round(propData["2000"]),
            "base": round(propData["1"]),
            "extra": round(propData["2000"] - propData["1"]),
        },
        {
            "name": "攻击力",
            "weight": affixWeight.get("攻击力百分比", 0),
            "value": round(propData["2001"]),
            "base": round(propData["1"]),
            "extra": round(propData["2001"] - propData["4"]),
        },
        {
            "name": "防御力",
            "weight": affixWeight.get("防御力百分比", 0),
            "value": round(propData["2002"]),
            "base": round(propData["7"]),
            "extra": round(propData["2002"] - propData["7"]),
        },
        {
            "name": "暴击率",
            "weight": affixWeight.get("暴击率", 0),
            "value": f'{round(propData["20"] * 100, 1)}%',
        },
        {
            "name": "暴击伤害",
            "weight": affixWeight.get("暴击伤害", 0),
            "value": f'{round(propData["22"] * 100, 1)}%',
        },
        {
            "name": "元素精通",
            "weight": affixWeight.get("元素精通", 0),
            "value": round(propData["28"]),
        },
        {
            "name": "治疗加成",
            "weight": affixWeight.get("治疗加成", 0),
            "value": f'{round(propData["26"] * 100, 1)}%',
        },
        {
            "name": "元素充能效率",
            "weight": affixWeight.get("元素充能效率", 0),
            "value": f'{round(propData["23"] * 100, 1)}%',
        },
        {
            "name": dmgType,
            "error": bool(dmgType[0] not in ["物", ELEM[charData["Element"]]]),
            "weight": affixWeight.get(dmgType[-6:], 0),
            "value": f"{dmgValue}%",
        },
    ]
    if tplProps[6]["value"] == "0%" and not tplProps[6]["weight"]:
        tplProps.pop(6)  # remove heal add

    # 命座数据
    consActivated, tplCons = teyvatBody["role_data"][0]["role_class"], []
    for cIdx, consImgName in enumerate(charData["Consts"]):
        tplCons.append(
            {
                "img": f"./{char}/{consImgName}.png",
                "state": "off" if cIdx + 1 > consActivated else "",
            }
        )
        dlTasks.append(
            download(charImgName, local=LOCAL_DIR / char / f"{consImgName}.png")
        )

    # 装备数据
    equipsMark, equipsCnt, tplWeapon, tplArtis, artiSet = 0.0, 0, {}, [], {}
    for equip in equipData:
        if equip["flat"]["itemType"] == "ITEM_WEAPON":
            # 图像下载及模板替换
            weaponImgName = equip["flat"]["icon"]
            weaponImg = LOCAL_DIR / "weapon" / f"{weaponImgName}.png"
            dlTasks.append(download(weaponImgName, local=weaponImg))
            # 模板渲染所需数据
            tplWeapon = {
                "name": trans.get(equip["flat"]["nameTextMapHash"], "缺少翻译"),
                "rarity": equip["flat"]["rankLevel"],
                "img": f"./weapon/{weaponImgName}.png",
                "affix": list(equip["weapon"].get("affixMap", {".": 0}).values())[0] + 1,
                "lvl": equip["weapon"]["level"],
            }
            teyvatBody["role_data"][0].update(
                {
                    "weapon": tplWeapon["name"],
                    "weapon_level": tplWeapon["lvl"],
                    "weapon_class": f"精炼{tplWeapon['affix']}阶",
                }
            )
            # dataFix from https://github.com/yoimiya-kokomi/miao-plugin/blob/ac27075276154ef5a87a458697f6e5492bd323bd/components/profile-data/enka-data.js#L186
            if tplWeapon["name"] in ["息灾", "波乱月白经津", "雾切之回光", "猎人之径"]:
                for dmg in [
                    "fire_dmg",
                    "water_dmg",
                    "thunder_dmg",
                    "wind_dmg",
                    "ice_dmg",
                    "rock_dmg",
                    "grass_dmg",
                ]:
                    teyvatBody["role_data"][0][dmg] = "{}%".format(
                        round(
                            max(
                                0,
                                float(teyvatBody["role_data"][0][dmg].replace("%", ""))
                                - 12
                                - 12 * (tplWeapon["affix"] - 1) / 4,
                            ),
                            1,
                        )
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
                [r[0] for r in RANK_MAP if calcTotal <= r[1]][0]
                if calcTotal <= 66
                else "E"
            )
            # 累积圣遗物套装评分和计数器
            equipsMark += calcTotal
            equipsCnt += 1
            # 图像下载及模板替换
            artiImgName = equip["flat"]["icon"]
            artiImg = LOCAL_DIR / "artifacts" / f"{artiImgName}.png"
            dlTasks.append(download(artiImgName, local=artiImg))
            # 面板渲染所需数据
            tplArtis.append(
                {
                    "index": posIdx,
                    "img": f"./artifacts/{artiImgName}.png",
                    "lvl": equip["reliquary"]["level"] - 1,
                    "name": trans.get(equip["flat"]["nameTextMapHash"], "缺少翻译"),
                    "calc_mark": round(calcTotal, 1),
                    "calc_rank": calcRankStr,
                    "calc_main": round(calcMainPct, 1),
                    "calc_total": round(calcTotalPct, 1),
                    "main_title": kStr(PROP[mainProp["mainPropId"]]),
                    "main_value": vStr(
                        PROP[mainProp["mainPropId"]], mainProp["statValue"]
                    ),
                    "main_mark": round(calcMain, 1) if calcMain else "-",
                    "main_style": "mark" if calcMain else "val",
                    "subs": [
                        {
                            "title": kStr(s[0]),
                            "value": vStr(s[0], s[1]),
                            "mark": round(s[2], 1),
                            "style": "great"
                            if affixWeight.get(
                                f"{s[0]}百分比" if s[0] in ["生命值", "攻击力", "防御力"] else s[0], 0
                            )
                            > 79.9
                            else ("useful" if s[2] else "nouse"),
                        }
                        for s in calcSubs
                    ],
                }
            )
            # 提瓦特请求数据
            artifacts = {
                "artifacts_name": trans.get(equip["flat"]["nameTextMapHash"], "缺少翻译"),
                "artifacts_type": POSCN[posIdx - 1],
                "level": equip["reliquary"]["level"] - 1,
                "maintips": PROP[mainProp["mainPropId"]].replace("百分比", ""),
                "mainvalue": vStr(PROP[mainProp["mainPropId"]], mainProp["statValue"]),
            }
            artifacts.update(
                {
                    f"tips{sIdx + 1}": f"{s[0].replace('百分比', '')}+{vStr(s[0], s[1])}"
                    for sIdx, s in enumerate(calcSubs)
                }
            )
            teyvatBody["role_data"][0]["artifacts_detail"].append(artifacts)
            artiSetName = trans.get(equip["flat"]["setNameTextMapHash"], "缺少翻译")
            artiSet[artiSetName] = artiSet.get(artiSetName, 0) + 1

    # 套装计算
    teyvatBody["role_data"][0]["artifacts"] = "+".join(
        f"{k}{v if v in [2, 4] else (2 if v == 3 else 4)}"
        for k, v in artiSet.items()
        if (v >= 2) or ("之人" in k)
    )

    # 下载所有图片
    await asyncio.gather(*dlTasks)
    dlTasks.clear()
    # 渲染截图
    tplDamage = await getTeyvatData(teyvatBody)
    htmlBase = str(LOCAL_DIR.resolve())
    return await template_to_pic(
        template_path=htmlBase,
        template_name="jinjia.html",
        templates={
            "uid": uid,
            "elem_type": f"elem_{ELEM[charData['Element']]}",
            "char_img": f"./{char}/{charImgName}.png",
            "char_name": char,
            "char_lvl": raw["propMap"]["4001"]["val"],
            "char_fet": raw["fetterInfo"]["expLevel"],
            "char_skills": tplSkills,
            "char_cons": tplCons,
            "char_props": tplProps,
            "total_mark_lvl": (
                [r[0] for r in RANK_MAP if equipsMark / equipsCnt <= r[1]][0]
                if equipsCnt and equipsMark <= 66 * equipsCnt
                else "E"
            ),
            "total_mark": str(round(equipsMark, 1)),
            "weapon": tplWeapon,
            "artis": tplArtis,
            "damage": tplDamage,
        },
        pages={
            "viewport": {"width": 600, "height": 300},
            "base_url": f"file://{htmlBase}",
        },
        wait=2,
    )
