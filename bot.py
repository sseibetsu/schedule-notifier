import json
import datetime
import os
import asyncio
import pytz
from telegram import Bot

# --- НАСТРОЙКИ ---
# часовой пояс
TIMEZONE = pytz.timezone('Asia/Almaty')


async def send_reminder(text):
    # берем токен из секретов GitHub
    token = os.environ.get("TG_BOT_TOKEN")
    chat_id = os.environ.get("TG_CHAT_ID")

    bot = Bot(token=token)
    await bot.send_message(chat_id=chat_id, text=text)


def main():
    # 1. Получаем текущее время в твоем часовом поясе
    now = datetime.datetime.now(TIMEZONE)
    current_weekday = now.weekday()  # monday = 0, sunday = 6

    # Загружаем расписание
    with open('schedule.json', 'r', encoding='utf-8') as f:
        schedule = json.load(f)

    # 2. Пробегаемся по расписанию
    for item in schedule:
        # проверка на корректность даты: "расписание не равно текущему дню недели"
        if item['day_of_week'] != current_weekday:
            continue
        lesson_time_str = item['time']
        lesson_hour, lesson_minute = map(int, lesson_time_str.split(':'))
        lesson_time = now.replace(
            hour=lesson_hour, minute=lesson_minute, second=0, microsecond=0)
        time_diff = lesson_time - now
        minutes_diff = time_diff.total_seconds() / 60

        message = ""

        if 90 <= minutes_diff <= 130:
            message = f"емае, уже через 2 часа пара: {item['subject']}, в {item['time']}. будет в: {item['room']}"

        elif 30 <= minutes_diff <= 80:
            message = f"пиздяо, уже через час пара: {item['subject']}, в {item['time']}. будет в: {item['room']}"

        if message:
            print(f"Отправляю: {message}")
            asyncio.run(send_reminder(message))
        else:
            print(
                f"Нет напоминаний для {item['subject']} (осталось {minutes_diff} мин)")


if __name__ == "__main__":
    main()
