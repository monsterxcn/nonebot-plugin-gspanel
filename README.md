<h1 align="center">NoneBot Plugin GsPanel</h1></br>


<p align="center">🤖 用于展示原神游戏内角色展柜数据的 NoneBot2 插件</p></br>


<p align="center">
  <a href="https://github.com/monsterxcn/nonebot-plugin-gspanel/actions">
    <img src="https://img.shields.io/github/workflow/status/monsterxcn/nonebot-plugin-gspanel/Build%20distributions?style=flat-square" alt="actions">
  </a>
  <a href="https://raw.githubusercontent.com/monsterxcn/nonebot-plugin-gspanel/master/LICENSE">
    <img src="https://img.shields.io/github/license/monsterxcn/nonebot-plugin-gspanel?style=flat-square" alt="license">
  </a>
  <a href="https://pypi.python.org/pypi/nonebot-plugin-gspanel">
    <img src="https://img.shields.io/pypi/v/nonebot-plugin-gspanel?style=flat-square" alt="pypi">
  </a>
  <img src="https://img.shields.io/badge/python-3.7.3+-blue?style=flat-square" alt="python"><br />
</p></br>


| ![刻晴](https://user-images.githubusercontent.com/22407052/187607775-61cfa24c-d736-4994-bd16-d211d807ae50.png) | ![琴](https://user-images.githubusercontent.com/22407052/187607799-b503f504-770f-4f80-85c6-9db78d5f849a.png) | ![香菱](https://user-images.githubusercontent.com/22407052/187607839-d29e3962-5bf6-4bf5-912d-2516e16b7643.png) |
|:--:|:--:|:--:|


## 安装方法


如果你正在使用 2.0.0.beta1 以上版本 NoneBot，推荐使用以下命令安装：


```bash
# 从 nb_cli 安装
python3 -m nb plugin install nonebot-plugin-gspanel

# 或从 PyPI 安装
python3 -m pip install nonebot-plugin-gspanel
```


<details><summary><i>在 NoneBot 2.0.0.alpha16 上使用此插件</i></summary></br>


在过时的 NoneBot 2.0.0.alpha16 上 **可能** 仍有机会体验此插件！不过，千万不要通过 NoneBot 脚手架或 PyPI 安装，仅支持通过 Git 手动安装此插件。

以下命令仅作参考：


```bash
# 进入 Bot 根目录
cd /path/to/bot
# 安装依赖
# source venv/bin/activate
python3 -m pip install playwright httpx
# 安装 Playwright 依赖
python3 -m playwright install-deps
python3 -m playwright install
# 安装插件
git clone https://github.com/monsterxcn/nonebot-plugin-gspanel.git
cd nonebot-plugin-gspanel
# 将文件夹 nonebot_plugin_gspanel 复制到 NoneBot2 插件目录下
cp -r nonebot_plugin_gspanel /path/to/bot/plugins/
# 将文件夹 resources 下内容复制到 /path/to/bot/data/ 目录下
mkdir /path/to/resources/gspanel/
cp -r data/gspanel /path/to/bot/data/
```


</details>


## 使用须知


 - 插件的圣遗物评分计算规则、卡片样式均来自 [@yoimiya-kokomi/miao-plugin](https://github.com/yoimiya-kokomi/miao-plugin)。此插件移植后作了以下修改：
   
   + 以角色生命值、攻击力、防御力的实际基础值进行词条得分计算，导致固定值的生命值、攻击力、防御力词条评分相较原版有小幅度波动
   + 于面板数据区域展示圣遗物评分使用的词条权重规则，插件尚未自定义词条权重规则的角色使用默认规则（攻击力 `75`、暴击率 `100`、暴击伤害 `100`）
   + 于面板数据区域展示角色最高的伤害加成数据，该属性与角色实际伤害属性不一致时区别显示词条权重规则
   + 对元素属性异常的空之杯进行评分惩罚，扣除该圣遗物总分的 50%（最大扣除比例）
   
 - 插件返回「暂时无法访问面板数据接口..」可能的原因有：Bot 与 [@Enka.Network](https://enka.shinshin.moe/) 的连接不稳定；[@Enka.Network](https://enka.shinshin.moe/) 服务器暂时故障等。
   
 - 插件首次生成某个角色的面板图片时，会尝试从 [@Enka.Network](https://enka.shinshin.moe/) 下载该角色的抽卡大图、命座图片、技能图片、圣遗物及武器图片等素材图片，生成面板图片的时间由 Bot 与 [@Enka.Network](https://enka.shinshin.moe/) 的连接质量决定。素材图片下载至本地后将不再从远程下载，生成面板图片的时间将大幅缩短。
   
 - 一般来说，插件安装完成后无需设置环境变量，只需重启 Bot 即可开始使用。你也可以在 Nonebot2 当前使用的 `.env` 文件中添加下表给出的环境变量，对插件进行更多配置。环境变量修改后需要重启 Bot 才能生效。
   
   | 环境变量 | 必需 | 默认 | 说明 |
   |:-------|:----:|:-----|:----|
   | `gspanel_expire_sec` | 否 | `300` | 面板数据缓存过期秒数 |
   | `resources_dir` | 否 | `/path/to/bot/data/` | 插件数据缓存目录的父文件夹，包含 `gspanel` 文件夹的上级文件夹路径 |



## 命令说明


插件响应以 `面板` / `评分` / `panel` 开头的消息，下面仅以 `面板` 为例。


 - `面板绑定100123456`
   
   绑定 UID `100123456` 至发送此指令的 QQ，QQ 已被绑定过则会更新绑定的 UID。
   
   Bot 管理员可以通过在此指令后附带 `@某人` 或 `2334556789` 的方式将 UID `100123456` 绑定至指定的 QQ。
   
 - `面板100123456`
   
   查找 UID `100123456` 角色展柜中展示的所有角色（文本）。
   
   仅发送 `面板` 时将尝试使用发送此指令的 QQ 绑定的 UID；发送 `面板@某人` 时将尝试使用指定 QQ 绑定的 UID。
   
 - `面板夜兰100123456` / `面板100123456夜兰`
   
   查找 UID `100123456` 的夜兰面板（图片）。
   
   仅发送 `面板夜兰` 时将尝试使用发送此指令的 QQ 绑定的 UID；发送 `面板夜兰@某人` 时将尝试使用指定 QQ 绑定的 UID。


*\*所有指令都可以用空格将关键词分割开来，如果你喜欢的话。*


## 特别鸣谢


[@nonebot/nonebot2](https://github.com/nonebot/nonebot2/) | [@Mrs4s/go-cqhttp](https://github.com/Mrs4s/go-cqhttp) | [@yoimiya-kokomi/miao-plugin](https://github.com/yoimiya-kokomi/miao-plugin) | [@Enka.Network](https://enka.network/)
