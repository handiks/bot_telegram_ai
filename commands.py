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

# --- REVISI: Menggunakan API baru yang lebih stabil untuk Asmaul Husna ---
async def asmaulhusna_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengambil dan mengirim salah satu Asmaul Husna secara acak."""
    if not update.message: return

    processing_message = await update.message.reply_text("📖 Sedang mencari nama terindah...")
    try:
        # API baru dari file JSON mentah di GitHub, sangat stabil.
        url = "https://raw.githubusercontent.com/Penggguna/QuranJSON/main/asmaul-husna.json"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        asmaul_husna_list = response.json()
        
        # Validasi data dari API baru
        if not isinstance(asmaul_husna_list, list) or not asmaul_husna_list:
            raise ValueError("API mengembalikan format data yang tidak valid atau daftar kosong.")
        
        nama = random.choice(asmaul_husna_list)
        message_text = (
            f"✨ <b>Asmaul Husna</b> ✨\n\n"
            # Menyesuaikan dengan kunci JSON yang baru: 'latin' dan 'arti_id'
            f"<b>{nama.get('urutan', '')}. {nama.get('latin', 'N/A')}</b> (<i>{nama.get('arab', '')}</i>)\n\n"
            f"<b>Artinya:</b>\n"
            f"{nama.get('arti_id', 'Tidak ada arti.')}"
        )
        await update.message.reply_text(message_text, parse_mode=ParseMode.HTML)
    except (requests.exceptions.RequestException, ValueError, json.JSONDecodeError) as e:
        logger.error(f"Error saat menghubungi API Asmaul Husna: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mencari Asmaul Husna. Coba lagi nanti.")
    finally:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)

async def tanya_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message: return
    if not gemini_model:
        await update.message.reply_text("Maaf, fitur AI saat ini tidak tersedia.")
        return
    if not context.args:
        await update.message.reply_text(
            "Gunakan format: <b><code>/tanya [pertanyaan Anda]</code></b>\n"
            "Contoh: <code>/tanya Apa itu istidraj?</code>"
        )
        return
    question = " ".join(context.args)
    processing_message = await update.message.reply_text("🤔 Sedang memproses pertanyaan Anda...")
    prompt = f"""
        Anda adalah seorang asisten AI cendekiawan Muslim.
        Tugas Anda adalah menjawab pertanyaan berikut dengan sopan, jelas, dan terstruktur.
        Prioritaskan jawaban berdasarkan Al-Qur'an dan Hadits shahih, sebutkan sumbernya jika memungkinkan (contoh: QS. Al-Baqarah: 255).
        Jika pertanyaan bersifat opini atau khilafiyah (perbedaan pendapat), jelaskan perspektif yang ada secara netral.
        Jika pertanyaan di luar konteks keislaman, tolak dengan sopan.
        Pertanyaan: "{question}"
    """
    try:
        response = await gemini_model.generate_content_async(prompt)
        await update.message.reply_text(response.text.strip())
    except Exception as e:
        logger.error(f"Error saat menggunakan fitur /tanya: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat berkomunikasi dengan AI. Coba lagi nanti.")
    finally:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)

async def kisah_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message: return
    if not gemini_model:
        await update.message.reply_text("Maaf, fitur AI saat ini tidak tersedia.")
        return
    if not context.args:
        await update.message.reply_text(
            "Gunakan format: <b><code>/kisah [nama tokoh]</code></b>\n"
            "Contoh: <code>/kisah Nabi Ibrahim AS</code>"
        )
        return
    tokoh = " ".join(context.args)
    processing_message = await update.message.reply_text(f"📜 Sedang membuka lembaran kisah {tokoh.title()}...")
    prompt = f"""
        Anda adalah seorang pencerita (hakawati) yang ahli dalam sejarah Islam.
        Ceritakan kisah dari tokoh berikut: "{tokoh}".
        Gunakan gaya bahasa yang menarik dan mudah dipahami.
        Struktur cerita Anda harus mencakup:
        1. Pengenalan singkat tokoh.
        2. Peristiwa penting dalam hidupnya.
        3. Penutup yang berisi hikmah atau pelajaran yang bisa diambil dari kisah tersebut.
    """
    try:
        response = await gemini_model.generate_content_async(prompt)
        await update.message.reply_text(response.text.strip())
    except Exception as e:
        logger.error(f"Error saat menggunakan fitur /kisah: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat berkomunikasi dengan AI. Coba lagi nanti.")
    finally:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)

async def hadith_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not context.args or len(context.args) != 2:
        await update.message.reply_text(
            "Format salah. Gunakan: <b><code>/hadits [riwayat] [nomor]</code></b>\n"
            "Contoh: <code>/hadits muslim 100</code>\n\n"
            "Riwayat tersedia: <code>bukhari</code>, <code>muslim</code>, <code>tirmidzi</code>, <code>nasai</code>, <code>dawud</code>, <code>majah</code>, <code>ahmad</code>."
        )
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
            logger.error(f"API Hadits mengembalikan status {e.response.status_code}")
            await update.message.reply_text("Maaf, terjadi kesalahan pada server Hadits.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error saat menghubungi API Hadits: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan koneksi saat mencari hadits.")
    finally:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)

def _parse_reminder_time(time_str: str) -> int:
    """Mengubah string waktu (e.g., 5m, 1h, 2d) menjadi detik. Returns 0 jika tidak valid."""
    try:
        time_str = time_str.lower()
        value = int(time_str[:-1])
        unit = time_str[-1]
        
        if unit == 's': return value
        if unit == 'm': return value * 60
        if unit == 'h': return value * 3600
        if unit == 'd': return value * 86400
        
        return 0
    except (ValueError, IndexError):
        return 0

async def _reminder_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fungsi yang dijalankan oleh job queue saat waktu pengingat tiba."""
    job = context.job
    if not job or not job.chat_id or not job.data: return
    await context.bot.send_message(
        chat_id=job.chat_id, 
        text=f"⏰ <b>Pengingat:</b>\n\n<i>{job.data}</i>", 
        parse_mode=ParseMode.HTML
    )

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengatur pengingat untuk pengguna."""
    if not update.message or not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Format salah. Gunakan: <b><code>/ingatkan [waktu] [pesan]</code></b>\n"
            "Contoh: <code>/ingatkan 30m Baca Al-Kahfi</code>\n"
            "Waktu: <code>s</code> (detik), <code>m</code> (menit), <code>h</code> (jam), <code>d</code> (hari)"
        )
        return

    if not context.job_queue:
        await update.message.reply_text("Maaf, fitur pengingat saat ini tidak dapat diaktifkan.")
        return

    time_str, reminder_text = context.args[0], " ".join(context.args[1:])
    delay = _parse_reminder_time(time_str)

    if not (0 < delay <= 2592000): # 30 hari
        await update.message.reply_text(
            "Format atau durasi waktu tidak valid. Gunakan angka diikuti <code>s</code>, <code>m</code>, <code>h</code>, atau <code>d</code>.\n"
            "Durasi maksimal adalah 30 hari."
        )
        return

    context.job_queue.run_once(_reminder_callback, delay, chat_id=update.message.chat.id, data=reminder_text)
    await update.message.reply_text(f"✅ Baik, pengingat untuk '<i>{reminder_text}</i>' telah diatur dalam {time_str}.")


async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menyapa setiap anggota baru yang bergabung ke grup."""
    if not update.message or not update.message.new_chat_members:
        return

    chat_id = update.message.chat_id
    
    if not db_handler.get_group_setting(chat_id, 'welcome_enabled', True):
        return

    welcome_template = db_handler.get_group_setting(chat_id, 'welcome_message', db_handler.get_default_welcome_message())

    for member in update.message.new_chat_members:
        if member.is_bot: continue
        
        message_to_send = welcome_template.format(
            user_mention=member.mention_html(),
            chat_title=update.message.chat.title
        )
        await update.message.reply_text(message_to_send, parse_mode=ParseMode.HTML)

