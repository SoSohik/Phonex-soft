# -*- coding: utf-8 -*-
"""
PHONEX SOFT - Standalone System Login Tool (Telethon syslogin)
Clean, robust terminal-based authentication without TUI interference.
Saves authorized StringSession directly to data/session.txt.
"""

import os
import sys
import asyncio
from pathlib import Path

# Enable UTF-8 encoding on Windows
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        pass
    try:
        os.system("chcp 65001 >nul 2>&1")
    except Exception:
        pass
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from config import AppConfig, DATA_DIR

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

SESSION_FILE = DATA_DIR / "session.txt"


def print_banner():
    banner = r"""
$$$$$$$\  $$\   $$\  $$$$$$\  $$\   $$\ $$$$$$$$\ $$\   $$\ 
$$  __$$\ $$ |  $$ |$$  __$$\ $$$\  $$ |$$  _____|$$ |  $$ |
$$ |  $$ |$$ |  $$ |$$ /  $$ |$$$$\ $$ |$$ |      \$$\ $$  |
$$$$$$$  |$$$$$$$$ |$$ |  $$ |$$ $$\$$ |$$$$$\     \$$$$  / 
$$  ____/ $$  __$$ |$$ |  $$ |$$ \$$$$ |$$  __|    $$  $$<  
$$ |      $$ |  $$ |$$ |  $$ |$$ |\$$$ |$$ |      $$  /\$$\ 
$$ |      $$ |  $$ | $$$$$$  |$$ | \$$ |$$$$$$$$\ $$ /  $$ |
\__|      \__|  \__| \______/ \__|  \__|\________|\__|  \__|
"""
    print(banner)
    print("=" * 60)
    print("  PHONEX SOFT - АВТОРИЗАЦІЯ TELEGRAM (SYSLOGIN / СИСТЕМА)")
    print("=" * 60)
    print()


async def qr_login_flow(client: TelegramClient) -> bool:
    print("\n[+] Генерація QR-коду для швидкого входу...")
    qr_login = await client.qr_login()

    print("\n" + "=" * 50)
    print("  ВІДКРИЙТЕ TELEGRAM НА ТЕЛЕФОНІ:")
    print("  Налаштування -> Пристрої -> Підключити пристрій")
    print("=" * 50 + "\n")

    if HAS_QRCODE:
        qr = qrcode.QRCode()
        qr.add_data(qr_login.url)
        qr.print_ascii(invert=True)
    else:
        print(f"Посилання для входу: {qr_login.url}")

    print("\nОчікуємо підтвердження сканування у Telegram (120 сек)...")
    try:
        user = await qr_login.wait(timeout=120)
    except SessionPasswordNeededError:
        print("\n[!] Увімкнено 2FA (хмарний пароль)!")
        pwd = input("Введіть пароль 2FA: ").strip()
        user = await client.sign_in(password=pwd)

    if user:
        me = await client.get_me()
        u_name = f"@{me.username}" if me.username else me.first_name
        print(f"\n[УСПІХ] Авторизовано як: {u_name} (ID: {me.id})")
        return True
    return False


async def phone_login_flow(client: TelegramClient) -> bool:
    print("\n" + "-" * 50)
    print("  ВХІД ЗА НОМЕРОМ ТЕЛЕФОНУ (Telethon SysLogin)")
    print("-" * 50)
    print("Введіть ваш номер у міжнародному форматі (наприклад: +380981234567)")
    print("або введіть '0' для повернення.")

    while True:
        phone = input("\nНомер телефону > ").strip()
        if phone == "0":
            return False
        if not phone:
            print("Номер не може бути порожнім!")
            continue

        # Clean phone
        import re
        phone = re.sub(r"[^\d+]", "", phone)
        if phone.startswith("0") and len(phone) == 10:
            phone = "+38" + phone
        elif not phone.startswith("+"):
            phone = "+" + phone

        print(f"\n[+] Відправляємо запит до Telegram для {phone}...")
        try:
            sent = await client.send_code_request(phone)
            break
        except FloodWaitError as e:
            print(f"[ПОМИЛКА] Забагато спроб (FloodWait). Зачекайте {e.seconds} сек.")
            return False
        except Exception as e:
            print(f"[ПОМИЛКА] Не вдалося надіслати запит: {e}")
            retry = input("Спробувати інший номер? (y/n) > ").strip().lower()
            if retry != "y":
                return False

    print("\n" + "=" * 56)
    import telethon.tl.types.auth as auth_types
    if isinstance(sent.type, auth_types.SentCodeTypeApp):
        print("  [ВАЖЛИВО!] Код надіслано в ДОДАТОК TELEGRAM!")
        print("  👉 Відкрийте Telegram на телефоні чи ПК.")
        print("  Код знаходиться у чаті 'Telegram' (службові повідомлення),")
        print("  а НЕ у звичайному SMS!")
    elif isinstance(sent.type, auth_types.SentCodeTypeSms):
        print("  [ВАЖЛИВО!] Код надіслано через SMS на ваш телефон!")
    elif isinstance(sent.type, auth_types.SentCodeTypeCall):
        print("  [ВАЖЛИВО!] Telegram телефонує вам і продиктує код голосом!")
    else:
        print("  [+] Код успішно сформовано Telegram.")
    print("=" * 56)

    while True:
        code_raw = input("\nВведіть 5-значний код підтвердження (або '0' для виходу) > ").strip()
        if code_raw == "0":
            return False
        code = re.sub(r"\D", "", code_raw)
        if not code:
            print("Код не може бути порожнім!")
            continue

        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=sent.phone_code_hash)
            break
        except SessionPasswordNeededError:
            print("\n[!] На акаунті активовано 2FA (двоетапний пароль)!")
            pwd = input("Введіть ваш хмарний пароль 2FA > ").strip()
            try:
                await client.sign_in(password=pwd)
                break
            except Exception as e:
                print(f"[ПОМИЛКА 2FA] {e}")
                return False
        except Exception as e:
            err_str = str(e)
            if "PHONE_CODE_INVALID" in err_str:
                print("[ПОМИЛКА] Невірний код! Перевірте цифри у чаті Telegram та введіть ще раз.")
            elif "PHONE_CODE_EXPIRED" in err_str:
                print("[ПОМИЛКА] Час дії коду вичерпано. Потрібно почати заново.")
                return False
            else:
                print(f"[ПОМИЛКА] {e}")
                return False

    me = await client.get_me()
    u_name = f"@{me.username}" if me.username else me.first_name
    print(f"\n[УСПІХ] Авторизовано як: {u_name} (ID: {me.id})")
    return True


