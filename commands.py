# -*- coding: utf-8 -*-

"""
Modul ini berisi semua fungsi dasar yang dipanggil oleh pengguna melalui perintah.
"""

import logging
import requests 
import random
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

# Ditambahkan untuk fitur /tanya dan /kisah
from ai_features import gemini_model

# Inisialisasi logger
logger = logging.getLogger(__name__)

# --- Fungsi Perintah Dasar ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengirim pesan sambutan saat pengguna memulai interaksi dengan bot."""
    if not update.message or not update.message.from_user:
        return
    user_name = update.message.from_user.first_name
    # REVISI: Pesan sambutan dibuat lebih personal dan informatif.
    welcome_message = (
        f"Assalamu'alaikum, {user_name}!\n\n"
        "Selamat datang di Bot Islami & Manajemen Grup.\n\n"
        "Saya siap membantu Anda dengan berbagai fitur, seperti:\n"
        "📖 <code>/ayat</code> & <code>/tafsir</code> untuk pencarian Al-Qur'an.\n"
        "🕋 <code>/hadits</code> untuk mencari hadits shahih.\n"
        "🧠 <code>/tanya</code> untuk bertanya seputar Islam.\n"
        "📜 <code>/kisah</code> untuk cerita nabi dan sahabat.\n"
        "🤲 <code>/doa</code> untuk doa-doa harian.\n\n"
        "Ketik <code>/help</code> untuk melihat daftar lengkap perintah."
    )
    await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan daftar semua perintah yang tersedia."""
    if not update.message: return
    # REVISI: Teks bantuan diubah ke format HTML untuk styling command.
    # Tag <code> akan membuat teks terlihat seperti command di Telegram (seringkali berwarna biru).
    help_text = (
        "📖 <b>Daftar Perintah Bot</b>\n\n"
        "<code>/start</code> - Memulai bot\n"
        "<code>/help</code> - Menampilkan pesan bantuan ini\n"
        "<code>/rules</code> - Menampilkan peraturan grup\n"
        "<code>/statistic</code> - Menampilkan statistik grup\n"
        "<code>/doa</code> - Menampilkan doa harian acak\n\n"
        "<b>Fitur Islami & AI:</b>\n"
        "<code>/tanya [pertanyaan]</code> - Tanya jawab Islami\n"
        "<code>/kisah [nama]</code> - Kisah Nabi/Sahabat\n"
        "<code>/ayat [surah]:[ayat]</code> - Mengirim ayat Al-Qur'an\n"
        "<code>/tafsir [surah]:[ayat]</code> - Menampilkan tafsir ayat\n"
        "<code>/hadits [riwayat] [nomor]</code> - Mencari hadits\n\n"
        "<b>Utilitas:</b>\n"
        "<code>/ingatkan [waktu] [pesan]</code> - Mengatur pengingat"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan peraturan grup yang telah ditetapkan."""
    if not update.message: return
    # SARAN: Peraturan ini bisa dipindahkan ke file konfigurasi atau database
    # agar mudah diubah tanpa mengubah kode.
    rules_text = (
        "📜 <b>Peraturan Grup</b>\n\n"
        "1. Jaga adab dan gunakan bahasa yang sopan.\n"
        "2. Dilarang keras mengirim spam, promosi, atau tautan yang tidak relevan.\n"
        "3. Dilarang membahas isu SARA, politik, atau hal yang dapat memicu perdebatan.\n"
        "4. Dilarang mengirim konten pornografi atau kekerasan.\n"
        "5. Hormati sesama anggota grup.\n\n"
        "<i>Pelanggaran terhadap aturan akan ditindak oleh admin atau moderator AI.</i>"
    )
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

# --- Fungsi untuk Doa Harian ---

