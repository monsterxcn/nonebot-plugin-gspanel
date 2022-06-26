<h1 align="center">Nonebot Plugin GsPanel</h1></br>


<p align="center">🤖 用于展示原神游戏内角色展柜数据的 Nonebot2 插件</p></br>


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


**安装方法**


> 不知道 `nonebot2.0.0b3` 用起来效果如何，因为我还在用 `nonebot2.0.0a16` 捏，大伙可以试试看。


使用以下命令安装 Nonebot Plugin GsPanel 插件：


```bash
# 从 Git 安装
git clone https://github.com/monsterxcn/nonebot-plugin-gspanel.git
cd nonebot-plugin-gspanel
# 将文件夹 utils 复制到 Nonebot2 根目录下
cp -r utils /path/to/nonebot/
# 将文件夹 nonebot_plugin_gspanel 复制到 Nonebot2 插件目录下
cp -r nonebot_plugin_gspanel /path/to/nonebot/plugins/
# 将文件夹 resources 下内容复制到 /path/to/resources/gspanel/ 目录下
mkdir /path/to/resources/gspanel/
cp -r resources /path/to/resources/gspanel/
```


打开 Nonebot2 正在使用的 `.env` 文件，添加一个 `gspanel_res` 环境变量，填写 resources 文件夹的本地路径。如果完全按照上面的命令安装，值可能像这样 `/path/to/resources/gspanel/`


重启 Bot 即可体验此插件。


<details><summary><i>不许看不许看不许看...</i></summary></br>


<img src="https://user-images.githubusercontent.com/22407052/175809169-38dbd472-a762-498a-940e-9ea9489ee6c7.PNG" height="600px"> <img src="https://user-images.githubusercontent.com/22407052/175809162-ea043b7e-d1ad-432d-9eb3-959e7afefe6e.PNG" height="600px">


</details>


**使用方法**


插件响应以 `面板` / `评分` / `panel` 开头的消息，下面仅以 `面板` 为例。


 - `面板100123456`
   
   绑定 UID `100123456` 与发送此指令的 QQ，QQ 已被绑定过则会覆盖。
   
   绑定过程将在服务器上缓存该 UID 角色展柜的全部数据，如果已有缓存则仅在缓存失效（1 小时）时更新。
   
 - `面板夜兰` / `面板夜兰100123456` / `面板夜兰@某人`
   
   如果指令未附带 UID，则返回与发送此指令 QQ 绑定的 UID 用户夜兰数据卡片。
   
   如果指令附带 UID，则返回指定 UID 用户数据卡片。
   
   如果指令附带 @QQ，则尝试返回 @QQ 绑定的 UID 用户数据卡片。优先使用未失效的本地缓存。
   
 - `面板刷新` / `面板100123456刷新` / `面板夜兰刷新`
   
   指令后附带 `刷新` 将忽略服务器缓存，同时将最新数据缓存到服务器。
   
   任何指令带来的强制刷新，都会将指定 UID 用户的角色展柜内所有角色数据一起刷新。


*\*大部分指令都可以用空格将关键词分割开来，如果你喜欢的话。*


**特别鸣谢**


[@nonebot/nonebot2](https://github.com/nonebot/nonebot2/) | [@Mrs4s/go-cqhttp](https://github.com/Mrs4s/go-cqhttp) | [@yoimiya-kokomi/miao-plugin](https://github.com/yoimiya-kokomi/miao-plugin) | [@Enka.Network](https://enka.shinshin.moe/)


> - [@Enka.Network](https://enka.shinshin.moe/) 最近服务器负担似乎有些重，时不时会连接不上，插件返回「暂时无法访问数据接口！」是正常情况。
>   
> - 插件的圣遗物评分仅供娱乐，计算规则和卡片样式均来自 [@yoimiya-kokomi/miao-plugin](https://github.com/yoimiya-kokomi/miao-plugin)
