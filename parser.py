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
    print("📱 Starting iPHONE Mode...")
    with sync_playwright() as p:
        # Используем пресет iPhone 13
        iphone = p.devices['iPhone 13']
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(**iphone)  # Применяем настройки айфона
        page = context.new_page()

        # СЛУШАЕМ ОШИБКИ БРАУЗЕРА (Самое важное!)
        page.on("console", lambda msg: print(
            f"   [BROWSER CONSOLE] {msg.type}: {msg.text}"))
        page.on("pageerror", lambda exc: print(f"   [BROWSER CRASH]: {exc}"))

        print("🌍 Loading page (Mobile)...")
        try:
            page.goto("https://univer.kaznu.kz/user/login", timeout=60000)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

        # Ждем чуть дольше
        page.wait_for_timeout(3000)

        # Если вылез выбор языка (на мобилке он может быть другим)
        if "lang/change" in page.url:
            print("⚠️ Picking RU...")
            try:
                page.click("text=Русский", timeout=5000)
            except:
                try:
                    page.click("a[href*='/ru/']", timeout=5000)
                except:
                    pass
            page.wait_for_load_state("networkidle")

        print("✍️ Typing Credentials...")
        try:
            # На мобильной версии селекторы могут быть те же, но проверим
            # 1. ЛОГИН
            login_input = page.locator("input[type='text']").first
            login_input.tap()  # На мобилке это tap, а не click
            page.wait_for_timeout(500)
            login_input.type(LOGIN, delay=200)  # type - старый надежный метод
            print("   -> Login typed.")

            # 2. ПАРОЛЬ
            pass_input = page.locator("input[type='password']").first
            pass_input.tap()
            page.wait_for_timeout(500)
            pass_input.type(PASSWORD, delay=200)
            print("   -> Password typed.")

            page.screenshot(path="mobile_filled.png")

        except Exception as e:
            print(f"❌ Input Error: {e}")
            sys.exit(1)

        print("🚀 Tapping Login...")
        try:
            # На мобилке часто кнопка может быть перекрыта
            btn = page.locator("input[type='submit']").first
            btn.tap()
        except:
            # Если tap не сработал, пробуем JS click
            page.locator("input[type='submit']").first.click(force=True)

        print("⏳ Waiting for result...")
        try:
            # Ждем перехода
            page.wait_for_selector("text=Выход", timeout=30000)
            print("✅ LOGIN SUCCESS!")
        except:
            print("❌ Login Failed.")
            page.screenshot(path="mobile_failed.png")
            # Проверяем, где мы
            print(f"   Current URL: {page.url}")

            # Если мы остались на логине - это провал
            if "login" in page.url:
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
                final_schedule.append(
                    {"day_of_week": day_index, "time": time_text, "subject": subject, "room": room})
            except:
                pass

    with open('schedule.json', 'w', encoding='utf-8') as f:
        json.dump(final_schedule, f, ensure_ascii=False, indent=2)
    print(f"🎉 Success! Saved {len(final_schedule)} items.")


if __name__ == "__main__":
    run()
