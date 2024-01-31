import re
import json
from pathlib import Path
from urllib import parse, request
from urllib.error import HTTPError


def read(fn: str):
    return json.loads(Path(f"./{fn}").read_text(encoding="UTF-8"))


def write(fn: str, content):
    Path(f"./{fn}").write_text(
        json.dumps(content, ensure_ascii=False, indent=2), encoding="UTF-8"
    )


AvatarDetail = read("Avatar.json")
TextMapCHS = read("TextMapCHS.json")
Avatar = read("AvatarExcelConfigData.json")
AvatarSkillRaw = read("AvatarSkillExcelConfigData.json")
AvatarSkillDepotRaw = read("AvatarSkillDepotExcelConfigData.json")
AvatarTalentRaw = read("AvatarTalentExcelConfigData.json")
AvatarCostumeRaw = read("AvatarCostumeExcelConfigData.json")
Weapons = read("WeaponExcelConfigData.json")
Reliquary = read("ReliquaryExcelConfigData.json")
ReliquaryAffix = read("ReliquaryAffixExcelConfigData.json")
ReliquarySet = read("EquipAffixExcelConfigData.json")

AvatarDetail = {i["Id"]: i for i in AvatarDetail}
AvatarSkill = {i["id"]: i for i in AvatarSkillRaw}
AvatarSkillDepot = {i["id"]: i for i in AvatarSkillDepotRaw}
AvatarTalent = {i["talentId"]: i for i in AvatarTalentRaw}
AvatarCostume = {i["itemId"]: i for i in AvatarCostumeRaw if i.get("itemId")}

OldCharData = read("../data/gspanel/char-data.json")
OldCharAlias = read("../data/gspanel/char-alias.json")
OldCalcRules = read("../data/gspanel/calc-rule.json")
MiaoCharAlias = read("miao-char-alias.json")
MiaoCalcRules = read("miao-calc-rule.json")
MIAO_REPO = "https://raw.githubusercontent.com/yoimiya-kokomi/miao-plugin"
MIAO_SPEC = MIAO_REPO + "/master/resources/meta-gs/character/{}/artis.js"
PROP_TRANS = {
    "生命值百分比": "hp",
    "攻击力百分比": "atk",
    "防御力百分比": "def",
    "暴击率": "cpct",
    "暴击伤害": "cdmg",
    "元素精通": "mastery",
    "元素伤害加成": "dmg",
    "物理伤害加成": "phy",
    "元素充能效率": "recharge",
    "治疗加成": "heal",
}
PRE, SUF = "\033[32m", "\033[0m"


