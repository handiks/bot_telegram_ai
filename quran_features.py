# -*- coding: utf-8 -*-

"""
Modul ini berisi semua fungsionalitas terkait fitur Al-Qur'an dan Tafsir.
Menggunakan API dari equran.id.
"""

import logging
import os
import random
import re
from typing import Dict, Any, Union

import requests
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

# Inisialisasi logger untuk modul ini
logger = logging.getLogger(__name__)

# Konfigurasi dasar
EQURAN_API_BASE = "https://equran.id/api/v2"
TARGET_GROUP_ID = os.environ.get('TARGET_GROUP_ID')

# Regex untuk membersihkan tag HTML dari teks tafsir, dikompilasi sekali untuk efisiensi
HTML_CLEANER = re.compile('<.*?>')

def _fetch_api(endpoint: str) -> Union[Dict[str, Any], str]:
    """
    Fungsi pembantu untuk mengambil data dari API equran.id.

    Args:
        endpoint: Endpoint API yang akan diakses (misal: "/surat/1").

    Returns:
        Sebuah dictionary berisi data JSON atau string yang menandakan jenis error.
    """
    url = f"{EQURAN_API_BASE}{endpoint}"
    try:
        # Tambahkan timeout untuk mencegah bot hang jika API lambat
        response = requests.get(url, timeout=15)
        response.raise_for_status()  # Akan raise error untuk status 4xx atau 5xx
        json_data = response.json()
        
        # Validasi respons dari API
        if json_data.get('code') != 200 or 'data' not in json_data:
            logger.error(f"API mengembalikan kode non-200 atau tanpa data untuk {url}: {json_data.get('message')}")
            return "api_error"
        return json_data['data']
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error saat mengambil {url}: {e}")
        return "not_found" if e.response.status_code == 404 else "api_error"
    except requests.exceptions.RequestException as e:
        # Menangkap error koneksi, timeout, dll.
        logger.error(f"Error permintaan saat mengambil {url}: {e}")
        return "api_error"

def get_verse_and_translation(surah: int, ayat: int) -> Union[Dict[str, Any], str]:
    """Mengambil detail ayat spesifik (teks Arab, terjemahan, nama surah) dari API."""
    data = _fetch_api(f"/surat/{surah}")
    if isinstance(data, str):
        return data  # Mengembalikan string error jika terjadi kesalahan

    # Validasi apakah ayat yang diminta ada dalam data
    if not data.get('ayat') or not (0 < ayat <= len(data['ayat'])):
        return "not_found"

    # Ambil data ayat yang sesuai (ingat, list di Python berbasis 0)
    verse_data = data['ayat'][ayat - 1]

    return {
        "surah_name": data.get('namaLatin', 'N/A'),
        "verse_key": f"{surah}:{ayat}",
        "arabic": verse_data.get('teksArab', ''),
        "translation": verse_data.get('teksIndonesia', '')
    }

def get_tafsir(surah: int, ayat: int) -> Union[Dict[str, Any], str]:
    """Mengambil tafsir untuk ayat spesifik, beserta teks ayatnya."""
    # Langkah 1: Dapatkan teks ayat dan nama surah
    verse_details = get_verse_and_translation(surah, ayat)
    if isinstance(verse_details, str):
        return verse_details  # Mengembalikan string error

    # Langkah 2: Dapatkan data tafsir untuk seluruh surah
    tafsir_data = _fetch_api(f"/tafsir/{surah}")
    if isinstance(tafsir_data, str):
        return tafsir_data

    # Langkah 3: Cari tafsir untuk ayat yang spesifik
    tafsir_for_ayat = next((t for t in tafsir_data.get('tafsir', []) if t.get('ayat') == ayat), None)

    if not tafsir_for_ayat:
        return "not_found"

    raw_tafsir = tafsir_for_ayat.get('teks', 'Tafsir tidak ditemukan.')
    
    # Gabungkan hasil
    return {
        "surah_name": verse_details['surah_name'],
        "verse_key": verse_details['verse_key'],
        "verse_text": verse_details['arabic'],
        "tafsir": re.sub(HTML_CLEANER, '', raw_tafsir)
    }

