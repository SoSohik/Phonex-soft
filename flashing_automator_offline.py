"""
PHONEX SOFT - Fully Autonomous Offline Firmware Flashing Bot (PhoneGet)
========================================================================
100% Offline & Local - ZERO AI, ZERO Vision API, ZERO Cloud Subscriptions!
Engineered specifically for Termux (Android) and PC using Pillow + Tesseract OCR.

Key Highlights:
1. solve_crypto_task_offline:
   - Green color-isolation filter: strips all gray/white strike-through lines & dark background.
   - Header OCR: extracts target 2-character token from "[ЗАДАЧА] Найдите блок XX".
   - 7-Column vertical strip OCR: reads each matrix column individually to locate the matching block.
2. Isolated Device Sessions (DeviceFlashingSession):
   - Multi-device concurrent tracking (Google Nexus One, Samsung Galaxy S6 Edge, etc.).
   - Concurrency lock per phone; state changes never cross-contaminate.
3. Accurate Error Event Handling:
   - Driver error: clicks "Переподключить шнур" (ONLY when an actual error is present).
   - Checksum error: clicks "Перейти в режим отладки".
   - Crypto puzzle: downloads image in-memory, solves offline via Tesseract, clicks column button (1-7).
   - Brick / failure: closes session, clicks "К прошитым телефонам".
"""

import asyncio
import io
import os
import re
import sys
from datetime import datetime
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from PIL import Image

try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

from telethon import TelegramClient, events
from telethon.tl.custom.message import Message
from telethon.errors import MessageNotModifiedError, FloodWaitError
from telethon.sessions import StringSession

from config import AppConfig

console = Console()

# Configure Windows Tesseract path if present
if sys.platform == "win32" and HAS_PYTESSERACT:
    default_win_tess = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_win_tess):
        pytesseract.pytesseract.tesseract_cmd = default_win_tess


# -------------------------------------------------------------------------
# 1. High-Performance Local Image Processing & Offline Matrix Solver
# -------------------------------------------------------------------------

