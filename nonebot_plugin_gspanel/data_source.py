import asyncio
import json
from copy import deepcopy
from time import time
from traceback import format_exc
from typing import Dict, Literal, Union

from httpx import AsyncClient, HTTPError
from nonebot_plugin_htmlrender import template_to_pic

from nonebot.log import logger

from .__utils__ import LOCAL_DIR, PANEL_TPL, SCALE_FACTOR, download
from .data_convert import simplDamageRes, simplFightProp, transFromEnka, transToTeyvat


async def queryPanelApi(uid: str, source: Literal["enka", "mgg"] = "enka") -> Dict:
    """
    原神游戏内角色展柜数据请求

    * ``param uid: str`` 查询用户 UID
    * ``param source: Literal["enka", "mgg"] = "enka"`` 查询接口
    - ``return: Dict`` 查询结果，出错时返回 ``{"error": "错误信息"}``
    """
    root = "https://enka.network" if source == "enka" else "https://enka.minigg.cn"
    try:
        async with AsyncClient() as client:
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
    except (HTTPError, json.decoder.JSONDecodeError):
        logger.error(f"面板数据接口无法访问或返回错误\n{format_exc()}")
        return {"error": "暂时无法访问面板数据接口.."}
    if not resJson.get("playerInfo"):
        return {"error": f"UID{uid} 返回信息不全，接口可能正在维护.."}
    if not resJson.get("avatarInfoList"):
        return {"error": f"UID{uid} 的角色展柜详细数据已隐藏！"}
    if not resJson["playerInfo"].get("showAvatarInfoList"):
        return {"error": f"UID{uid} 的角色展柜内还没有角色哦！"}
    return resJson


