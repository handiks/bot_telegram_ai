# -*- coding: utf-8 -*-

"""
Modul ini berisi semua fungsionalitas terkait AI untuk moderasi grup.
Versi ini terintegrasi dengan sistem peringatan.
"""

import logging
import os
import google.generativeai as genai
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import Forbidden

# Mengimpor fungsi dari file lain
import db_handler
from commands import issue_warning # <-- Impor fungsi peringatan yang baru

# Inisialisasi logger
logger = logging.getLogger(__name__)

# --- Konfigurasi Model AI ---
try:
    GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
    genai.configure(api_key=GEMINI_API_KEY)
    
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    gemini_model = genai.GenerativeModel(
        model_name='gemini-1.5-flash', 
        safety_settings=safety_settings
    )
    logger.info("Model Generative AI (Gemini) berhasil diinisialisasi.")
except KeyError:
    logger.warning("GEMINI_API_KEY tidak ditemukan. Fitur AI akan dinonaktifkan.")
    gemini_model = None
except Exception as e:
    logger.error(f"Terjadi kesalahan saat menginisialisasi Generative AI: {e}")
    gemini_model = None


async def moderate_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Menganalisis pesan grup menggunakan AI dan memberikan peringatan jika perlu.
    """
    if not gemini_model or not update.message or not update.message.text:
        return

    # Periksa apakah moderasi AI aktif untuk grup ini
    if not db_handler.get_group_setting(update.message.chat.id, 'ai_moderation_enabled', True):
        return

    if update.message.chat.type not in ['group', 'supergroup'] or update.message.text.startswith('/'):
        return

    user = update.message.from_user
    message_text = update.message.text
    user_fullname = user.full_name

    prompt = f"""
        Anda adalah AI moderator untuk grup Telegram. Analisis pesan berikut dari pengguna '{user_fullname}'.

        Aturan Grup yang harus ditegakkan:
        1. Dilarang spam atau promosi berulang.
        2. Dilarang bahasa kasar, SARA, atau ujaran kebencian.
        3. Dilarang berbagi informasi pribadi.
        4. Dilarang mengirim link berbahaya.
        5. Diskusi harus tetap relevan dengan topik grup.

        Pesan Pengguna: "{message_text}"

        Tugas Anda:
        - Jika pesan mematuhi semua aturan, balas HANYA dengan kata: safe
        - Jika pesan melanggar aturan, berikan alasan pelanggaran dalam satu kalimat singkat, sopan, dan jelas dalam Bahasa Indonesia.
    """

    try:
        response = await gemini_model.generate_content_async(prompt)
        
        if not response.text:
            logger.warning("AI memberikan respons kosong.")
            return

        ai_response_text = response.text.strip()

        if ai_response_text.lower() != 'safe':
            logger.warning(f"Pelanggaran terdeteksi oleh '{user_fullname}'. Alasan: '{ai_response_text}'")
            
            # 1. Hapus pesan yang melanggar
            try:
                await context.bot.delete_message(
                    chat_id=update.message.chat_id, 
                    message_id=update.message.message_id
                )
                logger.info(f"Berhasil menghapus pesan dari '{user_fullname}'.")
            except Exception as e:
                logger.error(f"Error saat menghapus pesan: {e}")

            # 2. REVISI: Berikan peringatan resmi menggunakan sistem /warn
            # Pesan peringatan akan dikirim oleh fungsi issue_warning
            await issue_warning(
                context=context,
                chat_id=update.effective_chat.id,
                user_to_warn=user,
                warned_by="Moderator AI",
                reason=ai_response_text # Sertakan alasan dari AI
            )

    except Exception as e:
        logger.error(f"Terjadi kesalahan saat berkomunikasi dengan Generative AI: {e}")

