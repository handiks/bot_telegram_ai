# -*- coding: utf-8 -*-

"""
Modul untuk menangani database pengaturan grup.
Menggunakan file JSON sederhana sebagai penyimpanan.
"""

import json
import logging
from typing import Dict, Any

# Inisialisasi logger
logger = logging.getLogger(__name__)

DB_FILE = "db_settings.json"

def load_settings() -> Dict[str, Any]:
    """Memuat semua pengaturan dari file JSON."""
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Jika file tidak ada, kembalikan dictionary kosong.
        logger.warning(f"{DB_FILE} tidak ditemukan. Akan dibuat file baru saat pengaturan disimpan.")
        return {}
    except json.JSONDecodeError:
        # Jika file rusak atau kosong, kembalikan dictionary kosong.
        logger.error(f"Error saat membaca {DB_FILE}. File mungkin rusak. Buat backup jika ada.")
        return {}

def save_settings(settings: Dict[str, Any]) -> None:
    """Menyimpan semua pengaturan ke file JSON."""
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Gagal menyimpan pengaturan ke {DB_FILE}: {e}")

def get_group_setting(chat_id: int, key: str, default: Any = None) -> Any:
    """
    Mengambil satu nilai pengaturan spesifik untuk sebuah grup.
    Jika tidak ada, kembalikan nilai default.
    """
    settings = load_settings()
    # Gunakan str(chat_id) karena kunci JSON harus string.
    return settings.get(str(chat_id), {}).get(key, default)

def set_group_setting(chat_id: int, key: str, value: Any) -> None:
    """Menyimpan satu nilai pengaturan spesifik untuk sebuah grup."""
    settings = load_settings()
    chat_id_str = str(chat_id)
    
    # Jika ini pertama kalinya grup diatur, buat entri baru.
    if chat_id_str not in settings:
        settings[chat_id_str] = {}
    
    settings[chat_id_str][key] = value
    save_settings(settings)

def get_default_welcome_message() -> str:
    """Mengembalikan pesan selamat datang default."""
    return (
        "Ahlan wa sahlan, {user_mention}!\n\n"
        "Selamat datang di grup <b>{chat_title}</b>. "
        "Semoga betah dan jangan lupa untuk membaca peraturan dengan perintah /rules."
    )

def get_default_rules() -> str:
    """Mengembalikan peraturan default."""
    return (
        "📜 <b>Peraturan Grup</b>\n\n"
        "1. Jaga adab dan gunakan bahasa yang sopan.\n"
        "2. Dilarang keras mengirim spam, promosi, atau tautan yang tidak relevan.\n"
        "3. Dilarang membahas isu SARA, politik, atau hal yang dapat memicu perdebatan.\n"
        "4. Dilarang mengirim konten pornografi atau kekerasan.\n"
        "5. Hormati sesama anggota grup.\n\n"
        "<i>Pelanggaran terhadap aturan akan ditindak oleh admin atau moderator AI.</i>"
    )
