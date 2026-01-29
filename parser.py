import os
import json
import sys
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# 1. Credentials
LOGIN = os.environ.get("UNI_LOGIN")
PASSWORD = os.environ.get("UNI_PASSWORD")

if not LOGIN or not PASSWORD:
    print("login or pass not found.")
    sys.exit(1)


def run():
    print("browsing...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("entering into the login page...")
        try:
            page.goto("https://univer.kaznu.kz/user/login", timeout=60000)
        except Exception as e:
            print(f"Error loading page: {e}")
            sys.exit(1)

        # Language selection check
        if "lang/change" in page.url or "Жүйеге кіру" in page.content():
            print("picking ru-RU...")
            try:
                page.click("a[href*='/ru/']", timeout=5000)
                page.wait_for_load_state("networkidle")
            except:
                pass

        page.wait_for_timeout(2000)
        print("implementing data (NUCLEAR METHOD)...")

        # --- ЯДЕРНЫЙ МЕТОД (JS INJECTION) ---
        # Мы не печатаем. Мы жестко присваиваем значение через JavaScript.
        try:
            # 1. Вставляем ЛОГИН через JS
            # Ищем любое текстовое поле, которое не скрыто
            login_selector = "input[type='text']:not([type='hidden'])"
            # Если есть поле с именем makelogin - берем его
            if page.locator("input[name='makelogin']").count() > 0:
                login_selector = "input[name='makelogin']"

            print(f"Injecting Login into {login_selector}...")
            # JS магия: находим элемент и меняем его .value
            page.evaluate(f"""
                const input = document.querySelector("{login_selector}");
                if (input) {{
                    input.value = "{LOGIN}";
                    input.dispatchEvent(new Event('input', {{ bubbles: true }})); // Сообщаем сайту, что мы что-то ввели
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            """)

            # 2. Вставляем ПАРОЛЬ через JS
            print("Injecting Password...")
            page.evaluate(f"""
                const passInput = document.querySelector("input[type='password']");
                if (passInput) {{
                    passInput.value = "{PASSWORD}";
                    passInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    passInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            """)

        except Exception as e:
            print(f"JS Injection failed: {e}")
            sys.exit(1)

        page.wait_for_timeout(1000)

        # Кликаем кнопку Войти
        print("logging in...")
        try:
            # Пробуем разные варианты кнопки
            if page.locator("input[value='Войти в систему']").is_visible():
                page.locator("input[value='Войти в систему']").click()
            elif page.locator("input[type='submit']").is_visible():
                page.locator("input[type='submit']").click()
            else:
                # Если кнопки нет - жмем Enter в поле пароля
                page.press("input[type='password']", "Enter")
        except Exception as e:
            print(f"Error clicking button: {e}")

        # Проверка успеха
        try:
            print("waiting for successful login...")
            page.wait_for_selector("text=Выход", timeout=30000)
            print("logged in successfully")
        except:
            print("ERROR: Login failed.")
            page.screenshot(path="login_error_nuclear.png")
            browser.close()
            sys.exit(1)

        print("going to the schedule...")
        page.goto("https://univer.kaznu.kz/student/myschedule/")

        try:
            page.wait_for_selector("table.schedule", timeout=20000)
        except:
            print("ERROR: Schedule table not found!")
            browser.close()
            sys.exit(1)

        html_content = page.content()
        browser.close()

        print("parsing HTML...")
        parse_html_to_json(html_content)


def parse_html_to_json(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    table = soup.find('table', class_='schedule')

    if not table:
        print("couldn't find the schedule table.")
        sys.exit(1)

    rows = table.find_all('tr')
    final_schedule = []

    if len(rows) < 2:
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
            except:
                pass

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(final_schedule, f, ensure_ascii=False, indent=2)
    print(f"successfully saved {len(final_schedule)} lessons.")


if __name__ == "__main__":
    run()
