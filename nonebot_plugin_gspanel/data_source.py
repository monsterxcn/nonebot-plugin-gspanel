import json
import asyncio
from time import time
from copy import deepcopy
from typing import Dict, List, Union, Literal
from datetime import datetime, timezone, timedelta

from nonebot import require
from nonebot.log import logger
from httpx import HTTPError, AsyncClient

from .__utils__ import LOCAL_DIR, TPL_VERSION, SCALE_FACTOR, download
from .data_convert import (
    transFromEnka,
    transToTeyvat,
    simplDamageRes,
    simplFightProp,
    simplTeamDamageRes,
)

require("nonebot_plugin_htmlrender")
from nonebot_plugin_htmlrender import template_to_pic  # noqa: E402


async def queryPanelApi(uid: str) -> Dict:
    """
    原神游戏内角色展柜数据请求

    * ``param uid: str`` 查询用户 UID
    - ``return: Dict`` 查询结果，出错时返回 ``{"error": "错误信息"}``
    """
    enkaMirrors = [
        "https://enka.network",
        "https://enka.minigg.cn",
        "https://enka.microgg.cn",
    ]
    async with AsyncClient() as client:
        resJson = {}
        for idx, root in enumerate(enkaMirrors):
            try:
                res = await client.get(
                    url=f"{root}/api/uid/{uid}",
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
                    follow_redirects=True,
                    timeout=20.0,
                )
                resJson = res.json()
                break
            except (HTTPError, json.decoder.JSONDecodeError) as e:
                if idx == len(enkaMirrors) - 1:
                    logger.opt(exception=e).error("面板数据接口无法访问或返回错误")
                    return {"error": f"[{e.__class__.__name__}] 暂时无法访问面板数据接口.."}
                else:
                    logger.info(f"从 {root} 获取面板失败，正在自动切换镜像重试...")
    if not resJson.get("playerInfo"):
        return {"error": f"玩家 {uid} 返回信息不全，接口可能正在维护.."}
    if not resJson.get("avatarInfoList"):
        return {"error": f"玩家 {uid} 的角色展柜详细数据已隐藏！"}
    if not resJson["playerInfo"].get("showAvatarInfoList"):
        return {"error": f"玩家 {uid} 的角色展柜内还没有角色哦！"}
    return resJson