def preprocess_terminal_image(img: Image.Image) -> Image.Image:
    """
    Cleans terminal screenshots from interference noise:
    - Retains bright-green terminal text (#00FF00).
    - Removes dark background and white/gray strike-through lines.
    - Yields a crisp binary image: black text on pure white background.

    Filter Condition:
      G > 110 and G > R * 1.3 and G > B * 1.3 -> Text (0)
      Else -> Background (255)
    """
    img_rgb = img.convert("RGB")
    width, height = img_rgb.size
    raw_bytes = img_rgb.tobytes()

    # Pre-allocate binary pixel buffer
    pixels = bytearray(width * height)

    for i in range(0, len(raw_bytes), 3):
        r = raw_bytes[i]
        g = raw_bytes[i + 1]
        b = raw_bytes[i + 2]

        # Isolate bright green terminal phosphor characters
        if g > 110 and g > (r * 1.3) and g > (b * 1.3):
            pixels[i // 3] = 0   # Black text for OCR
        else:
            pixels[i // 3] = 255 # White background (eliminates lines & black background)

    return Image.frombytes("L", (width, height), bytes(pixels))


def solve_crypto_task_offline_sync(image_bytes: bytes) -> Optional[int]:
    """
    Synchronous image processing & OCR pipeline:
    1. Preprocesses image by filtering out interference lines.
    2. Crops upper terminal area and extracts target token XX.
    3. Crops lower matrix area into 7 vertical column strips.
    4. Searches columns 1-7 for the target token.
    """
    if not HAS_PYTESSERACT:
        console.print("[bold red]❌ pytesseract is not installed! Run: pip install pytesseract[/bold red]")
        return None

    try:
        raw_image = Image.open(io.BytesIO(image_bytes))
        clean_img = preprocess_terminal_image(raw_image)
        width, height = clean_img.size

        # --- STEP 1: OCR the Header Task Section ---
        # The line "[ЗАДАЧА] Найдите блок XX" is typically in the top 30%
        top_h = int(height * 0.32)
        top_crop = clean_img.crop((0, 0, width, top_h))
        
        # PSM 6 = Assume a single uniform block of text
        header_text = pytesseract.image_to_string(
            top_crop, 
            config="--psm 6"
        )
        console.print(f"[dim]OCR Header scan: {header_text.strip().replace(chr(10), ' | ')}[/dim]")

        # Extract target 2-character hex/token code
        token_match = re.search(r"блок[^\w]*([A-Za-z0-9]{2})\b", header_text, re.IGNORECASE)
        if not token_match:
            # Fallback search for token after [ЗАДАЧА]
            token_match = re.search(r"ЗАДАЧА[^\n\r]*?([A-Za-z0-9]{2})\b", header_text, re.IGNORECASE)

        if not token_match:
            console.print("[bold yellow]⚠️ Could not parse target token XX from header![/bold yellow]")
            return None

        target_token = token_match.group(1).upper()
        console.print(f"[bold bright_green]🎯 Target token identified:[/bold bright_green] [bold yellow]'{target_token}'[/bold yellow]")

        # --- STEP 2: Divide Matrix into 7 Vertical Columns ---
        # Matrix starts below header (around 28% height down to bottom)
        matrix_top = int(height * 0.28)
        matrix_crop = clean_img.crop((0, matrix_top, width, height))
        m_width, m_height = matrix_crop.size

        col_width = m_width / 7.0
        ocr_config = "--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

        column_results = {}
        for col_idx in range(7):
            col_num = col_idx + 1
            x1 = int(col_idx * col_width)
            x2 = int((col_idx + 1) * col_width)

            col_strip = matrix_crop.crop((x1, 0, x2, m_height))
            col_text = pytesseract.image_to_string(col_strip, config=ocr_config).upper()
            column_results[col_num] = col_text

            # Check direct match
            if target_token in col_text:
                console.print(f"[bold green]✅ Token '{target_token}' found in Column {col_num}![/bold green]")
                return col_num

        # Secondary search with loose boundary if exact substring was slightly broken by OCR
        for col_num, col_text in column_results.items():
            # Check characters without spaces
            cleaned_text = re.sub(r"\s+", "", col_text)
            if target_token in cleaned_text:
                console.print(f"[bold green]✅ Token '{target_token}' matched in Column {col_num} (clean match)![/bold green]")
                return col_num

        console.print(f"[bold yellow]⚠️ Token '{target_token}' was not detected in any of the 7 columns.[/bold yellow]")
        return None

    except Exception as e:
        console.print(f"[bold red]❌ OCR processing error: {e}[/bold red]")
        return None


async def solve_crypto_task_offline(image_bytes: bytes) -> Optional[int]:
    """Non-blocking asynchronous wrapper running OCR in a worker thread."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, solve_crypto_task_offline_sync, image_bytes)


# -------------------------------------------------------------------------
# 2. Isolated Device Flashing Session
# -------------------------------------------------------------------------

class DeviceFlashingSession:
    """
    Manages isolated flashing state for an individual phone.
    """
    def __init__(self, device_name: str, message_id: int, manager: "DeviceFlashingManager"):
        self.device_name: str = device_name
        self.message_id: int = message_id
        self.manager: "DeviceFlashingManager" = manager

        self.progress_percent: int = 0
        self.remaining_time: str = "--:--"
        self.status: str = "INITIALIZING"
        self.is_active: bool = True
        self.errors_count: int = 0
        self.last_action: str = "Worker started"
        
        # Concurrency lock to prevent overlapping button clicks on the same message
        self._lock = asyncio.Lock()

    def log(self, text: str, style: str = "white"):
        ts = datetime.now().strftime("%H:%M:%S")
        console.print(f"[{ts}] [[bold cyan]{self.device_name}[/bold cyan]] [{style}]{text}[/{style}]")

    def parse_message_state(self, text: str):
        pct_match = re.search(r"(?:Процент установки|Прогресс|Установка)[:\s]+(\d{1,3})%", text, re.IGNORECASE)
        if pct_match:
            self.progress_percent = int(pct_match.group(1))

        time_match = re.search(r"(?:Оставшееся время|Осталось|Время)[:\s]+(\d{1,2}:\d{2})", text, re.IGNORECASE)
        if time_match:
            self.remaining_time = time_match.group(1)

    async def handle_update(self, message: Message):
        async with self._lock:
            if not self.is_active:
                return

            text = message.raw_text or message.message or ""
            self.parse_message_state(text)

            # -------------------------------------------------------------
            # Case 1: Driver Timeout / Cable Error
            # -------------------------------------------------------------
            cable_error_detected = any(k in text.lower() for k in [
                "ошибка драйвера", "driver_timeout", "устройство потеряно", 
                "отключился кабель", "сбой подключения", "кабель отключен"
            ])
            if cable_error_detected:
                self.status = "DRIVER_ERROR"
                self.errors_count += 1
                self.log(f"⚠️ Driver/Cable error detected at {self.progress_percent}%! Reconnecting...", "bold yellow")
                
                clicked = await self._click_button_by_patterns(
                    message, 
                    [r"переподключить(?:\s+шнур)?", r"подключить", r"повторить"]
                )
                if clicked:
                    self.last_action = "Reconnected cable"
                    self.status = "FLASHING"
                return

            # -------------------------------------------------------------
            # Case 2: Cryptographic Checksum Error -> Offline Tesseract OCR
            # -------------------------------------------------------------
            crypto_error_detected = any(k in text.lower() for k in [
                "криптографическая ошибка", "crypto_checksum", 
                "найдите блок", "сбой контрольной суммы"
            ])
            if crypto_error_detected:
                self.status = "CRYPTO_PUZZLE"
                self.errors_count += 1
                self.log("🧩 Cryptographic checksum fault! Downloading terminal image...", "bold magenta")

                if message.photo or message.media:
                    image_bytes = await message.download_media(file=bytes)
                    if image_bytes:
                        self.log("🔍 Executing offline Tesseract OCR with noise suppression...", "cyan")
                        col_digit = await solve_crypto_task_offline(image_bytes)
                        if col_digit:
                            self.log(f"🎯 Column {col_digit} verified! Clicking inline button...", "bold green")
                            clicked = await self._click_button_by_digit(message, col_digit)
                            if clicked:
                                self.last_action = f"Selected Column {col_digit}"
                                self.status = "FLASHING"
                                return
                        else:
                            self.log("⚠️ Offline OCR could not determine column.", "yellow")
                    else:
                        self.log("⚠️ Failed to load puzzle image bytes.", "yellow")
                else:
                    self.log("⚠️ Crypto error present but no image attached to message.", "yellow")
                return

            # -------------------------------------------------------------
            # Case 3: Unknown System Error -> Debug Mode Required
            # -------------------------------------------------------------
            unknown_error_detected = any(k in text.lower() for k in [
                "неизвестная ошибка", "режим отладки", "debug_mode", "system_halt"
            ])
            if unknown_error_detected:
                self.status = "UNKNOWN_ERROR"
                self.errors_count += 1
                self.log(f"🛠 Unknown system fault at {self.progress_percent}%. Activating Debug Mode...", "bold yellow")
                
                clicked = await self._click_button_by_patterns(
                    message,
                    [r"перейти в режим отладки", r"режим отладки", r"отладка"]
                )
                if clicked:
                    self.last_action = "Switched to debug mode"
                    self.status = "DEBUGGING"
                return

            # -------------------------------------------------------------
            # Case 4: Fatal Brick Failure ("кирпич" or "[СБОЙ]")
            # -------------------------------------------------------------
            brick_detected = any(k in text.lower() for k in [
                "кирпич", "[сбой]", "устройство повреждено", "прошивка не удалась"
            ])
            if brick_detected:
                self.status = "BRICKED"
                self.is_active = False
                self.log("💀 Device flashing failed critically (BRICKED)! Terminating worker...", "bold red")
                
                await self._click_button_by_patterns(
                    message,
                    [r"к прошитым телефонам", r"в меню", r"назад", r"закрыть"]
                )
                self.manager.close_session(self.device_name)
                return

            # -------------------------------------------------------------
            # Case 5: Successful Completion
            # -------------------------------------------------------------
            success_detected = any(k in text.lower() for k in [
                "успешно прошит", "прошивка завершена", "устройство готово", 
                "100%", "успех", "готово!"
            ]) and (self.progress_percent >= 100 or "успешно" in text.lower())
            
            if success_detected:
                self.status = "COMPLETED"
                self.progress_percent = 100
                self.is_active = False
                self.log("🎉 Flashing COMPLETED successfully! Firmware verified.", "bold green")
                
                await self._click_button_by_patterns(
                    message,
                    [r"к прошитым телефонам", r"забрать", r"в инвентарь", r"назад"]
                )
                self.manager.close_session(self.device_name)
                return

            # -------------------------------------------------------------
            # Case 6: Standard Active Progress (DO NOT TOUCH BUTTONS)
            # -------------------------------------------------------------
            self.status = "FLASHING"
            self.log(f"⚡ Flashing progress: {self.progress_percent}% | Remaining: {self.remaining_time}", "green")

    async def _click_button_by_patterns(self, message: Message, patterns: list) -> bool:
        if not message.buttons:
            return False

        for row in message.buttons:
            for btn in row:
                btn_text = btn.text.strip()
                for pat in patterns:
                    if re.search(pat, btn_text, re.IGNORECASE):
                        try:
                            self.log(f"👉 Clicking inline button: '{btn_text}'", "cyan")
                            await btn.click()
                            await asyncio.sleep(1.0)
                            return True
                        except (MessageNotModifiedError, FloodWaitError) as e:
                            self.log(f"Button notice: {e}", "dim yellow")
                            return True
                        except Exception as e:
                            self.log(f"Button click error: {e}", "bold red")
                            return False
        return False

    async def _click_button_by_digit(self, message: Message, digit: int) -> bool:
        if not message.buttons:
            return False

        target_str = str(digit)
        for row in message.buttons:
            for btn in row:
                btn_text = btn.text.strip()
                if btn_text == target_str or re.search(rf"\b{target_str}\b", btn_text):
                    try:
                        self.log(f"👉 Selected column inline button: '{btn_text}'", "bold green")
                        await btn.click()
                        await asyncio.sleep(1.0)
                        return True
                    except Exception as e:
                        self.log(f"Failed to click column button {digit}: {e}", "bold red")
                        return False
        return False


# -------------------------------------------------------------------------
# 3. Central Multi-Device Flashing Manager
# -------------------------------------------------------------------------

class DeviceFlashingManager:
    """
    Coordinates client connection, event subscriptions, and isolated device workers.
    """
    def __init__(self, target_bot: str = "@phonegetcardsbot"):
        self.config: AppConfig = AppConfig.load()
        self.target_bot: str = target_bot
        self.client: Optional[TelegramClient] = None
        self.target_entity = None
        
        self.sessions: Dict[str, DeviceFlashingSession] = {}
        self.msg_to_device: Dict[int, str] = {}

    def get_or_create_session(self, device_name: str, message_id: int) -> DeviceFlashingSession:
        if device_name not in self.sessions:
            session = DeviceFlashingSession(device_name, message_id, self)
            self.sessions[device_name] = session
            self.msg_to_device[message_id] = device_name
            session.log("🚀 Initialized new isolated flashing worker.", "bold bright_green")
            return session
        
        session = self.sessions[device_name]
        session.message_id = message_id
        self.msg_to_device[message_id] = device_name
        return session

    def close_session(self, device_name: str):
        if device_name in self.sessions:
            self.sessions[device_name].is_active = False
            del self.sessions[device_name]
            console.print(f"[[bold cyan]{device_name}[/bold cyan]] [dim]Worker session terminated and freed.[/dim]")

    @staticmethod
    def extract_device_name(text: str) -> Optional[str]:
        if not text:
            return None

        # Pattern 1: "Прошивка <Device Name> ->" or "Прошивка <Device Name>\n"
        m1 = re.search(r"Прошивка\s+([^\n\r->]+?)(?:\s*->|\s*\n|$)", text, re.IGNORECASE)
        if m1:
            name = m1.group(1).strip(" :[]()-")
            if len(name) > 2:
                return name

        # Pattern 2: "📱 <Device Name>"
        m2 = re.search(r"📱\s*([^\n\r]+?)(?:\s*\(|\s*\n|$)", text)
        if m2:
            name = m2.group(1).strip(" :[]()-")
            if len(name) > 2:
                return name

        # Pattern 3: Fallback generic header
        m3 = re.search(r"Устройство:\s*([^\n\r]+)", text, re.IGNORECASE)
        if m3:
            return m3.group(1).strip()

        return None

    def render_overview_table(self) -> Table:
        table = Table(title="⚡ PHONEX OFFLINE FLASHING SESSIONS", expand=True, border_style="cyan")
        table.add_column("Device Name", style="bold bright_white")
        table.add_column("Progress", style="bold green", justify="center")
        table.add_column("Remaining", style="magenta", justify="center")
        table.add_column("Status", style="yellow")
        table.add_column("Errors", style="red", justify="center")
        table.add_column("Last Action", style="dim")

        if not self.sessions:
            table.add_row("[dim]No active flashing sessions[/dim]", "--", "--", "IDLE", "0", "Waiting for bot...")
        else:
            for s in self.sessions.values():
                table.add_row(
                    s.device_name,
                    f"{s.progress_percent}%",
                    s.remaining_time,
                    s.status,
                    str(s.errors_count),
                    s.last_action
                )
        return table

    async def _on_bot_message_event(self, event):
        msg: Message = event.message
        if not msg:
            return

        text = msg.raw_text or msg.message or ""
        
        is_flashing_msg = any(k in text.lower() for k in [
            "прошивка", "процент установки", "оставшееся время", 
            "режим отладки", "криптографическая ошибка", "драйвер"
        ])
        if not is_flashing_msg:
            return

        device_name = self.extract_device_name(text)
        if not device_name:
            if msg.id in self.msg_to_device:
                device_name = self.msg_to_device[msg.id]

        if not device_name:
            device_name = f"Device_Msg_{msg.id}"

        session = self.get_or_create_session(device_name, msg.id)
        await session.handle_update(msg)

    async def start(self):
        console.clear()
        console.print(Panel(
            "[bold bright_cyan]⚡ PHONEX SOFT - AUTONOMOUS OFFLINE FIRMWARE FLASHING ENGINE[/bold bright_cyan]\n"
            "[bold white]100% Local: Telethon MTProto + Pillow + Tesseract OCR[/bold white]\n"
            "[dim]No AI, No API keys, No cloud subscriptions required[/dim]",
            border_style="cyan"
        ))

        # Check local OCR availability
        if not HAS_PYTESSERACT:
            console.print("[bold red]❌ Warning: pytesseract is not installed! Run: pip install pytesseract[/bold red]")
            console.print("[dim]In Termux: pkg install tesseract && pip install pytesseract[/dim]\n")

        session_path = "data/session.dat"
        session_str = ""
        if os.path.exists(session_path):
            with open(session_path, "r", encoding="utf-8") as f:
                session_str = f.read().strip()

        self.client = TelegramClient(StringSession(session_str), self.config.api_id, self.config.api_hash)
        await self.client.connect()

        if not await self.client.is_user_authorized():
            console.print("[bold red]❌ Telegram client is not authorized! Run 'main.py' first and log in with QR or Phone.[/bold red]")
            return

        me = await self.client.get_me()
        self.target_entity = await self.client.get_entity(self.target_bot)
        
        console.print(f"[bold green]✅ Connected as @{me.username or me.first_name}![/bold green]")
        console.print(f"[bold cyan]🎯 Monitoring bot: {self.target_bot}[/bold cyan]\n")

        # Register listeners for bot updates
        self.client.add_event_handler(
            self._on_bot_message_event,
            events.NewMessage(chats=self.target_entity)
        )
        self.client.add_event_handler(
            self._on_bot_message_event,
            events.MessageEdited(chats=self.target_entity)
        )

        console.print("[bold bright_green]🎧 Event listeners active. Waiting for device flashing updates...[/bold bright_green]")
        console.print("[dim]Press Ctrl+C to terminate.[/dim]\n")

        try:
            while True:
                await asyncio.sleep(5.0)
                if self.sessions:
                    console.print(self.render_overview_table())
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[bold yellow]Stopping offline flashing manager...[/bold yellow]")
        finally:
            if self.client and self.client.is_connected():
                await self.client.disconnect()
            console.print("[bold green]Manager stopped cleanly.[/bold green]")


# -------------------------------------------------------------------------
# Entrypoint
# -------------------------------------------------------------------------

if __name__ == "__main__":
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass

    manager = DeviceFlashingManager(target_bot="@phonegetcardsbot")
    try:
        asyncio.run(manager.start())
    except KeyboardInterrupt:
        pass
