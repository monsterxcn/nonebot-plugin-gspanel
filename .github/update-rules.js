const fs = require('fs');
const usefulAttr = require("./artis-mark").usefulAttr;
const trans = {
  "hp": "生命值百分比",
  "atk": "攻击力百分比",
  "def": "防御力百分比",
  "cpct": "暴击率",
  "cdmg": "暴击伤害",
  "mastery": "元素精通",
  "dmg": "元素伤害加成",
  "phy": "物理伤害加成",
  "recharge": "元素充能效率",
  "heal": "治疗加成"
}
const res = {}

Object.entries(usefulAttr).forEach(([k, v]) => {
    const weights = {}
    Object.entries(v).forEach(([propK, propV]) => {
        if (propV === 0) return
        weights[trans[propK]] = propV
    })
    res[k] = weights
})

const rules = JSON.stringify(res, null, 2);
fs.writeFile("calc-rule.json", rules, function (e, res) {
    if (e) console.log("error", e);
})
