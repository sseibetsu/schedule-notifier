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
    print("👻 Starting STEALTH Mode...")
    with sync_playwright() as p:
        # МАГИЯ МАСКИРОВКИ: Отключаем флаги автоматизации
        browser = p.chromium.launch(
            headless=True,
            args=[
                # Самое важное: скрывает, что мы бот
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080"
            ]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="ru-RU"
        )

        # Дополнительный скрипт, чтобы скрыть navigator.webdriver
        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        page = context.new_page()

        # Слушаем ошибки (на случай если сайт снова упадет)
        page.on("console", lambda msg: print(
            f"   [CONSOLE] {msg.text}") if msg.type == "error" else None)

        print("🌍 Loading page...")
        try:
            page.goto("https://univer.kaznu.kz/user/login", timeout=60000)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

        # Выбор языка (если перекинуло)
        if "lang/change" in page.url or "Жүйеге кіру" in page.content():
            print("⚠️ Picking RU...")
            try:
                page.click("a[href*='/ru/']", timeout=5000)
                page.wait_for_load_state("networkidle")
            except:
                pass

        page.wait_for_timeout(3000)

        print("✍️ Typing Credentials...")

        try:
            # Используем селектор по форме, который мы нашли в вашем HTML файле
            # Форма имеет id="login_frm"

            # 1. ЛОГИН
            # Ищем текстовое поле внутри формы логина (исключая скрытые)
            login_input = page.locator(
                "#login_frm input[type='text']:visible").first
            login_input.click()
            login_input.fill("")  # Очищаем (вдруг там что-то есть)
            login_input.type(LOGIN, delay=100)  # Печатаем как человек
            print("   -> Login typed.")

            page.wait_for_timeout(500)

            # 2. ПАРОЛЬ
            pass_input = page.locator(
                "#login_frm input[type='password']:visible").first
            pass_input.click()
            pass_input.fill("")
            pass_input.type(PASSWORD, delay=100)
            print("   -> Password typed.")

            # Делаем скриншот перед нажатием
            page.screenshot(path="stealth_filled.png")

        except Exception as e:
            print(f"❌ Input Error: {e}")
            page.screenshot(path="input_error.png")
            sys.exit(1)

        print("🚀 Clicking Submit (Letting JS handle encryption)...")
        try:
            # Нажимаем кнопку внутри формы
            submit_btn = page.locator("#login_frm input[type='submit']").first
            submit_btn.click()
        except Exception as e:
            print(f"Click error: {e}")
            # Запасной вариант: Enter
            page.keyboard.press("Enter")

        print("⏳ Waiting for result...")
        try:
            # Ждем перехода. Увеличили тайм-аут, так как шифрование требует времени
            page.wait_for_selector("text=Выход", timeout=40000)
            print("✅ LOGIN SUCCESS!")
        except:
            print(f"❌ Login Failed. URL: {page.url}")
            page.screenshot(path="stealth_failed.png")

            # Если мы на странице студента, но не видим кнопку "Выход" (редкий баг)
            if "student" in page.url:
                print("⚠️ URL looks acceptable. Trying to proceed...")
            else:
                browser.close()
                sys.exit(1)

        # --- СКАЧИВАНИЕ РАСПИСАНИЯ ---
        print("📅 Downloading schedule...")
        page.goto("https://univer.kaznu.kz/student/myschedule/")
        try:
            page.wait_for_selector("table.schedule", timeout=20000)
            html = page.content()
            browser.close()
            parse_html_to_json(html)
        except:
            print("❌ Schedule table missing.")
            page.screenshot(path="schedule_missing.png")
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
