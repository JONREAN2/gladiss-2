import asyncio
import os
import random
import requests
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"
LOGIN_URL = f"{BASE}/login"

TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")
ACCOUNTS = os.getenv("OKEMBY_ACCOUNT")  # user1#pass1&user2#pass2

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
            # 1️⃣ 打开首页触发CF
            print("🌐 访问首页触发CF")
            await page.goto(BASE, timeout=60000)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(random.randint(5000,8000))

            # 2️⃣ 直接进入登录页
            print("🔐 直接访问登录页")
            await page.goto(LOGIN_URL, timeout=60000)
            await page.wait_for_load_state("networkidle")

            # 3️⃣ 等待输入框
            await page.wait_for_selector("input[type='password']", timeout=60000)

            # 4️⃣ 填写账号密码
            await page.fill("input[type='text']", username)
            await page.fill("input[type='password']", password)

            # 点击登录按钮（匹配按钮而不是a标签）
            await page.locator("button[type='submit']").click()

            await page.wait_for_timeout(random.randint(5000,7000))

            # 5️⃣ 浏览器内 fetch 签到
            print("🚀 浏览器环境调用签到接口")
            retries = 3
            for i in range(retries):
                try:
                    result_json = await page.evaluate("""
                    async () => {
                        const res = await fetch('/api/checkin', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'}
                        });
                        return await res.json();
                    }
                    """)
                    if result_json.get("success"):
                        amount = result_json.get("amount", 0)
                        result += f"✅ 签到成功，获得 {amount} RCoin\n"
                        break
                    else:
                        result += f"⚠ 第{i+1}次失败: {result_json.get('message')}\n"
                except Exception as e:
                    result += f"⚠ 第{i+1}次异常: {e}\n"

        except Exception as e:
            print("❌ 异常:", e)
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