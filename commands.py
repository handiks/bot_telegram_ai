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
    {"author": "Imam Al-Ghazali", "quote": "Kebahagiaan terletak pada kemenangan memerangi hawa nafsu dan menahan kehendak yang berlebih-lebihan."},
    {"author": "Imam Syafi'i", "quote": "Ilmu itu bukan yang dihafal, tetapi yang memberi manfaat."},
    {"author": "Umar bin Khattab", "quote": "Aku tidak pernah mengkhawatirkan apakah doaku akan dikabulkan atau tidak, tapi yang lebih aku khawatirkan adalah aku tidak diberi hidayah untuk terus berdoa."},
    {"author": "Ali bin Abi Thalib", "quote": "Jangan menjelaskan tentang dirimu kepada siapa pun, karena yang menyukaimu tidak butuh itu dan yang membencimu tidak percaya itu."},
    {"author": "Hasan Al-Bashri", "quote": "Dunia ini hanya tiga hari: Kemarin, ia telah pergi bersama dengan semua isinya. Besok, engkau mungkin tak akan pernah menemuinya. Hari ini, itulah yang kau punya, maka beramallah di hari ini."},
    {"author": "Ibnu Qayyim Al-Jauziyyah", "quote": "Jika Allah memberimu nikmat, Dia ingin melihat jejak nikmat-Nya ada padamu."},
    {"author": "Imam Al-Ghazali", "quote": "Cintailah kekasihmu sekadarnya saja, siapa tahu nanti akan jadi musuhmu. Dan bencilah musuhmu sekadarnya saja, siapa tahu nanti akan jadi kekasihmu."},
    {"author": "Ali bin Abi Thalib", "quote": "Kesabaran itu ada dua macam: sabar atas sesuatu yang tidak kau ingin dan sabar menahan diri dari sesuatu yang kau ingini."}
]

# --- Fungsi Helper Moderasi ---

async def is_user_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Memeriksa apakah pengguna yang mengirim perintah adalah admin."""
    if not update.effective_chat or not update.effective_user:
        return False
    if update.effective_chat.type == 'private':
        return True
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
        return member.status in ['creator', 'administrator']
    except BadRequest:
        return False
    except Exception as e:
        logger.error(f"Error saat memeriksa status admin: {e}")
        return False

async def check_admin_and_bot_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Memeriksa apakah pengguna adalah admin dan bot memiliki izin yang diperlukan."""
    if not update.message or not update.effective_chat or not update.effective_user:
        return False
    
    if not await is_user_admin(update, context):
        await update.message.reply_text("Perintah ini hanya untuk admin grup.")
        return False

    bot_member = await context.bot.get_chat_member(update.effective_chat.id, context.bot.id)
    if not bot_member.status == 'administrator' or not bot_member.can_restrict_members:
        await update.message.reply_text("Saya tidak memiliki izin untuk melakukan ini. Jadikan saya admin dengan hak 'Restrict Members'.")
        return False
        
    return True

# --- Fungsi Peringatan Terpusat ---
async def issue_warning(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_to_warn, warned_by: str, reason: str = None):
    """Menangani logika pemberian peringatan, pengiriman pesan, dan pengecekan batas."""
    total_warnings = db_handler.add_user_warning(chat_id, user_to_warn.id)
    warn_limit = db_handler.get_group_setting(chat_id, 'warn_limit', 3)

    warning_message = f"⚠️ Pengguna {user_to_warn.mention_html()} telah diberi peringatan oleh {warned_by}.\n"
    if reason:
        warning_message += f"Alasan: <i>{reason}</i>\n"
    warning_message += f"Total peringatan: <b>{total_warnings}/{warn_limit}</b>."

    await context.bot.send_message(chat_id, warning_message, parse_mode=ParseMode.HTML)

    if total_warnings >= warn_limit:
        try:
            await context.bot.ban_chat_member(chat_id, user_to_warn.id)
            await context.bot.unban_chat_member(chat_id, user_to_warn.id)
            await context.bot.send_message(chat_id, f"🚫 {user_to_warn.mention_html()} telah dikeluarkan karena mencapai batas {warn_limit} peringatan.")
            db_handler.clear_user_warnings(chat_id, user_to_warn.id)
        except Exception as e:
            logger.error(f"Gagal mengeluarkan pengguna {user_to_warn.id}: {e}")
            await context.bot.send_message(chat_id, f"Gagal mengeluarkan {user_to_warn.mention_html()}. Periksa izin saya.")

# --- Fungsi Perintah Dasar ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.from_user: return
    user_name = update.message.from_user.first_name
    welcome_message = (
        f"Assalamu'alaikum, {user_name}!\n\n"
        "Selamat datang di Bot Islami & Manajemen Grup.\n\n"
        "Ketik <code>/help</code> untuk melihat daftar lengkap perintah."
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message: return
    chat_id = update.message.chat_id
    rules_text = db_handler.get_group_setting(chat_id, 'rules_text', db_handler.get_default_rules())
    await update.message.reply_text(rules_text, parse_mode=ParseMode.HTML)

async def statistic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def mutiarakata_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message: return
    quote_data = random.choice(ISLAMIC_QUOTES)
    message_text = (
        f"✨ <b>Mutiara Kata</b> ✨\n\n"
        f"<i>\"{quote_data['quote']}\"</i>\n\n"
        f"<b>— {quote_data['author']}</b>"
    )
    await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)