def gnrtCharJson():
    AvatarDictionary = {}
    blacklist = [
        10000001,
        11000008,
        11000009,
        11000010,
        11000011,
        11000013,
        11000017,
        11000018,
        11000019,
        11000025,
        11000026,
        11000027,
        11000028,
        11000030,
        11000031,
        11000032,
        11000033,
        11000034,
        11000035,
        11000036,
        11000037,
        11000038,
        11000039,
        11000040,
        11000041,
        11000042,
        11000043,
        11000044,
        11000045,
    ]
    haveCostume = [list(i.values())[5] for i in AvatarCostumeRaw if i.get("itemId")]
    print(f"拥有时装角色列表: {haveCostume}")

    for avatarData in Avatar:
        hs = avatarData["nameTextMapHash"]
        if avatarData["id"] in [10000005, 10000007]:
            print(f"角色 {TextMapCHS.get(str(hs), '未知')} 是旅行者被跳过")
            continue
        if avatarData["id"] in blacklist:
            print(f"角色 {TextMapCHS.get(str(hs), '未知')} 在黑名单中被跳过")
            continue
        avatarID = avatarData["id"]
        depot = AvatarSkillDepot[avatarData["skillDepotId"]]
        if not depot.get("energySkill"):
            print(f"角色 {TextMapCHS.get(str(hs), '未知')} 没有技能数据被跳过")
            continue
        AvatarDictionary[avatarID] = {
            "Element": AvatarSkill[depot["energySkill"]]["costElemType"],
            "Name": str(avatarData["iconName"]).split("_")[-1],
            "NameCN": TextMapCHS.get(str(hs), "未知"),
            "Slogan": AvatarDetail[avatarID]["FetterInfo"]["Title"],
            "NameTextMapHash": hs,
            "QualityType": avatarData["qualityType"],
            "iconName": avatarData["iconName"],
            "SideIconName": avatarData["sideIconName"],
            "Base": {
                "hpBase": avatarData["hpBase"],
                "attackBase": avatarData["attackBase"],
                "defenseBase": avatarData["defenseBase"],
            },
            "Consts": [AvatarTalent[talent]["icon"] for talent in depot["talents"]],
        }
        skills = [*depot["skills"][:2], depot["energySkill"]]
        AvatarDictionary[avatarID]["SkillOrder"] = skills
        AvatarDictionary[avatarID]["Skills"] = {
            str(skill): AvatarSkill[skill]["skillIcon"] for skill in skills
        }
        AvatarDictionary[avatarID]["ProudMap"] = {
            str(skill): AvatarSkill[skill]["proudSkillGroupId"] for skill in skills
        }
        if avatarID in haveCostume:
            AvatarDictionary[avatarID]["Costumes"] = {}
            costumes = [
                i
                for i in AvatarCostumeRaw
                if list(dict(i).values())[5] == avatarID and i.get("sideIconName")
            ]
            print(
                "角色 {} 有 {} 件时装：{}".format(
                    TextMapCHS.get(str(hs), "未知"),
                    len(costumes),
                    "/".join(x["sideIconName"].split("_")[-1] for x in costumes),
                )
            )
            AvatarDictionary[avatarID]["Costumes"] = {
                str(list(dict(costume).values())[0]): {
                    "sideIconName": costume["sideIconName"],
                    "icon": "UI_AvatarIcon_" + costume["sideIconName"].split("_")[-1],
                    "art": "UI_Costume_" + costume["sideIconName"].split("_")[-1],
                    "avatarId": list(dict(costume).values())[5],
                }
                for costume in costumes
                if costume.get("sideIconName")
            }

    print(
        "{}角色数据更新完成！{}{}".format(
            PRE,
            "无事发生"
            if len(OldCharData) == len(AvatarDictionary)
            else "本次更新 {} 位新角色：{}".format(
                len(AvatarDictionary) - len(OldCharData),
                "、".join(
                    AvatarDictionary[k]["NameCN"]
                    for k in list(AvatarDictionary.keys())[
                        -(len(AvatarDictionary) - len(OldCharData)) :
                    ]
                ),
            ),
            SUF,
        )
    )
    write("char-data.json", AvatarDictionary)


def gnrtAliasJson():
    AliasDictionary = {}
    CharData = read("char-data.json")  # after gnrtCharJson()

    for charId, charInfo in CharData.items():
        name = charInfo["NameCN"]
        if OldCharAlias.get(name):
            AliasDictionary[name] = OldCharAlias[name]
            if MiaoCharAlias.get(name):
                extra = [a for a in MiaoCharAlias[name] if a not in OldCharAlias[name]]
                print(f"角色「{name}」可选别名：{'、'.join(extra)}")
        elif MiaoCharAlias.get(name):
            newCharAlias = [
                a for a in MiaoCharAlias[name] if not re.match(r"^[a-zA-Z\s]+$", a)
            ]
            AliasDictionary[name] = newCharAlias
            print(f"新增角色「{name}」别名：{'、'.join(newCharAlias)}")
        else:
            AliasDictionary[name] = []
            print(f"角色「{name}」还没有别名数据！")

    print(f"{PRE}角色别名更新完成！{SUF}")
    write("char-alias.json", AliasDictionary)


