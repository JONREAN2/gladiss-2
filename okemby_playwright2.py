# -*- coding: utf-8 -*-
import asyncio
import os
import random
import requests
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"
LOGIN_API = f"{BASE}/api/auth/login"
TRANSFER_API = f"{BASE}/api/redpacket"

ACCOUNTS = os.getenv("OKEMBY_ACCOUNTS2")

TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

LOG = []

def log(msg):
    print(msg)
    LOG.append(str(msg))

def send_tg(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT_ID, "text": msg},
            timeout=20
        )
    except:
        pass

async def login(username, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(BASE, timeout=60000)
        await page.wait_for_timeout(random.randint(3, 6) * 1000)

        result = await page.evaluate(f"""
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

        token = result.get("token")
        user = result.get("user", {})
        balance = float(user.get("rCoin", 0))
        user_id = user.get("id")

        cookies = await context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        await browser.close()
        return token, balance, cookie_str, user_id

async def transfer(token, cookie_str, balance, to_id):
    if balance <= 0.01:
        return {"success": False, "message": "余额不足"}

    amount = round(balance - 0.01, 2)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
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
                    type: "single",
                    totalAmount: {amount},
                    recipientId: {to_id}
                }})
            }});
            return await r.json();
        }}
        """)

        await browser.close()
        return result

async def main():
    if not ACCOUNTS:
        log("❌ 未设置 OKEMBY_ACCOUNTS2")
        send_tg("\n".join(LOG))
        return

    acc_list = ACCOUNTS.split("&")

    if len(acc_list) < 2:
        log("❌ 至少需要2个账号")
        send_tg("\n".join(LOG))
        return

    log(f"🔍 账号数量: {len(acc_list)}\n")

    account_infos = []

    # 登录所有账号
    for acc in acc_list:
        username, password = acc.split("#")
        try:
            token, balance, cookie_str, user_id = await login(username, password)
            log(f"✅ {username} ID:{user_id} 余额:{balance}")
            account_infos.append({
                "username": username,
                "password": password,
                "token": token,
                "balance": balance,
                "cookie": cookie_str,
                "user_id": user_id
            })
        except:
            log(f"❌ {username} 登录失败")

    log("\n🚀 开始链式转账\n")

    # 链式转账
    for i in range(len(account_infos) - 1):

        sender = account_infos[i]
        receiver = account_infos[i + 1]

        if sender["balance"] <= 0.01:
            log(f"⚠ {sender['username']} 余额不足，跳过")
            continue

        log(f"💰 {sender['username']} ➜ {receiver['username']}")

        try:
            result = await transfer(
                sender["token"],
                sender["cookie"],
                sender["balance"],
                receiver["user_id"]
            )

            if result.get("success") or result.get("message") == "发送成功":
                log("✅ 成功\n")
            else:
                log(f"⚠ 失败: {result.get('message')}\n")

        except:
            log("⚠ 转账异常，继续下一笔\n")

        await asyncio.sleep(random.randint(5, 10))

    log("\n🎯 链式转账完成")
    send_tg("\n".join(LOG))

if __name__ == "__main__":
    asyncio.run(main())