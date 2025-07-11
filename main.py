# -*- coding: utf-8 -*-

"""
File utama untuk menjalankan bot Telegram Islami & Manajemen Grup.
Versi ini mendukung fitur moderasi /warn dan /kick.
"""

import logging
import os
# ... (import lainnya tetap sama)

# Mengimpor semua fungsi dari modul fitur.
from commands import (
    start, help_command, rules, statistic, doa_harian_command, mutiarakata_command,
    tanya_ai_command, kisah_command, hadith_command, set_reminder, 
    greet_new_member,
    # Impor baru untuk moderasi
    warn_command, kick_command,
    # Impor untuk settings
    settings_command, settings_button_callback, save_welcome_message, save_rules, cancel_settings,
    SELECTING_ACTION, AWAITING_WELCOME_MESSAGE, AWAITING_RULES
)
# ... (import lainnya tetap sama)

# ... (kode konfigurasi logging, env variables, keep-alive, error_handler tetap sama)

async def post_init(application: Application) -> None:
    # ... (kode post_init lainnya tetap sama)
    
    # REVISI: Menambahkan /warn dan /kick ke daftar menu
    commands = [
        BotCommand("start", "Memulai bot"),
        BotCommand("help", "Menampilkan bantuan"),
        BotCommand("rules", "Peraturan grup"),
        BotCommand("settings", "(Admin) Atur bot untuk grup ini"),
        BotCommand("warn", "(Admin) Beri peringatan ke anggota"),
        BotCommand("kick", "(Admin) Keluarkan anggota"),
        BotCommand("statistic", "Statistik grup"),
        BotCommand("doa", "Doa harian acak"),
        BotCommand("mutiarakata", "Mutiara kata dari para ulama"),
        BotCommand("ayat", "Cari ayat Al-Qur'an"),
        BotCommand("tafsir", "Cari tafsir ayat"),
        BotCommand("hadits", "Cari hadits"),
        BotCommand("tanya", "Tanya jawab Islami dengan AI"),
        BotCommand("kisah", "Kisah Nabi atau Sahabat dari AI"),
        BotCommand("ingatkan", "Buat pengingat"),
    ]
    await application.bot.set_my_commands(commands)
    logger.info("Menu perintah bot berhasil diatur.")

def main() -> None:
    """Fungsi utama untuk mengatur dan menjalankan bot."""
    # ... (kode awal main() tetap sama)
    
    # --- Handler untuk /settings ---
    # ... (kode ConversationHandler tetap sama)

    # --- Pendaftaran Handler Lainnya ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("rules", rules))
    application.add_handler(CommandHandler("statistic", statistic))
    application.add_handler(CommandHandler("doa", doa_harian_command))
    application.add_handler(CommandHandler("mutiarakata", mutiarakata_command))
    application.add_handler(CommandHandler("ingatkan", set_reminder))
    application.add_handler(CommandHandler("ayat", send_verse_command))
    application.add_handler(CommandHandler("tafsir", send_tafsir_command))
    application.add_handler(CommandHandler("hadits", hadith_command))
    
    # Handler Moderasi Baru
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(CommandHandler("kick", kick_command))
    
    # ... (sisa pendaftaran handler dan kode lainnya tetap sama)
    
    logger.info("Bot mulai berjalan...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
