import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

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
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stdin, "reconfigure"):
            sys.stdin.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.markup import escape
from rich.prompt import Prompt

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.custom.message import Message
from telethon.errors import (
    SessionPasswordNeededError,
    FloodWaitError,
    SessionRevokedError,
    SessionExpiredError,
    AuthKeyUnregisteredError,
    AuthKeyInvalidError,
    UserDeactivatedError,
    UserDeactivatedBanError,
    UnauthorizedError
)

AUTH_TERMINATED_ERRORS = (
    SessionRevokedError,
    SessionExpiredError,
    AuthKeyUnregisteredError,
    AuthKeyInvalidError,
    UserDeactivatedError,
    UserDeactivatedBanError,
    UnauthorizedError
)

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False
    qrcode = None

from config import AppConfig
from database import InventoryDB
from drop_parser import parse_drop_message
from flasher import DeviceFlashingManager, HAS_PYTESSERACT
from time_parser import parse_cooldown_seconds, calculate_wait_time, is_wait_message, format_countdown, format_duration_friendly


STATE_DISCONNECTED = "DISCONNECTED"
STATE_CONNECTING = "CONNECTING"
STATE_CONNECTED = "CONNECTED"
STATE_ROLLING = "ROLLING"
STATE_WAITING = "WAITING"
STATE_PAUSED = "PAUSED"


APP_NAME = "PHONEX SOFT"
APP_VERSION = "1.0"
APP_FULL_TITLE = "PHONEX SOFT"

SPLASH_ASCII_LOGO = r"""
$$$$$$$\  $$\   $$\  $$$$$$\  $$\   $$\ $$$$$$$$\ $$\   $$\ 
$$  __$$\ $$ |  $$ |$$  __$$\ $$$\  $$ |$$  _____|$$ |  $$ |
$$ |  $$ |$$ |  $$ |$$ /  $$ |$$$$\ $$ |$$ |      \$$\ $$  |
$$$$$$$  |$$$$$$$$ |$$ |  $$ |$$ $$\$$ |$$$$$\     \$$$$  / 
$$  ____/ $$  __$$ |$$ |  $$ |$$ \$$$$ |$$  __|    $$  $$<  
$$ |      $$ |  $$ |$$ |  $$ |$$ |\$$$ |$$ |      $$  /\$$\ 
$$ |      $$ |  $$ | $$$$$$  |$$ | \$$ |$$$$$$$$\ $$ /  $$ |
\__|      \__|  \__| \______/ \__|  \__|\________|\__|  \__|
"""

