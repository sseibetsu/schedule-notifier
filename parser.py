import os
import json
import sys
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# 1. retrieving login/pass from github secrets
LOGIN = os.environ.get("UNI_LOGIN")
PASSWORD = os.environ.get("UNI_PASSWORD")

if not LOGIN or not PASSWORD:
    print("login or pass not found.")
    sys.exit(1)

# 2. work is here


def run():
    print("browsing...")
    with sync_playwright() as p:
        # headless=True = no video processor
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # logging into the kaznu to retrieve schedule
        print("entering into the login page...")
        try:
            page.goto("https://univer.kaznu.kz/user/login", timeout=60000)
        except Exception as e:
            print(f"Error loading page: {e}")
            sys.exit(1)

        # if 213 pops up (Language selection)
        if "lang/change" in page.url or "Жүйеге кіру" in page.content():
            print("need to choose the lang, picking ru-RU...")
            try:
                page.click("a[href*='/ru/']", timeout=5000)
                print("ru is chosen.")
                page.wait_for_load_state("networkidle")
            except:
                print("couldn't choose the lang, trying another attempt...")

        page.wait_for_timeout(2000)
        print("implementing data...")

        # --- НОВАЯ ЛОГИКА ВВОДА (TAB + Печать по буквам) ---
        try:
            # 1. Кликаем точно в поле логина
            login_field = None
            if page.locator("input[name='makelogin']").count() > 0:
                login_field = page.locator("input[name='makelogin']")
            elif page.locator("input[name='login']").count() > 0:
                login_field = page.locator("input[name='login']")
            else:
                login_field = page.locator("input[type='text']:visible").first

            # Очищаем и печатаем логин
            login_field.click()
            login_field.clear()
            # press_sequentially печатает по буквам, как человек (delay=50мс)
            login_field.press_sequentially(LOGIN, delay=50)
            print("Login typed.")

            # 2. Жмем TAB, чтобы перейти в поле пароля
            page.keyboard.press("Tab")
            page.wait_for_timeout(500)  # Короткая пауза

            # 3. Печатаем пароль в то поле, которое сейчас активно (в фокусе)
            # Это обходит проблему с поиском селектора
            print("Typing password into focused field...")
            page.keyboard.type(PASSWORD, delay=50)

            # 4. Жмем Enter
            print("Pressing Enter...")
            page.keyboard.press("Enter")

        except Exception as e:
            print(f"Error during typing: {e}")
            page.screenshot(path="typing_error.png")
            sys.exit(1)

        try:
            print("waiting for successful login...")
            # Ждем выхода (увеличил тайм-аут до 30с)
            page.wait_for_selector("text=Выход", timeout=30000)
            print("logged in successfully")
        except:
            print("ERROR: Login failed. Check screenshot in artifacts.")
            page.screenshot(path="login_error.png")
            browser.close()
            sys.exit(1)

        print("going to the schedule...")
        page.goto("https://univer.kaznu.kz/student/myschedule/")

        try:
            page.wait_for_selector("table.schedule", timeout=20000)
        except:
            print("ERROR: Schedule table not found!")
            page.screenshot(path="schedule_error.png")
            browser.close()
            sys.exit(1)

        html_content = page.content()
        browser.close()

        print("parsing the downloaded HTML...")
        parse_html_to_json(html_content)

# 3. parsing the html to json


def parse_html_to_json(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', class_='schedule')

    if not table:
        print("couldn't find the schedule table in HTML.")
        sys.exit(1)

    rows = table.find_all('tr')
    final_schedule = []

    if len(rows) < 2:
        print("Table seems empty.")
        return

    for row in rows[1:]:
        cells = row.find_all('td')
        if len(cells) < 2:
            continue

        time_raw = cells[0].get_text(strip=True)
        time_text = time_raw.split('-')[0] if '-' in time_raw else time_raw

        for day_index, cell in enumerate(cells[1:]):
            group_div = cell.find('div', class_='groups')
            if not group_div or not group_div.get_text(strip=True):
                continue

            try:
                teacher_paragraphs = group_div.find_all('p', class_='teacher')
                subject = teacher_paragraphs[0].get_text(strip=True) if len(
                    teacher_paragraphs) > 0 else "Предмет"

                room = "Онлайн"
                params_p = group_div.find('p', class_='params')
                if params_p:
                    txt = params_p.get_text()
                    if "Ауд.:" in txt:
                        parts = txt.split("Ауд.:")
                        if len(parts) > 1:
                            room = parts[1].strip().split('\n')[0]

                final_schedule.append({
                    "day_of_week": day_index,
                    "time": time_text,
                    "subject": subject,
                    "room": room
                })
            except Exception as e:
                print(f"Ошибка парсинга ячейки: {e}")

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(final_schedule, f, ensure_ascii=False, indent=2)
    print(f"successfully saved {len(final_schedule)} of lessons.")


# 4. dunno
if __name__ == "__main__":
    run()
