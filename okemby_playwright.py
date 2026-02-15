import asyncio
import os
import random
import requests
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"
LOGIN_API = f"{BASE}/api/auth/login"
STATUS_API = f"{BASE}/api/checkin/status"
CHECKIN_API = f"{BASE}/api/checkin"

ACCOUNTS = os.getenv("OKEMBY_ACCOUNT")
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_tg(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT_ID, "text": msg}, timeout=20)
    except:
        pass

async def run_account(browser, username, password):
    result = f"\n====== {username} ======\n"
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="zh-CN",
        timezone_id="Asia/Shanghai"
    )

    # 屏蔽自动化特征
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3] });
    """)

    page = await context.new_page()
    try:
        # 过 CF 关键：等待页面 + 等待验证
        await page.goto(BASE, timeout=120000)
        await page.wait_for_timeout(random.uniform(8, 12))
        await page.wait_for_selector("body", timeout=60000)
        await page.wait_for_timeout(random.uniform(3, 6))

        # 登录
        login_res = await page.evaluate("""async (d) => {
            const r = await fetch(d.url, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ userName: d.user, password: d.pwd, verificationToken: null })
            });
            return await r.json();
        }""", {"url": LOGIN_API, "user": username, "pwd": password})

        token = login_res.get("token")
        if not token:
            result += "❌ 登录失败\n"
            return result

        result += "✅ 登录成功\n"

        # 状态
        status = await page.evaluate("""async (d) => {
            const r = await fetch(d.url, { headers: { Authorization: "Bearer " + d.token } });
            return await r.json();
        }""", {"url": STATUS_API, "token": token})

        if status.get("hasCheckedInToday"):
            result += f"ℹ️ 今日已签到：{status.get('amount')} RCoin\n"
            return result

        # 签到
        check = await page.evaluate("""async (d) => {
            const r = await fetch(d.url, { method: "POST", headers: { Authorization: "Bearer " + d.token } });
            return await r.json();
        }""", {"url": CHECKIN_API, "token": token})

        if check.get("success"):
            result += f"✅ 签到成功：{check.get('amount')} RCoin"
        else:
            result += f"❌ 签到失败：{check}"

    except Exception as e:
        result += f"❌ 异常：{str(e)[:100]}"
    finally:
        await context.close()
    return result

async def main():
    if not ACCOUNTS:
        print("未配置账号")
        return

    msg = "📢 OKEmby 自动签到（过CF版）\n"
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
            ]
        )

        for acc in ACCOUNTS.split("&"):
            try:
                u, p = acc.split("#", 1)
                msg += await run_account(browser, u, p)
                await asyncio.sleep(random.uniform(20, 40))
            except:
                msg += f"\n❌ 账号解析失败：{acc}"

        await browser.close()

    print(msg)
    send_tg(msg)

if __name__ == "__main__":
    asyncio.run(main())