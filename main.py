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
    """Menjalankan server HTTP di thread terpisah dengan pesan instruksional."""
    server_address = ('0.0.0.0', 8080)
    httpd = HTTPServer(server_address, KeepAliveHandler)
    # REVISI: Menambahkan pesan yang lebih jelas di log untuk membantu konfigurasi.
    logger.info("================================================================")
    logger.info("Server Keep-Alive dimulai pada port 8080.")
    logger.info("PASTIKAN di pengaturan Railway, Anda telah mengatur:")
    logger.info("1. Healthcheck untuk path '/' pada port 8080.")
    logger.info("2. Port 8080 diekspos ke publik (Expose Port).")
    logger.info("================================================================")
    httpd.serve_forever()

# --- Fungsi Penangan Error ---
async def error_handler(update: Optional[object], context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"Terjadi exception:\n<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )
    if DEVELOPER_CHAT_ID:
        try:
            await context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Gagal mengirim notifikasi error ke developer: {e}")

# --- Fungsi Inisialisasi Bot ---
async def post_init(application: Application) -> None:
    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook berhasil direset (mode polling aktif).")
    except Exception as e:
        logger.error(f"Gagal mereset webhook: {e}")

    commands = [
        BotCommand("start", "Memulai bot"),
        BotCommand("help", "Menampilkan bantuan"),
        BotCommand("rules", "Peraturan grup"),
        BotCommand("statistic", "Statistik grup"),
        BotCommand("doa", "Doa harian acak"),
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
    logger.info("Memulai fungsi main(). Menginisialisasi bot...")
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
    
    is_active_filter = IsActiveFilter()
    application.add_error_handler(error_handler)

    # Pendaftaran handler dengan filter
    application.add_handler(CommandHandler("start", start, filters=is_active_filter))
    application.add_handler(CommandHandler("help", help_command, filters=is_active_filter))
    application.add_handler(CommandHandler("rules", rules, filters=is_active_filter))
    application.add_handler(CommandHandler("statistic", statistic, filters=is_active_filter))
    application.add_handler(CommandHandler("doa", doa_harian_command, filters=is_active_filter))
    application.add_handler(CommandHandler("ingatkan", set_reminder, filters=is_active_filter))
    application.add_handler(CommandHandler("ayat", send_verse_command, filters=is_active_filter))
    application.add_handler(CommandHandler("tafsir", send_tafsir_command, filters=is_active_filter))
    application.add_handler(CommandHandler("hadits", hadith_command, filters=is_active_filter))

    if gemini_model:
        application.add_handler(CommandHandler("tanya", tanya_ai_command, filters=is_active_filter))
        application.add_handler(CommandHandler("kisah", kisah_command, filters=is_active_filter))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & is_active_filter, moderate_chat))
    
    logger.info("Bot mulai berjalan...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    logger.info("Aplikasi telah berhenti. Keluar dari main().")

if __name__ == "__main__":
    main()
