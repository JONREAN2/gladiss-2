name: OKEmby Auto Checkin

on:
  schedule:
    - cron: '10 2 * * *'   # 北京时间 10:10
  workflow_dispatch:

jobs:
  checkin:
    runs-on: ubuntu-latest

    steps:
      - name: 拉取代码
        uses: actions/checkout@v4

      - name: 安装 Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: 安装依赖
        run: |
          pip install playwright requests
          playwright install chromium

      - name: 运行签到
        env:
          OKEMBY_ACCOUNT: ${{ secrets.OKEMBY_ACCOUNT }}
          TG_BOT_TOKEN: ${{ secrets.TG_BOT_TOKEN }}
          TG_CHAT_ID: ${{ secrets.TG_CHAT_ID }}
        run: |
          python okemby_playwright.py