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

# ЗАЩИТА ОТ ДУРАКА: Проверяем, нет ли лишних пробелов
if len(PASSWORD) != len(PASSWORD.strip()):
    print("⚠️ WARNING: В пароле найдены лишние пробелы! Проверьте GitHub Secrets.")


def run():
    print("🤖 Starting CYBORG Mode v2...")
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
            print(f"Page load error: {e}")
            sys.exit(1)

        # Выбор языка
        if "lang/change" in page.url or "Жүйеге кіру" in page.content():
            print("⚠️ Picking RU...")
            try:
                page.click("a[href*='/ru/']", timeout=5000)
                page.wait_for_load_state("networkidle")
            except:
                pass

        page.wait_for_timeout(2000)

        print("✍️ Typing Credentials...")
        try:
            # 1. ЛОГИН
            login_input = page.locator("input[type='text']").first
            login_input.click()
            login_input.fill(LOGIN)  # .fill надежнее для логина
            print("   -> Login filled.")

            page.wait_for_timeout(500)

            # 2. ПАРОЛЬ (Печатаем по буквам, как человек)
            pass_input = page.locator("input[type='password']").first
            pass_input.click()
            pass_input.press_sequentially(PASSWORD, delay=100)
            print("   -> Password typed.")

            # Скриншот перед отправкой
            page.screenshot(path="filled_form.png")

        except Exception as e:
            print(f"❌ Input Error: {e}")
            page.screenshot(path="input_error.png")
            sys.exit(1)

        # --- ТРОЙНОЙ УДАР ПО КНОПКЕ ---
        print("🚀 Submitting...")

        # СПОСОБ 1: Клавиша Enter
        print("   [1] Trying ENTER key...")
        page.keyboard.press("Enter")
        page.wait_for_timeout(3000)  # Ждем реакции

        # Проверяем, ушли ли мы со страницы логина?
        if "/user/login" not in page.url and "Выход" in page.content():
            print("   ✅ Enter worked!")
        else:
            # СПОСОБ 2: Жесткий клик
            print("   [2] Enter didn't work. Trying FORCE CLICK...")
            try:
                page.locator("input[type='submit']").first.click(force=True)
            except:
                pass
            page.wait_for_timeout(3000)

        # СПОСОБ 3: JS Injection (Если ничего не помогло)
        if "/user/login" in page.url:
            print("   [3] Click didn't work. Trying JS FORM SUBMIT...")
            # Находим форму, в которой лежит пароль, и отправляем её принудительно
            page.evaluate("""
                const pass = document.querySelector("input[type='password']");
                if(pass && pass.form) {
                    pass.form.submit();
                }
            """)
            page.wait_for_timeout(5000)

        # --- ПРОВЕРКА РЕЗУЛЬТАТА ---
        print("⏳ Waiting for login result...")
        try:
            # Ищем любой признак успеха
            page.wait_for_selector("text=Выход", timeout=15000)
            print("✅ LOGIN SUCCESS! We are inside.")
        except:
            print("❌ Login Failed (Timeout). Still on login page.")
            page.screenshot(path="login_failed_final.png")
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
            print("❌ Schedule table missing (but login worked).")
            # Сохраняем HTML, чтобы понять, что мы видим
            page.screenshot(path="schedule_missing.png")
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
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
