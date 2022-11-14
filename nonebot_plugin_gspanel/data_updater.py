"""
迁移缓存的面板数据，将在未来某个版本删除
"""

import asyncio
import json

from nonebot.log import logger

from .__utils__ import LOCAL_DIR
from .data_convert import simplDamageRes, transFromEnka, transToTeyvat
from .data_source import queryDamageApi


async def updateCache() -> None:
    for f in (LOCAL_DIR / "cache").iterdir():
        cache = json.loads(f.read_text(encoding="UTF-8"))
        if f.name.replace(".json", "").isdigit():
            uid = f.name.replace(".json", "")
            for aIdx, a in enumerate(cache["avatars"]):
                if a["damage"]:
                    continue
                teyvatBody = await transToTeyvat(a, uid)
                teyvatRaw = await queryDamageApi(teyvatBody)
                cache["avatars"][aIdx]["damage"] = await simplDamageRes(teyvatRaw)
                if aIdx != len(cache["avatars"]) - 1:
                    await asyncio.sleep(2)
            f.write_text(
                json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            continue
        uid = f.name.replace("__data.json", "")
        newF = LOCAL_DIR / "cache" / f"{uid}.json"
        if newF.exists():
            continue
        now, avatars = cache["time"], []
        avatarInfoList = cache.get("avatarInfoList", [])
        if not avatarInfoList:
            logger.error(f"UID{uid} 没有角色数据")
            continue
        for idx, avatarData in enumerate(avatarInfoList):
            if avatarData["avatarId"] in [10000005, 10000007]:
                logger.info("旅行者面板查询暂未支持！")
                continue
            tmp = await transFromEnka(avatarData, now)
            teyvatBody = await transToTeyvat(tmp, uid)
            teyvatRaw = await queryDamageApi(teyvatBody)
            tmp["damage"] = await simplDamageRes(teyvatRaw)
            avatars.append(tmp)
            if idx != len(cache["avatarInfoList"]) - 1:
                await asyncio.sleep(2)
        newCache = {"avatars": avatars, "next": now + 120}
        newF.write_text(
            json.dumps(newCache, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        f.unlink(missing_ok=True)
        logger.info(f"UID{uid} 的角色面板缓存已迁移完毕！")
