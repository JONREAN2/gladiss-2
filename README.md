# GLaDOS Auto Checkin

自动签到GLaDOS账户并通过Telegram通知

## 功能特性

- 每日自动签到（北京时间16:00）
- 实现无限白嫖
- 账户状态查询
- Telegram通知结果
- 完善的错误处理

## 配置指南

1. Fork本仓库
2. 在 GLADOS 签到页面,按 f12 键，获取到自己的获取到自己的 Cookie
3. 添加GitHub Secrets：
   - `GLADOS_EMAIL`: 你的GLaDOS注册邮箱
   - `GLADOS_COOKIE`: 从浏览器获取的Cookie
   - `TG_BOT_TOKEN`: Telegram Bot Token
   - `TG_CHAT_ID`: 接收通知的Chat ID
4. 手动触发工作流测试：
   - 在Actions标签页手动运行工作流
