import asyncio
import os
import random
import requests
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"
LOGIN_API = f"{BASE}/api/auth/login"
CHECKIN_API = f"{BASE}/api/checkin"

ACCOUNTS = os.getenv("OKEMBY_ACCOUNT")  # user1#pass1&user2#pass2
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")


def send_tg(msg: str):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("⚠ 未配置 TG")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": msg},
            timeout=20
        )
    except Exception as e:
        print("TG 发送失败:", e)


async def run_account(browser, username, password):
    result = f"\n====== {username} ======\n"

    context = await browser.new_context()
    page = await context.new_page()

    try:
        # 1️⃣ 打开首页（触发 CF）
        await page.goto(BASE, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(random.randint(5000, 9000))

        # 2️⃣ 登录（浏览器内 fetch）
        login = await page.evaluate(
            """async ({url, username, password}) => {
                const r = await fetch(url, {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        userName: username,
                        password: password,
                        verificationToken: null
                    })
                });
                return await r.json();
            }""",
            {
                "url": LOGIN_API,
                "username": username,
                "password": password
            }
        )

        token = login.get("token")
        if not token:
            await context.close()
            return result + "❌ 登录失败\n"

        result += "✅ 登录成功\n"

        # 3️⃣ 进入 dashboard 生成 Turnstile token
        await page.goto(f"{BASE}/dashboard", timeout=60000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(6000)

        # 4️⃣ 获取 cf-turnstile-response
        verification_token = await page.evaluate("""
            () => {
                const el = document.querySelector('input[name="cf-turnstile-response"]');
                return el ? el.value : null;
            }
        """)

        if not verification_token:
            await context.close()
            return result + "❌ 未获取到人机验证 token（IP 可能被识别）\n"

        result += "✅ 获取人机验证 token 成功\n"

        # 5️⃣ 浏览器内发签到请求
        checkin = await page.evaluate(
            """async ({url, token, vtoken}) => {
                const r = await fetch(url, {
                    method: "POST",
                    headers: {
                        "Authorization": "Bearer " + token,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        verificationToken: vtoken
                    })
                });
                return await r.json();
            }""",
            {
                "url": CHECKIN_API,
                "token": token,
                "vtoken": verification_token
            }
        )

        if checkin.get("success"):
            result += f"🎉 签到成功 +{checkin.get('amount')} RCoin\n"
        else:
            result += f"❌ 签到失败: {checkin.get('message')}\n"

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
    send_tg(final_msg)


if __name__ == "__main__":
    asyncio.run(main())