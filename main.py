# -*- coding: utf-8 -*-

"""
File utama untuk menjalankan bot Telegram Islami & Manajemen Grup.
Versi ini berjalan 24/7 dan mendukung fitur pengaturan.
"""

import logging
import os
import datetime
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes,
    Defaults, ConversationHandler, CallbackQueryHandler
)
# ... (import lainnya tetap sama)

# Mengimpor semua fungsi dari modul fitur.
from commands import (
    start, help_command, rules, statistic, doa_harian_command,
    tanya_ai_command, kisah_command, hadith_command, set_reminder, 
    greet_new_member,
    # Impor baru untuk settings
    settings_command, settings_button_callback, save_welcome_message, save_rules, cancel_settings,
    SELECTING_ACTION, AWAITING_WELCOME_MESSAGE, AWAITING_RULES
)
from quran_features import send_verse_command, send_tafsir_command, send_daily_verse
from ai_features import moderate_chat, gemini_model
# ... (kode konfigurasi logging, env variables, keep-alive, error_handler, post_init tetap sama)

def main() -> None:
    """Fungsi utama untuk mengatur dan menjalankan bot."""
    # ... (kode awal main() tetap sama)
    
    defaults = Defaults(parse_mode="HTML", link_preview_options=LinkPreviewOptions(is_disabled=True))
    application = Application.builder().token(BOT_TOKEN).defaults(defaults).post_init(post_init).build()

    application.add_error_handler(error_handler)

    # --- FITUR BARU: Conversation Handler untuk /settings ---
    settings_handler = ConversationHandler(
        entry_points=[CommandHandler("settings", settings_command)],
        states={
            SELECTING_ACTION: [CallbackQueryHandler(settings_button_callback)],
            AWAITING_WELCOME_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_welcome_message)],
            AWAITING_RULES: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_rules)],
        },
        fallbacks=[CommandHandler("batal", cancel_settings)],
    )
    application.add_handler(settings_handler)

    # --- Pendaftaran Handler Lainnya ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules))
    # ... (daftarkan semua CommandHandler lain seperti sebelumnya)
    application.add_handler(CommandHandler("statistic", statistic))
    application.add_handler(CommandHandler("doa", doa_harian_command))
    application.add_handler(CommandHandler("ingatkan", set_reminder))
    application.add_handler(CommandHandler("ayat", send_verse_command))
    application.add_handler(CommandHandler("tafsir", send_tafsir_command))
    application.add_handler(CommandHandler("hadits", hadith_command))
    
    if gemini_model:
        application.add_handler(CommandHandler("tanya", tanya_ai_command))
        application.add_handler(CommandHandler("kisah", kisah_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, moderate_chat))
        logger.info("Handler untuk fitur AI telah aktif.")

    application.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_member))

    # ... (kode job_queue dan application.run_polling() tetap sama)
    
    logger.info("Bot mulai berjalan...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
