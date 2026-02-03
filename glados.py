import os
import random
import time
import requests
import datetime


class GLaDOSChecker:
    API_BASE = "https://glados.rocks/api/user"
    CHECKIN_URL = f"{API_BASE}/checkin"
    STATUS_URL = f"{API_BASE}/status"

    def __init__(self):
        self.bot_token = os.environ["TG_BOT_TOKEN"]
        self.chat_id = os.environ["TG_CHAT_ID"]
        self.accounts = self._load_accounts()

    def _load_accounts(self):
        accounts = []
        i = 1
        while True:
            email = os.getenv(f"GLADOS_EMAIL_{i}")
            cookie = os.getenv(f"GLADOS_COOKIE_{i}")
            if not email or not cookie:
                break
            accounts.append({"email": email, "cookie": cookie})
            i += 1

        if not accounts:
            raise RuntimeError("❌ 未检测到任何 GLaDOS 账号")
        return accounts

    @staticmethod
    def _now():
        return (datetime.datetime.utcnow() + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")

    def _headers(self, cookie):
        return {
            "Accept": "application/json",
            "Cookie": cookie,
            "User-Agent": random.choice([
                "Mozilla/5.0 Chrome/125.0.0.0",
                "Mozilla/5.0 Safari/605.1.15"
            ]),
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://glados.rocks"
        }

    def checkin(self, cookie):
        r = requests.post(
            self.CHECKIN_URL,
            headers=self._headers(cookie),
            json={"token": "glados.one"},
            timeout=15
        )
        r.raise_for_status()
        msg = r.json().get("message", "")
        if "Got" in msg:
            return f"✅ {msg}"
        if "Tomorrow" in msg:
            return "⏳ 今日已签到"
        return f"❓ {msg}"

    def status(self, cookie):
        r = requests.get(self.STATUS_URL, headers=self._headers(cookie), timeout=15)
        r.raise_for_status()
        days = r.json().get("data", {}).get("leftDays", 0)
        return f"剩余 {float(days):.1f} 天 🗓️"

    def notify_all(self, results: list[dict]):
        """
        合并所有账号结果，一次性推送到 TG
        results = [
            {"email": "...", "checkin": "...", "status": "..."},
            ...
        ]
        """
        lines = [f"🕒 {self._now()}  GLaDOS 签到结果\n"]
        for res in results:
            lines.append(
                f"📧 {res['email']}\n"
                f"🔔 签到: {res['checkin']}\n"
                f"📊 状态: {res['status']}\n"
                "--------------------"
            )

        message = "\n".join(lines)
        try:
            requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": self.chat_id, "text": message},
                timeout=10
            )
        except Exception as e:
            print(f"⚠️ TG 消息发送失败: {e}")

    def run(self):
        results = []
        for acc in self.accounts:
            time.sleep(random.uniform(2, 5))
            checkin_result = self.checkin(acc["cookie"])
            status_result = self.status(acc["cookie"])
            results.append({
                "email": acc["email"],
                "checkin": checkin_result,
                "status": status_result
            })

        self.notify_all(results)


if __name__ == "__main__":
    GLaDOSChecker().run()
