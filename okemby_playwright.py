import asyncio
import os
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
        print("⚠ 未配置 TG")
        return
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_CHAT_ID, "text": msg},
        timeout=20
    )


async def run_account(username, password):
    result = f"\n====== {username} ======\n"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # 1️⃣ 打开首页过 CF
        await page.goto(BASE, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(5000)

        # 2️⃣ API 登录（浏览器环境）
        login_data = await page.evaluate(f"""
        async () => {{
            const r = await fetch("{LOGIN_API}", {{
                method: "POST",
                headers: {{ "Content-Type": "application/json" }},
                body: JSON.stringify({{
                    userName: "{username}",
                    password: "{password}",
                    verificationToken: null
                }})
            }});
            return await r.json();
        }}
        """)

        token = login_data.get("token")
        if not token:
            await browser.close()
            return result + f"❌ 登录失败\n"

        result += "✅ 登录成功\n"

        # 3️⃣ 取浏览器 cookie
        cookies = await context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0",
            "Cookie": cookie_str
        }

        # 4️⃣ 查询签到状态
        status = requests.get(STATUS_API, headers=headers).json()

        if status.get("hasCheckedInToday"):
            result += f"ℹ 今日已签到 {status.get('amount')} RCoin\n"
            await browser.close()
            return result

        # 5️⃣ 执行签到
        checkin = requests.post(CHECKIN_API, headers=headers).json()

        if checkin.get("success"):
            result += f"✅ 签到成功 {checkin.get('amount')} RCoin\n"
        else:
            result += f"❌ 签到失败\n"

        await browser.close()
        return result


async def main():
    final_msg = "📢 OKEmby 自动签到结果\n"

    for acc in ACCOUNTS.split("&"):
        username, password = acc.split("#")
        res = await run_account(username, password)
        final_msg += res

    print(final_msg)
    send_tg(final_msg)


if __name__ == "__main__":
    asyncio.run(main())