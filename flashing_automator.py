"""
PHONEX SOFT - Device Flashing Automator (PhoneGet Telegram Bot)
==============================================================
Fully asynchronous, multi-device firmware flashing engine using Telethon and Gemini Vision.

Key Architectural Components:
1. DeviceFlashingSession: Isolated instance per device (tracks percentage, state, errors, locks).
2. solve_crypto_task: Gemini 2.5 Flash Vision solver for the 7-column hex/crypto grid puzzle.
3. DeviceFlashingManager: Central orchestrator managing Telethon events and device lifecycles.
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

from telethon import TelegramClient, events
from telethon.tl.custom.message import Message
from telethon.errors import MessageNotModifiedError, FloodWaitError

# Import Google GenAI SDK (gemini-2.5-flash)
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

from config import AppConfig

console = Console()

# -------------------------------------------------------------------------
# 1. Vision Solver for Cryptographic Puzzle (gemini-2.5-flash)
# -------------------------------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

async def solve_crypto_task(image_bytes: bytes) -> Optional[int]:
    """
    Solves the visual terminal puzzle from PhoneGet bot using Gemini 2.5 Flash.
    
    Task:
    1. Reads line: "[ЗАДАЧА] Найдите блок XX" (e.g. XX = A7, 3F, 9C, etc.)
    2. Searches the 7-column terminal grid below for token XX.
    3. Returns the matching column index as an integer from 1 to 7.
    """
    if not HAS_GENAI:
        console.print("[bold red]❌ Google GenAI SDK not installed! Run: pip install google-genai[/bold red]")
        return None

    api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        console.print("[bold red]❌ GEMINI_API_KEY is not set in environment or .env![/bold red]")
        return None

    prompt = (
        "You are an expert OCR and visual cryptographic puzzle solver.\n"
        "Analyze this terminal screenshot carefully:\n"
        "1. Find the target token specified in the line: '[ЗАДАЧА] Найдите блок XX' (where XX is a 2-character hexadecimal/alphanumeric code).\n"
        "2. Look at the grid below that has exactly 7 columns (numbered 1 to 7 from left to right).\n"
        "3. Find which column contains the exact token XX.\n\n"
        "CRITICAL REQUIREMENT:\n"
        "Respond with ONLY a single digit between 1 and 7 corresponding to the correct column number.\n"
        "Do not include any explanation, quotes, spaces, punctuation, or markdown. Just the single digit (e.g., 4)."
    )

    def _sync_gemini_call() -> str:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                prompt
            ]
        )
        return response.text.strip() if response and response.text else ""

    try:
        # Run in thread pool to prevent blocking Telethon event loop
        raw_output = await asyncio.to_thread(_sync_gemini_call)
        console.print(f"[dim cyan]🤖 Gemini Vision Raw Response:[/dim cyan] '{raw_output}'")
        
        # Parse column number 1-7
        match = re.search(r"\b([1-7])\b", raw_output)
        if match:
            return int(match.group(1))
        
        console.print(f"[bold yellow]⚠️ Could not parse column digit (1-7) from Gemini output: '{raw_output}'[/bold yellow]")
        return None
    except Exception as e:
        console.print(f"[bold red]❌ Gemini Vision API error: {e}[/bold red]")
        return None


# -------------------------------------------------------------------------
# 2. Isolated Device Flashing Session
# -------------------------------------------------------------------------

class DeviceFlashingSession:
    """
    Tracks and handles flashing state for a single phone in isolation.
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
        self.last_action: str = "Started tracking"
        self.last_action_timestamp: float = datetime.now().timestamp()
        
        # Concurrency lock to prevent concurrent button clicks on the same message
        self._lock = asyncio.Lock()

    def log(self, text: str, style: str = "white"):
        ts = datetime.now().strftime("%H:%M:%S")
        console.print(f"[{ts}] [[bold cyan]{self.device_name}[/bold cyan]] [{style}]{text}[/{style}]")

    def parse_message_state(self, text: str):
        """Extracts installation percent and remaining time from bot text."""
        # Progress percent: "Процент установки: 45%" or "Прогресс: 45%"
        pct_match = re.search(r"(?:Процент установки|Прогресс|Установка)[:\s]+(\d{1,3})%", text, re.IGNORECASE)
        if pct_match:
            self.progress_percent = int(pct_match.group(1))

        # Remaining time: "Оставшееся время: 02:45"
        time_match = re.search(r"(?:Оставшееся время|Осталось|Время)[:\s]+(\d{1,2}:\d{2})", text, re.IGNORECASE)
        if time_match:
            self.remaining_time = time_match.group(1)

    async def handle_update(self, message: Message):
        """Processes message updates and triggers corresponding button actions."""
        async with self._lock:
            if not self.is_active:
                return

            text = message.raw_text or message.message or ""
            self.parse_message_state(text)

            # -------------------------------------------------------------
            # Case 1: Cable Disconnection / Driver Timeout Error
            # -------------------------------------------------------------
            cable_error_detected = any(k in text.lower() for k in [
                "ошибка драйвера", "driver_timeout", "устройство потеряно", 
                "отключился кабель", "сбой подключения", "кабель отключен"
            ])
            if cable_error_detected:
                self.status = "DRIVER_ERROR"
                self.errors_count += 1
                self.log(f"⚠️ Driver/Cable fault detected at {self.progress_percent}%! Reconnecting cable...", "bold yellow")
                
                clicked = await self._click_button_by_patterns(
                    message, 
                    [r"переподключить(?:\s+шнур)?", r"подключить", r"повторить"]
                )
                if clicked:
                    self.last_action = "Reconnected cable"
                    self.status = "FLASHING"
                return

            # -------------------------------------------------------------
            # Case 2: Cryptographic / Hex Checksum Error (Vision Puzzle)
            # -------------------------------------------------------------
            crypto_error_detected = any(k in text.lower() for k in [
                "криптографическая ошибка", "crypto_checksum", 
                "найдите блок", "сбой контрольной суммы"
            ])
            if crypto_error_detected:
                self.status = "CRYPTO_PUZZLE"
                self.errors_count += 1
                self.log("🧩 Cryptographic checksum error detected! Downloading puzzle image...", "bold magenta")

                # If message has image media attached, download in-memory
                if message.photo or message.media:
                    image_bytes = await message.download_media(file=bytes)
                    if image_bytes:
                        self.log("🔍 Solving 7-column crypto task via Gemini Vision...", "cyan")
                        col_digit = await solve_crypto_task(image_bytes)
                        if col_digit:
                            self.log(f"🎯 Target block identified in Column {col_digit}! Clicking button...", "bold green")
                            clicked = await self._click_button_by_digit(message, col_digit)
                            if clicked:
                                self.last_action = f"Selected crypto column {col_digit}"
                                self.status = "FLASHING"
                                return
                        else:
                            self.log("⚠️ Vision solver could not identify column. Retrying...", "yellow")
                    else:
                        self.log("⚠️ Could not download photo bytes from message.", "yellow")
                else:
                    self.log("⚠️ Crypto error mentioned but message has no attached image.", "yellow")

            # -------------------------------------------------------------
            # Case 3: Unknown System Error -> Debug Mode Required
            # -------------------------------------------------------------
            unknown_error_detected = any(k in text.lower() for k in [
                "неизвестная ошибка", "режим отладки", "debug_mode", "system_halt"
            ])
            if unknown_error_detected:
                self.status = "UNKNOWN_ERROR"
                self.errors_count += 1
                self.log(f"🛠 Unknown system error at {self.progress_percent}%. Entering debug mode...", "bold yellow")
                
                clicked = await self._click_button_by_patterns(
                    message,
                    [r"перейти в режим отладки", r"режим отладки", r"отладка"]
                )
                if clicked:
                    self.last_action = "Switched to debug mode"
                    self.status = "DEBUGGING"
                return

            # -------------------------------------------------------------
            # Case 4: Fatal Error / Brick Failure ("кирпич" or "[СБОЙ]")
            # -------------------------------------------------------------
            brick_detected = any(k in text.lower() for k in [
                "кирпич", "[сбой]", "устройство повреждено", "прошивка не удалась"
            ])
            if brick_detected:
                self.status = "BRICKED"
                self.is_active = False
                self.log("💀 Device flashing failed critically (BRICKED)! Closing session...", "bold red")
                
                await self._click_button_by_patterns(
                    message,
                    [r"к прошитым телефонам", r"в меню", r"назад", r"закрыть"]
                )
                self.manager.close_session(self.device_name)
                return

            # -------------------------------------------------------------
            # Case 5: Successful Firmware Flash Completion
            # -------------------------------------------------------------
            success_detected = any(k in text.lower() for k in [
                "успешно прошит", "прошивка завершена", "устройство готово", 
                "100%", "успех", "готово!"
            ]) and (self.progress_percent >= 100 or "успешно" in text.lower())
            
            if success_detected:
                self.status = "COMPLETED"
                self.progress_percent = 100
                self.is_active = False
                self.log("🎉 Flashing COMPLETED successfully (100%)! Device is fully functional.", "bold green")
                
                await self._click_button_by_patterns(
                    message,
                    [r"к прошитым телефонам", r"забрать", r"в инвентарь", r"назад"]
                )
                self.manager.close_session(self.device_name)
                return

            # -------------------------------------------------------------
            # Case 6: Normal Active Flashing Progress
            # -------------------------------------------------------------
            self.status = "FLASHING"
            self.log(f"⚡ Flashing progress: {self.progress_percent}% | Time left: {self.remaining_time}", "green")

    async def _click_button_by_patterns(self, message: Message, patterns: list) -> bool:
        """Finds and clicks an inline button matching one of the regex patterns."""
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
                            self.log(f"Button click warning: {e}", "dim yellow")
                            return True
                        except Exception as e:
                            self.log(f"Button click error: {e}", "bold red")
                            return False
        return False

    async def _click_button_by_digit(self, message: Message, digit: int) -> bool:
        """Finds and clicks an inline button labeled with digit (1-7)."""
        if not message.buttons:
            return False

        target_str = str(digit)
        for row in message.buttons:
            for btn in row:
                btn_text = btn.text.strip()
                # Check for exact digit or bracketed digit e.g. "3" or "[3]" or "№3"
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
    Manages client connection, event dispatching, and multi-device session lifecycles.
    """
    def __init__(self, target_bot: str = "@phonegetcardsbot"):
        self.config: AppConfig = AppConfig.load()
        self.target_bot: str = target_bot
        self.client: Optional[TelegramClient] = None
        self.target_entity = None
        
        # Mapping: device_name -> DeviceFlashingSession
        self.sessions: Dict[str, DeviceFlashingSession] = {}
        # Mapping: message_id -> device_name
        self.msg_to_device: Dict[int, str] = {}
        
        self._running = False

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
        """
        Parses device name from headers such as:
        - "Прошивка Google Nexus One -> ..."
        - "Прошивка: Samsung Galaxy S6 Edge"
        - "📱 Google Nexus One (Прошивка)"
        """
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
        table = Table(title="⚡ PHONEX ACTIVE FLASHING SESSIONS", expand=True, border_style="cyan")
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
        """Unified handler for NewMessage and MessageEdited events from target bot."""
        msg: Message = event.message
        if not msg:
            return

        text = msg.raw_text or msg.message or ""
        
        # Check if message is relevant to flashing
        is_flashing_msg = any(k in text.lower() for k in [
            "прошивка", "процент установки", "оставшееся время", 
            "режим отладки", "криптографическая ошибка", "драйвер"
        ])
        if not is_flashing_msg:
            return

        # Associate with device session
        device_name = self.extract_device_name(text)
        if not device_name:
            # Fallback check by message ID if previously registered
            if msg.id in self.msg_to_device:
                device_name = self.msg_to_device[msg.id]

        if not device_name:
            device_name = f"Device_Msg_{msg.id}"

        session = self.get_or_create_session(device_name, msg.id)
        # Dispatch update to isolated worker
        await session.handle_update(msg)

    async def start(self):
        """Initializes Telethon and starts listening to events."""
        console.clear()
        console.print(Panel(
            "[bold bright_cyan]⚡ PHONEX SOFT - AUTONOMOUS FIRMWARE FLASHING ENGINE[/bold bright_cyan]\n"
            "[dim]Telethon MTProto + Gemini 2.5 Flash Vision Solver[/dim]",
            border_style="cyan"
        ))

        # Check Gemini API Key
        if not os.getenv("GEMINI_API_KEY"):
            console.print("[yellow]⚠️ Warning: GEMINI_API_KEY not found in environment. Set it in .env for vision puzzles![/yellow]\n")

        session_path = "data/session.dat"
        session_str = ""
        if os.path.exists(session_path):
            with open(session_path, "r", encoding="utf-8") as f:
                session_str = f.read().strip()

        from telethon.sessions import StringSession
        self.client = TelegramClient(StringSession(session_str), self.config.api_id, self.config.api_hash)
        await self.client.connect()

        if not await self.client.is_user_authorized():
            console.print("[bold red]❌ Client is not authorized! Please run 'main.py' first and log in with QR or Phone.[/bold red]")
            return

        me = await self.client.get_me()
        self.target_entity = await self.client.get_entity(self.target_bot)
        
        console.print(f"[bold green]✅ Connected as @{me.username or me.first_name}![/bold green]")
        console.print(f"[bold cyan]🎯 Monitoring bot: {self.target_bot}[/bold cyan]\n")

        # Register event listeners for both New Messages and Message Edits
        self.client.add_event_handler(
            self._on_bot_message_event,
            events.NewMessage(chats=self.target_entity)
        )
        self.client.add_event_handler(
            self._on_bot_message_event,
            events.MessageEdited(chats=self.target_entity)
        )

        console.print("[bold bright_green]🎧 Event listeners active. Waiting for device flashing messages...[/bold bright_green]")
        console.print("[dim]Press Ctrl+C to stop.[/dim]\n")

        try:
            while True:
                await asyncio.sleep(5.0)
                # Print periodic overview status table if sessions are active
                if self.sessions:
                    console.print(self.render_overview_table())
        except (KeyboardInterrupt, asyncio.CancelledError):
            console.print("\n[bold yellow]Stopping flashing manager...[/bold yellow]")
        finally:
            if self.client and self.client.is_connected():
                await self.client.disconnect()
            console.print("[bold green]Flashing manager stopped cleanly.[/bold green]")


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