async def main_async():
    print_banner()

    config = AppConfig.load()
    if not config.api_id or not config.api_hash:
        print("[!] Не знайдено Telegram API Credentials у config.py / .env!")
        api_id_in = input("Введіть API ID (з my.telegram.org): ").strip()
        api_hash_in = input("Введіть API HASH (з my.telegram.org): ").strip()
        if api_id_in.isdigit() and api_hash_in:
            config.api_id = int(api_id_in)
            config.api_hash = api_hash_in
            config.save()
        else:
            print("[ПОМИЛКА] Некоректні API ID/HASH!")
            input("\nНатисніть Enter для виходу...")
            return

    # Check existing session
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if SESSION_FILE.exists():
        existing_str = SESSION_FILE.read_text(encoding="utf-8").strip()
        if existing_str:
            print("[*] Перевіряємо вже збережену сесію...")
            test_client = TelegramClient(StringSession(existing_str), config.api_id, config.api_hash)
            try:
                await test_client.connect()
                if await test_client.is_user_authorized():
                    me = await test_client.get_me()
                    u_name = f"@{me.username}" if me.username else me.first_name
                    print(f"\n[OK] Ви вже авторизовані як: {u_name} (ID: {me.id})!")
                    print(f"Сесія активна і збережена у: {SESSION_FILE}")
                    ans = input("\nБажаєте увійти в інший акаунт? (y/n) [n] > ").strip().lower()
                    if ans != "y":
                        await test_client.disconnect()
                        input("\nГотово! Запускайте start.bat або main.py. Натисніть Enter...")
                        return
                await test_client.disconnect()
            except Exception:
                pass

    print("\nОберіть спосіб входу:")
    print("  1 -> Швидкий вхід через QR-код (найпростіше, сканувати телефоном)")
    print("  2 -> Вхід за номером телефону (код у додатку Telegram / SMS)")
    print("  3 -> Вставити готову StringSession")
    print("  0 -> Вийти")

    choice = input("\nВаш вибір [1/2/3/0] > ").strip()
    if not choice:
        choice = "1"

    if choice == "0":
        print("Скасовано.")
        return

    session = StringSession("")
    client = TelegramClient(session, config.api_id, config.api_hash)
    await client.connect()

    success = False
    try:
        if choice == "1":
            success = await qr_login_flow(client)
        elif choice == "2":
            success = await phone_login_flow(client)
        elif choice == "3":
            raw_s = input("\nВставте рядок StringSession > ").strip()
            if raw_s:
                test_c = TelegramClient(StringSession(raw_s), config.api_id, config.api_hash)
                await test_c.connect()
                if await test_c.is_user_authorized():
                    client = test_c
                    success = True
                    me = await test_c.get_me()
                    print(f"\n[УСПІХ] StringSession валідна! Авторизовано як @{me.username or me.first_name}")
                else:
                    print("\n[ПОМИЛКА] Вказана StringSession не авторизована!")
                    await test_c.disconnect()

        if success:
            saved_str = client.session.save()
            SESSION_FILE.write_text(saved_str, encoding="utf-8")
            print("\n" + "=" * 60)
            print("  ВХІД УСПІШНО ВИКОНАНО!")
            print(f"  Сесію збережено у: {SESSION_FILE}")
            print("  Тепер ви можете запустити start.bat або main.py,")
            print("  і програма автоматично підключиться без введення паролів!")
            print("=" * 60)
        else:
            print("\n[!] Авторизація не була завершена.")

    except Exception as e:
        print(f"\n[ПОМИЛКА] Критичний збій авторизації: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()

    input("\nНатисніть Enter для завершення...")


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nПерервано користувачем.")


if __name__ == "__main__":
    main()
