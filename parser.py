import os
import json
import sys
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

LOGIN = os.environ.get("UNI_LOGIN")
PASSWORD = os.environ.get("UNI_PASSWORD")

if not LOGIN or not PASSWORD:
    print("❌ Login/Pass not found.")
    sys.exit(1)


def run():
    print("🤖 Starting LAZY HUMAN Mode...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("🌍 Loading page...")
        try:
            page.goto("https://univer.kaznu.kz/user/login", timeout=60000)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

        # Если вылез выбор языка
        if "lang/change" in page.url or "Жүйеге кіру" in page.content():
            print("⚠️ Picking RU...")
            try:
                page.click("a[href*='/ru/']", timeout=5000)
                page.wait_for_load_state("networkidle")
            except:
                pass

        # Даем странице "подышать" перед стартом
        page.wait_for_timeout(3000)

        print("✍️ Typing Credentials (SLOWLY)...")

        try:
            # 1. ЛОГИН
            login_input = page.locator("input[type='text']").first
            login_input.click()
            # Очищаем поле на всякий случай
            login_input.fill("")
            # Печатаем по одной букве раз в 300мс (0.3 сек) - это достаточно медленно
            # Если поставить 0.5, то на длинных логинах можем упереться в тайм-аут GitHub
            login_input.press_sequentially(LOGIN, delay=300)
            print("   -> Login typed.")

            page.wait_for_timeout(1000)  # Пауза между полями

            # 2. ПАРОЛЬ
            pass_input = page.locator("input[type='password']").first
            pass_input.click()
            pass_input.fill("")
            # Пароль печатаем еще медленнее (0.5 сек)
            pass_input.press_sequentially(PASSWORD, delay=500)
            print("   -> Password typed.")

        except Exception as e:
            print(f"❌ Input Error: {e}")
            sys.exit(1)

        print("☕ Waiting 5 seconds before Submit (letting scripts work)...")
        page.wait_for_timeout(5000)

        # --- ОТПРАВКА ---
        print("🚀 Clicking Submit...")

        # Пробуем нажать Enter (самый человеческий способ)
        try:
            page.keyboard.press("Enter")
        except:
            # Если не сработало, ищем кнопку
            try:
                page.locator("input[type='submit']").first.click()
            except:
                pass

        print("⏳ Waiting for result...")
        try:
            # Ждем долго, сайт может думать
            page.wait_for_selector("text=Выход", timeout=40000)
            print("✅ LOGIN SUCCESS! We are inside.")
        except:
            print("❌ Login Failed.")
            page.screenshot(path="login_failed_lazy.png")
            # Проверка на случай успеха с другим URL
            if "student" in page.url or "Schedule" in page.url:
                print("⚠️ URL changed to student zone. Assuming success!")
            else:
                browser.close()
                sys.exit(1)

        # --- СКАЧИВАНИЕ ---
        print("📅 Downloading schedule...")
        page.goto("https://univer.kaznu.kz/student/myschedule/")
        try:
            page.wait_for_selector("table.schedule", timeout=20000)
            html = page.content()
            browser.close()
            parse_html_to_json(html)
        except:
            print("❌ Schedule table missing.")
            browser.close()
            sys.exit(1)


def parse_html_to_json(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', class_='schedule')
    if not table:
        return

    rows = table.find_all('tr')
    final_schedule = []

    if len(rows) < 2:
        return

    for row in rows[1:]:
        cells = row.find_all('td')
        if len(cells) < 2:
            continue

        time_text = cells[0].get_text(strip=True).split('-')[0]

        for day_index, cell in enumerate(cells[1:]):
            group_div = cell.find('div', class_='groups')
            if not group_div or not group_div.get_text(strip=True):
                continue

            try:
                teacher_ps = group_div.find_all('p', class_='teacher')
                subject = teacher_ps[0].get_text(
                    strip=True) if teacher_ps else "Предмет"
                room = "Онлайн"
                params_p = group_div.find('p', class_='params')
                if params_p:
                    txt = params_p.get_text()
                    if "Ауд.:" in txt:
                        room = txt.split("Ауд.:")[1].strip().split('\n')[0]

                final_schedule.append({
                    "day_of_week": day_index,
                    "time": time_text,
                    "subject": subject,
                    "room": room
                })
            except:
                pass

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(final_schedule, f, ensure_ascii=False, indent=2)
    print(f"🎉 Success! Saved {len(final_schedule)} items.")


if __name__ == "__main__":
    run()
