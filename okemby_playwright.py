import asyncio
import os
import random
import requests
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"
LOGIN_API = f"{BASE}/api/auth/login"
TRANSFER_API = f"{BASE}/api/redpacket"

ACCOUNTS = os.getenv("OKEMBY_ACCOUNT")
TG_TOKEN = os.getenv("TG_CHAT_ID")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

CHAIN_USERS = [
    650, 647, 648, 440, 646,
    645, 649, 424, 644, 390
]


def send_tg(msg):
    if TG_TOKEN and TG_CHAT_ID:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT_ID, "text": msg},
            timeout=20
        )


async def login_and_get_info(username, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(BASE, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(random.randint(4, 8) * 1000)

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
        user_info = login_data.get("user", {})
        balance = float(user_info.get("rCoin", 0))

        cookies = await context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        await browser.close()
        return token, balance, cookie_str


def try_transfer(token, cookie_str, amount, recipient_id):
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0",
        "Cookie": cookie_str,
        "Content-Type": "application/json"
    }

    data = {
        "type": "single",
        "totalAmount": amount,
        "recipientId": recipient_id
    }

    return requests.post(
        TRANSFER_API,
        headers=headers,
        json=data
    ).json()


async def main():
    final_msg = "📢 OKEmby 自动跳过失败链式归集结果\n"
    acc_list = ACCOUNTS.split("&")

    # ========= 第一阶段：链式转账 =========
    for i, acc in enumerate(acc_list):
        username, password = acc.split("#")
        current_id = CHAIN_USERS[i]

        final_msg += f"\n====== {username} ({current_id}) ======\n"

        token, balance, cookie_str = await login_and_get_info(username, password)

        if not token:
            final_msg += "❌ 登录失败\n"
            continue

        final_msg += f"💰 当前余额: {balance}\n"

        if balance <= 0.05:
            final_msg += "⚠ 余额过低，跳过\n"
            continue

        transfer_amount = round(balance - 0.01, 2)
        success = False

        for next_index in range(i + 1, len(CHAIN_USERS)):
            recipient_id = CHAIN_USERS[next_index]
            await asyncio.sleep(random.randint(3, 6))

            result = try_transfer(token, cookie_str, transfer_amount, recipient_id)

            if result.get("success") or result.get("message") == "发送成功":
                final_msg += f"➡ 成功转 {transfer_amount} → {recipient_id}\n"
                success = True
                break
            else:
                final_msg += f"⚠ 转给 {recipient_id} 失败，尝试下一个\n"

        if not success:
            final_msg += "❌ 本账号未成功转出\n"

    # ========= 第二阶段：最终余额检查 =========
    final_msg += "\n📊 ===== 最终余额检查 =====\n"

    total_balance = 0

    for i, acc in enumerate(acc_list):
        username, password = acc.split("#")
        token, balance, _ = await login_and_get_info(username, password)

        final_msg += f"{username} ({CHAIN_USERS[i]}) : {balance}\n"
        total_balance += balance

    final_msg += f"\n💎 所有账号总余额: {round(total_balance,2)} RCoin\n"

    print(final_msg)
    send_tg(final_msg)


if __name__ == "__main__":
    asyncio.run(main())