TEXTS = {
    "en": {
        "title": "⚡ PHONEX SOFT v1.0",
        "user": "User",
        "target": "Target",
        "command": "Command",
        "not_authorized": "Not authorized",
        "status_title": "STATUS",
        "timer_title": "TIMER",
        "stats_title": "STATS & DROPS",
        "latest_drop_title": "🎁 LATEST DROP",
        "bot_reply_title": "💬 BOT RESPONSE",
        "recent_logs_title": "📋 ACTIVITY LOG",
        "commands_guide_title": "📖 COMMANDS GUIDE",
        "state_disconnected": "🔴 DISCONNECTED",
        "state_paused": "⏸️ PAUSED",
        "state_rolling": "🎲 ROLLING...",
        "state_active": "🟢 ACTIVE (AUTO)",
        "state_connecting": "🟡 CONNECTING...",
        "hint_login": "Type 'login' to sign in",
        "hint_start": "Type 'on' to start auto-roll",
        "hint_rolling": "Sending command to bot",
        "hint_active": "Auto-roll running smoothly",
        "hint_connecting": "Authorizing session...",
        "timer_ready": "⚡ READY TO ROLL",
        "timer_sending": "Sending request...",
        "timer_paused": "Timer paused",
        "stat_sent": "Sent",
        "stat_success": "Success",
        "stat_cooldown": "Cooldowns",
        "stat_errors": "Errors",
        "stat_inventory": "In inventory (invlast)",
        "no_drops_yet": "No drops saved yet. Type 'on' or 'send'!",
        "no_bot_replies": "No replies from bot yet.",
        "log_empty": "Log is empty...",
        "cmd_prompt_hint": "Type [bold cyan]help[/bold cyan] for guide, [bold cyan]r[/bold cyan] to refresh, or [bold green]on[/bold green] to run.",
        "input_prompt": "\nCommand > ",
        "choice_prompt": "Choice",
        "unknown_cmd": "Unknown command '{}'. Type 'help'.",
        "press_enter": "\nPress Enter to return...",
        "shutdown_msg": "\n[bold yellow]Stopping and saving session...[/bold yellow]",
        "shutdown_done": "[bold green]Stopped successfully. Session saved![/bold green]\n",
        "lang_switched": "Language switched to English.",
        "inv_title": "📱 BOT PHONE INVENTORY (/myphones)",
        "inv_choose": "Select an item by number:",
        "inv_back_hint": "Type [bold red]0[/bold red] to return to main menu.",
        "inv_flashed_blocked": "❌ Selection of 'Прошитые телефоны' is disabled.",
        "inv_invalid_choice": "Invalid choice number!",
        "invlast_title": "🎁 LOCAL SAVED DROPS (invlast)",
        "invlast_total": "Total in DB",
        "invlast_sum": "Total value",
        "invlast_empty": "Database is currently empty. Run auto-roll with 'on' or 'send' to collect phones!",
        "col_id": "ID",
        "col_device": "📱 Device Name",
        "col_rarity": "✨ Rarity",
        "col_price": "💰 Price (pts)",
        "col_date": "🕒 Obtained At",
        "clearhist_title": "🗑️ CLEAR INVENTORY HISTORY",
        "clearhist_choose": "Choose clear option:",
        "clearhist_opt1": "1 -> Clear ALL history (delete all dropped phones)",
        "clearhist_opt2": "2 -> Delete specific phone model from history",
        "clearhist_opt0": "0 -> Cancel",
        "clearhist_confirm_all": "Are you sure you want to delete ALL inventory history? (yes/no)",
        "clearhist_all_deleted": "✅ All inventory history has been cleared.",
        "clearhist_select_device": "Select phone device number to delete:",
        "clearhist_deleted_count": "✅ Deleted {} records of '{}'.",
        "chat_title": "💬 LAST {} MESSAGES WITH {}",
        "login_title": "🔐 TELEGRAM MTPROTO AUTHENTICATION",
        "login_choose_method": "Select login method",
        "login_method_1": "1 -> Fast login via QR-Code (Recommended, scan in Telegram app)",
        "login_method_2": "2 -> Login by Phone Number (5-digit code in Telegram App / SMS)",
        "login_method_3": "3 -> Paste Telethon StringSession directly",
        "login_cancel": "0 -> Cancel",
        "phone_login_title": "📱 LOGIN BY PHONE NUMBER",
        "phone_login_hint": "Enter your phone number in international format (e.g. +380981234567) or type '0' to cancel:",
        "phone_empty_hint": "[yellow]Please enter a valid phone number (e.g. +380981234567) or '0' to cancel.[/yellow]",
        "phone_input_prompt": "Phone number > ",
        "phone_sending": "Sending authorization request for {}...",
        "phone_code_app_sent": "[bold bright_green]✅ Verification code sent to your Telegram App![/bold bright_green]\n[bold bright_yellow]👉 OPEN YOUR TELEGRAM APP (on phone or PC).[/bold bright_yellow]\n[bold white]The code arrived in the official chat [cyan]'Telegram' / 'Service Notifications'[/cyan] (NOT by SMS)![/bold white]",
        "phone_code_sms_sent": "[bold bright_green]✅ Verification code sent via SMS![/bold bright_green]\n[bold bright_yellow]👉 Check standard SMS messages on your phone.[/bold bright_yellow]",
        "phone_code_call_sent": "[bold yellow]📞 Telegram will call your phone and dictate the verification code.[/bold yellow]",
        "phone_code_general_sent": "[bold green]✅ Verification code dispatched![/bold green]",
        "phone_code_prompt": "Enter verification code (from Telegram / SMS) > ",
        "phone_2fa_notice": "Two-step verification (2FA Cloud Password) is enabled on this account!",
        "phone_2fa_prompt": "Enter your 2FA Cloud Password > ",
        "phone_auth_success": "Successfully authorized as {}!",
        "phone_err_invalid": "Invalid phone number: '{}'. Please verify your country code (+380...)!",
        "phone_err_code_invalid": "Invalid verification code! Please try again.",
        "phone_err_code_expired": "Verification code has expired. Please log in again.",
        "phone_err_flood": "Telegram temporary rate limit. Wait {} seconds.",
        "phone_err_general": "Login error: {}",
        "qr_title": "📱 SCAN QR CODE WITH TELEGRAM",
        "qr_hint": "Open Telegram -> Settings -> Devices -> Link Desktop Device",
        "qr_waiting": "Waiting for QR Code scan in Telegram App...",
        "qr_auth_success": "Authorized via QR Code as {}!",
        "qr_error": "QR Code login error: {}",
        "string_prompt": "Paste StringSession > ",
        "string_invalid": "Invalid StringSession!",
        "flash_table_title": "⚡ PHONEX OFFLINE FLASHING SESSIONS",
        "flash_status_label": "Auto-Flashing Status",
        "flash_enabled": "ENABLED (Auto-handling active)",
        "flash_disabled": "DISABLED (Auto-handling off)",
        "flash_options": "Options: [bold white]1[/bold white] Toggle ON/OFF  |  [bold white]r[/bold white] Refresh  |  [bold red]0[/bold red] Return to main menu",
        "flash_action_prompt": "Flashing action > ",
        "flash_toggled": "Auto-flashing module is now {}!",
        "flash_no_sessions": "No active flashing devices",
        "flash_waiting_bot": "Listening for bot messages...",
        "log_auto_on": "Auto-mode activated. Initial check dispatched.",
        "log_auto_off": "Auto-mode paused.",
        "log_manual_trigger": "Manual trigger '{}'...",
        "log_sending_cmd": "Sending command '{}'...",
        "log_drop_received": "🎁 Drop received: {} [{}] ({} pts)!",
        "log_cooldown_detected": "Cooldown: {} (+{}s jitter). Next: {}.",
        "log_wait_received": "Wait message received. Next retry in {}.",
        "log_cycle_success": "Success! Next cycle in {}.",
        "log_no_reply": "Bot did not reply within 25s. Retrying in {}s.",
        "log_session_revoked": "Saved session is no longer authorized. Please log in again using 'login'.",
        "log_logged_out": "Logged out successfully. Session cleared.",
        "log_bot_confirmed": "Target bot confirmed: {} ({})"
    },
    "ua": {
        "title": "⚡ PHONEX SOFT v1.0",
        "user": "Користувач",
        "target": "Ціль",
        "command": "Команда",
        "not_authorized": "Не авторизовано",
        "status_title": "СТАТУС",
        "timer_title": "ТАЙМЕР",
        "stats_title": "СТАТИСТИКА & ДРОПИ",
        "latest_drop_title": "🎁 ОСТАННІЙ ОТРИМАНИЙ ДРОП",
        "bot_reply_title": "💬 ВІДПОВІДЬ БОТА",
        "recent_logs_title": "📋 ОСТАННІ ПОДІЇ",
        "commands_guide_title": "📖 ДОВІДКА КОМАНД",
        "state_disconnected": "🔴 ВІДКЛЮЧЕНО",
        "state_paused": "⏸️ ПРИЗУПИНЕНО",
        "state_rolling": "🎲 РОЛИМО...",
        "state_active": "🟢 АКТИВНО (АВТО)",
        "state_connecting": "🟡 ПІДКЛЮЧЕННЯ...",
        "hint_login": "Введіть 'login' для входу",
        "hint_start": "Введіть 'on' для запуску",
        "hint_rolling": "Надсилаємо команду боту",
        "hint_active": "Авто-рол увімкнено",
        "hint_connecting": "Авторизація сесії...",
        "timer_ready": "⚡ ГОТОВО ДО РОЛУ",
        "timer_sending": "Запит відправляється...",
        "timer_paused": "Таймер на паузі",
        "stat_sent": "Відправлено",
        "stat_success": "Успішних",
        "stat_cooldown": "Кулдаунів",
        "stat_errors": "Помилок",
        "stat_inventory": "У базі (invlast)",
        "no_drops_yet": "Дропів у базі поки немає. Зробіть рол!",
        "no_bot_replies": "Повідомлень від бота ще немає.",
        "log_empty": "Журнал порожній...",
        "cmd_prompt_hint": "Введіть [bold cyan]help[/bold cyan] для довідки, [bold cyan]r[/bold cyan] для оновлення, або [bold green]on[/bold green] для запуску.",
        "input_prompt": "\nКоманда > ",
        "choice_prompt": "Вибір",
        "unknown_cmd": "Невідома команда '{}'. Введіть 'help'.",
        "press_enter": "\nНатисніть Enter для повернення...",
        "shutdown_msg": "\n[bold yellow]Зупинка та збереження сесії...[/bold yellow]",
        "shutdown_done": "[bold green]Роботу успішно завершено. Сесію збережено![/bold green]\n",
        "lang_switched": "Мову змінено на Українську.",
        "inv_title": "📱 ІНВЕНТАР БОТА (/myphones)",
        "inv_choose": "Оберіть пункт за номером:",
        "inv_back_hint": "Введіть [bold red]0[/bold red] для виходу в головне меню.",
        "inv_flashed_blocked": "❌ Вибір 'Прошитые телефоны' вимкнено.",
        "inv_invalid_choice": "Некоректний номер кнопки!",
        "invlast_title": "🎁 ВИБИТІ АВТО-РОЛОМ ТЕЛЕФОНИ (invlast)",
        "invlast_total": "Всього у базі",
        "invlast_sum": "Сума",
        "invlast_empty": "У базі ще немає збережених дропів. Запустіть авто-рол командою 'on' або зробіть 'send'!",
        "col_id": "ID",
        "col_device": "📱 Назва пристрою",
        "col_rarity": "✨ Рідкість",
        "col_price": "💰 Ціна (pts)",
        "col_date": "🕒 Дата отримання",
        "clearhist_title": "🗑️ ОЧИЩЕННЯ ІСТОРІЇ ДРОПІВ",
        "clearhist_choose": "Оберіть варіант очищення:",
        "clearhist_opt1": "1 -> Очистити повністю всю історію телефонів",
        "clearhist_opt2": "2 -> Видалити історію вибиття конкретної моделі",
        "clearhist_opt0": "0 -> Скасувати",
        "clearhist_confirm_all": "Ви впевнені, що хочете видалити ВСЮ історію вибитих телефонів? (yes/no)",
        "clearhist_all_deleted": "✅ Всю історію дропів успішно очищено.",
        "clearhist_select_device": "Оберіть номер пристрою для видалення:",
        "clearhist_deleted_count": "✅ Видалено {} записів про '{}'.",
        "chat_title": "💬 ОСТАННІ {} ПОВІДОМЛЕНЬ У ЧАТІ З {}",
        "login_title": "🔐 АВТОРИЗАЦІЯ TELEGRAM MTPROTO",
        "login_choose_method": "Оберіть спосіб входу",
        "login_method_1": "1 -> Швидкий вхід через QR-код (Рекомендовано, сканувати у додатку TG)",
        "login_method_2": "2 -> Вхід за номером телефону (Код у додатку Telegram / SMS)",
        "login_method_3": "3 -> Вставити готову StringSession",
        "login_cancel": "0 -> Скасувати",
        "phone_login_title": "📱 ВХІД ЗА НОМЕРОМ ТЕЛЕФОНУ",
        "phone_login_hint": "Введіть номер у міжнародному форматі (наприклад: +380981234567) або введіть '0' для скасування:",
        "phone_empty_hint": "[yellow]Будь ласка, введіть номер телефону (наприклад: +380981234567) або '0' для скасування.[/yellow]",
        "phone_input_prompt": "Номер телефону > ",
        "phone_sending": "Надсилаємо запит авторизації для {}...",
        "phone_code_app_sent": "[bold bright_green]✅ Код підтвердження надіслано в додаток Telegram![/bold bright_green]\n[bold bright_yellow]👉 ВІДКРИЙТЕ ВАШ ДОДАТОК TELEGRAM (на телефоні або ПК).[/bold bright_yellow]\n[bold white]Код надійшов у службовий чат [cyan]'Telegram' / 'Служебные уведомления'[/cyan] (НЕ в SMS)![/bold white]",
        "phone_code_sms_sent": "[bold bright_green]✅ Код підтвердження надіслано через SMS![/bold bright_green]\n[bold bright_yellow]👉 Перевірте звичайні SMS-повідомлення на телефоні.[/bold bright_yellow]",
        "phone_code_call_sent": "[bold yellow]📞 Telegram зателефонує вам і продиктує код підтвердження.[/bold yellow]",
        "phone_code_general_sent": "[bold green]✅ Код надіслано![/bold green]",
        "phone_code_prompt": "Введіть код підтвердження (з Telegram / SMS) > ",
        "phone_2fa_notice": "У вашому акаунті увімкнено 2FA (двоетапну аутентифікацію)!",
        "phone_2fa_prompt": "Введіть ваш пароль 2FA (хмарний пароль) > ",
        "phone_auth_success": "Успішно авторизовано як {}!",
        "phone_err_invalid": "Некоректний номер телефону: '{}'. Перевірте код країни (+380...)!",
        "phone_err_code_invalid": "Невірний код підтвердження! Спробуйте ще раз.",
        "phone_err_code_expired": "Термін дії коду вичерпано. Спробуйте увійти знову.",
        "phone_err_flood": "Telegram обмежив спроби входу через ліміт. Зачекайте {} секунд.",
        "phone_err_general": "Помилка входу: {}",
        "qr_title": "📱 СКАНУВАННЯ QR-КОДУ ЧЕРЕЗ TELEGRAM",
        "qr_hint": "Відкрийте Telegram -> Налаштування -> Пристрої -> Підключити пристрій",
        "qr_waiting": "Очікуємо сканування QR-коду у додатку Telegram...",
        "qr_auth_success": "Авторизовано через QR-код як {}!",
        "qr_error": "Помилка входу через QR-код: {}",
        "string_prompt": "Вставте StringSession > ",
        "string_invalid": "Недійсна StringSession!",
        "flash_table_title": "⚡ АКТИВНІ СЕСІЇ ПРОШИВКИ ТЕЛЕФОНІВ",
        "flash_status_label": "Статус авто-прошивки",
        "flash_enabled": "УВІМКНЕНО (Авто-обробка активна)",
        "flash_disabled": "ВИМКНЕНО (Авто-обробка вимкнена)",
        "flash_options": "Опції: [bold white]1[/bold white] Увімкнути/Вимкнути  |  [bold white]r[/bold white] Оновити  |  [bold red]0[/bold red] Повернутися в головне меню",
        "flash_action_prompt": "Дія прошивки > ",
        "flash_toggled": "Авто-прошивка тепер {}!",
        "flash_no_sessions": "Немає активних сесій прошивки",
        "flash_waiting_bot": "Слухаємо повідомлення бота...",
        "log_auto_on": "Автоматичний режим увімкнено. Перший запит надіслано.",
        "log_auto_off": "Автоматичний режим призупинено.",
        "log_manual_trigger": "Ручний запуск '{}'...",
        "log_sending_cmd": "Надсилаємо команду '{}'...",
        "log_drop_received": "🎁 Отримано дроп: {} [{}] ({} pts)!",
        "log_cooldown_detected": "Кулдаун: {} (+{}с джитер). Наступний запуск: {}.",
        "log_wait_received": "Отримано повідомлення очікування. Повтор через {}.",
        "log_cycle_success": "Успіх! Наступний цикл через {}.",
        "log_no_reply": "Бот не відповів за 25с. Повтор через {}с.",
        "log_session_revoked": "Збережена сесія втратила дію. Будь ласка, увійдіть заново через команду 'login'.",
        "log_logged_out": "Успішно вийшли з акаунта. Сесію очищено.",
        "log_bot_confirmed": "Цільового бота підтверджено: {} ({})"
    },
    "ru": {
        "title": "⚡ PHONEX SOFT v1.0",
        "user": "Пользователь",
        "target": "Цель",
        "command": "Команда",
        "not_authorized": "Не авторизован",
        "status_title": "СТАТУС",
        "timer_title": "ТАЙМЕР",
        "stats_title": "СТАТИСТИКА И ДРОПЫ",
        "latest_drop_title": "🎁 ПОСЛЕДНИЙ ВЫБИТЫЙ ДРОП",
        "bot_reply_title": "💬 ОТВЕТ БОТА",
        "recent_logs_title": "📋 ЖУРНАЛ СОБЫТИЙ",
        "commands_guide_title": "📖 СПИСОК КОМАНД",
        "state_disconnected": "🔴 ОТКЛЮЧЕНО",
        "state_paused": "⏸️ ПРИОСТАНОВЛЕНО",
        "state_rolling": "🎲 КРУТИМ...",
        "state_active": "🟢 АКТИВНО (АВТО)",
        "state_connecting": "🟡 ПОДКЛЮЧЕНИЕ...",
        "hint_login": "Введите 'login' для входа",
        "hint_start": "Введите 'on' для запуска",
        "hint_rolling": "Отправляем команду боту",
        "hint_active": "Авто-ролл включен",
        "hint_connecting": "Авторизация сессии...",
        "timer_ready": "⚡ ГОТОВО К РОЛЛУ",
        "timer_sending": "Запрос отправляется...",
        "timer_paused": "Таймер на паузе",
        "stat_sent": "Отправлено",
        "stat_success": "Успешных",
        "stat_cooldown": "Кулдаунов",
        "stat_errors": "Ошибок",
        "stat_inventory": "В базе (invlast)",
        "no_drops_yet": "Дропов в базе пока нет. Сделайте ролл!",
        "no_bot_replies": "Сообщений от бота ещё нет.",
        "log_empty": "Журнал пуст...",
        "cmd_prompt_hint": "Введите [bold cyan]help[/bold cyan] для справки, [bold cyan]r[/bold cyan] для обновления, или [bold green]on[/bold green] для запуска.",
        "input_prompt": "\nКоманда > ",
        "choice_prompt": "Выбор",
        "unknown_cmd": "Неизвестная команда '{}'. Введите 'help'.",
        "press_enter": "\nНажмите Enter для возврата...",
        "shutdown_msg": "\n[bold yellow]Остановка и сохранение сессии...[/bold yellow]",
        "shutdown_done": "[bold green]Работа успешно завершена. Сессия сохранена![/bold green]\n",
        "lang_switched": "Язык переключен на Русский.",
        "inv_title": "📱 ИНВЕНТАРЬ БОТА (/myphones)",
        "inv_choose": "Выберите пункт по номеру:",
        "inv_back_hint": "Введите [bold red]0[/bold red] для возврата в главное меню.",
        "inv_flashed_blocked": "❌ Выбор 'Прошитые телефоны' отключен.",
        "inv_invalid_choice": "Некорректный номер кнопки!",
        "invlast_title": "🎁 ВЫБИТЫЕ АВТО-РОЛЛОМ ТЕЛЕФОНЫ (invlast)",
        "invlast_total": "Всего в базе",
        "invlast_sum": "Сумма",
        "invlast_empty": "В базе ещё нет сохранённых дропов. Запустите авто-ролл командой 'on' или сделайте 'send'!",
        "col_id": "ID",
        "col_device": "📱 Название устройства",
        "col_rarity": "✨ Редкость",
        "col_price": "💰 Цена (pts)",
        "col_date": "🕒 Дата получения",
        "clearhist_title": "🗑️ ОЧИСТКА ИСТОРИИ ДРОПОВ",
        "clearhist_choose": "Выберите вариант очистки:",
        "clearhist_opt1": "1 -> Очистить полностью всю историю телефонов",
        "clearhist_opt2": "2 -> Удалить историю выбивания конкретной модели",
        "clearhist_opt0": "0 -> Отмена",
        "clearhist_confirm_all": "Вы уверены, что хотите удалить ВСЮ историю выбитых телефонов? (yes/no)",
        "clearhist_all_deleted": "✅ Вся история дропов успешно очищена.",
        "clearhist_select_device": "Выберите номер устройства для удаления:",
        "clearhist_deleted_count": "✅ Удалено {} записей о '{}'.",
        "chat_title": "💬 ПОСЛЕДНИЕ {} СООБЩЕНИЙ В ЧАТЕ С {}",
        "login_title": "🔐 АВТОРИЗАЦИЯ TELEGRAM MTPROTO",
        "login_choose_method": "Выберите способ входа",
        "login_method_1": "1 -> Быстрый вход через QR-код (Рекомендуется, сканировать в Telegram)",
        "login_method_2": "2 -> Вход по номеру телефона (Код в приложении Telegram / SMS)",
        "login_method_3": "3 -> Вставить готовую StringSession",
        "login_cancel": "0 -> Отмена",
        "phone_login_title": "📱 ВХОД ПО НОМЕРУ ТЕЛЕФОНА",
        "phone_login_hint": "Введите номер в международном формате (например: +380981234567) или '0' для отмены:",
        "phone_empty_hint": "[yellow]Пожалуйста, введите номер телефона (например: +380981234567) или '0' для отмены.[/yellow]",
        "phone_input_prompt": "Номер телефона > ",
        "phone_sending": "Отправляем запрос авторизации для {}...",
        "phone_code_app_sent": "[bold bright_green]✅ Код подтверждения отправлен в приложение Telegram![/bold bright_green]\n[bold bright_yellow]👉 ОТКРОЙТЕ ВАШЕ ПРИЛОЖЕНИЕ TELEGRAM (на телефоне или ПК).[/bold bright_yellow]\n[bold white]Код пришёл в служебный чат [cyan]'Telegram' / 'Служебные уведомления'[/cyan] (НЕ по SMS)![/bold white]",
        "phone_code_sms_sent": "[bold bright_green]✅ Код подтверждения отправлен по SMS![/bold bright_green]\n[bold bright_yellow]👉 Проверьте обычные SMS-сообщения на вашем телефоне.[/bold bright_yellow]",
        "phone_code_call_sent": "[bold yellow]📞 Telegram позвонит вам и продиктует код подтверждения.[/bold yellow]",
        "phone_code_general_sent": "[bold green]✅ Код отправлен![/bold green]",
        "phone_code_prompt": "Введите код подтверждения (из Telegram / SMS) > ",
        "phone_2fa_notice": "В вашем аккаунте включена 2FA (двухэтапная аутентификация)!",
        "phone_2fa_prompt": "Введите ваш пароль 2FA (облачный пароль) > ",
        "phone_auth_success": "Успешно авторизован как {}!",
        "phone_err_invalid": "Некорректный номер телефона: '{}'. Проверьте код страны (+380...)!",
        "phone_err_code_invalid": "Неверный код подтверждения! Попробуйте ещё раз.",
        "phone_err_code_expired": "Срок действия кода истёк. Попробуйте войти снова.",
        "phone_err_flood": "Telegram временно ограничил попытки входа. Подождите {} секунд.",
        "phone_err_general": "Ошибка входа: {}",
        "qr_title": "📱 СКАНИРОВАНИЕ QR-КОДА ЧЕРЕЗ TELEGRAM",
        "qr_hint": "Откройте Telegram -> Настройки -> Устройства -> Подключить устройство",
        "qr_waiting": "Ожидаем сканирования QR-кода в Telegram...",
        "qr_auth_success": "Авторизован через QR-код как {}!",
        "qr_error": "Ошибка входа через QR-код: {}",
        "string_prompt": "Вставьте StringSession > ",
        "string_invalid": "Недействительная StringSession!",
        "flash_table_title": "⚡ АКТИВНЫЕ СЕССИИ ПРОШИВКИ ТЕЛЕФОНОВ",
        "flash_status_label": "Статус авто-прошивки",
        "flash_enabled": "ВКЛЮЧЕНО (Авто-обработка активна)",
        "flash_disabled": "ВЫКЛЮЧЕНО (Авто-обработка выключена)",
        "flash_options": "Опции: [bold white]1[/bold white] Включить/Выключить  |  [bold white]r[/bold white] Обновить  |  [bold red]0[/bold red] Вернуться в главное меню",
        "flash_action_prompt": "Действие прошивки > ",
        "flash_toggled": "Авто-прошивка теперь {}!",
        "flash_no_sessions": "Нет активных устройств на прошивке",
        "flash_waiting_bot": "Ожидаем сообщений от бота...",
        "log_auto_on": "Автоматический режим включен. Первый запрос отправлен.",
        "log_auto_off": "Автоматический режим приостановлен.",
        "log_manual_trigger": "Ручной запуск '{}'...",
        "log_sending_cmd": "Отправляем команду '{}'...",
        "log_drop_received": "🎁 Получен дроп: {} [{}] ({} pts)!",
        "log_cooldown_detected": "Кулдаун: {} (+{}с джиттер). Следующий запуск: {}.",
        "log_wait_received": "Получено сообщение ожидания. Повтор через {}.",
        "log_cycle_success": "Успех! Следующий цикл через {}.",
        "log_no_reply": "Бот не ответил за 25с. Повтор через {}с.",
        "log_session_revoked": "Сохранённая сессия устарела. Пожалуйста, войдите снова с помощью 'login'.",
        "log_logged_out": "Успешно вышли из аккаунта. Сессия очищена.",
        "log_bot_confirmed": "Целевой бот подтверждён: {} ({})"
    }
}