def gnrtRuleJson():
    RuleDictionary = {}
    CharData = read("char-data.json")  # after gnrtCharJson()

    oldRulesKeys = {}
    for ruleKey, ruleInfo in OldCalcRules.items():
        name = ruleKey.split("-")[0]
        oldRulesKeys[name] = oldRulesKeys.get(name, []) + [ruleKey]

    for charId, charInfo in CharData.items():
        name = charInfo["NameCN"]
        rulesGot = []

        if OldCalcRules.get(name):
            RuleDictionary[name] = OldCalcRules[name]
            rulesGot.append(name)
            if MiaoCalcRules.get(name):
                RuleDictionary[name].update(MiaoCalcRules[name])
                if RuleDictionary[name] != OldCalcRules[name]:
                    print(f"角色「{name}」评分规则变动")
        elif MiaoCalcRules.get(name):
            RuleDictionary[name] = MiaoCalcRules[name]
            rulesGot.append(name)
            print(f"新增角色「{name}」评分规则")
        else:
            print(f"角色「{name}」还没有评分规则数据！")

        try:
            url = parse.quote(MIAO_SPEC.format(name), safe=":/")
            response = request.urlopen(url)
            content = response.read().decode("UTF-8")
            pattern = r"return rule\('(.+?)', (\{.+?\})\)"
            matches = re.findall(pattern, content)
            for ruleName, ruleStr in matches:
                ruleName = f"{name}-{ruleName.split('-')[-1]}"
                ruleInfo = json.loads(re.sub(r"(\w+):", r'"\1":', ruleStr))
                RuleDictionary[ruleName] = {
                    k: ruleInfo[v]
                    for k, v in PROP_TRANS.items()
                    if ruleInfo.get(PROP_TRANS[k])
                }
                rulesGot.append(ruleName)
                if ruleName in oldRulesKeys.get(name, []):
                    if RuleDictionary[ruleName] != OldCalcRules[ruleName]:
                        print(f"角色「{name}」{ruleName.split('-')[-1]}评分规则变动")
                else:
                    print(f"新增角色「{name}」{ruleName.split('-')[-1]}评分规则")
        except HTTPError as e:
            if str(e) == "HTTP Error 404: Not Found":
                pass

        for ruleName in [r for r in oldRulesKeys.get(name, []) if r not in rulesGot]:
            RuleDictionary[ruleName] = OldCalcRules[ruleName]
            print(f"角色「{name}」{ruleName.split('-')[-1]}评分规则继承")

    print(
        "{}角色评分规则更新完成！{}{}".format(
            PRE,
            "无事发生"
            if len(RuleDictionary) == len(OldCalcRules)
            else f"新增 {len(RuleDictionary) - len(OldCalcRules)} 条",
            SUF,
        )
    )
    write("calc-rule.json", RuleDictionary)


def gnrtTransJson():
    TranslateDictionary = {}
    for avatarData in Avatar:
        hs = str(avatarData.get("nameTextMapHash", 0))
        if TextMapCHS.get(hs):
            TranslateDictionary[hs] = TextMapCHS[hs]
    for weapon in Weapons:
        hs = str(weapon.get("nameTextMapHash", 0))
        if TextMapCHS.get(hs):
            TranslateDictionary[hs] = TextMapCHS[hs]
    for set in ReliquarySet:
        hs = str(set.get("nameTextMapHash", 0))
        if str(set.get("openConfig")).startswith("Rel") and TextMapCHS.get(hs):
            TranslateDictionary[hs] = TextMapCHS[hs]
    for reliquary in Reliquary:
        hs = str(reliquary.get("nameTextMapHash", 0))
        if TextMapCHS.get(hs):
            TranslateDictionary[hs] = TextMapCHS[hs]

    print(f"{PRE}文本翻译更新完成！{SUF}")
    write("hash-trans.json", TranslateDictionary)


def gnrtAppendJson() -> None:
    PropDictionary = {str(x["id"]): x["propType"] for x in ReliquaryAffix}
    print(f"{PRE}圣遗物词条更新完成！{SUF}")
    write("relic-append.json", PropDictionary)


gnrtCharJson()
gnrtAliasJson()
gnrtRuleJson()
gnrtTransJson()
gnrtAppendJson()
