const fs = require('fs');
const usefulAttr = require("./artis-mark").usefulAttr;
const alias = require("./alias").alias;
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
const attrRes = {}
const aliasRes = {}

Object.entries(usefulAttr).forEach(([k, v]) => {
  const weights = {}
  Object.entries(v).forEach(([propK, propV]) => {
    if (propV === 0) return
    weights[trans[propK]] = propV
  })
  attrRes[k] = weights
})
Object.entries(alias).forEach(([k, v]) => {
  aliasRes[k] = v.split(",")
})

const rules = JSON.stringify(attrRes, null, 2);
const names = JSON.stringify(aliasRes, null, 2);
fs.writeFile("miao-calc-rule.json", rules, function (e, res) {
  if (e) console.log("error", e);
})
fs.writeFile("miao-char-alias.json", names, function (e, res) {
  if (e) console.log("error", e);
})