async def doa_harian_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengambil dan mengirim doa harian acak."""
    if not update.message: return

    processing_message = await update.message.reply_text("🤲 Sedang mencari doa harian...")
    try:
        url = "https://doa-doa-api-ahmadramadhan.fly.dev/api"
        response = requests.get(url, timeout=15)
        response.raise_for_status() # Cek status HTTP
        
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
        # REVISI: Memastikan pesan "loading" selalu dihapus.
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)

# --- Fungsi AI ---

async def tanya_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menjawab pertanyaan pengguna tentang topik keislaman menggunakan AI."""
    if not update.message: return

    if not gemini_model:
        await update.message.reply_text("Maaf, fitur AI saat ini tidak tersedia.")
        return

    if not context.args:
        await update.message.reply_text(
            "Gunakan format: <code>/tanya [pertanyaan Anda]</code>\n"
            "Contoh: <code>/tanya Apa itu istidraj?</code>"
        )
        return

    question = " ".join(context.args)
    processing_message = await update.message.reply_text("🤔 Sedang memproses pertanyaan Anda...")

    # REVISI: Prompt disempurnakan untuk jawaban yang lebih terstruktur dan berdasar.
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
    """Menceritakan kisah nabi atau sahabat menggunakan AI."""
    if not update.message: return

    if not gemini_model:
        await update.message.reply_text("Maaf, fitur AI saat ini tidak tersedia.")
        return

    if not context.args:
        await update.message.reply_text(
            "Gunakan format: <code>/kisah [nama tokoh]</code>\n"
            "Contoh: <code>/kisah Nabi Ibrahim AS</code>"
        )
        return

    tokoh = " ".join(context.args)
    processing_message = await update.message.reply_text(f"📜 Sedang membuka lembaran kisah {tokoh.title()}...")

    # REVISI: Prompt disempurnakan untuk cerita yang lebih menarik dan berhikmah.
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

# --- Fungsi Pencarian Hadits ---

async def hadith_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencari hadits berdasarkan riwayat dan nomor."""
    if not update.message or not context.args or len(context.args) != 2:
        await update.message.reply_text(
            "Format salah. Gunakan: <code>/hadits [riwayat] [nomor]</code>\n"
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

# --- Fungsi Pengingat ---

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
        
        return 0 # Unit tidak valid
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
            "Format salah. Gunakan: <code>/ingatkan [waktu] [pesan]</code>\n"
            "Contoh: <code>/ingatkan 30m Baca Al-Kahfi</code>\n"
            "Waktu: <code>s</code> (detik), <code>m</code> (menit), <code>h</code> (jam), <code>d</code> (hari)"
        )
        return

    if not context.job_queue:
        await update.message.reply_text("Maaf, fitur pengingat saat ini tidak dapat diaktifkan.")
        return

    time_str, reminder_text = context.args[0], " ".join(context.args[1:])
    delay = _parse_reminder_time(time_str)

    # REVISI: Batas waktu yang lebih wajar, misal 30 hari.
    if not (0 < delay <= 2592000): # 30 hari dalam detik
        await update.message.reply_text(
            "Format atau durasi waktu tidak valid. Gunakan angka diikuti <code>s</code>, <code>m</code>, <code>h</code>, atau <code>d</code>.\n"
            "Durasi maksimal adalah 30 hari."
        )
        return

    context.job_queue.run_once(_reminder_callback, delay, chat_id=update.message.chat_id, data=reminder_text)
    await update.message.reply_text(f"✅ Baik, pengingat untuk '<i>{reminder_text}</i>' telah diatur dalam {time_str}.")

# --- Fungsi Anggota Baru ---

async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menyapa setiap anggota baru yang bergabung ke grup."""
    if not update.message or not update.message.new_chat_members:
        return

    for member in update.message.new_chat_members:
        if member.is_bot: continue

        welcome_message = (
            f"Ahlan wa sahlan, {member.mention_html()}!\n\n"
            f"Selamat datang di grup <b>{update.message.chat.title}</b>. "
            "Semoga betah dan mendapatkan banyak manfaat.\n\n"
            "Jangan lupa baca peraturan grup dengan perintah <code>/rules</code> ya."
        )
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)
