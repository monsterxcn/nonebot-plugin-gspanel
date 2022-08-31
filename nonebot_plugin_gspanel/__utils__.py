import asyncio
import json
from pathlib import Path
from typing import Optional, Union

from httpx import AsyncClient
from nonebot import get_driver
from nonebot.drivers import Driver
from nonebot.log import logger
from playwright.async_api import Browser, async_playwright

GROW_VALUE = {  # 词条成长值
    "暴击率": 3.89,
    "暴击伤害": 7.77,
    "元素精通": 23.31,
    "攻击力百分比": 5.83,
    "生命值百分比": 5.83,
    "防御力百分比": 7.29,
    "元素充能效率": 6.48,
    "元素伤害加成": 5.825,
    "物理伤害加成": 7.288,
    "治疗加成": 4.487,
}
MAIN_AFFIXS = {  # 可能的主词条
    "3": "攻击力百分比,防御力百分比,生命值百分比,元素精通,元素充能效率".split(","),  # EQUIP_SHOES
    "4": "攻击力百分比,防御力百分比,生命值百分比,元素精通,元素伤害加成,物理伤害加成".split(","),  # EQUIP_RING
    "5": "攻击力百分比,防御力百分比,生命值百分比,元素精通,治疗加成,暴击率,暴击伤害".split(","),  # EQUIP_DRESS
}
SUB_AFFIXS = "攻击力,攻击力百分比,防御力,防御力百分比,生命值,生命值百分比,元素精通,元素充能效率,暴击率,暴击伤害".split(",")
# STAR = {"QUALITY_ORANGE": 5, "QUALITY_PURPLE": 4}
ELEM = {
    "Fire": "火",
    "Water": "水",
    "Wind": "风",
    "Electric": "雷",
    "Grass": "草",
    "Ice": "冰",
    "Rock": "岩",
}
POS = ["EQUIP_BRACER", "EQUIP_NECKLACE", "EQUIP_SHOES", "EQUIP_RING", "EQUIP_DRESS"]
SKILL = {"1": "a", "2": "e", "9": "q"}
DMG = {
    "40": "火",
    "41": "雷",
    "42": "水",
    "43": "草",
    "44": "风",
    "45": "岩",
    "46": "冰",
}
PROP = {
    "FIGHT_PROP_BASE_ATTACK": "基础攻击力",
    "FIGHT_PROP_HP": "生命值",
    "FIGHT_PROP_ATTACK": "攻击力",
    "FIGHT_PROP_DEFENSE": "防御力",
    "FIGHT_PROP_HP_PERCENT": "生命值百分比",
    "FIGHT_PROP_ATTACK_PERCENT": "攻击力百分比",
    "FIGHT_PROP_DEFENSE_PERCENT": "防御力百分比",
    "FIGHT_PROP_CRITICAL": "暴击率",
    "FIGHT_PROP_CRITICAL_HURT": "暴击伤害",
    "FIGHT_PROP_CHARGE_EFFICIENCY": "元素充能效率",
    "FIGHT_PROP_HEAL_ADD": "治疗加成",
    "FIGHT_PROP_ELEMENT_MASTERY": "元素精通",
    "FIGHT_PROP_PHYSICAL_ADD_HURT": "物理伤害加成",
    "FIGHT_PROP_FIRE_ADD_HURT": "火元素伤害加成",
    "FIGHT_PROP_ELEC_ADD_HURT": "雷元素伤害加成",
    "FIGHT_PROP_WATER_ADD_HURT": "水元素伤害加成",
    "FIGHT_PROP_WIND_ADD_HURT": "风元素伤害加成",
    "FIGHT_PROP_ICE_ADD_HURT": "冰元素伤害加成",
    "FIGHT_PROP_ROCK_ADD_HURT": "岩元素伤害加成",
}

driver: Driver = get_driver()
_browser: Optional[Browser] = None

EXPIRE_SEC = (
    int(driver.config.gspanel_expire_sec)
    if hasattr(driver.config, "gspanel_expire_sec")
    else 60 * 5
)
LOCAL_DIR = (
    (Path(driver.config.resources_dir) / "gspanel")
    if hasattr(driver.config, "resources_dir")
    else (Path() / "data" / "gspanel")
)
if not LOCAL_DIR.exists():
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
if not (LOCAL_DIR / "cache").exists():
    (LOCAL_DIR / "cache").mkdir(parents=True, exist_ok=True)
if not (LOCAL_DIR / "qq-uid.json").exists():
    (LOCAL_DIR / "qq-uid.json").write_text("{}", encoding="UTF-8")


def kStr(prop: str) -> str:
    """转换词条名称为简短形式"""
    return (
        prop.replace("百分比", "")
        .replace("元素充能", "充能")
        .replace("元素伤害", "伤")
        .replace("物理伤害", "物伤")
    )


def vStr(prop: str, value: Union[int, float]) -> str:
    """转换词条数值为字符串形式"""
    if prop in ["生命值", "攻击力", "防御力", "元素精通"]:
        return str(value)
    else:
        return str(round(value, 1)) + "%"


async def initBrowser(**kwargs) -> Optional[Browser]:
    global _browser
    browser = await async_playwright().start()
    try:
        _browser = await browser.chromium.launch(**kwargs)
        return _browser
    except Exception as e:
        logger.error(f"启动 Chromium 发生错误 {type(e)}：{e}")
    return None


async def getBrowser(**kwargs) -> Optional[Browser]:
    return _browser or await initBrowser(**kwargs)


