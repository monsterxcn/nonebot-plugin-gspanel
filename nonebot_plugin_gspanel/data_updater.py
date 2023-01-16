"""
迁移缓存的面板数据，将在未来某个版本删除
"""

import json
import asyncio
from copy import deepcopy

from nonebot.log import logger

from .__utils__ import LOCAL_DIR
from .data_source import queryDamageApi
from .data_convert import transFromEnka, transToTeyvat, simplDamageRes


async def updateCache() -> None:
    for f in (LOCAL_DIR / "cache").iterdir():
        cache = json.loads(f.read_text(encoding="UTF-8"))
        if f.name.replace(".json", "").isdigit():
            # 已经迁移的文件中部分数据格式升级
            uid, wait4Dmg = f.name.replace(".json", ""), {}
            for aIdx, a in enumerate(cache["avatars"]):
                cache["avatars"][aIdx]["level"] = int(a["level"])
                if not a["damage"]:
                    wait4Dmg[str(aIdx)] = a
                else:
                    # 暴击伤害移动至期望伤害
                    for dIdx, d in enumerate(a["damage"].get("data", [])):
                        if str(d[1]).isdigit() and d[2] == "-":
                            cache["avatars"][aIdx]["damage"]["data"][dIdx] = [
                                d[0],
                                d[2],
                                d[1],
                            ]
            if wait4Dmg:
                # 补充角色伤害数据
                logger.info(
                    "正在为 UID{} 的 {} 重新请求伤害计算接口".format(
                        uid, "/".join(a["name"] for _, a in wait4Dmg.items())
                    )
                )
                teyvatBody = await transToTeyvat(
                    deepcopy([a for _, a in wait4Dmg.items()]), uid
                )
                teyvatRaw = await queryDamageApi(teyvatBody)
                if teyvatRaw.get("code", "x") != 200 or len(wait4Dmg) != len(
                    teyvatRaw.get("result", [])
                ):
                    logger.error(
                        f"UID{uid} 的 {len(wait4Dmg)} 位角色伤害计算请求失败！"
                        f"\n>>>> [提瓦特返回] {teyvatRaw}"
                    )
                for dmgIdx, dmgData in enumerate(teyvatRaw.get("result", [])):
                    aRealIdx = int(list(wait4Dmg.keys())[dmgIdx])
                    cache["avatars"][aRealIdx]["damage"] = await simplDamageRes(dmgData)
            f.write_text(
                json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            continue
        # 旧版缓存文件，内容为 Enka.Network 返回
        uid = f.name.replace("__data.json", "")
        now, newData = cache["time"], []
        avatarInfoList = cache.get("avatarInfoList", [])
        if not avatarInfoList:
            logger.error(f"UID{uid} 没有角色数据，清除旧版缓存")
            f.unlink(missing_ok=True)
            continue
        for avatarData in avatarInfoList:
            if avatarData["avatarId"] in [10000005, 10000007]:
                logger.info(f"UID{uid} 面板中含有旅行者，跳过暂未支持的角色！")
                continue
            newData.append(await transFromEnka(avatarData, now))
        # 补充角色伤害数据
        teyvatBody = await transToTeyvat(deepcopy(newData), uid)
        teyvatRaw = await queryDamageApi(teyvatBody)
        if teyvatRaw.get("code", "x") != 200 or len(newData) != len(
            teyvatRaw.get("result", [])
        ):
            logger.error(
                f"UID{uid} 的 {len(newData)} 位角色伤害计算请求失败！\n>>>> [提瓦特返回] {teyvatRaw}"
            )
        else:
            for tvtIdx, tvtDmg in enumerate(teyvatRaw["result"]):
                newData[tvtIdx]["damage"] = await simplDamageRes(tvtDmg)
        newCache = {"avatars": newData, "next": now + 120}
        (LOCAL_DIR / "cache" / f"{uid}.json").write_text(
            json.dumps(newCache, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        f.unlink(missing_ok=True)
        logger.info(f"UID{uid} 的角色面板缓存已迁移完毕！")
        await asyncio.sleep(2)