class TerminalAutomator:
    def __init__(self):
        self.console = Console()
        self.config: AppConfig = AppConfig.load()
        if not self.config.language:
            self.config.language = "en"

        self.db = InventoryDB()
        self.flasher = DeviceFlashingManager(automator=self)
        self.client: Optional[TelegramClient] = None
        self.current_user = None
        self.target_entity = None

        self.state: str = STATE_DISCONNECTED
        self.is_running: bool = self.config.auto_start
        self.is_sending: bool = False
        self.next_run_timestamp: Optional[float] = None

        self.total_sent: int = 0
        self.success_count: int = 0
        self.cooldown_count: int = 0
        self.error_count: int = 0

        self.last_response_text: str = self.tr("no_bot_replies")
        self.last_response_time: Optional[float] = None
        self.logs: List[Tuple[str, str, str]] = []
        self.max_logs: int = 10

        self.data_dir = Path(__file__).resolve().parent / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.data_dir / "session.dat"

        self._runner_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        self._is_interacting: bool = False
        self._current_input_buffer: str = ""

    def tr(self, key: str, *args) -> str:
        lang_dict = TEXTS.get(self.config.language, TEXTS["en"])
        template = lang_dict.get(key, TEXTS["en"].get(key, key))
        if args:
            try:
                return template.format(*args)
            except Exception:
                return template
        return template

    async def _prompt_input(self, prompt_text: str = "") -> str:
        loop = asyncio.get_running_loop()
        sys.stdout.flush()
        val = await loop.run_in_executor(None, input, prompt_text)
        return val.strip()

    def add_log(self, text: str, level: str = "info"):
        now_str = datetime.now().strftime("%H:%M:%S")
        self.logs.append((now_str, text, level))
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)

    def load_saved_session(self) -> str:
        if self.session_file.exists():
            try:
                return self.session_file.read_text(encoding="utf-8").strip()
            except Exception:
                return ""
        return ""

    def save_session(self, session_str: str):
        try:
            self.session_file.write_text(session_str.strip(), encoding="utf-8")
        except Exception:
            pass

    def clear_session(self):
        if self.session_file.exists():
            try:
                self.session_file.unlink()
            except Exception:
                pass

    def handle_session_revoked(self, reason: str = "Session terminated"):
        self.clear_session()
        self.current_user = None
        self.target_entity = None
        self.state = STATE_DISCONNECTED
        self.is_running = False
        self.next_run_timestamp = None
        self.add_log(f"⚠️ {reason}. Please log in again using 'login'.", "warning")

    async def init_telethon_client(self, session_str: Optional[str] = None) -> TelegramClient:
        if self.client and self.client.is_connected():
            try:
                await self.client.disconnect()
            except Exception:
                pass

        if session_str is None:
            session_str = self.load_saved_session()

        string_session = StringSession(session_str)
        self.client = TelegramClient(string_session, self.config.api_id, self.config.api_hash)
        return self.client

    async def connect_and_login_silent(self) -> bool:
        saved_session = self.load_saved_session()
        if not self.config.api_id or not self.config.api_hash:
            return False

        self.state = STATE_CONNECTING
        try:
            await self.init_telethon_client(saved_session)
            await self.client.connect()

            if await self.client.is_user_authorized():
                self.current_user = await self.client.get_me()
                saved_str = self.client.session.save()
                self.save_session(saved_str)

                u_name = f"@{self.current_user.username}" if self.current_user.username else self.current_user.first_name
                self.state = STATE_CONNECTED
                self.add_log(f"Auto-login verified: {u_name}", "success")
                await self.resolve_target_bot(self.config.target_bot)
                return True
            else:
                self.handle_session_revoked(self.tr("log_session_revoked"))
                return False
        except AUTH_TERMINATED_ERRORS:
            self.handle_session_revoked("Telegram session was revoked or expired")
            return False
        except Exception as e:
            self.state = STATE_DISCONNECTED
            self.add_log(f"Connection failed: {e}", "error")
            return False

    async def interactive_login(self):
        self._is_interacting = True
        loop = asyncio.get_running_loop()
        self.console.clear()
        self.console.print(Panel(
            Align.center(f"[bold cyan]{self.tr('login_title')}[/bold cyan]"),
            border_style="cyan"
        ))

        self.console.print(f"\n[bold]{self.tr('login_choose_method')}:[/bold]")
        self.console.print(f"  [bold green]1[/bold green] -> [cyan]{self.tr('login_method_1')}[/cyan]")
        self.console.print(f"  [bold green]2[/bold green] -> [cyan]{self.tr('login_method_2')}[/cyan]")
        self.console.print(f"  [bold green]3[/bold green] -> [cyan]{self.tr('login_method_3')}[/cyan]")
        self.console.print(f"  [bold red]0[/bold red] -> [dim]{self.tr('login_cancel')}[/dim]")

        choice = await self._prompt_input(f"\n{self.tr('choice_prompt')} [1/2/3/0] > ")
        if not choice:
            choice = "1"

        if choice == "1":
            try:
                await self.init_telethon_client("")
                await self.client.connect()
                qr_login = await self.client.qr_login()

                self.console.clear()
                self.console.print(Panel(
                    Align.center(f"[bold cyan]{self.tr('qr_title')}[/bold cyan]"),
                    border_style="cyan"
                ))
                self.console.print(f"[dim]{self.tr('qr_hint')}[/dim]\n")

                if HAS_QRCODE:
                    qr = qrcode.QRCode()
                    qr.add_data(qr_login.url)
                    qr.print_ascii(invert=True)
                else:
                    self.console.print(f"[yellow]{qr_login.url}[/yellow]")

                self.console.print(f"\n[bold cyan]{self.tr('qr_waiting')}[/bold cyan]")
                try:
                    user = await qr_login.wait(timeout=120)
                except SessionPasswordNeededError:
                    self.console.print(f"\n[yellow]{self.tr('phone_2fa_notice')}[/yellow]")
                    pwd = await self._prompt_input(self.tr('phone_2fa_prompt'))
                    user = await self.client.sign_in(password=pwd)

                self.current_user = user or await self.client.get_me()
                saved_str = self.client.session.save()
                self.save_session(saved_str)
                self.state = STATE_CONNECTED
                u_name = f"@{self.current_user.username}" if self.current_user.username else self.current_user.first_name
                self.console.print(f"\n[bold green]✅ {self.tr('qr_auth_success', u_name)}[/bold green]")
                self.add_log(f"Authorized via QR: {u_name}", "success")
                await self.resolve_target_bot(self.config.target_bot)
                await asyncio.sleep(2.0)
            except Exception as e:
                self.console.print(f"\n[bold red]{self.tr('qr_error', str(e))}[/bold red]")
                await self._prompt_input(self.tr('press_enter'))

        elif choice == "2":
            await self.init_telethon_client("")
            await self.client.connect()

            self.console.clear()
            self.console.print(Panel(
                Align.center(f"[bold cyan]{self.tr('phone_login_title')}[/bold cyan]"),
                border_style="cyan"
            ))
            self.console.print(f"\n[bold white]{self.tr('phone_login_hint')}[/bold white]\n")

            raw_phone = ""
            while not raw_phone:
                raw_phone = await self._prompt_input(self.tr('phone_input_prompt'))
                if raw_phone == "0":
                    self._is_interacting = False
                    return
                if not raw_phone:
                    self.console.print(self.tr('phone_empty_hint'))

            import re
            phone = re.sub(r"[^\d+]", "", raw_phone)
            if phone.startswith("0") and len(phone) == 10:
                phone = "+38" + phone
            elif not phone.startswith("+"):
                phone = "+" + phone

            self.console.print(f"\n[dim]{self.tr('phone_sending', phone)}[/dim]")

            try:
                sent = await self.client.send_code_request(phone)

                import telethon.tl.types.auth as auth_types
                if isinstance(sent.type, auth_types.SentCodeTypeApp):
                    dest_msg = self.tr('phone_code_app_sent')
                elif isinstance(sent.type, auth_types.SentCodeTypeSms):
                    dest_msg = self.tr('phone_code_sms_sent')
                elif isinstance(sent.type, auth_types.SentCodeTypeCall):
                    dest_msg = self.tr('phone_code_call_sent')
                else:
                    dest_msg = self.tr('phone_code_general_sent')

                self.console.print(f"\n{dest_msg}\n")

                code_raw = ""
                while not code_raw:
                    code_raw = await self._prompt_input(self.tr('phone_code_prompt'))
                    if code_raw == "0":
                        self._is_interacting = False
                        return

                code = re.sub(r"\D", "", code_raw)

                try:
                    await self.client.sign_in(phone=phone, code=code, phone_code_hash=sent.phone_code_hash)
                except SessionPasswordNeededError:
                    self.console.print(f"\n[yellow]{self.tr('phone_2fa_notice')}[/yellow]")
                    pwd = await self._prompt_input(self.tr('phone_2fa_prompt'))
                    await self.client.sign_in(password=pwd)

                self.current_user = await self.client.get_me()
                saved_str = self.client.session.save()
                self.save_session(saved_str)
                self.state = STATE_CONNECTED
                u_name = f"@{self.current_user.username}" if self.current_user.username else self.current_user.first_name
                self.console.print(f"\n[bold green]✅ {self.tr('phone_auth_success', u_name)}[/bold green]")
                self.add_log(f"Authorized via Phone: {u_name}", "success")
                await self.resolve_target_bot(self.config.target_bot)
                await asyncio.sleep(2.0)

            except FloodWaitError as e:
                self.console.print(f"\n[bold red]{self.tr('phone_err_flood', e.seconds)}[/bold red]")
                await self._prompt_input(self.tr('press_enter'))
            except Exception as e:
                err_str = str(e)
                if "PHONE_NUMBER_INVALID" in err_str:
                    self.console.print(f"\n[bold red]{self.tr('phone_err_invalid', phone)}[/bold red]")
                elif "PHONE_CODE_INVALID" in err_str:
                    self.console.print(f"\n[bold red]{self.tr('phone_err_code_invalid')}[/bold red]")
                elif "PHONE_CODE_EXPIRED" in err_str:
                    self.console.print(f"\n[bold red]{self.tr('phone_err_code_expired')}[/bold red]")
                else:
                    self.console.print(f"\n[bold red]{self.tr('phone_err_general', str(e))}[/bold red]")
                await self._prompt_input(self.tr('press_enter'))

        elif choice == "3":
            session_str = await self._prompt_input(f"\n{self.tr('string_prompt')}")
            if session_str:
                self.save_session(session_str)
                await self.init_telethon_client(session_str)
                await self.client.connect()
                if await self.client.is_user_authorized():
                    self.current_user = await self.client.get_me()
                    self.state = STATE_CONNECTED
                    u_name = f"@{self.current_user.username}" if self.current_user.username else self.current_user.first_name
                    self.console.print(f"\n[bold green]✅ {self.tr('phone_auth_success', u_name)}[/bold green]")
                    await asyncio.sleep(1.5)
                else:
                    self.console.print(f"\n[bold red]{self.tr('string_invalid')}[/bold red]")
                    await asyncio.sleep(2.0)

        if self.state == STATE_CONNECTED:
            await self.resolve_target_bot(self.config.target_bot)

        self._is_interacting = False

    async def resolve_target_bot(self, username: str) -> bool:
        if not self.client or not self.client.is_connected():
            return False
        try:
            self.target_entity = await self.client.get_entity(username)
            self.config.target_bot = username
            title = getattr(self.target_entity, 'title', None) or getattr(self.target_entity, 'first_name', username)
            self.add_log(f"Target bot confirmed: {title} ({username})", "success")
            self._setup_flasher_events()
            return True
        except Exception as e:
            self.add_log(f"Lookup error for '{username}': {e}", "warning")
            self.target_entity = None
            return False

    def _setup_flasher_events(self):
        if not self.client or not self.target_entity:
            return
        try:
            self.client.remove_event_handler(self.flasher.on_bot_message_event)
        except Exception:
            pass
        self.client.add_event_handler(
            self.flasher.on_bot_message_event,
            events.NewMessage(chats=self.target_entity)
        )
        self.client.add_event_handler(
            self.flasher.on_bot_message_event,
            events.MessageEdited(chats=self.target_entity)
        )

    def turn_on(self):
        self.is_running = True
        self.state = STATE_WAITING
        self.next_run_timestamp = time.time()
        self.add_log(self.tr("log_auto_on"), "success")

    def turn_off(self):
        self.is_running = False
        self.state = STATE_PAUSED if self.state == STATE_CONNECTED else self.state
        self.next_run_timestamp = None
        self.add_log(self.tr("log_auto_off"), "warning")

    def force_send(self):
        if not self.target_entity:
            self.add_log("Target bot not resolved!", "error")
            return
        self.add_log(self.tr("log_manual_trigger", self.config.command), "info")
        self.next_run_timestamp = time.time()

    async def _send_and_handle(self):
        if not self.target_entity or not self.client or not self.client.is_connected():
            self.next_run_timestamp = time.time() + 15
            return

        self.is_sending = True
        self.state = STATE_ROLLING
        cmd = self.config.command
        self.add_log(self.tr("log_sending_cmd", cmd), "info")

        try:
            self.total_sent += 1
            sent_msg = await self.client.send_message(self.target_entity, cmd)
            resp_text = await self._wait_for_reply(sent_msg.id, timeout=25.0)

            if resp_text:
                self.last_response_text = resp_text
                self.last_response_time = time.time()

                drop = parse_drop_message(resp_text)
                if drop:
                    self.success_count += 1
                    self.db.add_drop(
                        device_name=drop["device_name"],
                        rarity=drop["rarity"],
                        price=drop["price"],
                        raw_message=resp_text
                    )
                    self.add_log(f"🎁 Drop received: {drop['device_name']} [{drop['rarity']}] ({drop['price']} pts)!", "success")

                wait_s = parse_cooldown_seconds(resp_text)
                if wait_s is not None and wait_s > 0:
                    self.cooldown_count += 1
                    planned_wait = calculate_wait_time(
                        wait_s,
                        fixed_jitter=self.config.safety_jitter_seconds
                    )
                    self.next_run_timestamp = time.time() + planned_wait
                    self.state = STATE_WAITING
                    self.add_log(
                        f"Cooldown detected: {format_duration_friendly(wait_s, self.config.language)} "
                        f"(+{self.config.safety_jitter_seconds}s jitter). Next: {format_duration_friendly(planned_wait, self.config.language)}.",
                        "warning"
                    )
                else:
                    if is_wait_message(resp_text):
                        self.cooldown_count += 1
                        fallback = 300
                        self.next_run_timestamp = time.time() + fallback
                        self.state = STATE_WAITING
                        self.add_log(f"Wait message received. Next retry in {format_duration_friendly(fallback, self.config.language)}.", "warning")
                    else:
                        self.success_count += 1
                        interval = self.config.default_interval_seconds
                        self.next_run_timestamp = time.time() + interval
                        self.state = STATE_WAITING
                        self.add_log(f"Success! Next cycle in {format_duration_friendly(interval, self.config.language)}.", "success")
            else:
                self.error_count += 1
                retry_wait = 60
                self.next_run_timestamp = time.time() + retry_wait
                self.state = STATE_WAITING
                self.add_log(f"Bot did not reply within 25s. Retrying in {retry_wait}s.", "warning")

        except AUTH_TERMINATED_ERRORS as e:
            self.error_count += 1
            self.handle_session_revoked("Session was terminated from another device")
        except FloodWaitError as e:
            self.error_count += 1
            wait_s = e.seconds + 5
            self.next_run_timestamp = time.time() + wait_s
            self.state = STATE_WAITING
            self.add_log(f"Telegram FloodWait: waiting {wait_s}s.", "error")
        except Exception as e:
            self.error_count += 1
            retry_wait = 60
            self.next_run_timestamp = time.time() + retry_wait
            self.state = STATE_WAITING
            self.add_log(f"Request error: {e}. Retrying in {retry_wait}s.", "error")
        finally:
            self.is_sending = False
            if self.is_running and self.state == STATE_ROLLING:
                self.state = STATE_WAITING

    async def _wait_for_reply(self, sent_msg_id: int, timeout: float = 25.0) -> Optional[str]:
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        @self.client.on(events.NewMessage(chats=self.target_entity))
        async def reply_handler(event):
            if event.message and event.message.id > sent_msg_id:
                t = event.message.raw_text or event.message.message or ""
                if not future.done():
                    future.set_result(t)

        try:
            await asyncio.sleep(1.0)
            async for msg in self.client.iter_messages(self.target_entity, limit=3):
                if msg.id > sent_msg_id:
                    t = msg.raw_text or msg.message or ""
                    if not future.done():
                        future.set_result(t)
                    break
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self.client.remove_event_handler(reply_handler)

    async def _background_loop(self):
        while not self._stop_event.is_set():
            try:
                if self.is_running and not self.is_sending and self.next_run_timestamp is not None:
                    if time.time() >= self.next_run_timestamp:
                        self.next_run_timestamp = None
                        await self._send_and_handle()
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.add_log(f"Background task exception: {e}", "error")
                await asyncio.sleep(2.0)


    def get_remaining_seconds(self) -> int:
        if not self.is_running or self.next_run_timestamp is None:
            return 0
        return max(0, int(self.next_run_timestamp - time.time()))

    def render_header(self) -> Panel:
        w = self.console.width
        user_str = f"@{self.current_user.username}" if (self.current_user and self.current_user.username) else self.tr("not_authorized")
        user_style = "bold green" if self.current_user else "bold red"

        if w < 75:
            t = Text()
            t.append("⚡ PHONEX SOFT ", style="bold bright_white on blue")
            t.append("v1.0\n", style="bold black on bright_cyan")
            t.append(f"{self.tr('user')}: {user_str}  │  ", style=user_style)
            t.append(f"{self.tr('target')}: {self.config.target_bot} ({self.config.command})", style="bold cyan")
            return Panel(t, border_style="blue", padding=(0, 1))
        else:
            t = Text()
            t.append("⚡ PHONEX SOFT ", style="bold bright_white on blue")
            t.append("v1.0 ", style="bold black on bright_cyan")
            t.append(" │ ", style="dim")
            t.append(f"{self.tr('user')}: {user_str} ", style=user_style)
            t.append(" │ ", style="dim")
            t.append(f"{self.tr('target')}: {self.config.target_bot} ", style="bold cyan")
            t.append(" │ ", style="dim")
            t.append(f"{self.tr('command')}: {self.config.command}", style="bold yellow")
            return Panel(t, border_style="blue", padding=(0, 1))


    def render_dashboard(self) -> Table:
        w = self.console.width

        if not self.client or self.state == STATE_DISCONNECTED:
            s_text = Text.from_markup(f"[bold red]{self.tr('state_disconnected')}[/]\n[yellow]{self.tr('hint_login')}[/]")
            s_border = "red"
        elif not self.is_running:
            s_text = Text.from_markup(f"[bold yellow]{self.tr('state_paused')}[/]\n[dim]{self.tr('hint_start')}[/]")
            s_border = "yellow"
        elif self.is_sending:
            s_text = Text.from_markup(f"[bold bright_cyan]{self.tr('state_rolling')}[/]\n[cyan]{self.tr('hint_rolling')}[/]")
            s_border = "cyan"
        else:
            s_text = Text.from_markup(f"[bold green]{self.tr('state_active')}[/]\n[green]{self.tr('hint_active')}[/]")
            s_border = "green"
        panel_status = Panel(s_text, title=f"[bold]{self.tr('status_title')}[/]", border_style=s_border)

        rem = self.get_remaining_seconds()
        if not self.is_running:
            t_text = Text.from_markup(f"[dim]--:--:--[/]\n[dim]{self.tr('timer_paused')}[/]")
            t_border = "dim"
        elif rem > 0:
            t_text = Text.from_markup(f"[bold bright_magenta]⏳ {format_countdown(rem)}[/]\n[dim magenta]{format_duration_friendly(rem, self.config.language)}[/]")
            t_border = "magenta"
        else:
            t_text = Text.from_markup(f"[bold bright_green]{self.tr('timer_ready')}[/]\n[green]{self.tr('timer_sending')}[/]")
            t_border = "bright_green"
        panel_timer = Panel(t_text, title=f"[bold]{self.tr('timer_title')}[/]", border_style=t_border)

        stats = self.db.get_stats()
        tot_phones = stats["total_count"]
        tot_val = stats["total_price"]
        val_str = f"{int(tot_val):,}" if tot_val.is_integer() else f"{tot_val:,.1f}"

        stats_markup = (
            f"[dim]{self.tr('stat_sent')}:[/] [bold]{self.total_sent}[/]  "
            f"[green]{self.tr('stat_success')}:[/] [bold green]{self.success_count}[/]\n"
            f"[yellow]{self.tr('stat_cooldown')}:[/] [bold yellow]{self.cooldown_count}[/]  "
            f"[red]{self.tr('stat_errors')}:[/] [bold red]{self.error_count}[/]\n"
            f"[bold cyan]{self.tr('stat_inventory')}:[/] [bold white]{tot_phones}[/] ([bold bright_yellow]{val_str} pts[/])"
        )
        panel_stats = Panel(Text.from_markup(stats_markup), title=f"[bold]{self.tr('stats_title')}[/]", border_style="cyan")

        if w < 75:
            top_grid = Table.grid(expand=True)
            top_grid.add_column(ratio=1)
            top_grid.add_column(ratio=1)
            top_grid.add_row(panel_status, panel_timer)

            main_grid = Table.grid(expand=True)
            main_grid.add_row(top_grid)
            main_grid.add_row(panel_stats)
            return main_grid
        else:
            grid = Table.grid(expand=True)
            grid.add_column(ratio=3)
            grid.add_column(ratio=3)
            grid.add_column(ratio=4)
            if self.flasher.sessions:
                flash_panel = Panel(Text.from_markup(self.flasher.summary_badge(lang=self.config.language)), border_style="bright_cyan", padding=(0, 1))
                outer_grid = Table.grid(expand=True)
                outer_grid.add_row(grid)
                outer_grid.add_row(flash_panel)
                grid.add_row(panel_status, panel_timer, panel_stats)
                return outer_grid
            else:
                grid.add_row(panel_status, panel_timer, panel_stats)
                return grid


    def render_latest_drop_and_response(self) -> Table:
        w = self.console.width

        latest = self.db.get_latest_drop()
        if latest:
            p_val = latest["price"]
            p_str = f"{int(p_val):,}" if p_val.is_integer() else f"{p_val:,.1f}"
            drop_text = Text.from_markup(
                f"[bold bright_white]📱 {escape(latest['device_name'])}[/]\n"
                f"[bold magenta]{self.tr('col_rarity')}:[/] [bold yellow]{escape(latest['rarity'])}[/]  │  "
                f"[bold magenta]{self.tr('col_price')}:[/] [bold bright_green]{p_str} pts[/]\n"
                f"[dim]{self.tr('col_date')}: {latest['created_at']}[/]"
            )
        else:
            drop_text = Text.from_markup(f"[dim]{self.tr('no_drops_yet')}[/]")
        panel_drop = Panel(drop_text, title=f"[bold bright_yellow]{self.tr('latest_drop_title')}[/]", border_style="yellow")

        t_str = f" ({datetime.fromtimestamp(self.last_response_time).strftime('%H:%M:%S')})" if self.last_response_time else ""
        resp = self.last_response_text
        if len(resp) > 280:
            resp = resp[:277] + "..."
        panel_resp = Panel(
            Text(resp, style="italic bright_white"),
            title=f"[bold cyan]{self.tr('bot_reply_title')}{t_str}[/]",
            border_style="dim cyan"
        )

        grid = Table.grid(expand=True)
        if w < 75:
            grid.add_row(panel_drop)
            grid.add_row(panel_resp)
        else:
            grid.add_column(ratio=5)
            grid.add_column(ratio=5)
            grid.add_row(panel_drop, panel_resp)
        return grid


    def render_logs(self) -> Panel:
        table = Table.grid(expand=True)
        table.add_column(width=10)
        table.add_column()

        if not self.logs:
            table.add_row("", Text(f"[dim]{self.tr('log_empty')}[/]"))
        else:
            for ts, raw_msg, level in self.logs[-6:]:
                if level == "success":
                    style = "green"
                    prefix = "[bold green]✔[/bold green] "
                elif level == "warning":
                    style = "yellow"
                    prefix = "[bold yellow]![/bold yellow] "
                elif level == "error":
                    style = "bold red"
                    prefix = "[bold red]✖[/bold red] "
                else:
                    style = "white"
                    prefix = "[bold cyan]•[/bold cyan] "

                # Strip any existing duplicate prefix icon
                clean_msg = raw_msg
                for icon in ("✅", "⚠️", "❌", "ℹ️", "⚡"):
                    if clean_msg.startswith(icon):
                        clean_msg = clean_msg[len(icon):].strip()
                        break

                table.add_row(
                    Text(f"[{ts}]", style="dim"),
                    Text.from_markup(f"{prefix}[{style}]{escape(clean_msg)}[/{style}]")
                )

        return Panel(table, title=f"[bold bright_blue]{self.tr('recent_logs_title')}[/]", border_style="blue", padding=(0, 1))


    def render_help(self) -> Panel:
        t = Table.grid(expand=True, padding=(0, 1))
        t.add_column(style="bold bright_cyan", width=22)
        t.add_column(style="white")

        if self.config.language == "ua":
            t.add_row("on", "Увімкнути автоматичний режим")
            t.add_row("off (stop)", "Призупинити автоматичний режим")
            t.add_row("send (now)", "Примусово надіслати команду ролу")
            t.add_row("refresh (r)", "Оновити екран та таймер кулдауну")
            t.add_row("flash [on/off]", "Авто-прошивка девайсів (offline OCR)")
            t.add_row("inv", "Інтерактивний перегляд /myphones з кнопками")
            t.add_row("invlast", "Історія та статистика вибитих телефонів з SQLite")
            t.add_row("clearhistory", "Очистити всю або вибрану історію вибитих телефонів")
            t.add_row("lang (language)", "Змінити мову (english / русский / українська)")
            t.add_row("bot <@username>", "Змінити цільового бота")
            t.add_row("cmd </command>", "Змінити команду (напр: cmd /bonus)")
            t.add_row("chat [limit]", "Останні повідомлення чату з ботом")
            t.add_row("login", "Меню входу (QR-код / Телефон / StringSession)")
            t.add_row("logout", "Вийти з акаунта та видалити сесію")
            t.add_row("clear", "Очистити логи консолі")
            t.add_row("help (?)", "Показати або приховати цю довідку")
            t.add_row("exit (q)", "Зберегти сесію та завершити роботу")
        elif self.config.language == "ru":
            t.add_row("on", "Включить автоматический режим")
            t.add_row("off (stop)", "Приостановить автоматический режим")
            t.add_row("send (now)", "Принудительно отправить команду ролла")
            t.add_row("refresh (r)", "Обновить экран и таймер кулдауна")
            t.add_row("flash [on/off]", "Авто-прошивка девайсов (offline OCR)")
            t.add_row("inv", "Интерактивный просмотр /myphones с кнопками")
            t.add_row("invlast", "История и статистика выбитых телефонов из SQLite")
            t.add_row("clearhistory", "Очистить всю или выбранную историю телефонов")
            t.add_row("lang (language)", "Сменить язык (english / русский / украинский)")
            t.add_row("bot <@username>", "Сменить целевого бота")
            t.add_row("cmd </command>", "Сменить команду (напр: cmd /bonus)")
            t.add_row("chat [limit]", "Последние сообщения чата с ботом")
            t.add_row("login", "Меню входа (QR-код / Телефон / StringSession)")
            t.add_row("logout", "Выйти из аккаунта и удалить сессию")
            t.add_row("clear", "Очистить логи консоли")
            t.add_row("help (?)", "Показать или скрыть эту справку")
            t.add_row("exit (q)", "Сохранить сессию и завершить работу")
        else:
            t.add_row("on", "Start automated roll loop")
            t.add_row("off (stop)", "Pause automated roll loop")
            t.add_row("send (now)", "Force roll trigger immediately")
            t.add_row("refresh (r)", "Refresh screen and countdown timer")
            t.add_row("flash [on/off]", "Device firmware flashing manager (offline OCR)")
            t.add_row("inv", "Interactive /myphones explorer with buttons")
            t.add_row("invlast", "History & stats of dropped phones from SQLite")
            t.add_row("clearhistory", "Clear all or specific device drop history")
            t.add_row("lang (language)", "Switch language (english / русский / українська)")
            t.add_row("bot <@username>", "Change target bot username")
            t.add_row("cmd </command>", "Change trigger command (e.g. cmd /bonus)")
            t.add_row("chat [limit]", "Fetch recent chat history with bot")
            t.add_row("login", "Login menu (QR Code / Phone / StringSession)")
            t.add_row("logout", "Log out and delete session file")
            t.add_row("clear", "Clear console logs")
            t.add_row("help (?)", "Toggle this commands guide")
            t.add_row("exit (q)", "Save session and exit")

        return Panel(t, title=f"[bold bright_green]{self.tr('commands_guide_title')}[/]", border_style="green", padding=(0, 1))


    def draw_screen(self, show_help: bool = False):
        os.system('cls' if os.name == 'nt' else 'clear')
        self.console.print(self.render_header())
        self.console.print(self.render_dashboard())
        self.console.print(self.render_latest_drop_and_response())
        self.console.print(self.render_logs())
        if show_help:
            self.console.print(self.render_help())
        else:
            self.console.print(f"[dim]{self.tr('cmd_prompt_hint')}[/dim]")

    async def interactive_myphones_explorer(self):
        if not self.target_entity or not self.client or not self.client.is_connected():
            self.console.print("[bold red]No active connection to Telegram or target bot![/bold red]")
            time.sleep(2)
            return

        self._is_interacting = True
        loop = asyncio.get_running_loop()
        self.console.clear()
        self.console.print(Panel(Align.center(f"[bold cyan]{self.tr('inv_title')}...[/bold cyan]"), border_style="cyan"))

        cmd_msg = await self.client.send_message(self.target_entity, "/myphones")
        current_msg: Optional[Message] = await self._wait_for_message_with_buttons(cmd_msg.id, timeout=20.0)

        if not current_msg:
            self.console.print("[bold red]Bot did not reply with interactive buttons.[/bold red]")
            await loop.run_in_executor(None, input, self.tr("press_enter"))
            self._is_interacting = False
            return

        while True:
            self.console.clear()
            msg_text = current_msg.raw_text or current_msg.message or ""

            buttons_list = []
            if current_msg.buttons:
                for row in current_msg.buttons:
                    for btn in row:
                        buttons_list.append(btn)

            self.console.print(Panel(
                f"[bold bright_white]{escape(msg_text)}[/bold bright_white]",
                title=f"[bold bright_blue]{self.tr('inv_title')}[/bold bright_blue]",
                border_style="blue"
            ))

            if not buttons_list:
                await loop.run_in_executor(None, input, self.tr("press_enter"))
                break

            table = Table(title=f"[bold yellow]{self.tr('inv_choose')}[/bold yellow]", expand=True, border_style="dim yellow")
            table.add_column("№", style="bold bright_cyan", width=6, justify="center")
            table.add_column("Button", style="bold white")

            for idx, btn in enumerate(buttons_list, start=1):
                btn_title = btn.text or "[Button]"
                if "прошит" in btn_title.lower() or "flashed" in btn_title.lower():
                    btn_title = f"{btn_title} [dim red](Disabled)[/dim red]"
                table.add_row(str(idx), btn_title)

            self.console.print(table)
            self.console.print(f"[dim]{self.tr('inv_back_hint')}[/dim]")

            choice_str = await loop.run_in_executor(None, input, "\nChoice > ")
            choice_str = choice_str.strip()

            if choice_str == "0" or choice_str.lower() in ("q", "exit", "back"):
                break

            if not choice_str.isdigit():
                continue

            choice_idx = int(choice_str) - 1
            if 0 <= choice_idx < len(buttons_list):
                selected_btn = buttons_list[choice_idx]
                btn_name = selected_btn.text or ""

                if "прошит" in btn_name.lower() or "flashed" in btn_name.lower():
                    self.console.print(f"[bold red]{self.tr('inv_flashed_blocked')}[/bold red]")
                    time.sleep(1.5)
                    continue

                edit_future: asyncio.Future = loop.create_future()

                @self.client.on(events.MessageEdited(chats=self.target_entity))
                async def on_edit(event):
                    if event.message and event.message.id == current_msg.id:
                        if not edit_future.done():
                            edit_future.set_result(event.message)

                @self.client.on(events.NewMessage(chats=self.target_entity))
                async def on_new(event):
                    if event.message and event.message.id > current_msg.id:
                        if not edit_future.done():
                            edit_future.set_result(event.message)

                try:
                    await selected_btn.click()
                    try:
                        updated_msg = await asyncio.wait_for(edit_future, timeout=10.0)
                        current_msg = updated_msg
                    except asyncio.TimeoutError:
                        async for m in self.client.iter_messages(self.target_entity, limit=2):
                            if m.buttons:
                                current_msg = m
                                break
                except Exception as e:
                    self.console.print(f"[bold red]Click error: {e}[/bold red]")
                    time.sleep(1.5)
                finally:
                    self.client.remove_event_handler(on_edit)
                    self.client.remove_event_handler(on_new)
            else:
                self.console.print(f"[bold red]{self.tr('inv_invalid_choice')}[/bold red]")
                time.sleep(1)

        self._is_interacting = False

    async def _wait_for_message_with_buttons(self, sent_msg_id: int, timeout: float = 20.0) -> Optional[Message]:
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        @self.client.on(events.NewMessage(chats=self.target_entity))
        async def handler(event):
            if event.message and event.message.id > sent_msg_id and event.message.buttons:
                if not future.done():
                    future.set_result(event.message)

        try:
            await asyncio.sleep(0.5)
            async for msg in self.client.iter_messages(self.target_entity, limit=3):
                if msg.id > sent_msg_id and msg.buttons:
                    return msg
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self.client.remove_event_handler(handler)

    async def show_flashing_screen(self):
        self._is_interacting = True
        self.console.clear()

        table = self.flasher.render_overview_table(lang=self.config.language)
        self.console.print(table)

        status_txt = self.tr('flash_enabled') if self.flasher.enabled else self.tr('flash_disabled')
        self.console.print(f"\n[bold]{self.tr('flash_status_label')}:[/] [bold cyan]{status_txt}[/bold cyan]")
        self.console.print(f"[dim]{self.tr('flash_options')}[/dim]")

        while True:
            choice = await self._prompt_input(f"\n{self.tr('flash_action_prompt')}")
            choice = choice.strip().lower()
            if choice == "0" or not choice:
                break
            elif choice in ("1", "toggle", "on", "off"):
                self.flasher.enabled = not self.flasher.enabled
                st = self.tr('flash_enabled') if self.flasher.enabled else self.tr('flash_disabled')
                self.console.print(f"[bold green]{self.tr('flash_toggled', st)}[/bold green]")
                await asyncio.sleep(1.0)
                break
            elif choice in ("r", "refresh"):
                self.console.clear()
                self.console.print(self.flasher.render_overview_table(lang=self.config.language))
                status_txt = self.tr('flash_enabled') if self.flasher.enabled else self.tr('flash_disabled')
                self.console.print(f"\n[bold]{self.tr('flash_status_label')}:[/] [bold cyan]{status_txt}[/bold cyan]")
                self.console.print(f"[dim]{self.tr('flash_options')}[/dim]")

        self._is_interacting = False

    async def show_invlast_screen(self):
        self._is_interacting = True
        items = self.db.get_inventory(sort_by="highest_price")
        stats = self.db.get_stats()
        loop = asyncio.get_running_loop()

        self.console.clear()
        self.console.print(Panel(
            Align.center(f"[bold bright_yellow]{self.tr('invlast_title')}\n[bold white]{self.tr('invlast_total')}:[/] [bold cyan]{stats['total_count']}[/]  в”‚  [bold white]{self.tr('invlast_sum')}:[/] [bold bright_green]{stats['total_price']:,.1f} pts[/]"),
            border_style="yellow"
        ))

        if not items:
            self.console.print(f"\n[dim center]{self.tr('invlast_empty')}[/dim center]\n")
        else:
            t = Table(expand=True, border_style="dim yellow")
            t.add_column(self.tr("col_id"), width=6, style="dim", justify="center")
            t.add_column(self.tr("col_device"), style="bold white")
            t.add_column(self.tr("col_rarity"), style="bold")
            t.add_column(self.tr("col_price"), justify="right", style="bold green")
            t.add_column(self.tr("col_date"), style="dim")

            for item in items[:30]:
                rarity = item["rarity"]
                rarity_style = "yellow"
                r_lower = rarity.lower()
                if "legend" in r_lower: rarity_style = "bold bright_yellow"
                elif "myth" in r_lower: rarity_style = "bold bright_red"
                elif "secret" in r_lower: rarity_style = "bold bright_magenta"
                elif "epic" in r_lower: rarity_style = "bold magenta"
                elif "rare" in r_lower: rarity_style = "bold cyan"

                p_str = f"{int(item['price']):,}" if item["price"].is_integer() else f"{item['price']:,.2f}"
                t.add_row(
                    str(item["id"]),
                    item["device_name"],
                    f"[{rarity_style}]{rarity}[/{rarity_style}]",
                    f"{p_str} pts",
                    item["created_at"]
                )
            self.console.print(t)
            if len(items) > 30:
                self.console.print(f"[dim]Showing first 30 of {len(items)} items.[/dim]")

        await loop.run_in_executor(None, input, self.tr("press_enter"))
        self._is_interacting = False

    async def interactive_clear_history(self):
        self._is_interacting = True
        loop = asyncio.get_running_loop()
        self.console.clear()
        self.console.print(Panel(Align.center(f"[bold red]{self.tr('clearhist_title')}[/bold red]"), border_style="red"))

        self.console.print(f"\n[bold]{self.tr('clearhist_choose')}[/bold]")
        self.console.print(f"  [bold yellow]{self.tr('clearhist_opt1')}[/bold yellow]")
        self.console.print(f"  [bold cyan]{self.tr('clearhist_opt2')}[/bold cyan]")
        self.console.print(f"  [bold white]{self.tr('clearhist_opt0')}[/bold white]")

        choice = await loop.run_in_executor(None, input, "\nChoice > ")
        choice = choice.strip()

        if choice == "1":
            confirm = await loop.run_in_executor(None, input, f"\n{self.tr('clearhist_confirm_all')} > ")
            if confirm.strip().lower() in ("yes", "y", "так", "да"):
                self.db.clear_all()
                self.console.print(f"[bold green]{self.tr('clearhist_all_deleted')}[/bold green]")
                self.add_log("Inventory history fully cleared.", "warning")
                time.sleep(1.5)
        elif choice == "2":
            items = self.db.get_inventory(sort_by="newest")
            unique_devices = []
            seen = set()
            for it in items:
                name = it["device_name"]
                if name not in seen:
                    seen.add(name)
                    unique_devices.append(name)

            if not unique_devices:
                self.console.print(f"[dim]{self.tr('invlast_empty')}[/dim]")
                time.sleep(1.5)
            else:
                self.console.print(f"\n[bold]{self.tr('clearhist_select_device')}[/bold]")
                for idx, dev in enumerate(unique_devices, start=1):
                    self.console.print(f"  [bold cyan]{idx}[/bold cyan] -> {dev}")
                self.console.print("  [bold red]0[/bold red] -> Cancel")

                dev_choice = await loop.run_in_executor(None, input, "\nDevice # > ")
                dev_choice = dev_choice.strip()
                if dev_choice.isdigit() and int(dev_choice) > 0 and int(dev_choice) <= len(unique_devices):
                    target_dev = unique_devices[int(dev_choice) - 1]
                    deleted_cnt = self.db.delete_by_device_name(target_dev)
                    self.console.print(f"[bold green]{self.tr('clearhist_deleted_count', deleted_cnt, target_dev)}[/bold green]")
                    self.add_log(f"Cleared {deleted_cnt} records of '{target_dev}'.", "info")
                    time.sleep(1.5)

        self._is_interacting = False

    async def interactive_language_switch(self, chosen_lang: Optional[str] = None):
        self._is_interacting = True
        loop = asyncio.get_running_loop()

        if not chosen_lang:
            self.console.clear()
            self.console.print(Panel(Align.center("[bold cyan]SELECT LANGUAGE / ОБЕРІТЬ МОВУ / ВЫБЕРИТЕ ЯЗЫК[/bold cyan]"), border_style="cyan"))
            self.console.print("\n  [bold green]1[/bold green] -> [bold white]English[/bold white]")
            self.console.print("  [bold green]2[/bold green] -> [bold white]Русский[/bold white]")
            self.console.print("  [bold green]3[/bold green] -> [bold white]Українська[/bold white]")
            self.console.print("  [bold red]0[/bold red] -> Cancel")

            c = await loop.run_in_executor(None, input, "\nChoice / Вибір > ")
            c = c.strip().lower()
            lang_map = {
                "1": "en", "en": "en", "english": "en",
                "2": "ru", "ru": "ru", "русский": "ru",
                "3": "ua", "ua": "ua", "uk": "ua", "українська": "ua", "украинский": "ua"
            }
            chosen_lang = lang_map.get(c)

        if chosen_lang in ("en", "ua", "ru"):
            self.config.language = chosen_lang
            self.config.save()
            self.console.print(f"[bold green]{self.tr('lang_switched')}[/bold green]")
            self.add_log(self.tr("lang_switched"), "info")
            time.sleep(1.0)

        self._is_interacting = False

    async def show_chat_history(self, limit: int = 10):
        if not self.target_entity or not self.client:
            self.console.print("[bold red]No active connection to target bot![/bold red]")
            time.sleep(2)
            return

        self._is_interacting = True
        loop = asyncio.get_running_loop()
        self.console.clear()
        self.console.print(Panel(Align.center(f"[bold cyan]{self.tr('chat_title', limit, self.config.target_bot)}[/bold cyan]"), border_style="cyan"))

        messages = []
        async for msg in self.client.iter_messages(self.target_entity, limit=limit):
            messages.append(msg)
        messages.reverse()

        for m in messages:
            sender = self.tr("user") if m.out else self.config.target_bot
            color = "bright_blue" if m.out else "bright_green"
            time_str = m.date.strftime("%H:%M:%S") if m.date else ""
            txt = m.raw_text or m.message or "[Media / Photo]"
            self.console.print(f"[[dim]{time_str}[/dim]] [bold {color}]{sender}:[/bold {color}] {escape(txt)}")

        await loop.run_in_executor(None, input, self.tr("press_enter"))
        self._is_interacting = False

    async def _async_input(self, prompt_text: str) -> str:
        loop = asyncio.get_running_loop()
        self._current_input_buffer = ""
        user_input = await loop.run_in_executor(None, input, prompt_text)
        self._current_input_buffer = ""
        return user_input

    async def show_startup_splash(self):
        self.console.clear()
        self.console.print(Text(SPLASH_ASCII_LOGO, style="bold bright_cyan"))
        self.console.print(
            "       [bold bright_white on blue] ⚡ PHONEX SOFT [/bold bright_white on blue]  "
            "[bold black on bright_cyan] v1.0 [/bold black on bright_cyan]\n"
            "       [dim cyan]Next-Gen Autonomous Telegram Card Bot Engine[/dim cyan]\n"
        )
        await asyncio.sleep(3.0)
        self.console.clear()


    async def run(self):
        await self.show_startup_splash()
        self._stop_event.clear()
        self._runner_task = asyncio.create_task(self._background_loop())
        
        logged_in = await self.connect_and_login_silent()
        if not logged_in:
            self.add_log(self.tr("hint_login"), "warning")

        show_help = True
        self.draw_screen(show_help=show_help)

        while True:
            try:
                cmd_raw = await self._async_input(self.tr("input_prompt"))
                cmd_raw = cmd_raw.strip()
                if not cmd_raw:
                    self.draw_screen(show_help=show_help)
                    continue

                parts = cmd_raw.split()
                cmd = parts[0].lower()
                args = parts[1:]

                if cmd in ("refresh", "r", "ref", "update"):
                    self.draw_screen(show_help=False)
                    continue
                elif cmd == "on":
                    self.turn_on()
                    show_help = False
                elif cmd in ("off", "stop", "pause"):
                    self.turn_off()
                elif cmd in ("send", "now", "roll"):
                    self.force_send()
                    show_help = False
                elif cmd in ("flash", "flashing", "прошивка", "прошивки"):
                    if args and args[0] in ("on", "start", "enable"):
                        self.flasher.enabled = True
                        self.add_log("Auto-flashing module ENABLED.", "success")
                    elif args and args[0] in ("off", "stop", "disable"):
                        self.flasher.enabled = False
                        self.add_log("Auto-flashing module DISABLED.", "warning")
                    else:
                        await self.show_flashing_screen()
                elif cmd in ("inv", "myphones", "phones"):
                    await self.interactive_myphones_explorer()
                elif cmd in ("invlast", "last", "history_drops", "drops"):
                    await self.show_invlast_screen()
                elif cmd in ("clearhistory", "clearhist", "delhistory", "delhist"):
                    await self.interactive_clear_history()
                elif cmd in ("lang", "language", "мова", "язык", "english", "русский", "українська"):
                    chosen = None
                    if cmd in ("english", "en"): chosen = "en"
                    elif cmd in ("русский", "ru"): chosen = "ru"
                    elif cmd in ("українська", "ua"): chosen = "ua"
                    elif args:
                        arg_low = args[0].lower()
                        if arg_low in ("en", "english"): chosen = "en"
                        elif arg_low in ("ru", "русский", "russian"): chosen = "ru"
                        elif arg_low in ("ua", "uk", "українська", "ukrainian"): chosen = "ua"
                    await self.interactive_language_switch(chosen)
                elif cmd in ("chat", "history"):
                    lim = int(args[0]) if args and args[0].isdigit() else 10
                    await self.show_chat_history(limit=lim)
                elif cmd == "login":
                    await self.interactive_login()
                elif cmd == "logout":
                    if self.client and self.client.is_connected():
                        await self.client.disconnect()
                    self.clear_session()
                    self.state = STATE_DISCONNECTED
                    self.current_user = None
                    self.add_log(self.tr("log_logged_out"), "info")
                elif cmd == "bot":
                    if args:
                        new_bot = args[0]
                        self.add_log(f"Verifying bot {new_bot}...", "info")
                        await self.resolve_target_bot(new_bot)
                        self.config.save()
                    else:
                        self.add_log("Usage: bot @username", "warning")
                elif cmd in ("cmd", "command"):
                    if args:
                        new_cmd = args[0]
                        self.config.command = new_cmd
                        self.config.save()
                        self.add_log(f"Command set to: {new_cmd}", "success")
                    else:
                        self.add_log("Usage: cmd /command", "warning")
                elif cmd in ("jitter", "delay"):
                    if args and args[0].isdigit():
                        val = int(args[0])
                        self.config.safety_jitter_seconds = val
                        self.config.save()
                        self.add_log(f"Jitter set to: +{val}s", "success")
                    else:
                        self.add_log("Usage: jitter <seconds>", "warning")
                elif cmd == "clear":
                    self.logs.clear()
                elif cmd in ("help", "?", "h"):
                    show_help = not show_help
                elif cmd in ("exit", "quit", "q"):
                    break
                else:
                    self.add_log(self.tr("unknown_cmd", cmd), "warning")

                self.draw_screen(show_help=show_help)

            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                self.add_log(f"Runtime error: {e}", "error")
                self.draw_screen(show_help=show_help)

        self.console.print(self.tr("shutdown_msg"))
        self._stop_event.set()
        if self._runner_task:
            self._runner_task.cancel()
        if self.client and self.client.is_connected():
            await self.client.disconnect()
        self.console.print(self.tr("shutdown_done"))


def main():
    automator = TerminalAutomator()
    try:
        asyncio.run(automator.run())
    except KeyboardInterrupt:
        print("\nProcess terminated.")


if __name__ == "__main__":
    main()