async def queryDamageApi(
    body: Dict, mode: Literal["single", "team"] = "single"
) -> Dict:
    """
    角色伤害计算数据请求（提瓦特小助手）

    * ``param body: Dict`` 查询角色数据
    * ``param mode: Literal["single", "team"] = "single"`` 查询接口类型，默认请求角色伤害接口，传入 ``"team"`` 请求队伍伤害接口
    - ``return: Dict`` 查询结果，出错时返回 ``{}``
    """  # noqa: E501
    apiMap = {
        "single": "https://api.lelaer.com/ys/getDamageResult.php",
        "team": "https://api.lelaer.com/ys/getTeamResult.php",
    }
    async with AsyncClient() as client:
        try:
            res = await client.post(
                apiMap[mode],
                json=body,
                headers={
                    "referer": "https://servicewechat.com/wx2ac9dce11213c3a8/192/page-frame.html",  # noqa: E501
                    "user-agent": (
                        "Mozilla/5.0 (Linux; Android 12; SM-G977N Build/SP1A.210812.016"
                        "; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
                        "Chrome/86.0.4240.99 XWEB/4375 MMWEBSDK/20221011 Mobile Safari"
                        "/537.36 MMWEBID/4357 MicroMessenger/8.0.30.2244(0x28001E44) "
                        "WeChat/arm64 Weixin GPVersion/1 NetType/WIFI Language/zh_CN "
                        "ABI/arm64 MiniProgramEnv/android"
                    ),
                },
                timeout=20.0,
            )
            return res.json()
        except (HTTPError, json.decoder.JSONDecodeError) as e:
            logger.opt(exception=e).error("提瓦特小助手接口无法访问或返回错误")
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
        nextQueryTime: int = cacheData["next"]
    else:
        cacheData, nextQueryTime = {}, 0

    refreshed, _tip, _time = [], "", 0

    if int(time()) <= nextQueryTime:
        _tip, _time = "warning", nextQueryTime
        logger.info(f"UID{uid} 的角色展柜数据刷新冷却还有 {int(nextQueryTime - time())} 秒！")
    else:
        logger.info(f"UID{uid} 的角色展柜数据正在刷新！")
        newData = await queryPanelApi(uid)
        _time = time()
        # 没有缓存 & 本次刷新失败，返回错误信息
        if not cacheData and newData.get("error"):
            return newData
        # 本次刷新成功，处理全部角色
        elif not newData.get("error"):
            _tip = "success"
            avatarsCache = {str(x["id"]): x for x in cacheData.get("avatars", [])}
            now, wait4Dmg, avatars = int(time()), {}, []
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
                        logger.debug(
                            "UID{} 的 {} 数据变化细则：\n{}\n{}".format(
                                uid, tmp["name"], avatarsCache[str(tmp["id"])], nowStat
                            )
                        )
                refreshed.append(tmp["id"])
                avatars.append(tmp)
                if not gotDmg:
                    wait4Dmg[str(len(avatars) - 1)] = tmp

            if wait4Dmg:
                _names = "/".join(f"[{aI}]{a['name']}" for aI, a in wait4Dmg.items())
                logger.info(f"正在为 UID{uid} 的 {_names} 重新请求伤害计算接口")
                # 深拷贝避免转换对上下文中的 avatars 产生影响
                wtf = deepcopy([a for _, a in wait4Dmg.items()])
                teyvatBody = await transToTeyvat(wtf, uid)
                teyvatRaw = await queryDamageApi(teyvatBody)
                if teyvatRaw.get("code", "x") != 200 or len(wait4Dmg) != len(
                    teyvatRaw.get("result", [])
                ):
                    logger.error(
                        f"UID{uid} 的 {len(wait4Dmg)} 位角色伤害计算请求失败！"
                        f"\n>>>> [提瓦特返回] {teyvatRaw}"
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
                    if aData["id"] not in refreshed
                ],
            ]
            cacheData["next"] = now + newData["ttl"]
            cache.write_text(
                json.dumps(cacheData, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        # 有缓存 & 本次刷新失败，打印错误信息
        else:
            _tip = "error"
            logger.error(newData["error"])

    # 获取所需角色数据
    if char == "全部":
        # 为本次更新的角色添加刷新标记
        for aIdx, aData in enumerate(cacheData["avatars"]):
            cacheData["avatars"][aIdx]["refreshed"] = aData["id"] in refreshed
        # 格式化刷新时间
        _datetime = datetime.fromtimestamp(_time, timezone(timedelta(hours=8)))
        cacheData["timetips"] = [_tip, _datetime.strftime("%Y-%m-%d %H:%M:%S")]
        return cacheData
    searchRes = [x for x in cacheData["avatars"] if x["name"] == char]
    return (
        {
            "error": "玩家 {} 游戏内展柜中的 {} 位角色中没有 {}！".format(
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
    htmlBase = str(LOCAL_DIR.resolve())

    # 获取面板数据
    data = await getAvatarData(uid, char)
    if data.get("error"):
        return data["error"]

    mode = "list" if char == "全部" else "panel"

    # 图标下载任务
    dlTasks = (
        [
            download(data["icon"], local=char),
            download(data["gachaAvatarImg"], local=char),
            *[
                download(sData["icon"], local=char)
                for _, sData in data["skills"].items()
            ],
            *[download(conData["icon"], local=char) for conData in data["consts"]],
            download(data["weapon"]["icon"], local="weapon"),
            *[
                download(relicData["icon"], local="artifacts")
                for relicData in data["relics"]
            ],
        ]
        if mode == "panel"
        else [download(role["icon"], local=role["name"]) for role in data["avatars"]]
    )
    await asyncio.gather(*dlTasks)
    dlTasks.clear()

    # 如果渲染角色面板，额外根据需要精简面板数据（缓存中仍保留全部数据）
    if mode == "panel":
        data["fightProp"] = await simplFightProp(
            data["fightProp"], data["baseProp"], char, data["element"]
        )

    # 渲染截图
    return await template_to_pic(
        template_path=htmlBase,
        template_name=f"{mode}-{TPL_VERSION}.html",
        templates={"css": TPL_VERSION, "uid": uid, "data": data},
        pages={
            "device_scale_factor": SCALE_FACTOR,
            "viewport": {"width": 600, "height": 300},
            "base_url": f"file://{htmlBase}",
        },
        wait=2,
    )


async def getTeam(uid: str, chars: List[str] = []) -> Union[bytes, str]:
    """
    队伍伤害消息生成入口

    * ``param uid: str`` 查询用户 UID
    * ``param chars: List[str] = []`` 查询角色，为空默认数据中前四个
    - ``return: Union[bytes, str]`` 查询结果。一般返回图片字节，出错时返回错误信息字符串
    """
    # 获取面板数据
    data = await getAvatarData(uid, "全部")
    if data.get("error"):
        return data["error"]

    if chars:
        extract = [a for a in data["avatars"] if a["name"] in chars]
        if len(extract) != len(chars):
            gotThis = [a["name"] for a in extract]
            return "玩家 {} 的最新数据中未发现{}！".format(
                uid, "、".join(c for c in chars if c not in gotThis)
            )
    elif len(data["avatars"]) >= 4:
        extract = data["avatars"][:4]
        logger.info(
            "UID{} 未指定队伍，自动选择面板中前 4 位进行计算：{} ...".format(
                uid, "、".join(a["name"] for a in extract)
            )
        )
    else:
        return f"玩家 {uid} 的面板数据甚至不足以组成一支队伍呢！"

    # 图片下载任务
    for tmp in extract:
        dlTasks = [
            download(tmp["icon"], local=tmp["name"]),
            *[
                download(sData["icon"], local=tmp["name"])
                for _, sData in tmp["skills"].items()
            ],
            download(tmp["weapon"]["icon"], local="weapon"),
            *[
                download(
                    f"UI_RelicIcon_{relicData['icon'].split('_')[-2]}_4",
                    local="artifacts",
                )
                for relicData in tmp["relics"]
            ],
        ]
        await asyncio.gather(*dlTasks)
        dlTasks.clear()

    teyvatBody = await transToTeyvat(deepcopy(extract), uid)
    teyvatRaw = await queryDamageApi(teyvatBody, "team")
    if teyvatRaw.get("code", "x") != 200 or not teyvatRaw.get("result"):
        logger.error(
            f"UID{uid} 的 {len(extract)} 位角色队伍伤害计算请求失败！" f"\n>>>> [提瓦特返回] {teyvatRaw}"
        )
        return f"玩家 {uid} 队伍伤害计算失败，接口可能发生变动！" if teyvatRaw else "啊哦，队伍伤害计算小程序状态异常！"
    try:
        data = await simplTeamDamageRes(
            teyvatRaw["result"], {a["name"]: a for a in extract}
        )
    except Exception as e:
        logger.opt(exception=e).error("队伍伤害数据解析出错")
        return f"[{e.__class__.__name__}] 队伍伤害数据解析出错咯"

    htmlBase = str(LOCAL_DIR.resolve())
    return await template_to_pic(
        template_path=htmlBase,
        template_name=f"team-{TPL_VERSION}.html",
        templates={"css": TPL_VERSION, "data": data},
        pages={
            "device_scale_factor": SCALE_FACTOR,
            "viewport": {"width": 600, "height": 300},
            "base_url": f"file://{htmlBase}",
        },
        wait=2,
    )
