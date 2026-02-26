# -*- coding: utf-8 -*-
import asyncio
import os
import random
import requests
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"
LOGIN_API = f"{BASE}/api/auth/login"
TRANSFER_API = f"{BASE}/api/redpacket"

ACCOUNTS = os.getenv("OKEMBY_ACCOUNTS2")  # 10个账号 username#password & ... 
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

TARGET_USERNAME = "jonrean"  # 最终归集到这个账号
TARGET_USER_ID = None  # 运行时获取

LOG = []

def log(msg):
    print(msg)
    LOG.append(str(msg))

def send_tg(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        log("⚠ 未配置 TG")
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
            data={"chat_id": TG_CHAT_ID, "text": msg},
            timeout=20
        )
    except Exception as e:
        log(f"TG 发送失败: {e}")

# 登录并获取 token + 余额 + userid
async def login_and_get_info(username, password):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto(BASE, timeout=60000)
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(random.randint(3,6)*1000)

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
        user = login_data.get("user", {})
        balance = float(user.get("rCoin", 0))
        user_id = user.get("id")
        cookies = await context.cookies()
        cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
        await browser.close()
        return token, balance, cookie_str, user_id

# 转币，保留0.01
async def transfer(token, cookie_str, balance, to_id):
    if balance <= 0.01:
        return {"success": False, "message": "余额太少"}
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
        log("未设置 OKEMBY_ACCOUNTS")
        send_tg("\n".join(LOG))
        return

    acc_list = ACCOUNTS.split("&")

    # 先获取所有账号的真实ID，顺便找出 jonrean 的 ID
    account_infos = []
    for acc in acc_list:
        username, password = acc.split("#")
        try:
            token, balance, cookie_str, user_id = await login_and_get_info(username, password)
            account_infos.append({
                "username": username,
                "password": password,
                "token": token,
                "balance": balance,
                "cookie": cookie_str,
                "user_id": user_id
            })
            log(f"✅ 登录成功: {username} ({user_id}) 余额: {balance})")
            if username == TARGET_USERNAME:
                global TARGET_USER_ID
                TARGET_USER_ID = user_id
        except:
            log(f"❌ 登录失败: {username}")

    if not TARGET_USER_ID:
        log("⛔ 未找到 jonrean 用户 ID，停止执行")
        send_tg("\n".join(LOG))
        return

    log("🚀 开始归集转账\n")

    # 按顺序转账，最后归集到 jonrean
    for info in account_infos:
        if info["username"] == TARGET_USERNAME:
            continue  # 跳过 jonrean 自己
        if info["balance"] <= 0:
            log(f"⚠ {info['username']} 余额为0，跳过")
            continue
        log(f"💰 {info['username']} 余额 {info['balance']} → 转给 {TARGET_USERNAME} ({TARGET_USER_ID})")
        result = await transfer(info["token"], info["cookie"], info["balance"], TARGET_USER_ID)
        if result.get("success") or result.get("message") == "发送成功":
            log(f"✅ 转账成功")
        else:
            log(f"⚠ 转账失败: {result.get('message')}")
        await asyncio.sleep(random.randint(5,10))

    log("\n🔎 最终余额检查")
    for info in account_infos:
        try:
            token, balance, cookie_str, user_id = await login_and_get_info(info["username"], info["password"])
            log(f"{info['username']} ({user_id}) 余额: {balance}")
        except:
            log(f"{info['username']} 查询失败")

    log("\n🎯 执行结束")
    send_tg("\n".join(LOG))

if __name__ == "__main__":
    asyncio.run(main())
