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
    print("🕵️‍♂️ Starting DEBUG Mode...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        print("🌍 Loading login page...")
        try:
            page.goto("https://univer.kaznu.kz/user/login", timeout=60000)
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

        # Language handler
        if "lang/change" in page.url or "Жүйеге кіру" in page.content():
            print("⚠️ Changing lang to RU...")
            try:
                page.click("a[href*='/ru/']", timeout=5000)
                page.wait_for_load_state("networkidle")
            except:
                pass

        page.wait_for_timeout(3000)  # Ждем полной прогрузки

        # --- ДИАГНОСТИКА: ЧТО ЕСТЬ НА СТРАНИЦЕ? ---
        print("\n🔎 --- SCANNING INPUTS ---")
        inputs = page.locator("input").all()
        print(f"Found {len(inputs)} input fields:")

        password_locator = None

        for i, inp in enumerate(inputs):
            try:
                # Получаем HTML код каждого поля
                html_code = inp.evaluate("el => el.outerHTML")
                is_visible = inp.is_visible()
                print(
                    f"   Input #{i}: Visible={is_visible} | Code: {html_code}")

                # Ищем поле, похожее на пароль (по типу или имени)
                if "password" in html_code.lower():
                    print(
                        f"      👉 CANDIDATE FOR PASSWORD DETECTED (Index {i})")
                    if is_visible:
                        password_locator = inp
            except:
                pass
        print("🔎 --- END SCAN ---\n")

        # --- ВВОД ДАННЫХ ---
        print("✍️ Filling Login...")
        try:
            # Ищем логин
            if page.locator("input[name='makelogin']").count() > 0:
                page.fill("input[name='makelogin']", LOGIN)
            elif page.locator("input[name='login']").count() > 0:
                page.fill("input[name='login']", LOGIN)
            else:
                page.locator("input[type='text']").first.fill(LOGIN)
        except Exception as e:
            print(f"Login fill error: {e}")

        print("✍️ Filling Password...")
        try:
            # Если мы нашли явное поле пароля при сканировании - используем его
            if password_locator:
                print("   -> Using detected visible password field...")
                password_locator.click()
                password_locator.fill(PASSWORD)
            else:
                # ЗАПАСНОЙ ВАРИАНТ: Бьем по всем полям type=password
                print("   -> Blindly filling ALL password fields...")
                pass_inputs = page.locator("input[type='password']").all()
                for p_inp in pass_inputs:
                    try:
                        p_inp.fill(PASSWORD)
                        print("      Filled one password field.")
                    except:
                        pass
        except Exception as e:
            print(f"Password fill error: {e}")

        # 📸 СКРИНШОТ ПРОВЕРКИ (ДО НАЖАТИЯ ВОЙТИ)
        # Самое важное: увидеть, заполнилось ли поле
        print("📸 Taking CHECK screenshot (check_input.png)...")
        page.screenshot(path="check_input.png")

        # Нажимаем войти
        print("👊 Clicking Login...")
        try:
            if page.locator("input[value='Войти в систему']").is_visible():
                page.locator("input[value='Войти в систему']").click()
            elif page.locator("input[type='submit']").is_visible():
                page.locator("input[type='submit']").click()
            else:
                page.press("input[type='password']", "Enter")
        except:
            pass

        # Проверяем результат
        try:
            page.wait_for_selector("text=Выход", timeout=15000)
            print("✅ LOGIN SUCCESS!")
        except:
            print("❌ Login Failed.")
            # Если не вошло - не падаем, чтобы скрипт успел сохранить скриншоты
            pass

        # --- ЕСЛИ УСПЕХ, ТО КАЧАЕМ РАСПИСАНИЕ ---
        # (Оставляем эту часть, чтобы если вдруг заработает - всё скачалось)
        if "Выход" in page.content():
            print("📅 Getting schedule...")
            page.goto("https://univer.kaznu.kz/student/myschedule/")
            try:
                page.wait_for_selector("table.schedule", timeout=20000)
                html_content = page.content()
                parse_html_to_json(html_content)
            except:
                print("Schedule table not found.")


def parse_html_to_json(html_content):
    # (Тот же код парсера, что и раньше)
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
    print(f"🎉 Saved {len(final_schedule)} lessons.")


if __name__ == "__main__":
    run()
