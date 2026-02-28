# -*- coding: utf-8 -*-
import asyncio
import os
import random
import requests
import json
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


async def login(page, username, password):
    result = await page.evaluate(
        """async ({LOGIN_API, username, password}) => {
            const r = await fetch(LOGIN_API, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    userName: username,
                    password: password,
                    verificationToken: null
                })
            });
            return await r.json();
        }""",
        {"LOGIN_API": LOGIN_API, "username": username, "password": password}
    )

    token = result.get("token")
    user = result.get("user", {})
    balance = float(user.get("rCoin", 0))
    user_id = user.get("id")

    return token, balance, user_id


async def transfer(page, token, amount, to_id):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    result = await page.evaluate(
        """async ({TRANSFER_API, headers, amount, to_id}) => {
            const r = await fetch(TRANSFER_API, {
                method: "POST",
                headers: headers,
                body: JSON.stringify({
                    type: "single",
                    totalAmount: amount,
                    recipientId: to_id
                })
            });
            return await r.json();
        }""",
        {
            "TRANSFER_API": TRANSFER_API,
            "headers": headers,
            "amount": amount,
            "to_id": to_id
        }
    )

    return result


async def main():
    if not ACCOUNTS:
        log("❌ 未设置 OKEMBY_ACCOUNTS2")
        return

    acc_list = ACCOUNTS.split("&")

    if len(acc_list) < 2:
        log("❌ 至少需要2个账号")
        return

    log(f"🔍 账号数量: {len(acc_list)}")
    log("🚀 开始真正完全链式转账\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        for i in range(len(acc_list) - 1):

            sender_user, sender_pass = acc_list[i].split("#")
            receiver_user, receiver_pass = acc_list[i + 1].split("#")

            page = await context.new_page()
            await page.goto(BASE)
            await page.wait_for_timeout(random.randint(2000,4000))

            # 1️⃣ 登录发送方
            token, balance, user_id = await login(page, sender_user, sender_pass)

            if not token:
                log(f"❌ {sender_user} 登录失败")
                await page.close()
                continue

            log(f"💰 {sender_user} 余额 {balance}")

            if balance <= 0.01:
                log(f"⚠ {sender_user} 余额不足，跳过\n")
                await page.close()
                continue

            # 2️⃣ 获取接收方ID
            token2, _, receiver_id = await login(page, receiver_user, receiver_pass)

            if not receiver_id:
                log(f"❌ 无法获取 {receiver_user} ID")
                await page.close()
                continue

            amount = round(balance - 0.01, 2)

            log(f"➡ 转账 {amount} 给 {receiver_user}")

            # 3️⃣ 执行转账
            result = await transfer(page, token, amount, receiver_id)

            if result.get("success") or result.get("message") == "发送成功":
                log("✅ 转账成功")

                # 4️⃣ 再次确认余额
                token3, new_balance, _ = await login(page, sender_user, sender_pass)

                if abs(new_balance - 0.01) < 0.02:
                    log("✔ 余额确认只剩 0.01\n")
                else:
                    log(f"⚠ 异常余额: {new_balance}\n")
            else:
                log(f"❌ 转账失败: {result.get('message')}\n")

            await page.close()
            await asyncio.sleep(random.randint(5,10))

        await browser.close()

    log("🎯 链式执行完成")
    send_tg("\n".join(LOG))


if __name__ == "__main__":
    asyncio.run(main())
