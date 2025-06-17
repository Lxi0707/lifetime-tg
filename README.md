# lifetime-tg

 使用说明

1. **准备工作**：
   - 创建一个 Telegram 机器人并获取其 API token
   - 获取要发布消息的 Telegram 频道 ID（注意频道需要添加机器人管理员）

2. **设置 Secrets**：
   - 在 GitHub 仓库的 Settings > Secrets 中添加：
     - `TELEGRAM_BOT_TOKEN` - 你的 Telegram 机器人 token
     - `TELEGRAM_CHANNEL_ID` - 目标频道的 ID（以 @ 开头的频道用户名或以 - 开头的数字 ID）

3. **自定义**：
   - 可以根据需要调整抓取频率（修改 cron 表达式）
   - 可以修改消息格式（在 `format_message` 函数中）
   - 可以添加更多的分类或过滤条件

4. **手动触发**：
   - 除了定时运行，你也可以在 GitHub Actions 页面手动触发此工作流
