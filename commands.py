# -*- coding: utf-8 -*-

"""
Modul ini berisi semua fungsi dasar yang dipanggil oleh pengguna melalui perintah.
"""

import logging
import requests 
import datetime 
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
    welcome_message = (
        f"Assalamu'alaikum, {user_name}!\n\n"
        "Saya adalah Bot Islami & Manajemen Grup.\n"
        "Saya bisa membantu Anda dengan fitur-fitur berikut:\n"
        "- Menjawab pertanyaan (`/tanya`).\n"
        "- Mendongeng kisah nabi & sahabat (`/kisah`).\n"
        "- Menampilkan doa harian (`/doa`).\n"
        "- Mengirim ayat Al-Qur'an & tafsirnya.\n"
        "- Mencari hadits.\n"
        "- Mengatur pengingat & memoderasi grup.\n\n"
        "Ketik `/help` untuk melihat daftar lengkap perintah."
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan daftar semua perintah yang tersedia."""
    if not update.message:
        return
    help_text = (
        "📖 *Perintah yang Tersedia*\n\n"
        "`/start` - Memulai bot\n"
        "`/help` - Menampilkan pesan bantuan ini\n"
        "`/rules` - Menampilkan peraturan grup\n"
        "`/statistic` - Menampilkan statistik grup\n"
        "`/doa` - Menampilkan doa harian acak\n"
        "`/tanya [pertanyaan]` - Tanya jawab Islami. Contoh: `/tanya Apa itu istidraj?`\n"
        "`/kisah [nama]` - Kisah Nabi/Sahabat. Contoh: `/kisah Nabi Muhammad SAW`\n"
        "`/ingatkan [waktu] [pesan]` - Mengatur pengingat. Contoh: `/ingatkan 10m Baca Al-Kahfi`\n"
        "`/ayat [surah]:[ayat]` - Mengirim ayat Al-Qur'an. Contoh: `/ayat 18:10`\n"
        "`/tafsir [surah]:[ayat]` - Menampilkan tafsir ayat. Contoh: `/tafsir 2:255`\n"
        "`/hadits [riwayat] [nomor]` - Mencari hadits. Contoh: `/hadits bukhari 52`"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan peraturan grup yang telah ditetapkan."""
    if not update.message:
        return
    # Anda bisa mengubah peraturan ini sesuai dengan grup Anda
    rules_text = (
        "📜 *Peraturan Grup*\n\n"
        "1. Jaga adab dan gunakan bahasa yang sopan.\n"
        "2. Dilarang keras mengirim spam, promosi, atau tautan yang tidak relevan.\n"
        "3. Dilarang membahas isu SARA, politik, atau hal-hal yang dapat memicu perdebatan.\n"
        "4. Dilarang mengirim konten pornografi atau kekerasan.\n"
        "5. Hormati sesama anggota grup.\n\n"
        "Pelanggaran terhadap aturan akan ditindak oleh admin atau moderator AI."
    )
    await update.message.reply_text(rules_text, parse_mode=ParseMode.MARKDOWN)

async def statistic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menampilkan statistik dasar untuk grup."""
    if not update.message or update.message.chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Perintah ini hanya dapat digunakan di dalam grup.")
        return

    try:
        chat_id = update.message.chat.id
        chat_title = update.message.chat.title

        # Dapatkan jumlah anggota grup
        member_count = await context.bot.get_chat_member_count(chat_id)

        stats_text = (
            f"📊 *Statistik untuk Grup: {chat_title}*\n\n"
            f"👤 **Jumlah Anggota:** {member_count}"
        )

        await update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error saat mengambil statistik grup: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mencoba mengambil data statistik grup.")

# --- Fungsi untuk Doa Harian ---

async def doa_harian_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengambil dan mengirim doa harian acak."""
    if not update.message:
        return

    processing_message = await update.message.reply_text("🤲 Sedang mencari doa harian...")
    try:
        url = "https://doa-doa-api-ahmadramadhan.fly.dev/api"
        response = requests.get(url, timeout=15)
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)

        if response.status_code == 200:
            # API mengembalikan list, kita ambil satu secara acak
            doa_list = response.json()
            if not doa_list:
                raise ValueError("API returned an empty list")

            import random
            doa = random.choice(doa_list)

            doa_text = (
                f"🤲 **{doa['doa']}**\n\n"
                f"<b dir='rtl'>{doa['ayat']}</b>\n\n"
                f"<i>{doa['latin']}</i>\n\n"
                f"<b>Artinya:</b>\n"
                f"\"{doa['artinya']}\""
            )
            await update.message.reply_text(doa_text, parse_mode=ParseMode.HTML)
        else:
            logger.error(f"API Doa Harian mengembalikan status {response.status_code}")
            await update.message.reply_text("Maaf, terjadi kesalahan pada server Doa. Coba lagi nanti.")

    except (requests.exceptions.RequestException, ValueError) as e:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)
        logger.error(f"Error saat menghubungi API Doa Harian: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan koneksi saat mencari doa harian.")


