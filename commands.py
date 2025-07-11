# -*- coding: utf-8 -*-

"""
Modul ini berisi semua fungsi dasar yang dipanggil oleh pengguna melalui perintah.
Termasuk fitur Asmaul Husna yang baru.
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

# State untuk ConversationHandler (untuk fitur /settings)
(SELECTING_ACTION, AWAITING_WELCOME_MESSAGE, AWAITING_RULES) = range(3)

# --- Fungsi Perintah Dasar ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan sambutan saat pengguna memulai interaksi dengan bot."""
    if not update.message or not update.message.from_user:
        return
    user_name = update.message.from_user.first_name
    welcome_message = (
        f"Assalamu'alaikum, {user_name}!\n\n"
        "Selamat datang di Bot Islami & Manajemen Grup.\n\n"
        "Ketik <code>/help</code> untuk melihat daftar lengkap perintah."
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan daftar semua perintah yang tersedia."""
    if not update.message: return
    help_text = (
        "📖 <b>Daftar Perintah Bot</b>\n\n"
        "<b><code>/start</code></b> - Memulai bot\n"
        "<b><code>/help</code></b> - Menampilkan pesan bantuan ini\n"
        "<b><code>/rules</code></b> - Menampilkan peraturan grup\n"
        "<b><code>/settings</code></b> - (Admin) Mengatur bot untuk grup ini\n"
        "<b><code>/statistic</code></b> - Menampilkan statistik grup\n"
        "<b><code>/doa</code></b> - Menampilkan doa harian acak\n"
        "<b><code>/asmaulhusna</code></b> - Menampilkan Asmaul Husna acak\n\n"
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

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan peraturan grup yang telah ditetapkan dari database."""
    if not update.message: return
    chat_id = update.message.chat_id
    rules_text = db_handler.get_group_setting(chat_id, 'rules_text', db_handler.get_default_rules())
    await update.message.reply_text(rules_text, parse_mode=ParseMode.HTML)

async def statistic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan statistik dasar untuk grup."""
    if not update.message or update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Perintah ini hanya dapat digunakan di dalam grup.")
        return
    try:
        chat_id = update.message.chat.id
        chat_title = update.message.chat.title
        member_count = await context.bot.get_chat_member_count(chat_id)
        stats_text = (
            f"📊 <b>Statistik Grup: {chat_title}</b>\n\n"
            f"👤 <b>Jumlah Anggota:</b> {member_count}"
        )
        await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Error saat mengambil statistik grup: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mengambil data statistik.")

async def doa_harian_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengambil dan mengirim doa harian acak."""
    if not update.message: return
    processing_message = await update.message.reply_text("🤲 Sedang mencari doa harian...")
    try:
        url = "https://doa-doa-api-ahmadramadhan.fly.dev/api"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        doa_list = response.json()
        if not isinstance(doa_list, list) or not doa_list:
            raise ValueError("API mengembalikan data kosong atau format salah.")
        doa = random.choice(doa_list)
        doa_text = (
            f"🤲 <b>{doa['doa']}</b>\n\n"
            f"<b dir='rtl'>{doa['ayat']}</b>\n\n"
            f"<i>{doa['latin']}</i>\n\n"
            f"<b>Artinya:</b>\n"
            f"\"{doa['artinya']}\""
        )
        await update.message.reply_text(doa_text, parse_mode=ParseMode.HTML)
    except (requests.exceptions.RequestException, ValueError) as e:
        logger.error(f"Error saat menghubungi API Doa Harian: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mencari doa harian. Coba lagi nanti.")
    finally:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)

# --- FITUR BARU: Asmaul Husna ---
async def asmaulhusna_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengambil dan mengirim salah satu Asmaul Husna secara acak."""
    if not update.message: return

    processing_message = await update.message.reply_text("📖 Sedang mencari nama terindah...")
    try:
        url = "https://islamic-api-indonesia.vercel.app/api/data/asmaulhusna"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()
        if not data or 'result' not in data or not isinstance(data['result'], list):
            raise ValueError("API mengembalikan format data yang tidak valid.")
        asmaul_husna_list = data['result']
        if not asmaul_husna_list:
            raise ValueError("API mengembalikan daftar kosong.")
        
        nama = random.choice(asmaul_husna_list)
        message_text = (
            f"✨ <b>Asmaul Husna</b> ✨\n\n"
            f"<b>{nama.get('urutan', '')}. {nama.get('latin', 'N/A')}</b> (<i>{nama.get('arab', '')}</i>)\n\n"
            f"<b>Artinya:</b>\n"
            f"{nama.get('arti', 'Tidak ada arti.')}"
        )
        await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)
    except (requests.exceptions.RequestException, ValueError) as e:
        logger.error(f"Error saat menghubungi API Asmaul Husna: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mencari Asmaul Husna. Coba lagi nanti.")
    finally:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)

async def tanya_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (kode fungsi tanya_ai_command tetap sama)
    pass

async def kisah_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (kode fungsi kisah_command tetap sama)
    pass

async def hadith_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (kode fungsi hadith_command tetap sama)
    pass

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (kode fungsi set_reminder dan helpernya tetap sama)
    pass

async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (kode fungsi greet_new_member tetap sama)
    pass

# --- FITUR PENGATURAN GRUP (/settings) ---
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (kode fungsi settings_command dan semua helpernya tetap sama)
    pass

async def settings_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (kode fungsi settings_button_callback tetap sama)
    pass

async def save_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (kode fungsi save_welcome_message tetap sama)
    pass

async def save_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (kode fungsi save_rules tetap sama)
    pass

async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ... (kode fungsi cancel_settings tetap sama)
    pass
