# -*- coding: utf-8 -*-
import asyncio
import os
import random
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"
LOGIN_API = BASE + "/api/Users/AuthenticateByName"
TRANSFER_API = BASE + "/api/RedPacket/Send"

ACCOUNTS = os.getenv("OKEMBY_ACCOUNTS")

# 链式顺序（必须与账号顺序对应）
CHAIN_USERS = [
    650,  # jonrean
    647,  # plsmean
    648,  # jonrea
    440,  # showlo3
    646,  # komeanx
    645,  # b11871457
    649,  # K_lomn
    424,  # show
    644,  # f55i933
    390   # showlo
]


# 登录并获取 token + 余额 + id
async def login_and_get_info(username, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(BASE, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(random.randint(3, 6) * 1000)

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

        token = login_data.get("AccessToken")
        user = login_data.get("User", {})
        balance = float(user.get("rCoin", 0))
        user_id = user.get("Id")

        cookies = await context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        await browser.close()

        return token, balance, cookie_str, user_id


# 转币
async def transfer(token, cookie_str, amount, to_id):
    headers = {
        "Content-Type": "application/json",
        "X-Emby-Token": token,
        "Cookie": cookie_str
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(BASE)
        await page.wait_for_timeout(2000)

        result = await page.evaluate(f"""
        async () => {{
            const r = await fetch("{TRANSFER_API}", {{
                method: "POST",
                headers: {headers},
                body: JSON.stringify({{
                    userId: {to_id},
                    amount: {amount}
                }})
            }});
            return await r.json();
        }}
        """)

        await browser.close()
        return result


# 校验ID
async def verify_accounts(acc_list):
    print("🔍 校验账号ID中...")

    for i, acc in enumerate(acc_list):
        username, password = acc.split("#")
        token, balance, cookie_str, real_id = await login_and_get_info(username, password)

        if real_id != CHAIN_USERS[i]:
            print(f"❌ ID不匹配: {username}")
            print(f"期望ID: {CHAIN_USERS[i]} 实际ID: {real_id}")
            return False

        print(f"✅ {username} ID正确 ({real_id})")

    print("🎉 全部ID校验通过\n")
    return True


async def main():
    if not ACCOUNTS:
        print("未设置 OKEMBY_ACCOUNTS")
        return

    acc_list = ACCOUNTS.split("&")

    if len(acc_list) != len(CHAIN_USERS):
        print("账号数量与ID链数量不一致")
        return

    # 先校验ID
    ok = await verify_accounts(acc_list)
    if not ok:
        print("⛔ ID校验失败，停止执行")
        return

    print("🚀 开始链式转账\n")

    for i in range(len(acc_list) - 1):

        username, password = acc_list[i].split("#")
        to_id = CHAIN_USERS[i + 1]

        try:
            token, balance, cookie_str, user_id = await login_and_get_info(username, password)
        except:
            print(f"❌ {username} 登录失败，跳过")
            continue

        if balance <= 0:
            print(f"⚠ {username} 余额为0，跳过")
            continue

        print(f"💰 {username} 余额 {balance} → 转给 {to_id}")

        result = await transfer(token, cookie_str, balance, to_id)

        if result.get("success"):
            print(f"✅ 转账成功\n")
        else:
            print(f"⚠ 转账失败: {result.get('message')}\n")

        await asyncio.sleep(random.randint(5, 10))

    print("\n🔎 最终余额检查\n")

    for i, acc in enumerate(acc_list):
        username, password = acc.split("#")
        try:
            token, balance, cookie_str, user_id = await login_and_get_info(username, password)
            print(f"{username} ({user_id}) 余额: {balance}")
        except:
            print(f"{username} 查询失败")

    print("\n🎯 执行结束")


if __name__ == "__main__":
    asyncio.run(main())
