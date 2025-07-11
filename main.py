# -*- coding: utf-8 -*-

"""
File utama untuk menjalankan bot Telegram.
Versi ini telah direfaktor untuk memisahkan logika fitur ke dalam modul terpisah.
"""

import logging
import os
import traceback
import datetime
from typing import Optional

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Import untuk server web agar bot tetap aktif
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Mengimpor semua fungsi dari commands.py, termasuk yang baru
from commands import (
    start, 
    help_command, 
    rules, 
    statistic, 
    doa_harian_command,
    tanya_ai_command,
    kisah_command,
    hadith_command,
    set_reminder, 
    greet_new_member
)

# Mengimpor fitur Al-Qur'an yang telah direfaktor dari file quran_features.py
from quran_features import send_verse_command, send_tafsir_command, send_daily_verse

# Mengimpor fitur AI
from ai_features import moderate_chat

# Atur logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# Kurangi verbositas logger dari library HTTP yang digunakan oleh python-telegram-bot
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


# --- Bagian Server Keep-Alive ---
class KeepAliveHandler(BaseHTTPRequestHandler):
    """Handler sederhana untuk merespons permintaan HTTP dan menjaga bot tetap aktif."""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is running.")

def run_keep_alive_server():
    """Menjalankan server HTTP di thread terpisah."""
    server_address = ('0.0.0.0', 8080)
    httpd = HTTPServer(server_address, KeepAliveHandler)
    logger.info("Keep-alive server started on port 8080.")
    httpd.serve_forever()


# --- Fungsi Penangan Error ---
async def error_handler(update: Optional[object], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencatat semua error yang muncul."""
    logger.error("Terjadi error saat menangani update:", exc_info=context.error)
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    print("--- TRACEBACK LENGKAP ---\n" + tb_string + "--------------------------")


# --- Fungsi untuk dijalankan setelah bot siap ---
async def post_init(application: Application) -> None:
    """Fungsi ini akan dijalankan setelah aplikasi siap tetapi sebelum polling dimulai."""
    try:
        # Menghapus webhook yang mungkin ada untuk memastikan bot berjalan dengan polling
        await application.bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook berhasil direset.")
    except Exception as e:
        logger.error(f"Gagal mereset webhook: {e}")

    # Mengatur daftar perintah yang akan muncul di menu Telegram
    commands = [
        BotCommand("start", "Memulai bot"),
        BotCommand("help", "Menampilkan bantuan"),
        BotCommand("rules", "Menampilkan peraturan grup"),
        BotCommand("statistic", "Menampilkan statistik grup"),
        BotCommand("doa", "Menampilkan doa harian acak"),
        BotCommand("tanya", "Tanya jawab Islami dengan AI"),
        BotCommand("kisah", "Kisah Nabi atau Sahabat"),
        BotCommand("ingatkan", "Mengatur pengingat (misal: /ingatkan 5m pesan)"),
        BotCommand("ayat", "Mengirim ayat Al-Qur'an (misal: /ayat 1:5)"),
        BotCommand("tafsir", "Menampilkan tafsir ayat (misal: /tafsir 1:5)"),
        BotCommand("hadits", "Mencari hadits (misal: /hadits bukhari 52)"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Menu perintah berhasil diatur.")


def main() -> None:
    """Fungsi utama untuk mengatur dan menjalankan bot."""
    # Jalankan server keep-alive di thread terpisah agar tidak memblokir bot
    keep_alive_thread = Thread(target=run_keep_alive_server)
    keep_alive_thread.daemon = True
    keep_alive_thread.start()

    # Ambil token dan ID dari environment variables (Secrets di Replit)
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    TARGET_GROUP_ID = os.environ.get('TARGET_GROUP_ID')
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

    if not BOT_TOKEN:
        logger.critical("FATAL ERROR: BOT_TOKEN tidak ditemukan! Pastikan sudah diatur di Secrets.")
        return
    if not TARGET_GROUP_ID:
        logger.warning("WARNING: TARGET_GROUP_ID tidak ditemukan! Pengiriman pesan terjadwal tidak akan berfungsi.")
    if not GEMINI_API_KEY:
        logger.warning("WARNING: GEMINI_API_KEY tidak ditemukan! Fitur AI tidak akan aktif.")

    # Bangun aplikasi bot
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Daftarkan handler error
    application.add_error_handler(error_handler)

    # --- Daftarkan semua handler untuk setiap perintah ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("statistic", statistic))
    application.add_handler(CommandHandler("doa", doa_harian_command))
    application.add_handler(CommandHandler("tanya", tanya_ai_command))
    application.add_handler(CommandHandler("kisah", kisah_command))
    application.add_handler(CommandHandler("ingatkan", set_reminder))
    application.add_handler(CommandHandler("hadits", hadith_command))

    # Handler dari quran_features.py
    application.add_handler(CommandHandler("ayat", send_verse_command))
    application.add_handler(CommandHandler("tafsir", send_tafsir_command))

    # Handler untuk sapaan anggota baru
    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_member))

    # Handler untuk moderasi AI
    if GEMINI_API_KEY:
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderate_chat))
        logger.info("Handler moderasi AI telah aktif.")

    # Atur jadwal pengiriman otomatis jika TARGET_GROUP_ID tersedia
    if TARGET_GROUP_ID and application.job_queue:
        time_morning = datetime.time(hour=22, minute=0, tzinfo=datetime.timezone.utc)
        application.job_queue.run_daily(send_daily_verse, time_morning, name="daily_morning_verse")

        time_evening = datetime.time(hour=10, minute=0, tzinfo=datetime.timezone.utc)
        application.job_queue.run_daily(send_daily_verse, time_evening, name="daily_evening_verse")

        logger.info("Jadwal pengiriman ayat harian telah diatur.")
    elif not application.job_queue:
        logger.warning("JobQueue tidak tersedia, fitur pengiriman otomatis tidak dapat dijalankan.")

    # Mulai bot
    logger.info("Bot sedang berjalan...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
