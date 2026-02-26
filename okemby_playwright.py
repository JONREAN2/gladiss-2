# -*- coding: utf-8 -*-
import asyncio
import os
import random
import requests
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"
LOGIN_API = BASE + "/api/auth/login"   # 🔥 修正登录接口
TRANSFER_API = BASE + "/api/redpacket"

ACCOUNTS = os.getenv("OKEMBY_ACCOUNTS")
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

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

LOG = []  # 日志缓存

def log(msg):
    print(msg)
    LOG.append(str(msg))

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

        # 🔥 修正返回字段
        token = login_data.get("token")
        user = login_data.get("user", {})
        balance = float(user.get("rCoin", 0))
        user_id = user.get("id")

        cookies = await context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

        await browser.close()
        return token, balance, cookie_str, user_id

# 转币
async def transfer(token, cookie_str, amount, to_id):
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

# 校验ID
async def verify_accounts(acc_list):
    log("🔍 校验账号ID中...")

    for i, acc in enumerate(acc_list):
        username, password = acc.split("#")
        try:
            token, balance, cookie_str, real_id = await login_and_get_info(username, password)
        except:
            log(f"❌ {username} 登录失败")
            return False

        if real_id != CHAIN_USERS[i]:
            log(f"❌ ID不匹配: {username}")
            log(f"期望ID: {CHAIN_USERS[i]} 实际ID: {real_id}")
            return False

        log(f"✅ {username} ID正确 ({real_id})")

    log("🎉 全部ID校验通过\n")
    return True

async def main():
    if not ACCOUNTS:
        log("未设置 OKEMBY_ACCOUNTS")
        send_tg("\n".join(LOG))
        return

    acc_list = ACCOUNTS.split("&")

    if len(acc_list) != len(CHAIN_USERS):
        log("账号数量与ID链数量不一致")
        send_tg("\n".join(LOG))
        return

    ok = await verify_accounts(acc_list)
    if not ok:
        log("⛔ ID校验失败，停止执行")
        send_tg("\n".join(LOG))
        return

    log("🚀 开始链式转账\n")

    for i in range(len(acc_list) - 1):
        username, password = acc_list[i].split("#")
        to_id = CHAIN_USERS[i + 1]

        try:
            token, balance, cookie_str, user_id = await login_and_get_info(username, password)
        except:
            log(f"❌ {username} 登录失败，跳过")
            continue

        if balance <= 0:
            log(f"⚠ {username} 余额为0，跳过")
            continue

        log(f"💰 {username} 余额 {balance} → 转给 {to_id}")

        result = await transfer(token, cookie_str, balance, to_id)

        if result.get("success") or result.get("message") == "发送成功":
            log("✅ 转账成功\n")
        else:
            log(f"⚠ 转账失败: {result.get('message')}\n")

        await asyncio.sleep(random.randint(5, 10))

    log("\n🔎 最终余额检查\n")

    for i, acc in enumerate(acc_list):
        username, password = acc.split("#")
        try:
            token, balance, cookie_str, user_id = await login_and_get_info(username, password)
            log(f"{username} ({user_id}) 余额: {balance}")
        except:
            log(f"{username} 查询失败")

    log("\n🎯 执行结束")
    send_tg("\n".join(LOG))

if __name__ == "__main__":
    asyncio.run(main())
