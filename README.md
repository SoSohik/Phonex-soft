# PHONEX SOFT SOFT v1.0 - Cyberpunk Telegram Bot Automator

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Fast, lightweight, terminal-based automation client for Telegram card & drop bots (such as `@phonegetcardsbot`). Features an OLED terminal UI, interactive Telegram inline menus navigation, SQLite drop history tracking, and multi-language support.

---

## 🌐 Quick Language Navigation / Навігація мовами / Навигация по языкам

- [🇺🇦 Інструкція українською (Повне покрокове керівництво)](#-інструкція-українською)
- [🇬🇧 English Guide (Comprehensive Step-by-Step)](#-english-guide)
- [🇷🇺 Инструкция на русском (Полное пошаговое руководство)](#-инструкция-на-русском)

---

## 🇺🇦 Інструкція українською

### 📌 Що це за програма?
PHONEX SOFT — це автономний консольний помічник, який у фоновому режимі надсилає команди боту (за замовчуванням `/tcard`), автоматично зчитує час до наступного ролу (кулдаун), вираховує безпечний джитер (антифлуд захист) та зберігає вибиті телефони в локальну базу даних SQLite. Також програма дозволяє переглядати інвентар бота (`/myphones`) через зручне цифрове меню.

> **Усі необхідні ключі Telegram API вже вшиті в програму!** Вам і вашим користувачам не потрібно ніде реєструватися чи шукати API ID та HASH — достатньо лише увійти у свій Telegram-акаунт за 1 клік через QR-код або номер телефону.

---

### 📂 Крок 1. Підготовка папки та розміщення файлів

Для зручності створіть окрему папку в корені вашого диску або домашньої директорії.

#### На Windows:
1. Відкрийте диск `C:\` (або `D:\`).
2. Створіть нову папку з назвою **`tgbot`** (шлях буде `C:\tgbot`).
3. Скопіюйте у цю папку всі файли проекту:
   - `main.py`
   - `config.py`
   - `database.py`
   - `drop_parser.py`
   - `time_parser.py`
   - `requirements.txt`
   - `start.bat`
   - `start.sh`
   - `.env`

#### На Linux / macOS:
1. Створіть папку `tgbot` у вашому домашньому каталозі:
   ```bash
   mkdir -p ~/tgbot
   cd ~/tgbot
   ```
2. Перемістіть туди всі файли програми.

#### На Android у додатку Termux:
1. Відкрийте Termux та створіть папку:
   ```bash
   mkdir -p ~/tgbot
   cd ~/tgbot
   ```
2. Скопіюйте файли проекту в цю папку.

---

### ⚙️ Крок 2. Встановлення та запуск програми

#### Варіант А: Windows PC
1. Переконайтеся, що на комп'ютері встановлено **Python 3.10 або новіший** (при встановленні Python обов'язково поставте галочку *"Add Python to PATH"*).
2. Відкрийте командний рядок (`cmd`) або PowerShell і перейдіть до папки:
   ```powershell
   cd C:\tgbot
   ```
3. Встановіть необхідні бібліотеки:
   ```powershell
   pip install -r requirements.txt
   ```
4. Запустіть програму:
   ```powershell
   python main.py
   ```
   *(Або просто двічі клікніть файл `start.bat` у папці `C:\tgbot`)*.

---

#### Варіант Б: Linux (Ubuntu / Debian / Arch / Fedora)
1. Встановіть Python та системні залежності:
   ```bash
   sudo apt update
   sudo apt install -y python3 python3-pip python3-venv git
   ```
2. Перейдіть у створену папку `~/tgbot`:
   ```bash
   cd ~/tgbot
   ```
3. Створіть віртуальне середовище (рекомендовано):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
4. Встановіть залежності проекту:
   ```bash
   pip install -r requirements.txt
   ```
5. Запустіть скрипт:
   ```bash
   chmod +x start.sh
   ./start.sh
   # Або напряму: python3 main.py
   ```

---

#### Варіант В: macOS
1. Відкрийте програму **Термінал** (Terminal).
2. Встановіть Python (якщо ще не встановлено, наприклад через `brew install python`).
3. Перейдіть до папки з ботом:
   ```bash
   cd ~/tgbot
   ```
4. Встановіть бібліотеки та запустіть:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python3 main.py
   ```

---

#### Варіант Г: Android через Termux
1. Відкрийте Termux і виконайте оновлення:
   ```bash
   pkg update -y && pkg upgrade -y
   pkg install python git clang libjpeg-turbo -y
   ```
2. Перейдіть у робочу папку:
   ```bash
   cd ~/tgbot
   ```
3. Встановіть бібліотеки:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Запустіть:
   ```bash
   python main.py
   ```

---

### 🔑 Крок 3. Вхід та авторизація (Login)

1. Після запуску програми введіть команду:
   ```text
   login
   ```
2. Оберіть спосіб входу:
   - **1 — Швидкий вхід через QR-код (Найзручніше):** програма відобразить QR-код прямо в терміналі. Візьміть телефон із Telegram, відкрийте *Налаштування -> Пристрої -> Підключити пристрій* та наведіть камеру на екран.
   - **2 — Вхід за номером телефону:** введіть свій номер (`+380...`), отримайте 5-значний офіційний код у додатку Telegram та введіть його. Якщо увімкнено хмарний пароль 2FA — введіть його.
   - **3 — Вхід через StringSession:** якщо є готовий рядок сесії Telethon — вставте його.
3. **Готово!** Сесія надійно збережеться у файл `data/session.dat`. При наступних запусках вхід відбуватиметься **миттєво та автоматично**.

---

### 🎮 Крок 4. Список усіх команд

У нижній частині екрана завжди активний рядок введення: `Command > `.

| Команда | Опис дії |
| :--- | :--- |
| **`on`** | Запускає автоматичний режим. Бот одразу робить перевірочний запит, визначає кулдаун і починає самостійно крутити роли по таймеру. |
| **`off`** (або `stop`) | Ставить авто-рол на паузу. |
| **`send`** (або `now`) | Зробити примусовий рол прямо зараз, не чекаючи завершення таймера. |
| **`inv`** (або `myphones`) | Відкриває інтерактивне меню інвентарю бота з цифровими кнопками (1, 2, 3...). Дозволяє переглядати робочі/неробочі телефони, рідкості та списки вибитих апаратів. *(Пункт "Прошитые телефоны" вимкнено для безпеки)*. |
| **`invlast`** | Відкриває таблицю всіх вибитих телефонів, які бот зберіг у локальну базу даних SQLite під час авто-ролів (показує ID, назву, рідкість кольором, ціну в pts та дату). |
| **`clearhistory`** | Очищення історії вибиття. Меню запропонує: `1` — очистити всю базу повністю, або `2` — видалити записи про конкретну модель телефону. |
| **`lang`** | Зміна мови інтерфейсу. Можна також написати прямо: `english`, `русский`, або `українська`. |
| **`bot @юзернейм`** | Змінити цільового бота (за замовчуванням стоїть `@phonegetcardsbot`). |
| **`cmd /команда`** | Змінити тригер-команду ролу (за замовчуванням `/tcard`). Наприклад: `cmd /bonus` або `cmd /daily`. |
| **`chat 15`** | Показати останні 15 повідомлень вашого листування з ботом. |
| **`jitter 5`** | Налаштувати затримку безпеки у секундах (захист від блокувань). |
| **`clear`** | Очистити журнал останніх подій на екрані. |
| **`help`** (або `?`) | Показати або приховати панель підказок. |
| **`logout`** | Вийти з облікового запису Telegram та видалити збережену сесію. |
| **`exit`** (або `q`) | Коректно зберегти всі дані та вийти з програми. |

---

## 🇬🇧 English Guide

### 📌 Overview
PHONEX SOFT is an autonomous CLI tool designed to automate roll and card drops in Telegram bots (default target: `@phonegetcardsbot`). It intelligently parses cooldown durations, adds anti-ban safety jitter, stores all acquired devices into a local SQLite database, and offers interactive terminal navigation for Telegram inline menus.

> **Pre-configured Telegram API Credentials!** The required API keys are already built into the application. Users do not need to register on any portal—simply run the app and log in seamlessly via QR code or phone number.

---

### 📂 Step 1. Create Folder & Place Files

#### On Windows:
1. Open drive `C:\` (or `D:\`).
2. Create a folder named **`tgbot`** (`C:\tgbot`).
3. Move all project files into `C:\tgbot`:
   - `main.py`, `config.py`, `database.py`, `drop_parser.py`, `time_parser.py`, `requirements.txt`, `start.bat`, `start.sh`, `.env`

#### On Linux / macOS:
```bash
mkdir -p ~/tgbot
cd ~/tgbot
# Move all project files here
```

#### On Android (Termux):
```bash
mkdir -p ~/tgbot
cd ~/tgbot
```

---

### ⚙️ Step 2. Installation & Run

#### Option A: Windows PC
1. Ensure **Python 3.10+** is installed with the *"Add Python to PATH"* checkbox checked.
2. Open PowerShell or Command Prompt:
   ```powershell
   cd C:\tgbot
   pip install -r requirements.txt
   python main.py
   ```
   *(Or simply double-click `start.bat`)*.

#### Option B: Linux
```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv
cd ~/tgbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

#### Option C: macOS
```bash
brew install python
cd ~/tgbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

#### Option D: Android (Termux)
```bash
pkg update -y && pkg install python git -y
cd ~/tgbot
pip install -r requirements.txt
python main.py
```

---

### 🔑 Step 3. Telegram Authentication

1. Once the application starts, enter:
   ```text
   login
   ```
2. Select your preferred login method:
   - **1 — QR Code (Fastest):** Scan the ASCII QR code displayed in your terminal using your phone (*Telegram -> Settings -> Devices -> Link Desktop Device*).
   - **2 — Phone Number:** Receive an official 5-digit verification code in Telegram. Enter your 2FA password if enabled.
   - **3 — StringSession:** Paste an existing Telethon session string.
3. The session is saved permanently in `data/session.dat` for instant auto-login on future launches.

---

### 🎮 Step 4. Commands Reference

| Command | Action |
| :--- | :--- |
| **`on`** | Starts automated loop. Immediately sends check, detects cooldown, and loops. |
| **`off`** / `stop` | Pauses automation loop. |
| **`send`** / `now` | Forces roll command execution immediately. |
| **`inv`** / `myphones` | Opens interactive `/myphones` Telegram inline buttons explorer via simple numeric choices (1..N). Flashed phones option is disabled for safety. |
| **`invlast`** | Displays local SQLite database table of all dropped phones (Device, Price in pts, Rarity, Date). |
| **`clearhistory`** | Deletes either all local drop history or instances of a specific phone model. |
| **`lang`** | Switches UI language. Direct commands: `english`, `українська`, `русский`. |
| **`bot <@username>`** | Sets target bot username (e.g. `bot @phonegetcardsbot`). |
| **`cmd </command>`** | Sets roll trigger command (e.g. `cmd /bonus`). |
| **`chat [limit]`** | Displays the latest messages from the bot chat. |
| **`jitter <seconds>`**| Sets safety jitter delay in seconds. |
| **`clear`** | Clears on-screen event log. |
| **`help`** | Toggles commands guide panel. |
| **`logout`** | Logs out and removes local session. |
| **`exit`** / `q` | Saves state and safely exits. |

---

## 🇷🇺 Инструкция на русском

### 📌 Описание
PHONEX SOFT — это автономный консольный ассистент для автоматизации карточных дроп-ботов в Telegram (по умолчанию `@phonegetcardsbot`). Клиент автоматически распознает кулдауны, предотвращает баны рандомным джиттером, ведет базу выпавших телефонов в SQLite и позволяет нажимать инлайн-кнопки бота через удобное цифровое меню в терминале.

> **Telegram API уже встроен в программу!** Вам и пользователям не требуется регистрироваться на портале разработчиков — достаточно просто войти через QR-код или номер телефона в 1 клик.

---

### 📂 Шаг 1. Создание папки и размещение файлов

#### На Windows:
1. Откройте диск `C:\` (или `D:\`).
2. Создайте папку **`tgbot`** (путь: `C:\tgbot`).
3. Скопируйте туда все файлы:
   - `main.py`, `config.py`, `database.py`, `drop_parser.py`, `time_parser.py`, `requirements.txt`, `start.bat`, `start.sh`, `.env`

#### На Linux / macOS:
```bash
mkdir -p ~/tgbot
cd ~/tgbot
# Скопируйте файлы программы сюда
```

#### На Android в Termux:
```bash
mkdir -p ~/tgbot
cd ~/tgbot
```

---

### ⚙️ Шаг 2. Установка и запуск

#### Вариант А: Windows PC
1. Убедитесь, что установлен **Python 3.10+** (с галочкой *"Add Python to PATH"*).
2. Запустите консоль (`cmd` или PowerShell):
   ```powershell
   cd C:\tgbot
   pip install -r requirements.txt
   python main.py
   ```
   *(Или дважды нажмите на `start.bat` в папке `C:\tgbot`)*.

#### Вариант Б: Linux
```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv
cd ~/tgbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

#### Вариант В: macOS
```bash
brew install python
cd ~/tgbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

#### Вариант Г: Android (Termux)
```bash
pkg update -y && pkg install python git -y
cd ~/tgbot
pip install -r requirements.txt
python main.py
```

---

### 🔑 Шаг 3. Вход в аккаунт Telegram

1. Запустите программу и введите:
   ```text
   login
   ```
2. Выберите способ входа:
   - **1 — QR-код:** Терминал выведет QR-код. Откройте Telegram на телефоне (*Настройки -> Устройства -> Подключить устройство*) и отсканируйте код.
   - **2 — По номеру телефона:** Получите 5-значный код в приложении Telegram. Если включен пароль 2FA — введите его.
   - **3 — По StringSession:** Вставьте готовую строку Telethon.
3. Сессия надежно сохранится в `data/session.dat`. В следующий раз вход произойдет автоматически без повторного ввода.

---

### 🎮 Шаг 4. Список команд

| Команда | Действие |
| :--- | :--- |
| **`on`** | Включает автоматический режим. Бот сразу отправит команду, определит таймер и начнет крутить по расписанию. |
| **`off`** / `stop` | Приостанавливает автоматический режим. |
| **`send`** / `now` | Принудительно отправляет команду ролла прямо сейчас. |
| **`inv`** / `myphones` | Интерактивный навигатор по кнопкам меню `/myphones` (цифры 1, 2, 3...). Пункт "Прошитые телефоны" отключен для безопасности. |
| **`invlast`** | Открывает таблицу всех выпавших телефонов из локальной базы данных SQLite. |
| **`clearhistory`** | Очистка истории: `1` — очистить всю базу, `2` — удалить записи определенной модели телефона. |
| **`lang`** | Смена языка интерфейса (`english`, `русский`, `українська`). |
| **`bot <@юзернейм>`** | Смена целевого бота (по умолчанию `@phonegetcardsbot`). |
| **`cmd </команда>`** | Смена команды ролла (по умолчанию `/tcard`). |
| **`chat [кол-во]`** | Показывает последние сообщения переписки с ботом. |
| **`jitter <сек>`** | Настройка антифлуд-задержки в секундах. |
| **`clear`** | Очищает журнал событий в консоли. |
| **`help`** | Показывает/скрывает справку команд. |
| **`logout`** | Выход из аккаунта и удаление локальной сессии. |
| **`exit`** / `q` | Сохранение сессии и выход из программы. |
