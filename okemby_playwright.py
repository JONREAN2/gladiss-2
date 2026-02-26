import asyncio
import os
import random
import requests
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"
LOGIN_API = f"{BASE}/api/auth/login"
DASHBOARD_URL = f"{BASE}/dashboard"
CHECKIN_API_PATTERN = "**/api/checkin"

# TG Bot 配置
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

# 多账号配置，格式: user1#pass1&user2#pass2
ACCOUNTS = os.getenv("OKEMBY_ACCOUNT")  

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

async def wait_loading_end(page):
    """等待页面动画/加载结束"""
    try:
        while await page.evaluate("window.isLoadingAnimating ? window.isLoadingAnimating() : false"):
            await page.wait_for_timeout(500)
    except:
        pass

async def run_account(username, password):
    result = f"\n====== {username} ======\n"
@@ -45,99 +32,75 @@ async def run_account(username, password):
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 1️⃣ 访问首页触发 CF
            print("🌐 访问首页")
            await page.goto(BASE, timeout=60000)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(random.randint(4000,7000))
            await wait_loading_end(page)

            # 2️⃣ API 登录
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
            await wait_loading_end(page)

            # 4️⃣ 判断是否已签到
            if await page.locator("text=今日已签到").count() > 0:
                result += "ℹ 今日已签到，无需再次操作\n"
                return result

            # 5️⃣ 点击签到卡片
            print("🚀 点击签到卡片")
            retries = 3
            for i in range(retries):
                try:
                    await page.wait_for_selector('[data-checkin-card="default"]', state="attached", timeout=20000)

                    async with page.expect_response(CHECKIN_API_PATTERN, timeout=15000) as response_info:
                        await page.locator('[data-checkin-card="default"]').click(force=True)

                    response = await response_info.value
                    data = await response.json()

                    if data.get("success"):
                        amount = data.get("amount", 0)
                        result += f"✅ 签到成功，获得 {amount} RCoin\n"
                        break
                    else:
                        result += f"⚠ 第{i+1}次失败: {data.get('message')}\n"
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
