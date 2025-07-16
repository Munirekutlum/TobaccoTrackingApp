from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import pandas as pd
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)

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

def initialize_db():
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (initialize_db)")
        return False
    try:
        cursor = conn.cursor()
        cursor.execute('PRAGMA foreign_keys = ON;')
        # --- Tüm tabloları oluştur ---
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            surname TEXT
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS fcv_bakim (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placeholder_col TEXT
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS fcv_genel (
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
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS fcv_kirim_gunluk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            userId INTEGER NOT NULL,
            tarih TEXT NOT NULL,
            bocaSayisi INTEGER NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            UNIQUE(userId, tarih),
            FOREIGN KEY(userId) REFERENCES users(id) ON DELETE CASCADE
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS fcv_kirim_agirlik (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gunlukId INTEGER NOT NULL,
            agirlik REAL NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY(gunlukId) REFERENCES fcv_kirim_gunluk(id) ON DELETE CASCADE
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS fcv_rask_dolum (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placeholder_col TEXT
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_dizim (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placeholder_col TEXT
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_dizim_dayibasi_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            dayibasi TEXT NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_dizim_gunluk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dayibasi_id INTEGER NOT NULL,
            diziAdedi INTEGER NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY(dayibasi_id) REFERENCES izmir_dizim_dayibasi_table(id) ON DELETE CASCADE
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_dizim_agirlik (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dayibasi_id INTEGER NOT NULL,
            agirlik REAL NOT NULL,
            yaprakSayisi INTEGER NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY(dayibasi_id) REFERENCES izmir_dizim_dayibasi_table(id) ON DELETE CASCADE
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_genel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placeholder_col TEXT
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_kirim (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placeholder_col TEXT
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_kirim_dayibasi_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            dayibasi TEXT NOT NULL,
            UNIQUE(dayibasi, tarih)
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_kirim_gunluk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dayibasi_id INTEGER NOT NULL,
            bohcaSayisi INTEGER,
            agirlik_id INTEGER,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY(dayibasi_id) REFERENCES izmir_kirim_dayibasi_table(id)
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_kirim_agirlik (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dayibasi_id INTEGER NOT NULL,
            agirlik REAL NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY(dayibasi_id) REFERENCES izmir_kirim_dayibasi_table(id) ON DELETE CASCADE
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_kutulama (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placeholder_col TEXT
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_kutulama_dayibasi_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            dayibasi TEXT NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_kutulama_kuru_kg (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dayibasi_id INTEGER NOT NULL,
            value REAL NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY(dayibasi_id) REFERENCES izmir_kutulama_dayibasi_table(id) ON DELETE CASCADE
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_kutulama_sera_yas_kg (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dayibasi_id INTEGER NOT NULL,
            value REAL NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY(dayibasi_id) REFERENCES izmir_kutulama_dayibasi_table(id) ON DELETE CASCADE
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_sera (
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
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS izmir_sera_yerleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sera_yeri TEXT NOT NULL UNIQUE,
            toplam_sera_sayisi INTEGER NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
        );''')
        # --- PMI SCV DİZİM ---
        cursor.execute('''CREATE TABLE IF NOT EXISTS pmi_scv_dizim (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placeholder_col TEXT
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_dayibasi_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            dayibasi TEXT NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_gunluk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dayibasi_id INTEGER NOT NULL,
            diziAdedi INTEGER NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_agirlik (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dayibasi_id INTEGER NOT NULL,
            agirlik REAL NOT NULL,
            yaprakSayisi INTEGER NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
        );''')
        # --- PMI SCV KIRIM ---
        cursor.execute('''CREATE TABLE IF NOT EXISTS pmi_scv_kirim (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placeholder_col TEXT
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS pmi_scv_kirim_dayibasi_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            dayibasi TEXT NOT NULL
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS pmi_scv_kirim_gunluk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dayibasi_id INTEGER NOT NULL,
            bohcaSayisi INTEGER NOT NULL,
            agirlik_id INTEGER,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_kirim_dayibasi_table(id)
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS pmi_scv_kirim_agirlik (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dayibasi_id INTEGER NOT NULL,
            agirlik REAL NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_kirim_dayibasi_table(id) ON DELETE CASCADE
        );''')
        # --- PMI SCV KUTULAMA ---
        cursor.execute('''CREATE TABLE IF NOT EXISTS pmi_scv_kutulama (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placeholder_col TEXT
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS pmi_scv_kutulama_dayibasi_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarih TEXT NOT NULL,
            dayibasi TEXT NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP)
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS pmi_scv_kutulama_kuru_kg (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dayibasi_id INTEGER NOT NULL,
            value REAL NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_kutulama_dayibasi_table(id) ON DELETE CASCADE
        );''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS pmi_scv_kutulama_sera_yas_kg (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dayibasi_id INTEGER NOT NULL,
            value REAL NOT NULL,
            created_at TEXT DEFAULT (CURRENT_TIMESTAMP),
            FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_kutulama_dayibasi_table(id) ON DELETE CASCADE
        );''')
        # --- INSERT INTO örnek veriler ---
        # pmi_scv_dizim_dayibasi_table
        cursor.execute("SELECT COUNT(*) FROM pmi_scv_dizim_dayibasi_table")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO pmi_scv_dizim_dayibasi_table (id, tarih, dayibasi, created_at) VALUES (1, '2025-07-10', 'kkk', '2025-07-10 16:37:32')")
        # pmi_scv_dizim_gunluk
        cursor.execute("SELECT COUNT(*) FROM pmi_scv_dizim_gunluk")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO pmi_scv_dizim_gunluk (id, dayibasi_id, diziAdedi, created_at) VALUES (1, 1, 150, '2025-07-13 13:07:19')")
        # pmi_scv_dizim_agirlik
        cursor.execute("SELECT COUNT(*) FROM pmi_scv_dizim_agirlik")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (1, 1, 10, 140, '2025-07-13 13:04:10')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (2, 1, 11, 20, '2025-07-13 13:04:15')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (3, 1, 12, 52, '2025-07-13 13:04:21')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (4, 1, 12, 45, '2025-07-13 13:04:27')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (5, 1, 13, 150, '2025-07-13 13:04:32')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (6, 1, 16, 120, '2025-07-13 13:05:35')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (7, 1, 16, 120, '2025-07-13 13:05:35')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (8, 1, 15, 140, '2025-07-13 13:05:52')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (9, 1, 14, 240, '2025-07-13 13:05:59')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (10, 1, 16, 52, '2025-07-13 13:06:06')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (11, 1, 20, 140, '2025-07-13 13:06:12')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (12, 1, 16, 240, '2025-07-13 13:06:18')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (13, 1, 14, 180, '2025-07-13 13:06:27')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (14, 1, 14, 180, '2025-07-13 13:06:27')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (15, 1, 16, 140, '2025-07-13 13:06:34')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (16, 1, 19, 150, '2025-07-13 13:06:38')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (17, 1, 6, 75, '2025-07-13 13:06:45')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (18, 1, 16, 120, '2025-07-13 13:06:53')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (19, 1, 16, 310, '2025-07-13 13:07:02')")
            cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (id, dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (20, 1, 16, 210, '2025-07-13 13:07:11')")
        # --- PMI SCV KIRIM örnek veriler ---
        cursor.execute("SELECT COUNT(*) FROM pmi_scv_kirim_dayibasi_table")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO pmi_scv_kirim_dayibasi_table (id, tarih, dayibasi) VALUES (1, '2025-07-09', 'aaa')")
            cursor.execute("INSERT INTO pmi_scv_kirim_dayibasi_table (id, tarih, dayibasi) VALUES (2, '2025-07-10', 'aaaaaaa')")
        cursor.execute("SELECT COUNT(*) FROM pmi_scv_kirim_gunluk")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO pmi_scv_kirim_gunluk (id, dayibasi_id, bohcaSayisi, agirlik_id, created_at) VALUES (1, 1, 230, NULL, '2025-07-01 23:50:29')")
            cursor.execute("INSERT INTO pmi_scv_kirim_gunluk (id, dayibasi_id, bohcaSayisi, agirlik_id, created_at) VALUES (2, 2, 150, NULL, '2025-07-13 23:05:13')")
            cursor.execute("INSERT INTO pmi_scv_kirim_gunluk (id, dayibasi_id, bohcaSayisi, agirlik_id, created_at) VALUES (3, 2, 150, NULL, '2025-07-13 23:05:13')")
        cursor.execute("SELECT COUNT(*) FROM pmi_scv_kirim_agirlik")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (1, 2, 15, '2025-07-10 16:44:19')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (2, 2, 85, '2025-07-10 16:44:23')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (3, 2, 15, '2025-07-13 13:00:40')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (4, 2, 17, '2025-07-13 13:00:44')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (5, 2, 17, '2025-07-13 13:00:44')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (6, 2, 8, '2025-07-13 13:00:47')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (7, 2, 74, '2025-07-13 13:00:49')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (8, 2, 16, '2025-07-13 13:00:52')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (9, 2, 12, '2025-07-13 13:00:54')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (10, 2, 11, '2025-07-13 13:00:56')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (11, 2, 13, '2025-07-13 13:01:00')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (12, 2, 16, '2025-07-13 13:01:04')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (13, 2, 18, '2025-07-13 13:01:06')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (14, 2, 20, '2025-07-13 13:01:09')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (15, 2, 14, '2025-07-13 13:01:13')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (16, 2, 16, '2025-07-13 13:01:16')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (17, 2, 18, '2025-07-13 13:01:19')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (18, 2, 20, '2025-07-13 13:01:21')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (19, 2, 17, '2025-07-13 13:01:50')")
            cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (id, dayibasi_id, agirlik, created_at) VALUES (20, 2, 22, '2025-07-13 13:01:55')")
        # pmi_scv_kutulama_dayibasi_table
        cursor.execute("SELECT COUNT(*) FROM pmi_scv_kutulama_dayibasi_table")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO pmi_scv_kutulama_dayibasi_table (id, tarih, dayibasi, created_at) VALUES (1, '2025-07-10', 'kkk', '2025-07-10 16:37:32')")
        # pmi_scv_kutulama_kuru_kg
        cursor.execute("SELECT COUNT(*) FROM pmi_scv_kutulama_kuru_kg")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO pmi_scv_kutulama_kuru_kg (id, dayibasi_id, value, created_at) VALUES (1, 1, 15, '2025-07-10 13:47:52')")
            cursor.execute("INSERT INTO pmi_scv_kutulama_kuru_kg (id, dayibasi_id, value, created_at) VALUES (2, 1, 15, '2025-07-10 13:47:58')")
        # pmi_scv_kutulama_sera_yas_kg
        cursor.execute("SELECT COUNT(*) FROM pmi_scv_kutulama_sera_yas_kg")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO pmi_scv_kutulama_sera_yas_kg (id, dayibasi_id, value, created_at) VALUES (1, 1, 25, '2025-07-10 13:47:52')")
            cursor.execute("INSERT INTO pmi_scv_kutulama_sera_yas_kg (id, dayibasi_id, value, created_at) VALUES (2, 1, 15, '2025-07-10 13:47:52')")
            cursor.execute("INSERT INTO pmi_scv_kutulama_sera_yas_kg (id, dayibasi_id, value, created_at) VALUES (3, 1, 25, '2025-07-10 13:47:58')")
            cursor.execute("INSERT INTO pmi_scv_kutulama_sera_yas_kg (id, dayibasi_id, value, created_at) VALUES (4, 1, 15, '2025-07-10 13:47:58')")
        conn.commit()
        print("✅ SQLite tabloları ve başlangıç verileri başarıyla oluşturuldu.")
        return True
    except Exception as e:
        print(f"❌ Tablo/veri oluşturma hatası: {e}")
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

# --- API Endpointleri ---
#-----------------------------------------------------------------------------------------------
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = (data.get('email') or '').strip()
    password = data.get('password')
    name = (data.get('name') or '').strip()
    surname = (data.get('surname') or '').strip()

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
        user_data = {'id': user.id, 'email': user.email, 'name': user.name, 'surname': user.surname}
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
    sql_insert = "INSERT INTO fcv_kirim_gunluk (userId, tarih, bocaSayisi) VALUES (?, ?, ?)"
    sql_update = "UPDATE fcv_kirim_gunluk SET bocaSayisi = ? WHERE id = ?"
    
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['userId'], data['tarih']))
        existing = cursor.fetchone()
        if existing:
            cursor.execute(sql_update, (data['bocaSayisi'], existing.id))
        else:
            cursor.execute(sql_insert, (data['userId'], data['tarih'], data['bocaSayisi']))
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
        
    sql = "INSERT INTO fcv_kirim_agirlik (gunlukId, agirlik) VALUES (?, ?)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (data['gunlukId'], data['agirlik']))
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
@app.route('/api/izmir_kirim/summary', methods=['GET'])
def get_izmir_kirim_summary():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi,
                g.id as gunluk_id,
                g.bohcaSayisi,
                g.agirlik_id,
                (SELECT COUNT(a.id) FROM izmir_kirim_agirlik a WHERE a.dayibasi_id = d.id) as girilenAgirlikSayisi,
                (SELECT AVG(a.agirlik) FROM izmir_kirim_agirlik a WHERE a.dayibasi_id = d.id) as ortalamaAgirlik
            FROM izmir_kirim_dayibasi_table d
            LEFT JOIN izmir_kirim_gunluk g ON d.id = g.dayibasi_id
            ORDER BY d.tarih DESC, d.dayibasi
        """)
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            if r['ortalamaAgirlik'] and r['bohcaSayisi']:
                r['toplamTahminiKg'] = r['ortalamaAgirlik'] * r['bohcaSayisi']
            else:
                r['toplamTahminiKg'] = 0
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/izmir_kirim/gunluk', methods=['POST'])
def add_or_update_izmir_kirim_gunluk():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    bohcaSayisi = data.get('bohcaSayisi')
    agirlik_id = data.get('agirlik_id')  # opsiyonel

    if not dayibasi_id or bohcaSayisi is None:
        return jsonify({'message': 'dayibasi_id ve bohcaSayisi zorunludur.'}), 400

    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Kayıt var mı kontrol et
        cursor.execute("SELECT id FROM izmir_kirim_gunluk WHERE dayibasi_id = ?", dayibasi_id)
        existing = cursor.fetchone()
        if existing:
            if agirlik_id:
                cursor.execute("UPDATE izmir_kirim_gunluk SET bohcaSayisi = ?, agirlik_id = ? WHERE id = ?", (bohcaSayisi, agirlik_id, existing.id))
            else:
                cursor.execute("UPDATE izmir_kirim_gunluk SET bohcaSayisi = ? WHERE id = ?", (bohcaSayisi, existing.id))
            conn.commit()
            return jsonify({'message': 'Günlük güncellendi.'}), 200
        else:
            if agirlik_id:
                cursor.execute("INSERT INTO izmir_kirim_gunluk (dayibasi_id, bohcaSayisi, agirlik_id) VALUES (?, ?, ?)", (dayibasi_id, bohcaSayisi, agirlik_id))
            else:
                cursor.execute("INSERT INTO izmir_kirim_gunluk (dayibasi_id, bohcaSayisi) VALUES (?, ?)", (dayibasi_id, bohcaSayisi))
            conn.commit()
            return jsonify({'message': 'Günlük eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/izmir_kirim/agirlik', methods=['POST'])
def add_izmir_kirim_agirlik():
    data = request.get_json()
    agirlik = data.get('agirlik')
    dayibasi_id = data.get('dayibasi_id')
    if not agirlik or not dayibasi_id:
        return jsonify({'message': 'dayibasi_id ve agirlik zorunludur.'}), 400

    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO izmir_kirim_agirlik (dayibasi_id, agirlik) VALUES (?, ?)", (dayibasi_id, agirlik))
        conn.commit()
        return jsonify({'message': 'Ağırlık başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/izmir_kirim/agirlik/details', methods=['GET'])
def get_izmir_kirim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    sql = "SELECT id, agirlik, created_at FROM izmir_kirim_agirlik WHERE dayibasi_id = ? ORDER BY id"
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

@app.route('/api/izmir_kirim/dayibasi', methods=['POST'])
def add_izmir_kirim_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400

    sql_check = "SELECT id FROM izmir_kirim_dayibasi_table WHERE dayibasi = ? AND tarih = ?"
    sql_insert = "INSERT INTO izmir_kirim_dayibasi_table (tarih, dayibasi) VALUES (?, ?)"
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
        cursor.execute("INSERT INTO izmir_dizim_agirlik (dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (?, ?, ?, GETDATE())", (dayibasi_id, agirlik, yaprakSayisi))
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
    sql = "SELECT id, agirlik, yaprakSayisi, created_at FROM izmir_dizim_agirlik WHERE dayibasi_id = ? ORDER BY id"
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
        cursor.execute("SELECT id FROM izmir_dizim_gunluk WHERE dayibasi_id = ?", dayibasi_id)
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE izmir_dizim_gunluk SET diziAdedi = ? WHERE id = ?", (diziAdedi, existing.id))
            conn.commit()
            return jsonify({'message': 'Dizi adedi güncellendi.'}), 200
        else:
            cursor.execute("INSERT INTO izmir_dizim_gunluk (dayibasi_id, diziAdedi, created_at) VALUES (?, ?, GETDATE())", (dayibasi_id, diziAdedi))
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
#---scv jtı KIRIM api endpointleri-------
@app.route('/api/jti_scv_kirim/summary', methods=['GET'])
def get_jti_scv_kirim_summary():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi,
                g.id as gunluk_id,
                g.bohcaSayisi,
                g.agirlik_id,
                (SELECT COUNT(a.id) FROM jti_scv_kirim_agirlik a WHERE a.dayibasi_id = d.id) as girilenAgirlikSayisi,
                (SELECT AVG(a.agirlik) FROM jti_scv_kirim_agirlik a WHERE a.dayibasi_id = d.id) as ortalamaAgirlik
            FROM jti_scv_kirim_dayibasi_table d
            LEFT JOIN jti_scv_kirim_gunluk g ON d.id = g.dayibasi_id
            ORDER BY d.tarih DESC, d.dayibasi
        """)
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            if r['ortalamaAgirlik'] and r['bohcaSayisi']:
                r['toplamTahminiKg'] = r['ortalamaAgirlik'] * r['bohcaSayisi']
            else:
                r['toplamTahminiKg'] = 0
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_kirim/gunluk', methods=['POST'])
def add_or_update_jti_scv_kirim_gunluk():
    data = request.get_json()
    print(f"JTI SCV KIRIM GUNLUK - Gelen veri: {data}")
    
    dayibasi_id = data.get('dayibasi_id')
    bohcaSayisi = data.get('bohcaSayisi')
    agirlik_id = data.get('agirlik_id')  # opsiyonel

    print(f"dayibasi_id: {dayibasi_id}, bohcaSayisi: {bohcaSayisi}, agirlik_id: {agirlik_id}")

    if not dayibasi_id or bohcaSayisi is None:
        print("Eksik parametreler")
        return jsonify({'message': 'dayibasi_id ve bohcaSayisi zorunludur.'}), 400

    conn = get_db_connection()
    if not conn: 
        print("Veritabanı bağlantı hatası")
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        
        # Önce dayibasi_id'nin mevcut olup olmadığını kontrol et
        cursor.execute("SELECT id FROM jti_scv_kirim_dayibasi_table WHERE id = ?", dayibasi_id)
        dayibasi_exists = cursor.fetchone()
        print(f"Dayıbaşı mevcut mu: {dayibasi_exists}")
        
        if not dayibasi_exists:
            print(f"Dayıbaşı ID {dayibasi_id} bulunamadı")
            return jsonify({'message': f'Dayıbaşı ID {dayibasi_id} bulunamadı. Önce dayıbaşı kaydı oluşturun.'}), 400
        
        # Kayıt var mı kontrol et
        cursor.execute("SELECT id FROM jti_scv_kirim_gunluk WHERE dayibasi_id = ?", dayibasi_id)
        existing = cursor.fetchone()
        print(f"Mevcut kayıt: {existing}")
        
        if existing:
            if agirlik_id:
                cursor.execute("UPDATE jti_scv_kirim_gunluk SET bohcaSayisi = ?, agirlik_id = ? WHERE id = ?", (bohcaSayisi, agirlik_id, existing.id))
            else:
                cursor.execute("UPDATE jti_scv_kirim_gunluk SET bohcaSayisi = ? WHERE id = ?", (bohcaSayisi, existing.id))
            conn.commit()
            print("Günlük güncellendi")
            return jsonify({'message': 'Günlük güncellendi.'}), 200
        else:
            if agirlik_id:
                cursor.execute("INSERT INTO jti_scv_kirim_gunluk (dayibasi_id, bohcaSayisi, agirlik_id) VALUES (?, ?, ?)", (dayibasi_id, bohcaSayisi, agirlik_id))
            else:
                cursor.execute("INSERT INTO jti_scv_kirim_gunluk (dayibasi_id, bohcaSayisi, agirlik_id) VALUES (?, ?, ?)", (dayibasi_id, bohcaSayisi, None))
            conn.commit()
            print("Günlük eklendi")
            return jsonify({'message': 'Günlük eklendi.'}), 201
    except Exception as e:
        print(f"JTI SCV KIRIM GUNLUK - Hata: {e}")
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_kirim/agirlik', methods=['POST'])
def add_jti_scv_kirim_agirlik():
    data = request.get_json()
    print(f"JTI SCV KIRIM AGIRLIK - Gelen veri: {data}")
    
    agirlik = data.get('agirlik')
    dayibasi_id = data.get('dayibasi_id')
    print(f"agirlik: {agirlik}, dayibasi_id: {dayibasi_id}")
    
    if not agirlik or not dayibasi_id:
        print("Eksik parametreler")
        return jsonify({'message': 'dayibasi_id ve agirlik zorunludur.'}), 400

    conn = get_db_connection()
    if not conn: 
        print("Veritabanı bağlantı hatası")
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        
        # Önce dayibasi_id'nin mevcut olup olmadığını kontrol et
        cursor.execute("SELECT id FROM jti_scv_kirim_dayibasi_table WHERE id = ?", dayibasi_id)
        dayibasi_exists = cursor.fetchone()
        print(f"Dayıbaşı mevcut mu: {dayibasi_exists}")
        
        if not dayibasi_exists:
            print(f"Dayıbaşı ID {dayibasi_id} bulunamadı")
            return jsonify({'message': f'Dayıbaşı ID {dayibasi_id} bulunamadı. Önce dayıbaşı kaydı oluşturun.'}), 400
        
        cursor.execute("INSERT INTO jti_scv_kirim_agirlik (dayibasi_id, agirlik) VALUES (?, ?)", (dayibasi_id, agirlik))
        conn.commit()
        print("Ağırlık başarıyla eklendi")
        return jsonify({'message': 'Ağırlık başarıyla eklendi.'}), 201
    except Exception as e:
        print(f"JTI SCV KIRIM AGIRLIK - Hata: {e}")
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_kirim/agirlik/details', methods=['GET'])
def get_jti_scv_kirim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    sql = "SELECT id, agirlik, created_at FROM jti_scv_kirim_agirlik WHERE dayibasi_id = ? ORDER BY id"
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

@app.route('/api/jti_scv_kirim/dayibasi', methods=['POST'])
def add_jti_scv_kirim_dayibasi():
    data = request.get_json()
    print(f"JTI SCV KIRIM DAYIBASI - Gelen veri: {data}")
    
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        print("Eksik parametreler")
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400

    sql_check = "SELECT id FROM jti_scv_kirim_dayibasi_table WHERE dayibasi = ? AND tarih = ?"
    sql_insert = "INSERT INTO jti_scv_kirim_dayibasi_table (tarih, dayibasi) VALUES (?, ?)"
    conn = get_db_connection()
    if not conn: 
        print("Veritabanı bağlantı hatası")
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['dayibasi'], data['tarih']))
        existing = cursor.fetchone()
        print(f"Mevcut dayıbaşı kaydı: {existing}")
        
        if existing:
            print("Bu dayıbaşı ve tarihe ait kayıt zaten var")
            return jsonify({'message': 'Bu dayıbaşı ve tarihe ait kayıt zaten var.'}), 409
        cursor.execute(sql_insert, (data['tarih'], data['dayibasi']))
        conn.commit()
        print("Dayıbaşı kaydı başarıyla eklendi")
        return jsonify({'message': 'Dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        print(f"JTI SCV KIRIM DAYIBASI - Hata: {e}")
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()



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
    yaprakSayisi = data.get('yaprakSayisi')
    dayibasi_id = data.get('dayibasi_id')
    if not agirlik or not dayibasi_id or not yaprakSayisi:
        return jsonify({'message': 'dayibasi_id, agirlik ve yaprakSayisi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO jti_scv_dizim_agirlik (dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (?, ?, ?, GETDATE())", (dayibasi_id, agirlik, yaprakSayisi))
        conn.commit()
        return jsonify({'message': 'Ağırlık ve yaprak sayısı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_dizim/agirlik/details', methods=['GET'])
def get_jti_scv_dizim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    sql = "SELECT id, agirlik, yaprakSayisi, created_at FROM jti_scv_dizim_agirlik WHERE dayibasi_id = ? ORDER BY id"
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

@app.route('/api/jti_scv_dizim/gunluk', methods=['POST'])
def add_or_update_jti_scv_dizim_gunluk():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    diziAdedi = data.get('bohcaSayisi')  # frontend 'bohcaSayisi' gönderiyor, burada diziAdedi olarak kaydediyoruz
    if not dayibasi_id or diziAdedi is None:
        return jsonify({'message': 'dayibasi_id ve diziAdedi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM jti_scv_dizim_gunluk WHERE dayibasi_id = ?", dayibasi_id)
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE jti_scv_dizim_gunluk SET diziAdedi = ? WHERE id = ?", (diziAdedi, existing.id))
            conn.commit()
            return jsonify({'message': 'Dizi adedi güncellendi.'}), 200
        else:
            cursor.execute("INSERT INTO jti_scv_dizim_gunluk (dayibasi_id, diziAdedi, created_at) VALUES (?, ?, GETDATE())", (dayibasi_id, diziAdedi))
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
#---scv pmı KIRIRM api endpointleri---------------
@app.route('/api/pmi_scv_kirim/summary', methods=['GET'])
def get_pmi_scv_kirim_summary():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi,
                g.id as gunluk_id,
                g.bohcaSayisi,
                g.agirlik_id,
                (SELECT COUNT(a.id) FROM pmi_scv_kirim_agirlik a WHERE a.dayibasi_id = d.id) as girilenAgirlikSayisi,
                (SELECT AVG(a.agirlik) FROM pmi_scv_kirim_agirlik a WHERE a.dayibasi_id = d.id) as ortalamaAgirlik
            FROM pmi_scv_kirim_dayibasi_table d
            LEFT JOIN pmi_scv_kirim_gunluk g ON d.id = g.dayibasi_id
            ORDER BY d.tarih DESC, d.dayibasi
        """)
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            if r['ortalamaAgirlik'] and r['bohcaSayisi']:
                r['toplamTahminiKg'] = r['ortalamaAgirlik'] * r['bohcaSayisi']
            else:
                r['toplamTahminiKg'] = 0
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_kirim/gunluk', methods=['POST'])
def add_or_update_pmi_scv_kirim_gunluk():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    bohcaSayisi = data.get('bohcaSayisi')
    agirlik_id = data.get('agirlik_id')  # opsiyonel

    if not dayibasi_id or bohcaSayisi is None:
        return jsonify({'message': 'dayibasi_id ve bohcaSayisi zorunludur.'}), 400

    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Kayıt var mı kontrol et
        cursor.execute("SELECT id FROM pmi_scv_kirim_gunluk WHERE dayibasi_id = ?", dayibasi_id)
        existing = cursor.fetchone()
        if existing:
            if agirlik_id:
                cursor.execute("UPDATE pmi_scv_kirim_gunluk SET bohcaSayisi = ?, agirlik_id = ? WHERE id = ?", (bohcaSayisi, agirlik_id, existing.id))
            else:
                cursor.execute("UPDATE pmi_scv_kirim_gunluk SET bohcaSayisi = ? WHERE id = ?", (bohcaSayisi, existing.id))
            conn.commit()
            return jsonify({'message': 'Günlük güncellendi.'}), 200
        else:
            if agirlik_id:
                cursor.execute("INSERT INTO pmi_scv_kirim_gunluk (dayibasi_id, bohcaSayisi, agirlik_id) VALUES (?, ?, ?)", (dayibasi_id, bohcaSayisi, agirlik_id))
            else:
                cursor.execute("INSERT INTO pmi_scv_kirim_gunluk (dayibasi_id, bohcaSayisi, agirlik_id) VALUES (?, ?, ?)", (dayibasi_id, bohcaSayisi, None))
            conn.commit()
            return jsonify({'message': 'Günlük eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_kirim/agirlik', methods=['POST'])
def add_pmi_scv_kirim_agirlik():
    data = request.get_json()
    agirlik = data.get('agirlik')
    dayibasi_id = data.get('dayibasi_id')
    if not agirlik or not dayibasi_id:
        return jsonify({'message': 'dayibasi_id ve agirlik zorunludur.'}), 400

    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pmi_scv_kirim_agirlik (dayibasi_id, agirlik) VALUES (?, ?)", (dayibasi_id, agirlik))
        conn.commit()
        return jsonify({'message': 'Ağırlık başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_kirim/agirlik/details', methods=['GET'])
def get_pmi_scv_kirim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    sql = "SELECT id, agirlik, created_at FROM pmi_scv_kirim_agirlik WHERE dayibasi_id = ? ORDER BY id"
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

@app.route('/api/pmi_scv_kirim/dayibasi', methods=['POST'])
def add_pmi_scv_kirim_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400

    sql_check = "SELECT id FROM pmi_scv_kirim_dayibasi_table WHERE dayibasi = ? AND tarih = ?"
    sql_insert = "INSERT INTO pmi_scv_kirim_dayibasi_table (tarih, dayibasi) VALUES (?, ?)"
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
    yaprakSayisi = data.get('yaprakSayisi')
    dayibasi_id = data.get('dayibasi_id')
    if not agirlik or not dayibasi_id or not yaprakSayisi:
        return jsonify({'message': 'dayibasi_id, agirlik ve yaprakSayisi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (?, ?, ?, GETDATE())", (dayibasi_id, agirlik, yaprakSayisi))
        conn.commit()
        return jsonify({'message': 'Ağırlık ve yaprak sayısı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_dizim/agirlik/details', methods=['GET'])
def get_pmi_scv_dizim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    sql = "SELECT id, agirlik, yaprakSayisi, created_at FROM pmi_scv_dizim_agirlik WHERE dayibasi_id = ? ORDER BY id"
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
            cursor.execute("UPDATE pmi_scv_dizim_gunluk SET diziAdedi = ? WHERE id = ?", (diziAdedi, existing.id))
            conn.commit()
            return jsonify({'message': 'Dizi adedi güncellendi.'}), 200
        else:
            cursor.execute("INSERT INTO pmi_scv_dizim_gunluk (dayibasi_id, diziAdedi, created_at) VALUES (?, ?, GETDATE())", (dayibasi_id, diziAdedi))
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
#------scv pmi KIRIM topping api endpointleri---------------------------
@app.route('/api/pmi_topping_kirim/summary', methods=['GET'])
def get_pmi_topping_kirim_summary():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi,
                g.id as gunluk_id,
                g.bohcaSayisi,
                g.agirlik_id,
                (SELECT COUNT(a.id) FROM pmi_topping_kirim_agirlik a WHERE a.dayibasi_id = d.id) as girilenAgirlikSayisi,
                (SELECT AVG(a.agirlik) FROM pmi_topping_kirim_agirlik a WHERE a.dayibasi_id = d.id) as ortalamaAgirlik
            FROM pmi_topping_kirim_dayibasi_table d
            LEFT JOIN pmi_topping_kirim_gunluk g ON d.id = g.dayibasi_id
            ORDER BY d.tarih DESC, d.dayibasi
        """)
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            if r['ortalamaAgirlik'] and r['bohcaSayisi']:
                r['toplamTahminiKg'] = r['ortalamaAgirlik'] * r['bohcaSayisi']
            else:
                r['toplamTahminiKg'] = 0
        return jsonify(results)
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_kirim/gunluk', methods=['POST'])
def add_or_update_pmi_topping_kirim_gunluk():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    bohcaSayisi = data.get('bohcaSayisi')
    agirlik_id = data.get('agirlik_id')  # opsiyonel

    if not dayibasi_id or bohcaSayisi is None:
        return jsonify({'message': 'dayibasi_id ve bohcaSayisi zorunludur.'}), 400

    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Kayıt var mı kontrol et
        cursor.execute("SELECT id FROM pmi_topping_kirim_gunluk WHERE dayibasi_id = ?", dayibasi_id)
        existing = cursor.fetchone()
        if existing:
            if agirlik_id:
                cursor.execute("UPDATE pmi_topping_kirim_gunluk SET bohcaSayisi = ?, agirlik_id = ? WHERE id = ?", (bohcaSayisi, agirlik_id, existing.id))
            else:
                cursor.execute("UPDATE pmi_topping_kirim_gunluk SET bohcaSayisi = ? WHERE id = ?", (bohcaSayisi, existing.id))
            conn.commit()
            return jsonify({'message': 'Günlük güncellendi.'}), 200
        else:
            if agirlik_id:
                cursor.execute("INSERT INTO pmi_topping_kirim_gunluk (dayibasi_id, bohcaSayisi, agirlik_id) VALUES (?, ?, ?)", (dayibasi_id, bohcaSayisi, agirlik_id))
            else:
                cursor.execute("INSERT INTO pmi_topping_kirim_gunluk (dayibasi_id, bohcaSayisi, agirlik_id) VALUES (?, ?, ?)", (dayibasi_id, bohcaSayisi, None))
            conn.commit()
            return jsonify({'message': 'Günlük eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_kirim/agirlik', methods=['POST'])
def add_pmi_topping_kirim_agirlik():
    data = request.get_json()
    agirlik = data.get('agirlik')
    dayibasi_id = data.get('dayibasi_id')
    if not agirlik or not dayibasi_id:
        return jsonify({'message': 'dayibasi_id ve agirlik zorunludur.'}), 400

    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pmi_topping_kirim_agirlik (dayibasi_id, agirlik) VALUES (?, ?)", (dayibasi_id, agirlik))
        conn.commit()
        return jsonify({'message': 'Ağırlık başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_kirim/agirlik/details', methods=['GET'])
def get_pmi_topping_kirim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    sql = "SELECT id, agirlik, created_at FROM pmi_topping_kirim_agirlik WHERE dayibasi_id = ? ORDER BY id"
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

@app.route('/api/pmi_topping_kirim/dayibasi', methods=['POST'])
def add_pmi_topping_kirim_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400

    sql_check = "SELECT id FROM pmi_topping_kirim_dayibasi_table WHERE dayibasi = ? AND tarih = ?"
    sql_insert = "INSERT INTO pmi_topping_kirim_dayibasi_table (tarih, dayibasi) VALUES (?, ?)"
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
    yaprakSayisi = data.get('yaprakSayisi')
    dayibasi_id = data.get('dayibasi_id')
    if not agirlik or not dayibasi_id or not yaprakSayisi:
        return jsonify({'message': 'dayibasi_id, agirlik ve yaprakSayisi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO pmi_topping_dizim_agirlik (dayibasi_id, agirlik, yaprakSayisi, created_at) VALUES (?, ?, ?, GETDATE())", (dayibasi_id, agirlik, yaprakSayisi))
        conn.commit()
        return jsonify({'message': 'Ağırlık ve yaprak sayısı başarıyla eklendi.'}), 201
    except Exception as e:
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_dizim/agirlik/details', methods=['GET'])
def get_pmi_topping_dizim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    sql = "SELECT id, agirlik, yaprakSayisi, created_at FROM pmi_topping_dizim_agirlik WHERE dayibasi_id = ? ORDER BY id"
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
        cursor.execute("SELECT id FROM pmi_topping_dizim_gunluk WHERE dayibasi_id = ?", dayibasi_id)
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE pmi_topping_dizim_gunluk SET diziAdedi = ? WHERE id = ?", (diziAdedi, existing.id))
            conn.commit()
            return jsonify({'message': 'Dizi adedi güncellendi.'}), 200
        else:
            cursor.execute("INSERT INTO pmi_topping_dizim_gunluk (dayibasi_id, diziAdedi, created_at) VALUES (?, ?, GETDATE())", (dayibasi_id, diziAdedi))
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
        INSERT INTO scv_sera (sera_yeri, alan, sera_no, dizi_sayisi, dizi_kg1, dizi_kg2, dizi_kg3, dizi_kg4, dizi_kg5, dizi_kg6)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data['sera_yeri'], data['alan'], data['sera_no'], data['dizi_sayisi'],
            data['dizi_kg1'], data['dizi_kg2'], data['dizi_kg3'], data['dizi_kg4'], data['dizi_kg5'], data['dizi_kg6']
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
        cursor.execute("INSERT INTO scv_sera_yerleri (sera_yeri, toplam_sera_sayisi) VALUES (?, ?)", 
                      sera_yeri, toplam_sera_sayisi)
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
    required_fields = ['tarih', 'dayibasi', 'sera_yeri', 'sera_no', 'sera_yas_kg', 'kutular', 'toplam_kuru_kg', 'yas_kuru_orani']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO scv_kutulama (tarih, dayibasi, sera_yeri, sera_no, sera_yas_kg, kutular, toplam_kuru_kg, yas_kuru_orani, alan)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            data['tarih'], data['dayibasi'], data['sera_yeri'], data['sera_no'], 
            data['sera_yas_kg'], data['kutular'], data['toplam_kuru_kg'], data['yas_kuru_orani'],
            data.get('alan')
        )
        cursor.execute(sql, params)
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
                      sera_yeri, toplam_sera_sayisi)
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
            INSERT INTO izmir_kutulama (tarih, dayibasi, sera_yeri, sera_no, sera_yas_kg, kutular, toplam_kuru_kg, yas_kuru_orani)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('tarih'),
            data.get('dayibasi'),
            data.get('sera_yeri'),
            data.get('sera_no'),
            data.get('sera_yas_kg'),
            data.get('kutular'),
            data.get('toplam_kuru_kg'),
            data.get('yas_kuru_orani')
        ))
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
            alan = (row.alan or '').strip().upper()
            kutular_json = row.kutular
            toplam_kg = row.toplam_kuru_kg or 0
            try:
                kutular_array = json.loads(kutular_json)
                kutu_sayisi = len([k for k in kutular_array if k and k > 0])
            except:
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
                # Hem tire hem de boşluk ile arama yap
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

if __name__ == '__main__':
    print("🔄 Veritabanı bağlantısı kontrol ediliyor...")
    if initialize_db():
        ensure_kutulama_alan_column()
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