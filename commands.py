# -*- coding: utf-8 -*-

"""
Modul ini berisi semua fungsi dasar yang dipanggil oleh pengguna melalui perintah.
Termasuk fitur pengaturan grup yang baru.
"""

import logging
import requests 
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from telegram.error import BadRequest

# Mengimpor model AI dan handler database
from ai_features import gemini_model
import db_handler

# Inisialisasi logger
logger = logging.getLogger(__name__)

# State untuk ConversationHandler
(SELECTING_ACTION, AWAITING_WELCOME_MESSAGE, AWAITING_RULES) = range(3)

# --- Fungsi Perintah Dasar (Tidak Berubah) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (kode fungsi start tetap sama)
    user_name = update.message.from_user.first_name
    welcome_message = (
        f"Assalamu'alaikum, {user_name}!\n\n"
        "Selamat datang di Bot Islami & Manajemen Grup.\n\n"
        "Ketik <code>/help</code> untuk melihat daftar lengkap perintah."
    )
    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (kode fungsi help_command tetap sama)
    help_text = (
        "📖 <b>Daftar Perintah Bot</b>\n\n"
        "<b><code>/start</code></b> - Memulai bot\n"
        "<b><code>/help</code></b> - Menampilkan pesan bantuan ini\n"
        "<b><code>/rules</code></b> - Menampilkan peraturan grup\n"
        "<b><code>/statistic</code></b> - Menampilkan statistik grup\n"
        "<b><code>/doa</code></b> - Menampilkan doa harian acak\n"
        "<b><code>/settings</code></b> - (Admin) Mengatur bot untuk grup ini\n\n"
        "<b>Fitur Islami & AI:</b>\n"
        "<b><code>/tanya [pertanyaan]</code></b> - Tanya jawab Islami\n"
        "<b><code>/kisah [nama]</code></b> - Kisah Nabi/Sahabat\n"
        "<b><code>/ayat [surah]:[ayat]</code></b> - Mengirim ayat Al-Qur'an\n"
        "<b><code>/tafsir [surah]:[ayat]</code></b> - Menampilkan tafsir ayat\n"
        "<b><code>/hadits [riwayat] [nomor]</code></b> - Mencari hadits\n\n"
        "<b>Utilitas:</b>\n"
        "<b><code>/ingatkan [waktu] [pesan]</code></b> - Mengatur pengingat"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)


# --- REVISI: Fungsi /rules sekarang mengambil data dari database ---
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan peraturan grup yang telah ditetapkan dari database."""
    if not update.message: return
    
    chat_id = update.message.chat_id
    # Ambil peraturan dari DB, jika tidak ada, gunakan default.
    rules_text = db_handler.get_group_setting(chat_id, 'rules_text', db_handler.get_default_rules())
    
    await update.message.reply_text(rules_text, parse_mode=ParseMode.HTML)

# --- REVISI: Fungsi sapaan anggota baru sekarang mengambil data dari database ---
async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menyapa setiap anggota baru yang bergabung ke grup."""
    if not update.message or not update.message.new_chat_members:
        return

    chat_id = update.message.chat_id
    
    # Periksa apakah fitur sapaan aktif untuk grup ini (default: True)
    if not db_handler.get_group_setting(chat_id, 'welcome_enabled', True):
        return

    # Ambil pesan selamat datang kustom dari DB, jika tidak ada, gunakan default.
    welcome_template = db_handler.get_group_setting(chat_id, 'welcome_message', db_handler.get_default_welcome_message())

    for member in update.message.new_chat_members:
        if member.is_bot: continue
        
        # Ganti placeholder dengan data pengguna
        message_to_send = welcome_template.format(
            user_mention=member.mention_html(),
            chat_title=update.message.chat.title
        )
        await update.message.reply_text(message_to_send, parse_mode=ParseMode.HTML)

# --- Fungsi Lainnya (statistic, doa, tanya, dll. tetap sama) ---
# ... (letakkan kode fungsi statistic, doa_harian_command, tanya_ai_command, dll. di sini)
# Pastikan semua fungsi lain yang tidak berubah tetap ada di file ini.

# --- FITUR BARU: Pengaturan Grup (/settings) ---

