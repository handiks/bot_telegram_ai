# -*- coding: utf-8 -*-

"""
Modul ini berisi semua fungsi dasar yang dipanggil oleh pengguna melalui perintah.
Sistem peringatan telah dipusatkan untuk digunakan oleh admin dan AI.
"""

import logging
import requests 
import random
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from telegram.error import BadRequest

# Mengimpor model AI dan handler database
from ai_features import gemini_model
import db_handler

# Inisialisasi logger
logger = logging.getLogger(__name__)

# State untuk ConversationHandler (untuk fitur /settings)
(SELECTING_ACTION, AWAITING_WELCOME_MESSAGE, AWAITING_RULES) = range(3)

# --- Daftar Mutiara Kata Islami ---
ISLAMIC_QUOTES = [
    # ... (data kutipan tetap sama)
]

# --- Fungsi Helper ---

async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    # ... (kode fungsi is_user_admin tetap sama)
    pass

async def check_admin_and_bot_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    # ... (kode fungsi check_admin_and_bot_permissions tetap sama)
    pass

# --- FUNGSI BARU: Logika Peringatan Terpusat ---

async def issue_warning(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_to_warn, warned_by: str, reason: str = None):
    """
    Menangani logika pemberian peringatan, pengiriman pesan, dan pengecekan batas.
    Bisa dipanggil oleh admin (manual) atau AI (otomatis).
    """
    total_warnings = db_handler.add_user_warning(chat_id, user_to_warn.id)
    warn_limit = db_handler.get_group_setting(chat_id, 'warn_limit', 3)

    # Buat pesan peringatan
    warning_message = (
        f"⚠️ Pengguna {user_to_warn.mention_html()} telah diberi peringatan oleh {warned_by}.\n"
    )
    if reason:
        warning_message += f"Alasan: <i>{reason}</i>\n"
    warning_message += f"Total peringatan: <b>{total_warnings}/{warn_limit}</b>."

    await context.bot.send_message(chat_id, warning_message, parse_mode=ParseMode.HTML)

    # Jika batas tercapai, keluarkan pengguna
    if total_warnings >= warn_limit:
        try:
            await context.bot.ban_chat_member(chat_id, user_to_warn.id)
            # Langsung unban agar bisa diundang kembali jika diperlukan
            await context.bot.unban_chat_member(chat_id, user_to_warn.id)
            
            await context.bot.send_message(
                chat_id,
                f"🚫 {user_to_warn.mention_html()} telah dikeluarkan dari grup karena mencapai batas {warn_limit} peringatan."
            )
            # Hapus catatan peringatan setelah dikeluarkan
            db_handler.clear_user_warnings(chat_id, user_to_warn.id)
        except Exception as e:
            logger.error(f"Gagal mengeluarkan pengguna {user_to_warn.id}: {e}")
            await context.bot.send_message(chat_id, f"Gagal mengeluarkan {user_to_warn.mention_html()}. Periksa izin saya.")

# --- Fungsi Perintah Moderasi (Direvisi) ---

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memberikan peringatan kepada pengguna (manual oleh admin)."""
    if not await check_admin_and_bot_permissions(update, context):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Gunakan perintah ini dengan membalas pesan pengguna yang ingin diperingatkan.")
        return

    user_to_warn = update.message.reply_to_message.from_user
    admin_name = update.effective_user.mention_html()
    
    # Ekstrak alasan jika ada
    reason = " ".join(context.args) if context.args else "Pelanggaran aturan."
    
    # Panggil fungsi terpusat
    await issue_warning(context, update.effective_chat.id, user_to_warn, admin_name, reason)

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (kode fungsi kick_command tetap sama)
    pass

# --- Fungsi Perintah Lainnya (start, help, dll.) ---
# ... (Semua fungsi lain seperti start, help, rules, statistic, dll. tetap ada di sini)
# Pastikan Anda tidak menghapus fungsi-fungsi ini dari file Anda.
