# KazNU Schedule Parser

Automated schedule parser for Univer 2.0 system. Runs daily on **GitHub Actions**, bypasses bot protection, and updates `schedule.json` if changes are detected.

## Quick Setup (GitHub):
1. Create TG bot via @BotFather, and copy the token of your new bot.
2. Add your bot into the any of TG chats, tag him once or twice, and go to:
https://api.telegram.org/bot<YOUR_BOTS_TOKEN>/getUpdates, there you will see JSON page and you have to find the chat_id

3. **Fork** this repository.
4. Go to **Settings** → **Secrets and variables** → **Actions**.
5. Click **New repository secret** and add:
   * `TG_BOT_TOKEN` (step №1)
   * `TG_CHAT_ID` (step №2)
   * `UNI_LOGIN` (your Univer login)
   * `UNI_PASSWORD` (your Univer password)
4. Go to the **Actions** tab and enable workflows to understand whether they are working or not.

The bot will run automatically at XX:XX UTC(you can change the XX:XX time in updater.yml), in my project I have changed the time to 01:00, Almaty's 6 am.
You can also run it manually via the Actions tab.
