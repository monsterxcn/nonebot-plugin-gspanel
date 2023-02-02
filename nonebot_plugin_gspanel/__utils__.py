import json
import asyncio
from pathlib import Path
from re import IGNORECASE, sub, findall
from typing import Set, List, Tuple, Union

from nonebot import get_driver
from nonebot.log import logger
from nonebot.drivers import Driver
from httpx import Client, AsyncClient

GROW_VALUE = {  # 理论最高档（4档）词条成长值
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
SINGLE_VALUE = {  # 用于计算词条数
    "暴击率": 3.3,
    "暴击伤害": 6.6,
    "元素精通": 19.75,
    "生命值百分比": 4.975,
    "攻击力百分比": 4.975,
    "防御力百分比": 6.2,
    "元素充能效率": 5.5,
}
MAIN_AFFIXS = {  # 可能的主词条
    "3": "攻击力百分比,防御力百分比,生命值百分比,元素精通,元素充能效率".split(","),  # EQUIP_SHOES
    "4": "攻击力百分比,防御力百分比,生命值百分比,元素精通,元素伤害加成,物理伤害加成".split(","),  # EQUIP_RING
    "5": "攻击力百分比,防御力百分比,生命值百分比,元素精通,治疗加成,暴击率,暴击伤害".split(","),  # EQUIP_DRESS
}
SUB_AFFIXS = "攻击力,攻击力百分比,防御力,防御力百分比,生命值,生命值百分比,元素精通,元素充能效率,暴击率,暴击伤害".split(",")
RANK_MAP = [
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
ELEM = {
    "Fire": "火",
    "Water": "水",
    "Wind": "风",
    "Electric": "雷",
    "Grass": "草",
    "Ice": "冰",
    "Rock": "岩",
}
POS = {
    "EQUIP_BRACER": "生之花",
    "EQUIP_NECKLACE": "死之羽",
    "EQUIP_SHOES": "时之沙",
    "EQUIP_RING": "空之杯",
    "EQUIP_DRESS": "理之冠",
}
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
    "FIGHT_PROP_GRASS_ADD_HURT": "草元素伤害加成",
    "FIGHT_PROP_WIND_ADD_HURT": "风元素伤害加成",
    "FIGHT_PROP_ICE_ADD_HURT": "冰元素伤害加成",
    "FIGHT_PROP_ROCK_ADD_HURT": "岩元素伤害加成",
}

driver: Driver = get_driver()

GSPANEL_ALIAS: Set[Union[str, Tuple[str, ...]]] = (
    set(driver.config.gspanel_alias)
    if hasattr(driver.config, "gspanel_alias")
    else {"面板"}
)
LOCAL_DIR = (
    (Path(driver.config.resources_dir) / "gspanel")
    if hasattr(driver.config, "resources_dir")
    else (Path() / "data" / "gspanel")
)
SCALE_FACTOR = (
    float(driver.config.gspanel_scale)
    if hasattr(driver.config, "gspanel_scale")
    else 1.0
)
DOWNLOAD_MIRROR = (
    str(driver.config.resources_mirror)
    if hasattr(driver.config, "resources_mirror")
    else "https://enka.network/ui/"
)
if not LOCAL_DIR.exists():
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
if not (LOCAL_DIR / "cache").exists():
    (LOCAL_DIR / "cache").mkdir(parents=True, exist_ok=True)
if not (LOCAL_DIR / "qq-uid.json").exists():
    (LOCAL_DIR / "qq-uid.json").write_text("{}", encoding="UTF-8")
_client = Client(verify=False)
CALC_RULES = _client.get("https://cdn.monsterx.cn/bot/gspanel/calc-rule.json").json()
(LOCAL_DIR / "calc-rule.json").write_text(
    json.dumps(CALC_RULES, ensure_ascii=False, indent=2), encoding="utf-8"
)
CHAR_DATA = _client.get("https://cdn.monsterx.cn/bot/gspanel/char-data.json").json()
(LOCAL_DIR / "char-data.json").write_text(
    json.dumps(CHAR_DATA, ensure_ascii=False, indent=2), encoding="utf-8"
)
CHAR_ALIAS = _client.get("https://cdn.monsterx.cn/bot/gspanel/char-alias.json").json()
(LOCAL_DIR / "char-alias.json").write_text(
    json.dumps(CHAR_ALIAS, ensure_ascii=False, indent=2), encoding="utf-8"
)
TEAM_ALIAS = _client.get("https://cdn.monsterx.cn/bot/gspanel/team-alias.json").json()
(LOCAL_DIR / "team-alias.json").write_text(
    json.dumps(TEAM_ALIAS, ensure_ascii=False, indent=2), encoding="utf-8"
)
HASH_TRANS = _client.get("https://cdn.monsterx.cn/bot/gspanel/hash-trans.json").json()
(LOCAL_DIR / "hash-trans.json").write_text(
    json.dumps(HASH_TRANS, ensure_ascii=False, indent=2), encoding="utf-8"
)
RELIC_APPEND = _client.get(
    "https://cdn.monsterx.cn/bot/gspanel/relic-append.json"
).json()
(LOCAL_DIR / "relic-append.json").write_text(
    json.dumps(RELIC_APPEND, ensure_ascii=False, indent=2), encoding="utf-8"
)
TPL_VERSION = "0.2.7"


def kStr(prop: str, reverse: bool = False) -> str:
    """转换词条名称为简短形式"""
    if reverse:
        return prop.replace("充能", "元素充能").replace("伤加成", "元素伤害加成").replace("物理元素", "物理")
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


def getServer(uid: str, teyvat: bool = False) -> str:
    """获取指定 UID 所属服务器，返回如 ``cn_gf01``"""
    if uid[0] == "5":
        return "cn_qd01"
    elif uid[0] == "6":
        return "us" if teyvat else "os_usa"
    elif uid[0] == "7":
        return "eur" if teyvat else "os_euro"
    elif uid[0] == "8":
        return "asia" if teyvat else "os_asia"
    elif uid[0] == "9":
        return "hk" if teyvat else "os_cht"
    return "cn_gf01"


async def formatInput(msg: str, qq: str, atqq: str = "") -> Tuple[str, str]:
    """
    输入消息中的 UID 与角色名格式化，应具备处理 ``msg`` 为空、包含中文或数字的能力。
    - 首个中文字符串捕获为角色名，若不包含则返回 ``all`` 请求角色面板列表数据
    - 首个数字字符串捕获为 UID，若不包含则返回 ``uidHelper()`` 根据绑定配置查找的 UID

    * ``param msg: str`` 输入消息，由 ``state["_prefix"]["command_arg"]`` 或 ``event.get_plaintext()`` 生成，可能包含 CQ 码
    * ``param qq: str`` 输入消息触发 QQ
    * ``param atqq: str = ""`` 输入消息中首个 at 的 QQ
    - ``return: Tuple[str, str]``  UID、角色名
    """  # noqa: E501
    uid, char, tmp = "", "", ""
    group = findall(
        r"[0-9]+|[\u4e00-\u9fa5]+|[a-z]+", sub(r"\[CQ:.*\]", "", msg), flags=IGNORECASE
    )
    for s in group:
        if s.isdigit():
            if len(s) == 9:
                if not uid:
                    uid = s
            else:
                # 0人，1斗，97忍
                tmp = s
        elif s.encode().isalpha():
            # dio娜，abd
            tmp = s.lower()
        elif not s.isdigit() and not char:
            char = tmp + s
    uid = uid or await uidHelper(atqq or qq)
    char = await aliasWho(char or tmp or "全部")
    return uid, char


async def formatTeam(msg: str, qq: str, atqq: str = "") -> Tuple[str, List]:
    """
    输入消息中的 UID 与队伍角色名格式化

    * ``param msg: str`` 输入消息，由 ``MessageSegment.data["text"]`` 拼接组成
    * ``param qq: str`` 输入消息触发 QQ
    * ``param atqq: str = ""`` 输入消息中首个 at 的 QQ
    - ``return: Tuple[str, List]``  UID、队伍角色名
    """
    uid, chars = "", []
    for seg in msg.split():
        _uid, char = await formatInput(seg, qq, atqq)
        uid = uid or _uid
        if char != "全部" and char not in chars:
            logger.info(f"从 QQ{qq} 的输入「{seg}」中识别到 UID[{uid}] CHAR[{char}]")
            chars.append(char)
    if not msg:
        uid, _ = await formatInput("", qq, atqq)
    if len(chars) == 1:
        searchTeam = await aliasTeam(chars[0])
        chars = searchTeam if isinstance(searchTeam, List) else chars
    return uid, chars


async def fetchInitRes() -> None:
    """
    插件初始化资源下载，通过阿里云 CDN 获取 HTML 模板资源文件、角色词条权重配置、角色数据、TextMap 中文翻译数据等
    """
    logger.info("正在检查面板插件所需资源...")
    # 仅首次启用插件下载的文件
    initRes = [
        "https://cdn.monsterx.cn/bot/gspanel/font/HYWH-65W.ttf",
        "https://cdn.monsterx.cn/bot/gspanel/font/tttgbnumber.ttf",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-anemo.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-cryo.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-dendro.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-electro.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-geo.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-hydro.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/bg-pyro.jpg",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-anemo.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-cryo.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-dendro.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-electro.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-geo.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-hydro.png",
        "https://cdn.monsterx.cn/bot/gspanel/imgs/talent-pyro.png",
        "https://cdn.monsterx.cn/bot/gspanel/g2plot.min.js",
        f"https://cdn.monsterx.cn/bot/gspanel/team-{TPL_VERSION}.css",
        f"https://cdn.monsterx.cn/bot/gspanel/team-{TPL_VERSION}.html",
        f"https://cdn.monsterx.cn/bot/gspanel/panel-{TPL_VERSION}.css",
        f"https://cdn.monsterx.cn/bot/gspanel/panel-{TPL_VERSION}.html",
        f"https://cdn.monsterx.cn/bot/gspanel/list-{TPL_VERSION}.css",
        f"https://cdn.monsterx.cn/bot/gspanel/list-{TPL_VERSION}.html",
    ]
    tasks = []
    for r in initRes:
        d = r.replace("https://cdn.monsterx.cn/bot/gspanel/", "").split("/")[0]
        tasks.append(download(r, local=("" if "." in d else d)))
    await asyncio.gather(*tasks)
    tasks.clear()
    logger.info("面板插件所需资源检查完毕！")


async def download(
    url: str, local: Union[Path, str] = "", retry: int = 3
) -> Union[Path, None]:
    """
    一般文件下载，通常是即用即下的角色命座图片、技能图片、抽卡大图、圣遗物图片等

    * ``param url: str`` 下载链接
    * ``param local: Union[Path, str] = ""`` 下载路径，传入类型为 ``Path`` 时视为保存文件完整路径，传入类型为 ``str`` 时视为保存文件子文件夹名（默认下载至插件资源根目录）
    * ``param retry: int = 3`` 下载失败重试次数
    - ``return: Union[Path, None]`` 本地文件路径，出错时返回空
    """  # noqa: E501
    if not url.startswith("http"):
        url = DOWNLOAD_MIRROR + url + ".png"
    if not isinstance(local, Path):
        d = (LOCAL_DIR / local) if local else LOCAL_DIR
        if not d.exists():
            d.mkdir(parents=True, exist_ok=True)
        f = d / url.split("/")[-1]
    else:
        if not local.parent.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
        f = local
    # 本地文件存在时便不再下载，JSON 文件除外
    if f.exists() and ".json" not in f.name:
        return f
    client, retry = AsyncClient(), 3
    while retry:
        try:
            async with client.stream(
                "GET", url, headers={"user-agent": "NoneBot-GsPanel"}
            ) as res:
                with open(f, "wb") as fb:
                    async for chunk in res.aiter_bytes():
                        fb.write(chunk)
            return f
        except Exception as e:
            retry -= 1
            if retry:
                await asyncio.sleep(2)
            else:
                logger.opt(exception=e).error(f"面板资源 {f.name} 下载出错")
    return None


async def uidHelper(qq: Union[str, int], uid: str = "") -> str:
    """
    UID 助手，根据 QQ 获取对应原神 UID，也可传入 UID 更新指定 QQ 的绑定情况

    * ``param qq: Union[str, int]`` 操作 QQ
    * ``param uid: str = ""`` 操作 UID，默认不传入以查找该值，传入则视为绑定/更新
    - ``return: str``指定 QQ 绑定的原神 UID，绑定/更新时返回操作结果
    """
    qq = str(qq)
    cfgFile = LOCAL_DIR / "qq-uid.json"
    uidCfg = json.loads(cfgFile.read_text(encoding="utf-8"))
    if uid:
        uidCfg[qq] = uid
        cfgFile.write_text(
            json.dumps(uidCfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return "已{} QQ{} 的 UID 为 {}".format("更新" if qq in uidCfg else "绑定", qq, uid)
    return uidCfg.get(qq, "")


async def aliasWho(input: str) -> str:
    """角色别名，未找到别名配置的原样返回"""
    for char in CHAR_ALIAS:
        if (input in char) or (input in CHAR_ALIAS[char]):
            return char
    return input


async def aliasTeam(input: str) -> Union[str, List]:
    """队伍别名，未找到别名配置的原样返回"""
    for team in TEAM_ALIAS:
        if (input == team) or (input in TEAM_ALIAS[team].get("alias", [])):
            return TEAM_ALIAS[team]["chars"]
    return input
