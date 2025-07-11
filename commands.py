# -*- coding: utf-8 -*-

"""
Modul ini berisi semua fungsi dasar yang dipanggil oleh pengguna melalui perintah.
Termasuk fitur moderasi /warn dan /kick.
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

# --- Fungsi Helper Moderasi ---

async def check_admin_and_bot_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Memeriksa apakah pengguna adalah admin dan bot memiliki izin yang diperlukan."""
    if not update.message or not update.effective_chat or not update.effective_user:
        return False
    
    # 1. Periksa apakah pengguna adalah admin
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    if member.status not in ['creator', 'administrator']:
        await update.message.reply_text("Perintah ini hanya untuk admin grup.")
        return False

    # 2. Periksa apakah bot adalah admin dan bisa membatasi anggota
    bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
    if not bot_member.status == 'administrator' or not bot_member.can_restrict_members:
        await update.message.reply_text("Saya tidak memiliki izin untuk melakukan ini. Jadikan saya admin dengan hak 'Restrict Members'.")
        return False
        
    return True

# --- Fungsi Perintah Moderasi ---

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Memberikan peringatan kepada pengguna."""
    if not await check_admin_and_bot_permissions(update, context):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Gunakan perintah ini dengan membalas pesan pengguna yang ingin diperingatkan.")
        return

    user_to_warn = update.message.reply_to_message.from_user
    admin_name = update.effective_user.mention_html()
    chat_id = update.effective_chat.id
    
    # Tambahkan peringatan dan dapatkan jumlah totalnya
    total_warnings = db_handler.add_user_warning(chat_id, user_to_warn.id)
    
    # Ambil batas peringatan dari pengaturan (default: 3)
    warn_limit = db_handler.get_group_setting(chat_id, 'warn_limit', 3)

    await update.message.reply_to_message.reply_text(
        f"⚠️ Pengguna {user_to_warn.mention_html()} telah diberi peringatan oleh {admin_name}.\n"
        f"Total peringatan: <b>{total_warnings}/{warn_limit}</b>."
    )

    if total_warnings >= warn_limit:
        try:
            await context.bot.ban_chat_member(chat_id, user_to_warn.id)
            await update.effective_chat.send_message(
                f"🚫 {user_to_warn.mention_html()} telah dikeluarkan dari grup karena mencapai batas {warn_limit} peringatan."
            )
            # Hapus catatan peringatan setelah dikeluarkan
            db_handler.clear_user_warnings(chat_id, user_to_warn.id)
        except Exception as e:
            logger.error(f"Gagal mengeluarkan pengguna {user_to_warn.id}: {e}")
            await update.effective_chat.send_message(f"Gagal mengeluarkan {user_to_warn.mention_html()}. Periksa izin saya.")

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengeluarkan pengguna dari grup."""
    if not await check_admin_and_bot_permissions(update, context):
        return

    if not update.message.reply_to_message:
        await update.message.reply_text("Gunakan perintah ini dengan membalas pesan pengguna yang ingin dikeluarkan.")
        return

    user_to_kick = update.message.reply_to_message.from_user
    admin_name = update.effective_user.mention_html()
    chat_id = update.effective_chat.id
    
    try:
        await context.bot.ban_chat_member(chat_id, user_to_kick.id)
        await update.effective_chat.send_message(
            f"🚫 {user_to_kick.mention_html()} telah dikeluarkan dari grup oleh {admin_name}."
        )
        # Hapus catatan peringatan setelah dikeluarkan
        db_handler.clear_user_warnings(chat_id, user_to_kick.id)
    except Exception as e:
        logger.error(f"Gagal mengeluarkan pengguna {user_to_kick.id}: {e}")
        await update.effective_chat.send_message(f"Gagal mengeluarkan {user_to_kick.mention_html()}. Periksa izin saya.")

# --- Fungsi Perintah Lainnya (start, help, dll.) ---

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan daftar semua perintah yang tersedia."""
    if not update.message: return
    help_text = (
        "📖 <b>Daftar Perintah Bot</b>\n\n"
        "<b><code>/start</code></b> - Memulai bot\n"
        "<b><code>/help</code></b> - Menampilkan pesan bantuan ini\n"
        "<b><code>/rules</code></b> - Menampilkan peraturan grup\n"
        "<b><code>/settings</code></b> - (Admin) Mengatur bot untuk grup ini\n"
        "<b><code>/statistic</code></b> - Menampilkan statistik grup\n\n"
        "<b>Moderasi (Hanya Admin):</b>\n"
        "<b><code>/warn</code></b> - Beri peringatan (balas pesan)\n"
        "<b><code>/kick</code></b> - Keluarkan anggota (balas pesan)\n\n"
        "<b>Fitur Islami & Lainnya:</b>\n"
        "<b><code>/doa</code></b> - Menampilkan doa harian acak\n"
        "<b><code>/mutiarakata</code></b> - Mutiara kata dari para ulama\n"
        "<b><code>/tanya [pertanyaan]</code></b> - Tanya jawab Islami\n"
        "<b><code>/kisah [nama]</code></b> - Kisah Nabi/Sahabat\n"
        "<b><code>/ayat [surah]:[ayat]</code></b> - Mengirim ayat Al-Qur'an\n"
        "<b><code>/tafsir [surah]:[ayat]</code></b> - Menampilkan tafsir ayat\n"
        "<b><code>/hadits [riwayat] [nomor]</code></b> - Mencari hadits\n"
        "<b><code>/ingatkan [waktu] [pesan]</code></b> - Mengatur pengingat"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

# ... (Sisa kode untuk start, rules, statistic, doa, mutiarakata, dll. tetap sama)
# Pastikan semua fungsi lainnya tetap ada di sini.