# --- FITUR PENGATURAN GRUP (/settings) ---

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

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Memulai alur percakapan untuk pengaturan grup."""
    if not update.message or not await is_user_admin(update, context):
        await update.message.reply_text("Perintah ini hanya untuk admin grup.")
        return ConversationHandler.END

    chat_id = update.effective_chat.id
    
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
        # Perbarui keyboard untuk menampilkan status baru
        welcome_status = "✅ Aktif" if not current_status else "❌ Nonaktif"
        moderation_status = "✅ Aktif" if db_handler.get_group_setting(chat_id, 'ai_moderation_enabled', True) else "❌ Nonaktif"
        keyboard = [
            [InlineKeyboardButton("Ubah Pesan Selamat Datang", callback_data='set_welcome_msg')],
            [InlineKeyboardButton("Ubah Peraturan Grup", callback_data='set_rules')],
            [InlineKeyboardButton(f"Sapaan Anggota Baru: {welcome_status}", callback_data='toggle_welcome')],
            [InlineKeyboardButton(f"Moderasi AI: {moderation_status}", callback_data='toggle_moderation')],
            [InlineKeyboardButton("Tutup Menu", callback_data='close_settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Pengaturan sapaan anggota baru telah diperbarui.", reply_markup=reply_markup)
        return SELECTING_ACTION


    elif action == 'toggle_moderation':
        current_status = db_handler.get_group_setting(chat_id, 'ai_moderation_enabled', True)
        db_handler.set_group_setting(chat_id, 'ai_moderation_enabled', not current_status)
        # Perbarui keyboard untuk menampilkan status baru
        welcome_status = "✅ Aktif" if db_handler.get_group_setting(chat_id, 'welcome_enabled', True) else "❌ Nonaktif"
        moderation_status = "✅ Aktif" if not current_status else "❌ Nonaktif"
        keyboard = [
            [InlineKeyboardButton("Ubah Pesan Selamat Datang", callback_data='set_welcome_msg')],
            [InlineKeyboardButton("Ubah Peraturan Grup", callback_data='set_rules')],
            [InlineKeyboardButton(f"Sapaan Anggota Baru: {welcome_status}", callback_data='toggle_welcome')],
            [InlineKeyboardButton(f"Moderasi AI: {moderation_status}", callback_data='toggle_moderation')],
            [InlineKeyboardButton("Tutup Menu", callback_data='close_settings')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Pengaturan moderasi AI telah diperbarui.", reply_markup=reply_markup)
        return SELECTING_ACTION


    elif action == 'close_settings':
        await query.edit_message_text("Menu pengaturan ditutup.")
        return ConversationHandler.END
    
    return SELECTING_ACTION

async def save_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan pesan selamat datang yang baru dari pengguna."""
    if not update.message or not update.message.text:
        return AWAITING_WELCOME_MESSAGE
        
    db_handler.set_group_setting(update.effective_chat.id, 'welcome_message', update.message.text_html)
    await update.message.reply_text("✅ Pesan selamat datang berhasil diperbarui. Kembali ke menu pengaturan...")
    await settings_command(update, context) # Kembali ke menu utama
    return ConversationHandler.END

async def save_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Menyimpan peraturan baru dari pengguna."""
    if not update.message or not update.message.text:
        return AWAITING_RULES
        
    db_handler.set_group_setting(update.effective_chat.id, 'rules_text', update.message.text_html)
    await update.message.reply_text("✅ Peraturan grup berhasil diperbarui. Kembali ke menu pengaturan...")
    await settings_command(update, context) # Kembali ke menu utama
    return ConversationHandler.END

async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Membatalkan alur percakapan pengaturan."""
    await update.message.reply_text("Aksi dibatalkan. Menu pengaturan ditutup.")
    return ConversationHandler.END
