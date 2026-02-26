import asyncio
import os
import requests
from playwright.async_api import async_playwright

BASE = "https://www.okemby.com"
LOGIN_API = f"{BASE}/api/auth/login"
USER_API = f"{BASE}/api/user"
ACCOUNTS = os.getenv("OKEMBY_ACCOUNT")
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_tg(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        print("⚠ 未配置 TG")
        return
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        data={"chat_id": TG_CHAT_ID, "text": msg},
        timeout=20
    )

async def get_user_balance(headers):
    """查询用户钱包余额"""
    try:
        response = requests.get(USER_API, headers=headers, timeout=10)
        data = response.json()
        
        if response.status_code == 200 and data.get("success"):
            balance = data.get("data", {}).get("balance") or data.get("balance") or 0
            return balance
        return None
    except Exception as e:
        print(f"查询余额异常: {str(e)}")
        return None

async def run_account(username, password):
    result = f"\n====== {username} ======\n"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # 1️⃣ 打开首页过 CF
            await page.goto(BASE, timeout=60000)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(5000)
            
            # 2️⃣ API 登录（浏览器环境）
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
                return result + f"❌ 登录失败\n"
            
            result += "✅ 登录成功\n"
            
            # 3️⃣ 取浏览器 cookie
            cookies = await context.cookies()
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_7 like Mac OS X) AppleWebKit/605.1.15",
                "Cookie": cookie_str,
                "Content-Type": "application/json"
            }
            
            # 4️⃣ 查询钱包余额
            balance = await get_user_balance(headers)
            if balance is not None:
                result += f"💰 钱包余额: {balance} RCoin\n"
            else:
                result += f"⚠ 无法获取余额信息\n"
        
        except Exception as e:
            result += f"❌ 执行异常: {str(e)}\n"
        
        finally:
            await browser.close()
        
        return result

async def main():
    final_msg = "📢 OKEmby 钱包查询结果\n"
    
    if not ACCOUNTS:
        print("❌ 未配置账户")
        return
    
    for acc in ACCOUNTS.split("&"):
        if not acc or "#" not in acc:
            continue
        parts = acc.split("#", 1)
        if len(parts) != 2:
            continue
        username, password = parts
        res = await run_account(username, password)
        final_msg += res
    
    print(final_msg)
    send_tg(final_msg)

if __name__ == "__main__":
    asyncio.run(main())
