# -*- coding: utf-8 -*-

"""
File utama untuk menjalankan bot Telegram Islami & Manajemen Grup.
Versi ini telah direvisi untuk meningkatkan stabilitas di platform hosting seperti Railway.
"""

import logging
import os
import traceback
import html
import json
import datetime
from typing import Optional

from telegram import BotCommand, Update, LinkPreviewOptions
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes,
    Defaults
)
from telegram.constants import ParseMode

# Import untuk server web agar bot tetap aktif.
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Mengimpor semua fungsi dari modul fitur.
from commands import (
    start, help_command, rules, statistic, doa_harian_command,
    tanya_ai_command, kisah_command, hadith_command, set_reminder, 
    greet_new_member
)
from quran_features import send_verse_command, send_tafsir_command, send_daily_verse
from ai_features import moderate_chat, gemini_model

# --- Konfigurasi Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- Konfigurasi Bot dari Environment Variables ---
try:
    BOT_TOKEN = os.environ['BOT_TOKEN']
except KeyError:
    logger.critical("FATAL ERROR: BOT_TOKEN tidak ditemukan! Bot tidak dapat dijalankan.")
    exit()

DEVELOPER_CHAT_ID = os.environ.get('DEVELOPER_CHAT_ID')
TARGET_GROUP_ID = os.environ.get('TARGET_GROUP_ID')

# --- Penjadwalan Aktivitas Bot ---
wib = datetime.timezone(datetime.timedelta(hours=7))

class IsActiveFilter(filters.BaseFilter):
    def filter(self, update: Update) -> bool:
        return update.get_bot().bot_data.get('is_active', False)

async def activate_bot(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.bot_data['is_active'] = True
    logger.info("Bot diaktifkan sesuai jadwal (07:00 WIB).")

async def deactivate_bot(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.bot_data['is_active'] = False
    logger.info("Bot dinonaktifkan sesuai jadwal (00:00 WIB).")

# --- Bagian Server Keep-Alive dengan Logging ---
class KeepAliveHandler(BaseHTTPRequestHandler):
    """Handler untuk merespons permintaan HTTP dan menjaga bot tetap aktif."""
    def do_GET(self):
        # REVISI: Menambahkan logging untuk memastikan Railway melakukan ping.
        logger.info(f"Keep-alive server menerima permintaan GET dari {self.client_address[0]}")
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running and active.")
    
    def log_message(self, format, *args):
        # Mencegah logging HTTP default yang berlebihan ke konsol.
        return

def run_keep_alive_server():
    server_address = ('0.0.0.0', 8080)
    httpd = HTTPServer(server_address, KeepAliveHandler)
    logger.info("Keep-alive server dimulai pada port 8080.")
    httpd.serve_forever()

# --- Fungsi Penangan Error ---
async def error_handler(update: Optional[object], context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    # ... (kode notifikasi error ke developer tetap sama)

# --- Fungsi Inisialisasi Bot ---
async def post_init(application: Application) -> None:
    # ... (kode post_init tetap sama)
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook berhasil direset (mode polling aktif).")
    except Exception as e:
        logger.error(f"Gagal mereset webhook: {e}")

    commands = [
        BotCommand("start", "Memulai bot"),
        BotCommand("help", "Menampilkan bantuan"),
        # ... (daftar perintah lainnya)
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Menu perintah bot berhasil diatur.")

def main() -> None:
    """Fungsi utama untuk mengatur dan menjalankan bot."""
    keep_alive_thread = Thread(target=run_keep_alive_server, daemon=True)
    keep_alive_thread.start()

    defaults = Defaults(parse_mode=ParseMode.HTML, link_preview_options=LinkPreviewOptions(is_disabled=True))
    application = Application.builder().token(BOT_TOKEN).defaults(defaults).post_init(post_init).build()

    # --- Atur Status Awal & Jadwal Aktivitas ---
    now_wib = datetime.datetime.now(wib)
    is_currently_active = 7 <= now_wib.hour < 24
    application.bot_data['is_active'] = is_currently_active
    logger.info(f"Inisialisasi bot. Status aktif awal: {is_currently_active}")

    if application.job_queue:
        application.job_queue.run_daily(deactivate_bot, time=datetime.time(hour=0, minute=0, tzinfo=wib), name="deactivate_bot")
        application.job_queue.run_daily(activate_bot, time=datetime.time(hour=7, minute=0, tzinfo=wib), name="activate_bot")
        logger.info("Jadwal aktivasi (07:00 WIB) dan deaktivasi (00:00 WIB) telah diatur.")
    
    # ... (sisa pendaftaran handler dan job queue tetap sama)

    is_active_filter = IsActiveFilter()
    application.add_error_handler(error_handler)

    # Pendaftaran handler dengan filter
    application.add_handler(CommandHandler("start", start, filters=is_active_filter))
    # ... (semua handler lainnya menggunakan is_active_filter)
    
    logger.info("Bot mulai berjalan...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    # REVISI: Tambahkan log ini untuk melihat apakah bot berhenti secara normal.
    logger.info("Aplikasi telah berhenti. Keluar dari main().")

if __name__ == "__main__":
    main()
