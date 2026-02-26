import asyncio
import os
import random
import requests
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"




ACCOUNTS = os.getenv("OKEMBY_ACCOUNT")
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")


def send_tg(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("⚠ 未配置 TG")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg},
            timeout=20
        )
    except:
        pass


async def human_behavior(page):
    # 随机鼠标移动
    for _ in range(random.randint(5, 12)):
        await page.mouse.move(
            random.randint(100, 1200),
            random.randint(100, 800),
            steps=random.randint(5, 20)
        )
        await asyncio.sleep(random.uniform(0.2, 0.8))

    # 随机滚动
    for _ in range(random.randint(2, 5)):
        await page.mouse.wheel(0, random.randint(200, 600))
        await asyncio.sleep(random.uniform(0.5, 1.2))


async def run_account(browser, username, password):
    result = f"\n====== {username} ======\n"
    context = await browser.new_context()
    page = await context.new_page()












    try:
        # 打开首页（触发 CF）
        await page.goto(BASE, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(random.uniform(4, 8))

        await human_behavior(page)

        # 登录页
        await page.goto(f"{BASE}/login")
        await page.fill('input[name="userName"]', username)
        await asyncio.sleep(random.uniform(0.5, 1.5))
        await page.fill('input[name="password"]', password)
        await asyncio.sleep(random.uniform(0.5, 1.5))

        await human_behavior(page)

        await page.click('button:has-text("登录")')
        await asyncio.sleep(random.uniform(6, 10))

        if "login" in page.url:
            await context.close()
            return result + "❌ 登录失败\n"

        result += "✅ 登录成功\n"

        # 进入 dashboard
        await page.goto(f"{BASE}/dashboard")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(random.uniform(6, 10))

        await human_behavior(page)

        # 等待 Turnstile 渲染
        await asyncio.sleep(random.uniform(5, 10))


        # 查找签到卡片
        try:
            card = await page.wait_for_selector(
                '[data-checkin-card="default"]',
                timeout=20000
            )

            box = await card.bounding_box()

            # 模拟鼠标移动到按钮
            await page.mouse.move(
                box["x"] + box["width"] / 2,
                box["y"] + box["height"] / 2,
                steps=25
            )

            await asyncio.sleep(random.uniform(1, 2))

            await page.mouse.click(
                box["x"] + box["width"] / 2,
                box["y"] + box["height"] / 2
            )

            await asyncio.sleep(random.uniform(5, 8))

            result += "🎉 已尝试点击签到\n"

        except:
            result += "⚠ 未找到签到按钮（可能已签到或被拦截）\n"

    except Exception as e:
        result += f"❌ 异常: {e}\n"
        await page.screenshot(path=f"{username}_error.png")

    await context.close()
    return result


async def main():
    if not ACCOUNTS:
        print("❌ 未配置 OKEMBY_ACCOUNT")
        return

    final_msg = "📢 OKEmby GitHub 强化拟人签到\n"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"

            ]
        )

        accounts = ACCOUNTS.split("&")

        for i, acc in enumerate(accounts):
            username, password = acc.split("#")

            if i > 0:
                delay = random.randint(30, 90)
                print(f"⏳ 等待 {delay} 秒避免风控...")
                await asyncio.sleep(delay)

            res = await run_account(browser, username, password)
            final_msg += res

        await browser.close()

    print(final_msg)
    send_tg(final_msg)


if __name__ == "__main__":
    asyncio.run(main())
