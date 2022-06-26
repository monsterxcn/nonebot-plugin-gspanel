# https://github.com/HibiKier/zhenxun_bot/blob/main/utils/browser.py

from typing import Optional

from nonebot import get_driver
from nonebot.drivers import Driver
from nonebot.log import logger
from playwright.async_api import Browser, async_playwright

driver: Driver = get_driver()
_browser: Optional[Browser] = None


async def init(**kwargs) -> Optional[Browser]:
    global _browser
    browser = await async_playwright().start()
    try:
        _browser = await browser.chromium.launch(**kwargs)
        return _browser
    except Exception as e:
        logger.warning(f"启动 Chromium 发生错误 {type(e)}：{e}")
    return None


async def get_browser(**kwargs) -> Optional[Browser]:
    return _browser or await init(**kwargs)