# --- Fungsi Tanya Jawab Islami dengan AI ---

async def tanya_ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menjawab pertanyaan pengguna tentang topik keislaman menggunakan AI."""
    if not update.message:
        return

    if not gemini_model:
        await update.message.reply_text("Maaf, fitur AI saat ini tidak tersedia. Kunci API belum diatur.")
        return

    if not context.args:
        await update.message.reply_text(
            "Format salah. Gunakan: `/tanya [pertanyaan Anda]`\n"
            "Contoh: `/tanya Apa hukum jual beli online?`"
        )
        return

    question = " ".join(context.args)
    processing_message = await update.message.reply_text("🤔 Sedang memikirkan jawaban...")

    # Prompt yang dirancang khusus untuk jawaban Islami
    prompt = f"""
        Anda adalah seorang asisten AI yang berpengetahuan luas dalam ilmu agama Islam.
        Tugas Anda adalah menjawab pertanyaan berikut dengan sopan, jelas, dan berdasarkan sumber yang terpercaya (Al-Qur'an dan Hadits shahih) jika memungkinkan.
        Hindari memberikan opini pribadi. Jika pertanyaan berada di luar konteks keislaman atau Anda tidak tahu jawabannya, katakan dengan jujur.

        Pertanyaan dari pengguna: "{question}"

        Jawaban Anda:
    """

    try:
        response = await gemini_model.generate_content_async(prompt)
        ai_response_text = response.text.strip()

        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)
        await update.message.reply_text(ai_response_text)

    except Exception as e:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)
        logger.error(f"Error saat menggunakan fitur /tanya: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat berkomunikasi dengan AI. Coba lagi nanti.")

# --- Fungsi Kisah Nabi & Sahabat ---

async def kisah_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menceritakan kisah nabi atau sahabat menggunakan AI."""
    if not update.message:
        return

    if not gemini_model:
        await update.message.reply_text("Maaf, fitur AI saat ini tidak tersedia. Kunci API belum diatur.")
        return

    if not context.args:
        await update.message.reply_text(
            "Format salah. Gunakan: `/kisah [nama tokoh]`\n"
            "Contoh: `/kisah Nabi Ibrahim AS`"
        )
        return

    tokoh = " ".join(context.args)
    processing_message = await update.message.reply_text(f"📜 Sedang membuka lembaran kisah {tokoh.title()}...")

    # Prompt yang dirancang khusus untuk bercerita
    prompt = f"""
        Anda adalah seorang pencerita (storyteller) yang ahli dalam sejarah Islam.
        Tugas Anda adalah menceritakan kisah dari tokoh berikut: "{tokoh}".
        Ceritakan dengan gaya bahasa yang menarik, ringkas, dan mudah dipahami oleh semua kalangan. 
        Fokus pada pelajaran atau hikmah yang bisa diambil dari kisah tersebut.

        Kisah dari: "{tokoh}"
    """

    try:
        response = await gemini_model.generate_content_async(prompt)
        ai_response_text = response.text.strip()

        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)
        await update.message.reply_text(ai_response_text)

    except Exception as e:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)
        logger.error(f"Error saat menggunakan fitur /kisah: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat berkomunikasi dengan AI. Coba lagi nanti.")


# --- Fungsi untuk Pencarian Hadits ---

