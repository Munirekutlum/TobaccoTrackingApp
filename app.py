from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import pandas as pd
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers="*", supports_credentials=True)

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'veritabani.sqlite3')

def get_db_connection():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None

def test_connection():
    """Bağlantıyı test eder ve sunucu bilgilerini gösterir"""
    conn = get_db_connection()
    if not conn:
        print("Bağlantı test edilemedi.")
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print(f"SQL Server Version: {version}")
        
        cursor.execute("SELECT DB_NAME()")
        db_name = cursor.fetchone()[0]
        print(f"Current Database: {db_name}")
        
        cursor.execute("SELECT SYSTEM_USER")
        user = cursor.fetchone()[0]
        print(f"Connected as: {user}")
        
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Bağlantı testi hatası: {e}")
        return False

def table_exists(cursor, table_name):
    """Tablonun var olup olmadığını kontrol eder"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None

def count_records(cursor, table_name):
    """Tablodaki kayıt sayısını döndürür"""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
    except:
        return 0

def initialize_db():
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (initialize_db)")
        return False

    try:
        cursor = conn.cursor()
        cursor.execute('PRAGMA foreign_keys = ON;')
        
        # Tablo tanımları
        tables = {
            'users': '''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT,
                surname TEXT
            );''',
            'fcv_bakim': '''CREATE TABLE IF NOT EXISTS fcv_bakim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'fcv_genel': '''CREATE TABLE IF NOT EXISTS fcv_genel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                firinNo INTEGER,
                tarla TEXT,
                turSayisi INTEGER,
                gTarih TEXT,
                cTarih TEXT,
                yasKg REAL,
                kuruKg REAL,
                ortalama REAL,
                koliSayisi INTEGER,
                yakitToplam REAL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'fcv_kirim_gunluk': '''CREATE TABLE IF NOT EXISTS fcv_kirim_gunluk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                userId INTEGER NOT NULL,
                tarih TEXT NOT NULL,
                bocaSayisi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                UNIQUE(userId, tarih),
                FOREIGN KEY(userId) REFERENCES users(id) ON DELETE CASCADE
            );''',
            'fcv_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS fcv_kirim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gunlukId INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(gunlukId) REFERENCES fcv_kirim_gunluk(id) ON DELETE CASCADE
            );''',
            'fcv_rask_dolum': '''CREATE TABLE IF NOT EXISTS fcv_rask_dolum (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'izmir_dizim': '''CREATE TABLE IF NOT EXISTS izmir_dizim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'izmir_dizim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS izmir_dizim_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'izmir_dizim_gunluk': '''CREATE TABLE IF NOT EXISTS izmir_dizim_gunluk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                diziAdedi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES izmir_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'izmir_dizim_agirlik': '''CREATE TABLE IF NOT EXISTS izmir_dizim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yaprakSayisi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES izmir_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'izmir_genel': '''CREATE TABLE IF NOT EXISTS izmir_genel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'izmir_kirim': '''CREATE TABLE IF NOT EXISTS izmir_kirim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'izmir_kirim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS izmir_kirim_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                UNIQUE(dayibasi, tarih)
            );''',
            'izmir_kirim_gunluk': '''CREATE TABLE IF NOT EXISTS izmir_kirim_gunluk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                bohcaSayisi INTEGER,
                agirlik_id INTEGER,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES izmir_kirim_dayibasi_table(id)
            );''',
            'izmir_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS izmir_kirim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES izmir_kirim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'izmir_kutulama': '''CREATE TABLE IF NOT EXISTS izmir_kutulama (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                sera_yeri TEXT NOT NULL,
                sera_no TEXT NOT NULL,
                sera_yas_kg REAL NOT NULL,
                kutular TEXT NOT NULL,
                toplam_kuru_kg REAL NOT NULL,
                yas_kuru_orani REAL NOT NULL,
                yazici_adi TEXT,
                sera_bosaltildi TEXT DEFAULT 'hayir',
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'izmir_kutulama_dayibasi_table': '''CREATE TABLE IF NOT EXISTS izmir_kutulama_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'izmir_kutulama_kuru_kg': '''CREATE TABLE IF NOT EXISTS izmir_kutulama_kuru_kg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                value REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES izmir_kutulama_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'izmir_kutulama_sera_yas_kg': '''CREATE TABLE IF NOT EXISTS izmir_kutulama_sera_yas_kg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                value REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES izmir_kutulama_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'izmir_sera': '''CREATE TABLE IF NOT EXISTS izmir_sera (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sera_yeri TEXT,
                sera_no TEXT,
                dizi_sayisi INTEGER,
                dizi_kg1 REAL,
                dizi_kg2 REAL,
                dizi_kg3 REAL,
                dizi_kg4 REAL,
                dizi_kg5 REAL,
                dizi_kg6 REAL,
                bosaltma_tarihi TEXT,
                sera_bosaltildi TEXT DEFAULT 'hayir',
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'izmir_sera_yerleri': '''CREATE TABLE IF NOT EXISTS izmir_sera_yerleri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sera_yeri TEXT NOT NULL UNIQUE,
                toplam_sera_sayisi INTEGER NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'jti_scv_kirim': '''CREATE TABLE IF NOT EXISTS jti_scv_kirim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'jti_scv_kirim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS jti_scv_kirim_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                UNIQUE(dayibasi, tarih)
            );''',
            'jti_scv_kirim_gunluk': '''CREATE TABLE IF NOT EXISTS jti_scv_kirim_gunluk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                bohcaSayisi INTEGER,
                agirlik_id INTEGER,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES jti_scv_kirim_dayibasi_table(id)
            );''',
            'jti_scv_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS jti_scv_kirim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES jti_scv_kirim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'jti_scv_dizim': '''CREATE TABLE IF NOT EXISTS jti_scv_dizim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'jti_scv_dizim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS jti_scv_dizim_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'jti_scv_dizim_gunluk': '''CREATE TABLE IF NOT EXISTS jti_scv_dizim_gunluk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                diziAdedi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES jti_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'jti_scv_dizim_agirlik': '''CREATE TABLE IF NOT EXISTS jti_scv_dizim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES jti_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'jti_scv_kutulama': '''CREATE TABLE IF NOT EXISTS jti_scv_kutulama (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'jti_scv_kutulama_dayibasi_table': '''CREATE TABLE IF NOT EXISTS jti_scv_kutulama_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'jti_scv_kutulama_kuru_kg': '''CREATE TABLE IF NOT EXISTS jti_scv_kutulama_kuru_kg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                value REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES jti_scv_kutulama_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'jti_scv_kutulama_sera_yas_kg': '''CREATE TABLE IF NOT EXISTS jti_scv_kutulama_sera_yas_kg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                value REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES jti_scv_kutulama_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_scv_dizim': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'pmi_scv_dizim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'pmi_scv_dizim_gunluk': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_gunluk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                diziAdedi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_scv_dizim_agirlik': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_scv_kirim': '''CREATE TABLE IF NOT EXISTS pmi_scv_kirim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'pmi_scv_kirim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_scv_kirim_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL
            );''',
            'pmi_scv_kirim_gunluk': '''CREATE TABLE IF NOT EXISTS pmi_scv_kirim_gunluk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                bohcaSayisi INTEGER NOT NULL,
                agirlik_id INTEGER,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_kirim_dayibasi_table(id)
            );''',
            'pmi_scv_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS pmi_scv_kirim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_kirim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_scv_kutulama': '''CREATE TABLE IF NOT EXISTS pmi_scv_kutulama (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'pmi_scv_kutulama_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_scv_kutulama_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'pmi_scv_kutulama_kuru_kg': '''CREATE TABLE IF NOT EXISTS pmi_scv_kutulama_kuru_kg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                value REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_kutulama_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_scv_kutulama_sera_yas_kg': '''CREATE TABLE IF NOT EXISTS pmi_scv_kutulama_sera_yas_kg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                value REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_kutulama_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_topping_kirim': '''CREATE TABLE IF NOT EXISTS pmi_topping_kirim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'pmi_topping_kirim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_topping_kirim_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                UNIQUE(dayibasi, tarih)
            );''',
            'pmi_topping_kirim_gunluk': '''CREATE TABLE IF NOT EXISTS pmi_topping_kirim_gunluk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                bohcaSayisi INTEGER,
                agirlik_id INTEGER,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_kirim_dayibasi_table(id)
            );''',
            'pmi_topping_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS pmi_topping_kirim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_kirim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_topping_dizim': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'pmi_topping_dizim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'pmi_topping_dizim_gunluk': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_gunluk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                diziAdedi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_topping_dizim_agirlik': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_topping_kutulama': '''CREATE TABLE IF NOT EXISTS pmi_topping_kutulama (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                placeholder_col TEXT
            );''',
            'pmi_topping_kutulama_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_topping_kutulama_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'pmi_topping_kutulama_kuru_kg': '''CREATE TABLE IF NOT EXISTS pmi_topping_kutulama_kuru_kg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                value REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_kutulama_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_topping_kutulama_sera_yas_kg': '''CREATE TABLE IF NOT EXISTS pmi_topping_kutulama_sera_yas_kg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                value REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_kutulama_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'scv_sera': '''CREATE TABLE IF NOT EXISTS scv_sera (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sera_yeri TEXT,
                alan TEXT,
                sera_no TEXT,
                dizi_sayisi INTEGER,
                dizi_kg1 REAL,
                dizi_kg2 REAL,
                dizi_kg3 REAL,
                dizi_kg4 REAL,
                dizi_kg5 REAL,
                dizi_kg6 REAL,
                bosaltma_tarihi TEXT,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'scv_sera_yerleri': '''CREATE TABLE IF NOT EXISTS scv_sera_yerleri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sera_yeri TEXT NOT NULL UNIQUE,
                toplam_sera_sayisi INTEGER NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'scv_kutulama': '''CREATE TABLE IF NOT EXISTS scv_kutulama (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                sera_yeri TEXT NOT NULL,
                sera_no TEXT NOT NULL,
                sera_yas_kg REAL NOT NULL,
                kutular TEXT NOT NULL,
                toplam_kuru_kg REAL NOT NULL,
                yas_kuru_orani REAL NOT NULL,
                alan TEXT NOT NULL,
                yazici_adi TEXT,
                sera_bosaltildi TEXT DEFAULT 'hayir',
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'pmi_scv_dizim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'pmi_scv_dizim_gunluk': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_gunluk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                diziAdedi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_scv_dizim_agirlik': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_topping_kirim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_topping_kirim_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                UNIQUE(dayibasi, tarih)
            );''',
            'pmi_topping_kirim_gunluk': '''CREATE TABLE IF NOT EXISTS pmi_topping_kirim_gunluk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                bohcaSayisi INTEGER,
                agirlik_id INTEGER,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_kirim_dayibasi_table(id)
            );''',
            'pmi_topping_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS pmi_topping_kirim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_kirim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_topping_dizim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'pmi_topping_dizim_gunluk': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_gunluk (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                diziAdedi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_topping_dizim_agirlik': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_topping_kutulama_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_topping_kutulama_dayibasi_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'pmi_topping_kutulama_kuru_kg': '''CREATE TABLE IF NOT EXISTS pmi_topping_kutulama_kuru_kg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                value REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_kutulama_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_topping_kutulama_sera_yas_kg': '''CREATE TABLE IF NOT EXISTS pmi_topping_kutulama_sera_yas_kg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dayibasi_id INTEGER NOT NULL,
                value REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_kutulama_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'sevkiyat': '''CREATE TABLE IF NOT EXISTS sevkiyat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT,
                kutu INTEGER,
                kg REAL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
            );''',
            'jti_scv_dizim_yaprak': '''CREATE TABLE IF NOT EXISTS jti_scv_dizim_yaprak (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agirlik_id INTEGER NOT NULL,
                yaprakSayisi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(agirlik_id) REFERENCES jti_scv_dizim_agirlik(id) ON DELETE CASCADE
            );''',
            'pmi_scv_dizim_yaprak': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_yaprak (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agirlik_id INTEGER NOT NULL,
                yaprakSayisi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(agirlik_id) REFERENCES pmi_scv_dizim_agirlik(id) ON DELETE CASCADE
            );''',
            'pmi_topping_dizim_yaprak': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_yaprak (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agirlik_id INTEGER NOT NULL,
                yaprakSayisi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(agirlik_id) REFERENCES pmi_topping_dizim_agirlik(id) ON DELETE CASCADE
            );''',
            # --- JTI SCV KIRIM yeni sistem için ---
            'traktor_gelis_jti_kirim': '''CREATE TABLE IF NOT EXISTS traktor_gelis_jti_kirim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                plaka TEXT NOT NULL,
                gelis_no INTEGER NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                UNIQUE(tarih, plaka, gelis_no)
            );''',
            'traktor_gelis_jti_kirim_dayibasi': '''CREATE TABLE IF NOT EXISTS traktor_gelis_jti_kirim_dayibasi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                traktor_gelis_jti_kirim_id INTEGER NOT NULL,
                dayibasi_adi TEXT NOT NULL,
                bohca_sayisi INTEGER NOT NULL,
                FOREIGN KEY(traktor_gelis_jti_kirim_id) REFERENCES traktor_gelis_jti_kirim(id) ON DELETE CASCADE
            );''',
            'traktor_gelis_jti_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS traktor_gelis_jti_kirim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                traktor_gelis_jti_kirim_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(traktor_gelis_jti_kirim_id) REFERENCES traktor_gelis_jti_kirim(id) ON DELETE CASCADE
            );''',
            # --- PMI SCV KIRIM yeni sistem için ---
            'traktor_gelis_pmi_kirim': '''CREATE TABLE IF NOT EXISTS traktor_gelis_pmi_kirim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                plaka TEXT NOT NULL,
                gelis_no INTEGER NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                UNIQUE(tarih, plaka, gelis_no)
            );''',
            'traktor_gelis_pmi_kirim_dayibasi': '''CREATE TABLE IF NOT EXISTS traktor_gelis_pmi_kirim_dayibasi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                traktor_gelis_pmi_kirim_id INTEGER NOT NULL,
                dayibasi_adi TEXT NOT NULL,
                bohca_sayisi INTEGER NOT NULL,
                FOREIGN KEY(traktor_gelis_pmi_kirim_id) REFERENCES traktor_gelis_pmi_kirim(id) ON DELETE CASCADE
            );''',
            'traktor_gelis_pmi_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS traktor_gelis_pmi_kirim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                traktor_gelis_pmi_kirim_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(traktor_gelis_pmi_kirim_id) REFERENCES traktor_gelis_pmi_kirim(id) ON DELETE CASCADE
            );''',
            # --- PMI TOPPING KIRIM yeni sistem için ---
            'traktor_gelis_pmi_topping_kirim': '''CREATE TABLE IF NOT EXISTS traktor_gelis_pmi_topping_kirim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                plaka TEXT NOT NULL,
                gelis_no INTEGER NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                UNIQUE(tarih, plaka, gelis_no)
            );''',
            'traktor_gelis_pmi_topping_kirim_dayibasi': '''CREATE TABLE IF NOT EXISTS traktor_gelis_pmi_topping_kirim_dayibasi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                traktor_gelis_pmi_topping_kirim_id INTEGER NOT NULL,
                dayibasi_adi TEXT NOT NULL,
                bohca_sayisi INTEGER NOT NULL,
                FOREIGN KEY(traktor_gelis_pmi_topping_kirim_id) REFERENCES traktor_gelis_pmi_topping_kirim(id) ON DELETE CASCADE
            );''',
            'traktor_gelis_pmi_topping_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS traktor_gelis_pmi_topping_kirim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                traktor_gelis_pmi_topping_kirim_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(traktor_gelis_pmi_topping_kirim_id) REFERENCES traktor_gelis_pmi_topping_kirim(id) ON DELETE CASCADE
            );''',
            # --- IZMIR KIRIM yeni sistem için ---
            'traktor_gelis_izmir_kirim': '''CREATE TABLE IF NOT EXISTS traktor_gelis_izmir_kirim (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tarih TEXT NOT NULL,
                plaka TEXT NOT NULL,
                gelis_no INTEGER NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                UNIQUE(tarih, plaka, gelis_no)
            );''',
            'traktor_gelis_izmir_kirim_dayibasi': '''CREATE TABLE IF NOT EXISTS traktor_gelis_izmir_kirim_dayibasi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                traktor_gelis_izmir_kirim_id INTEGER NOT NULL,
                dayibasi_adi TEXT NOT NULL,
                bohca_sayisi INTEGER NOT NULL,
                FOREIGN KEY(traktor_gelis_izmir_kirim_id) REFERENCES traktor_gelis_izmir_kirim(id) ON DELETE CASCADE
            );''',
            'traktor_gelis_izmir_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS traktor_gelis_izmir_kirim_agirlik (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                traktor_gelis_izmir_kirim_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
                FOREIGN KEY(traktor_gelis_izmir_kirim_id) REFERENCES traktor_gelis_izmir_kirim(id) ON DELETE CASCADE
            );''',
        }
        
        created_tables = []
        existing_tables = []
        
        # Her tablo için kontrol et ve oluştur
        for table_name, create_sql in tables.items():
            if table_exists(cursor, table_name):
                record_count = count_records(cursor, table_name)
                existing_tables.append(f"{table_name} ({record_count} kayıt)")
            else:
                cursor.execute(create_sql)
                created_tables.append(table_name)
        
        conn.commit()
        
        # Sonuçları rapor et
        if created_tables:
            print(f"✅ Yeni oluşturulan tablolar: {', '.join(created_tables)}")
        
        if existing_tables:
            print(f"ℹ️  Zaten var olan tablolar: {', '.join(existing_tables)}")
        
        if not created_tables and not existing_tables:
            print("⚠️  Hiç tablo bulunamadı veya oluşturulamadı.")
        
        return True
    except Exception as e:
        print(f"❌ Tablo oluşturma hatası: {e}")
        return False
    finally:
        conn.close()

def ensure_kutulama_alan_column():
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (alan sütunu kontrolü)")
        return
    try:
        cursor = conn.cursor()
        # SQLite'da sütun kontrolü
        cursor.execute("PRAGMA table_info(scv_kutulama)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'alan' not in columns:
            print("'scv_kutulama' tablosuna 'alan' sütunu ekleniyor...")
            cursor.execute("ALTER TABLE scv_kutulama ADD COLUMN alan TEXT")
            conn.commit()
            print("'alan' sütunu eklendi.")
        else:
            print("'alan' sütunu zaten var.")
    except Exception as e:
        print(f"'alan' sütunu eklenirken hata: {e}")
    finally:
        conn.close()

def ensure_izmir_kutulama_sera_bosaltildi_column():
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (izmir_kutulama sera_bosaltildi sütunu kontrolü)")
        return
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(izmir_kutulama)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'sera_bosaltildi' not in columns:
            print("'izmir_kutulama' tablosuna 'sera_bosaltildi' sütunu ekleniyor...")
            cursor.execute("ALTER TABLE izmir_kutulama ADD COLUMN sera_bosaltildi TEXT DEFAULT 'hayir'")
            conn.commit()
            print("'sera_bosaltildi' sütunu eklendi.")
        else:
            print("'sera_bosaltildi' sütunu zaten var.")
    except Exception as e:
        print(f"'sera_bosaltildi' sütunu eklenirken hata: {e}")
    finally:
        conn.close()

def ensure_izmir_sera_bosaltildi_column():
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (izmir_sera sera_bosaltildi sütunu kontrolü)")
        return
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(izmir_sera)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'sera_bosaltildi' not in columns:
            print("'izmir_sera' tablosuna 'sera_bosaltildi' sütunu ekleniyor...")
            cursor.execute("ALTER TABLE izmir_sera ADD COLUMN sera_bosaltildi TEXT DEFAULT 'hayir'")
            conn.commit()
            print("'sera_bosaltildi' sütunu eklendi.")
        else:
            print("'sera_bosaltildi' sütunu zaten var.")
    except Exception as e:
        print(f"'sera_bosaltildi' sütunu eklenirken hata: {e}")
    finally:
        conn.close()

def ensure_scv_sera_new_columns():
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (scv_sera yeni sütunlar kontrolü)")
        return
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(scv_sera)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'el_grubu' not in columns:
            print("'scv_sera' tablosuna 'el_grubu' sütunu ekleniyor...")
            cursor.execute("ALTER TABLE scv_sera ADD COLUMN el_grubu TEXT")
            conn.commit()
            print("'el_grubu' sütunu eklendi.")
        else:
            print("'el_grubu' sütunu zaten var.")
        if 'soldurma_giris_tarihi' not in columns:
            print("'scv_sera' tablosuna 'soldurma_giris_tarihi' sütunu ekleniyor...")
            cursor.execute("ALTER TABLE scv_sera ADD COLUMN soldurma_giris_tarihi TEXT")
            conn.commit()
            print("'soldurma_giris_tarihi' sütunu eklendi.")
        else:
            print("'soldurma_giris_tarihi' sütunu zaten var.")
        if 'soldurma_bitis_tarihi' not in columns:
            print("'scv_sera' tablosuna 'soldurma_bitis_tarihi' sütunu ekleniyor...")
            cursor.execute("ALTER TABLE scv_sera ADD COLUMN soldurma_bitis_tarihi TEXT")
            conn.commit()
            print("'soldurma_bitis_tarihi' sütunu eklendi.")
        else:
            print("'soldurma_bitis_tarihi' sütunu zaten var.")
    except Exception as e:
        print(f"scv_sera yeni sütunlar eklenirken hata: {e}")
    finally:
        conn.close()

# --- API Endpointleri ---
#-----------------------------------------------------------------------------------------------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = (data.get('email') or '').strip()
    password = data.get('password')
    name = (data.get('name') or '').strip()
    surname = (data.get('surname') or '').strip()

    print(f"[REGISTER] email: {email}, password: {password}")

    if not email or not password or not name or not surname:
        return jsonify({'message': 'Tüm alanlar zorunlu.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı hatası.'}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (email, password, name, surname) VALUES (?, ?, ?, ?)", (email, password, name, surname))
        user_id = cursor.lastrowid
        conn.commit()
        # Yeni kullanıcıyı çek
        cursor.execute("SELECT id, email, name, surname FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        user_data = {'id': user['id'], 'email': user['email'], 'name': user['name'], 'surname': user['surname']}
        return jsonify({'message': 'Kayıt başarılı.', 'user': user_data}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Bu email zaten kayıtlı.'}), 409
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    print(f"[LOGIN] email: {email}, password: {password}")

    if not email or not password:
        return jsonify({'message': 'Email ve şifre gerekli.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500

    cursor = conn.cursor()
    cursor.execute("SELECT id, email, name, surname FROM users WHERE email = ? AND password = ?", (email, password))
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        user_data = {'id': user['id'], 'email': user['email'], 'name': user['name'], 'surname': user['surname']}
        return jsonify({'message': 'Giriş başarılı.', 'user': user_data})
    else:
        return jsonify({'message': 'Email veya şifre hatalı.'}), 401

# --- FCV Genel API Endpointleri ---
#-----------------------------------------------------------------------------------------------------
@app.route('/api/fcv_genel', methods=['POST'])
def add_fcv_genel_data():
    data = request.get_json()
    
    # Gerekli tüm alanların gelip gelmediğini kontrol et
    required_fields = ['firinNo', 'tarla', 'turSayisi', 'gTarih', 'cTarih', 'yasKg', 'kuruKg', 'ortalama', 'koliSayisi', 'yakitToplam']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        sql = """INSERT INTO fcv_genel (firinNo, tarla, turSayisi, gTarih, cTarih, yasKg, kuruKg, ortalama, koliSayisi, yakitToplam)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (
            data['firinNo'], data['tarla'], data['turSayisi'], data['gTarih'], data['cTarih'],
            data['yasKg'], data['kuruKg'], data['ortalama'], data['koliSayisi'], data['yakitToplam']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Veri başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/fcv_genel', methods=['GET'])
def get_fcv_genel_data():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, firinNo, tarla, turSayisi, gTarih, cTarih, yasKg, kuruKg, ortalama, koliSayisi, yakitToplam FROM fcv_genel ORDER BY id DESC")
        
        # Sütun adlarını al
        columns = [column[0] for column in cursor.description]
        # Sonuçları dict listesine çevir
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

# --- FCV Kırım API Endpointleri (YENİ YAPI) ---
#-----------------------------------------------------------------------------------------------------
@app.route('/api/fcv_kirim/summary', methods=['GET'])
def get_kirim_summary():
    tarih = request.args.get('tarih')
    user_id = request.args.get('userId')
    # Tarih parametresi opsiyonel, verilmezse tüm kayıtlar gelir
    sql = '''
        SELECT 
            u.id as userId,
            u.name,
            u.surname,
            g.id as gunlukId,
            g.tarih,
            g.bocaSayisi,
            g.yazici_adi,
            (SELECT COUNT(a.id) FROM fcv_kirim_agirlik a WHERE a.gunlukId = g.id) as girilenAgirlikSayisi,
            (SELECT AVG(a.agirlik) FROM fcv_kirim_agirlik a WHERE a.gunlukId = g.id) as ortalamaAgirlik
        FROM users u
        JOIN fcv_kirim_gunluk g ON u.id = g.userId
        WHERE 1=1
    '''
    params = []
    if tarih:
        sql += ' AND g.tarih = ?'
        params.append(tarih)
    if user_id:
        sql += ' AND u.id = ?'
        params.append(user_id)
    sql += ' ORDER BY g.tarih DESC, u.name, u.surname'

    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            if r['ortalamaAgirlik'] and r['bocaSayisi']:
                r['toplamTahminiKg'] = r['ortalamaAgirlik'] * r['bocaSayisi']
            else:
                r['toplamTahminiKg'] = 0
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/fcv_kirim/gunluk', methods=['POST'])
def add_or_update_gunluk_entry():
    """Bir kullanıcı ve tarih için günlük girişi ekler veya günceller."""
    data = request.get_json()
    required = ['userId', 'tarih', 'bocaSayisi']
    if not all(k in data for k in required):
        return jsonify({'message': 'userId, tarih ve bocaSayisi zorunludur.'}), 400
    
    sql_check = "SELECT id FROM fcv_kirim_gunluk WHERE userId = ? AND tarih = ?"
    sql_insert = "INSERT INTO fcv_kirim_gunluk (userId, tarih, bocaSayisi, yazici_adi) VALUES (?, ?, ?, ?)"
    sql_update = "UPDATE fcv_kirim_gunluk SET bocaSayisi = ?, yazici_adi = ? WHERE id = ?"
    
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['userId'], data['tarih']))
        existing = cursor.fetchone()
        if existing:
            cursor.execute(sql_update, (data['bocaSayisi'], data['yazici_adi'], existing.id))
        else:
            cursor.execute(sql_insert, (data['userId'], data['tarih'], data['bocaSayisi'], data['yazici_adi']))
        conn.commit()
        return jsonify({'message': 'Günlük giriş başarıyla kaydedildi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/fcv_kirim/agirlik', methods=['POST'])
def add_agirlik_entry():
    """Bir günlük kaydına yeni bir ağırlık ekler."""
    data = request.get_json()
    if not data.get('gunlukId') or not data.get('agirlik'):
        return jsonify({'message': 'gunlukId ve agirlik zorunludur.'}), 400
        
    sql = "INSERT INTO fcv_kirim_agirlik (gunlukId, agirlik, yazici_adi) VALUES (?, ?, ?)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (data['gunlukId'], data['agirlik'], data['yazici_adi']))
        conn.commit()
        return jsonify({'message': 'Ağırlık başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/fcv_kirim/agirlik/details', methods=['GET'])
def get_agirlik_details_by_gunlukId():
    """Bir gunlukId'ye ait tüm ağırlık girişlerini döner."""
    gunluk_id = request.args.get('gunlukId')
    if not gunluk_id:
        return jsonify({'message': 'gunlukId parametresi zorunludur.'}), 400
        
    sql = "SELECT id, agirlik, created_at FROM fcv_kirim_agirlik WHERE gunlukId = ? ORDER BY id"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (gunluk_id,))
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/fcv_kirim/agirlik/<int:agirlik_id>', methods=['DELETE'])
def delete_agirlik_entry(agirlik_id):
    """Bir ağırlık girişini siler."""
    sql = "DELETE FROM fcv_kirim_agirlik WHERE id = ?"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (agirlik_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla silindi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/users', methods=['GET'])
def get_users():
    """Tüm kullanıcıları (dayıbaşıları) döner."""
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, surname FROM users ORDER BY name, surname")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

# --- İzmir Kırım API Endpointleri ---
#-----------------------------------------------------------------------------------------------------
#--İzmir dizim api endpointleri----

@app.route('/api/izmir_dizim/summary', methods=['GET'])
def get_izmir_dizim_summary():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi,
                g.id as gunluk_id,
                g.diziAdedi,
                (SELECT COUNT(a.id) FROM izmir_dizim_agirlik a WHERE a.dayibasi_id = d.id) as girilenAgirlikSayisi,
                (SELECT AVG(a.agirlik) FROM izmir_dizim_agirlik a WHERE a.dayibasi_id = d.id) as ortalamaAgirlik
            FROM izmir_dizim_dayibasi_table d
            LEFT JOIN izmir_dizim_gunluk g ON d.id = g.dayibasi_id
            ORDER BY d.tarih DESC, d.dayibasi
        ''')
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            if r['ortalamaAgirlik'] and r['diziAdedi']:
                r['toplamTahminiKg'] = r['ortalamaAgirlik'] * r['diziAdedi']
            else:
                r['toplamTahminiKg'] = 0
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/izmir_dizim/dayibasi', methods=['POST'])
def add_izmir_dizim_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400
    sql_check = "SELECT id FROM izmir_dizim_dayibasi_table WHERE dayibasi = ? AND tarih = ?"
    sql_insert = "INSERT INTO izmir_dizim_dayibasi_table (tarih, dayibasi) VALUES (?, ?)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['dayibasi'], data['tarih']))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'message': 'Bu dayıbaşı ve tarihe ait kayıt zaten var.'}), 409
        cursor.execute(sql_insert, (data['tarih'], data['dayibasi']))
        conn.commit()
        return jsonify({'message': 'Dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/izmir_dizim/agirlik', methods=['POST'])
def add_izmir_dizim_agirlik():
    data = request.get_json()
    agirlik = data.get('agirlik')
    yaprakSayisi = data.get('yaprakSayisi')
    dayibasi_id = data.get('dayibasi_id')
    if not agirlik or not dayibasi_id or not yaprakSayisi:
        return jsonify({'message': 'dayibasi_id, agirlik ve yaprakSayisi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO izmir_dizim_agirlik (dayibasi_id, agirlik, yaprakSayisi, yazici_adi) VALUES (?, ?, ?, ?)", (dayibasi_id, agirlik, yaprakSayisi, data['yazici_adi']))
        conn.commit()
        return jsonify({'message': 'Ağırlık ve yaprak sayısı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/izmir_dizim/agirlik/details', methods=['GET'])
def get_izmir_dizim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    sql = "SELECT id, agirlik,yazici_adi,  created_at FROM izmir_dizim_agirlik WHERE dayibasi_id = ? ORDER BY id"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (dayibasi_id,))
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/izmir_dizim/gunluk', methods=['POST'])
def add_or_update_izmir_dizim_gunluk():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    diziAdedi = data.get('bohcaSayisi')  # frontend 'bohcaSayisi' gönderiyor, burada diziAdedi olarak kaydediyoruz
    if not dayibasi_id or diziAdedi is None:
        return jsonify({'message': 'dayibasi_id ve diziAdedi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM izmir_dizim_gunluk WHERE dayibasi_id = ?", (dayibasi_id,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE izmir_dizim_gunluk SET diziAdedi = ?, yazici_adi = ? WHERE id = ?", (diziAdedi, data['yazici_adi'], existing[0]))
            conn.commit()
            return jsonify({'message': 'Dizi adedi güncellendi.'}), 200
        else:
            cursor.execute("INSERT INTO izmir_dizim_gunluk (dayibasi_id, diziAdedi, yazici_adi) VALUES (?, ?, ?)", (dayibasi_id, diziAdedi, data['yazici_adi']))
            conn.commit()
            return jsonify({'message': 'Dizi adedi eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

#---izmir kutulama api endpointleri-----------
#---izmir kutulama api endpointleri-----------

@app.route('/api/izmir_kutulama/summary', methods=['GET'])
def get_izmir_kutulama_summary():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi
            FROM izmir_kutulama_dayibasi_table d
            ORDER BY d.tarih DESC, d.dayibasi
        ''')
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            # Kuru kg listesi
            cursor.execute("SELECT id, value FROM izmir_kutulama_kuru_kg WHERE dayibasi_id = ? ORDER BY id", r['dayibasi_id'])
            r['kuruKgList'] = [{'value': row.value} for row in cursor.fetchall()]
            # Sera yaş kg listesi
            cursor.execute("SELECT id, value FROM izmir_kutulama_sera_yas_kg WHERE dayibasi_id = ? ORDER BY id", r['dayibasi_id'])
            r['seraYasKgList'] = [{'value': row.value} for row in cursor.fetchall()]
            r['toplamKuruKg'] = sum([kg['value'] or 0 for kg in r['kuruKgList']])
            r['toplamYasKg'] = sum([kg['value'] or 0 for kg in r['seraYasKgList']])
            r['yasKuruOrani'] = r['toplamKuruKg'] > 0 and (r['toplamYasKg'] / r['toplamKuruKg']) or 0
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/izmir_kutulama/dayibasi', methods=['POST'])
def add_izmir_kutulama_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400
    sql_check = "SELECT id FROM izmir_kutulama_dayibasi_table WHERE dayibasi = ? AND tarih = ?"
    sql_insert = "INSERT INTO izmir_kutulama_dayibasi_table (tarih, dayibasi) VALUES (?, ?)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['dayibasi'], data['tarih']))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'message': 'Bu dayıbaşı ve tarihe ait kayıt zaten var.'}), 409
        cursor.execute(sql_insert, (data['tarih'], data['dayibasi']))
        conn.commit()
        return jsonify({'message': 'Dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/izmir_kutulama/kuru_kg', methods=['POST'])
def add_izmir_kutulama_kuru_kg():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    value = data.get('value')
    if not dayibasi_id or value is None:
        return jsonify({'message': 'dayibasi_id ve value zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO izmir_kutulama_kuru_kg (dayibasi_id, value) VALUES (?, ?)", (dayibasi_id, value))
        conn.commit()
        return jsonify({'message': 'Kuru kg başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/izmir_kutulama/sera_yas_kg', methods=['POST'])
def add_izmir_kutulama_sera_yas_kg():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    value = data.get('value')
    if not dayibasi_id or value is None:
        return jsonify({'message': 'dayibasi_id ve value zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO izmir_kutulama_sera_yas_kg (dayibasi_id, value) VALUES (?, ?)", (dayibasi_id, value))
        conn.commit()
        return jsonify({'message': 'Sera yaş kg başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

#------------------------------------------------------------------------------------------------------------
#--scv jtı dizim api endpointleri-------------------------------------------------
@app.route('/api/jti_scv_dizim/summary', methods=['GET'])
def get_jti_scv_dizim_summary():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi,
                g.id as gunluk_id,
                g.diziAdedi,
                g.yazici_adi,
                (SELECT COUNT(a.id) FROM jti_scv_dizim_agirlik a WHERE a.dayibasi_id = d.id) as girilenAgirlikSayisi,
                (SELECT AVG(a.agirlik) FROM jti_scv_dizim_agirlik a WHERE a.dayibasi_id = d.id) as ortalamaAgirlik
            FROM jti_scv_dizim_dayibasi_table d
            LEFT JOIN jti_scv_dizim_gunluk g ON d.id = g.dayibasi_id
            ORDER BY d.tarih DESC, d.dayibasi
        ''')
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            if r['ortalamaAgirlik'] and r['diziAdedi']:
                r['toplamTahminiKg'] = r['ortalamaAgirlik'] * r['diziAdedi']
            else:
                r['toplamTahminiKg'] = 0
            # İlk 10 agirlik ve yaprakSayisi
            cursor.execute("SELECT id, agirlik FROM jti_scv_dizim_agirlik WHERE dayibasi_id = ? ORDER BY id LIMIT 10", (r['dayibasi_id'],))
            agirliklar = cursor.fetchall()
            agirlikDetails = []
            for agirlik_row in agirliklar:
                agirlik_id, agirlik = agirlik_row
                cursor.execute("SELECT yaprakSayisi FROM jti_scv_dizim_yaprak WHERE agirlik_id = ? ORDER BY id DESC LIMIT 1", (agirlik_id,))
                yaprak = cursor.fetchone()
                agirlikDetails.append({
                    'agirlik': agirlik,
                    'yaprakSayisi': yaprak[0] if yaprak else None
                })
            r['agirlikDetails'] = agirlikDetails
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_dizim/dayibasi', methods=['POST'])
def add_jti_scv_dizim_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400
    sql_check = "SELECT id FROM jti_scv_dizim_dayibasi_table WHERE dayibasi = ? AND tarih = ?"
    sql_insert = "INSERT INTO jti_scv_dizim_dayibasi_table (tarih, dayibasi) VALUES (?, ?)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['dayibasi'], data['tarih']))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'message': 'Bu dayıbaşı ve tarihe ait kayıt zaten var.'}), 409
        cursor.execute(sql_insert, (data['tarih'], data['dayibasi']))
        conn.commit()
        return jsonify({'message': 'Dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_dizim/agirlik', methods=['POST'])
def add_jti_scv_dizim_agirlik():
    data = request.get_json()
    agirlik = data.get('agirlik')
    dayibasi_id = data.get('dayibasi_id')
    yazici_adi = data.get('yazici_adi')
    if not agirlik or not dayibasi_id:
        return jsonify({'message': 'dayibasi_id ve agirlik zorunludur.'}), 400
    try:
        dayibasi_id = int(dayibasi_id)
        agirlik = float(agirlik)
    except (ValueError, TypeError):
        return jsonify({'message': 'dayibasi_id integer, agirlik float olmalıdır.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO jti_scv_dizim_agirlik (dayibasi_id, agirlik, yazici_adi) VALUES (?, ?, ?)", (dayibasi_id, agirlik, yazici_adi))
        conn.commit()
        return jsonify({'message': 'Ağırlık başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_dizim/agirlik/details', methods=['GET'])
def get_jti_scv_dizim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    sql = "SELECT id, agirlik, yazici_adi, created_at FROM jti_scv_dizim_agirlik WHERE dayibasi_id = ? ORDER BY id"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (dayibasi_id,))
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            cursor.execute("SELECT id, yaprakSayisi FROM jti_scv_dizim_yaprak WHERE agirlik_id = ? ORDER BY id DESC LIMIT 1", (row_dict['id'],))
            yaprak = cursor.fetchone()
            if yaprak:
                row_dict['yaprakSayisi'] = yaprak[1]
                row_dict['yaprakId'] = yaprak[0]
            else:
                row_dict['yaprakSayisi'] = None
                row_dict['yaprakId'] = None
            results.append(row_dict)
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_dizim/gunluk', methods=['POST'])
def add_or_update_jti_scv_dizim_gunluk():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    diziAdedi = data.get('bohcaSayisi')  # frontend 'bohcaSayisi' gönderiyor, burada diziAdedi olarak kaydediyoruz
    if not dayibasi_id or diziAdedi is None:
        return jsonify({'message': 'dayibasi_id ve diziAdedi zorunludur.'}), 400
    
    # Veri tipi dönüşümleri
    try:
        dayibasi_id = int(dayibasi_id)
        diziAdedi = int(diziAdedi)
    except (ValueError, TypeError):
        return jsonify({'message': 'dayibasi_id ve diziAdedi integer olmalıdır.'}), 400
    
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Kayıt var mı kontrol et
        cursor.execute("SELECT id FROM jti_scv_dizim_gunluk WHERE dayibasi_id = ?", (dayibasi_id,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE jti_scv_dizim_gunluk SET diziAdedi = ?, yazici_adi = ? WHERE id = ?", (diziAdedi, data['yazici_adi'], existing[0]))
            conn.commit()
            return jsonify({'message': 'Dizi adedi güncellendi.'}), 200
        else:
            cursor.execute("INSERT INTO jti_scv_dizim_gunluk (dayibasi_id, diziAdedi, yazici_adi) VALUES (?, ?, ?)", (dayibasi_id, diziAdedi, data['yazici_adi']))
            conn.commit()
            return jsonify({'message': 'Dizi adedi eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()


#-- scv jtı kutulama api endpointleri-----
#-- scv jtı kutulama api endpointleri-----

@app.route('/api/jti_scv_kutulama/summary', methods=['GET'])
def get_jti_scv_kutulama_summary():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi
            FROM jti_scv_kutulama_dayibasi_table d
            ORDER BY d.tarih DESC, d.dayibasi
        ''')
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            cursor.execute("SELECT id, value FROM jti_scv_kutulama_kuru_kg WHERE dayibasi_id = ? ORDER BY id", r['dayibasi_id'])
            r['kuruKgList'] = [{'value': row.value} for row in cursor.fetchall()]
            cursor.execute("SELECT id, value FROM jti_scv_kutulama_sera_yas_kg WHERE dayibasi_id = ? ORDER BY id", r['dayibasi_id'])
            r['seraYasKgList'] = [{'value': row.value} for row in cursor.fetchall()]
            r['toplamKuruKg'] = sum([kg['value'] or 0 for kg in r['kuruKgList']])
            r['toplamYasKg'] = sum([kg['value'] or 0 for kg in r['seraYasKgList']])
            r['yasKuruOrani'] = r['toplamKuruKg'] > 0 and (r['toplamYasKg'] / r['toplamKuruKg']) or 0
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_kutulama/dayibasi', methods=['POST'])
def add_jti_scv_kutulama_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400
    sql_check = "SELECT id FROM jti_scv_kutulama_dayibasi_table WHERE dayibasi = ? AND tarih = ?"
    sql_insert = "INSERT INTO jti_scv_kutulama_dayibasi_table (tarih, dayibasi) VALUES (?, ?)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['dayibasi'], data['tarih']))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'message': 'Bu dayıbaşı ve tarihe ait kayıt zaten var.'}), 409
        cursor.execute(sql_insert, (data['tarih'], data['dayibasi']))
        conn.commit()
        return jsonify({'message': 'Dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_kutulama/kuru_kg', methods=['POST'])
def add_jti_scv_kutulama_kuru_kg():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    value = data.get('value')
    if not dayibasi_id or value is None:
        return jsonify({'message': 'dayibasi_id ve value zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO jti_scv_kutulama_kuru_kg (dayibasi_id, value) VALUES (?, ?)", (dayibasi_id, value))
        conn.commit()
        return jsonify({'message': 'Kuru kg başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_kutulama/sera_yas_kg', methods=['POST'])
def add_jti_scv_kutulama_sera_yas_kg():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    value = data.get('value')
    if not dayibasi_id or value is None:
        return jsonify({'message': 'dayibasi_id ve value zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO jti_scv_kutulama_sera_yas_kg (dayibasi_id, value) VALUES (?, ?)", (dayibasi_id, value))
        conn.commit()
        return jsonify({'message': 'Sera yaş kg başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

#------------------------------------------------------------------------------------------------------------

#--scv pmı dizim api endpointleri----
@app.route('/api/pmi_scv_dizim/summary', methods=['GET'])
def get_pmi_scv_dizim_summary():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi,
                g.id as gunluk_id,
                g.diziAdedi,
                g.yazici_adi,
                (SELECT COUNT(a.id) FROM pmi_scv_dizim_agirlik a WHERE a.dayibasi_id = d.id) as girilenAgirlikSayisi,
                (SELECT AVG(a.agirlik) FROM pmi_scv_dizim_agirlik a WHERE a.dayibasi_id = d.id) as ortalamaAgirlik
            FROM pmi_scv_dizim_dayibasi_table d
            LEFT JOIN pmi_scv_dizim_gunluk g ON d.id = g.dayibasi_id
            ORDER BY d.tarih DESC, d.dayibasi
        ''')
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            if r['ortalamaAgirlik'] and r['diziAdedi']:
                r['toplamTahminiKg'] = r['ortalamaAgirlik'] * r['diziAdedi']
            else:
                r['toplamTahminiKg'] = 0
            # İlk 10 agirlik ve yaprakSayisi
            cursor.execute("SELECT id, agirlik FROM pmi_scv_dizim_agirlik WHERE dayibasi_id = ? ORDER BY id LIMIT 10", (r['dayibasi_id'],))
            agirliklar = cursor.fetchall()
            agirlikDetails = []
            for agirlik_row in agirliklar:
                agirlik_id, agirlik = agirlik_row
                cursor.execute("SELECT yaprakSayisi FROM pmi_scv_dizim_yaprak WHERE agirlik_id = ? ORDER BY id DESC LIMIT 1", (agirlik_id,))
                yaprak = cursor.fetchone()
                agirlikDetails.append({
                    'agirlik': agirlik,
                    'yaprakSayisi': yaprak[0] if yaprak else None
                })
            r['agirlikDetails'] = agirlikDetails
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_dizim/dayibasi', methods=['POST'])
def add_pmi_scv_dizim_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400
    sql_check = "SELECT id FROM pmi_scv_dizim_dayibasi_table WHERE dayibasi = ? AND tarih = ?"
    sql_insert = "INSERT INTO pmi_scv_dizim_dayibasi_table (tarih, dayibasi) VALUES (?, ?)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['dayibasi'], data['tarih']))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'message': 'Bu dayıbaşı ve tarihe ait kayıt zaten var.'}), 409
        cursor.execute(sql_insert, (data['tarih'], data['dayibasi']))
        conn.commit()
        return jsonify({'message': 'Dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_dizim/agirlik', methods=['POST'])
def add_pmi_scv_dizim_agirlik():
    data = request.get_json()
    agirlik = data.get('agirlik')
    dayibasi_id = data.get('dayibasi_id')
    yazici_adi = data.get('yazici_adi')
    if not agirlik or not dayibasi_id:
        return jsonify({'message': 'dayibasi_id ve agirlik zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (dayibasi_id, agirlik, yazici_adi) VALUES (?, ?, ?)", (dayibasi_id, agirlik, yazici_adi))
        conn.commit()
        return jsonify({'message': 'Ağırlık başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_dizim/agirlik/details', methods=['GET'])
def get_pmi_scv_dizim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    sql = "SELECT id, agirlik, yazici_adi, created_at FROM pmi_scv_dizim_agirlik WHERE dayibasi_id = ? ORDER BY id"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (dayibasi_id,))
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            cursor.execute("SELECT id, yaprakSayisi FROM pmi_scv_dizim_yaprak WHERE agirlik_id = ? ORDER BY id DESC LIMIT 1", (row_dict['id'],))
            yaprak = cursor.fetchone()
            if yaprak:
                row_dict['yaprakSayisi'] = yaprak[1]
                row_dict['yaprakId'] = yaprak[0]
            else:
                row_dict['yaprakSayisi'] = None
                row_dict['yaprakId'] = None
            results.append(row_dict)
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_dizim/gunluk', methods=['POST'])
def add_or_update_pmi_scv_dizim_gunluk():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    diziAdedi = data.get('bohcaSayisi')  # frontend 'bohcaSayisi' gönderiyor, burada diziAdedi olarak kaydediyoruz
    if not dayibasi_id or diziAdedi is None:
        return jsonify({'message': 'dayibasi_id ve diziAdedi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM pmi_scv_dizim_gunluk WHERE dayibasi_id = ?", dayibasi_id)
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE pmi_scv_dizim_gunluk SET diziAdedi = ?, yazici_adi = ? WHERE id = ?", (diziAdedi, data['yazici_adi'], existing.id))
            conn.commit()
            return jsonify({'message': 'Dizi adedi güncellendi.'}), 200
        else:
            cursor.execute("INSERT INTO pmi_scv_dizim_gunluk (dayibasi_id, diziAdedi, yazici_adi) VALUES (?, ?, ?)", (dayibasi_id, diziAdedi, data['yazici_adi']))
            conn.commit()
            return jsonify({'message': 'Dizi adedi eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

#--scv pmı kutulama api endpointleri------
#--scv pmı kutulama api endpointleri------

@app.route('/api/pmi_scv_kutulama/summary', methods=['GET'])
def get_pmi_scv_kutulama_summary():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi
            FROM pmi_scv_kutulama_dayibasi_table d
            ORDER BY d.tarih DESC, d.dayibasi
        ''')
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            cursor.execute("SELECT id, value FROM pmi_scv_kutulama_kuru_kg WHERE dayibasi_id = ? ORDER BY id", r['dayibasi_id'])
            r['kuruKgList'] = [{'value': row.value} for row in cursor.fetchall()]
            cursor.execute("SELECT id, value FROM pmi_scv_kutulama_sera_yas_kg WHERE dayibasi_id = ? ORDER BY id", r['dayibasi_id'])
            r['seraYasKgList'] = [{'value': row.value} for row in cursor.fetchall()]
            r['toplamKuruKg'] = sum([kg['value'] or 0 for kg in r['kuruKgList']])
            r['toplamYasKg'] = sum([kg['value'] or 0 for kg in r['seraYasKgList']])
            r['yasKuruOrani'] = r['toplamKuruKg'] > 0 and (r['toplamYasKg'] / r['toplamKuruKg']) or 0
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_kutulama/dayibasi', methods=['POST'])
def add_pmi_scv_kutulama_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400
    sql_check = "SELECT id FROM pmi_scv_kutulama_dayibasi_table WHERE dayibasi = ? AND tarih = ?"
    sql_insert = "INSERT INTO pmi_scv_kutulama_dayibasi_table (tarih, dayibasi) VALUES (?, ?)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['dayibasi'], data['tarih']))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'message': 'Bu dayıbaşı ve tarihe ait kayıt zaten var.'}), 409
        cursor.execute(sql_insert, (data['tarih'], data['dayibasi']))
        conn.commit()
        return jsonify({'message': 'Dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_kutulama/kuru_kg', methods=['POST'])
def add_pmi_scv_kutulama_kuru_kg():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    value = data.get('value')
    if not dayibasi_id or value is None:
        return jsonify({'message': 'dayibasi_id ve value zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pmi_scv_kutulama_kuru_kg (dayibasi_id, value) VALUES (?, ?)", (dayibasi_id, value))
        conn.commit()
        return jsonify({'message': 'Kuru kg başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_kutulama/sera_yas_kg', methods=['POST'])
def add_pmi_scv_kutulama_sera_yas_kg():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    value = data.get('value')
    if not dayibasi_id or value is None:
        return jsonify({'message': 'dayibasi_id ve value zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pmi_scv_kutulama_sera_yas_kg (dayibasi_id, value) VALUES (?, ?)", (dayibasi_id, value))
        conn.commit()
        return jsonify({'message': 'Sera yaş kg başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

#-----------------------------------------------------------------------------------------------------------
#------scv pmi topping dizim api endpointleri----

@app.route('/api/pmi_topping_dizim/summary', methods=['GET'])
def get_pmi_topping_dizim_summary():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi,
                g.id as gunluk_id,
                g.diziAdedi,
                g.yazici_adi,
                (SELECT COUNT(a.id) FROM pmi_topping_dizim_agirlik a WHERE a.dayibasi_id = d.id) as girilenAgirlikSayisi,
                (SELECT AVG(a.agirlik) FROM pmi_topping_dizim_agirlik a WHERE a.dayibasi_id = d.id) as ortalamaAgirlik
            FROM pmi_topping_dizim_dayibasi_table d
            LEFT JOIN pmi_topping_dizim_gunluk g ON d.id = g.dayibasi_id
            ORDER BY d.tarih DESC, d.dayibasi
        ''')
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            if r['ortalamaAgirlik'] and r['diziAdedi']:
                r['toplamTahminiKg'] = r['ortalamaAgirlik'] * r['diziAdedi']
            else:
                r['toplamTahminiKg'] = 0
            # İlk 10 agirlik ve yaprakSayisi
            cursor.execute("SELECT id, agirlik FROM pmi_topping_dizim_agirlik WHERE dayibasi_id = ? ORDER BY id LIMIT 10", (r['dayibasi_id'],))
            agirliklar = cursor.fetchall()
            agirlikDetails = []
            for agirlik_row in agirliklar:
                agirlik_id, agirlik = agirlik_row
                cursor.execute("SELECT yaprakSayisi FROM pmi_topping_dizim_yaprak WHERE agirlik_id = ? ORDER BY id DESC LIMIT 1", (agirlik_id,))
                yaprak = cursor.fetchone()
                agirlikDetails.append({
                    'agirlik': agirlik,
                    'yaprakSayisi': yaprak[0] if yaprak else None
                })
            r['agirlikDetails'] = agirlikDetails
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_dizim/dayibasi', methods=['POST'])
def add_pmi_topping_dizim_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400
    sql_check = "SELECT id FROM pmi_topping_dizim_dayibasi_table WHERE dayibasi = ? AND tarih = ?"
    sql_insert = "INSERT INTO pmi_topping_dizim_dayibasi_table (tarih, dayibasi) VALUES (?, ?)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['dayibasi'], data['tarih']))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'message': 'Bu dayıbaşı ve tarihe ait kayıt zaten var.'}), 409
        cursor.execute(sql_insert, (data['tarih'], data['dayibasi']))
        conn.commit()
        return jsonify({'message': 'Dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_dizim/agirlik', methods=['POST'])
def add_pmi_topping_dizim_agirlik():
    data = request.get_json()
    agirlik = data.get('agirlik')
    dayibasi_id = data.get('dayibasi_id')
    yazici_adi = data.get('yazici_adi')
    if not agirlik or not dayibasi_id:
        return jsonify({'message': 'dayibasi_id ve agirlik zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pmi_topping_dizim_agirlik (dayibasi_id, agirlik, yazici_adi) VALUES (?, ?, ?)", (dayibasi_id, agirlik, yazici_adi))
        conn.commit()
        return jsonify({'message': 'Ağırlık başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_dizim/agirlik/details', methods=['GET'])
def get_pmi_topping_dizim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    sql = "SELECT id, agirlik,yazici_adi, created_at FROM pmi_topping_dizim_agirlik WHERE dayibasi_id = ? ORDER BY id"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (dayibasi_id,))
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            cursor.execute("SELECT id, yaprakSayisi FROM pmi_topping_dizim_yaprak WHERE agirlik_id = ? ORDER BY id DESC LIMIT 1", (row_dict['id'],))
            yaprak = cursor.fetchone()
            if yaprak:
                row_dict['yaprakSayisi'] = yaprak[1]
                row_dict['yaprakId'] = yaprak[0]
            else:
                row_dict['yaprakSayisi'] = None
                row_dict['yaprakId'] = None
            results.append(row_dict)
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_dizim/gunluk', methods=['POST'])
def add_or_update_pmi_topping_dizim_gunluk():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    diziAdedi = data.get('bohcaSayisi')  # frontend 'bohcaSayisi' gönderiyor, burada diziAdedi olarak kaydediyoruz
    if not dayibasi_id or diziAdedi is None:
        return jsonify({'message': 'dayibasi_id ve diziAdedi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM pmi_topping_dizim_gunluk WHERE dayibasi_id = ?", (dayibasi_id,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE pmi_topping_dizim_gunluk SET diziAdedi = ?, yazici_adi = ? WHERE id = ?", (diziAdedi, data['yazici_adi'], existing[0]))
            conn.commit()
            return jsonify({'message': 'Dizi adedi güncellendi.'}), 200
        else:
            cursor.execute("INSERT INTO pmi_topping_dizim_gunluk (dayibasi_id, diziAdedi, yazici_adi) VALUES (?, ?, ?)", (dayibasi_id, diziAdedi, data['yazici_adi']))
            conn.commit()
            return jsonify({'message': 'Dizi adedi eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

#----- scv pmi topping kutulama api endpointleri---------

@app.route('/api/pmi_topping_kutulama/summary', methods=['GET'])
def get_pmi_topping_kutulama_summary():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi
            FROM pmi_topping_kutulama_dayibasi_table d
            ORDER BY d.tarih DESC, d.dayibasi
        ''')
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            cursor.execute("SELECT id, value FROM pmi_topping_kutulama_kuru_kg WHERE dayibasi_id = ? ORDER BY id", r['dayibasi_id'])
            r['kuruKgList'] = [{'value': row.value} for row in cursor.fetchall()]
            cursor.execute("SELECT id, value FROM pmi_topping_kutulama_sera_yas_kg WHERE dayibasi_id = ? ORDER BY id", r['dayibasi_id'])
            r['seraYasKgList'] = [{'value': row.value} for row in cursor.fetchall()]
            r['toplamKuruKg'] = sum([kg['value'] or 0 for kg in r['kuruKgList']])
            r['toplamYasKg'] = sum([kg['value'] or 0 for kg in r['seraYasKgList']])
            r['yasKuruOrani'] = r['toplamKuruKg'] > 0 and (r['toplamYasKg'] / r['toplamKuruKg']) or 0
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_kutulama/dayibasi', methods=['POST'])
def add_pmi_topping_kutulama_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400
    sql_check = "SELECT id FROM pmi_topping_kutulama_dayibasi_table WHERE dayibasi = ? AND tarih = ?"
    sql_insert = "INSERT INTO pmi_topping_kutulama_dayibasi_table (tarih, dayibasi) VALUES (?, ?)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['dayibasi'], data['tarih']))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'message': 'Bu dayıbaşı ve tarihe ait kayıt zaten var.'}), 409
        cursor.execute(sql_insert, (data['tarih'], data['dayibasi']))
        conn.commit()
        return jsonify({'message': 'Dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_kutulama/kuru_kg', methods=['POST'])
def add_pmi_topping_kutulama_kuru_kg():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    value = data.get('value')
    if not dayibasi_id or value is None:
        return jsonify({'message': 'dayibasi_id ve value zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pmi_topping_kutulama_kuru_kg (dayibasi_id, value) VALUES (?, ?)", (dayibasi_id, value))
        conn.commit()
        return jsonify({'message': 'Kuru kg başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_kutulama/sera_yas_kg', methods=['POST'])
def add_pmi_topping_kutulama_sera_yas_kg():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    value = data.get('value')
    if not dayibasi_id or value is None:
        return jsonify({'message': 'dayibasi_id ve value zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pmi_topping_kutulama_sera_yas_kg (dayibasi_id, value) VALUES (?, ?)", (dayibasi_id, value))
        conn.commit()
        return jsonify({'message': 'Sera yaş kg başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()
#-----------------------------------------------------------------------------------------------------------
# Test endpoint'i
@app.route('/api/test-connection', methods=['GET'])
def test_db_connection():
    """Veritabanı bağlantısını test etmek için endpoint"""
    if test_connection():
        return jsonify({'message': 'Veritabanı bağlantısı başarılı!'}), 200
    else:
        return jsonify({'message': 'Veritabanı bağlantısı başarısız!'}), 500

@app.route('/api/jti_scv_kirim/test', methods=['GET'])
def test_jti_scv_kirim_tables():
    """JTI SCV KIRIM tablolarını test etmek için endpoint"""
    conn = get_db_connection()
    if not conn: 
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Dayıbaşı tablosundaki kayıtları kontrol et
        cursor.execute("SELECT id, tarih, dayibasi FROM jti_scv_kirim_dayibasi_table ORDER BY id")
        dayibasi_records = []
        for row in cursor.fetchall():
            dayibasi_records.append({
                'id': row.id,
                'tarih': str(row.tarih),
                'dayibasi': row.dayibasi
            })
        
        # Günlük tablosundaki kayıtları kontrol et
        cursor.execute("SELECT id, dayibasi_id, bohcaSayisi FROM jti_scv_kirim_gunluk ORDER BY id")
        gunluk_records = []
        for row in cursor.fetchall():
            gunluk_records.append({
                'id': row.id,
                'dayibasi_id': row.dayibasi_id,
                'bohcaSayisi': row.bohcaSayisi
            })
        
        # Ağırlık tablosundaki kayıtları kontrol et
        cursor.execute("SELECT id, dayibasi_id, agirlik FROM jti_scv_kirim_agirlik ORDER BY id")
        agirlik_records = []
        for row in cursor.fetchall():
            agirlik_records.append({
                'id': row.id,
                'dayibasi_id': row.dayibasi_id,
                'agirlik': row.agirlik
            })
        
        return jsonify({
            'dayibasi_records': dayibasi_records,
            'gunluk_records': gunluk_records,
            'agirlik_records': agirlik_records,
            'message': 'Test başarılı'
        })
        
    except Exception as e:
        print(f"Test hatası: {e}")
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

# --- SCV Sera API Endpointleri ---
#-----------------------------------------------------------------------------------------------------
@app.route('/api/scv_sera', methods=['POST'])
def add_scv_sera():
    data = request.get_json()
    required_fields = ['sera_yeri', 'alan', 'sera_no', 'dizi_sayisi', 'dizi_kg1', 'dizi_kg2', 'dizi_kg3', 'dizi_kg4', 'dizi_kg5', 'dizi_kg6']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO scv_sera (
            sera_yeri, alan, sera_no, dizi_sayisi, dizi_kg1, dizi_kg2, dizi_kg3, dizi_kg4, dizi_kg5, dizi_kg6,
            el_grubu, soldurma_giris_tarihi, soldurma_bitis_tarihi
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data['sera_yeri'], data['alan'], data['sera_no'], data['dizi_sayisi'],
            data['dizi_kg1'], data['dizi_kg2'], data['dizi_kg3'], data['dizi_kg4'], data['dizi_kg5'], data['dizi_kg6'],
            data.get('el_grubu'), data.get('soldurma_giris_tarihi'), data.get('soldurma_bitis_tarihi')
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Sera başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/scv_sera', methods=['GET'])
def get_scv_seralar():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scv_sera ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/scv_sera/yerler', methods=['GET'])
def get_scv_sera_yerleri():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Hem scv_sera tablosundan hem de scv_sera_yerleri tablosundan sera yerlerini al
        cursor.execute("""
            SELECT DISTINCT sera_yeri 
            FROM (
                SELECT sera_yeri FROM scv_sera
                UNION
                SELECT sera_yeri FROM scv_sera_yerleri
            ) combined_yerler
            ORDER BY sera_yeri
        """)
        yerler = [row[0] for row in cursor.fetchall()]
        return jsonify(yerler)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/scv_sera/nolar', methods=['GET'])
def get_scv_sera_nolar():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT sera_no FROM scv_sera ORDER BY sera_no")
        nolar = [row[0] for row in cursor.fetchall()]
        return jsonify(nolar)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

# --- SCV Sera Yerleri Yönetimi ---
@app.route('/api/scv_sera_yerleri', methods=['POST'])
def add_scv_sera_yeri():
    data = request.get_json()
    sera_yeri = data.get('sera_yeri')
    toplam_sera_sayisi = data.get('toplam_sera_sayisi')
    
    if not sera_yeri or not toplam_sera_sayisi:
        return jsonify({'message': 'Sera yeri ve toplam sera sayısı gerekli.'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO scv_sera_yerleri (sera_yeri, toplam_sera_sayisi) VALUES (?, ?)", (sera_yeri, toplam_sera_sayisi))
        conn.commit()
        return jsonify({'message': 'Sera yeri başarıyla eklendi.'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Bu sera yeri zaten mevcut.'}), 409
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/scv_sera_yerleri', methods=['GET'])
def get_scv_sera_yerleri_detay():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sy.sera_yeri, sy.toplam_sera_sayisi, 
                   COUNT(s.id) as mevcut_sera_sayisi
            FROM scv_sera_yerleri sy
            LEFT JOIN scv_sera s ON sy.sera_yeri = s.sera_yeri
            GROUP BY sy.sera_yeri, sy.toplam_sera_sayisi
            ORDER BY sy.sera_yeri
        """)
        
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

# --- SCV Kutulama API Endpointleri ---
#-----------------------------------------------------------------------------------------------------
@app.route('/api/scv_kutulama', methods=['POST'])
def add_scv_kutulama():
    data = request.get_json()
    required_fields = ['tarih', 'dayibasi', 'sera_yeri', 'sera_no', 'sera_yas_kg', 'kutular', 'toplam_kuru_kg', 'yas_kuru_orani', 'alan']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO scv_kutulama (tarih, dayibasi, sera_yeri, sera_no, sera_yas_kg, kutular, toplam_kuru_kg, yas_kuru_orani, alan, yazici_adi, sera_bosaltildi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data['tarih'], data['dayibasi'], data['sera_yeri'], data['sera_no'], 
            data['sera_yas_kg'], data['kutular'], data['toplam_kuru_kg'], data['yas_kuru_orani'],
            data.get('alan'), data.get('yazici_adi'), data.get('sera_bosaltildi', 'hayir')
        )
        cursor.execute(sql, params)
        # Eğer sera boşaltıldıysa, scv_sera tablosunda dizi_sayisi=0 ve bosaltma_tarihi güncellenmeli
        if data.get('sera_bosaltildi') == 'evet':
            from datetime import datetime
            cursor.execute(
                "UPDATE scv_sera SET dizi_sayisi = 0, bosaltma_tarihi = ? WHERE sera_yeri = ? AND sera_no = ?",
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), data['sera_yeri'], data['sera_no'])
            )
        conn.commit()
        return jsonify({'message': 'Kutulama kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/scv_kutulama', methods=['GET'])
def get_scv_kutulama():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scv_kutulama ORDER BY tarih DESC, id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/scv_kutulama/tarih/<tarih>', methods=['GET'])
def get_scv_kutulama_by_date(tarih):
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM scv_kutulama WHERE tarih = ? ORDER BY id DESC", tarih)
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

# --- Sera Boşaltma Endpoint ---
@app.route('/api/scv_sera/bosalt', methods=['POST'])
def bosalt_scv_sera():
    data = request.json
    sera_id = data.get('id')
    tarih = data.get('tarih') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if not sera_id:
        return jsonify({'error': 'Sera id gerekli'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Veritabanı bağlantı hatası'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE scv_sera
            SET dizi_sayisi=0, bosaltma_tarihi=?
            WHERE id=?
        """, (tarih, sera_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'id': sera_id, 'bosaltma_tarihi': tarih})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- İzmir Sera CRUD ---
@app.route('/api/izmir_sera', methods=['POST'])
def add_izmir_sera():
    data = request.json
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Veritabanı bağlantı hatası'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO izmir_sera (sera_yeri, sera_no, dizi_sayisi, dizi_kg1, dizi_kg2, dizi_kg3, dizi_kg4, dizi_kg5, dizi_kg6)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('sera_yeri'),
            data.get('sera_no'),
            data.get('dizi_sayisi'),
            data.get('dizi_kg1'),
            data.get('dizi_kg2'),
            data.get('dizi_kg3'),
            data.get('dizi_kg4'),
            data.get('dizi_kg5'),
            data.get('dizi_kg6')
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/izmir_sera', methods=['GET'])
def get_izmir_seralar():
    conn = get_db_connection()
    if not conn:
        return jsonify([])
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM izmir_sera')
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(results)

@app.route('/api/izmir_sera/yerler', methods=['GET'])
def get_izmir_sera_yerleri():
    conn = get_db_connection()
    if not conn:
        return jsonify([])
    try:
        cursor = conn.cursor()
        # Hem izmir_sera tablosundan hem de izmir_sera_yerleri tablosundan sera yerlerini al
        cursor.execute("""
            SELECT DISTINCT sera_yeri 
            FROM (
                SELECT sera_yeri FROM izmir_sera
                UNION
                SELECT sera_yeri FROM izmir_sera_yerleri
            ) combined_yerler
            ORDER BY sera_yeri
        """)
        yerler = [row[0] for row in cursor.fetchall()]
        return jsonify(yerler)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/izmir_sera/nolar', methods=['GET'])
def get_izmir_sera_nolar():
    conn = get_db_connection()
    if not conn:
        return jsonify([])
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT sera_no FROM izmir_sera')
    nolar = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(nolar)

# --- İzmir Sera Yerleri Yönetimi ---
@app.route('/api/izmir_sera_yerleri', methods=['POST'])
def add_izmir_sera_yeri():
    data = request.get_json()
    sera_yeri = data.get('sera_yeri')
    toplam_sera_sayisi = data.get('toplam_sera_sayisi')
    
    if not sera_yeri or not toplam_sera_sayisi:
        return jsonify({'message': 'Sera yeri ve toplam sera sayısı gerekli.'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO izmir_sera_yerleri (sera_yeri, toplam_sera_sayisi) VALUES (?, ?)", 
                      (sera_yeri, toplam_sera_sayisi))
        conn.commit()
        return jsonify({'message': 'Sera yeri başarıyla eklendi.'}), 201
    except sqlite3.IntegrityError:
        return jsonify({'message': 'Bu sera yeri zaten mevcut.'}), 409
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/izmir_sera_yerleri', methods=['GET'])
def get_izmir_sera_yerleri_detay():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sy.sera_yeri, sy.toplam_sera_sayisi, 
                   COUNT(s.id) as mevcut_sera_sayisi
            FROM izmir_sera_yerleri sy
            LEFT JOIN izmir_sera s ON sy.sera_yeri = s.sera_yeri
            GROUP BY sy.sera_yeri, sy.toplam_sera_sayisi
            ORDER BY sy.sera_yeri
        """)
        
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

# --- İzmir Sera Boşaltma ---
@app.route('/api/izmir_sera/bosalt', methods=['POST'])
def bosalt_izmir_sera():
    data = request.json
    sera_id = data.get('id')
    tarih = data.get('tarih') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if not sera_id:
        return jsonify({'error': 'Sera id gerekli'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Veritabanı bağlantı hatası'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE izmir_sera
            SET dizi_sayisi=0, bosaltma_tarihi=?
            WHERE id=?
        """, (tarih, sera_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'id': sera_id, 'bosaltma_tarihi': tarih})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- İzmir Kutulama CRUD ---
@app.route('/api/izmir_kutulama', methods=['POST'])
def add_izmir_kutulama():
    data = request.json
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Veritabanı bağlantı hatası'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO izmir_kutulama (tarih, dayibasi, sera_yeri, sera_no, sera_yas_kg, kutular, toplam_kuru_kg, yas_kuru_orani, yazici_adi, sera_bosaltildi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('tarih'),
            data.get('dayibasi'),
            data.get('sera_yeri'),
            data.get('sera_no'),
            data.get('sera_yas_kg'),
            data.get('kutular'),
            data.get('toplam_kuru_kg'),
            data.get('yas_kuru_orani'),
            data.get('yazici_adi'),
            data.get('sera_bosaltildi', 'hayir')
        ))
        # Eğer sera_bosaltildi == 'evet' ise izmir_sera tablosunda dizi_sayisi=0, bosaltma_tarihi ve sera_bosaltildi güncellenmeli
        if data.get('sera_bosaltildi') == 'evet':
            from datetime import datetime
            cursor.execute(
                "UPDATE izmir_sera SET dizi_sayisi = 0, bosaltma_tarihi = ?, sera_bosaltildi = 'evet' WHERE sera_yeri = ? AND sera_no = ?",
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), data.get('sera_yeri'), data.get('sera_no'))
            )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/izmir_kutulama', methods=['GET'])
def get_izmir_kutulama():
    conn = get_db_connection()
    if not conn:
        return jsonify([])
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM izmir_kutulama')
    columns = [column[0] for column in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return jsonify(results)

# Filtre ve form değişkenleri birbirinden bağımsız olmalı
filterSeraYeri: str = ''
selectedSeraYeri: str = ''

# --- SCV Kutulama Summary API Endpoint ---
@app.route('/api/scv_kutulama/summary', methods=['GET'])
def get_scv_kutulama_summary():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT alan, kutular, toplam_kuru_kg FROM scv_kutulama")
        kutulama_kayitlari = cursor.fetchall()
        
        alan_istatistik = {}
        genel_kayit = 0
        genel_kutu_sayisi = 0
        genel_toplam_kg = 0
        
        for row in kutulama_kayitlari:
            alan = (row['alan'] if isinstance(row, dict) else getattr(row, 'alan', None)) or ''
            alan = alan.strip().upper()
            kutular_json = row['kutular'] if isinstance(row, dict) else getattr(row, 'kutular', None)
            toplam_kg = row['toplam_kuru_kg'] if isinstance(row, dict) else getattr(row, 'toplam_kuru_kg', 0) or 0
            try:
                kutular_array = json.loads(kutular_json) if kutular_json else []
                # Kutu sayısı: 0'dan büyük olan kutuların sayısı
                kutu_sayisi = len([k for k in kutular_array if k and k > 0])
            except Exception:
                kutu_sayisi = 0
            if alan not in alan_istatistik:
                alan_istatistik[alan] = {'toplam_kayit': 0, 'toplam_kutu_kg': 0, 'toplam_kutu_sayisi': 0}
            alan_istatistik[alan]['toplam_kayit'] += 1
            alan_istatistik[alan]['toplam_kutu_kg'] += toplam_kg
            alan_istatistik[alan]['toplam_kutu_sayisi'] += kutu_sayisi
            genel_kayit += 1
            genel_kutu_sayisi += kutu_sayisi
            genel_toplam_kg += toplam_kg
        
        # Debug için alan istatistiklerini yazdır
        print(f"Alan istatistikleri: {alan_istatistik}")
        
        # Standart başlıklar
        def get_alan(anahtar):
            for k in alan_istatistik:
                if anahtar in k or anahtar.replace(' ', '-') in k or anahtar.replace('-', ' ') in k:
                    return alan_istatistik[k]
            return {'toplam_kayit': 0, 'toplam_kutu_kg': 0, 'toplam_kutu_sayisi': 0}
        
        return jsonify({
            'pmi_scv': get_alan('PMI SCV'),
            'jti_scv': get_alan('JTI SCV'),
            'pmi_topping': get_alan('PMI TOPPING'),
            'genel': {
                'toplam_kayit': genel_kayit,
                'toplam_kutu_kg': genel_toplam_kg,
                'toplam_kutu_sayisi': genel_kutu_sayisi
            }
        })
    except Exception as e:
        print(f"Kutulama özeti hatası: {e}")
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route("/")
def home():
    return "API çalışıyor!"

def get_genel_stok():
    conn = get_db_connection()
    if not conn:
        return {'kutu': 0, 'kg': 0}
    try:
        cursor = conn.cursor()
        # SCV kutulama
        cursor.execute("SELECT kutular, toplam_kuru_kg FROM scv_kutulama")
        scv_rows = cursor.fetchall()
        scv_kutu = 0
        scv_kg = 0
        for row in scv_rows:
            kutular_json = row['kutular'] if isinstance(row, dict) else getattr(row, 'kutular', None)
            try:
                kutular = json.loads(kutular_json) if kutular_json else []
                scv_kutu += len([k for k in kutular if k and k > 0])
            except Exception:
                pass
            scv_kg += row['toplam_kuru_kg'] if isinstance(row, dict) else getattr(row, 'toplam_kuru_kg', 0) or 0
        # İzmir kutulama
        cursor.execute("SELECT kutular, toplam_kuru_kg FROM izmir_kutulama")
        izmir_rows = cursor.fetchall()
        izmir_kutu = 0
        izmir_kg = 0
        for row in izmir_rows:
            kutular_json = row['kutular'] if isinstance(row, dict) else getattr(row, 'kutular', None)
            try:
                kutular = json.loads(kutular_json) if kutular_json else []
                izmir_kutu += len([k for k in kutular if k and k > 0])
            except Exception:
                pass
            izmir_kg += row['toplam_kuru_kg'] if isinstance(row, dict) else getattr(row, 'toplam_kuru_kg', 0) or 0
        return {'kutu': scv_kutu + izmir_kutu, 'kg': scv_kg + izmir_kg}
    except Exception as e:
        print(f"Genel stok hesaplama hatası: {e}")
        return {'kutu': 0, 'kg': 0}
    finally:
        conn.close()

# Sevkiyat ekleme endpoint örneği (varsa, yoksa ekleyin):
@app.route('/api/sevkiyat', methods=['POST'])
def add_sevkiyat():
    data = request.get_json()
    istenen_kutu = int(data.get('kutu', 0))
    istenen_kg = float(data.get('kg', 0))
    alan = data.get('alan', '').strip().upper()
    stok = None
    genel_stok = None
    # Alan bazında stok kontrolü
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # SCV kutulama
        cursor.execute("SELECT alan, kutular, toplam_kuru_kg FROM scv_kutulama")
        scv_rows = cursor.fetchall()
        alanlar = {}
        for row in scv_rows:
            row_alan = (row['alan'] if isinstance(row, dict) else getattr(row, 'alan', None)) or ''
            row_alan = row_alan.strip().upper()
            kutular_json = row['kutular'] if isinstance(row, dict) else getattr(row, 'kutular', None)
            toplam_kg = row['toplam_kuru_kg'] if isinstance(row, dict) else getattr(row, 'toplam_kuru_kg', 0) or 0
            try:
                kutular_array = json.loads(kutular_json) if kutular_json else []
                kutu_sayisi = len([k for k in kutular_array if k and k > 0])
            except Exception:
                kutu_sayisi = 0
            if row_alan not in alanlar:
                alanlar[row_alan] = {'kutu': 0, 'kg': 0}
            alanlar[row_alan]['kutu'] += kutu_sayisi
            alanlar[row_alan]['kg'] += toplam_kg
        # İzmir kutulama
        cursor.execute("SELECT kutular, toplam_kuru_kg FROM izmir_kutulama")
        izmir_rows = cursor.fetchall()
        izmir_kutu = 0
        izmir_kg = 0
        for row in izmir_rows:
            kutular_json = row['kutular'] if isinstance(row, dict) else getattr(row, 'kutular', None)
            try:
                kutular = json.loads(kutular_json) if kutular_json else []
                izmir_kutu += len([k for k in kutular if k and k > 0])
            except Exception:
                pass
            izmir_kg += row['toplam_kuru_kg'] if isinstance(row, dict) else getattr(row, 'toplam_kuru_kg', 0) or 0
        alanlar['İZMİR'] = {'kutu': izmir_kutu, 'kg': izmir_kg}
        # Alan stokunu bul
        stok = alanlar.get(alan, {'kutu': 0, 'kg': 0})
        genel_stok = {'kutu': sum([v['kutu'] for v in alanlar.values()]), 'kg': sum([v['kg'] for v in alanlar.values()])}
        if istenen_kutu > stok['kutu'] or istenen_kg > stok['kg']:
            return jsonify({'message': f'Stokta bu kadar ürün yok! (Alan: {alan}, Kutu: {stok["kutu"]}, KG: {stok["kg"]})'}), 400
        # Stoktan düşme işlemi (alan bazında)
        # ... (mevcut kodunuzu buraya ekleyin, alan bazında düşme için gerekirse güncelleyin)
        # Sevkiyat kaydını ekle
        cursor.execute("INSERT INTO sevkiyat (tarih, kutu, kg) VALUES (?, ?, ?)", (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), istenen_kutu, istenen_kg))
        conn.commit()
        return jsonify({'message': 'Sevkiyat kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/genel_stok', methods=['GET'])
def genel_stok():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # SCV kutulama
        cursor.execute("SELECT alan, kutular, toplam_kuru_kg FROM scv_kutulama")
        scv_rows = cursor.fetchall()
        alanlar = {}
        for row in scv_rows:
            alan = (row['alan'] if isinstance(row, dict) else getattr(row, 'alan', None)) or ''
            alan = alan.strip().upper()
            kutular_json = row['kutular'] if isinstance(row, dict) else getattr(row, 'kutular', None)
            toplam_kg = row['toplam_kuru_kg'] if isinstance(row, dict) else getattr(row, 'toplam_kuru_kg', 0) or 0
            try:
                kutular_array = json.loads(kutular_json) if kutular_json else []
                kutu_sayisi = len([k for k in kutular_array if k and k > 0])
            except Exception:
                kutu_sayisi = 0
            if alan not in alanlar:
                alanlar[alan] = {'kutu': 0, 'kg': 0}
            alanlar[alan]['kutu'] += kutu_sayisi
            alanlar[alan]['kg'] += toplam_kg
        # İzmir kutulama
        cursor.execute("SELECT kutular, toplam_kuru_kg FROM izmir_kutulama")
        izmir_rows = cursor.fetchall()
        izmir_kutu = 0
        izmir_kg = 0
        for row in izmir_rows:
            kutular_json = row['kutular'] if isinstance(row, dict) else getattr(row, 'kutular', None)
            try:
                kutular = json.loads(kutular_json) if kutular_json else []
                izmir_kutu += len([k for k in kutular if k and k > 0])
            except Exception:
                pass
            izmir_kg += row['toplam_kuru_kg'] if isinstance(row, dict) else getattr(row, 'toplam_kuru_kg', 0) or 0
        alanlar['İZMİR'] = {'kutu': izmir_kutu, 'kg': izmir_kg}
        # Genel toplam
        toplam_kutu = sum([v['kutu'] for v in alanlar.values()])
        toplam_kg = sum([v['kg'] for v in alanlar.values()])
        return jsonify({'alanlar': alanlar, 'genel': {'kutu': toplam_kutu, 'kg': toplam_kg}})
    except Exception as e:
        print(f"Genel stok hesaplama hatası: {e}")
        return jsonify({'kutu': 0, 'kg': 0}), 500
    finally:
        conn.close()

@app.route('/api/sevkiyat/reset', methods=['POST'])
def reset_sevkiyat():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sevkiyat")
        conn.commit()
        return jsonify({'message': 'Tüm sevkiyat kayıtları silindi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/fcv_kirim/agirlik/<int:agirlik_id>', methods=['PUT'])
def update_fcv_kirim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    yazici_adi = data.get('yazici_adi')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE fcv_kirim_agirlik SET agirlik = ?, yazici_adi = ? WHERE id = ?", (agirlik, yazici_adi, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/izmir_kirim/agirlik/<int:agirlik_id>', methods=['PUT'])
def update_izmir_kirim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    yazici_adi = data.get('yazici_adi')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE izmir_kirim_agirlik SET agirlik = ?, yazici_adi = ? WHERE id = ?", (agirlik, yazici_adi, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()



@app.route('/api/pmi_topping_kirim/agirlik/<int:agirlik_id>', methods=['PUT'])
def update_pmi_topping_kirim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    yazici_adi = data.get('yazici_adi')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE pmi_topping_kirim_agirlik SET agirlik = ?, yazici_adi = ? WHERE id = ?", (agirlik, yazici_adi, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/izmir_dizim/agirlik/<int:agirlik_id>', methods=['PUT'])
def update_izmir_dizim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    yazici_adi = data.get('yazici_adi')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE izmir_dizim_agirlik SET agirlik = ?, yazici_adi = ? WHERE id = ?", (agirlik, yazici_adi, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()


@app.route('/api/fcv_kirim/gunluk/<int:gunluk_id>', methods=['PUT'])
def update_fcv_kirim_gunluk(gunluk_id):
    data = request.get_json()
    bohcaSayisi = data.get('bocaSayisi')
    yazici_adi = data.get('yazici_adi')
    if bohcaSayisi is None:
        return jsonify({'message': 'bocaSayisi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE fcv_kirim_gunluk SET bocaSayisi = ?, yazici_adi = ? WHERE id = ?", (bohcaSayisi, yazici_adi, gunluk_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Günlük başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/izmir_kirim/gunluk/<int:gunluk_id>', methods=['PUT'])
def update_izmir_kirim_gunluk(gunluk_id):
    data = request.get_json()
    bohcaSayisi = data.get('bohcaSayisi')
    yazici_adi = data.get('yazici_adi')
    if bohcaSayisi is None:
        return jsonify({'message': 'bohcaSayisi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE izmir_kirim_gunluk SET bohcaSayisi = ?, yazici_adi = ? WHERE id = ?", (bohcaSayisi, yazici_adi, gunluk_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Günlük başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/jti_scv_dizim/gunluk/<int:gunluk_id>', methods=['PUT'])
def update_jti_scv_dizim_gunluk(gunluk_id):
    data = request.get_json()
    diziAdedi = data.get('diziAdedi')
    yazici_adi = data.get('yazici_adi')
    if diziAdedi is None:
        return jsonify({'message': 'diziAdedi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE jti_scv_dizim_gunluk SET diziAdedi = ?, yazici_adi = ? WHERE id = ?", (diziAdedi, yazici_adi, gunluk_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Günlük başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/pmi_scv_dizim/gunluk/<int:gunluk_id>', methods=['PUT'])
def update_pmi_scv_dizim_gunluk(gunluk_id):
    data = request.get_json()
    diziAdedi = data.get('diziAdedi')
    yazici_adi = data.get('yazici_adi')
    if diziAdedi is None:
        return jsonify({'message': 'diziAdedi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE pmi_scv_dizim_gunluk SET diziAdedi = ?, yazici_adi = ? WHERE id = ?", (diziAdedi, yazici_adi, gunluk_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Günlük başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/pmi_topping_dizim/gunluk/<int:gunluk_id>', methods=['PUT'])
def update_pmi_topping_dizim_gunluk(gunluk_id):
    data = request.get_json()
    diziAdedi = data.get('diziAdedi')
    yazici_adi = data.get('yazici_adi')
    if diziAdedi is None:
        return jsonify({'message': 'diziAdedi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE pmi_topping_dizim_gunluk SET diziAdedi = ?, yazici_adi = ? WHERE id = ?", (diziAdedi, yazici_adi, gunluk_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Günlük başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/pmi_scv_dizim/agirlik/<int:agirlik_id>', methods=['PUT'])
def update_pmi_scv_dizim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        if yaprakSayisi is not None:
            cursor.execute("UPDATE pmi_scv_dizim_agirlik SET agirlik = ?, yaprakSayisi = ?, yazici_adi = ? WHERE id = ?", (agirlik, yaprakSayisi, yazici_adi, agirlik_id))
        else:
            cursor.execute("UPDATE pmi_scv_dizim_agirlik SET agirlik = ?, yazici_adi = ? WHERE id = ?", (agirlik, yazici_adi, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/jti_scv_dizim/agirlik/<int:agirlik_id>', methods=['PUT'])
def update_jti_scv_dizim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        if yaprakSayisi is not None:
            cursor.execute("UPDATE jti_scv_dizim_agirlik SET agirlik = ?, yaprakSayisi = ?, yazici_adi = ? WHERE id = ?", (agirlik, yaprakSayisi, yazici_adi, agirlik_id))
        else:
            cursor.execute("UPDATE jti_scv_dizim_agirlik SET agirlik = ?, yazici_adi = ? WHERE id = ?", (agirlik, yazici_adi, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/pmi_topping_dizim/agirlik/<int:agirlik_id>', methods=['PUT'])
def update_pmi_topping_dizim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        if yaprakSayisi is not None:
            cursor.execute("UPDATE pmi_topping_dizim_agirlik SET agirlik = ?, yaprakSayisi = ?, yazici_adi = ? WHERE id = ?", (agirlik, yaprakSayisi, yazici_adi, agirlik_id))
        else:
            cursor.execute("UPDATE pmi_topping_dizim_agirlik SET agirlik = ?, yazici_adi = ? WHERE id = ?", (agirlik, yazici_adi, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/jti_scv_dizim_yaprak', methods=['POST'])
def add_jti_scv_dizim_yaprak():
    data = request.get_json()
    agirlik_id = data.get('agirlik_id')
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    if not agirlik_id or yaprakSayisi is None:
        return jsonify({'message': 'agirlik_id ve yaprakSayisi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO jti_scv_dizim_yaprak (agirlik_id, yaprakSayisi, yazici_adi) VALUES (?, ?, ?)", (agirlik_id, yaprakSayisi, yazici_adi))
        conn.commit()
        return jsonify({'message': 'Yaprak sayısı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/jti_scv_dizim_yaprak/<int:yaprak_id>', methods=['PUT'])
def update_jti_scv_dizim_yaprak(yaprak_id):
    data = request.get_json()
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    if yaprakSayisi is None:
        return jsonify({'message': 'yaprakSayisi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE jti_scv_dizim_yaprak SET yaprakSayisi = ?, yazici_adi = ? WHERE id = ?", (yaprakSayisi, yazici_adi, yaprak_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Yaprak kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Yaprak sayısı başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/pmi_scv_dizim_yaprak', methods=['POST'])
def add_pmi_scv_dizim_yaprak():
    data = request.get_json()
    agirlik_id = data.get('agirlik_id')
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    if not agirlik_id or yaprakSayisi is None:
        return jsonify({'message': 'agirlik_id ve yaprakSayisi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pmi_scv_dizim_yaprak (agirlik_id, yaprakSayisi, yazici_adi) VALUES (?, ?, ?)", (agirlik_id, yaprakSayisi, yazici_adi))
        conn.commit()
        return jsonify({'message': 'Yaprak sayısı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/pmi_scv_dizim_yaprak/<int:yaprak_id>', methods=['PUT'])
def update_pmi_scv_dizim_yaprak(yaprak_id):
    data = request.get_json()
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    if yaprakSayisi is None:
        return jsonify({'message': 'yaprakSayisi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE pmi_scv_dizim_yaprak SET yaprakSayisi = ?, yazici_adi = ? WHERE id = ?", (yaprakSayisi, yazici_adi, yaprak_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Yaprak kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Yaprak sayısı başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/pmi_topping_dizim_yaprak', methods=['POST'])
def add_pmi_topping_dizim_yaprak():
    data = request.get_json()
    agirlik_id = data.get('agirlik_id')
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    if not agirlik_id or yaprakSayisi is None:
        return jsonify({'message': 'agirlik_id ve yaprakSayisi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pmi_topping_dizim_yaprak (agirlik_id, yaprakSayisi, yazici_adi) VALUES (?, ?, ?)", (agirlik_id, yaprakSayisi, yazici_adi))
        conn.commit()
        return jsonify({'message': 'Yaprak sayısı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

@app.route('/api/pmi_topping_dizim_yaprak/<int:yaprak_id>', methods=['PUT'])
def update_pmi_topping_dizim_yaprak(yaprak_id):
    data = request.get_json()
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    if yaprakSayisi is None:
        return jsonify({'message': 'yaprakSayisi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE pmi_topping_dizim_yaprak SET yaprakSayisi = ?, yazici_adi = ? WHERE id = ?", (yaprakSayisi, yazici_adi, yaprak_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Yaprak kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Yaprak sayısı başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        conn.close()

# --- JTI SCV KIRIM yeni sistem için ---
@app.route('/api/traktor_gelis_jti_kirim', methods=['POST'])
def add_traktor_gelis_jti_kirim():
    data = request.get_json()
    required_fields = ['tarih', 'plaka', 'gelis_no']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_jti_kirim (tarih, plaka, gelis_no)
        VALUES (?, ?, ?)
        """
        params = (
            data['tarih'], data['plaka'], data['gelis_no']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Türücü gelis kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_jti_kirim', methods=['GET'])
def get_traktor_gelis_jti_kirim():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_jti_kirim ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_jti_kirim/dayibasi', methods=['POST'])
def add_traktor_gelis_jti_kirim_dayibasi():
    data = request.get_json()
    required_fields = ['traktor_gelis_jti_kirim_id', 'dayibasi_adi', 'bohca_sayisi']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_jti_kirim_dayibasi (traktor_gelis_jti_kirim_id, dayibasi_adi, bohca_sayisi)
        VALUES (?, ?, ?)
        """
        params = (
            data['traktor_gelis_jti_kirim_id'], data['dayibasi_adi'], data['bohca_sayisi']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Türücü gelis dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_jti_kirim_dayibasi', methods=['GET'])
def get_traktor_gelis_jti_kirim_dayibasi():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_jti_kirim_dayibasi ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_jti_kirim_agirlik', methods=['POST'])
def add_traktor_gelis_jti_kirim_agirlik():
    data = request.get_json()
    required_fields = ['traktor_gelis_jti_kirim_id', 'agirlik', 'created_at']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_jti_kirim_agirlik (traktor_gelis_jti_kirim_id, agirlik, created_at)
        VALUES (?, ?, ?)
        """
        params = (
            data['traktor_gelis_jti_kirim_id'], data['agirlik'], data['created_at']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Türücü gelis ağırlık kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_jti_kirim_agirlik', methods=['GET'])
def get_traktor_gelis_jti_kirim_agirlik():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_jti_kirim_agirlik ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_jti_kirim_agirlik/<int:agirlik_id>', methods=['PUT'])
def update_traktor_gelis_jti_kirim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE traktor_gelis_jti_kirim_agirlik SET agirlik = ? WHERE id = ?", (agirlik, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_jti_kirim/summary', methods=['GET'])
def get_traktor_gelis_jti_kirim_summary():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_jti_kirim ORDER BY tarih DESC, plaka, gelis_no DESC")
        kartlar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        for kart in kartlar:
            cursor.execute("SELECT * FROM traktor_gelis_jti_kirim_dayibasi WHERE traktor_gelis_jti_kirim_id = ?", (kart['id'],))
            dayibasilari = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['dayibasilari'] = dayibasilari
            kart['toplam_bohca'] = sum([d['bohca_sayisi'] for d in dayibasilari]) if dayibasilari else 0
            cursor.execute("SELECT id, agirlik, created_at FROM traktor_gelis_jti_kirim_agirlik WHERE traktor_gelis_jti_kirim_id = ? ORDER BY id", (kart['id'],))
            agirliklar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['agirliklar'] = agirliklar
            if agirliklar:
                kart['ortalama_agirlik'] = sum([a['agirlik'] for a in agirliklar]) / len(agirliklar)
            else:
                kart['ortalama_agirlik'] = 0
            kart['toplam_kg'] = kart['toplam_bohca'] * kart['ortalama_agirlik']
        return jsonify(kartlar)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

# --- PMI SCV KIRIM yeni sistem için ---
@app.route('/api/traktor_gelis_pmi_kirim', methods=['POST'])
def add_traktor_gelis_pmi_kirim():
    data = request.get_json()
    required_fields = ['tarih', 'plaka', 'gelis_no']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_pmi_kirim (tarih, plaka, gelis_no)
        VALUES (?, ?, ?)
        """
        params = (
            data['tarih'], data['plaka'], data['gelis_no']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_kirim', methods=['GET'])
def get_traktor_gelis_pmi_kirim():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_pmi_kirim ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_kirim/dayibasi', methods=['POST'])
def add_traktor_gelis_pmi_kirim_dayibasi():
    data = request.get_json()
    required_fields = ['traktor_gelis_pmi_kirim_id', 'dayibasi_adi', 'bohca_sayisi']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_pmi_kirim_dayibasi (traktor_gelis_pmi_kirim_id, dayibasi_adi, bohca_sayisi)
        VALUES (?, ?, ?)
        """
        params = (
            data['traktor_gelis_pmi_kirim_id'], data['dayibasi_adi'], data['bohca_sayisi']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_kirim_dayibasi', methods=['GET'])
def get_traktor_gelis_pmi_kirim_dayibasi():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_pmi_kirim_dayibasi ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_kirim_agirlik', methods=['POST'])
def add_traktor_gelis_pmi_kirim_agirlik():
    data = request.get_json()
    required_fields = ['traktor_gelis_pmi_kirim_id', 'agirlik', 'created_at']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_pmi_kirim_agirlik (traktor_gelis_pmi_kirim_id, agirlik, created_at)
        VALUES (?, ?, ?)
        """
        params = (
            data['traktor_gelis_pmi_kirim_id'], data['agirlik'], data['created_at']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş ağırlık kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_kirim_agirlik', methods=['GET'])
def get_traktor_gelis_pmi_kirim_agirlik():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_pmi_kirim_agirlik ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_kirim_agirlik/<int:agirlik_id>', methods=['PUT'])
def update_traktor_gelis_pmi_kirim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE traktor_gelis_pmi_kirim_agirlik SET agirlik = ? WHERE id = ?", (agirlik, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_kirim/summary', methods=['GET'])
def get_traktor_gelis_pmi_kirim_summary():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_pmi_kirim ORDER BY tarih DESC, plaka, gelis_no DESC")
        kartlar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        for kart in kartlar:
            cursor.execute("SELECT * FROM traktor_gelis_pmi_kirim_dayibasi WHERE traktor_gelis_pmi_kirim_id = ?", (kart['id'],))
            dayibasilari = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['dayibasilari'] = dayibasilari
            kart['toplam_bohca'] = sum([d['bohca_sayisi'] for d in dayibasilari]) if dayibasilari else 0
            cursor.execute("SELECT id, agirlik, created_at FROM traktor_gelis_pmi_kirim_agirlik WHERE traktor_gelis_pmi_kirim_id = ? ORDER BY id", (kart['id'],))
            agirliklar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['agirliklar'] = agirliklar
            if agirliklar:
                kart['ortalama_agirlik'] = sum([a['agirlik'] for a in agirliklar]) / len(agirliklar)
            else:
                kart['ortalama_agirlik'] = 0
            kart['toplam_kg'] = kart['toplam_bohca'] * kart['ortalama_agirlik']
        return jsonify(kartlar)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

# --- PMI TOPPING KIRIM yeni sistem için ---
@app.route('/api/traktor_gelis_pmi_topping_kirim', methods=['POST'])
def add_traktor_gelis_pmi_topping_kirim():
    data = request.get_json()
    required_fields = ['tarih', 'plaka', 'gelis_no']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_pmi_topping_kirim (tarih, plaka, gelis_no)
        VALUES (?, ?, ?)
        """
        params = (
            data['tarih'], data['plaka'], data['gelis_no']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_topping_kirim', methods=['GET'])
def get_traktor_gelis_pmi_topping_kirim():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_pmi_topping_kirim ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_topping_kirim/dayibasi', methods=['POST'])
def add_traktor_gelis_pmi_topping_kirim_dayibasi():
    data = request.get_json()
    required_fields = ['traktor_gelis_pmi_topping_kirim_id', 'dayibasi_adi', 'bohca_sayisi']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_pmi_topping_kirim_dayibasi (traktor_gelis_pmi_topping_kirim_id, dayibasi_adi, bohca_sayisi)
        VALUES (?, ?, ?)
        """
        params = (
            data['traktor_gelis_pmi_topping_kirim_id'], data['dayibasi_adi'], data['bohca_sayisi']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_topping_kirim_dayibasi', methods=['GET'])
def get_traktor_gelis_pmi_topping_kirim_dayibasi():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_pmi_topping_kirim_dayibasi ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_topping_kirim_agirlik', methods=['POST'])
def add_traktor_gelis_pmi_topping_kirim_agirlik():
    data = request.get_json()
    required_fields = ['traktor_gelis_pmi_topping_kirim_id', 'agirlik', 'created_at']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_pmi_topping_kirim_agirlik (traktor_gelis_pmi_topping_kirim_id, agirlik, created_at)
        VALUES (?, ?, ?)
        """
        params = (
            data['traktor_gelis_pmi_topping_kirim_id'], data['agirlik'], data['created_at']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş ağırlık kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_topping_kirim_agirlik', methods=['GET'])
def get_traktor_gelis_pmi_topping_kirim_agirlik():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_pmi_topping_kirim_agirlik ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_topping_kirim_agirlik/<int:agirlik_id>', methods=['PUT'])
def update_traktor_gelis_pmi_topping_kirim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE traktor_gelis_pmi_topping_kirim_agirlik SET agirlik = ? WHERE id = ?", (agirlik, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_topping_kirim/summary', methods=['GET'])
def get_traktor_gelis_pmi_topping_kirim_summary():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_pmi_topping_kirim ORDER BY tarih DESC, plaka, gelis_no DESC")
        kartlar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        for kart in kartlar:
            cursor.execute("SELECT * FROM traktor_gelis_pmi_topping_kirim_dayibasi WHERE traktor_gelis_pmi_topping_kirim_id = ?", (kart['id'],))
            dayibasilari = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['dayibasilari'] = dayibasilari
            kart['toplam_bohca'] = sum([d['bohca_sayisi'] for d in dayibasilari]) if dayibasilari else 0
            cursor.execute("SELECT id, agirlik, created_at FROM traktor_gelis_pmi_topping_kirim_agirlik WHERE traktor_gelis_pmi_topping_kirim_id = ? ORDER BY id", (kart['id'],))
            agirliklar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['agirliklar'] = agirliklar
            if agirliklar:
                kart['ortalama_agirlik'] = sum([a['agirlik'] for a in agirliklar]) / len(agirliklar)
            else:
                kart['ortalama_agirlik'] = 0
            kart['toplam_kg'] = kart['toplam_bohca'] * kart['ortalama_agirlik']
        return jsonify(kartlar)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

# --- IZMIR KIRIM yeni sistem için ---
@app.route('/api/traktor_gelis_izmir_kirim', methods=['POST'])
def add_traktor_gelis_izmir_kirim():
    data = request.get_json()
    required_fields = ['tarih', 'plaka', 'gelis_no']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_izmir_kirim (tarih, plaka, gelis_no)
        VALUES (?, ?, ?)
        """
        params = (
            data['tarih'], data['plaka'], data['gelis_no']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_izmir_kirim', methods=['GET'])
def get_traktor_gelis_izmir_kirim():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_izmir_kirim ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_izmir_kirim/dayibasi', methods=['POST'])
def add_traktor_gelis_izmir_kirim_dayibasi():
    data = request.get_json()
    required_fields = ['traktor_gelis_izmir_kirim_id', 'dayibasi_adi', 'bohca_sayisi']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_izmir_kirim_dayibasi (traktor_gelis_izmir_kirim_id, dayibasi_adi, bohca_sayisi)
        VALUES (?, ?, ?)
        """
        params = (
            data['traktor_gelis_izmir_kirim_id'], data['dayibasi_adi'], data['bohca_sayisi']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_izmir_kirim_dayibasi', methods=['GET'])
def get_traktor_gelis_izmir_kirim_dayibasi():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_izmir_kirim_dayibasi ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_izmir_kirim_agirlik', methods=['POST'])
def add_traktor_gelis_izmir_kirim_agirlik():
    data = request.get_json()
    required_fields = ['traktor_gelis_izmir_kirim_id', 'agirlik', 'created_at']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_izmir_kirim_agirlik (traktor_gelis_izmir_kirim_id, agirlik, created_at)
        VALUES (?, ?, ?)
        """
        params = (
            data['traktor_gelis_izmir_kirim_id'], data['agirlik'], data['created_at']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş ağırlık kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_izmir_kirim_agirlik', methods=['GET'])
def get_traktor_gelis_izmir_kirim_agirlik():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_izmir_kirim_agirlik ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_izmir_kirim_agirlik/<int:agirlik_id>', methods=['PUT'])
def update_traktor_gelis_izmir_kirim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE traktor_gelis_izmir_kirim_agirlik SET agirlik = ? WHERE id = ?", (agirlik, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_izmir_kirim/summary', methods=['GET'])
def get_traktor_gelis_izmir_kirim_summary():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM traktor_gelis_izmir_kirim ORDER BY tarih DESC, plaka, gelis_no DESC")
        kartlar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        for kart in kartlar:
            cursor.execute("SELECT * FROM traktor_gelis_izmir_kirim_dayibasi WHERE traktor_gelis_izmir_kirim_id = ?", (kart['id'],))
            dayibasilari = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['dayibasilari'] = dayibasilari
            kart['toplam_bohca'] = sum([d['bohca_sayisi'] for d in dayibasilari]) if dayibasilari else 0
            cursor.execute("SELECT id, agirlik, created_at FROM traktor_gelis_izmir_kirim_agirlik WHERE traktor_gelis_izmir_kirim_id = ? ORDER BY id", (kart['id'],))
            agirliklar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['agirliklar'] = agirliklar
            if agirliklar:
                kart['ortalama_agirlik'] = sum([a['agirlik'] for a in agirliklar]) / len(agirliklar)
            else:
                kart['ortalama_agirlik'] = 0
            kart['toplam_kg'] = kart['toplam_bohca'] * kart['ortalama_agirlik']
        return jsonify(kartlar)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/scv_sera/<int:sera_id>', methods=['PATCH'])
def update_scv_sera_bitis_tarihi(sera_id):
    data = request.get_json()
    soldurma_bitis_tarihi = data.get('soldurma_bitis_tarihi')
    if not soldurma_bitis_tarihi:
        return jsonify({'message': 'soldurma_bitis_tarihi gerekli.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE scv_sera SET soldurma_bitis_tarihi = ? WHERE id = ?", (soldurma_bitis_tarihi, sera_id))
        conn.commit()
        return jsonify({'message': 'Soldurma bitiş tarihi güncellendi.'})
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print(" Veritabanı bağlantısı kontrol ediliyor...")
    if initialize_db():
        ensure_kutulama_alan_column()
        ensure_izmir_kutulama_sera_bosaltildi_column()
        ensure_izmir_sera_bosaltildi_column()
        ensure_scv_sera_new_columns()
        print("🚀 Flask uygulaması başlatılıyor...")
        #app.run(debug=True, port=5000)
        port = int(os.environ.get("PORT", 5000))
        app.run(debug=True, host="0.0.0.0", port=port)

    else:
        print("❌ Veritabanı bağlantısı kurulamadı. Uygulama başlatılamıyor.")
        print("\n🔧 Sorun giderme adımları:")
        print("1. SQL Server Management Studio'dan veritabanına bağlanabildiğinizi kontrol edin")
        print("2. Windows Authentication'ın etkin olduğundan emin olun")
        print("3. SQL Server Browser servisinin çalıştığını kontrol edin")
        print("4. Firewall ayarlarını kontrol edin")
        print("5. 'pip install pyodbc' ile pyodbc'nin güncel olduğundan emin olun")
        print("5. 'pip install pyodbc' ile pyodbc'nin güncel olduğundan emin olun")