async def tanya_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message: return
    if not gemini_model:
        await update.message.reply_text("Maaf, fitur AI saat ini tidak tersedia.")
        return
    if not context.args:
        await update.message.reply_text("Gunakan format: <b><code>/tanya [pertanyaan Anda]</code></b>")
        return
    question = " ".join(context.args)
    processing_message = await update.message.reply_text("🤔 Sedang memproses pertanyaan Anda...")
    prompt = f"""
        Anda adalah seorang asisten AI cendekiawan Muslim.
        Tugas Anda adalah menjawab pertanyaan berikut dengan sopan, jelas, dan terstruktur.
        Prioritaskan jawaban berdasarkan Al-Qur'an dan Hadits shahih.
        Pertanyaan: "{question}"
    """
    try:
        response = await gemini_model.generate_content_async(prompt)
        await update.message.reply_text(response.text.strip())
    except Exception as e:
        logger.error(f"Error saat menggunakan fitur /tanya: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat berkomunikasi dengan AI.")
    finally:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)

async def kisah_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message: return
    if not gemini_model:
        await update.message.reply_text("Maaf, fitur AI saat ini tidak tersedia.")
        return
    if not context.args:
        await update.message.reply_text("Gunakan format: <b><code>/kisah [nama tokoh]</code></b>")
        return
    tokoh = " ".join(context.args)
    processing_message = await update.message.reply_text(f"📜 Sedang membuka lembaran kisah {tokoh.title()}...")
    prompt = f"""
        Anda adalah seorang pencerita (hakawati) yang ahli dalam sejarah Islam.
        Ceritakan kisah dari tokoh berikut: "{tokoh}".
        Gunakan gaya bahasa yang menarik dan mudah dipahami.
        Fokus pada hikmah yang bisa diambil dari kisah tersebut.
    """
    try:
        response = await gemini_model.generate_content_async(prompt)
        await update.message.reply_text(response.text.strip())
    except Exception as e:
        logger.error(f"Error saat menggunakan fitur /kisah: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat berkomunikasi dengan AI.")
    finally:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)

async def hadith_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or len(context.args) != 2:
        await update.message.reply_text("Format salah. Gunakan: <b><code>/hadits [riwayat] [nomor]</code></b>")
        return
    riwayat, nomor_str = context.args[0].lower(), context.args[1]
    if not nomor_str.isdigit():
        await update.message.reply_text("Nomor hadits harus berupa angka.")
        return
    nomor = int(nomor_str)
    processing_message = await update.message.reply_text(f"🔍 Sedang mencari Hadits {riwayat.capitalize()} No. {nomor}...")
    try:
        url = f"https://api.hadith.gading.dev/books/{riwayat}/{nomor}"
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        data = response.json()['data']
        hadith = data['contents']
        message = (
            f"📜 <b>Hadits {data['name']} No. {hadith['number']}</b>\n\n"
            f"<b dir='rtl'>{hadith['arab']}</b>\n\n"
            f"<i>Artinya: \"{hadith['id']}\"</i>"
        )
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            await update.message.reply_text(f"Maaf, Hadits {riwayat.capitalize()} nomor {nomor} tidak ditemukan.")
        else:
            await update.message.reply_text("Maaf, terjadi kesalahan pada server Hadits.")
    except requests.exceptions.RequestException as e:
        await update.message.reply_text("Maaf, terjadi kesalahan koneksi saat mencari hadits.")
    finally:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)

def _parse_reminder_time(time_str: str) -> int:
    try:
        value = int(time_str[:-1])
        unit = time_str[-1].lower()
        if unit == 's': return value
        if unit == 'm': return value * 60
        if unit == 'h': return value * 3600
        if unit == 'd': return value * 86400
        return 0
    except (ValueError, IndexError):
        return 0

async def _reminder_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    if not job or not job.chat_id or not job.data: return
    await context.bot.send_message(chat_id=job.chat_id, text=f"⏰ <b>Pengingat:</b>\n\n<i>{job.data}</i>")

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or len(context.args) < 2:
        await update.message.reply_text("Format salah. Gunakan: <b><code>/ingatkan [waktu] [pesan]</code></b>")
        return
    if not context.job_queue:
        await update.message.reply_text("Maaf, fitur pengingat tidak tersedia.")
        return
    delay = _parse_reminder_time(context.args[0])
    if delay <= 0:
        await update.message.reply_text("Format waktu tidak valid.")
        return
    reminder_text = " ".join(context.args[1:])
    context.job_queue.run_once(_reminder_callback, delay, chat_id=update.message.chat.id, data=reminder_text)
    await update.message.reply_text(f"✅ Pengingat untuk '<i>{reminder_text}</i>' telah diatur.")

