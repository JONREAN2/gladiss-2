import asyncio
import os
import random
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"
LOGIN_API = f"{BASE}/api/auth/login"
STATUS_API = f"{BASE}/api/checkin/status"
CHECKIN_API = f"{BASE}/api/checkin"

ACCOUNTS = os.getenv("OKEMBY_ACCOUNT")
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")


async def send_tg(page, msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("⚠ 未配置 TG")
        return

    await page.evaluate(f"""
    async () => {{
        await fetch("https://api.telegram.org/bot{TG_TOKEN}/sendMessage", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{
                chat_id: "{TG_CHAT_ID}",
                text: `{msg}`
            }})
        }});
    }}
    """)


async def run_account(browser, username, password):
    result = f"\n====== {username} ======\n"

    context = await browser.new_context()
    page = await context.new_page()

    try:
        # 1️⃣ 访问首页过 CF
        await page.goto(BASE, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(random.randint(5000, 9000))

        # 2️⃣ 浏览器内登录
        login = await page.evaluate(f"""
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

        token = login?.token || login.token

        if not token:
            return result + "❌ 登录失败\n"

        result += "✅ 登录成功\n"

        # 3️⃣ 查询状态（浏览器内）
        status = await page.evaluate(f"""
        async () => {{
            const r = await fetch("{STATUS_API}", {{
                headers: {{
                    "Authorization": "Bearer {token}"
                }}
            }});
            return await r.json();
        }}
        """)

        if status.get("hasCheckedInToday"):
            result += f"ℹ 今日已签到 {status.get('amount')} RCoin\n"
            return result

        # 4️⃣ 真正签到（浏览器内执行，避免CF二次挑战）
        checkin = await page.evaluate(f"""
        async () => {{
            const r = await fetch("{CHECKIN_API}", {{
                method: "POST",
                headers: {{
                    "Authorization": "Bearer {token}"
                }}
            }});
            return await r.json();
        }}
        """)

        if checkin.get("success"):
            result += f"✅ 签到成功 {checkin.get('amount')} RCoin\n"
        else:
            result += "❌ 签到失败（可能触发CF）\n"

    except Exception as e:
        result += f"❌ 异常: {e}\n"
        await page.screenshot(path=f"{username}_error.png")

    await context.close()
    return result


async def main():
    if not ACCOUNTS:
        print("❌ 未配置 OKEMBY_ACCOUNT")
        return

    final_msg = "📢 OKEmby 自动签到结果\n"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        accounts = ACCOUNTS.split("&")

        for i, acc in enumerate(accounts):
            username, password = acc.split("#")

            if i > 0:
                delay = random.randint(20, 60)
                print(f"⏳ 等待 {delay} 秒避免风控...")
                await asyncio.sleep(delay)

            res = await run_account(browser, username, password)
            final_msg += res

        await browser.close()

    print(final_msg)

    # 用浏览器发TG（避免requests暴露IP特征）
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await send_tg(page, final_msg)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())