async def hadith_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mencari hadits berdasarkan riwayat dan nomor."""
    if not update.message or not context.args or len(context.args) != 2:
        await update.message.reply_text(
            "Format salah. Gunakan: `/hadits [riwayat] [nomor]`\n"
            "Contoh: `/hadits muslim 100`\n\n"
            "Riwayat yang tersedia: `bukhari`, `muslim`, `tirmidzi`, `nasai`, `dawud`, `majah`, `ahmad`."
        )
        return

    riwayat = context.args[0].lower()
    nomor_str = context.args[1]

    # Validasi nomor
    if not nomor_str.isdigit():
        await update.message.reply_text("Nomor hadits harus berupa angka.")
        return

    nomor = int(nomor_str)

    processing_message = await update.message.reply_text(f"🔍 Sedang mencari Hadits {riwayat.capitalize()} nomor {nomor}...")

    try:
        url = f"https://api.hadith.gading.dev/books/{riwayat}/{nomor}"
        response = requests.get(url, timeout=20)
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)

        if response.status_code == 200:
            data = response.json()['data']
            hadith = data['contents']

            message = (
                f"📜 **Hadits {data['name']} No. {hadith['number']}**\n\n"
                f"<b dir='rtl'>{hadith['arab']}</b>\n\n"
                f"<i>Artinya: \"{hadith['id']}\"</i>"
            )

            # Kirim dalam beberapa bagian jika pesan terlalu panjang
            if len(message) <= 4096:
                await update.message.reply_text(message, parse_mode=ParseMode.HTML)
            else:
                header = (f"📜 **Hadits {data['name']} No. {hadith['number']}**\n\n"
                          f"<b dir='rtl'>{hadith['arab']}</b>\n\n"
                          f"<i>Artinya:</i>")
                await update.message.reply_text(header, parse_mode=ParseMode.HTML)

                translation_body = f"\"{hadith['id']}\""
                for i in range(0, len(translation_body), 4000):
                    chunk = translation_body[i:i + 4000]
                    await update.message.reply_text(f"<i>{chunk}</i>", parse_mode=ParseMode.HTML)

        elif response.status_code == 404:
            await update.message.reply_text(f"Maaf, Hadits {riwayat.capitalize()} nomor {nomor} tidak dapat ditemukan.")
        else:
            logger.error(f"API Hadits mengembalikan status {response.status_code}")
            await update.message.reply_text("Maaf, terjadi kesalahan pada server Hadits. Coba lagi nanti.")

    except requests.exceptions.RequestException as e:
        await context.bot.delete_message(chat_id=update.message.chat.id, message_id=processing_message.message_id)
        logger.error(f"Error saat menghubungi API Hadits: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan koneksi saat mencari hadits.")


# --- Fungsi untuk Pengingat ---

def _parse_reminder_time(time_str: str) -> int:
    """Mengubah string waktu (misal: 5m, 1h, 2d) menjadi detik."""
    time_str = time_str.lower()
    if time_str.endswith('s'):
        return int(time_str[:-1])
    if time_str.endswith('m'):
        return int(time_str[:-1]) * 60
    if time_str.endswith('h'):
        return int(time_str[:-1]) * 3600
    if time_str.endswith('d'):
        return int(time_str[:-1]) * 86400
    raise ValueError("Format waktu tidak valid.")

async def _reminder_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fungsi yang dijalankan saat waktu pengingat tiba."""
    job = context.job
    if not job or not job.chat_id or not job.data:
        return
    await context.bot.send_message(chat_id=job.chat_id, text=f"⏰ **Pengingat:**\n\n_{job.data}_", parse_mode=ParseMode.MARKDOWN)

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mengatur pengingat untuk pengguna."""
    if not update.message or not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Format salah. Gunakan: `/ingatkan [waktu] [pesan]`\n"
            "Contoh: `/ingatkan 30m Jangan lupa sholat`\n"
            "Waktu: `s` (detik), `m` (menit), `h` (jam), `d` (hari)"
        )
        return

    # Periksa apakah job_queue tersedia sebelum menggunakannya
    if not context.job_queue:
        await update.message.reply_text("Maaf, fitur pengingat saat ini tidak tersedia.")
        return

    try:
        delay = _parse_reminder_time(context.args[0])
        reminder_text = " ".join(context.args[1:])

        if not (0 < delay <= 31536000): # Batasi hingga 1 tahun
            raise ValueError("Durasi tidak valid.")

        # Atur tugas pengingat
        context.job_queue.run_once(_reminder_callback, delay, chat_id=update.message.chat.id, data=reminder_text)

        await update.message.reply_text(f"Baik, saya akan mengingatkan Anda tentang '{reminder_text}' dalam {context.args[0]}.")

    except (ValueError, IndexError):
        await update.message.reply_text(
            "Format waktu tidak valid. Gunakan angka diikuti `s`, `m`, `h`, atau `d`.\n"
            "Contoh: `10m` untuk 10 menit."
        )
    except Exception as e:
        logger.error(f"Error saat mengatur pengingat: {e}")
        await update.message.reply_text("Maaf, terjadi kesalahan saat mengatur pengingat.")


# --- Fungsi untuk Anggota Baru ---

async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Menyapa setiap anggota baru yang bergabung ke grup."""
    if not update.message or not update.message.new_chat_members:
        return

    for member in update.message.new_chat_members:
        # Abaikan jika bot itu sendiri yang ditambahkan
        if member.is_bot:
            continue

        welcome_message = (
            f"Ahlan wa sahlan, {member.mention_html()}!\n\n"
            f"Selamat datang di grup <b>{update.message.chat.title}</b>.\n"
            "Semoga betah dan jangan lupa untuk membaca peraturan dengan perintah `/rules`."
        )
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.HTML)