async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Memeriksa apakah pengguna yang mengirim perintah adalah admin."""
    if not update.effective_chat or not update.effective_user:
        return False
    if update.effective_chat.type == 'private':
        return True # Anggap admin di chat pribadi
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in ['creator', 'administrator']
    except BadRequest:
        return False # Jika bot bukan anggota grup
    except Exception as e:
        logger.error(f"Error saat memeriksa status admin: {e}")
        return False

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Memulai alur percakapan untuk pengaturan grup."""
    if not update.message or not await is_user_admin(update, context):
        await update.message.reply_text("Perintah ini hanya untuk admin grup.")
        return ConversationHandler.END

    chat_id = update.effective_chat.id
    
    # Ambil status pengaturan saat ini
    welcome_status = "✅ Aktif" if db_handler.get_group_setting(chat_id, 'welcome_enabled', True) else "❌ Nonaktif"
    moderation_status = "✅ Aktif" if db_handler.get_group_setting(chat_id, 'ai_moderation_enabled', True) else "❌ Nonaktif"

    keyboard = [
        [InlineKeyboardButton("Ubah Pesan Selamat Datang", callback_data='set_welcome_msg')],
        [InlineKeyboardButton("Ubah Peraturan Grup", callback_data='set_rules')],
        [InlineKeyboardButton(f"Sapaan Anggota Baru: {welcome_status}", callback_data='toggle_welcome')],
        [InlineKeyboardButton(f"Moderasi AI: {moderation_status}", callback_data='toggle_moderation')],
        [InlineKeyboardButton("Tutup Menu", callback_data='close_settings')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("⚙️ *Pengaturan Bot untuk Grup Ini*\n\nPilih salah satu opsi:", reply_markup=reply_markup, parse_mode="Markdown")
    return SELECTING_ACTION

async def settings_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menangani semua tombol yang ditekan dari menu /settings."""
    query = update.callback_query
    await query.answer()
    
    if not await is_user_admin(update, context):
        await query.edit_message_text("Maaf, Anda tidak memiliki izin untuk melakukan ini.")
        return ConversationHandler.END

    action = query.data
    chat_id = update.effective_chat.id

    if action == 'set_welcome_msg':
        await query.edit_message_text("Silakan kirim pesan selamat datang yang baru.\n\nGunakan placeholder `{user_mention}` untuk menyebut nama anggota baru dan `{chat_title}` untuk nama grup.\n\nKetik /batal untuk membatalkan.")
        return AWAITING_WELCOME_MESSAGE
    
    elif action == 'set_rules':
        await query.edit_message_text("Silakan kirim teks peraturan grup yang baru.\n\nAnda bisa menggunakan format HTML dasar (<b>tebal</b>, <i>miring</i>).\n\nKetik /batal untuk membatalkan.")
        return AWAITING_RULES

    elif action == 'toggle_welcome':
        current_status = db_handler.get_group_setting(chat_id, 'welcome_enabled', True)
        db_handler.set_group_setting(chat_id, 'welcome_enabled', not current_status)
        await query.edit_message_text("Pengaturan sapaan anggota baru telah diperbarui.")
        return ConversationHandler.END

    elif action == 'toggle_moderation':
        current_status = db_handler.get_group_setting(chat_id, 'ai_moderation_enabled', True)
        db_handler.set_group_setting(chat_id, 'ai_moderation_enabled', not current_status)
        await query.edit_message_text("Pengaturan moderasi AI telah diperbarui.")
        return ConversationHandler.END

    elif action == 'close_settings':
        await query.edit_message_text("Menu pengaturan ditutup.")
        return ConversationHandler.END
    
    return SELECTING_ACTION

async def save_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan pesan selamat datang yang baru dari pengguna."""
    if not update.message or not update.message.text:
        return AWAITING_WELCOME_MESSAGE
        
    db_handler.set_group_setting(update.effective_chat.id, 'welcome_message', update.message.text_html)
    await update.message.reply_text("✅ Pesan selamat datang berhasil diperbarui.")
    return ConversationHandler.END

async def save_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan peraturan baru dari pengguna."""
    if not update.message or not update.message.text:
        return AWAITING_RULES
        
    db_handler.set_group_setting(update.effective_chat.id, 'rules_text', update.message.text_html)
    await update.message.reply_text("✅ Peraturan grup berhasil diperbarui.")
    return ConversationHandler.END

async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Membatalkan alur percakapan pengaturan."""
    await update.message.reply_text("Aksi dibatalkan. Menu pengaturan ditutup.")
    return ConversationHandler.END

# --- REVISI: ai_features.py perlu diubah sedikit ---
# Anda harus menambahkan pemeriksaan ini di awal fungsi `moderate_chat` di file `ai_features.py`
# import db_handler
# if not db_handler.get_group_setting(update.message.chat.id, 'ai_moderation_enabled', True):
#     return