async def send_verse_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /ayat."""
    if not update.message or not context.args:
        await update.message.reply_text("Format salah: `/ayat [surah]:[ayat]`\nContoh: `/ayat 1:5`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        surah_str, ayat_str = context.args[0].split(':')
        surah, ayat = int(surah_str), int(ayat_str)
        if not (1 <= surah <= 114 and ayat > 0):
            raise ValueError
    except (ValueError, IndexError):
        await update.message.reply_text("Format nomor surah atau ayat tidak valid. Contoh: `/ayat 2:255`")
        return

    processing_msg = await update.message.reply_text("📖 Sedang mencari ayat...")
    result = get_verse_and_translation(surah, ayat)
    await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)

    if isinstance(result, dict):
        message = (f"📖 **{result['surah_name']} ({result['verse_key']})**\n\n"
                   f"<b dir='rtl'>{result['arabic']}</b>\n\n"
                   f"<i>Artinya: \"{result['translation']}\"</i>")
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)
    elif result == "not_found":
        await update.message.reply_text(f"Maaf, Surah {surah} Ayat {ayat} tidak dapat ditemukan.")
    else:
        await update.message.reply_text("Maaf, terjadi kesalahan pada server Al-Qur'an. Coba lagi nanti.")

async def send_tafsir_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /tafsir."""
    if not update.message or not context.args:
        await update.message.reply_text("Format salah: `/tafsir [surah]:[ayat]`\nContoh: `/tafsir 2:255`", parse_mode=ParseMode.MARKDOWN)
        return

    try:
        surah_str, ayat_str = context.args[0].split(':')
        surah, ayat = int(surah_str), int(ayat_str)
        if not (1 <= surah <= 114 and ayat > 0):
            raise ValueError
    except (ValueError, IndexError):
        await update.message.reply_text("Format nomor surah atau ayat tidak valid. Contoh: `/tafsir 2:255`")
        return

    processing_msg = await update.message.reply_text("📜 Sedang mencari tafsir...")
    result = get_tafsir(surah, ayat)
    await context.bot.delete_message(chat_id=update.message.chat_id, message_id=processing_msg.message_id)
    
    if isinstance(result, dict):
        header = (f"📜 **Tafsir {result['surah_name']} ({result['verse_key']})**\n\n"
                  f"<b dir='rtl'>{result['verse_text']}</b>\n\n"
                  f"<b>Tafsir (Kemenag):</b>\n")
        tafsir_body = result['tafsir']
        full_message = header + tafsir_body

        if len(full_message) <= 4096:
            await update.message.reply_text(full_message, parse_mode=ParseMode.HTML)
        else:
            # Kirim dalam beberapa bagian jika pesan terlalu panjang
            await update.message.reply_text(header, parse_mode=ParseMode.HTML)
            for i in range(0, len(tafsir_body), 4000):
                await update.message.reply_text(tafsir_body[i:i + 4000], parse_mode=ParseMode.HTML)
    elif result == "not_found":
        await update.message.reply_text(f"Maaf, Tafsir untuk Surah {surah} Ayat {ayat} tidak dapat ditemukan.")
    else:
        await update.message.reply_text("Maaf, terjadi kesalahan pada server Tafsir. Coba lagi nanti.")

async def send_daily_verse(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fungsi yang dijalankan oleh scheduler untuk mengirim ayat acak."""
    if not TARGET_GROUP_ID:
        logger.warning("TARGET_GROUP_ID tidak diatur, membatalkan tugas terjadwal.")
        return
        
    logger.info("Menjalankan tugas terjadwal: mengirim ayat harian...")
    random_surah_num = random.randint(1, 114)
    
    # Hanya satu panggilan API untuk mendapatkan semua data surah
    surah_data = _fetch_api(f"/surat/{random_surah_num}")
    if isinstance(surah_data, str) or not surah_data.get('ayat'):
        logger.error(f"Gagal mendapatkan data ayat harian untuk Surah {random_surah_num}. Respon API: {surah_data}")
        return

    # Pilih ayat acak dari daftar ayat yang diterima
    ayat_list = surah_data['ayat']
    random_verse = random.choice(ayat_list)
    
    surah_name = surah_data.get('namaLatin', 'N/A')
    verse_num = random_verse.get('nomorAyat', 'N/A')
    verse_key = f"{random_surah_num}:{verse_num}"
    arabic_text = random_verse.get('teksArab', '')
    translation_text = random_verse.get('teksIndonesia', '')

    message = (f"✨ **Ayat Harian** ✨\n\n"
               f"📖 **{surah_name} ({verse_key})**\n\n"
               f"<b dir='rtl'>{arabic_text}</b>\n\n"
               f"<i>Artinya: \"{translation_text}\"</i>\n\n#AyatHarian")
               
    try:
        await context.bot.send_message(chat_id=TARGET_GROUP_ID, text=message, parse_mode=ParseMode.HTML)
        logger.info(f"Berhasil mengirim ayat harian {verse_key} ke grup {TARGET_GROUP_ID}")
    except Exception as e:
        logger.error(f"Gagal mengirim ayat harian ke grup {TARGET_GROUP_ID}: {e}")
