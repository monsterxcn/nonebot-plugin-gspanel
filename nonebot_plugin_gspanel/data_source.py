import json
import os
import time
from typing import Optional, Tuple, Union

from httpx import AsyncClient
from nonebot import get_driver
from nonebot.log import logger

from .calc_meta import getArtiTrans, getElement, getEnkaTrans, getNameTrans

resPath = get_driver().config.gspanel_res
if not resPath:
    raise ValueError("请在环境变量中添加 gspanel_res 参数")
nameTrans, weaponTrans = getNameTrans()
propTrans, posTrans, eTypeTrans = getEnkaTrans()
artiTrans = getArtiTrans()


# 根据 QQ 获取用户 UID
async def getUid(qq: str, uid: str = "") -> str:
    config = f"{resPath}qq-uid.json"
    if not os.path.exists(config):
        with open(config, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
        return ""
    with open(config, encoding="utf-8") as f:
        cookies = json.load(f)
    if uid:
        cookies[qq] = uid
        with open(config, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
    return cookies[qq] if qq in list(cookies) else ""


# 检查 UID 是否合法
def uidChecker(uid: Union[str, int]) -> Tuple[str, Optional[str]]:
    try:
        uid = str(int(uid))
        if len(uid) == 9:
            # 判断 9 位 UID 首位得到所在服务器
            if uid[0] == "1" or uid[0] == "2":
                return uid, "cn_gf01"
            if uid[0] == "5":
                return uid, "cn_qd01"
        elif len(uid) < 9:
            # 少于 9 位 UID 自动补成官服形式
            uid = str(int(uid.zfill(9)) + 100000000)
            return uid, "cn_gf01"
    except Exception:
        pass
    # 输入 UID 不合法返回所在服务器为空
    return str(uid), None


# 检查缓存是否有效
async def cacheChecker(cacheFile: str) -> dict:
    try:
        timeNow = int(time.time())
        with open(cacheFile, encoding="UTF-8") as f:
            cache = json.load(f)
            f.close()
        timeCache = int(cache["time"])
        # 文件存在且查询时间在 5 分钟（300 秒）以内则缓存有效
        if timeNow - timeCache < 3600:  # 还是 1 小时吧
            # 返回读取到的缓存字典
            return cache
    except FileNotFoundError:
        pass
    except Exception as e:
        logger.error(f"检查缓存文件 {cacheFile} 出错 {type(e)}：{e}")
        pass
    # 出错或缓存失效则返回空
    return {}


# 查询 Enka.Network API
async def enkaHttp(uid: str) -> dict:
    enkaUrl = f"https://enka.shinshin.moe/u/{uid}/__data.json"
    enkaHeaders = {
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
        "Cache-Control": "no-cache",
        "Cookie": "locale=zh-CN",
        "Referer": "https://enka.shinshin.moe/",
        "User-Agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Mobile Safari/537.36", # noqa
    }
    async with AsyncClient() as client:
        try:
            res = await client.get(enkaUrl, headers=enkaHeaders, timeout=20.0)
            resJson = res.json()
            # cacheFile = f"{resPath}{uid}.raw.json"
            # with open(cacheFile, "w", encoding="utf-8") as f:
            #     json.dump(resJson, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"请求 Enka.Network 出错 {type(e)}：{e}")
            return {}
    # 返回 Enka.Network API 查询结果
    return resJson


# 处理装备信息（武器、圣遗物）
def getEquipInfo(equipList: list) -> dict:
    eInfo = {"weapon": {}, "artifacts": []}
    for equip in equipList:
        if eTypeTrans[equip["flat"]["itemType"]] == "武器":
            eInfo["weapon"] = {
                "id": equip["itemId"],
                "rank": int(str(equip["itemId"])[2]),
                # "rank": list(equip["weapon"]["affixMap"].values())[0],
                "level": equip["weapon"]["level"],
                "promote": equip["weapon"].get("promoteLevel", 0),
                "affix": [*equip["weapon"].get("affixMap", {"_": 0}).values()][0] + 1,
                "name": weaponTrans[str(equip["itemId"])],
                "base": equip["flat"]["weaponStats"][0]["statValue"],
                "stat": {},
            }
            if len(equip["flat"]["weaponStats"]) > 1:
                eInfo["weapon"]["stat"] = [
                    {
                        "name": propTrans[stat["appendPropId"]],
                        "value": stat["statValue"],
                    }
                    for stat in equip["flat"]["weaponStats"]
                    if propTrans[stat["appendPropId"]] != "武器基础攻击力"
                ][0]
        else:
            artiSetId = equip["flat"]["icon"].split("_")[-2]
            artiPosId = posTrans[equip["flat"]["equipType"]]
            artiCnName = artiTrans[artiSetId][str(artiPosId)]
            eInfo["artifacts"].append({
                "id": equip["itemId"],
                "set": int(artiSetId),
                "pos": artiPosId,
                "rank": equip["flat"]["rankLevel"],
                "level": equip["reliquary"]["level"] - 1,
                "name": artiCnName,
                "main": {
                    "prop": propTrans[
                        equip["flat"]["reliquaryMainstat"]["mainPropId"]
                    ],
                    "value": equip["flat"]["reliquaryMainstat"]["statValue"],
                },
                "sub": [
                    {
                        "prop": propTrans[stat["appendPropId"]],
                        "value": stat["statValue"]
                    } for stat in equip["flat"]["reliquarySubstats"]
                ],
            })
    return eInfo


# 处理命座与技能等级信息
def getConsAndSkill(
    skillLevelMap: dict,
    talentIdList: Optional[list],
    proudSkillExtraLevelMap: Optional[dict]
) -> Tuple[int, dict]:
    cons = len(talentIdList) if talentIdList else 0
    aLevel, eLevel, qLevel = [*skillLevelMap.values()][-3:]
    skill = {
        "a": {"origin": aLevel, "current": aLevel},
        "e": {"origin": eLevel, "current": eLevel},
        "q": {"origin": qLevel, "current": qLevel},
    }
    if not proudSkillExtraLevelMap:
        return cons, skill
    addTo = {"1": "a", "2": "e", "9": "q"}
    for extra in proudSkillExtraLevelMap:
        sType = addTo[extra[-1]]
        sAdd = proudSkillExtraLevelMap[extra]
        skill[sType]["current"] += sAdd
    return cons, skill


# 处理单个角色信息
def getAvatarInfo(avatar: dict) -> dict:
    fightProp = {
        "hp": round(avatar["fightPropMap"]["2000"]),
        "hpBase": round(avatar["fightPropMap"]["1"]),
        "atk": round(avatar["fightPropMap"]["2001"]),
        "atkBase": round(avatar["fightPropMap"]["4"]),
        "def": round(avatar["fightPropMap"]["2002"]),
        "defBase": round(avatar["fightPropMap"]["7"]),
        "cr": round(avatar["fightPropMap"]["20"] * 100, 1),
        "cd": round(avatar["fightPropMap"]["22"] * 100, 1),
        "em": round(avatar["fightPropMap"]["28"]),
        "er": round(avatar["fightPropMap"]["23"] * 100, 1),
        "heal": round(avatar["fightPropMap"]["26"] * 100, 1),
        "phy": round(avatar["fightPropMap"]["30"] * 100, 1),
        "dmg": {}
    }
    # 显示数值最高的伤害加成
    dmgType = {
        "40": "火",
        "41": "雷",
        "42": "水",
        "43": "草",
        "44": "风",
        "45": "岩",
        "46": "冰"
    }
    dmgBonus = [
        {
            "type": dmgType[t],
            "value": round(avatar["fightPropMap"][t] * 100, 1)
        } for t in ["40", "41", "42", "43", "44", "45", "46"]
    ]
    dmgBonus = sorted(dmgBonus, key=lambda x: x["value"], reverse=True)
    fightProp["dmg"] = dmgBonus[0]
    # 处理命座与技能等级信息
    skillLevel = avatar["skillLevelMap"]
    consList = avatar.get("talentIdList", [])
    extraLevel = avatar.get("proudSkillExtraLevelMap", {})
    cons, skill = getConsAndSkill(skillLevel, consList, extraLevel)
    # 处理装备信息
    equipments = getEquipInfo(avatar["equipList"])
    avatarName = nameTrans[str(avatar["avatarId"])[-2:]]
    avatarInfo = {
        "id": avatar["avatarId"],
        "name": avatarName,
        "elem": getElement(avatarName),
        "level": int(avatar["propMap"]["4001"]["ival"]),
        "fetter": avatar["fetterInfo"]["expLevel"],
        "stat": fightProp,
        "cons": cons,
        "skill": skill,
        # "weapon": {},
        # "reliquaries": [],
    }
    avatarInfo = {**avatarInfo, **equipments}
    return avatarInfo


# 获取完整用户信息
async def getFullJson(uid: str, force: bool = False) -> Union[str, dict]:
    # 先检查缓存，缓存失效再请求 Enka.Network API
    enkaCacheFile = f"{resPath}{uid}.enka.json"
    enkaRaw = await cacheChecker(enkaCacheFile) if not force else {}
    if enkaRaw:
        # 其实也不是 Raw，而是已经处理过的更好读的 JSON 了
        return enkaRaw
    enkaRaw = await enkaHttp(uid)
    if not enkaRaw:
        return "暂时无法访问数据接口！"
    # 未展示返回警告
    if not enkaRaw["playerInfo"].get("showAvatarInfoList"):
        return "角色展柜内还没有角色哦！"
    if not enkaRaw.get("avatarInfoList"):
        return "角色展柜详细数据已隐藏！"
    # 生成可读 JSON
    readableJson = {
        "playerInfo": {
            "uid": uid,
            "level": enkaRaw["playerInfo"]["level"],
            "worldLevel": enkaRaw["playerInfo"]["worldLevel"],
            "nameCardId": enkaRaw["playerInfo"]["nameCardId"],
            "avatar": nameTrans[
                str(enkaRaw["playerInfo"]["profilePicture"]["avatarId"])[-2:]
            ],
            "nickname": enkaRaw["playerInfo"]["nickname"],
            "signature": enkaRaw["playerInfo"].get("signature", ""),
        },
        "avatarInfoList": [],
        "time": int(time.time())
    }
    for avatar in enkaRaw["avatarInfoList"]:
        avatarInfo = getAvatarInfo(avatar)
        readableJson["avatarInfoList"].append(avatarInfo)
    with open(enkaCacheFile, "w", encoding="utf-8") as f:
        json.dump(readableJson, f, ensure_ascii=False, indent=2)
    # 返回查询结果
    return readableJson
