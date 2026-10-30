"""
PHONEX SOFT - Autonomous Offline Firmware Flashing Module (flasher.py)
======================================================================
100% Offline, Termux & PC compatible local firmware flashing automation.
Uses Pillow and Tesseract OCR with pixel-level interference noise filtration.
"""

import asyncio
import io
import os
import re
import sys
from datetime import datetime
from typing import Optional, Dict, Any, List

from PIL import Image

try:
    import pytesseract
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from telethon.tl.custom.message import Message
from telethon.errors import MessageNotModifiedError, FloodWaitError

# Auto-configure Tesseract path on Windows
if sys.platform == "win32" and HAS_PYTESSERACT:
    default_win_tess = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_win_tess):
        pytesseract.pytesseract.tesseract_cmd = default_win_tess


# -------------------------------------------------------------------------
# 1. Image Preprocessing & Offline Tesseract OCR
# -------------------------------------------------------------------------

def preprocess_terminal_image(img: Image.Image) -> Image.Image:
    """
    Cleans terminal screenshots from interference noise:
    - Keeps bright-green terminal text (#00FF00).
    - Removes dark background and white/gray strike-through lines.
    - Converts text to black (0) and background to white (255) for high-accuracy OCR.

    Filter Condition:
      G > 110 and G > R * 1.3 and G > B * 1.3 -> Text (0)
      Else -> Background (255)
    """
    img_rgb = img.convert("RGB")
    width, height = img_rgb.size
    raw_bytes = img_rgb.tobytes()

    pixels = bytearray(width * height)

    for i in range(0, len(raw_bytes), 3):
        r = raw_bytes[i]
        g = raw_bytes[i + 1]
        b = raw_bytes[i + 2]

        if g > 110 and g > (r * 1.3) and g > (b * 1.3):
            pixels[i // 3] = 0   # Black text
        else:
            pixels[i // 3] = 255 # Pure white background

    return Image.frombytes("L", (width, height), bytes(pixels))


def solve_crypto_task_offline_sync(image_bytes: bytes) -> Optional[int]:
    """
    Synchronous offline matrix OCR solver:
    1. Preprocesses image by filtering color and eliminating noise lines.
    2. Crops top section containing '[ЗАДАЧА] Найдите блок XX'.
    3. Crops lower matrix area into 7 vertical column strips.
    4. Finds which column contains the matching token and returns its index (1 to 7).
    """
    if not HAS_PYTESSERACT:
        return None

    try:
        raw_image = Image.open(io.BytesIO(image_bytes))
        clean_img = preprocess_terminal_image(raw_image)
        width, height = clean_img.size

        # 1. OCR the header section
        top_h = int(height * 0.32)
        top_crop = clean_img.crop((0, 0, width, top_h))
        header_text = pytesseract.image_to_string(top_crop, config="--psm 6")

        # Extract target 2-character hex/token code
        token_match = re.search(r"блок[^\w]*([A-Za-z0-9]{2})\b", header_text, re.IGNORECASE)
        if not token_match:
            token_match = re.search(r"ЗАДАЧА[^\n\r]*?([A-Za-z0-9]{2})\b", header_text, re.IGNORECASE)

        if not token_match:
            return None

        target_token = token_match.group(1).upper()

        # 2. Divide matrix into 7 vertical columns
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

            if target_token in col_text:
                return col_num

        # Secondary search with whitespace stripped
        for col_num, col_text in column_results.items():
            cleaned_text = re.sub(r"\s+", "", col_text)
            if target_token in cleaned_text:
                return col_num

        return None
    except Exception:
        return None


async def solve_crypto_task_offline(image_bytes: bytes) -> Optional[int]:
    """Non-blocking async wrapper running OCR in a separate thread."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, solve_crypto_task_offline_sync, image_bytes)


# -------------------------------------------------------------------------
# 2. Isolated Device Flashing Session
# -------------------------------------------------------------------------

class DeviceFlashingSession:
    """
    Manages firmware flashing for a specific device in isolation.
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
        self.last_update_time: float = datetime.now().timestamp()

        self._lock = asyncio.Lock()

    def log(self, text: str, level: str = "info"):
        self.manager.add_log(f"[{self.device_name}] {text}", level)

    def parse_message_state(self, text: str):
        pct_match = re.search(r"(?:Процент установки|Прогресс|Установка)[:\s]+(\d{1,3})%", text, re.IGNORECASE)
        if pct_match:
            self.progress_percent = int(pct_match.group(1))

        time_match = re.search(r"(?:Оставшееся время|Осталось|Время)[:\s]+(\d{1,2}:\d{2})", text, re.IGNORECASE)
        if time_match:
            self.remaining_time = time_match.group(1)

        self.last_update_time = datetime.now().timestamp()

    async def handle_update(self, message: Message):
        async with self._lock:
            if not self.is_active:
                return

            text = message.raw_text or message.message or ""
            self.parse_message_state(text)

            # 1. Driver Timeout / Cable Error
            cable_error = any(k in text.lower() for k in [
                "ошибка драйвера", "driver_timeout", "устройство потеряно", 
                "отключился кабель", "сбой подключения", "кабель отключен"
            ])
            if cable_error:
                self.status = "DRIVER_ERROR"
                self.errors_count += 1
                self.log(f"Cable/Driver fault at {self.progress_percent}%! Reconnecting...", "warning")
                
                clicked = await self._click_button_by_patterns(
                    message, 
                    [r"переподключить(?:\s+шнур)?", r"подключить", r"повторить"]
                )
                if clicked:
                    self.last_action = "Reconnected cable"
                    self.status = "FLASHING"
                return

            # 2. Cryptographic Checksum Error -> Offline Tesseract OCR
            crypto_error = any(k in text.lower() for k in [
                "криптографическая ошибка", "crypto_checksum", 
                "найдите блок", "сбой контрольной суммы"
            ])
            if crypto_error:
                self.status = "CRYPTO_PUZZLE"
                self.errors_count += 1
                self.log("Crypto checksum fault! Running offline Tesseract OCR...", "warning")

                if message.photo or message.media:
                    image_bytes = await message.download_media(file=bytes)
                    if image_bytes:
                        col_digit = await solve_crypto_task_offline(image_bytes)
                        if col_digit:
                            self.log(f"Offline OCR verified Column {col_digit}! Clicking...", "success")
                            clicked = await self._click_button_by_digit(message, col_digit)
                            if clicked:
                                self.last_action = f"Selected Column {col_digit}"
                                self.status = "FLASHING"
                                return
                        else:
                            self.log("Offline OCR could not determine column.", "warning")
                    else:
                        self.log("Could not download puzzle image bytes.", "warning")
                return

            # 3. Unknown System Error -> Debug Mode
            unknown_error = any(k in text.lower() for k in [
                "неизвестная ошибка", "режим отладки", "debug_mode", "system_halt"
            ])
            if unknown_error:
                self.status = "UNKNOWN_ERROR"
                self.errors_count += 1
                self.log(f"Unknown system fault at {self.progress_percent}%. Switching to Debug Mode...", "warning")
                
                clicked = await self._click_button_by_patterns(
                    message,
                    [r"перейти в режим отладки", r"режим отладки", r"отладка"]
                )
                if clicked:
                    self.last_action = "Activated debug mode"
                    self.status = "DEBUGGING"
                return

            # 4. Fatal Brick Failure ("кирпич" or "[СБОЙ]")
            brick_detected = any(k in text.lower() for k in [
                "кирпич", "[сбой]", "устройство повреждено", "прошивка не удалась"
            ])
            if brick_detected:
                self.status = "BRICKED"
                self.is_active = False
                self.log("💀 Device flashing failed (BRICKED)! Terminating worker...", "error")
                
                await self._click_button_by_patterns(
                    message,
                    [r"к прошитым телефонам", r"в меню", r"назад", r"закрыть"]
                )
                self.manager.close_session(self.device_name)
                return

            # 5. Successful Completion
            success_detected = any(k in text.lower() for k in [
                "успешно прошит", "прошивка завершена", "устройство готово", 
                "100%", "успех", "готово!"
            ]) and (self.progress_percent >= 100 or "успешно" in text.lower())
            
            if success_detected:
                self.status = "COMPLETED"
                self.progress_percent = 100
                self.is_active = False
                self.log("🎉 Flashing COMPLETED successfully! Firmware verified.", "success")
                
                await self._click_button_by_patterns(
                    message,
                    [r"к прошитым телефонам", r"забрать", r"в инвентарь", r"назад"]
                )
                self.manager.close_session(self.device_name)
                return

            # 6. Standard Active Progress (DO NOT TOUCH BUTTONS)
            self.status = "FLASHING"

    async def _click_button_by_patterns(self, message: Message, patterns: list) -> bool:
        if not message.buttons:
            return False

        for row in message.buttons:
            for btn in row:
                btn_text = btn.text.strip()
                for pat in patterns:
                    if re.search(pat, btn_text, re.IGNORECASE):
                        try:
                            await btn.click()
                            await asyncio.sleep(1.0)
                            return True
                        except (MessageNotModifiedError, FloodWaitError):
                            return True
                        except Exception as e:
                            self.log(f"Button click error: {e}", "error")
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
                        await btn.click()
                        await asyncio.sleep(1.0)
                        return True
                    except Exception as e:
                        self.log(f"Column click error: {e}", "error")
                        return False
        return False


# -------------------------------------------------------------------------
# 3. Central Multi-Device Flashing Manager
# -------------------------------------------------------------------------

class DeviceFlashingManager:
    """
    Orchestrates device workers and Telethon event stream.
    """
    def __init__(self, automator: Any):
        self.automator = automator
        self.enabled: bool = True
        
        self.sessions: Dict[str, DeviceFlashingSession] = {}
        self.msg_to_device: Dict[int, str] = {}

    def add_log(self, text: str, level: str = "info"):
        if hasattr(self.automator, "add_log"):
            self.automator.add_log(text, level)

    def get_or_create_session(self, device_name: str, message_id: int) -> DeviceFlashingSession:
        if device_name not in self.sessions:
            session = DeviceFlashingSession(device_name, message_id, self)
            self.sessions[device_name] = session
            self.msg_to_device[message_id] = device_name
            self.add_log(f"[{device_name}] Initialized new flashing session.", "success")
            return session

        session = self.sessions[device_name]
        session.message_id = message_id
        self.msg_to_device[message_id] = device_name
        return session

    def close_session(self, device_name: str):
        if device_name in self.sessions:
            self.sessions[device_name].is_active = False
            del self.sessions[device_name]

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

    def summary_badge(self) -> str:
        """Returns brief string for header / dashboard."""
        if not self.enabled:
            return "[dim]Flashing: Off[/dim]"
        if not self.sessions:
            return "[dim green]Flashing: Standby (0 active)[/dim green]"
        
        parts = []
        for s in list(self.sessions.values())[:2]:
            parts.append(f"{s.device_name[:12]}: {s.progress_percent}% [{s.remaining_time}]")
        more = f" +{len(self.sessions) - 2}" if len(self.sessions) > 2 else ""
        return f"[bold bright_cyan]⚡ Flashing ({len(self.sessions)}):[/bold bright_cyan] " + ", ".join(parts) + more

    def render_overview_table(self) -> Table:
        table = Table(title="⚡ PHONEX OFFLINE FLASHING SESSIONS", expand=True, border_style="cyan")
        table.add_column("Device Name", style="bold bright_white")
        table.add_column("Progress", style="bold green", justify="center")
        table.add_column("Remaining", style="magenta", justify="center")
        table.add_column("Status", style="yellow")
        table.add_column("Errors", style="red", justify="center")
        table.add_column("Last Action", style="dim")

        if not self.sessions:
            table.add_row("[dim]No active flashing devices[/dim]", "--", "--", "STANDBY", "0", "Listening for bot messages...")
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

    async def on_bot_message_event(self, event):
        """Unified handler for Telegram bot events."""
        if not self.enabled:
            return

        msg: Message = event.message
        if not msg:
            return

        text = msg.raw_text or msg.message or ""

        # Filter flashing-related messages
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
