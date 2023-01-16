import json
from pathlib import Path


def read(fn: str):
    return json.loads(Path(f"./{fn}").read_text(encoding="UTF-8"))


AvatarDetail = read("Avatar.json")
TextMapCHS = read("TextMapCHS.json")
Avatar = read("AvatarExcelConfigData.json")
AvatarSkillRaw = read("AvatarSkillExcelConfigData.json")
AvatarSkillDepotRaw = read("AvatarSkillDepotExcelConfigData.json")
AvatarTalentRaw = read("AvatarTalentExcelConfigData.json")
AvatarCostumeRaw = read("AvatarCostumeExcelConfigData.json")
Weapons = read("WeaponExcelConfigData.json")
Reliquary = read("ReliquaryExcelConfigData.json")
ReliquarySet = read("EquipAffixExcelConfigData.json")

AvatarDetail = {i["Id"]: i for i in AvatarDetail}
AvatarSkill = {i["id"]: i for i in AvatarSkillRaw}
AvatarSkillDepot = {i["id"]: i for i in AvatarSkillDepotRaw}
AvatarTalent = {i["talentId"]: i for i in AvatarTalentRaw}
AvatarCostume = {i["itemId"]: i for i in AvatarCostumeRaw if i.get("itemId")}
haveCostume = [list(dict(i).values())[5] for i in AvatarCostumeRaw if i.get("itemId")]
print(f"拥有时装角色列表: {haveCostume}")


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

    Path("./char-data.json").write_text(
        json.dumps(AvatarDictionary, ensure_ascii=False, indent=2), encoding="UTF-8"
    )


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

    Path("./hash-trans.json").write_text(
        json.dumps(TranslateDictionary, ensure_ascii=False, indent=2), encoding="UTF-8"
    )


gnrtCharJson()
gnrtTransJson()