async def fetchInitRes() -> None:
    """
    插件初始化资源下载，通过阿里云 CDN 获取 Enka.Network API 提供的 JSON 文件、HTML 模板资源文件、角色词条权重配置等
    - https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/loc.json
    - https://raw.githubusercontent.com/Dimbreath/GenshinData/master/TextMap/TextMapCHS.json
    - https://raw.githubusercontent.com/EnkaNetwork/API-docs/master/store/characters.json
    - https://raw.githubusercontent.com/monsterxcn/nonebot_plugin_gspanel/main/data/gspanel/template.json
    - https://raw.githubusercontent.com/monsterxcn/nonebot_plugin_gspanel/main/data/gspanel/calc-rule.json
    """
    logger.info("正在检查面板插件所需资源...")
    # 仅首次启用插件下载的文件
    initRes = [
        "https://cdn.monsterx.cn/bot/gspanel/font/华文中宋.TTF",
        "https://cdn.monsterx.cn/bot/gspanel/font/HYWH-65W.ttf",
        "https://cdn.monsterx.cn/bot/gspanel/font/NZBZ.ttf",
        "https://cdn.monsterx.cn/bot/gspanel/font/tttgbnumber.ttf",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-anemo.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-cryo.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-dendro.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-electro.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-geo.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-hydro.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-pyro.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/card-bg.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/star.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-anemo.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-cryo.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-dendro.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-electro.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-geo.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-hydro.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-pyro.png",
        "https://cdn.monsterx.cn/bot/gspanel/style.css",
        "https://cdn.monsterx.cn/bot/gspanel/tpl.html",
        "https://cdn.monsterx.cn/bot/gspanel/calc-rule.json",
    ]
    tasks = []
    for r in initRes:
        d = r.replace("https://cdn.monsterx.cn/bot/gspanel/", "").split("/")[0]
        tasks.append(download(r, local=("" if "." in d else d)))
    await asyncio.gather(*tasks)
    tasks.clear()
    logger.debug("首次启用所需资源检查完毕..")
    # 总是尝试更新的文件
    urls = [
        # "https://cdn.monsterx.cn/bot/gapanel/loc.json",  # 仅包含 zh-CN 语言
        "https://cdn.monsterx.cn/bot/gspanel/TextMapCHS.json",
        "https://cdn.monsterx.cn/bot/gspanel/characters.json",
    ]
    tmp = {"0": {}, "1": {}}
    async with AsyncClient(verify=False) as client:
        for idx, url in enumerate(urls):
            tmp[str(idx)] = (await client.get(url)).json()
            (LOCAL_DIR / url.split("/")[-1]).write_text(
                json.dumps(tmp[str(idx)], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    # 额外生成一份 {"中文名": "8 位角色 ID", ...} 配置
    name2id, unknownCnt = {}, 1
    for charId in tmp["1"]:  # characters.json
        if not tmp["1"][charId].get("NameTextMapHash"):
            # 10000005-502 10000005-503 10000005-505
            # 10000007-702 10000007-703 10000007-705
            continue
        nameTextMapHash = tmp["1"][charId]["NameTextMapHash"]  # type: int
        nameCn = tmp["0"].get(str(nameTextMapHash), f"未知角色{unknownCnt}")
        name2id[nameCn] = charId
        if nameCn == f"未知角色{unknownCnt}":
            unknownCnt += 1
    (LOCAL_DIR / "name2id.json").write_text(
        json.dumps(name2id, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("面板插件所需资源检查完毕！")


async def download(url: str, local: Union[Path, str] = "") -> Union[Path, None]:
    """
    一般文件下载，通常是即用即下的角色命座图片、技能图片、抽卡大图、圣遗物图片等

    * ``param url: str`` 指定下载链接
    * ``param local: Union[Path, str] = ""`` 指定本地目标路径，传入类型为 ``Path`` 时视为保存文件完整路径，传入类型为 ``str`` 时视为保存文件子文件夹名（默认下载至插件资源根目录）
    - ``return: Union[Path, None]`` 本地文件地址，出错时返回空
    """
    if not isinstance(local, Path):
        d = (LOCAL_DIR / local) if local else LOCAL_DIR
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
        f = d / url.split("/")[-1]
    else:
        f = local
    # 本地文件存在时便不再下载，JSON 文件除外
    if f.exists() and ".json" not in f.name:
        return f
    client = AsyncClient()
    retryCnt = 3
    while retryCnt:
        try:
            async with client.stream(
                "GET", url, headers={"user-agent": "NoneBot-GsPanel"}
            ) as res:
                with open(f, "wb") as fb:
                    async for chunk in res.aiter_bytes():
                        fb.write(chunk)
            return f
        except Exception as e:
            logger.error(f"面板资源 {f.name} 下载出错 {type(e)}：{e}")
            retryCnt -= 1
            await asyncio.sleep(2)
    return None


async def uidHelper(qq: Union[str, int], uid: str = "") -> str:
    """
    UID 助手，根据 QQ 获取对应原神 UID，也可传入 UID 更新指定 QQ 的绑定情况

    * ``param qq: Union[str, int]`` 指定操作 QQ
    * ``param uid: str = ""`` 指定 UID，默认不传入以查找该值，传入则视为绑定/更新
    - ``return: str``指定 QQ 绑定的原神 UID，绑定/更新时返回操作结果
    """
    uidCfg = json.loads((LOCAL_DIR / "qq-uid.json").read_text(encoding="utf-8"))
    if uid:
        already = bool(str(qq) in uidCfg)
        uidCfg[str(qq)] = uid
        (LOCAL_DIR / "qq-uid.json").write_text(
            json.dumps(uidCfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return f"已{'更新' if already else '绑定'} QQ{qq} 的 UID 为 {uid}"
    return uidCfg.get(str(qq), "")
