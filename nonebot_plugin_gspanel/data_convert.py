import json
from time import time
from typing import Dict, List, Tuple

from nonebot.log import logger

from .__utils__ import (
    POS,
    ELEM,
    PROP,
    SKILL,
    RANK_MAP,
    CHAR_DATA,
    CALC_RULES,
    GROW_VALUE,
    HASH_TRANS,
    SUB_AFFIXS,
    MAIN_AFFIXS,
    RELIC_APPEND,
    kStr,
    vStr,
    getServer,
)


async def getRelicConfig(char: str, base: Dict = {}) -> Tuple[Dict, Dict, Dict]:
    """
    指定角色圣遗物计算配置获取，包括词条评分权重、词条数值原始权重、各位置圣遗物总分理论最高分和主词条理论最高得分

    * ``param char: str`` 角色名
    * ``param base: Dict = {}`` 角色的基础数值，可由 Enka 返回获得，格式为 ``{"生命值": 1, "攻击力": 1, "防御力": 1}``
    - ``return: Tuple[Dict, Dict, Dict]`` 词条评分权重、词条数值原始权重、各位置圣遗物最高得分
    """  # noqa: E501
    affixWeight = CALC_RULES.get(char, {"攻击力百分比": 75, "暴击率": 100, "暴击伤害": 100})
    # 词条评分权重的 key 排序影响最优主词条选择
    # 通过特定排序使同等权重时生命攻击防御固定值词条优先级最低
    # key 的原始排序为 生命值攻击力防御力百分比、暴击率、暴击伤害、元素精通、元素伤害加成、物理伤害加成、元素充能效率
    # 注：已经忘了最初为什么这样写了，但总之就是顺序有影响+现在这样写能用
    affixWeight = dict(
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
    # 计算词条数值原始权重
    # 是一种与词条数值的乘积在百位数级别的东西，后续据此计算最终得分
    # 非百分比的生命攻击防御词条也按百分比词条的 affixWeight 权重计算
    pointMark = {k: v / GROW_VALUE[k] for k, v in affixWeight.items()}
    if pointMark.get("攻击力百分比"):
        pointMark["攻击力"] = pointMark["攻击力百分比"] / base.get("攻击力", 1020) * 100
    if pointMark.get("防御力百分比"):
        pointMark["防御力"] = pointMark["防御力百分比"] / base.get("防御力", 300) * 100
    if pointMark.get("生命值百分比"):
        pointMark["生命值"] = pointMark["生命值百分比"] / base.get("生命值", 400) * 100
    # 各位置圣遗物的总分理论最高分、主词条理论最高得分
    maxMark = {"1": {}, "2": {}, "3": {}, "4": {}, "5": {}}
    for posIdx in range(1, 6):
        # 主词条最高得分
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
            # logger.debug(
            #     "{} 的主词条推荐顺序为：\n{}".format(
            #         list(POS.values())[posIdx - 1],
            #         " / ".join(f"{k}[{v}]" for k, v in avalMainAffix.items()),
            #     )
            # )
            mainAffix = list(avalMainAffix)[0]
            maxMark[str(posIdx)]["main"] = affixWeight[mainAffix]
            maxMark[str(posIdx)]["total"] = affixWeight[mainAffix] * 2
        # 副词条最高得分
        maxSubAffixs = {
            k: v
            for k, v in affixWeight.items()
            if k in SUB_AFFIXS and k != mainAffix and affixWeight.get(k)
        }
        # logger.debug(
        #     "{} 的副词条推荐顺序为：\n{}".format(
        #         list(POS.values())[posIdx - 1],
        #         " / ".join(f"{k}[{v}]" for k, v in maxSubAffixs.items()),
        #     )
        # )
        # 副词条中评分权重最高的词条得分大幅提升
        maxMark[str(posIdx)]["total"] += sum(
            affixWeight[k] * (1 if kIdx else 6)
            for kIdx, k in enumerate(list(maxSubAffixs)[0:4])
        )
    logger.debug(
        (
            "「{}」圣遗物评分依据："
            "\n\t词条评分权重 affixWeight\n\t{}"
            "\n\t词条数值原始权重 pointMark\n\t{}"
            "\n\t各位置圣遗物最高得分 maxMark\n\t{}"
        ).format(
            char,
            " / ".join(f"{k}[{v}]" for k, v in affixWeight.items()),
            " / ".join(f"{k}[{v}]" for k, v in pointMark.items()),
            " / ".join(
                f"{list(POS.values())[int(k)-1]}>主词条[{v['main']}]总分[{v['total']}]"
                for k, v in maxMark.items()
            ),
        )
    )
    return affixWeight, pointMark, maxMark


def getRelicRank(score: float) -> str:
    """圣遗物评级获取"""
    # 在角色等级较低（基础数值较低）时评级可能显示为 "ERR"
    # 注：角色等级较低时不为 "ERR" 的评分也有可能出错
    return [r[0] for r in RANK_MAP if score <= r[1]][0] if score <= 66 else "ERR"


async def calcRelicMark(
    relicData: Dict, charElement: str, affixWeight: Dict, pointMark: Dict, maxMark: Dict
) -> Dict:
    """
    指定角色圣遗物评分计算

    * ``param relicData: Dict`` 圣遗物数据
    * ``param charElement: str`` 角色的中文元素属性
    * ``param affixWeight: Dict`` 角色的词条评分权重，由 ``getRelicConfig()`` 获取
    * ``param pointMark: Dict`` 角色的词条数值原始权重，由 ``getRelicConfig()`` 获取
    * ``param maxMark: Dict`` 角色的各位置圣遗物最高得分，由 ``getRelicConfig()`` 获取
    - ``return: Dict`` 圣遗物评分结果
    """
    posIdx, relicLevel = str(relicData["pos"]), relicData["level"]
    mainProp, subProps = relicData["main"], relicData["sub"]
    # 主词条得分、主词条收益系数（百分数）
    if posIdx in ["1", "2"]:
        calcMain, calcMainPct = 0.0, 100
    else:
        # 角色元素属性与伤害属性不同时权重为 0，不影响物理伤害得分
        _mainPointMark: float = pointMark.get(
            mainProp["prop"].replace(charElement, ""), 0
        )
        _point: float = _mainPointMark * mainProp["value"]
        # 主词条与副词条的得分计算规则一致，但只取 25%
        calcMain = _point * 46.6 / 6 / 100 / 4
        # 主词条收益系数用于沙杯头位置主词条不正常时的圣遗物总分惩罚，最多扣除 50% 总分
        _punishPct: float = _point / maxMark[posIdx]["main"] / 2 / 4
        calcMainPct = 100 - 50 * (1 - _punishPct)
    # 副词条得分
    calcSubs = []
    for s in subProps:
        _subPointMark: float = pointMark.get(s["prop"], 0)
        calcSub: float = _subPointMark * s["value"] * 46.6 / 6 / 100
        # 副词条 CSS 样式
        _awKey = f"{s['prop']}百分比" if s["prop"] in ["生命值", "攻击力", "防御力"] else s["prop"]
        _subAffixWeight: int = affixWeight.get(_awKey, 0)
        subStyleClass = (
            ("great" if _subAffixWeight > 79 else "use") if calcSub else "unuse"
        )
        # [词条名, 词条数值, 词条得分]
        calcSubs.append([subStyleClass, calcSub])
    # 总分对齐系数（百分数），按满分 66 对齐各位置圣遗物的总分
    calcTotalPct: float = 66 / (maxMark[posIdx]["total"] * 46.6 / 6 / 100) * 100
    # 最终圣遗物总分
    _total = calcMain + sum(s[1] for s in calcSubs)
    calcTotal = _total * calcMainPct * calcTotalPct / 10000
    # 强化歪次数
    realAppendPropIdList: List[int] = (
        relicData["_appendPropIdList"][-(relicLevel // 4) :]
        if (relicLevel // 4)
        else []
    )
    # logger.debug(
    #     "{} 强化记录：\n{}".format(
    #         list(POS.values())[int(posIdx) - 1],
    #         " / ".join(
    #             PROP.get(RELIC_APPEND[str(x)], RELIC_APPEND[str(x)])
    #             for x in realAppendPropIdList
    #         ),
    #     )
    # )
    notHit = len(
        [
            x
            for x in realAppendPropIdList
            if not pointMark.get(PROP.get(RELIC_APPEND[str(x)], RELIC_APPEND[str(x)]))
        ]
    )
    return {
        "rank": getRelicRank(calcTotal),
        "total": calcTotal,
        "nohit": notHit,
        "main": round(calcMain, 1),
        "sub": [
            {"style": subRes[0], "goal": round(subRes[1], 1)} for subRes in calcSubs
        ],
        "main_pct": round(calcMainPct, 1),
        "total_pct": round(calcTotalPct, 1),
    }


async def transFromEnka(avatarInfo: Dict, ts: int = 0) -> Dict:
    """
    转换 Enka.Network 角色查询数据为内部格式

    * ``param avatarInfo: Dict`` Enka.Network 角色查询数据，取自 ``data["avatarInfoList"]`` 列表
    * ``param ts: int = 0`` 数据时间戳
    - ``return: Dict`` 内部格式角色数据，用于本地缓存等
    """
    charData = CHAR_DATA[str(avatarInfo["avatarId"])]
    res = {
        "id": avatarInfo["avatarId"],
        "rarity": 5 if "QUALITY_ORANGE" in charData["QualityType"] else 4,
        "name": charData["NameCN"],
        "slogan": charData["Slogan"],
        "element": ELEM[charData["Element"]],  # 中文单字
        "cons": len(avatarInfo.get("talentIdList", [])),  # int
        "fetter": avatarInfo["fetterInfo"]["expLevel"],  # int
        "level": int(avatarInfo["propMap"]["4001"]["val"]),  # int
        "icon": charData["Costumes"][str(avatarInfo["costumeId"])]["icon"]
        if avatarInfo.get("costumeId")
        else charData["iconName"],
        "gachaAvatarImg": charData["Costumes"][str(avatarInfo["costumeId"])]["art"]
        if avatarInfo.get("costumeId")
        else charData["iconName"].replace("UI_AvatarIcon_", "UI_Gacha_AvatarImg_"),
        "baseProp": {  # float
            "生命值": avatarInfo["fightPropMap"]["1"],
            "攻击力": avatarInfo["fightPropMap"]["4"],
            "防御力": avatarInfo["fightPropMap"]["7"],
        },
        "fightProp": {  # float
            "生命值": avatarInfo["fightPropMap"]["2000"],
            # "攻击力": avatarInfo["fightPropMap"]["2001"],
            "攻击力": avatarInfo["fightPropMap"]["4"]
            * (1 + avatarInfo["fightPropMap"].get("6", 0))
            + avatarInfo["fightPropMap"].get("5", 0),
            "防御力": avatarInfo["fightPropMap"]["2002"],
            "暴击率": avatarInfo["fightPropMap"]["20"] * 100,
            "暴击伤害": avatarInfo["fightPropMap"]["22"] * 100,
            "治疗加成": avatarInfo["fightPropMap"]["26"] * 100,
            "元素精通": avatarInfo["fightPropMap"]["28"],
            "元素充能效率": avatarInfo["fightPropMap"]["23"] * 100,
            "物理伤害加成": avatarInfo["fightPropMap"]["30"] * 100,
            "火元素伤害加成": avatarInfo["fightPropMap"]["40"] * 100,
            "水元素伤害加成": avatarInfo["fightPropMap"]["42"] * 100,
            "风元素伤害加成": avatarInfo["fightPropMap"]["44"] * 100,
            "雷元素伤害加成": avatarInfo["fightPropMap"]["41"] * 100,
            "草元素伤害加成": avatarInfo["fightPropMap"]["43"] * 100,
            "冰元素伤害加成": avatarInfo["fightPropMap"]["46"] * 100,
            "岩元素伤害加成": avatarInfo["fightPropMap"]["45"] * 100,
        },
        "skills": {},
        "consts": [],
        "weapon": {},
        "relics": [],
        "relicSet": {},
        "relicCalc": {},
        "damage": {},  # 预留
        "time": ts or int(time()),
    }
    # 技能数据
    skills = {"a": {}, "e": {}, "q": {}}
    extraLevels = {
        k[-1]: v for k, v in avatarInfo.get("proudSkillExtraLevelMap", {}).items()
    }
    for idx, skillId in enumerate(charData["SkillOrder"]):
        # 实际技能等级、显示技能等级
        level = avatarInfo["skillLevelMap"][str(skillId)]
        currentLvl = level + extraLevels.get(list(SKILL)[idx], 0)
        skills[list(SKILL.values())[idx]] = {
            "style": "extra" if currentLvl > level else "",
            "icon": charData["Skills"][str(skillId)],
            "level": currentLvl,
            "originLvl": level,
        }
    res["skills"] = skills
    # 命座数据
    consts = []
    for cIdx, consImgName in enumerate(charData["Consts"]):
        consts.append(
            {
                "style": "off" if cIdx + 1 > res["cons"] else "",
                "icon": consImgName,
            }
        )
    res["consts"] = consts
    # 装备数据
    affixWeight, pointMark, maxMark = await getRelicConfig(
        charData["NameCN"], res["baseProp"]
    )
    relicsMark, relicsCnt, relicSet = 0.0, 0, {}
    for equip in avatarInfo["equipList"]:
        if equip["flat"]["itemType"] == "ITEM_WEAPON":
            weaponSub: str = equip["flat"]["weaponStats"][-1]["appendPropId"]
            weaponSubValue = equip["flat"]["weaponStats"][-1]["statValue"]
            res["weapon"] = {
                "id": equip["itemId"],
                "rarity": equip["flat"]["rankLevel"],  # int
                "name": HASH_TRANS.get(equip["flat"]["nameTextMapHash"], "缺少翻译"),
                "affix": list(equip["weapon"].get("affixMap", {"_": 0}).values())[0]
                + 1,
                "level": equip["weapon"]["level"],  # int
                "icon": equip["flat"]["icon"],
                "main": equip["flat"]["weaponStats"][0]["statValue"],  # int
                "sub": {
                    "prop": PROP[weaponSub].replace("百分比", ""),
                    "value": "{}{}".format(
                        weaponSubValue,
                        "" if weaponSub.endswith("ELEMENT_MASTERY") else "%",
                    ),
                }
                if weaponSub != "FIGHT_PROP_BASE_ATTACK"
                else {},
            }
        elif equip["flat"]["itemType"] == "ITEM_RELIQUARY":
            mainProp: Dict = equip["flat"]["reliquaryMainstat"]
            subProps: List = equip["flat"].get("reliquarySubstats", [])
            posIdx = list(POS.keys()).index(equip["flat"]["equipType"]) + 1
            relicData = {
                "pos": posIdx,
                "rarity": equip["flat"]["rankLevel"],
                "name": HASH_TRANS.get(equip["flat"]["nameTextMapHash"], "缺少翻译"),
                "setName": HASH_TRANS.get(equip["flat"]["setNameTextMapHash"], "缺少翻译"),
                "level": equip["reliquary"]["level"] - 1,
                "main": {
                    "prop": PROP[mainProp["mainPropId"]],
                    "value": mainProp["statValue"],
                },
                "sub": [
                    {"prop": PROP[s["appendPropId"]], "value": s["statValue"]}
                    for s in subProps
                ],
                "calc": {},
                "icon": equip["flat"]["icon"],
                "_appendPropIdList": equip["reliquary"].get("appendPropIdList", []),
            }
            relicData["calc"] = await calcRelicMark(
                relicData, res["element"], affixWeight, pointMark, maxMark
            )
            # 分数计算完毕后再将词条名称、数值转为适合 HTML 渲染的格式
            relicData["main"]["value"] = vStr(
                relicData["main"]["prop"], relicData["main"]["value"]
            )
            relicData["main"]["prop"] = kStr(relicData["main"]["prop"])
            relicData["sub"] = [
                {"prop": kStr(s["prop"]), "value": vStr(s["prop"], s["value"])}
                for s in relicData["sub"]
            ]
            # 额外数据处理
            relicData["calc"]["total"] = round(relicData["calc"]["total"], 1)
            relicData.pop("_appendPropIdList")
            relicSet[relicData["setName"]] = relicSet.get(relicData["setName"], 0) + 1
            res["relics"].append(relicData)
            # 累积圣遗物套装评分和计数器
            relicsMark += relicData["calc"]["total"]
            relicsCnt += 1
    # 圣遗物套装
    res["relicSet"] = relicSet
    res["relicCalc"] = {
        "rank": getRelicRank(relicsMark / relicsCnt) if relicsCnt else "NaN",
        "total": round(relicsMark, 1),
    }
    return res


async def transToTeyvat(avatarsData: List[Dict], uid: str) -> Dict:
    """
    转换内部格式角色数据为 Teyvat Helper 请求格式

    * ``param avatarsData: List[Dict]`` 内部格式角色数据，由 ``transFromEnka()`` 获取
    * ``param uid: str`` 角色所属用户 UID
    - ``return: Dict`` Teyvat Helper 请求格式角色数据
    """
    res = {"uid": uid, "role_data": []}
    if uid[0] not in ["1", "2"]:
        res["server"] = getServer(uid, teyvat=True)

    for avatarData in avatarsData:
        name = avatarData["name"]
        cons = avatarData["cons"]
        weapon = avatarData["weapon"]
        baseProp = avatarData["baseProp"]
        fightProp = avatarData["fightProp"]
        skills = avatarData["skills"]
        relics = avatarData["relics"]
        relicSet = avatarData["relicSet"]

        # dataFix from https://github.com/yoimiya-kokomi/miao-plugin/blob/ac27075276154ef5a87a458697f6e5492bd323bd/components/profile-data/enka-data.js#L186  # noqa: E501
        if name == "雷电将军":
            _thunderDmg = fightProp["雷元素伤害加成"]
            _recharge = fightProp["元素充能效率"]
            fightProp["雷元素伤害加成"] = max(0, _thunderDmg - (_recharge - 100) * 0.4)
        if name == "莫娜":
            _waterDmg = fightProp["水元素伤害加成"]
            _recharge = fightProp["元素充能效率"]
            fightProp["水元素伤害加成"] = max(0, _waterDmg - _recharge * 0.2)
        if name == "妮露" and cons == 6:
            _count = float(fightProp["生命值"] / 1000)
            _crit = fightProp["暴击率"]
            _critDmg = fightProp["暴击伤害"]
            fightProp["暴击率"] = max(5, _crit - min(30, _count * 0.6))
            fightProp["暴击伤害"] = max(50, _critDmg - min(60, _count * 1.2))
        if weapon["name"] in ["息灾", "波乱月白经津", "雾切之回光", "猎人之径"]:
            for elem in ["火", "水", "雷", "风", "冰", "岩", "草"]:
                _origin = fightProp[f"{elem}元素伤害加成"]
                fightProp[f"{elem}元素伤害加成"] = max(
                    0, _origin - 12 - 12 * (weapon["affix"] - 1) / 4
                )

        # 圣遗物数据
        artifacts = []
        for a in relics:
            tData = {
                "artifacts_name": a["name"],
                "artifacts_type": list(POS.values())[a["pos"] - 1],
                "level": a["level"],
                "maintips": kStr(a["main"]["prop"], reverse=True),
                "mainvalue": a["main"]["value"],
            }
            tData.update(
                {
                    f"tips{sIdx + 1}": "{}+{}".format(
                        kStr(s["prop"], reverse=True), s["value"]
                    )
                    for sIdx, s in enumerate(a["sub"])
                }
            )
            artifacts.append(tData)

        # 单个角色最终结果
        res["role_data"].append(
            {
                "uid": uid,
                "role": name,
                "role_class": cons,
                "level": int(avatarData["level"]),
                "weapon": weapon["name"],
                "weapon_level": weapon["level"],
                "weapon_class": f"精炼{weapon['affix']}阶",
                "hp": int(fightProp["生命值"]),
                "base_hp": int(baseProp["生命值"]),
                "attack": int(fightProp["攻击力"]),
                "base_attack": int(baseProp["攻击力"]),
                "defend": int(fightProp["防御力"]),
                "base_defend": int(baseProp["防御力"]),
                "element": round(fightProp["元素精通"]),
                "crit": f"{round(fightProp['暴击率'], 1)}%",
                "crit_dmg": f"{round(fightProp['暴击伤害'], 1)}%",
                "heal": f"{round(fightProp['治疗加成'], 1)}%",
                "recharge": f"{round(fightProp['元素充能效率'], 1)}%",
                "fire_dmg": f"{round(fightProp['火元素伤害加成'], 1)}%",
                "water_dmg": f"{round(fightProp['水元素伤害加成'], 1)}%",
                "thunder_dmg": f"{round(fightProp['雷元素伤害加成'], 1)}%",
                "wind_dmg": f"{round(fightProp['风元素伤害加成'], 1)}%",
                "ice_dmg": f"{round(fightProp['冰元素伤害加成'], 1)}%",
                "rock_dmg": f"{round(fightProp['岩元素伤害加成'], 1)}%",
                "grass_dmg": f"{round(fightProp['草元素伤害加成'], 1)}%",
                "physical_dmg": f"{round(fightProp['物理伤害加成'], 1)}%",
                "artifacts": "+".join(
                    f"{k}{4 if v >= 4 else (2 if v >= 2 else 1)}"
                    for k, v in relicSet.items()
                    if (v >= 2) or ("之人" in k)
                ),
                "ability1": skills["a"]["level"],
                "ability2": skills["e"]["level"],
                "ability3": skills["q"]["level"],
                "artifacts_detail": artifacts,
            }
        )

    return res


async def simplDamageRes(damage: Dict) -> Dict:
    """
    转换角色伤害计算请求数据为精简格式

    * ``param damage: Dict`` 角色伤害计算请求数据，由 ``queryDamageApi()["result"][int]`` 获取
    - ``return: Dict`` 精简格式伤害数据，出错时返回 ``{}``
    """
    res = {"level": damage["zdl_result"] or "NaN", "data": [], "buff": []}
    for key in ["damage_result_arr", "damage_result_arr2"]:
        for dmgDetail in damage[key]:
            dmgTitle = "{}{}".format(
                f"[{damage['zdl_result2']}]<br>" if key == "damage_result_arr2" else "",
                dmgDetail["title"],
            )
            if "期望" in str(dmgDetail["value"]) or not dmgDetail.get("expect"):
                dmgCrit, dmgExp = "-", str(dmgDetail["value"]).replace("期望", "")
            else:
                dmgCrit = str(dmgDetail["value"])
                dmgExp = str(dmgDetail["expect"]).replace("期望", "")
            res["data"].append([dmgTitle, dmgCrit, dmgExp])
    for buff in damage["bonus"]:
        # damage["bonus"]: {"0": {}, "2": {}, ...}
        # damage["bonus"]: [{}, {}, ...]
        intro = (
            damage["bonus"][buff]["intro"] if isinstance(buff, str) else buff["intro"]
        )
        buffTitle, buffDetail = intro.split("：")
        if buffTitle not in ["注", "备注"]:
            res["buff"].append([buffTitle, buffDetail])
    return res


async def simplFightProp(
    fightProp: Dict, baseProp: Dict, char: str, element: str
) -> Dict[str, Dict]:
    """
    转换角色面板数据为 HTML 模板需求格式

    * ``param fightProp: Dict`` 角色面板数据，由 ``transFromEnka()["fightProp"]`` 获取
    * ``param baseProp: Dict`` 角色基础数据，由 ``transFromEnka()["baseProp"]`` 获取
    * ``param element: str`` 角色元素属性
    - ``return: Dict[str, Dict]`` HTML 模板需求格式面板数据
    """
    affixWeight = CALC_RULES.get(char, {"攻击力百分比": 75, "暴击率": 100, "暴击伤害": 100})

    # 排列伤害加成
    prefer = (
        element if affixWeight.get("元素伤害加成", 0) > affixWeight.get("物理伤害加成", 0) else "物"
    )
    damages = sorted(
        [{"k": k, "v": v} for k, v in fightProp.items() if str(k).endswith("伤害加成")],
        key=lambda x: (x["v"], x["k"][0] == prefer),
        reverse=True,
    )
    for unuseDmg in damages[1:]:
        fightProp.pop(unuseDmg["k"])

    # 生成模板渲染所需数据
    res = {}
    for propTitle, propValue in fightProp.items():
        # 跳过无效治疗加成
        if propTitle == "治疗加成" and not propValue and not affixWeight.get(propTitle):
            continue
        # 整理渲染数据
        res[propTitle] = {
            "value": f"{round(propValue, 1)}%"
            if propTitle not in ["生命值", "攻击力", "防御力", "元素精通"]
            else round(propValue),
            "weight": max(affixWeight.get("元素伤害加成", 0), affixWeight.get("物理伤害加成", 0))
            if propTitle.endswith("伤害加成")
            else affixWeight.get(propTitle) or affixWeight.get(f"{propTitle}百分比", 0),
        }
        # 补充基础数值
        if propTitle in ["生命值", "攻击力", "防御力"]:
            res[propTitle]["detail"] = [
                round(baseProp[propTitle]),
                round(res[propTitle]["value"] - baseProp[propTitle]),
            ]
        # 标记异常伤害加成
        if propTitle.endswith("伤害加成"):
            if (
                propTitle[0] not in ["物", element]
                or affixWeight.get(propTitle[-6:], 0) != res[propTitle]["weight"]
            ):
                res[propTitle]["error"] = True

    return res


async def simplTeamDamageRes(raw: Dict, rolesData: Dict) -> Dict:
    """
    转换队伍伤害计算请求数据为精简格式

    * ``param raw: Dict`` 队伍伤害计算请求数据，由 ``queryDamageApi(*, "team")["result"]`` 获取
    * ``param rolesData: Dict`` 角色数据，键为角色中文名，值为内部格式
    - ``return: Dict`` 精简格式伤害数据。出错时返回 ``{"error": "错误信息"}``
    """
    s = (
        str(raw["zdl_tips0"])
        .replace("你的队伍", "")
        .replace("秒内造成总伤害", "-")
        .replace("，DPS为:", "")
    )
    tm, total = s.split("-")

    pieData, pieColor = [], []
    for x in raw["chart_data"]:
        char, damage = x["name"].split("\n")
        pieData.append({"char": char, "damage": float(damage.replace("W", ""))})
        pieColor.append(x["label"]["color"])
    pieData = sorted(pieData, key=lambda x: x["damage"], reverse=True)
    # 寻找伤害最高的角色元素属性，跳过绽放等伤害来源
    elem = [
        rolesData[_source["char"]]["element"]
        for _source in pieData
        if rolesData.get(_source["char"])
    ][0]

    avatars = {}
    for role in raw["role_list"]:
        panelData = rolesData[role["role"]]
        avatars[role["role"]] = {
            "rarity": role["role_star"],
            "icon": panelData["icon"],
            "name": role["role"],
            "elem": panelData["element"],
            "cons": role["role_class"],
            "level": role["role_level"].replace("Lv", ""),
            "weapon": {
                "icon": panelData["weapon"]["icon"],
                "level": panelData["weapon"]["level"],
                "rarity": panelData["weapon"]["rarity"],
                "affix": panelData["weapon"]["affix"],
            },
            "sets": {
                [r for r in panelData["relics"] if r["setName"] == k][0]["icon"].split(
                    "_"
                )[-2]: (2 if v < 4 else 4)
                for k, v in panelData["relicSet"].items()
                if v >= 2  # 暂未排版 祭X之人 单件套装
            },
            "cp": round(panelData["fightProp"]["暴击率"], 1),
            "cd": round(panelData["fightProp"]["暴击伤害"], 1),
            "key_prop": role["key_ability"],
            "key_value": role["key_value"],
            "skills": [
                {
                    "icon": skill["icon"],
                    "style": skill["style"],
                    "level": skill["level"],
                }
                for _, skill in panelData["skills"].items()
            ],
        }

    for rechargeData in raw["recharge_info"]:
        name, tmp = rechargeData["recharge"].split("共获取同色球")
        same, diff = tmp.split("个，异色球")
        if len(diff.split("个，无色球")) == 2:
            # 暂未排版无色球
            diff = diff.split("个，无色球")[0]
        avatars[name]["recharge"] = {
            "pct": rechargeData["rate"],
            "same": round(float(same), 1),
            "diff": round(float(diff.replace("个", "")), 1),
        }

    damages = []
    for step in raw["advice"]:
        if not step.get("content"):
            logger.error(f"奇怪的伤害：{step}")
            continue
        # content: "4.2s 雷神e协同，暴击:3016,不暴击:1565,期望:2343"
        t, s = step["content"].split(" ")
        if len(s.split("，")) == 1:
            # "3.89s 万叶q染色为:雷"
            a = s.split("，")[0]
            d = ["-", "-", "-"]
        else:
            a, dmgs = s.split("，")
            if len(dmgs.split(",")) == 1:
                d = ["-", "-", dmgs.split(",")[0].split("：")[-1]]
            else:
                d = [dd.split(":")[-1] for dd in dmgs.split(",")]
        damages.append([t.replace("s", ""), a.upper(), *d])

    buffs = []
    for buff in raw["buff"]:
        if not buff.get("content"):
            logger.error(f"奇怪的 Buff：{buff}")
            continue
        # buff: "1.5s 风套-怪物雷抗减少-40%"
        t, tmp = buff["content"].split(" ", 1)
        b, bd = tmp.split("-", 1)
        buffs.append([t.replace("s", ""), b.upper(), bd.upper()])

    return {
        "uid": raw["uid"],
        "elem": elem,
        "rank": raw["zdl_tips2"],
        "dps": raw["zdl_result"],
        "tm": tm,
        "total": total,
        "pie_data": json.dumps(pieData, ensure_ascii=False),
        "pie_color": json.dumps(pieColor),
        "avatars": avatars,
        "actions": raw["combo_intro"].split(","),
        "damages": damages,
        "buffs": buffs,
    }