async def queryDamageApi(body: Dict) -> Dict:
    """
    角色伤害计算数据请求（提瓦特小助手）

    * ``param body: Dict`` 查询角色数据
    - ``return: Dict`` 查询结果，出错时返回 ``{}``
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
        except (HTTPError, json.decoder.JSONDecodeError):
            logger.error(f"提瓦特小助手接口无法访问或返回错误\n{format_exc()}")
            return {}
        except Exception as e:
            logger.error(f"提瓦特小助手接口错误：{e.__class__.__name__}\n{format_exc()}")
            return {}


async def getAvatarData(uid: str, char: str = "全部") -> Dict:
    """
    角色数据获取（内部格式）

    * ``param uid: str`` 查询用户 UID
    * ``param char: str = "全部"`` 查询角色名
    - ``return: Dict`` 查询结果。出错时返回 ``{"error": "错误信息"}``
    """
    # 总是先读取一遍缓存
    cache = LOCAL_DIR / "cache" / f"{uid}.json"
    if cache.exists():
        cacheData = json.loads(cache.read_text(encoding="utf-8"))
        nextQueryTime = cacheData["next"]
    else:
        cacheData, nextQueryTime = {}, 0

    if int(time()) <= nextQueryTime:
        logger.info("UID{} 的角色展柜数据刷新冷却还有 {} 秒！".format(uid, nextQueryTime - int(time())))
    else:
        logger.info(f"UID{uid} 的角色展柜数据正在刷新！")
        newData = await queryPanelApi(uid)
        if not cacheData and newData.get("error"):
            return newData
        elif not newData.get("error"):
            avatarsCache = {str(x["id"]): x for x in cacheData.get("avatars", [])}
            now, wait4Dmg, avatars, avatarIdsNew = int(time()), {}, [], []
            for newAvatar in newData["avatarInfoList"]:
                if newAvatar["avatarId"] in [10000005, 10000007]:
                    logger.info("旅行者面板查询暂未支持！")
                    continue
                tmp, gotDmg = await transFromEnka(newAvatar, now), False

                if str(tmp["id"]) in avatarsCache:
                    # 保留旧的伤害计算数据
                    avatarsCache[str(tmp["id"])].pop("time")
                    cacheDmg = avatarsCache[str(tmp["id"])].pop("damage")
                    nowStat = {
                        k: v for k, v in tmp.items() if k not in ["damage", "time"]
                    }
                    if cacheDmg and avatarsCache[str(tmp["id"])] == nowStat:
                        logger.info(f"UID{uid} 的 {tmp['name']} 伤害计算结果无需刷新！")
                        tmp["damage"], gotDmg = cacheDmg, True
                    else:
                        logger.info(
                            "UID{} 的 {} 数据发生变化：\n{}\n{}".format(
                                uid, tmp["name"], avatarsCache[str(tmp["id"])], nowStat
                            )
                        )
                avatarIdsNew.append(tmp["id"])
                avatars.append(tmp)
                if not gotDmg:
                    wait4Dmg[str(len(avatars) - 1)] = tmp

            if wait4Dmg:
                logger.info(
                    "正在为 UID{} 的 {} 重新请求伤害计算接口".format(
                        uid, "/".join(f"[{aI}]{a['name']}" for aI, a in wait4Dmg.items())
                    )
                )
                # 深拷贝避免转换对上下文中的 avatars 产生影响
                wtf = deepcopy([a for _, a in wait4Dmg.items()])
                teyvatBody = await transToTeyvat(wtf, uid)
                teyvatRaw = await queryDamageApi(teyvatBody)
                if teyvatRaw.get("code", "x") != 200 or len(wait4Dmg) != len(
                    teyvatRaw.get("result", [])
                ):
                    logger.error(
                        (
                            f"UID{uid} 的 {len(wait4Dmg)} 位角色伤害计算请求失败！"
                            f"\n>>>> [提瓦特返回] {teyvatRaw}"
                        )
                    )
                else:
                    for dmgIdx, dmgData in enumerate(teyvatRaw.get("result", [])):
                        aIdx = int(list(wait4Dmg.keys())[dmgIdx])
                        avatars[aIdx]["damage"] = await simplDamageRes(dmgData)

            cacheData["avatars"] = [
                *avatars,
                *[
                    aData
                    for _, aData in avatarsCache.items()
                    if aData["id"] not in avatarIdsNew
                ],
            ]
            cacheData["next"] = now + newData["ttl"]
            cache.write_text(
                json.dumps(cacheData, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    # 获取所需角色数据
    if char == "全部":
        return {
            "error": "成功获取了 UID{} 的{}等 {} 位角色数据！".format(
                uid,
                "、".join(a["name"] for a in cacheData["avatars"]),
                len(cacheData["avatars"]),
            )
        }
    searchRes = [x for x in cacheData["avatars"] if x["name"] == char]
    return (
        {
            "error": "UID{} 游戏内展柜中的 {} 位角色中没有 {}！".format(
                uid, len(cacheData["avatars"]), char
            )
        }
        if not searchRes
        else searchRes[0]
    )


async def getPanel(uid: str, char: str = "全部") -> Union[bytes, str]:
    """
    原神游戏内角色展柜消息生成入口

    * ``param uid: str`` 查询用户 UID
    * ``param char: str = "全部"`` 查询角色
    - ``return: Union[bytes, str]`` 查询结果。一般返回图片字节，出错时返回错误信息字符串
    """
    # 获取面板数据
    data = await getAvatarData(uid, char)
    if data.get("error"):
        return data["error"]

    # 图标下载任务
    dlTasks = [
        download(data["icon"], local=char),
        download(data["gachaAvatarImg"], local=char),
        *[download(sData["icon"], local=char) for _, sData in data["skills"].items()],
        *[download(conData["icon"], local=char) for conData in data["consts"]],
        download(data["weapon"]["icon"], local="weapon"),
        *[download(relicData["icon"], local="artifacts") for relicData in data["relics"]],
    ]
    await asyncio.gather(*dlTasks)
    dlTasks.clear()

    # 渲染截图
    data["fightProp"] = await simplFightProp(
        data["fightProp"], data["baseProp"], char, data["element"]
    )
    htmlBase = str(LOCAL_DIR.resolve())
    return await template_to_pic(
        template_path=htmlBase,
        template_name=f"{PANEL_TPL}.html",
        templates={"css": PANEL_TPL, "uid": uid, "data": data},
        pages={
            "device_scale_factor": SCALE_FACTOR,
            "viewport": {"width": 600, "height": 300},
            "base_url": f"file://{htmlBase}",
        },
        wait=2,
    )