async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.new_chat_members: return
    chat_id = update.message.chat_id
    if not db_handler.get_group_setting(chat_id, 'welcome_enabled', True): return
    welcome_template = db_handler.get_group_setting(chat_id, 'welcome_message', db_handler.get_default_welcome_message())
    for member in update.message.new_chat_members:
        if member.is_bot: continue
        message_to_send = welcome_template.format(user_mention=member.mention_html(), chat_title=update.message.chat.title)
        await update.message.reply_text(message_to_send)

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_and_bot_permissions(update, context): return
    if not update.message.reply_to_message:
        await update.message.reply_text("Balas pesan pengguna yang ingin diperingatkan.")
        return
    user_to_warn = update.message.reply_to_message.from_user
    admin_name = update.effective_user.mention_html()
    reason = " ".join(context.args) if context.args else "Pelanggaran aturan."
    await issue_warning(context, update.effective_chat.id, user_to_warn, admin_name, reason)

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not await check_admin_and_bot_permissions(update, context): return
    if not update.message.reply_to_message:
        await update.message.reply_text("Balas pesan pengguna yang ingin dikeluarkan.")
        return
    user_to_kick = update.message.reply_to_message.from_user
    admin_name = update.effective_user.mention_html()
    chat_id = update.effective_chat.id
    try:
        await context.bot.ban_chat_member(chat_id, user_to_kick.id)
        await context.bot.unban_chat_member(chat_id, user_to_kick.id)
        await update.effective_chat.send_message(f"🚫 {user_to_kick.mention_html()} dikeluarkan oleh {admin_name}.")
        db_handler.clear_user_warnings(chat_id, user_to_kick.id)
    except Exception as e:
        await update.effective_chat.send_message(f"Gagal mengeluarkan {user_to_kick.mention_html()}.")

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not await is_user_admin(update, context):
        await update.message.reply_text("Perintah ini hanya untuk admin.")
        return ConversationHandler.END
    chat_id = update.effective_chat.id
    welcome_status = "✅ Aktif" if db_handler.get_group_setting(chat_id, 'welcome_enabled', True) else "❌ Nonaktif"
    moderation_status = "✅ Aktif" if db_handler.get_group_setting(chat_id, 'ai_moderation_enabled', True) else "❌ Nonaktif"
    keyboard = [
        [InlineKeyboardButton("Ubah Pesan Selamat Datang", callback_data='set_welcome_msg')],
        [InlineKeyboardButton("Ubah Peraturan Grup", callback_data='set_rules')],
        [InlineKeyboardButton(f"Sapaan Anggota: {welcome_status}", callback_data='toggle_welcome')],
        [InlineKeyboardButton(f"Moderasi AI: {moderation_status}", callback_data='toggle_moderation')],
        [InlineKeyboardButton("Tutup", callback_data='close_settings')],
    ]
    await update.message.reply_text("⚙️ *Pengaturan Bot*", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return SELECTING_ACTION

async def settings_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if not await is_user_admin(update, context):
        await query.edit_message_text("Anda bukan admin.")
        return ConversationHandler.END
    action = query.data
    chat_id = update.effective_chat.id
    if action == 'set_welcome_msg':
        await query.edit_message_text("Kirim pesan selamat datang baru. Gunakan {user_mention} dan {chat_title}. Ketik /batal untuk batal.")
        return AWAITING_WELCOME_MESSAGE
    elif action == 'set_rules':
        await query.edit_message_text("Kirim peraturan baru. Gunakan format HTML. Ketik /batal untuk batal.")
        return AWAITING_RULES
    elif action == 'toggle_welcome' or action == 'toggle_moderation':
        key = 'welcome_enabled' if action == 'toggle_welcome' else 'ai_moderation_enabled'
        current_status = db_handler.get_group_setting(chat_id, key, True)
        db_handler.set_group_setting(chat_id, key, not current_status)
        await settings_command(update.callback_query, context) # Refresh menu
        return SELECTING_ACTION
    elif action == 'close_settings':
        await query.edit_message_text("Menu pengaturan ditutup.")
        return ConversationHandler.END
    return SELECTING_ACTION

async def save_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text: return AWAITING_WELCOME_MESSAGE
    db_handler.set_group_setting(update.effective_chat.id, 'welcome_message', update.message.text_html)
    await update.message.reply_text("✅ Pesan selamat datang diperbarui.")
    await settings_command(update, context)
    return ConversationHandler.END

async def save_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text: return AWAITING_RULES
    db_handler.set_group_setting(update.effective_chat.id, 'rules_text', update.message.text_html)
    await update.message.reply_text("✅ Peraturan diperbarui.")
    await settings_command(update, context)
    return ConversationHandler.END

async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Aksi dibatalkan.")
    return ConversationHandler.END
