# -*- coding: utf-8 -*-

"""
File utama untuk menjalankan bot Telegram Islami & Manajemen Grup.
Versi ini berjalan 24/7 dan mendukung fitur pengaturan dan Asmaul Husna.
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
    Defaults, ConversationHandler, CallbackQueryHandler
)
from telegram.constants import ParseMode

# Import untuk server web agar bot tetap aktif.
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Mengimpor semua fungsi dari modul fitur.
from commands import (
    start, help_command, rules, statistic, doa_harian_command, asmaulhusna_command,
    tanya_ai_command, kisah_command, hadith_command, set_reminder, 
    greet_new_member,
    # Impor untuk settings
    settings_command, settings_button_callback, save_welcome_message, save_rules, cancel_settings,
    SELECTING_ACTION, AWAITING_WELCOME_MESSAGE, AWAITING_RULES
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

# --- Bagian Server Keep-Alive ---
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running.")
    def log_message(self, format, *args):
        return

def run_keep_alive_server():
    server_address = ('0.0.0.0', 8080)
    httpd = HTTPServer(server_address, KeepAliveHandler)
    logger.info("Server Keep-Alive dimulai pada port 8080.")
    httpd.serve_forever()

# --- Fungsi Penangan Error ---
async def error_handler(update: Optional[object], context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (kode fungsi error_handler tetap sama)
    pass

# --- Fungsi Inisialisasi Bot ---
async def post_init(application: Application) -> None:
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook berhasil direset (mode polling aktif).")
    except Exception as e:
        logger.error(f"Gagal mereset webhook: {e}")

    # REVISI: Menambahkan /asmaulhusna ke daftar menu
    commands = [
        BotCommand("start", "Memulai bot"),
        BotCommand("help", "Menampilkan bantuan"),
        BotCommand("rules", "Peraturan grup"),
        BotCommand("settings", "(Admin) Atur bot untuk grup ini"),
        BotCommand("statistic", "Statistik grup"),
        BotCommand("doa", "Doa harian acak"),
        BotCommand("asmaulhusna", "Menampilkan Asmaul Husna acak"),
        BotCommand("ayat", "Cari ayat Al-Qur'an (contoh: /ayat 1:5)"),
        BotCommand("tafsir", "Cari tafsir ayat (contoh: /tafsir 1:5)"),
        BotCommand("hadits", "Cari hadits (contoh: /hadits bukhari 52)"),
        BotCommand("tanya", "Tanya jawab Islami dengan AI"),
        BotCommand("kisah", "Kisah Nabi atau Sahabat dari AI"),
        BotCommand("ingatkan", "Buat pengingat (contoh: /ingatkan 5m pesan)"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Menu perintah bot berhasil diatur.")

def main() -> None:
    """Fungsi utama untuk mengatur dan menjalankan bot."""
    keep_alive_thread = Thread(target=run_keep_alive_server, daemon=True)
    keep_alive_thread.start()
    
    defaults = Defaults(parse_mode="HTML", link_preview_options=LinkPreviewOptions(is_disabled=True))
    application = Application.builder().token(BOT_TOKEN).defaults(defaults).post_init(post_init).build()

    application.add_error_handler(error_handler)

    # --- Handler untuk /settings ---
    settings_handler = ConversationHandler(
        entry_points=[CommandHandler("settings", settings_command)],
        states={
            SELECTING_ACTION: [CallbackQueryHandler(settings_button_callback)],
            AWAITING_WELCOME_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_welcome_message)],
            AWAITING_RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_rules)],
        },
        fallbacks=[CommandHandler("batal", cancel_settings)],
    )
    application.add_handler(settings_handler)

    # --- Pendaftaran Handler Lainnya ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("statistic", statistic))
    application.add_handler(CommandHandler("doa", doa_harian_command))
    application.add_handler(CommandHandler("asmaulhusna", asmaulhusna_command)) # <-- BARU
    application.add_handler(CommandHandler("ingatkan", set_reminder))
    application.add_handler(CommandHandler("ayat", send_verse_command))
    application.add_handler(CommandHandler("tafsir", send_tafsir_command))
    application.add_handler(CommandHandler("hadits", hadith_command))
    
    if gemini_model:
        application.add_handler(CommandHandler("tanya", tanya_ai_command))
        application.add_handler(CommandHandler("kisah", kisah_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderate_chat))
        logger.info("Handler untuk fitur AI telah aktif.")

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_member))

    # ... (kode job_queue dan application.run_polling() tetap sama)
    
    logger.info("Bot mulai berjalan...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
