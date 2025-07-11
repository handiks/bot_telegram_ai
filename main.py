# -*- coding: utf-8 -*-

"""
File utama untuk menjalankan bot Telegram Islami & Manajemen Grup.
Versi ini telah direfaktor untuk memisahkan logika fitur ke dalam modul terpisah
dan ditambahkan fitur jadwal aktif untuk menghemat sumber daya.
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

# Import untuk server web agar bot tetap aktif di platform seperti Replit.
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler

# Mengimpor semua fungsi dari modul fitur.
from commands import (
    start, help_command, rules, statistic, doa_harian_command,
    tanya_ai_command, kisah_command, hadith_command, set_reminder, 
    greet_new_member
)
from quran_features import send_verse_command, send_tafsir_command, send_daily_verse
from ai_features import moderate_chat, gemini_model # Import gemini_model untuk pengecekan

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

if not TARGET_GROUP_ID:
    logger.warning("TARGET_GROUP_ID tidak ditemukan. Pengiriman pesan terjadwal tidak akan berfungsi.")
if not gemini_model:
    logger.warning("Fitur AI tidak aktif karena model gagal diinisialisasi (cek GEMINI_API_KEY).")

# --- Penjadwalan Aktivitas Bot ---

# Tentukan zona waktu WIB (UTC+7)
wib = datetime.timezone(datetime.timedelta(hours=7))

class IsActiveFilter(filters.BaseFilter):
    """Filter kustom untuk memeriksa apakah bot sedang dalam jam aktif."""
    def __init__(self):
        super().__init__(name='IsActiveFilter')

    def filter(self, update: Update) -> bool:
        # Mengambil status dari bot_data. Jika kunci tidak ada, anggap tidak aktif.
        return update.get_bot().bot_data.get('is_active', False)

async def activate_bot(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengaktifkan bot pada jam 7 pagi WIB."""
    context.bot_data['is_active'] = True
    logger.info("Bot diaktifkan sesuai jadwal. Siap menerima perintah.")
    if DEVELOPER_CHAT_ID:
        try:
            await context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text="✅ Bot sekarang AKTIF (07:00 WIB).")
        except Exception as e:
            logger.warning(f"Gagal mengirim notifikasi aktif ke developer: {e}")

async def deactivate_bot(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menonaktifkan bot pada jam 12 malam WIB."""
    context.bot_data['is_active'] = False
    logger.info("Bot dinonaktifkan sesuai jadwal. Masuk mode tidur.")
    if DEVELOPER_CHAT_ID:
        try:
            await context.bot.send_message(chat_id=DEVELOPER_CHAT_ID, text="🌙 Bot sekarang NONAKTIF (00:00 WIB).")
        except Exception as e:
            logger.warning(f"Gagal mengirim notifikasi nonaktif ke developer: {e}")

# --- Perintah Khusus Developer ---
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Perintah khusus untuk developer memeriksa status bot."""
    if not update.effective_user or str(update.effective_user.id) != DEVELOPER_CHAT_ID:
        return  # Abaikan jika bukan developer

    is_active = context.bot_data.get('is_active', False)
    status_text = (
        f"<b>Bot Status Check</b>\n\n"
        f"<b>Status:</b> {'✅ Aktif' if is_active else '🌙 Tidur'}\n"
        f"<b>Waktu Server (WIB):</b> {datetime.datetime.now(wib).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    await update.message.reply_text(status_text)

# --- Bagian Server Keep-Alive ---
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Bot is running.")

def run_keep_alive_server():
    server_address = ('0.0.0.0', 8080)
    httpd = HTTPServer(server_address, KeepAliveHandler)
    logger.info("Keep-alive server dimulai pada port 8080.")
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
    
    if TARGET_GROUP_ID and application.job_queue:
        time_afternoon = datetime.time(hour=16, minute=0, tzinfo=wib)
        application.job_queue.run_daily(send_daily_verse, time_afternoon, name="daily_afternoon_verse")
        logger.info(f"Jadwal pengiriman ayat harian sore telah diatur.")

    is_active_filter = IsActiveFilter()
    application.add_error_handler(error_handler)

    # --- Pendaftaran Handler ---
    # Perintah khusus developer (tanpa filter aktif)
    if DEVELOPER_CHAT_ID:
        application.add_handler(CommandHandler("status", status_command))

    # Perintah dan pesan untuk pengguna (dengan filter aktif)
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
        logger.info("Handler untuk fitur AI telah aktif dan terikat pada jadwal.")

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS & is_active_filter, greet_new_member))

    logger.info("Bot mulai berjalan...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
