# Modified from @yoimiya-kokomi/miao-plugin
# https://github.com/yoimiya-kokomi/miao-plugin/blob/master/components/models/Reliquaries2.js

# import json

from typing import Dict, Tuple

from .calc_meta import getCalcData, getCharRule

# from nonebot.log import logger


attrValue, allMainAffix, allSubAffix, multiRule = getCalcData()


# 获取期望词条
def getMostExp(weights: dict, avalAffixs: list, exclude: str = "") -> list:
    count = 4 if exclude else 1
    affixs = [
        {"prop": affix, "weight": weights[affix]}
        for affix in avalAffixs
        if weights[affix] and affix != exclude
    ]
    affixs = sorted(affixs, key=lambda x: x["weight"])
    affixs.reverse()
    if len(affixs) > 2:
        if affixs[0]["weight"] == affixs[1]["weight"]:
            if affixs[0]["prop"] == "暴击率":
                affixs[0], affixs[1] = affixs[1], affixs[0]
    # logger.info(json.dumps(affixs, ensure_ascii=False, indent=2))
    affixsName = [affix["prop"] for affix in affixs[:count]]
    return affixsName


# 获取单个圣遗物分数上限？
def getMaxMark(weights: dict) -> dict:
    maxMark = {}
    for posIdx in range(1, 6):
        mainMark, totalMark = 0, 0
        if posIdx == 1:
            expMainAffix = "生命值[小]"
        elif posIdx == 2:
            expMainAffix = "攻击力[小]"
        else:
            expMainAffix = getMostExp(weights, allMainAffix[str(posIdx)])[0]
            mainMark = weights[expMainAffix]
            totalMark += mainMark * 2
            # logger.info(f"posIdx({posIdx}) - Main exp：{expMainAffix}")
        expSubAffix = getMostExp(weights, allSubAffix, expMainAffix)
        # logger.info(f"posIdx({posIdx}) - Sub exp：{expSubAffix}")
        totalMark += sum(
            weights[affix] * (6 if idx == 0 else 1)
            for idx, affix in enumerate(expSubAffix, start=0)
        )
        maxMark[posIdx] = {
            "main": mainMark,
            "total": totalMark
        }
        # logger.info(f"posIdx({posIdx}) - main({mainMark}), total({totalMark})")  # noqa
        # print("\n")
    return maxMark


# 获取角色计算规则数据
def getAvatarCfg(name: str) -> Tuple[dict, dict, dict]:
    # name is cn string
    charData = getCharRule(name)
    base = charData["基础"]  # character's lv.90 stat
    weight = charData["权重"]  # useful prop weight
    mark = {
        propName: propValue / attrValue[propName]
        for propName, propValue in weight.items()
    }
    exchange = {
        "生命值": mark["生命值"] / base["生命值"] * 100,
        "攻击力": mark["攻击力"] / (base["攻击力"] + 400) * 100,
        "防御力": mark["防御力"] / base["防御力"] * 100,
    }
    for c in ["生命值", "攻击力", "防御力"]:
        mark[c + "百分比"] = mark[c]
        if mark[c]:
            mark[c] = exchange[c]
    # logger.info(json.dumps(weight, ensure_ascii=False, indent=2))
    # logger.info(json.dumps(mark, ensure_ascii=False, indent=2))
    maxMark = getMaxMark(weight)
    return weight, mark, maxMark


# 计算单个圣遗物词条得分
def getAffixScore(weights: dict, affix: dict) -> float:
    # logger.info(f'attr({affix["prop"]}, {affix["value"]}) * weight({weights.get(affix["prop"], 0)}) = {weights.get(affix["prop"], 0) * affix["value"]}')  # noqa
    wIdx = affix["prop"][1:] if "元素伤害" in affix["prop"] else affix["prop"]
    return weights.get(wIdx, 0) * affix["value"]


# 计算单件圣遗物得分
def getScore(avatarCfg: Tuple, artisData: dict) -> float:
    weight, mark, maxMark = avatarCfg
    posIdx = artisData["pos"]
    mainAffix = artisData["main"]
    subAffixs = artisData["sub"]
    score = sum(getAffixScore(mark, affix) for affix in subAffixs)
    # logger.info(f"posIdx({posIdx}) - Sub score: {score}\n")
    fixPct = 1
    if posIdx >= 3:
        if "元素伤害" in mainAffix["prop"]:
            wIdx = mainAffix["prop"][1:]
        else:
            wIdx = mainAffix["prop"].replace("百分比", "")
        tmp = weight.get(wIdx, 0)
        tmp = tmp / maxMark[posIdx]["main"]
        fixPct = max(0, min(1, tmp))
        mainScore = getAffixScore(mark, mainAffix)
        # logger.info(f"posIdx({posIdx}) - Main score: {mainScore}")
        score += mainScore / 4
    # logger.info(f"posIdx({posIdx}) - Total score: {score} [FIX:{fixPct}]")
    return score * (1 + fixPct) / 2 / maxMark[posIdx]["total"] * 66


# 获取得分评级
def getScoreLevel(score: float) -> str:
    scoreMap = [
        ["D", 10],
        ["C", 16.5],
        ["B", 23.1],
        ["A", 29.7],
        ["S", 36.3],
        ["SS", 42.9],
        ["SSS", 49.5],
        ["ACE", 56.1],
        ["ACE²", 66]
    ]
    for idx in range(len(scoreMap)):
        if score < scoreMap[idx][1]:
            return scoreMap[idx][0]
    return "E"


# 计算全套圣遗物得分，有多个计算规则时返回套装总得分最高的结果
def getAllScore(avatarInfo: dict) -> Dict:
    name = avatarInfo["name"]
    rules = multiRule[name] if name in multiRule else [name]
    avatarCfgs = [getAvatarCfg(r) for r in rules]
    allScores = [
        {"rule": r, "score": 0, "level": "E", "pos": {}, "use": {}}
        for r in rules
    ]
    for idx, avatarCfg in enumerate(avatarCfgs, start=0):
        cnt = 5
        for arti in avatarInfo["artifacts"]:
            posIdx = str(arti["pos"])
            # try:
            score = round(getScore(avatarCfg, arti), 1)
            level = getScoreLevel(score)
            allScores[idx]["pos"][posIdx] = {"score": score, "level": level}
            allScores[idx]["score"] += score
            # except Exception as e:
            # logger.error(f"{name}圣遗物({posIdx})评分出错 {type(e)}：{e}")
            # allScores[idx]["pos"][posIdx] = {"score": 0, "level": "E"}
            # cnt -= 1
        allScores[idx]["score"] = round(allScores[idx]["score"], 1)
        allScores[idx]["level"] = getScoreLevel(allScores[idx]["score"] / cnt)
        allScores[idx]["use"] = avatarCfg[0]
    allScores = sorted(allScores, key=lambda x: x["score"], reverse=True)
    return allScores[0]
