import asyncio
import os
import random
import requests
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"
LOGIN_API = f"{BASE}/api/auth/login"
DASHBOARD_URL = f"{BASE}/dashboard"
CHECKIN_API_PATTERN = "**/api/checkin"

TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
ACCOUNTS = os.getenv("OKEMBY_ACCOUNT")  # 格式: user1#pass1&user2#pass2

def send_tg(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("⚠ 未配置 TG")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT_ID, "text": msg},
            timeout=20
        )
    except Exception as e:
        print("TG 发送失败:", e)

async def run_account(username, password):
    result = f"\n====== {username} ======\n"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 1️⃣ 访问首页触发 CF
            print("🌐 访问首页")
            await page.goto(BASE, timeout=60000)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(random.randint(4000,7000))

            # 2️⃣ 浏览器内 API 登录
            print("🔐 API 登录")
            login_res = await page.evaluate(f"""
            async () => {{
                const res = await fetch("{LOGIN_API}", {{
                    method: "POST",
                    headers: {{"Content-Type": "application/json"}},
                    body: JSON.stringify({{
                        "userName": "{username}",
                        "password": "{password}",
                        "verificationToken": null
                    }})
                }});
                return await res.json();
            }}
            """)

            token = login_res.get("token")
            if not token:
                result += f"❌ 登录失败: {login_res.get('message')}\n"
                return result
            result += "✅ 登录成功\n"

            # 3️⃣ 进入 dashboard
            print("📊 进入 dashboard")
            await page.goto(DASHBOARD_URL, timeout=60000)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(random.randint(3000,6000))

            # 4️⃣ 点击图标+文字签到按钮
            print("🚀 点击签到按钮")
            retries = 3
            for i in range(retries):
                try:
                    async with page.expect_response(CHECKIN_API_PATTERN, timeout=15000) as response_info:
                        # ✅ 终极稳定点击方式
                        await page.locator("button:has-text('签到')").first.click()

                    response = await response_info.value
                    data = await response.json()

                    if data.get("success"):
                        amount = data.get("amount", 0)
                        result += f"✅ 签到成功，获得 {amount} RCoin\n"
                        break
                    else:
                        msg = data.get("message")
                        result += f"⚠ 第{i+1}次失败: {msg}\n"

                    await page.wait_for_timeout(3000)

                except Exception as e:
                    result += f"⚠ 第{i+1}次异常: {e}\n"
                    await page.wait_for_timeout(3000)

        except Exception as e:
            result += f"❌ 异常: {e}\n"
            await page.screenshot(path=f"{username}_error.png")
            print(f"📸 已保存截图 {username}_error.png")

        await browser.close()

    return result

async def main():
    if not ACCOUNTS:
        print("❌ 未配置 OKEMBY_ACCOUNT")
        return

    final_msg = "📢 OKEmby 自动签到结果\n"

    for acc in ACCOUNTS.split("&"):
        try:
            username, password = acc.split("#")
        except:
            final_msg += f"⚠ 格式错误: {acc}\n"
            continue
        res = await run_account(username, password)
        final_msg += res

    print(final_msg)
    send_tg(final_msg)

if __name__ == "__main__":
    asyncio.run(main())