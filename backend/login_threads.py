from __future__ import annotations

import asyncio
from pathlib import Path

from playwright.async_api import async_playwright


SESSION_DIR = Path(__file__).resolve().parent / ".threads-session"


async def main() -> None:
    async with async_playwright() as playwright:
        context = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=False,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://www.threads.net/", wait_until="domcontentloaded")
        print("請在開啟的 Chromium 視窗完成 Threads 登入。")
        print("登入完成後，回到這個終端機按 Enter 保存 Session。")
        await asyncio.to_thread(input)
        await context.close()
        print(f"Threads Session 已保存至：{SESSION_DIR}")


if __name__ == "__main__":
    asyncio.run(main())