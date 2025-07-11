# -*- coding: utf-8 -*-

"""
Modul ini berisi semua fungsionalitas terkait AI untuk moderasi grup.
Menggunakan Google Generative AI (Gemini).
"""

import logging
import os
import google.generativeai as genai
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import Forbidden

# Inisialisasi logger
logger = logging.getLogger(__name__)

# Konfigurasi API Key dari environment variables (Replit Secrets)
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY tidak ditemukan. Fitur AI tidak akan berfungsi.")
    # Setel ke None agar kita bisa memeriksa keberadaannya nanti
    gemini_model = None
else:
    genai.configure(api_key=GEMINI_API_KEY)
    # Konfigurasi model dengan pengaturan keamanan yang sesuai
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    gemini_model = genai.GenerativeModel('gemini-1.5-flash', safety_settings=safety_settings)


async def moderate_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Menganalisis pesan grup menggunakan AI dan melakukan tindakan jika perlu.
    """
    # Pastikan model AI sudah siap dan pesan valid untuk dianalisis
    if not gemini_model or not update.message or not update.message.text:
        return

    # Abaikan pesan dari channel yang ditautkan ke grup atau pesan pribadi
    if update.message.chat.type not in ['group', 'supergroup']:
        return
        
    # Abaikan pesan yang merupakan perintah
    if update.message.text.startswith('/'):
        return

    user = update.message.from_user
    message_text = update.message.text
    user_fullname = user.full_name

    # Prompt yang akan kita kirim ke AI
    # Ini adalah bagian terpenting, karena menentukan bagaimana AI akan berperilaku
    prompt = f"""
        Anda adalah moderator AI untuk grup Telegram. Analisis pesan berikut dari pengguna '{user_fullname}'.

        Aturan Grup:
        1. Dilarang keras mengirim spam atau promosi berulang.
        2. Dilarang menggunakan bahasa kasar, SARA, atau ujaran kebencian.
        3. Dilarang membagikan informasi pribadi (nomor telepon, alamat).
        4. Dilarang mengirim link phising, malware, atau konten berbahaya.
        5. Tetap pada topik yang relevan dengan grup.

        Pesan Pengguna: "{message_text}"

        Tugas Anda:
        - Jika pesan tersebut mematuhi semua aturan, balas HANYA dengan kata: safe
        - Jika pesan tersebut melanggar salah satu aturan, berikan teguran singkat, sopan, dan jelas dalam Bahasa Indonesia yang menjelaskan aturan mana yang dilanggar. Jangan menambahkan kata pembuka atau penutup, langsung ke poin teguran. Contoh: "Pesan Anda mengandung promosi yang tidak diizinkan." atau "Harap gunakan bahasa yang sopan dan tidak menyinggung."
    """

    try:
        logger.info(f"Mengirim pesan dari '{user_fullname}' ke AI untuk dianalisis.")
        # Menggunakan versi async untuk tidak memblokir bot
        response = await gemini_model.generate_content_async(prompt)
        ai_response_text = response.text.strip()

        # Jika respons AI BUKAN 'safe', berarti ada pelanggaran
        if ai_response_text.lower() != 'safe':
            logger.warning(f"AI mendeteksi pelanggaran oleh '{user_fullname}'. Pesan: '{message_text}'. Respon AI: '{ai_response_text}'")
            
            # 1. Kirim pesan teguran sebagai balasan ke pesan pengguna
            await update.message.reply_text(f"⚠️ Peringatan untuk {user.mention_html()}:\n_{ai_response_text}_", parse_mode='HTML')
            
            # 2. Hapus pesan yang melanggar
            try:
                await context.bot.delete_message(chat_id=update.message.chat_id, message_id=update.message.message_id)
                logger.info(f"Berhasil menghapus pesan dari '{user_fullname}'.")
            except Forbidden:
                logger.error("Gagal menghapus pesan. Bot tidak memiliki hak admin untuk menghapus pesan.")
            except Exception as e:
                logger.error(f"Error saat mencoba menghapus pesan: {e}")

    except Exception as e:
        logger.error(f"Terjadi kesalahan saat berkomunikasi dengan Generative AI: {e}")


### --- AKHIR DARI ai_features.py ---
