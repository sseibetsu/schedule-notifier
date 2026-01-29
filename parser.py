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
    print("🤖 Starting FRANKENSTEIN Mode...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # --- СЕТЕВОЙ ШПИОН ---
        # Мы будем слушать, что уходит на сервер
        page.on("request", lambda request: print(
            f"   >> POST Request: {request.url} \n      Data: {request.post_data}") if request.method == "POST" else None)
        page.on("response", lambda response: print(
            f"   << Response: {response.status} from {response.url}") if "login" in response.url else None)

        print("🌍 Loading page...")
        try:
            page.goto("https://univer.kaznu.kz/user/login", timeout=60000)
        except Exception as e:
            print(f"Page load error: {e}")
            sys.exit(1)

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
            login_input.press_sequentially(LOGIN, delay=50)

            # 2. ПАРОЛЬ
            pass_input = page.locator("input[type='password']").first
            pass_input.click()
            pass_input.press_sequentially(PASSWORD, delay=50)

            print("   -> Credentials typed.")
        except Exception as e:
            print(f"❌ Input Error: {e}")
            sys.exit(1)

        # --- ОПЕРАЦИЯ "ФРАНКЕНШТЕЙН" (FIX NO NAME ATTRIBUTE) ---
        print("💉 Injecting missing 'NAME' attributes...")
        page.evaluate("""
            // Находим поле логина и даем ему имя 'login'
            var l = document.querySelector("input[type='text']");
            if(l) { 
                l.setAttribute("name", "login"); 
                console.log("Login name set.");
            }
            
            // Находим поле пароля и даем ему имя 'password'
            var p = document.querySelector("input[type='password']");
            if(p) { 
                p.setAttribute("name", "password"); 
                console.log("Password name set.");
            }
        """)

        page.wait_for_timeout(1000)

        # --- ОТПРАВКА ---
        print("🚀 Submitting...")
        try:
            # Жмем кнопку
            submit_btn = page.locator("input[type='submit']").first
            submit_btn.click()
        except:
            # Если кнопки нет, жмем Enter
            page.keyboard.press("Enter")

        # --- ОЖИДАНИЕ ---
        print("⏳ Waiting for result...")
        try:
            # Ждем выхода (успех) или перезагрузки (провал)
            # Ждем чуть дольше
            page.wait_for_selector("text=Выход", timeout=25000)
            print("✅ LOGIN SUCCESS! We are inside.")
        except:
            print("❌ Login Failed (Timeout).")
            # Снимаем экран, чтобы понять, где мы
            page.screenshot(path="login_failed_final.png")

            # Проверяем, может мы на странице расписания, но "Выход" называется иначе?
            if "Schedule" in page.url or "student" in page.url:
                print("⚠️ URL changed to student area, assuming success...")
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
