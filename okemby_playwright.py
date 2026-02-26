import asyncio
import os
import random
import requests
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"
LOGIN_API = f"{BASE}/api/auth/login"
STATUS_API = f"{BASE}/api/checkin/status"
CHECKIN_API = f"{BASE}/api/checkin"
TRANSFER_API = f"{BASE}/api/redpacket"

ACCOUNTS = os.getenv("OKEMBY_ACCOUNT")
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

TARGET_USER_ID = 647   # 🔥 改成你要归集的用户ID


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

        # 过CF
        await page.goto(BASE, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(random.randint(4, 8) * 1000)

        # 登录
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
            return result + "❌ 登录失败\n"

        result += "✅ 登录成功\n"

        user_info = login_data.get("user", {})
        balance = float(user_info.get("rCoin", 0))
        result += f"💰 当前余额: {balance} RCoin\n"

        if balance <= 0.05:
            result += "⚠ 余额太少，不转账\n"
            await browser.close()
            return result

        cookies = await context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Mozilla/5.0",
            "Cookie": cookie_str,
            "Content-Type": "application/json"
        }

        await asyncio.sleep(random.randint(3, 6))

        # 保留0.01
        transfer_amount = round(balance - 0.01, 2)

        transfer_data = {
            "type": "single",
            "totalAmount": transfer_amount,
            "recipientId": TARGET_USER_ID
        }

        transfer = requests.post(
            TRANSFER_API,
            headers=headers,
            json=transfer_data
        ).json()

        if transfer.get("success") or transfer.get("message") == "发送成功":
            result += f"💸 已转账 {transfer_amount} RCoin → 用户 {TARGET_USER_ID}\n"
        else:
            result += f"❌ 转账失败: {transfer}\n"

        await browser.close()
        return result


async def main():
    final_msg = "📢 OKEmby 自动归集结果\n"

    for acc in ACCOUNTS.split("&"):
        username, password = acc.split("#")
        res = await run_account(username, password)
        final_msg += res

    print(final_msg)
    send_tg(final_msg)


if __name__ == "__main__":
    asyncio.run(main())
