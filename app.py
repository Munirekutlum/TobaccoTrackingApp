from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from datetime import datetime
import json
import os
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers="*", supports_credentials=True)

# PostgreSQL veritabanı bağlantı URL'i
DATABASE_URL = "postgresql://bag_tech_masraf_user:bxJYj5rIJpH8PEvgfBtfuwr3LXVd5ukC@dpg-d54dh8ruibrs738dlstg-a.frankfurt-postgres.render.com/bag_tech_masraf"

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
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
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"PostgreSQL Version: {version}")
        
        cursor.execute("SELECT current_database()")
        db_name = cursor.fetchone()[0]
        print(f"Current Database: {db_name}")
        
        cursor.execute("SELECT current_user")
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
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        )
    """, (table_name,))
    return cursor.fetchone()[0]

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
        # PostgreSQL'de foreign keys varsayılan olarak aktif
        
        # Tablo tanımları
        tables = {
            'users': '''CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT,
                surname TEXT
            );''',
            'fcv_bakim': '''CREATE TABLE IF NOT EXISTS fcv_bakim (
                id SERIAL PRIMARY KEY,
                placeholder_col TEXT
            );''',
            'fcv_genel': '''CREATE TABLE IF NOT EXISTS fcv_genel (
                id SERIAL PRIMARY KEY,
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'fcv_kirim_gunluk': '''CREATE TABLE IF NOT EXISTS fcv_kirim_gunluk (
                id SERIAL PRIMARY KEY,
                userId INTEGER NOT NULL,
                tarih TEXT NOT NULL,
                bocaSayisi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(userId, tarih),
                FOREIGN KEY(userId) REFERENCES users(id) ON DELETE CASCADE
            );''',
            'fcv_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS fcv_kirim_agirlik (
                id SERIAL PRIMARY KEY,
                gunlukId INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(gunlukId) REFERENCES fcv_kirim_gunluk(id) ON DELETE CASCADE
            );''',
            'fcv_rask_dolum': '''CREATE TABLE IF NOT EXISTS fcv_rask_dolum (
                id SERIAL PRIMARY KEY,
                placeholder_col TEXT
            );''',
            'izmir_dizim': '''CREATE TABLE IF NOT EXISTS izmir_dizim (
                id SERIAL PRIMARY KEY,
                placeholder_col TEXT
            );''',
            'izmir_dizim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS izmir_dizim_dayibasi_table (
                id SERIAL PRIMARY KEY,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'izmir_dizim_gunluk': '''CREATE TABLE IF NOT EXISTS izmir_dizim_gunluk (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                diziAdedi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES izmir_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'izmir_dizim_agirlik': '''CREATE TABLE IF NOT EXISTS izmir_dizim_agirlik (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yaprakSayisi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES izmir_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'izmir_kutulama': '''CREATE TABLE IF NOT EXISTS izmir_kutulama (
                id SERIAL PRIMARY KEY,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                sergi_numaralari TEXT NOT NULL, -- JSON string
                kutular TEXT NOT NULL, -- JSON string
                toplam_yas_tutun REAL NOT NULL,
                toplam_kuru_tutun REAL NOT NULL,
                yas_kuru_orani REAL NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'jti_scv_kirim': '''CREATE TABLE IF NOT EXISTS jti_scv_kirim (
                id SERIAL PRIMARY KEY,
                placeholder_col TEXT
            );''',
            'jti_scv_kirim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS jti_scv_kirim_dayibasi_table (
                id SERIAL PRIMARY KEY,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                UNIQUE(dayibasi, tarih)
            );''',
            'jti_scv_kirim_gunluk': '''CREATE TABLE IF NOT EXISTS jti_scv_kirim_gunluk (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                bohcaSayisi INTEGER,
                agirlik_id INTEGER,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES jti_scv_kirim_dayibasi_table(id)
            );''',
            'jti_scv_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS jti_scv_kirim_agirlik (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES jti_scv_kirim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'jti_scv_dizim': '''CREATE TABLE IF NOT EXISTS jti_scv_dizim (
                id SERIAL PRIMARY KEY,
                placeholder_col TEXT
            );''',
            'jti_scv_dizim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS jti_scv_dizim_dayibasi_table (
                id SERIAL PRIMARY KEY,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'jti_scv_dizim_gunluk': '''CREATE TABLE IF NOT EXISTS jti_scv_dizim_gunluk (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                diziAdedi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES jti_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'jti_scv_dizim_agirlik': '''CREATE TABLE IF NOT EXISTS jti_scv_dizim_agirlik (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES jti_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'jti_scv_kutulama': '''CREATE TABLE IF NOT EXISTS jti_scv_kutulama (
                id SERIAL PRIMARY KEY,
                placeholder_col TEXT
            );''',
            'jti_scv_kutulama_dayibasi_table': '''CREATE TABLE IF NOT EXISTS jti_scv_kutulama_dayibasi_table (
                id SERIAL PRIMARY KEY,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'jti_scv_kutulama_kuru_kg': '''CREATE TABLE IF NOT EXISTS jti_scv_kutulama_kuru_kg (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                value REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES jti_scv_kutulama_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'jti_scv_kutulama_sera_yas_kg': '''CREATE TABLE IF NOT EXISTS jti_scv_kutulama_sera_yas_kg (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                value REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES jti_scv_kutulama_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_scv_dizim': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim (
                id SERIAL PRIMARY KEY,
                placeholder_col TEXT
            );''',
            'pmi_scv_dizim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_dayibasi_table (
                id SERIAL PRIMARY KEY,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'pmi_scv_dizim_gunluk': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_gunluk (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                diziAdedi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_scv_dizim_agirlik': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_agirlik (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',

            
            'pmi_topping_dizim': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim (
                id SERIAL PRIMARY KEY,
                placeholder_col TEXT
            );''',
            'pmi_topping_dizim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_dayibasi_table (
                id SERIAL PRIMARY KEY,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'pmi_topping_dizim_gunluk': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_gunluk (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                diziAdedi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_topping_dizim_agirlik': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_agirlik (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'scv_sera': '''CREATE TABLE IF NOT EXISTS scv_sera (
                id SERIAL PRIMARY KEY,
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'scv_sera_yerleri': '''CREATE TABLE IF NOT EXISTS scv_sera_yerleri (
                id SERIAL PRIMARY KEY,
                sera_yeri TEXT NOT NULL UNIQUE,
                toplam_sera_sayisi INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'scv_kutulama': '''CREATE TABLE IF NOT EXISTS scv_kutulama (
                id SERIAL PRIMARY KEY,
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'pmi_scv_dizim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_dayibasi_table (
                id SERIAL PRIMARY KEY,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'pmi_scv_dizim_gunluk': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_gunluk (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                diziAdedi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_scv_dizim_agirlik': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_agirlik (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_scv_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',

            'pmi_topping_dizim_dayibasi_table': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_dayibasi_table (
                id SERIAL PRIMARY KEY,
                tarih TEXT NOT NULL,
                dayibasi TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'pmi_topping_dizim_gunluk': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_gunluk (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                diziAdedi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'pmi_topping_dizim_agirlik': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_agirlik (
                id SERIAL PRIMARY KEY,
                dayibasi_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(dayibasi_id) REFERENCES pmi_topping_dizim_dayibasi_table(id) ON DELETE CASCADE
            );''',
            'sevkiyat': '''CREATE TABLE IF NOT EXISTS sevkiyat (
                id SERIAL PRIMARY KEY,
                tarih TEXT,
                kutu INTEGER,
                kg REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'jti_scv_dizim_yaprak': '''CREATE TABLE IF NOT EXISTS jti_scv_dizim_yaprak (
                id SERIAL PRIMARY KEY,
                agirlik_id INTEGER NOT NULL,
                yaprakSayisi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agirlik_id) REFERENCES jti_scv_dizim_agirlik(id) ON DELETE CASCADE
            );''',
            'pmi_scv_dizim_yaprak': '''CREATE TABLE IF NOT EXISTS pmi_scv_dizim_yaprak (
                id SERIAL PRIMARY KEY,
                agirlik_id INTEGER NOT NULL,
                yaprakSayisi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agirlik_id) REFERENCES pmi_scv_dizim_agirlik(id) ON DELETE CASCADE
            );''',
            'pmi_topping_dizim_yaprak': '''CREATE TABLE IF NOT EXISTS pmi_topping_dizim_yaprak (
                id SERIAL PRIMARY KEY,
                agirlik_id INTEGER NOT NULL,
                yaprakSayisi INTEGER NOT NULL,
                yazici_adi TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agirlik_id) REFERENCES pmi_topping_dizim_agirlik(id) ON DELETE CASCADE
            );''',
            # --- JTI SCV KIRIM yeni sistem için ---
            'traktor_gelis_jti_kirim': '''CREATE TABLE IF NOT EXISTS traktor_gelis_jti_kirim (
                id SERIAL PRIMARY KEY,
                tarih TEXT NOT NULL,
                plaka TEXT NOT NULL,
                gelis_no INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tarih, plaka, gelis_no)
            );''',
            'traktor_gelis_jti_kirim_dayibasi': '''CREATE TABLE IF NOT EXISTS traktor_gelis_jti_kirim_dayibasi (
                id SERIAL PRIMARY KEY,
                traktor_gelis_jti_kirim_id INTEGER NOT NULL,
                dayibasi_adi TEXT NOT NULL,
                bohca_sayisi INTEGER NOT NULL,
                FOREIGN KEY(traktor_gelis_jti_kirim_id) REFERENCES traktor_gelis_jti_kirim(id) ON DELETE CASCADE
            );''',
            'traktor_gelis_jti_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS traktor_gelis_jti_kirim_agirlik (
                id SERIAL PRIMARY KEY,
                traktor_gelis_jti_kirim_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(traktor_gelis_jti_kirim_id) REFERENCES traktor_gelis_jti_kirim(id) ON DELETE CASCADE
            );''',
            # --- PMI SCV KIRIM yeni sistem için ---
            'traktor_gelis_pmi_kirim': '''CREATE TABLE IF NOT EXISTS traktor_gelis_pmi_kirim (
                id SERIAL PRIMARY KEY,
                tarih TEXT NOT NULL,
                plaka TEXT NOT NULL,
                gelis_no INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tarih, plaka, gelis_no)
            );''',
            'traktor_gelis_pmi_kirim_dayibasi': '''CREATE TABLE IF NOT EXISTS traktor_gelis_pmi_kirim_dayibasi (
                id SERIAL PRIMARY KEY,
                traktor_gelis_pmi_kirim_id INTEGER NOT NULL,
                dayibasi_adi TEXT NOT NULL,
                bohca_sayisi INTEGER NOT NULL,
                FOREIGN KEY(traktor_gelis_pmi_kirim_id) REFERENCES traktor_gelis_pmi_kirim(id) ON DELETE CASCADE
            );''',
            'traktor_gelis_pmi_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS traktor_gelis_pmi_kirim_agirlik (
                id SERIAL PRIMARY KEY,
                traktor_gelis_pmi_kirim_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(traktor_gelis_pmi_kirim_id) REFERENCES traktor_gelis_pmi_kirim(id) ON DELETE CASCADE
            );''',
            # --- PMI TOPPING KIRIM yeni sistem için ---
            'traktor_gelis_pmi_topping_kirim': '''CREATE TABLE IF NOT EXISTS traktor_gelis_pmi_topping_kirim (
                id SERIAL PRIMARY KEY,
                tarih TEXT NOT NULL,
                plaka TEXT NOT NULL,
                gelis_no INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tarih, plaka, gelis_no)
            );''',
            'traktor_gelis_pmi_topping_kirim_dayibasi': '''CREATE TABLE IF NOT EXISTS traktor_gelis_pmi_topping_kirim_dayibasi (
                id SERIAL PRIMARY KEY,
                traktor_gelis_pmi_topping_kirim_id INTEGER NOT NULL,
                dayibasi_adi TEXT NOT NULL,
                bohca_sayisi INTEGER NOT NULL,
                FOREIGN KEY(traktor_gelis_pmi_topping_kirim_id) REFERENCES traktor_gelis_pmi_topping_kirim(id) ON DELETE CASCADE
            );''',
            'traktor_gelis_pmi_topping_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS traktor_gelis_pmi_topping_kirim_agirlik (
                id SERIAL PRIMARY KEY,
                traktor_gelis_pmi_topping_kirim_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(traktor_gelis_pmi_topping_kirim_id) REFERENCES traktor_gelis_pmi_topping_kirim(id) ON DELETE CASCADE
            );''',
            # --- IZMIR KIRIM yeni sistem için ---
            'traktor_gelis_izmir_kirim': '''CREATE TABLE IF NOT EXISTS traktor_gelis_izmir_kirim (
                id SERIAL PRIMARY KEY,
                tarih TEXT NOT NULL,
                plaka TEXT NOT NULL,
                gelis_no INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(tarih, plaka, gelis_no)
            );''',
            'traktor_gelis_izmir_kirim_dayibasi': '''CREATE TABLE IF NOT EXISTS traktor_gelis_izmir_kirim_dayibasi (
                id SERIAL PRIMARY KEY,
                traktor_gelis_izmir_kirim_id INTEGER NOT NULL,
                dayibasi_adi TEXT NOT NULL,
                bohca_sayisi INTEGER NOT NULL,
                FOREIGN KEY(traktor_gelis_izmir_kirim_id) REFERENCES traktor_gelis_izmir_kirim(id) ON DELETE CASCADE
            );''',
            'traktor_gelis_izmir_kirim_agirlik': '''CREATE TABLE IF NOT EXISTS traktor_gelis_izmir_kirim_agirlik (
                id SERIAL PRIMARY KEY,
                traktor_gelis_izmir_kirim_id INTEGER NOT NULL,
                agirlik REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(traktor_gelis_izmir_kirim_id) REFERENCES traktor_gelis_izmir_kirim(id) ON DELETE CASCADE
            );''',
            'sergi_kiriz': '''CREATE TABLE IF NOT EXISTS sergi_kiriz (
                id SERIAL PRIMARY KEY,
                sergi_no TEXT NOT NULL UNIQUE,
                toplam_sepet INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',

            'sergi_sepet_dagitim': '''CREATE TABLE IF NOT EXISTS sergi_sepet_dagitim (
                id SERIAL PRIMARY KEY,
                sergi_id INTEGER NOT NULL,
                traktor_gelis_izmir_kirim_id INTEGER NOT NULL,
                sepet_sayisi INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sergi_id) REFERENCES sergi_kiriz(id) ON DELETE CASCADE,
                FOREIGN KEY (traktor_gelis_izmir_kirim_id) REFERENCES traktor_gelis_izmir_kirim(id) ON DELETE CASCADE,
                UNIQUE (sergi_id, traktor_gelis_izmir_kirim_id)
            );''',
            'admin_users': '''CREATE TABLE IF NOT EXISTS admin_users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT,
                surname TEXT,
                is_super_admin INTEGER DEFAULT 0,
                user_type TEXT DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );''',
            'user_regions': '''CREATE TABLE IF NOT EXISTS user_regions (
                id SERIAL PRIMARY KEY,
                admin_user_id INTEGER NOT NULL,
                region_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_user_id) REFERENCES admin_users(id) ON DELETE CASCADE,
                UNIQUE(admin_user_id, region_code)
            );'''

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
        
        # admin_users tablosuna user_type kolonu ekle (eğer yoksa)
        try:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'admin_users'
            """)
            columns_info = cursor.fetchall()
            # PostgreSQL information_schema döner: (column_name,)
            columns = [col[0] for col in columns_info]  # İlk eleman kolon adı
            if 'user_type' not in columns:
                cursor.execute("ALTER TABLE admin_users ADD COLUMN user_type TEXT DEFAULT 'admin'")
                conn.commit()
                print("✅ admin_users tablosuna user_type kolonu eklendi")
        except Exception as e:
            print(f"⚠️  user_type kolonu eklenirken hata: {e}")
            import traceback
            print(traceback.format_exc())
        
        # Varsayılan admin kullanıcısını oluştur (eğer yoksa)
        try:
            cursor.execute("SELECT COUNT(*) FROM admin_users WHERE username = 'admin'")
            admin_exists = cursor.fetchone()[0] > 0
            if not admin_exists:
                # Basit şifre hash (production'da bcrypt kullanılmalı)
                import hashlib
                default_password = hashlib.md5('admin123'.encode()).hexdigest()
                cursor.execute("""
                    INSERT INTO admin_users (username, password, name, surname, is_super_admin, user_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, ('admin', default_password, 'Admin', 'User', 1, 'admin'))
                conn.commit()
                print("✅ Varsayılan admin kullanıcısı oluşturuldu (username: admin, password: admin123)")
        except Exception as e:
            print(f"⚠️  Admin kullanıcısı oluşturulurken hata: {e}")
        
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
        # PostgreSQL'de sütun kontrolü
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'scv_kutulama'
        """)
        columns = [row[0] for row in cursor.fetchall()]
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

def ensure_scv_sera_new_columns():
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (scv_sera yeni sütunlar kontrolü)")
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'scv_sera'
        """)
        columns = [row[0] for row in cursor.fetchall()]
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

def ensure_scv_dizim_region_columns():
    """SCV dizim tablolarına region kolonu ekler"""
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (scv_dizim region kolonu kontrolü)")
        return
    try:
        cursor = conn.cursor()
        # JTI SCV Dizim tabloları
        tables = [
            'jti_scv_dizim_dayibasi_table',
            'pmi_scv_dizim_dayibasi_table',
            'pmi_topping_dizim_dayibasi_table'
        ]
        for table_name in tables:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = %s
            """, (table_name,))
            columns = [row[0] for row in cursor.fetchall()]
            if 'region' not in columns:
                print(f"'{table_name}' tablosuna 'region' sütunu ekleniyor...")
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN region TEXT")
                conn.commit()
                print(f"'{table_name}' tablosuna 'region' sütunu eklendi.")
            else:
                print(f"'{table_name}' tablosunda 'region' sütunu zaten var.")
    except Exception as e:
        print(f"SCV dizim region kolonları eklenirken hata: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        conn.close()

def ensure_scv_kirim_region_columns():
    """SCV kırım tablolarına region kolonu ekler"""
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (scv_kirim region kolonu kontrolü)")
        return
    try:
        cursor = conn.cursor()
        # Kırım tabloları
        tables = [
            'traktor_gelis_jti_kirim',
            'traktor_gelis_pmi_kirim',
            'traktor_gelis_pmi_topping_kirim',
            'traktor_gelis_izmir_kirim'
        ]
        for table_name in tables:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = %s
            """, (table_name,))
            columns = [row[0] for row in cursor.fetchall()]
            if 'region' not in columns:
                print(f"'{table_name}' tablosuna 'region' sütunu ekleniyor...")
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN region TEXT")
                conn.commit()
                print(f"'{table_name}' tablosuna 'region' sütunu eklendi.")
            else:
                print(f"'{table_name}' tablosunda 'region' sütunu zaten var.")
    except Exception as e:
        print(f"SCV kırım region kolonları eklenirken hata: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        conn.close()

def ensure_scv_kutulama_region_column():
    """SCV kutulama tablosuna region kolonu ekler"""
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (scv_kutulama region kolonu kontrolü)")
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'scv_kutulama'
        """)
        columns = [row[0] for row in cursor.fetchall()]
        if 'region' not in columns:
            print("'scv_kutulama' tablosuna 'region' sütunu ekleniyor...")
            cursor.execute("ALTER TABLE scv_kutulama ADD COLUMN region TEXT")
            conn.commit()
            print("'scv_kutulama' tablosuna 'region' sütunu eklendi.")
        else:
            print("'scv_kutulama' tablosunda 'region' sütunu zaten var.")
    except Exception as e:
        print(f"SCV kutulama region kolonu eklenirken hata: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        conn.close()

def ensure_scv_sera_region_column():
    """SCV sera tablosuna region kolonu ekler"""
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (scv_sera region kolonu kontrolü)")
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'scv_sera'
        """)
        columns = [row[0] for row in cursor.fetchall()]
        if 'region' not in columns:
            print("'scv_sera' tablosuna 'region' sütunu ekleniyor...")
            cursor.execute("ALTER TABLE scv_sera ADD COLUMN region TEXT")
            conn.commit()
            print("'scv_sera' tablosuna 'region' sütunu eklendi.")
        else:
            print("'scv_sera' tablosunda 'region' sütunu zaten var.")
    except Exception as e:
        print(f"SCV sera region kolonu eklenirken hata: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        conn.close()

def ensure_fcv_region_columns():
    """FCV tablolarına region kolonu ekler"""
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (fcv region kolonu kontrolü)")
        return
    try:
        cursor = conn.cursor()
        tables = ['fcv_kirim_gunluk', 'fcv_genel']
        for table_name in tables:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = %s
            """, (table_name,))
            columns = [row[0] for row in cursor.fetchall()]
            if 'region' not in columns:
                print(f"'{table_name}' tablosuna 'region' sütunu ekleniyor...")
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN region TEXT")
                conn.commit()
                print(f"'{table_name}' tablosuna 'region' sütunu eklendi.")
            else:
                print(f"'{table_name}' tablosunda 'region' sütunu zaten var.")
    except Exception as e:
        print(f"FCV region kolonları eklenirken hata: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        conn.close()

def ensure_sevkiyat_region_column():
    """Sevkiyat tablosuna region kolonu ekler"""
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (sevkiyat region kolonu kontrolü)")
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'sevkiyat'
        """)
        columns = [row[0] for row in cursor.fetchall()]
        if 'region' not in columns:
            print("'sevkiyat' tablosuna 'region' sütunu ekleniyor...")
            cursor.execute("ALTER TABLE sevkiyat ADD COLUMN region TEXT")
            conn.commit()
            print("'sevkiyat' tablosuna 'region' sütunu eklendi.")
        else:
            print("'sevkiyat' tablosunda 'region' sütunu zaten var.")
    except Exception as e:
        print(f"Sevkiyat region kolonu eklenirken hata: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        conn.close()

def ensure_scv_sera_yerleri_region_column():
    """SCV sera yerleri tablosuna region kolonu ekler"""
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantı hatası (scv_sera_yerleri region kolonu kontrolü)")
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'scv_sera_yerleri'
        """)
        columns = [row[0] for row in cursor.fetchall()]
        if 'region' not in columns:
            print("'scv_sera_yerleri' tablosuna 'region' sütunu ekleniyor...")
            cursor.execute("ALTER TABLE scv_sera_yerleri ADD COLUMN region TEXT")
            conn.commit()
            print("'scv_sera_yerleri' tablosuna 'region' sütunu eklendi.")
        else:
            print("'scv_sera_yerleri' tablosunda 'region' sütunu zaten var.")
    except Exception as e:
        print(f"SCV sera yerleri region kolonu eklenirken hata: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        conn.close()

# --- API Endpointleri ---
#-----------------------------------------------------------------------------------------------

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
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        params = (
            data['firinNo'], data['tarla'], data['turSayisi'], data['gTarih'], data['cTarih'],
            data['yasKg'], data['kuruKg'], data['ortalama'], data['koliSayisi'], data['yakitToplam']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Veri başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        region = request.args.get('region')
        if region:
            cursor.execute("SELECT id, firinNo, tarla, turSayisi, gTarih, cTarih, yasKg, kuruKg, ortalama, koliSayisi, yakitToplam FROM fcv_genel WHERE region = %s ORDER BY id DESC", (region,))
        else:
            cursor.execute("SELECT id, firinNo, tarla, turSayisi, gTarih, cTarih, yasKg, kuruKg, ortalama, koliSayisi, yakitToplam FROM fcv_genel ORDER BY id DESC")
        
        # Sütun adlarını al
        columns = [column[0] for column in cursor.description]
        # Sonuçları dict listesine çevir
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        return jsonify(results)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

# --- FCV Kırım API Endpointleri (YENİ YAPI) ---
#-----------------------------------------------------------------------------------------------------
@app.route('/api/fcv_kirim/summary', methods=['GET'])
def get_kirim_summary():
    tarih = request.args.get('tarih')
    user_id = request.args.get('userId')
    region = request.args.get('region')
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
        sql += ' AND g.tarih = %s'
        params.append(tarih)
    if user_id:
        sql += ' AND u.id = %s'
        params.append(user_id)
    if region:
        sql += ' AND g.region = %s'
        params.append(region)
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/fcv_kirim/gunluk', methods=['POST'])
def add_or_update_gunluk_entry():
    """Bir kullanıcı ve tarih için günlük girişi ekler veya günceller."""
    data = request.get_json()
    required = ['userId', 'tarih', 'bocaSayisi']
    if not all(k in data for k in required):
        return jsonify({'message': 'userId, tarih ve bocaSayisi zorunludur.'}), 400
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    
    sql_check = "SELECT id FROM fcv_kirim_gunluk WHERE userId = %s AND tarih = %s AND region = %s"
    sql_insert = "INSERT INTO fcv_kirim_gunluk (userId, tarih, bocaSayisi, yazici_adi, region) VALUES (%s, %s, %s, %s, %s)"
    sql_update = "UPDATE fcv_kirim_gunluk SET bocaSayisi = %s, yazici_adi = %s WHERE id = %s"
    
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['userId'], data['tarih'], region))
        existing = cursor.fetchone()
        if existing:
            # Bölge kontrolü
            cursor.execute("SELECT region FROM fcv_kirim_gunluk WHERE id = %s", (existing[0],))
            existing_region = cursor.fetchone()
            if existing_region and existing_region[0] != region:
                return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
            cursor.execute(sql_update, (data['bocaSayisi'], data['yazici_adi'], existing[0]))
        else:
            cursor.execute(sql_insert, (data['userId'], data['tarih'], data['bocaSayisi'], data['yazici_adi'], region))
        conn.commit()
        return jsonify({'message': 'Günlük giriş başarıyla kaydedildi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/fcv_kirim/agirlik', methods=['POST'])
def add_agirlik_entry():
    """Bir günlük kaydına yeni bir ağırlık ekler."""
    data = request.get_json()
    if not data.get('gunlukId') or not data.get('agirlik'):
        return jsonify({'message': 'gunlukId ve agirlik zorunludur.'}), 400
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
        
    sql = "INSERT INTO fcv_kirim_agirlik (gunlukId, agirlik, yazici_adi) VALUES (%s, %s, %s)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - gunlukId'den region'ı kontrol et
        cursor.execute("SELECT region FROM fcv_kirim_gunluk WHERE id = %s", (data['gunlukId'],))
        gunluk_region = cursor.fetchone()
        if not gunluk_region:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        if gunluk_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı: Bu günlük kaydı farklı bir bölgeye ait.'}), 403
        cursor.execute(sql, (data['gunlukId'], data['agirlik'], data['yazici_adi']))
        conn.commit()
        return jsonify({'message': 'Ağırlık başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/fcv_kirim/agirlik/details', methods=['GET'])
def get_agirlik_details_by_gunlukId():
    """Bir gunlukId'ye ait tüm ağırlık girişlerini döner."""
    gunluk_id = request.args.get('gunlukId')
    if not gunluk_id:
        return jsonify({'message': 'gunlukId parametresi zorunludur.'}), 400
        
    sql = "SELECT id, agirlik, created_at FROM fcv_kirim_agirlik WHERE gunlukId = %s ORDER BY id"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (gunluk_id,))
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/fcv_kirim/agirlik/<int:agirlik_id>', methods=['DELETE'])
def delete_agirlik_entry(agirlik_id):
    """Bir ağırlık girişini siler."""
    sql = "DELETE FROM fcv_kirim_agirlik WHERE id = %s"
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

# --- İzmir Kırım API Endpointleri ---
#-----------------------------------------------------------------------------------------------------
# İzmir Kutulama için eksik endpoint'ler - Flask app'inize ekleyin
@app.route('/api/izmir_kutulama', methods=['POST'])
def handle_izmir_kutulama():
    try:
        data = request.get_json()
        
        # Gerekli alan kontrolü
        required_fields = ['tarih', 'dayibasi', 'sergi_numaralari', 'kutular']
        if not all(field in data for field in required_fields):
            return jsonify({'message': f'Eksik alanlar: {required_fields}'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
        INSERT INTO izmir_kutulama (
            tarih, dayibasi, sergi_numaralari, kutular,
            toplam_yas_tutun, toplam_kuru_tutun, yas_kuru_orani, yazici_adi
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            data['tarih'],
            data['dayibasi'],
            json.dumps(data['sergi_numaralari']),  # JSON string
            json.dumps(data['kutular']),           # JSON string
            data.get('toplam_yas_tutun', 0),
            data.get('toplam_kuru_tutun', 0),
            data.get('yas_kuru_orani', 0),
            data.get('yazici_adi', 'Bilinmiyor')
        )
        
        cursor.execute(sql, params)
        conn.commit()
        
        return jsonify({'message': 'Kayıt başarıyla eklendi'}), 201
        
    except Exception as e:
        return jsonify({'message': f'Sunucu hatası: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

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

# Flask örneği
@app.route('/api/bosaltilan_sergiler', methods=['GET'])
def get_bosaltilan_sergiler():
    try:
        conn = get_db_connection()
        # Boşaltılan sergi numaralarını al
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT DISTINCT jsonb_array_elements_text(sergi_numaralari::jsonb) as sergi_no
            FROM izmir_kutulama
        """)
        
        results = [row['sergi_no'] for row in cursor.fetchall()]
        return jsonify(results)
        
    except Exception as e:
        return jsonify({'message': f'Hata: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/izmir_kutulama/dolu_sergiler', methods=['GET'])
def get_dolu_sergiler():
    """Kırım verilerinden dolu sergileri getir"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Dolu sergileri traktor kırım verilerinden al
        cursor.execute("""
            SELECT DISTINCT 
                sk.sergi_no,
                sk.toplam_sepet,
                'dolu' as durum,
                COALESCE(AVG(tka.agirlik), 0) as ortalama_agirlik
            FROM sergi_kiriz sk
            LEFT JOIN sergi_sepet_dagitim ssd ON sk.id = ssd.sergi_id
            LEFT JOIN traktor_gelis_izmir_kirim_agirlik tka ON ssd.traktor_gelis_izmir_kirim_id = tka.traktor_gelis_izmir_kirim_id
            WHERE sk.toplam_sepet >= 150
            GROUP BY sk.sergi_no, sk.toplam_sepet
            ORDER BY sk.sergi_no
        """)
        
        columns = [column[0] for column in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            sergi_data = dict(zip(columns, row))
            # Yaş tütün kg hesapla (sepet sayısı * ortalama ağırlık)
            yaş_tutun_kg = sergi_data['toplam_sepet'] * sergi_data['ortalama_agirlik']
            
            results.append({
                'sergi_no': sergi_data['sergi_no'],
                'durum': sergi_data['durum'],
                'yaş_tutun_kg': round(yaş_tutun_kg, 2),
                'toplam_sepet': sergi_data['toplam_sepet']
            })
        
        return jsonify(results)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/izmir_kutulama/sergi_bosalt', methods=['POST'])
def bosalt_sergiler():
    """Seçili sergileri boşaltılmış olarak işaretle"""
    data = request.get_json()
    sergi_numaralari = data.get('sergi_numaralari', [])
    
    if not sergi_numaralari:
        return jsonify({'message': 'Sergi numaraları gerekli.'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Sergileri boşaltılmış olarak işaretle (toplam_sepet = 0)
        for sergi_no in sergi_numaralari:
            cursor.execute("""
                UPDATE sergi_kiriz 
                SET toplam_sepet = 0, updated_at = CURRENT_TIMESTAMP
                WHERE sergi_no = %s
            """, (sergi_no,))
        
        conn.commit()
        return jsonify({'message': f'{len(sergi_numaralari)} sergi başarıyla boşaltıldı.'}), 200
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()
#------------------------------------------------------------------------------------------------------------
#--scv jtı dizim api endpointleri-------------------------------------------------
@app.route('/api/jti_scv_dizim/summary', methods=['GET'])
def get_jti_scv_dizim_summary():
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge parametresini al
        region = request.args.get('region')
        
        # Region kolonunun varlığını kontrol et
        try:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'jti_scv_dizim_dayibasi_table' AND column_name = 'region'
            """)
            has_region = cursor.fetchone() is not None
            if not has_region:
                # Region kolonu yoksa ekle
                cursor.execute("ALTER TABLE jti_scv_dizim_dayibasi_table ADD COLUMN IF NOT EXISTS region TEXT")
                conn.commit()
        except Exception as col_check_error:
            print(f"Region kolonu kontrolü hatası: {col_check_error}")
        
        # SQL sorgusuna bölge filtresi ekle
        if region:
            cursor.execute('''
                SELECT 
                    d.id as dayibasi_id,
                    d.tarih,
                    d.dayibasi,
                    g.id as gunluk_id,
                    g.diziAdedi,
                    g.yazici_adi,
                    COALESCE((SELECT COUNT(a.id) FROM jti_scv_dizim_agirlik a WHERE a.dayibasi_id = d.id), 0) as girilenAgirlikSayisi,
                    COALESCE((SELECT AVG(a.agirlik) FROM jti_scv_dizim_agirlik a WHERE a.dayibasi_id = d.id), 0) as ortalamaAgirlik
                FROM jti_scv_dizim_dayibasi_table d
                LEFT JOIN jti_scv_dizim_gunluk g ON d.id = g.dayibasi_id
                WHERE d.region = %s
                ORDER BY d.tarih DESC, d.dayibasi
            ''', (region,))
        else:
            cursor.execute('''
                SELECT 
                    d.id as dayibasi_id,
                    d.tarih,
                    d.dayibasi,
                    g.id as gunluk_id,
                    g.diziAdedi,
                    g.yazici_adi,
                    COALESCE((SELECT COUNT(a.id) FROM jti_scv_dizim_agirlik a WHERE a.dayibasi_id = d.id), 0) as girilenAgirlikSayisi,
                    COALESCE((SELECT AVG(a.agirlik) FROM jti_scv_dizim_agirlik a WHERE a.dayibasi_id = d.id), 0) as ortalamaAgirlik
                FROM jti_scv_dizim_dayibasi_table d
                LEFT JOIN jti_scv_dizim_gunluk g ON d.id = g.dayibasi_id
                ORDER BY d.tarih DESC, d.dayibasi
            ''')
        
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        for r in results:
            # PostgreSQL column name'leri lowercase olabilir, camelCase'e çevir
            if 'diziadedi' in r and 'diziAdedi' not in r:
                r['diziAdedi'] = r['diziadedi']
            if 'gunluk_id' not in r and 'gunlukid' in r:
                r['gunluk_id'] = r['gunlukid']
            if 'dayibasi_id' not in r and 'dayibasiid' in r:
                r['dayibasi_id'] = r['dayibasiid']
            
            # diziAdedi değerini açıkça yazdır (debug için)
            print(f"DEBUG - dayibasi_id: {r.get('dayibasi_id')}, diziAdedi from DB: {r.get('diziAdedi')}, diziadedi: {r.get('diziadedi')}, type: {type(r.get('diziAdedi'))}")
            
            # diziAdedi'yi integer olarak ayarla, None ise None olarak bırak
            diziAdediValue = r.get('diziAdedi') or r.get('diziadedi')
            if diziAdediValue is not None:
                r['diziAdedi'] = int(diziAdediValue)
            else:
                r['diziAdedi'] = None
            
            # Tahmini toplam hesapla: Ortalama Ağırlık × Dizi Adedi
            ortalamaAgirlik = r.get('ortalamaAgirlik') or 0
            diziAdedi = r.get('diziAdedi')
            # diziAdedi None değilse ve 0'dan büyükse hesapla
            if ortalamaAgirlik and ortalamaAgirlik > 0 and diziAdedi is not None and diziAdedi > 0:
                r['toplamTahminiKg'] = float(ortalamaAgirlik) * float(diziAdedi)
            else:
                r['toplamTahminiKg'] = 0
            
            # İlk 10 agirlik ve yaprakSayisi
            cursor.execute("SELECT id, agirlik FROM jti_scv_dizim_agirlik WHERE dayibasi_id = %s ORDER BY id LIMIT 10", (r['dayibasi_id'],))
            agirliklar = cursor.fetchall()
            agirlikDetails = []
            for agirlik_row in agirliklar:
                agirlik_id, agirlik = agirlik_row
                cursor.execute("SELECT yaprakSayisi FROM jti_scv_dizim_yaprak WHERE agirlik_id = %s ORDER BY id DESC LIMIT 1", (agirlik_id,))
                yaprak = cursor.fetchone()
                agirlikDetails.append({
                    'agirlik': agirlik,
                    'yaprakSayisi': yaprak[0] if yaprak else None
                })
            r['agirlikDetails'] = agirlikDetails
        
        return jsonify(results)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"JTI SCV Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_dizim/dayibasi', methods=['POST'])
def add_jti_scv_dizim_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    sql_check = "SELECT id FROM jti_scv_dizim_dayibasi_table WHERE dayibasi = %s AND tarih = %s AND region = %s"
    sql_insert = "INSERT INTO jti_scv_dizim_dayibasi_table (tarih, dayibasi, region) VALUES (%s, %s, %s)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['dayibasi'], data['tarih'], region))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'message': 'Bu dayıbaşı ve tarihe ait kayıt zaten var.'}), 409
        cursor.execute(sql_insert, (data['tarih'], data['dayibasi'], region))
        conn.commit()
        return jsonify({'message': 'Dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_dizim/agirlik', methods=['POST'])
def add_jti_scv_dizim_agirlik():
    data = request.get_json()
    agirlik = data.get('agirlik')
    dayibasi_id = data.get('dayibasi_id')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if not agirlik or not dayibasi_id:
        return jsonify({'message': 'dayibasi_id ve agirlik zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    try:
        dayibasi_id = int(dayibasi_id)
        agirlik = float(agirlik)
    except (ValueError, TypeError):
        return jsonify({'message': 'dayibasi_id integer, agirlik float olmalıdır.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - dayibasi_id'nin region'ı ile eşleşmeli
        cursor.execute("SELECT region FROM jti_scv_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region:
            return jsonify({'message': 'Dayıbaşı kaydı bulunamadı.'}), 404
        if dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı: Bu dayıbaşı kaydı farklı bir bölgeye ait.'}), 403
        cursor.execute("INSERT INTO jti_scv_dizim_agirlik (dayibasi_id, agirlik, yazici_adi) VALUES (%s, %s, %s)", (dayibasi_id, agirlik, yazici_adi))
        conn.commit()
        return jsonify({'message': 'Ağırlık başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_dizim/agirlik/details', methods=['GET'])
def get_jti_scv_dizim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    region = request.args.get('region')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        if region:
            cursor.execute("SELECT region FROM jti_scv_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
            dayibasi_region = cursor.fetchone()
            if not dayibasi_region:
                return jsonify({'message': 'Dayıbaşı kaydı bulunamadı.'}), 404
            if dayibasi_region[0] != region:
                return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        sql = "SELECT id, agirlik, yazici_adi, created_at FROM jti_scv_dizim_agirlik WHERE dayibasi_id = %s ORDER BY id"
        cursor.execute(sql, (dayibasi_id,))
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            cursor.execute("SELECT id, yaprakSayisi FROM jti_scv_dizim_yaprak WHERE agirlik_id = %s ORDER BY id DESC LIMIT 1", (row_dict['id'],))
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/jti_scv_dizim/gunluk', methods=['POST'])
def add_or_update_jti_scv_dizim_gunluk():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    diziAdedi = data.get('bohcaSayisi')  # frontend 'bohcaSayisi' gönderiyor, burada diziAdedi olarak kaydediyoruz
    yazici_adi = data.get('yazici_adi') or ''  # yazici_adi opsiyonel, None ise boş string
    if not dayibasi_id or diziAdedi is None:
        return jsonify({'message': 'dayibasi_id ve diziAdedi zorunludur.'}), 400
    
    # Veri tipi dönüşümleri
    try:
        dayibasi_id = int(dayibasi_id)
        diziAdedi = int(diziAdedi)
    except (ValueError, TypeError):
        return jsonify({'message': 'dayibasi_id ve diziAdedi integer olmalıdır.'}), 400
    
    # diziAdedi 0 olamaz kontrolü
    if diziAdedi <= 0:
        return jsonify({'message': 'diziAdedi 0\'dan büyük olmalıdır.'}), 400
    
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Kayıt var mı kontrol et
        cursor.execute("SELECT id FROM jti_scv_dizim_gunluk WHERE dayibasi_id = %s", (dayibasi_id,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE jti_scv_dizim_gunluk SET diziAdedi = %s, yazici_adi = %s WHERE id = %s", (diziAdedi, yazici_adi, existing[0]))
            conn.commit()
            # Kayıt sonrası doğrulama
            cursor.execute("SELECT diziAdedi FROM jti_scv_dizim_gunluk WHERE id = %s", (existing[0],))
            verify = cursor.fetchone()
            print(f"JTI SCV Dizim - UPDATE: dayibasi_id={dayibasi_id}, diziAdedi={diziAdedi}, kaydedilen={verify[0] if verify else 'None'}")
            return jsonify({'message': 'Dizi adedi güncellendi.', 'gunluk_id': existing[0], 'diziAdedi': diziAdedi}), 200
        else:
            cursor.execute("INSERT INTO jti_scv_dizim_gunluk (dayibasi_id, diziAdedi, yazici_adi) VALUES (%s, %s, %s) RETURNING id", (dayibasi_id, diziAdedi, yazici_adi))
            new_id = cursor.fetchone()[0]
            conn.commit()
            # Kayıt sonrası doğrulama
            cursor.execute("SELECT diziAdedi FROM jti_scv_dizim_gunluk WHERE id = %s", (new_id,))
            verify = cursor.fetchone()
            print(f"JTI SCV Dizim - INSERT: dayibasi_id={dayibasi_id}, diziAdedi={diziAdedi}, kaydedilen={verify[0] if verify else 'None'}")
            return jsonify({'message': 'Dizi adedi eklendi.', 'gunluk_id': new_id, 'id': new_id, 'diziAdedi': diziAdedi}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"JTI SCV Dizim gunluk hatası: {error_trace}")
        conn.rollback()
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        # Bölge parametresini al
        region = request.args.get('region')
        
        # Region kolonunun varlığını kontrol et
        try:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'pmi_scv_dizim_dayibasi_table' AND column_name = 'region'
            """)
            has_region = cursor.fetchone() is not None
            if not has_region:
                # Region kolonu yoksa ekle
                cursor.execute("ALTER TABLE pmi_scv_dizim_dayibasi_table ADD COLUMN IF NOT EXISTS region TEXT")
                conn.commit()
        except Exception as col_check_error:
            print(f"Region kolonu kontrolü hatası: {col_check_error}")
        
        # SQL sorgusuna bölge filtresi ekle
        if region:
            cursor.execute('''
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi,
                g.id as gunluk_id,
                    g.diziAdedi,
                g.yazici_adi,
                    COALESCE((SELECT COUNT(a.id) FROM pmi_scv_dizim_agirlik a WHERE a.dayibasi_id = d.id), 0) as girilenAgirlikSayisi,
                    COALESCE((SELECT AVG(a.agirlik) FROM pmi_scv_dizim_agirlik a WHERE a.dayibasi_id = d.id), 0) as ortalamaAgirlik
                FROM pmi_scv_dizim_dayibasi_table d
                LEFT JOIN pmi_scv_dizim_gunluk g ON d.id = g.dayibasi_id
                WHERE d.region = %s
                ORDER BY d.tarih DESC, d.dayibasi
            ''', (region,))
        else:
            cursor.execute('''
                SELECT 
                    d.id as dayibasi_id,
                    d.tarih,
                    d.dayibasi,
                    g.id as gunluk_id,
                    g.diziAdedi,
                    g.yazici_adi,
                    COALESCE((SELECT COUNT(a.id) FROM pmi_scv_dizim_agirlik a WHERE a.dayibasi_id = d.id), 0) as girilenAgirlikSayisi,
                    COALESCE((SELECT AVG(a.agirlik) FROM pmi_scv_dizim_agirlik a WHERE a.dayibasi_id = d.id), 0) as ortalamaAgirlik
            FROM pmi_scv_dizim_dayibasi_table d
            LEFT JOIN pmi_scv_dizim_gunluk g ON d.id = g.dayibasi_id
            ORDER BY d.tarih DESC, d.dayibasi
        ''')
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            ortalamaAgirlik = r.get('ortalamaAgirlik', 0) or 0
            # diziAdedi 0 da geçerli bir değer olabilir, sadece null/None kontrolü yap
            diziAdedi = r.get('diziAdedi')
            if diziAdedi is None:
                diziAdedi = 0
            # Debug: diziAdedi değerini logla
            if r.get('dayibasi_id'):
                print(f"PMI SCV Dizim Summary - dayibasi_id={r.get('dayibasi_id')}, diziAdedi={diziAdedi}, gunluk_id={r.get('gunluk_id')}")
            r['diziAdedi'] = diziAdedi  # Backend'de diziAdedi'yi koru (0 da geçerli)
            if ortalamaAgirlik and diziAdedi:
                r['toplamTahminiKg'] = float(ortalamaAgirlik) * float(diziAdedi)
            else:
                r['toplamTahminiKg'] = 0
            # İlk 10 agirlik ve yaprakSayisi
            cursor.execute("SELECT id, agirlik FROM pmi_scv_dizim_agirlik WHERE dayibasi_id = %s ORDER BY id LIMIT 10", (r['dayibasi_id'],))
            agirliklar = cursor.fetchall()
            agirlikDetails = []
            for agirlik_row in agirliklar:
                agirlik_id, agirlik = agirlik_row
                cursor.execute("SELECT yaprakSayisi FROM pmi_scv_dizim_yaprak WHERE agirlik_id = %s ORDER BY id DESC LIMIT 1", (agirlik_id,))
                yaprak = cursor.fetchone()
                agirlikDetails.append({
                    'agirlik': agirlik,
                    'yaprakSayisi': yaprak[0] if yaprak else None
                })
            r['agirlikDetails'] = agirlikDetails
        return jsonify(results)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_dizim/dayibasi', methods=['POST'])
def add_pmi_scv_dizim_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    sql_check = "SELECT id FROM pmi_scv_dizim_dayibasi_table WHERE dayibasi = %s AND tarih = %s AND region = %s"
    sql_insert = "INSERT INTO pmi_scv_dizim_dayibasi_table (tarih, dayibasi, region) VALUES (%s, %s, %s)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['dayibasi'], data['tarih'], region))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'message': 'Bu dayıbaşı ve tarihe ait kayıt zaten var.'}), 409
        cursor.execute(sql_insert, (data['tarih'], data['dayibasi'], region))
        conn.commit()
        return jsonify({'message': 'Dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_dizim/agirlik', methods=['POST'])
def add_pmi_scv_dizim_agirlik():
    data = request.get_json()
    agirlik = data.get('agirlik')
    dayibasi_id = data.get('dayibasi_id')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if not agirlik or not dayibasi_id:
        return jsonify({'message': 'dayibasi_id ve agirlik zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - dayibasi_id'nin region'ı ile eşleşmeli
        cursor.execute("SELECT region FROM pmi_scv_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region:
            return jsonify({'message': 'Dayıbaşı kaydı bulunamadı.'}), 404
        if dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı: Bu dayıbaşı kaydı farklı bir bölgeye ait.'}), 403
        cursor.execute("INSERT INTO pmi_scv_dizim_agirlik (dayibasi_id, agirlik, yazici_adi) VALUES (%s, %s, %s)", (dayibasi_id, agirlik, yazici_adi))
        conn.commit()
        return jsonify({'message': 'Ağırlık başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_dizim/agirlik/details', methods=['GET'])
def get_pmi_scv_dizim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    region = request.args.get('region')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        if region:
            cursor.execute("SELECT region FROM pmi_scv_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
            dayibasi_region = cursor.fetchone()
            if not dayibasi_region:
                return jsonify({'message': 'Dayıbaşı kaydı bulunamadı.'}), 404
            if dayibasi_region[0] != region:
                return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        sql = "SELECT id, agirlik, yazici_adi, created_at FROM pmi_scv_dizim_agirlik WHERE dayibasi_id = %s ORDER BY id"
        cursor.execute(sql, (dayibasi_id,))
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            cursor.execute("SELECT id, yaprakSayisi FROM pmi_scv_dizim_yaprak WHERE agirlik_id = %s ORDER BY id DESC LIMIT 1", (row_dict['id'],))
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_scv_dizim/gunluk', methods=['POST'])
def add_or_update_pmi_scv_dizim_gunluk():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    diziAdedi = data.get('bohcaSayisi')  # frontend 'bohcaSayisi' gönderiyor, burada diziAdedi olarak kaydediyoruz
    region = data.get('region')
    yazici_adi = data.get('yazici_adi', '')  # yazici_adi opsiyonel, yoksa boş string
    if not dayibasi_id or diziAdedi is None:
        return jsonify({'message': 'dayibasi_id ve diziAdedi zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    
    # Veri tipi dönüşümleri
    try:
        dayibasi_id = int(dayibasi_id)
        diziAdedi = int(diziAdedi)
    except (ValueError, TypeError):
        return jsonify({'message': 'dayibasi_id ve diziAdedi integer olmalıdır.'}), 400
    
    # diziAdedi 0 olamaz kontrolü
    if diziAdedi <= 0:
        return jsonify({'message': 'diziAdedi 0\'dan büyük olmalıdır.'}), 400
    
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        cursor.execute("SELECT region FROM pmi_scv_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region:
            return jsonify({'message': 'Dayıbaşı kaydı bulunamadı.'}), 404
        if dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı: Bu dayıbaşı kaydı farklı bir bölgeye ait.'}), 403
        cursor.execute("SELECT id FROM pmi_scv_dizim_gunluk WHERE dayibasi_id = %s", (dayibasi_id,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE pmi_scv_dizim_gunluk SET diziAdedi = %s, yazici_adi = %s WHERE id = %s", (diziAdedi, yazici_adi, existing[0]))
            conn.commit()
            # Kayıt sonrası doğrulama
            cursor.execute("SELECT diziAdedi FROM pmi_scv_dizim_gunluk WHERE id = %s", (existing[0],))
            verify = cursor.fetchone()
            print(f"PMI SCV Dizim - UPDATE: dayibasi_id={dayibasi_id}, diziAdedi={diziAdedi}, kaydedilen={verify[0] if verify else 'None'}")
            return jsonify({'message': 'Dizi adedi güncellendi.', 'gunluk_id': existing[0], 'id': existing[0], 'diziAdedi': diziAdedi}), 200
        else:
            cursor.execute("INSERT INTO pmi_scv_dizim_gunluk (dayibasi_id, diziAdedi, yazici_adi) VALUES (%s, %s, %s) RETURNING id", (dayibasi_id, diziAdedi, yazici_adi))
            new_id = cursor.fetchone()[0]
            conn.commit()
            # Kayıt sonrası doğrulama
            cursor.execute("SELECT diziAdedi FROM pmi_scv_dizim_gunluk WHERE id = %s", (new_id,))
            verify = cursor.fetchone()
            print(f"PMI SCV Dizim - INSERT: dayibasi_id={dayibasi_id}, diziAdedi={diziAdedi}, kaydedilen={verify[0] if verify else 'None'}")
            return jsonify({'message': 'Dizi adedi eklendi.', 'gunluk_id': new_id, 'id': new_id, 'diziAdedi': diziAdedi}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI SCV Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        # Bölge parametresini al
        region = request.args.get('region')
        
        # Region kolonunun varlığını kontrol et
        try:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = 'pmi_topping_dizim_dayibasi_table' AND column_name = 'region'
            """)
            has_region = cursor.fetchone() is not None
            if not has_region:
                # Region kolonu yoksa ekle
                cursor.execute("ALTER TABLE pmi_topping_dizim_dayibasi_table ADD COLUMN IF NOT EXISTS region TEXT")
                conn.commit()
        except Exception as col_check_error:
            print(f"Region kolonu kontrolü hatası: {col_check_error}")
        
        # SQL sorgusuna bölge filtresi ekle
        if region:
            cursor.execute('''
            SELECT 
                d.id as dayibasi_id,
                d.tarih,
                d.dayibasi,
                g.id as gunluk_id,
                    g.diziAdedi,
                g.yazici_adi,
                    COALESCE((SELECT COUNT(a.id) FROM pmi_topping_dizim_agirlik a WHERE a.dayibasi_id = d.id), 0) as girilenAgirlikSayisi,
                    COALESCE((SELECT AVG(a.agirlik) FROM pmi_topping_dizim_agirlik a WHERE a.dayibasi_id = d.id), 0) as ortalamaAgirlik
                FROM pmi_topping_dizim_dayibasi_table d
                LEFT JOIN pmi_topping_dizim_gunluk g ON d.id = g.dayibasi_id
                WHERE d.region = %s
                ORDER BY d.tarih DESC, d.dayibasi
            ''', (region,))
        else:
            cursor.execute('''
                SELECT 
                    d.id as dayibasi_id,
                    d.tarih,
                    d.dayibasi,
                    g.id as gunluk_id,
                    g.diziAdedi,
                    g.yazici_adi,
                    COALESCE((SELECT COUNT(a.id) FROM pmi_topping_dizim_agirlik a WHERE a.dayibasi_id = d.id), 0) as girilenAgirlikSayisi,
                    COALESCE((SELECT AVG(a.agirlik) FROM pmi_topping_dizim_agirlik a WHERE a.dayibasi_id = d.id), 0) as ortalamaAgirlik
            FROM pmi_topping_dizim_dayibasi_table d
            LEFT JOIN pmi_topping_dizim_gunluk g ON d.id = g.dayibasi_id
            ORDER BY d.tarih DESC, d.dayibasi
        ''')
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        for r in results:
            ortalamaAgirlik = r.get('ortalamaAgirlik', 0) or 0
            # diziAdedi 0 da geçerli bir değer olabilir, sadece null/None kontrolü yap
            diziAdedi = r.get('diziAdedi')
            if diziAdedi is None:
                diziAdedi = 0
            # Debug: diziAdedi değerini logla
            if r.get('dayibasi_id'):
                print(f"PMI Topping Dizim Summary - dayibasi_id={r.get('dayibasi_id')}, diziAdedi={diziAdedi}, gunluk_id={r.get('gunluk_id')}")
            r['diziAdedi'] = diziAdedi  # Backend'de diziAdedi'yi koru (0 da geçerli)
            if ortalamaAgirlik and diziAdedi:
                r['toplamTahminiKg'] = float(ortalamaAgirlik) * float(diziAdedi)
            else:
                r['toplamTahminiKg'] = 0
            # İlk 10 agirlik ve yaprakSayisi
            cursor.execute("SELECT id, agirlik FROM pmi_topping_dizim_agirlik WHERE dayibasi_id = %s ORDER BY id LIMIT 10", (r['dayibasi_id'],))
            agirliklar = cursor.fetchall()
            agirlikDetails = []
            for agirlik_row in agirliklar:
                agirlik_id, agirlik = agirlik_row
                cursor.execute("SELECT yaprakSayisi FROM pmi_topping_dizim_yaprak WHERE agirlik_id = %s ORDER BY id DESC LIMIT 1", (agirlik_id,))
                yaprak = cursor.fetchone()
                agirlikDetails.append({
                    'agirlik': agirlik,
                    'yaprakSayisi': yaprak[0] if yaprak else None
                })
            r['agirlikDetails'] = agirlikDetails
        return jsonify(results)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_dizim/dayibasi', methods=['POST'])
def add_pmi_topping_dizim_dayibasi():
    data = request.get_json()
    required = ['tarih', 'dayibasi']
    if not all(k in data for k in required):
        return jsonify({'message': 'tarih ve dayibasi zorunludur.'}), 400
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    sql_check = "SELECT id FROM pmi_topping_dizim_dayibasi_table WHERE dayibasi = %s AND tarih = %s AND region = %s"
    sql_insert = "INSERT INTO pmi_topping_dizim_dayibasi_table (tarih, dayibasi, region) VALUES (%s, %s, %s)"
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        cursor.execute(sql_check, (data['dayibasi'], data['tarih'], region))
        existing = cursor.fetchone()
        if existing:
            return jsonify({'message': 'Bu dayıbaşı ve tarihe ait kayıt zaten var.'}), 409
        cursor.execute(sql_insert, (data['tarih'], data['dayibasi'], region))
        conn.commit()
        return jsonify({'message': 'Dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_dizim/agirlik', methods=['POST'])
def add_pmi_topping_dizim_agirlik():
    data = request.get_json()
    agirlik = data.get('agirlik')
    dayibasi_id = data.get('dayibasi_id')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if not agirlik or not dayibasi_id:
        return jsonify({'message': 'dayibasi_id ve agirlik zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - dayibasi_id'nin region'ı ile eşleşmeli
        cursor.execute("SELECT region FROM pmi_topping_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region:
            return jsonify({'message': 'Dayıbaşı kaydı bulunamadı.'}), 404
        if dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı: Bu dayıbaşı kaydı farklı bir bölgeye ait.'}), 403
        cursor.execute("INSERT INTO pmi_topping_dizim_agirlik (dayibasi_id, agirlik, yazici_adi) VALUES (%s, %s, %s)", (dayibasi_id, agirlik, yazici_adi))
        conn.commit()
        return jsonify({'message': 'Ağırlık başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_dizim/agirlik/details', methods=['GET'])
def get_pmi_topping_dizim_agirlik_details():
    dayibasi_id = request.args.get('dayibasi_id')
    region = request.args.get('region')
    if not dayibasi_id:
        return jsonify({'message': 'dayibasi_id parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        if region:
            cursor.execute("SELECT region FROM pmi_topping_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
            dayibasi_region = cursor.fetchone()
            if not dayibasi_region:
                return jsonify({'message': 'Dayıbaşı kaydı bulunamadı.'}), 404
            if dayibasi_region[0] != region:
                return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        sql = "SELECT id, agirlik,yazici_adi, created_at FROM pmi_topping_dizim_agirlik WHERE dayibasi_id = %s ORDER BY id"
        cursor.execute(sql, (dayibasi_id,))
        columns = [column[0] for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            cursor.execute("SELECT id, yaprakSayisi FROM pmi_topping_dizim_yaprak WHERE agirlik_id = %s ORDER BY id DESC LIMIT 1", (row_dict['id'],))
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

@app.route('/api/pmi_topping_dizim/gunluk', methods=['POST'])
def add_or_update_pmi_topping_dizim_gunluk():
    data = request.get_json()
    dayibasi_id = data.get('dayibasi_id')
    diziAdedi = data.get('bohcaSayisi')  # frontend 'bohcaSayisi' gönderiyor, burada diziAdedi olarak kaydediyoruz
    region = data.get('region')
    yazici_adi = data.get('yazici_adi', '')  # yazici_adi opsiyonel, yoksa boş string
    if not dayibasi_id or diziAdedi is None:
        return jsonify({'message': 'dayibasi_id ve diziAdedi zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    
    # Veri tipi dönüşümleri
    try:
        dayibasi_id = int(dayibasi_id)
        diziAdedi = int(diziAdedi)
    except (ValueError, TypeError):
        return jsonify({'message': 'dayibasi_id ve diziAdedi integer olmalıdır.'}), 400
    
    # diziAdedi 0 olamaz kontrolü
    if diziAdedi <= 0:
        return jsonify({'message': 'diziAdedi 0\'dan büyük olmalıdır.'}), 400
    
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        cursor.execute("SELECT region FROM pmi_topping_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region:
            return jsonify({'message': 'Dayıbaşı kaydı bulunamadı.'}), 404
        if dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı: Bu dayıbaşı kaydı farklı bir bölgeye ait.'}), 403
        cursor.execute("SELECT id FROM pmi_topping_dizim_gunluk WHERE dayibasi_id = %s", (dayibasi_id,))
        existing = cursor.fetchone()
        if existing:
            cursor.execute("UPDATE pmi_topping_dizim_gunluk SET diziAdedi = %s, yazici_adi = %s WHERE id = %s", (diziAdedi, yazici_adi, existing[0]))
            conn.commit()
            # Kayıt sonrası doğrulama
            cursor.execute("SELECT diziAdedi FROM pmi_topping_dizim_gunluk WHERE id = %s", (existing[0],))
            verify = cursor.fetchone()
            print(f"PMI Topping Dizim - UPDATE: dayibasi_id={dayibasi_id}, diziAdedi={diziAdedi}, kaydedilen={verify[0] if verify else 'None'}")
            return jsonify({'message': 'Dizi adedi güncellendi.', 'gunluk_id': existing[0], 'id': existing[0], 'diziAdedi': diziAdedi}), 200
        else:
            cursor.execute("INSERT INTO pmi_topping_dizim_gunluk (dayibasi_id, diziAdedi, yazici_adi) VALUES (%s, %s, %s) RETURNING id", (dayibasi_id, diziAdedi, yazici_adi))
            new_id = cursor.fetchone()[0]
            conn.commit()
            # Kayıt sonrası doğrulama
            cursor.execute("SELECT diziAdedi FROM pmi_topping_dizim_gunluk WHERE id = %s", (new_id,))
            verify = cursor.fetchone()
            print(f"PMI Topping Dizim - INSERT: dayibasi_id={dayibasi_id}, diziAdedi={diziAdedi}, kaydedilen={verify[0] if verify else 'None'}")
            return jsonify({'message': 'Dizi adedi eklendi.', 'gunluk_id': new_id, 'id': new_id, 'diziAdedi': diziAdedi}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO scv_sera (
            sera_yeri, alan, sera_no, dizi_sayisi, dizi_kg1, dizi_kg2, dizi_kg3, dizi_kg4, dizi_kg5, dizi_kg6,
            el_grubu, soldurma_giris_tarihi, soldurma_bitis_tarihi, region
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['sera_yeri'], data['alan'], data['sera_no'], data['dizi_sayisi'],
            data['dizi_kg1'], data['dizi_kg2'], data['dizi_kg3'], data['dizi_kg4'], data['dizi_kg5'], data['dizi_kg6'],
            data.get('el_grubu'), data.get('soldurma_giris_tarihi'), data.get('soldurma_bitis_tarihi'), region
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Sera başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        region = request.args.get('region')
        if region:
            cursor.execute("SELECT * FROM scv_sera WHERE region = %s ORDER BY id DESC", (region,))
        else:
            cursor.execute("SELECT * FROM scv_sera ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        region = request.args.get('region')
        # Hem scv_sera tablosundan hem de scv_sera_yerleri tablosundan sera yerlerini al (bölge filtresi ile)
        if region:
            cursor.execute("""
                SELECT DISTINCT sera_yeri 
                FROM (
                    SELECT sera_yeri FROM scv_sera WHERE region = %s
                    UNION
                    SELECT sera_yeri FROM scv_sera_yerleri WHERE region = %s
                ) combined_yerler
                ORDER BY sera_yeri
            """, (region, region))
        else:
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        region = request.args.get('region')
        if region:
            cursor.execute("SELECT DISTINCT sera_no FROM scv_sera WHERE region = %s ORDER BY sera_no", (region,))
        else:
            cursor.execute("SELECT DISTINCT sera_no FROM scv_sera ORDER BY sera_no")
        nolar = [row[0] for row in cursor.fetchall()]
        return jsonify(nolar)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

# --- SCV Sera Yerleri Yönetimi ---
@app.route('/api/scv_sera_yerleri', methods=['POST'])
def add_scv_sera_yeri():
    data = request.get_json()
    sera_yeri = data.get('sera_yeri')
    toplam_sera_sayisi = data.get('toplam_sera_sayisi')
    region = data.get('region')
    
    if not sera_yeri or not toplam_sera_sayisi:
        return jsonify({'message': 'Sera yeri ve toplam sera sayısı gerekli.'}), 400
    
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO scv_sera_yerleri (sera_yeri, toplam_sera_sayisi, region) VALUES (%s, %s, %s)", (sera_yeri, toplam_sera_sayisi, region))
        conn.commit()
        return jsonify({'message': 'Sera yeri başarıyla eklendi.'}), 201
    except psycopg2.IntegrityError:
        return jsonify({'message': 'Bu sera yeri zaten mevcut.'}), 409
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        region = request.args.get('region')
        if region:
            cursor.execute("""
                SELECT sy.sera_yeri, sy.toplam_sera_sayisi, 
                       COUNT(s.id) as mevcut_sera_sayisi
                FROM scv_sera_yerleri sy
                LEFT JOIN scv_sera s ON sy.sera_yeri = s.sera_yeri AND s.region = %s
                WHERE sy.region = %s
                GROUP BY sy.sera_yeri, sy.toplam_sera_sayisi
                ORDER BY sy.sera_yeri
            """, (region, region))
        else:
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO scv_kutulama (tarih, dayibasi, sera_yeri, sera_no, sera_yas_kg, kutular, toplam_kuru_kg, yas_kuru_orani, alan, yazici_adi, sera_bosaltildi, region)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            data['tarih'], data['dayibasi'], data['sera_yeri'], data['sera_no'], 
            data['sera_yas_kg'], data['kutular'], data['toplam_kuru_kg'], data['yas_kuru_orani'],
            data.get('alan'), data.get('yazici_adi'), data.get('sera_bosaltildi', 'hayir'), region
        )
        cursor.execute(sql, params)
        # Eğer sera boşaltıldıysa, scv_sera tablosunda dizi_sayisi=0 ve bosaltma_tarihi güncellenmeli
        if data.get('sera_bosaltildi') == 'evet':
            from datetime import datetime
            cursor.execute(
                "UPDATE scv_sera SET dizi_sayisi = 0, bosaltma_tarihi = %s WHERE sera_yeri = %s AND sera_no = %s",
                (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), data['sera_yeri'], data['sera_no'])
            )
        conn.commit()
        return jsonify({'message': 'Kutulama kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        region = request.args.get('region')
        if region:
            cursor.execute("SELECT * FROM scv_kutulama WHERE region = %s ORDER BY tarih DESC, id DESC", (region,))
        else:
            cursor.execute("SELECT * FROM scv_kutulama ORDER BY tarih DESC, id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        region = request.args.get('region')
        if region:
            cursor.execute("SELECT * FROM scv_kutulama WHERE tarih = %s AND region = %s ORDER BY id DESC", (tarih, region))
        else:
            cursor.execute("SELECT * FROM scv_kutulama WHERE tarih = %s ORDER BY id DESC", (tarih,))
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

# Filtre ve form değişkenleri birbirinden bağımsız olmalı
filterSeraYeri: str = ''
selectedSeraYeri: str = ''

# --- SCV Kutulama Summary API Endpoint (Düzeltilmiş) ---
@app.route('/api/scv_kutulama/summary', methods=['GET'])
def get_scv_kutulama_summary():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        region = request.args.get('region')
        if region:
            cursor.execute("SELECT alan, kutular, toplam_kuru_kg FROM scv_kutulama WHERE region = %s", (region,))
        else:
            cursor.execute("SELECT alan, kutular, toplam_kuru_kg FROM scv_kutulama")
        kutulama_kayitlari = cursor.fetchall()
        
        # İstatistikleri tutacak sözlükler
        pmi_scv = {'toplam_kayit': 0, 'toplam_kutu_kg': 0, 'toplam_kutu_sayisi': 0}
        jti_scv = {'toplam_kayit': 0, 'toplam_kutu_kg': 0, 'toplam_kutu_sayisi': 0}
        pmi_topping = {'toplam_kayit': 0, 'toplam_kutu_kg': 0, 'toplam_kutu_sayisi': 0}
        genel = {'toplam_kayit': 0, 'toplam_kutu_kg': 0, 'toplam_kutu_sayisi': 0}
        
        for row in kutulama_kayitlari:
            # Alan adını al ve normalize et
            alan = row['alan'] if isinstance(row, dict) else row[0]
            alan = str(alan).strip().lower()
            
            # Kutuları parse et
            kutular_json = row['kutular'] if isinstance(row, dict) else row[1]
            try:
                kutular = json.loads(kutular_json) if kutular_json else []
            except:
                kutular = []
            
            # Kutu istatistiklerini hesapla
            kayit_kutu_sayisi = 0
            kayit_toplam_kg = 0
            
            for kutu in kutular:
                if isinstance(kutu, dict):
                    # Yeni format: {"alan": "pmi-scv", "toplam_kg": 150, "adet": 5}
                    kayit_kutu_sayisi += kutu.get('adet', 0)
                    kayit_toplam_kg += kutu.get('toplam_kg', 0)
                else:
                    # Eski format: sadece sayı
                    if isinstance(kutu, (int, float)) and kutu > 0:
                        kayit_kutu_sayisi += 1
                        kayit_toplam_kg += kutu
            
            # Alanına göre istatistikleri güncelle
            if 'pmi' in alan and 'scv' in alan:
                pmi_scv['toplam_kayit'] += 1
                pmi_scv['toplam_kutu_sayisi'] += kayit_kutu_sayisi
                pmi_scv['toplam_kutu_kg'] += kayit_toplam_kg
            elif 'jti' in alan and 'scv' in alan:
                jti_scv['toplam_kayit'] += 1
                jti_scv['toplam_kutu_sayisi'] += kayit_kutu_sayisi
                jti_scv['toplam_kutu_kg'] += kayit_toplam_kg
            elif 'pmi' in alan and 'topping' in alan:
                pmi_topping['toplam_kayit'] += 1
                pmi_topping['toplam_kutu_sayisi'] += kayit_kutu_sayisi
                pmi_topping['toplam_kutu_kg'] += kayit_toplam_kg
            
            # Genel istatistikleri güncelle
            genel['toplam_kayit'] += 1
            genel['toplam_kutu_sayisi'] += kayit_kutu_sayisi
            genel['toplam_kutu_kg'] += kayit_toplam_kg
        
        return jsonify({
            'pmi_scv': pmi_scv,
            'jti_scv': jti_scv,
            'pmi_topping': pmi_topping,
            'genel': genel
        })
        
    except Exception as e:
        print(f"Kutulama özeti hatası: {e}")
        return jsonify({
            'pmi_scv': {'toplam_kayit': 0, 'toplam_kutu_kg': 0, 'toplam_kutu_sayisi': 0},
            'jti_scv': {'toplam_kayit': 0, 'toplam_kutu_kg': 0, 'toplam_kutu_sayisi': 0},
            'pmi_topping': {'toplam_kayit': 0, 'toplam_kutu_kg': 0, 'toplam_kutu_sayisi': 0},
            'genel': {'toplam_kayit': 0, 'toplam_kutu_kg': 0, 'toplam_kutu_sayisi': 0}
        }), 500
    finally:
        if conn:
            conn.close()

# --- Sera Boşaltma Endpoint ---
@app.route('/api/scv_sera/bosalt', methods=['POST'])
def bosalt_scv_sera():
    data = request.json
    sera_id = data.get('id')
    tarih = data.get('tarih') or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    region = data.get('region')
    if not sera_id:
        return jsonify({'error': 'Sera id gerekli'}), 400
    if not region:
        return jsonify({'error': 'region parametresi zorunludur'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'error': 'Veritabanı bağlantı hatası'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        cursor.execute("SELECT region FROM scv_sera WHERE id = %s", (sera_id,))
        sera_region = cursor.fetchone()
        if not sera_region:
            return jsonify({'error': 'Sera kaydı bulunamadı'}), 404
        if sera_region[0] != region:
            return jsonify({'error': 'Bölge uyuşmazlığı'}), 403
        cursor.execute("""
            UPDATE scv_sera
            SET dizi_sayisi=0, bosaltma_tarihi=%s
            WHERE id=%s
        """, (tarih, sera_id))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'id': sera_id, 'bosaltma_tarihi': tarih})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route("/")
def home():
    return "API çalışıyor!"

# Eski verileri temizleme endpoint'i (region kolonu NULL olan verileri siler)
@app.route('/api/cleanup_old_data', methods=['POST'])
def cleanup_old_data():
    """Region kolonu NULL olan eski verileri temizler"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        deleted_counts = {}
        
        # Tüm region kolonu olan tabloları temizle
        tables_to_clean = [
            'traktor_gelis_jti_kirim',
            'traktor_gelis_pmi_kirim',
            'traktor_gelis_pmi_topping_kirim',
            'traktor_gelis_izmir_kirim',
            'jti_scv_dizim_dayibasi_table',
            'pmi_scv_dizim_dayibasi_table',
            'pmi_topping_dizim_dayibasi_table',
            'scv_kutulama',
            'scv_sera',
            'scv_sera_yerleri',
            'fcv_kirim_gunluk',
            'fcv_genel',
            'sevkiyat'
        ]
        
        for table_name in tables_to_clean:
            try:
                # Önce region kolonunun olup olmadığını kontrol et
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' AND table_name = %s AND column_name = 'region'
                """, (table_name,))
                has_region = cursor.fetchone()
                
                if has_region:
                    # Region NULL olan kayıtları sil
                    cursor.execute(f"DELETE FROM {table_name} WHERE region IS NULL")
                    deleted_count = cursor.rowcount
                    deleted_counts[table_name] = deleted_count
                    conn.commit()
            except Exception as e:
                print(f"{table_name} tablosu temizlenirken hata: {e}")
                continue
        
        return jsonify({
            'message': 'Eski veriler temizlendi.',
            'deleted_counts': deleted_counts
        }), 200
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()


# Alan stok bilgilerini getiren endpoint
@app.route('/api/alan_stok', methods=['GET'])
def get_alan_stok():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        region = request.args.get('region')
        alanlar = {}
        
        # SCV kutulama verilerini al - alan bazında ayrı ayrı grupla (bölge filtresi ile)
        if region:
            cursor.execute("SELECT alan, kutular, toplam_kuru_kg FROM scv_kutulama WHERE region = %s", (region,))
        else:
            cursor.execute("SELECT alan, kutular, toplam_kuru_kg FROM scv_kutulama")
        scv_rows = cursor.fetchall()
        
        for row in scv_rows:
            row_alan = (row['alan'] if isinstance(row, dict) else getattr(row, 'alan', None)) or ''
            row_alan = row_alan.strip().upper()
            
            # Alan adını normalize et
            if 'JTI' in row_alan and 'SCV' in row_alan:
                alan_key = 'JTI SCV'
            elif 'PMI' in row_alan and 'SCV' in row_alan:
                alan_key = 'PMI SCV'
            elif 'PMI' in row_alan and 'TOPPING' in row_alan:
                alan_key = 'PMI TOPPING'
            else:
                alan_key = row_alan
            
            kutular_json = row['kutular'] if isinstance(row, dict) else getattr(row, 'kutular', None)
            toplam_kg = row['toplam_kuru_kg'] if isinstance(row, dict) else getattr(row, 'toplam_kuru_kg', 0) or 0
            
            try:
                kutular_array = json.loads(kutular_json) if kutular_json else []
                # Kutu sayısını hesapla - summary endpoint'indeki mantıkla aynı
                kutu_sayisi = 0
                for kutu in kutular_array:
                    if isinstance(kutu, dict):
                        # Yeni format: {"alan": "pmi-scv", "toplam_kg": 150, "adet": 5}
                        kutu_sayisi += kutu.get('adet', 0)
                    else:
                        # Eski format: sadece sayı
                        if isinstance(kutu, (int, float)) and kutu > 0:
                            kutu_sayisi += 1
            except Exception:
                kutu_sayisi = 0
            
            if alan_key not in alanlar:
                alanlar[alan_key] = {'kutu': 0, 'kg': 0}
            
            alanlar[alan_key]['kutu'] += kutu_sayisi
            alanlar[alan_key]['kg'] += toplam_kg
        
        # İzmir kutulama verilerini al - ayrı tablo (bölge filtresi ile)
        try:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'izmir_kutulama' AND column_name = 'region'")
            has_region = cursor.fetchone()
            if has_region and region:
                cursor.execute("SELECT kutular, toplam_kuru_tutun FROM izmir_kutulama WHERE region = %s", (region,))
            else:
                cursor.execute("SELECT kutular, toplam_kuru_tutun FROM izmir_kutulama")
        except:
            cursor.execute("SELECT kutular, toplam_kuru_tutun FROM izmir_kutulama")
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
            
            izmir_kg += row['toplam_kuru_tutun'] if isinstance(row, dict) else getattr(row, 'toplam_kuru_tutun', 0) or 0
        
        alanlar['İZMİR'] = {'kutu': izmir_kutu, 'kg': izmir_kg}
        
        return jsonify(alanlar), 200
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

# Sevkiyat ekleme endpoint'i (güncellenmiş)
@app.route('/api/sevkiyat', methods=['POST'])
def add_sevkiyat():
    data = request.get_json()
    istenen_kutu = int(data.get('kutu', 0))
    istenen_kg = float(data.get('kg', 0))
    alan_input = data.get('alan', '').strip()
    tarih = data.get('tarih', datetime.now().strftime('%Y-%m-%d'))
    region = data.get('region')
    
    if not alan_input:
        return jsonify({'message': 'Alan bilgisi gerekli.'}), 400
    
    if istenen_kutu <= 0 or istenen_kg <= 0:
        return jsonify({'message': 'Kutu ve KG değerleri 0\'dan büyük olmalı.'}), 400
    
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    
    # Frontend'den gelen alan adını normalize et (küçük harf, tire -> büyük harf, boşluk)
    alan_mapping = {
        'pmi-topping': 'PMI TOPPING',
        'pmi-scv': 'PMI SCV',
        'jti-scv': 'JTI SCV',
        'izmir': 'İZMİR',
        'PMI-TOPPING': 'PMI TOPPING',
        'PMI-SCV': 'PMI SCV',
        'JTI-SCV': 'JTI SCV',
        'İZMİR': 'İZMİR'
    }
    
    # Önce mapping'den bak, yoksa büyük harfe çevir
    alan = alan_mapping.get(alan_input.lower(), alan_input.upper().replace('-', ' '))
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        alanlar = {}
        
        # SCV kutulama verilerini al - alan bazında ayrı ayrı grupla (bölge filtresi ile)
        cursor.execute("SELECT id, alan, kutular, toplam_kuru_kg FROM scv_kutulama WHERE region = %s", (region,))
        scv_rows = cursor.fetchall()
        
        for row in scv_rows:
            row_alan = (row.get('alan') or '').strip().upper()
            
            # Alan adını normalize et
            if 'JTI' in row_alan and 'SCV' in row_alan:
                alan_key = 'JTI SCV'
            elif 'PMI' in row_alan and 'SCV' in row_alan:
                alan_key = 'PMI SCV'
            elif 'PMI' in row_alan and 'TOPPING' in row_alan:
                alan_key = 'PMI TOPPING'
            else:
                alan_key = row_alan
            
            kutular_json = row.get('kutular')
            toplam_kg = row.get('toplam_kuru_kg', 0) or 0
            
            kutular_array = []
            kutu_sayisi = 0
            try:
                # Eğer kutular_json zaten bir list/dict ise, direkt kullan
                if isinstance(kutular_json, (list, dict)):
                    kutular_array = kutular_json
                elif isinstance(kutular_json, str):
                    kutular_array = json.loads(kutular_json) if kutular_json else []
                else:
                    kutular_array = []
                
                # Kutu sayısını hesapla - summary endpoint'indeki mantıkla aynı
                for kutu in kutular_array:
                    if isinstance(kutu, dict):
                        # Yeni format: {"alan": "pmi-scv", "toplam_kg": 150, "adet": 5}
                        kutu_sayisi += kutu.get('adet', 0)
                    else:
                        # Eski format: sadece sayı
                        if isinstance(kutu, (int, float)) and kutu > 0:
                            kutu_sayisi += 1
            except Exception as e:
                print(f"Kutular parse hatası: {e}")
                kutular_array = []
                kutu_sayisi = 0
            
            if alan_key not in alanlar:
                alanlar[alan_key] = {'kutu': 0, 'kg': 0, 'scv_rows': []}
            
            alanlar[alan_key]['kutu'] += kutu_sayisi
            alanlar[alan_key]['kg'] += toplam_kg
            alanlar[alan_key]['scv_rows'].append({
                'id': row.get('id'),
                'kutular': kutular_array,
                'kg': toplam_kg,
                'original_alan': row_alan  # Orijinal alan adını sakla güncelleme için
            })
        
        # İzmir kutulama verilerini al (bölge filtresi ile - izmir_kutulama tablosunda region kolonu varsa)
        # Not: izmir_kutulama tablosunda region kolonu olmayabilir, kontrol et
        try:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'izmir_kutulama' AND column_name = 'region'")
            has_region = cursor.fetchone()
            if has_region:
                cursor.execute("SELECT id, kutular, toplam_kuru_tutun FROM izmir_kutulama WHERE region = %s", (region,))
            else:
                cursor.execute("SELECT id, kutular, toplam_kuru_tutun FROM izmir_kutulama")
        except:
            cursor.execute("SELECT id, kutular, toplam_kuru_tutun FROM izmir_kutulama")
        izmir_rows = cursor.fetchall()
        
        izmir_kutu = 0
        izmir_kg = 0
        izmir_data = []
        
        for row in izmir_rows:
            kutular_json = row.get('kutular')
            kutular = []
            row_kutu = 0
            try:
                # Eğer kutular_json zaten bir list/dict ise, direkt kullan
                if isinstance(kutular_json, (list, dict)):
                    kutular = kutular_json
                elif isinstance(kutular_json, str):
                    kutular = json.loads(kutular_json) if kutular_json else []
                else:
                    kutular = []
                
                # Kutu sayısını hesapla - yeni format kontrolü
                for kutu in kutular:
                    if isinstance(kutu, dict):
                        # Yeni format: {"adet": 5, "toplam_kg": 150}
                        row_kutu += kutu.get('adet', 0)
                    else:
                        # Eski format: sadece sayı
                        if isinstance(kutu, (int, float)) and kutu > 0:
                            row_kutu += 1
                izmir_kutu += row_kutu
            except Exception as e:
                print(f"İzmir kutular parse hatası: {e}")
                kutular = []
                row_kutu = 0
            
            row_kg = row.get('toplam_kuru_tutun', 0) or 0
            izmir_kg += row_kg
            
            izmir_data.append({
                'id': row.get('id'),
                'kutular': kutular,
                'kg': row_kg
            })
        
        alanlar['İZMİR'] = {'kutu': izmir_kutu, 'kg': izmir_kg, 'izmir_rows': izmir_data}
        
        # Alan stokunu kontrol et
        if alan not in alanlar:
            return jsonify({'message': f'Belirtilen alan bulunamadı: {alan} (Gelen: {alan_input})'}), 400
        
        stok = alanlar[alan]
        
        if istenen_kutu > stok['kutu']:
            return jsonify({
                'message': f'{alan} alanında yeterli kutu stoku yok! Mevcut: {stok["kutu"]} kutu, İstenen: {istenen_kutu} kutu'
            }), 400
        
        if istenen_kg > stok['kg']:
            return jsonify({
                'message': f'{alan} alanında yeterli KG stoku yok! Mevcut: {stok["kg"]:.2f} KG, İstenen: {istenen_kg} KG'
            }), 400
        
        # Stoktan düşme işlemi
        kalan_kutu = istenen_kutu
        kalan_kg = istenen_kg
        
        if alan == 'İZMİR':
            # İzmir için stok düşme
            for izmir_row in alanlar['İZMİR']['izmir_rows']:
                if kalan_kutu <= 0 and kalan_kg <= 0:
                    break
                
                kutular = izmir_row.get('kutular', [])
                # Eğer kutular bir list değilse, boş list yap
                if not isinstance(kutular, list):
                    kutular = []
                # Kutu sayısını hesapla - yeni format kontrolü
                row_kutu = 0
                for kutu in kutular:
                    if isinstance(kutu, dict):
                        # Yeni format: {"alan": "pmi-scv", "toplam_kg": 150, "adet": 5}
                        row_kutu += kutu.get('adet', 0)
                    else:
                        # Eski format: sadece sayı
                        if isinstance(kutu, (int, float)) and kutu > 0:
                            row_kutu += 1
                row_kg = izmir_row['kg']
                
                if row_kutu > 0 and row_kg > 0:
                    # Bu satırdan ne kadar düşeceğimizi hesapla
                    dusulecek_kutu = min(kalan_kutu, row_kutu)
                    kutu_orani = dusulecek_kutu / row_kutu if row_kutu > 0 else 0
                    dusulecek_kg = min(kalan_kg, row_kg * kutu_orani)
                    
                    # Kutuları güncelle - yeni format kontrolü
                    yeni_kutular = []
                    dusurulmus_kutu = 0
                    for kutu in kutular:
                        if isinstance(kutu, dict):
                            # Yeni format: {"alan": "pmi-scv", "toplam_kg": 150, "adet": 5}
                            kutu_adet = kutu.get('adet', 0)
                            if kutu_adet > 0 and dusurulmus_kutu < dusulecek_kutu:
                                kalan_adet = kutu_adet - min(kutu_adet, dusulecek_kutu - dusurulmus_kutu)
                                dusurulmus_kutu += min(kutu_adet, dusulecek_kutu - dusurulmus_kutu)
                                if kalan_adet > 0:
                                    # Kalan adet varsa güncellenmiş kutu objesini ekle
                                    yeni_kutu = kutu.copy()
                                    yeni_kutu['adet'] = kalan_adet
                                    # KG'yi de orantılı olarak güncelle
                                    if kutu.get('toplam_kg', 0) > 0:
                                        yeni_kutu['toplam_kg'] = kutu.get('toplam_kg', 0) * (kalan_adet / kutu_adet)
                                    yeni_kutular.append(yeni_kutu)
                            else:
                                yeni_kutular.append(kutu)
                        else:
                            # Eski format: sadece sayı
                            if kutu and kutu > 0 and dusurulmus_kutu < dusulecek_kutu:
                                dusurulmus_kutu += 1
                            else:
                                yeni_kutular.append(kutu)
                    
                    # Veritabanını güncelle
                    yeni_kg = max(0, row_kg - dusulecek_kg)
                    cursor.execute(
                        "UPDATE izmir_kutulama SET kutular = %s, toplam_kuru_tutun = %s WHERE id = %s",
                        (json.dumps(yeni_kutular), yeni_kg, izmir_row['id'])
                    )
                    
                    kalan_kutu -= dusulecek_kutu
                    kalan_kg -= dusulecek_kg
        
        else:
            # SCV alanları için stok düşme (alan bazında ayrı ayrı)
            if alan in alanlar and 'scv_rows' in alanlar[alan]:
                for scv_row in alanlar[alan]['scv_rows']:
                    if kalan_kutu <= 0 and kalan_kg <= 0:
                        break
                    
                    kutular = scv_row.get('kutular', [])
                    # Eğer kutular bir list değilse, boş list yap
                    if not isinstance(kutular, list):
                        kutular = []
                    # Kutu sayısını hesapla - yeni format kontrolü
                    row_kutu = 0
                    for kutu in kutular:
                        if isinstance(kutu, dict):
                            # Yeni format: {"alan": "pmi-scv", "toplam_kg": 150, "adet": 5}
                            row_kutu += kutu.get('adet', 0)
                        else:
                            # Eski format: sadece sayı
                            if isinstance(kutu, (int, float)) and kutu > 0:
                                row_kutu += 1
                    row_kg = scv_row['kg']
                    
                    if row_kutu > 0 and row_kg > 0:
                        # Bu satırdan ne kadar düşeceğimizi hesapla
                        dusulecek_kutu = min(kalan_kutu, row_kutu)
                        kutu_orani = dusulecek_kutu / row_kutu if row_kutu > 0 else 0
                        dusulecek_kg = min(kalan_kg, row_kg * kutu_orani)
                        
                        # Kutuları güncelle - yeni format kontrolü
                        yeni_kutular = []
                        dusurulmus_kutu = 0
                        for kutu in kutular:
                            if isinstance(kutu, dict):
                                # Yeni format: {"alan": "pmi-scv", "toplam_kg": 150, "adet": 5}
                                kutu_adet = kutu.get('adet', 0)
                                if kutu_adet > 0 and dusurulmus_kutu < dusulecek_kutu:
                                    kalan_adet = kutu_adet - min(kutu_adet, dusulecek_kutu - dusurulmus_kutu)
                                    dusurulmus_kutu += min(kutu_adet, dusulecek_kutu - dusurulmus_kutu)
                                    if kalan_adet > 0:
                                        # Kalan adet varsa güncellenmiş kutu objesini ekle
                                        yeni_kutu = kutu.copy()
                                        yeni_kutu['adet'] = kalan_adet
                                        # KG'yi de orantılı olarak güncelle
                                        if kutu.get('toplam_kg', 0) > 0:
                                            yeni_kutu['toplam_kg'] = kutu.get('toplam_kg', 0) * (kalan_adet / kutu_adet)
                                        yeni_kutular.append(yeni_kutu)
                                else:
                                    yeni_kutular.append(kutu)
                            else:
                                # Eski format: sadece sayı
                                if kutu and kutu > 0 and dusurulmus_kutu < dusulecek_kutu:
                                    dusurulmus_kutu += 1
                                else:
                                    yeni_kutular.append(kutu)
                        
                        # Veritabanını güncelle
                        yeni_kg = max(0, row_kg - dusulecek_kg)
                        cursor.execute(
                            "UPDATE scv_kutulama SET kutular = %s, toplam_kuru_kg = %s WHERE id = %s",
                            (json.dumps(yeni_kutular), yeni_kg, scv_row['id'])
                        )
                        
                        kalan_kutu -= dusulecek_kutu
                        kalan_kg -= dusulecek_kg
        
        # Sevkiyat kaydını ekle
        cursor.execute(
            "INSERT INTO sevkiyat (tarih, alan, kutu, kg, created_at, region) VALUES (%s, %s, %s, %s, %s, %s)",
            (tarih, alan, istenen_kutu, istenen_kg, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), region)
        )
        
        conn.commit()
        return jsonify({'message': 'Sevkiyat kaydı başarıyla eklendi.'}), 201
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Sevkiyat POST hatası: {error_trace}")
        print(f"Hata detayı: {str(e)}")
        print(f"Request data: {data}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass

# Sevkiyat listesini getiren endpoint
@app.route('/api/sevkiyat', methods=['GET'])
def get_sevkiyat():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        region = request.args.get('region')
        if region:
            cursor.execute("SELECT * FROM sevkiyat WHERE region = %s ORDER BY created_at DESC", (region,))
        else:
            cursor.execute("SELECT * FROM sevkiyat ORDER BY created_at DESC")
        rows = cursor.fetchall()
        
        sevkiyatlar = []
        for row in rows:
            sevkiyat = {
                'id': row['id'] if isinstance(row, dict) else getattr(row, 'id'),
                'tarih': row['tarih'] if isinstance(row, dict) else getattr(row, 'tarih'),
                'alan': row['alan'] if isinstance(row, dict) else getattr(row, 'alan', ''),
                'kutuAdedi': row['kutu'] if isinstance(row, dict) else getattr(row, 'kutu'),
                'toplamKg': row['kg'] if isinstance(row, dict) else getattr(row, 'kg'),
                'kayitTarihi': row['created_at'] if isinstance(row, dict) else getattr(row, 'created_at')
            }
            sevkiyatlar.append(sevkiyat)
        
        return jsonify(sevkiyatlar), 200
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

# Sevkiyat tablosunu güncelle
def update_sevkiyat_table():
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        # Alan sütunu yoksa ekle
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'sevkiyat'
        """)
        columns = [column[0] for column in cursor.fetchall()]
        
        if 'alan' not in columns:
            cursor.execute("ALTER TABLE sevkiyat ADD COLUMN alan TEXT")
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"Tablo güncelleme hatası: {e}")
        return False
    finally:
        conn.close()









@app.route('/api/genel_stok', methods=['GET'])
def get_genel_stok():
    """Genel stok bilgilerini getir - tüm departmanlar için özet (Düzeltilmiş Versiyon)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        region = request.args.get('region')
        
        # Sonuç yapısını başlat
        result = {
            'toplamlar': {
                # SCV genel toplam
                'SCV': {'kirim_kg': 0, 'kirim_bohca': 0, 'dizim_kg': 0, 'dizim_dizi': 0, 'kutulama_kg': 0, 'kutulama_kutu': 0},
                # SCV alt departmanlar (manager ekranında ayrı gösterim için)
                'JTI_SCV': {'kirim_kg': 0, 'kirim_bohca': 0, 'dizim_kg': 0, 'dizim_dizi': 0, 'kutulama_kg': 0, 'kutulama_kutu': 0},
                'PMI_SCV': {'kirim_kg': 0, 'kirim_bohca': 0, 'dizim_kg': 0, 'dizim_dizi': 0, 'kutulama_kg': 0, 'kutulama_kutu': 0},
                'SCV_TOPPING': {'kirim_kg': 0, 'kirim_bohca': 0, 'dizim_kg': 0, 'dizim_dizi': 0, 'kutulama_kg': 0, 'kutulama_kutu': 0},
                # İzmir
                'IZMIR': {'kirim_kg': 0, 'kirim_bohca': 0, 'dizim_kg': 0, 'dizim_dizi': 0, 'kutulama_kg': 0, 'kutulama_kutu': 0},
                # FCV
                'FCV': {'kirim_kg': 0, 'kirim_bohca': 0, 'kutulama_kg': 0, 'kutulama_kutu': 0},
                # Diğerleri
                'N_RUSTICA': {'kirim_kg': 0, 'kirim_bohca': 0, 'dizim_kg': 0, 'dizim_dizi': 0, 'kutulama_kg': 0, 'kutulama_kutu': 0},
                'BASMA': {'kirim_kg': 0, 'kirim_bohca': 0, 'dizim_kg': 0, 'dizim_dizi': 0, 'kutulama_kg': 0, 'kutulama_kutu': 0},
                'PRILEP': {'kirim_kg': 0, 'kirim_bohca': 0, 'dizim_kg': 0, 'dizim_dizi': 0, 'kutulama_kg': 0, 'kutulama_kutu': 0},
                'KATERINI': {'kirim_kg': 0, 'kirim_bohca': 0, 'dizim_kg': 0, 'dizim_dizi': 0, 'kutulama_kg': 0, 'kutulama_kutu': 0}
            },
            'detaylar': {}
        }

        # === 1. SCV BÖLÜMÜ ===
        
        # 1.1 SCV Kırım (JTI + PMI)
        if region:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(ta.agirlik), 0) as kg, 
                    COALESCE(SUM(td.bohca_sayisi), 0) as bohca
                FROM traktor_gelis_jti_kirim t
                LEFT JOIN traktor_gelis_jti_kirim_agirlik ta ON t.id = ta.traktor_gelis_jti_kirim_id
                LEFT JOIN traktor_gelis_jti_kirim_dayibasi td ON t.id = td.traktor_gelis_jti_kirim_id
                WHERE ta.agirlik > 0 AND t.region = %s
            """, (region,))
        else:
            cursor.execute("""
            SELECT 
                COALESCE(SUM(ta.agirlik), 0) as kg, 
                COALESCE(SUM(td.bohca_sayisi), 0) as bohca
            FROM traktor_gelis_jti_kirim t
            LEFT JOIN traktor_gelis_jti_kirim_agirlik ta ON t.id = ta.traktor_gelis_jti_kirim_id
            LEFT JOIN traktor_gelis_jti_kirim_dayibasi td ON t.id = td.traktor_gelis_jti_kirim_id
            WHERE ta.agirlik > 0
        """)
        scv_kirim = cursor.fetchone()
        result['toplamlar']['SCV']['kirim_kg'] += float(scv_kirim[0])
        result['toplamlar']['SCV']['kirim_bohca'] += int(scv_kirim[1])
        # JTI SCV detay
        result['toplamlar']['JTI_SCV']['kirim_kg'] = float(scv_kirim[0])
        result['toplamlar']['JTI_SCV']['kirim_bohca'] = int(scv_kirim[1])
        
        # PMI SCV Kırım
        if region:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(ta.agirlik), 0) as kg, 
                    COALESCE(SUM(td.bohca_sayisi), 0) as bohca
                FROM traktor_gelis_pmi_kirim t
                LEFT JOIN traktor_gelis_pmi_kirim_agirlik ta ON t.id = ta.traktor_gelis_pmi_kirim_id
                LEFT JOIN traktor_gelis_pmi_kirim_dayibasi td ON t.id = td.traktor_gelis_pmi_kirim_id
                WHERE ta.agirlik > 0 AND t.region = %s
            """, (region,))
        else:
            cursor.execute("""
            SELECT 
                COALESCE(SUM(ta.agirlik), 0) as kg, 
                COALESCE(SUM(td.bohca_sayisi), 0) as bohca
            FROM traktor_gelis_pmi_kirim t
            LEFT JOIN traktor_gelis_pmi_kirim_agirlik ta ON t.id = ta.traktor_gelis_pmi_kirim_id
            LEFT JOIN traktor_gelis_pmi_kirim_dayibasi td ON t.id = td.traktor_gelis_pmi_kirim_id
            WHERE ta.agirlik > 0
        """)
        pmi_kirim = cursor.fetchone()
        result['toplamlar']['SCV']['kirim_kg'] += float(pmi_kirim[0])
        result['toplamlar']['SCV']['kirim_bohca'] += int(pmi_kirim[1])
        # PMI SCV detay
        result['toplamlar']['PMI_SCV']['kirim_kg'] = float(pmi_kirim[0])
        result['toplamlar']['PMI_SCV']['kirim_bohca'] = int(pmi_kirim[1])

        # PMI Topping Kırım
        if region:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(ta.agirlik), 0) as kg, 
                    COALESCE(SUM(td.bohca_sayisi), 0) as bohca
                FROM traktor_gelis_pmi_topping_kirim t
                LEFT JOIN traktor_gelis_pmi_topping_kirim_agirlik ta ON t.id = ta.traktor_gelis_pmi_topping_kirim_id
                LEFT JOIN traktor_gelis_pmi_topping_kirim_dayibasi td ON t.id = td.traktor_gelis_pmi_topping_kirim_id
                WHERE ta.agirlik > 0 AND t.region = %s
            """, (region,))
        else:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(ta.agirlik), 0) as kg, 
                    COALESCE(SUM(td.bohca_sayisi), 0) as bohca
                FROM traktor_gelis_pmi_topping_kirim t
                LEFT JOIN traktor_gelis_pmi_topping_kirim_agirlik ta ON t.id = ta.traktor_gelis_pmi_topping_kirim_id
                LEFT JOIN traktor_gelis_pmi_topping_kirim_dayibasi td ON t.id = td.traktor_gelis_pmi_topping_kirim_id
                WHERE ta.agirlik > 0
            """)
        pmi_topping_kirim = cursor.fetchone()
        result['toplamlar']['SCV']['kirim_kg'] += float(pmi_topping_kirim[0])
        result['toplamlar']['SCV']['kirim_bohca'] += int(pmi_topping_kirim[1])
        # SCV TOPPING detay
        result['toplamlar']['SCV_TOPPING']['kirim_kg'] = float(pmi_topping_kirim[0])
        result['toplamlar']['SCV_TOPPING']['kirim_bohca'] = int(pmi_topping_kirim[1])

        # 1.2 SCV Dizim (JTI + PMI)
        # Dizim KG için: sadece ağırlık > 0 olanları topla
        if region:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(a.agirlik), 0) as kg
                FROM jti_scv_dizim_gunluk g
                JOIN jti_scv_dizim_dayibasi_table d ON g.dayibasi_id = d.id
                LEFT JOIN jti_scv_dizim_agirlik a ON g.dayibasi_id = a.dayibasi_id
                WHERE a.agirlik > 0 AND d.region = %s
            """, (region,))
        else:
            cursor.execute("""
            SELECT 
                    COALESCE(SUM(a.agirlik), 0) as kg
            FROM jti_scv_dizim_gunluk g
            LEFT JOIN jti_scv_dizim_agirlik a ON g.dayibasi_id = a.dayibasi_id
            WHERE a.agirlik > 0
        """)
        scv_dizim_kg = cursor.fetchone()[0]
        
        # Dizim Dizi için: tüm gunluk kayıtlarını topla (ağırlık koşulu olmadan)
        if region:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(g.diziAdedi), 0) as dizi
                FROM jti_scv_dizim_gunluk g
                JOIN jti_scv_dizim_dayibasi_table d ON g.dayibasi_id = d.id
                WHERE d.region = %s AND g.diziAdedi > 0
            """, (region,))
        else:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(g.diziAdedi), 0) as dizi
                FROM jti_scv_dizim_gunluk g
                WHERE g.diziAdedi > 0
            """)
        scv_dizim_dizi = cursor.fetchone()[0]
        
        result['toplamlar']['SCV']['dizim_kg'] += float(scv_dizim_kg)
        result['toplamlar']['SCV']['dizim_dizi'] += int(scv_dizim_dizi)
        result['toplamlar']['JTI_SCV']['dizim_kg'] = float(scv_dizim_kg)
        result['toplamlar']['JTI_SCV']['dizim_dizi'] = int(scv_dizim_dizi)

        # PMI SCV Dizim
        # Dizim KG için: sadece ağırlık > 0 olanları topla
        if region:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(a.agirlik), 0) as kg
                FROM pmi_scv_dizim_gunluk g
                JOIN pmi_scv_dizim_dayibasi_table d ON g.dayibasi_id = d.id
                LEFT JOIN pmi_scv_dizim_agirlik a ON g.dayibasi_id = a.dayibasi_id
                WHERE a.agirlik > 0 AND d.region = %s
            """, (region,))
        else:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(a.agirlik), 0) as kg
                FROM pmi_scv_dizim_gunluk g
                LEFT JOIN pmi_scv_dizim_agirlik a ON g.dayibasi_id = a.dayibasi_id
                WHERE a.agirlik > 0
            """)
        pmi_scv_dizim_kg = cursor.fetchone()[0]
        
        # Dizim Dizi için: tüm gunluk kayıtlarını topla (ağırlık koşulu olmadan)
        if region:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(g.diziAdedi), 0) as dizi
                FROM pmi_scv_dizim_gunluk g
                JOIN pmi_scv_dizim_dayibasi_table d ON g.dayibasi_id = d.id
                WHERE d.region = %s AND g.diziAdedi > 0
            """, (region,))
        else:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(g.diziAdedi), 0) as dizi
                FROM pmi_scv_dizim_gunluk g
                WHERE g.diziAdedi > 0
            """)
        pmi_scv_dizim_dizi = cursor.fetchone()[0]
        
        result['toplamlar']['SCV']['dizim_kg'] += float(pmi_scv_dizim_kg)
        result['toplamlar']['SCV']['dizim_dizi'] += int(pmi_scv_dizim_dizi)
        result['toplamlar']['PMI_SCV']['dizim_kg'] = float(pmi_scv_dizim_kg)
        result['toplamlar']['PMI_SCV']['dizim_dizi'] = int(pmi_scv_dizim_dizi)

        # PMI Topping Dizim
        # Dizim KG için: sadece ağırlık > 0 olanları topla
        if region:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(a.agirlik), 0) as kg
                FROM pmi_topping_dizim_gunluk g
                JOIN pmi_topping_dizim_dayibasi_table d ON g.dayibasi_id = d.id
                LEFT JOIN pmi_topping_dizim_agirlik a ON g.dayibasi_id = a.dayibasi_id
                WHERE a.agirlik > 0 AND d.region = %s
            """, (region,))
        else:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(a.agirlik), 0) as kg
                FROM pmi_topping_dizim_gunluk g
                LEFT JOIN pmi_topping_dizim_agirlik a ON g.dayibasi_id = a.dayibasi_id
                WHERE a.agirlik > 0
            """)
        pmi_topping_dizim_kg = cursor.fetchone()[0]
        
        # Dizim Dizi için: tüm gunluk kayıtlarını topla (ağırlık koşulu olmadan)
        if region:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(g.diziAdedi), 0) as dizi
                FROM pmi_topping_dizim_gunluk g
                JOIN pmi_topping_dizim_dayibasi_table d ON g.dayibasi_id = d.id
                WHERE d.region = %s AND g.diziAdedi > 0
            """, (region,))
        else:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(g.diziAdedi), 0) as dizi
                FROM pmi_topping_dizim_gunluk g
                WHERE g.diziAdedi > 0
            """)
        pmi_topping_dizim_dizi = cursor.fetchone()[0]
        
        result['toplamlar']['SCV']['dizim_kg'] += float(pmi_topping_dizim_kg)
        result['toplamlar']['SCV']['dizim_dizi'] += int(pmi_topping_dizim_dizi)
        result['toplamlar']['SCV_TOPPING']['dizim_kg'] = float(pmi_topping_dizim_kg)
        result['toplamlar']['SCV_TOPPING']['dizim_dizi'] = int(pmi_topping_dizim_dizi)

        # 1.3 SCV Kutulama
        if region:
            cursor.execute("SELECT COALESCE(SUM(toplam_kuru_kg), 0) as kg FROM scv_kutulama WHERE toplam_kuru_kg > 0 AND region = %s", (region,))
        else:
            cursor.execute("SELECT COALESCE(SUM(toplam_kuru_kg), 0) as kg FROM scv_kutulama WHERE toplam_kuru_kg > 0")
        scv_kutulama_kg = cursor.fetchone()[0]
        result['toplamlar']['SCV']['kutulama_kg'] += float(scv_kutulama_kg)

        if region:
            cursor.execute("SELECT kutular FROM scv_kutulama WHERE region = %s", (region,))
        else:
            cursor.execute("SELECT kutular FROM scv_kutulama")
        scv_kutu_sayisi = sum(len(json.loads(row[0] or '[]')) for row in cursor.fetchall())
        result['toplamlar']['SCV']['kutulama_kutu'] += int(scv_kutu_sayisi)
        # SCV alt departmanlar için kutulama verisi alt ayrımı olmadığı için paylaşılmıyor (0 bırakıldı)

        # === 2. İZMİR BÖLÜMÜ ===
        
        # 2.1 İzmir Kırım
        if region:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(ta.agirlik), 0) as kg, 
                    COALESCE(SUM(td.bohca_sayisi), 0) as bohca
                FROM traktor_gelis_izmir_kirim t
                LEFT JOIN traktor_gelis_izmir_kirim_agirlik ta ON t.id = ta.traktor_gelis_izmir_kirim_id
                LEFT JOIN traktor_gelis_izmir_kirim_dayibasi td ON t.id = td.traktor_gelis_izmir_kirim_id
                WHERE ta.agirlik > 0 AND t.region = %s
            """, (region,))
        else:
            cursor.execute("""
            SELECT 
                COALESCE(SUM(ta.agirlik), 0) as kg, 
                COALESCE(SUM(td.bohca_sayisi), 0) as bohca
            FROM traktor_gelis_izmir_kirim t
            LEFT JOIN traktor_gelis_izmir_kirim_agirlik ta ON t.id = ta.traktor_gelis_izmir_kirim_id
            LEFT JOIN traktor_gelis_izmir_kirim_dayibasi td ON t.id = td.traktor_gelis_izmir_kirim_id
            WHERE ta.agirlik > 0
        """)
        izmir_kirim = cursor.fetchone()
        result['toplamlar']['IZMIR']['kirim_kg'] = float(izmir_kirim[0])
        result['toplamlar']['IZMIR']['kirim_bohca'] = int(izmir_kirim[1])

        # 2.2 İzmir Dizim (izmir_dizim tablosunda region kolonu olmayabilir, kontrol et)
        # Dizim KG için: sadece ağırlık > 0 olanları topla
        try:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'izmir_dizim_gunluk' AND column_name = 'region'")
            has_region = cursor.fetchone()
            if has_region and region:
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(a.agirlik), 0) as kg
                    FROM izmir_dizim_gunluk g
                    LEFT JOIN izmir_dizim_agirlik a ON g.dayibasi_id = a.dayibasi_id
                    WHERE a.agirlik > 0 AND g.region = %s
                """, (region,))
            else:
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(a.agirlik), 0) as kg
                    FROM izmir_dizim_gunluk g
                    LEFT JOIN izmir_dizim_agirlik a ON g.dayibasi_id = a.dayibasi_id
                    WHERE a.agirlik > 0
                """)
        except:
            cursor.execute("""
            SELECT 
                    COALESCE(SUM(a.agirlik), 0) as kg
            FROM izmir_dizim_gunluk g
            LEFT JOIN izmir_dizim_agirlik a ON g.dayibasi_id = a.dayibasi_id
            WHERE a.agirlik > 0
        """)
        izmir_dizim_kg = cursor.fetchone()[0]
        
        # Dizim Dizi için: tüm gunluk kayıtlarını topla (ağırlık koşulu olmadan)
        try:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'izmir_dizim_gunluk' AND column_name = 'region'")
            has_region = cursor.fetchone()
            if has_region and region:
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(g.diziAdedi), 0) as dizi
                    FROM izmir_dizim_gunluk g
                    WHERE g.region = %s AND g.diziAdedi > 0
                """, (region,))
            else:
                cursor.execute("""
                    SELECT 
                        COALESCE(SUM(g.diziAdedi), 0) as dizi
                    FROM izmir_dizim_gunluk g
                    WHERE g.diziAdedi > 0
                """)
        except:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(g.diziAdedi), 0) as dizi
                FROM izmir_dizim_gunluk g
                WHERE g.diziAdedi > 0
            """)
        izmir_dizim_dizi = cursor.fetchone()[0]
        
        result['toplamlar']['IZMIR']['dizim_kg'] = float(izmir_dizim_kg)
        result['toplamlar']['IZMIR']['dizim_dizi'] = int(izmir_dizim_dizi)

        # 2.3 İzmir Kutulama
        try:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'izmir_kutulama' AND column_name = 'region'")
            has_region = cursor.fetchone()
            if has_region and region:
                cursor.execute("SELECT COALESCE(SUM(toplam_kuru_tutun), 0) as kg FROM izmir_kutulama WHERE toplam_kuru_tutun > 0 AND region = %s", (region,))
            else:
                cursor.execute("SELECT COALESCE(SUM(toplam_kuru_tutun), 0) as kg FROM izmir_kutulama WHERE toplam_kuru_tutun > 0")
        except:
            cursor.execute("SELECT COALESCE(SUM(toplam_kuru_tutun), 0) as kg FROM izmir_kutulama WHERE toplam_kuru_tutun > 0")
        izmir_kutulama_kg = cursor.fetchone()[0]
        result['toplamlar']['IZMIR']['kutulama_kg'] = float(izmir_kutulama_kg)

        try:
            cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'izmir_kutulama' AND column_name = 'region'")
            has_region = cursor.fetchone()
            if has_region and region:
                cursor.execute("SELECT kutular FROM izmir_kutulama WHERE region = %s", (region,))
            else:
                cursor.execute("SELECT kutular FROM izmir_kutulama")
        except:
            cursor.execute("SELECT kutular FROM izmir_kutulama")
        izmir_kutu_sayisi = sum(len(json.loads(row[0] or '[]')) for row in cursor.fetchall())
        result['toplamlar']['IZMIR']['kutulama_kutu'] = int(izmir_kutu_sayisi)

        # === 3. FCV BÖLÜMÜ ===
        
        # 3.1 FCV Kırım
        if region:
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(fa.agirlik), 0) as kg, 
                    COALESCE(SUM(fg.bocaSayisi), 0) as bohca
                FROM fcv_kirim_gunluk fg
                LEFT JOIN fcv_kirim_agirlik fa ON fg.id = fa.gunlukId
                WHERE fa.agirlik > 0 AND fg.region = %s
            """, (region,))
        else:
            cursor.execute("""
            SELECT 
                COALESCE(SUM(fa.agirlik), 0) as kg, 
                COALESCE(SUM(fg.bocaSayisi), 0) as bohca
            FROM fcv_kirim_gunluk fg
            LEFT JOIN fcv_kirim_agirlik fa ON fg.id = fa.gunlukId
            WHERE fa.agirlik > 0
        """)
        fcv_kirim = cursor.fetchone()
        result['toplamlar']['FCV']['kirim_kg'] = float(fcv_kirim[0])
        result['toplamlar']['FCV']['kirim_bohca'] = int(fcv_kirim[1])

        # 3.2 FCV Kutulama
        if region:
            cursor.execute("SELECT COALESCE(SUM(kuruKg), 0) as kg, COALESCE(SUM(koliSayisi), 0) as kutu FROM fcv_genel WHERE kuruKg > 0 AND region = %s", (region,))
        else:
            cursor.execute("SELECT COALESCE(SUM(kuruKg), 0) as kg, COALESCE(SUM(koliSayisi), 0) as kutu FROM fcv_genel WHERE kuruKg > 0")
        fcv_kutulama = cursor.fetchone()
        result['toplamlar']['FCV']['kutulama_kg'] = float(fcv_kutulama[0])
        result['toplamlar']['FCV']['kutulama_kutu'] = int(fcv_kutulama[1])

        # === SEVKİYAT VERİLERİ ===
        # Sevkiyat verilerini alan bazında topla
        sevkiyat_toplamlari = {
            'JTI SCV': 0,
            'PMI SCV': 0,
            'PMI TOPPING': 0,
            'İZMİR': 0,
            'IZMIR': 0
        }
        
        if region:
            cursor.execute("""
                SELECT alan, COALESCE(SUM(kutu), 0) as toplam_kutu
                FROM sevkiyat
                WHERE region = %s
                GROUP BY alan
            """, (region,))
        else:
            cursor.execute("""
                SELECT alan, COALESCE(SUM(kutu), 0) as toplam_kutu
                FROM sevkiyat
                GROUP BY alan
            """)
        
        sevkiyat_rows = cursor.fetchall()
        for row in sevkiyat_rows:
            alan = (row['alan'] if isinstance(row, dict) else getattr(row, 'alan', None)) or ''
            kutu = row['toplam_kutu'] if isinstance(row, dict) else getattr(row, 'toplam_kutu', 0) or 0
            
            # Alan adını normalize et
            alan_upper = alan.strip().upper()
            if 'JTI' in alan_upper and 'SCV' in alan_upper:
                sevkiyat_toplamlari['JTI SCV'] += int(kutu)
            elif 'PMI' in alan_upper and 'SCV' in alan_upper:
                sevkiyat_toplamlari['PMI SCV'] += int(kutu)
            elif 'PMI' in alan_upper and 'TOPPING' in alan_upper:
                sevkiyat_toplamlari['PMI TOPPING'] += int(kutu)
            elif 'İZMİR' in alan_upper or 'IZMIR' in alan_upper:
                sevkiyat_toplamlari['İZMİR'] += int(kutu)
                sevkiyat_toplamlari['IZMIR'] += int(kutu)
        
        # Sevkiyat verilerini result'a ekle
        result['sevkiyat'] = {
            'JTI_SCV': sevkiyat_toplamlari['JTI SCV'],
            'PMI_SCV': sevkiyat_toplamlari['PMI SCV'],
            'SCV_TOPPING': sevkiyat_toplamlari['PMI TOPPING'],
            'IZMIR': sevkiyat_toplamlari['İZMİR'] + sevkiyat_toplamlari['IZMIR']
        }
        
        # SCV genel sevkiyat toplamı
        result['sevkiyat']['SCV'] = (
            sevkiyat_toplamlari['JTI SCV'] + 
            sevkiyat_toplamlari['PMI SCV'] + 
            sevkiyat_toplamlari['PMI TOPPING']
        )

        # === GENEL TOPLAMLAR ===
        result['genel_toplam'] = {
            'kirim_kg': round(result['toplamlar']['SCV']['kirim_kg'] + result['toplamlar']['IZMIR']['kirim_kg'] + result['toplamlar']['FCV']['kirim_kg'], 2),
            'kirim_bohca': result['toplamlar']['SCV']['kirim_bohca'] + result['toplamlar']['IZMIR']['kirim_bohca'] + result['toplamlar']['FCV']['kirim_bohca'],
            'dizim_kg': round(result['toplamlar']['SCV']['dizim_kg'] + result['toplamlar']['IZMIR']['dizim_kg'], 2),
            'dizim_dizi': result['toplamlar']['SCV']['dizim_dizi'] + result['toplamlar']['IZMIR']['dizim_dizi'],
            'kutulama_kg': round(result['toplamlar']['SCV']['kutulama_kg'] + result['toplamlar']['IZMIR']['kutulama_kg'] + result['toplamlar']['FCV']['kutulama_kg'], 2),
            'kutulama_kutu': result['toplamlar']['SCV']['kutulama_kutu'] + result['toplamlar']['IZMIR']['kutulama_kutu'] + result['toplamlar']['FCV']['kutulama_kutu']
        }

        # Yaş-Kuru Oranı Hesaplama
        if result['genel_toplam']['kutulama_kg'] > 0:
            result['genel_toplam']['yas_kuru_orani'] = round(
                result['genel_toplam']['kirim_kg'] / result['genel_toplam']['kutulama_kg'], 2
            )
        else:
            result['genel_toplam']['yas_kuru_orani'] = 0

        return jsonify(result)
        
    except Exception as e:
        print(f"Hata: {str(e)}")
        return jsonify({'error': f'Veritabanı hatası: {str(e)}'}), 500
    finally:
        if conn:
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

@app.route('/api/fcv_kirim/agirlik/<int:agirlik_id>', methods=['PUT'])
def update_fcv_kirim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - agirlik_id'den gunlukId'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT gunlukId FROM fcv_kirim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        gunluk_id = agirlik_record[0]
        cursor.execute("SELECT region FROM fcv_kirim_gunluk WHERE id = %s", (gunluk_id,))
        gunluk_region = cursor.fetchone()
        if not gunluk_region or gunluk_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("UPDATE fcv_kirim_agirlik SET agirlik = %s, yazici_adi = %s WHERE id = %s", (agirlik, yazici_adi, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        cursor.execute("UPDATE izmir_kirim_agirlik SET agirlik = %s, yazici_adi = %s WHERE id = %s", (agirlik, yazici_adi, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        cursor.execute("UPDATE pmi_topping_kirim_agirlik SET agirlik = %s, yazici_adi = %s WHERE id = %s", (agirlik, yazici_adi, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()


@app.route('/api/fcv_kirim/gunluk/<int:gunluk_id>', methods=['PUT'])
def update_fcv_kirim_gunluk(gunluk_id):
    data = request.get_json()
    bohcaSayisi = data.get('bocaSayisi')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if bohcaSayisi is None:
        return jsonify({'message': 'bocaSayisi zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        cursor.execute("SELECT region FROM fcv_kirim_gunluk WHERE id = %s", (gunluk_id,))
        gunluk_region = cursor.fetchone()
        if not gunluk_region:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        if gunluk_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("UPDATE fcv_kirim_gunluk SET bocaSayisi = %s, yazici_adi = %s WHERE id = %s", (bohcaSayisi, yazici_adi, gunluk_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Günlük başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        cursor.execute("UPDATE izmir_kirim_gunluk SET bohcaSayisi = %s, yazici_adi = %s WHERE id = %s", (bohcaSayisi, yazici_adi, gunluk_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Günlük başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

@app.route('/api/jti_scv_dizim/gunluk/<int:gunluk_id>', methods=['PUT'])
def update_jti_scv_dizim_gunluk(gunluk_id):
    data = request.get_json()
    diziAdedi = data.get('diziAdedi')
    yazici_adi = data.get('yazici_adi')
    if diziAdedi is None:
        return jsonify({'message': 'diziAdedi zorunludur.'}), 400
    
    # Veri tipi dönüşümü
    try:
        diziAdedi = int(diziAdedi)
    except (ValueError, TypeError):
        return jsonify({'message': 'diziAdedi integer olmalıdır.'}), 400
    
    # diziAdedi 0 olamaz kontrolü
    if diziAdedi <= 0:
        return jsonify({'message': 'diziAdedi 0\'dan büyük olmalıdır.'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # ESKİ VERSİYON GİBİ - region kontrolü yok, direkt güncelle
        cursor.execute("UPDATE jti_scv_dizim_gunluk SET diziAdedi = %s, yazici_adi = %s WHERE id = %s", (diziAdedi, yazici_adi, gunluk_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        # Kayıt sonrası doğrulama
        cursor.execute("SELECT diziAdedi FROM jti_scv_dizim_gunluk WHERE id = %s", (gunluk_id,))
        verify = cursor.fetchone()
        print(f"JTI SCV Dizim - UPDATE PUT: gunluk_id={gunluk_id}, diziAdedi={diziAdedi}, kaydedilen={verify[0] if verify else 'None'}")
        return jsonify({'message': 'Günlük başarıyla güncellendi.', 'diziAdedi': diziAdedi}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

@app.route('/api/pmi_scv_dizim/gunluk/<int:gunluk_id>', methods=['PUT'])
def update_pmi_scv_dizim_gunluk(gunluk_id):
    data = request.get_json()
    diziAdedi = data.get('diziAdedi')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if diziAdedi is None:
        return jsonify({'message': 'diziAdedi zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    
    # Veri tipi dönüşümü
    try:
        diziAdedi = int(diziAdedi)
    except (ValueError, TypeError):
        return jsonify({'message': 'diziAdedi integer olmalıdır.'}), 400
    
    # diziAdedi 0 olamaz kontrolü
    if diziAdedi <= 0:
        return jsonify({'message': 'diziAdedi 0\'dan büyük olmalıdır.'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - gunluk_id'den dayibasi_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT dayibasi_id FROM pmi_scv_dizim_gunluk WHERE id = %s", (gunluk_id,))
        gunluk_record = cursor.fetchone()
        if not gunluk_record:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        dayibasi_id = gunluk_record[0]
        cursor.execute("SELECT region FROM pmi_scv_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region or dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("UPDATE pmi_scv_dizim_gunluk SET diziAdedi = %s, yazici_adi = %s WHERE id = %s", (diziAdedi, yazici_adi, gunluk_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        # Kayıt sonrası doğrulama
        cursor.execute("SELECT diziAdedi FROM pmi_scv_dizim_gunluk WHERE id = %s", (gunluk_id,))
        verify = cursor.fetchone()
        print(f"PMI SCV Dizim - UPDATE PUT: gunluk_id={gunluk_id}, diziAdedi={diziAdedi}, kaydedilen={verify[0] if verify else 'None'}")
        return jsonify({'message': 'Günlük başarıyla güncellendi.', 'diziAdedi': diziAdedi}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

@app.route('/api/pmi_topping_dizim/gunluk/<int:gunluk_id>', methods=['PUT'])
def update_pmi_topping_dizim_gunluk(gunluk_id):
    data = request.get_json()
    diziAdedi = data.get('diziAdedi')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if diziAdedi is None:
        return jsonify({'message': 'diziAdedi zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    
    # Veri tipi dönüşümü
    try:
        diziAdedi = int(diziAdedi)
    except (ValueError, TypeError):
        return jsonify({'message': 'diziAdedi integer olmalıdır.'}), 400
    
    # diziAdedi 0 olamaz kontrolü
    if diziAdedi <= 0:
        return jsonify({'message': 'diziAdedi 0\'dan büyük olmalıdır.'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - gunluk_id'den dayibasi_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT dayibasi_id FROM pmi_topping_dizim_gunluk WHERE id = %s", (gunluk_id,))
        gunluk_record = cursor.fetchone()
        if not gunluk_record:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        dayibasi_id = gunluk_record[0]
        cursor.execute("SELECT region FROM pmi_topping_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region or dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("UPDATE pmi_topping_dizim_gunluk SET diziAdedi = %s, yazici_adi = %s WHERE id = %s", (diziAdedi, yazici_adi, gunluk_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Günlük kaydı bulunamadı.'}), 404
        # Kayıt sonrası doğrulama
        cursor.execute("SELECT diziAdedi FROM pmi_topping_dizim_gunluk WHERE id = %s", (gunluk_id,))
        verify = cursor.fetchone()
        print(f"PMI Topping Dizim - UPDATE PUT: gunluk_id={gunluk_id}, diziAdedi={diziAdedi}, kaydedilen={verify[0] if verify else 'None'}")
        return jsonify({'message': 'Günlük başarıyla güncellendi.', 'diziAdedi': diziAdedi}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

@app.route('/api/pmi_scv_dizim/agirlik/<int:agirlik_id>', methods=['PUT'])
def update_pmi_scv_dizim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - agirlik_id'den dayibasi_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT dayibasi_id FROM pmi_scv_dizim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        dayibasi_id = agirlik_record[0]
        cursor.execute("SELECT region FROM pmi_scv_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region or dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        if yaprakSayisi is not None:
            cursor.execute("UPDATE pmi_scv_dizim_agirlik SET agirlik = %s, yaprakSayisi = %s, yazici_adi = %s WHERE id = %s", (agirlik, yaprakSayisi, yazici_adi, agirlik_id))
        else:
            cursor.execute("UPDATE pmi_scv_dizim_agirlik SET agirlik = %s, yazici_adi = %s WHERE id = %s", (agirlik, yazici_adi, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

@app.route('/api/jti_scv_dizim/agirlik/<int:agirlik_id>', methods=['PUT'])
def update_jti_scv_dizim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - agirlik_id'den dayibasi_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT dayibasi_id FROM jti_scv_dizim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        dayibasi_id = agirlik_record[0]
        cursor.execute("SELECT region FROM jti_scv_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region or dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        if yaprakSayisi is not None:
            cursor.execute("UPDATE jti_scv_dizim_agirlik SET agirlik = %s, yaprakSayisi = %s, yazici_adi = %s WHERE id = %s", (agirlik, yaprakSayisi, yazici_adi, agirlik_id))
        else:
            cursor.execute("UPDATE jti_scv_dizim_agirlik SET agirlik = %s, yazici_adi = %s WHERE id = %s", (agirlik, yazici_adi, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

@app.route('/api/pmi_topping_dizim/agirlik/<int:agirlik_id>', methods=['PUT'])
def update_pmi_topping_dizim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - agirlik_id'den dayibasi_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT dayibasi_id FROM pmi_topping_dizim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        dayibasi_id = agirlik_record[0]
        cursor.execute("SELECT region FROM pmi_topping_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region or dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        if yaprakSayisi is not None:
            cursor.execute("UPDATE pmi_topping_dizim_agirlik SET agirlik = %s, yaprakSayisi = %s, yazici_adi = %s WHERE id = %s", (agirlik, yaprakSayisi, yazici_adi, agirlik_id))
        else:
            cursor.execute("UPDATE pmi_topping_dizim_agirlik SET agirlik = %s, yazici_adi = %s WHERE id = %s", (agirlik, yazici_adi, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

@app.route('/api/jti_scv_dizim_yaprak', methods=['POST'])
def add_jti_scv_dizim_yaprak():
    data = request.get_json()
    agirlik_id = data.get('agirlik_id')
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if not agirlik_id or yaprakSayisi is None:
        return jsonify({'message': 'agirlik_id ve yaprakSayisi zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - agirlik_id'den dayibasi_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT dayibasi_id FROM jti_scv_dizim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        dayibasi_id = agirlik_record[0]
        cursor.execute("SELECT region FROM jti_scv_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region or dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("INSERT INTO jti_scv_dizim_yaprak (agirlik_id, yaprakSayisi, yazici_adi) VALUES (%s, %s, %s)", (agirlik_id, yaprakSayisi, yazici_adi))
        conn.commit()
        return jsonify({'message': 'Yaprak sayısı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

@app.route('/api/jti_scv_dizim_yaprak/<int:yaprak_id>', methods=['PUT'])
def update_jti_scv_dizim_yaprak(yaprak_id):
    data = request.get_json()
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if yaprakSayisi is None:
        return jsonify({'message': 'yaprakSayisi zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - yaprak_id'den agirlik_id'yi bul, sonra dayibasi_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT agirlik_id FROM jti_scv_dizim_yaprak WHERE id = %s", (yaprak_id,))
        yaprak_record = cursor.fetchone()
        if not yaprak_record:
            return jsonify({'message': 'Yaprak kaydı bulunamadı.'}), 404
        agirlik_id = yaprak_record[0]
        cursor.execute("SELECT dayibasi_id FROM jti_scv_dizim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        dayibasi_id = agirlik_record[0]
        cursor.execute("SELECT region FROM jti_scv_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region or dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("UPDATE jti_scv_dizim_yaprak SET yaprakSayisi = %s, yazici_adi = %s WHERE id = %s", (yaprakSayisi, yazici_adi, yaprak_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Yaprak kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Yaprak sayısı başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

@app.route('/api/pmi_scv_dizim_yaprak', methods=['POST'])
def add_pmi_scv_dizim_yaprak():
    data = request.get_json()
    agirlik_id = data.get('agirlik_id')
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if not agirlik_id or yaprakSayisi is None:
        return jsonify({'message': 'agirlik_id ve yaprakSayisi zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - agirlik_id'den dayibasi_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT dayibasi_id FROM pmi_scv_dizim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        dayibasi_id = agirlik_record[0]
        cursor.execute("SELECT region FROM pmi_scv_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region or dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("INSERT INTO pmi_scv_dizim_yaprak (agirlik_id, yaprakSayisi, yazici_adi) VALUES (%s, %s, %s)", (agirlik_id, yaprakSayisi, yazici_adi))
        conn.commit()
        return jsonify({'message': 'Yaprak sayısı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

@app.route('/api/pmi_scv_dizim_yaprak/<int:yaprak_id>', methods=['PUT'])
def update_pmi_scv_dizim_yaprak(yaprak_id):
    data = request.get_json()
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if yaprakSayisi is None:
        return jsonify({'message': 'yaprakSayisi zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - yaprak_id'den agirlik_id'yi bul, sonra dayibasi_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT agirlik_id FROM pmi_scv_dizim_yaprak WHERE id = %s", (yaprak_id,))
        yaprak_record = cursor.fetchone()
        if not yaprak_record:
            return jsonify({'message': 'Yaprak kaydı bulunamadı.'}), 404
        agirlik_id = yaprak_record[0]
        cursor.execute("SELECT dayibasi_id FROM pmi_scv_dizim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        dayibasi_id = agirlik_record[0]
        cursor.execute("SELECT region FROM pmi_scv_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region or dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("UPDATE pmi_scv_dizim_yaprak SET yaprakSayisi = %s, yazici_adi = %s WHERE id = %s", (yaprakSayisi, yazici_adi, yaprak_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Yaprak kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Yaprak sayısı başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

@app.route('/api/pmi_topping_dizim_yaprak', methods=['POST'])
def add_pmi_topping_dizim_yaprak():
    data = request.get_json()
    agirlik_id = data.get('agirlik_id')
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if not agirlik_id or yaprakSayisi is None:
        return jsonify({'message': 'agirlik_id ve yaprakSayisi zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - agirlik_id'den dayibasi_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT dayibasi_id FROM pmi_topping_dizim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        dayibasi_id = agirlik_record[0]
        cursor.execute("SELECT region FROM pmi_topping_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region or dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("INSERT INTO pmi_topping_dizim_yaprak (agirlik_id, yaprakSayisi, yazici_adi) VALUES (%s, %s, %s)", (agirlik_id, yaprakSayisi, yazici_adi))
        conn.commit()
        return jsonify({'message': 'Yaprak sayısı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

@app.route('/api/pmi_topping_dizim_yaprak/<int:yaprak_id>', methods=['PUT'])
def update_pmi_topping_dizim_yaprak(yaprak_id):
    data = request.get_json()
    yaprakSayisi = data.get('yaprakSayisi')
    yazici_adi = data.get('yazici_adi')
    region = data.get('region')
    if yaprakSayisi is None:
        return jsonify({'message': 'yaprakSayisi zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn: return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - yaprak_id'den agirlik_id'yi bul, sonra dayibasi_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT agirlik_id FROM pmi_topping_dizim_yaprak WHERE id = %s", (yaprak_id,))
        yaprak_record = cursor.fetchone()
        if not yaprak_record:
            return jsonify({'message': 'Yaprak kaydı bulunamadı.'}), 404
        agirlik_id = yaprak_record[0]
        cursor.execute("SELECT dayibasi_id FROM pmi_topping_dizim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        dayibasi_id = agirlik_record[0]
        cursor.execute("SELECT region FROM pmi_topping_dizim_dayibasi_table WHERE id = %s", (dayibasi_id,))
        dayibasi_region = cursor.fetchone()
        if not dayibasi_region or dayibasi_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("UPDATE pmi_topping_dizim_yaprak SET yaprakSayisi = %s, yazici_adi = %s WHERE id = %s", (yaprakSayisi, yazici_adi, yaprak_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Yaprak kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Yaprak sayısı başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        conn.close()

# --- JTI SCV KIRIM yeni sistem için ---
@app.route('/api/traktor_gelis_jti_kirim', methods=['POST'])
def add_traktor_gelis_jti_kirim():
    data = request.get_json()
    required_fields = ['tarih', 'plaka', 'gelis_no']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_jti_kirim (tarih, plaka, gelis_no, region)
        VALUES (%s, %s, %s, %s)
        """
        params = (
            data['tarih'], data['plaka'], data['gelis_no'], region
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Türücü gelis kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_jti_kirim/dayibasi', methods=['POST'])
def add_traktor_gelis_jti_kirim_dayibasi():
    data = request.get_json()
    required_fields = ['traktor_gelis_jti_kirim_id', 'dayibasi_adi', 'bohca_sayisi']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        cursor.execute("SELECT region FROM traktor_gelis_jti_kirim WHERE id = %s", (data['traktor_gelis_jti_kirim_id'],))
        kart_region = cursor.fetchone()
        if not kart_region:
            return jsonify({'message': 'Kart kaydı bulunamadı.'}), 404
        if kart_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı: Bu kart farklı bir bölgeye ait.'}), 403
        sql = """
        INSERT INTO traktor_gelis_jti_kirim_dayibasi (traktor_gelis_jti_kirim_id, dayibasi_adi, bohca_sayisi)
        VALUES (%s, %s, %s)
        """
        params = (
            data['traktor_gelis_jti_kirim_id'], data['dayibasi_adi'], data['bohca_sayisi']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Türücü gelis dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_jti_kirim_agirlik', methods=['POST'])
def add_traktor_gelis_jti_kirim_agirlik():
    data = request.get_json()
    required_fields = ['traktor_gelis_jti_kirim_id', 'agirlik', 'created_at']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        cursor.execute("SELECT region FROM traktor_gelis_jti_kirim WHERE id = %s", (data['traktor_gelis_jti_kirim_id'],))
        kart_region = cursor.fetchone()
        if not kart_region:
            return jsonify({'message': 'Kart kaydı bulunamadı.'}), 404
        if kart_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı: Bu kart farklı bir bölgeye ait.'}), 403
        sql = """
        INSERT INTO traktor_gelis_jti_kirim_agirlik (traktor_gelis_jti_kirim_id, agirlik, created_at)
        VALUES (%s, %s, %s)
        """
        params = (
            data['traktor_gelis_jti_kirim_id'], data['agirlik'], data['created_at']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Türücü gelis ağırlık kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_jti_kirim_agirlik/<int:agirlik_id>', methods=['PUT'])
def update_traktor_gelis_jti_kirim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    region = data.get('region')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - agirlik_id'den kart_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT traktor_gelis_jti_kirim_id FROM traktor_gelis_jti_kirim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        kart_id = agirlik_record[0]
        cursor.execute("SELECT region FROM traktor_gelis_jti_kirim WHERE id = %s", (kart_id,))
        kart_region = cursor.fetchone()
        if not kart_region or kart_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("UPDATE traktor_gelis_jti_kirim_agirlik SET agirlik = %s WHERE id = %s", (agirlik, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        region = request.args.get('region')
        if region:
            cursor.execute("SELECT * FROM traktor_gelis_jti_kirim WHERE region = %s ORDER BY tarih DESC, plaka, gelis_no DESC", (region,))
        else:
            cursor.execute("SELECT * FROM traktor_gelis_jti_kirim ORDER BY tarih DESC, plaka, gelis_no DESC")
        kartlar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        for kart in kartlar:
            cursor.execute("SELECT * FROM traktor_gelis_jti_kirim_dayibasi WHERE traktor_gelis_jti_kirim_id = %s", (kart['id'],))
            dayibasilari = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['dayibasilari'] = dayibasilari
            kart['toplam_bohca'] = sum([d['bohca_sayisi'] for d in dayibasilari]) if dayibasilari else 0
            cursor.execute("SELECT id, agirlik, created_at FROM traktor_gelis_jti_kirim_agirlik WHERE traktor_gelis_jti_kirim_id = %s ORDER BY id", (kart['id'],))
            agirliklar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['agirliklar'] = agirliklar
            if agirliklar:
                kart['ortalama_agirlik'] = sum([a['agirlik'] for a in agirliklar]) / len(agirliklar)
                # Toplam KG = Tüm ağırlıkların toplamı (ortalama * bohça değil!)
                kart['toplam_kg'] = sum([a['agirlik'] for a in agirliklar])
            else:
                kart['ortalama_agirlik'] = 0
                kart['toplam_kg'] = 0
        return jsonify(kartlar)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_pmi_kirim (tarih, plaka, gelis_no, region)
        VALUES (%s, %s, %s, %s)
        """
        params = (
            data['tarih'], data['plaka'], data['gelis_no'], region
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_kirim/dayibasi', methods=['POST'])
def add_traktor_gelis_pmi_kirim_dayibasi():
    data = request.get_json()
    required_fields = ['traktor_gelis_pmi_kirim_id', 'dayibasi_adi', 'bohca_sayisi']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        cursor.execute("SELECT region FROM traktor_gelis_pmi_kirim WHERE id = %s", (data['traktor_gelis_pmi_kirim_id'],))
        kart_region = cursor.fetchone()
        if not kart_region:
            return jsonify({'message': 'Kart kaydı bulunamadı.'}), 404
        if kart_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı: Bu kart farklı bir bölgeye ait.'}), 403
        sql = """
        INSERT INTO traktor_gelis_pmi_kirim_dayibasi (traktor_gelis_pmi_kirim_id, dayibasi_adi, bohca_sayisi)
        VALUES (%s, %s, %s)
        """
        params = (
            data['traktor_gelis_pmi_kirim_id'], data['dayibasi_adi'], data['bohca_sayisi']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_kirim_agirlik', methods=['POST'])
def add_traktor_gelis_pmi_kirim_agirlik():
    data = request.get_json()
    required_fields = ['traktor_gelis_pmi_kirim_id', 'agirlik', 'created_at']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        cursor.execute("SELECT region FROM traktor_gelis_pmi_kirim WHERE id = %s", (data['traktor_gelis_pmi_kirim_id'],))
        kart_region = cursor.fetchone()
        if not kart_region:
            return jsonify({'message': 'Kart kaydı bulunamadı.'}), 404
        if kart_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı: Bu kart farklı bir bölgeye ait.'}), 403
        sql = """
        INSERT INTO traktor_gelis_pmi_kirim_agirlik (traktor_gelis_pmi_kirim_id, agirlik, created_at)
        VALUES (%s, %s, %s)
        """
        params = (
            data['traktor_gelis_pmi_kirim_id'], data['agirlik'], data['created_at']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş ağırlık kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_kirim_agirlik/<int:agirlik_id>', methods=['PUT'])
def update_traktor_gelis_pmi_kirim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    region = data.get('region')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - agirlik_id'den kart_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT traktor_gelis_pmi_kirim_id FROM traktor_gelis_pmi_kirim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        kart_id = agirlik_record[0]
        cursor.execute("SELECT region FROM traktor_gelis_pmi_kirim WHERE id = %s", (kart_id,))
        kart_region = cursor.fetchone()
        if not kart_region or kart_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("UPDATE traktor_gelis_pmi_kirim_agirlik SET agirlik = %s WHERE id = %s", (agirlik, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        region = request.args.get('region')
        if region:
            cursor.execute("SELECT * FROM traktor_gelis_pmi_kirim WHERE region = %s ORDER BY tarih DESC, plaka, gelis_no DESC", (region,))
        else:
            cursor.execute("SELECT * FROM traktor_gelis_pmi_kirim ORDER BY tarih DESC, plaka, gelis_no DESC")
        kartlar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        for kart in kartlar:
            cursor.execute("SELECT * FROM traktor_gelis_pmi_kirim_dayibasi WHERE traktor_gelis_pmi_kirim_id = %s", (kart['id'],))
            dayibasilari = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['dayibasilari'] = dayibasilari
            kart['toplam_bohca'] = sum([d['bohca_sayisi'] for d in dayibasilari]) if dayibasilari else 0
            cursor.execute("SELECT id, agirlik, created_at FROM traktor_gelis_pmi_kirim_agirlik WHERE traktor_gelis_pmi_kirim_id = %s ORDER BY id", (kart['id'],))
            agirliklar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['agirliklar'] = agirliklar
            if agirliklar:
                kart['ortalama_agirlik'] = sum([a['agirlik'] for a in agirliklar]) / len(agirliklar)
                # Toplam KG = Tüm ağırlıkların toplamı (ortalama * bohça değil!)
                kart['toplam_kg'] = sum([a['agirlik'] for a in agirliklar])
            else:
                kart['ortalama_agirlik'] = 0
                kart['toplam_kg'] = 0
        return jsonify(kartlar)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_pmi_topping_kirim (tarih, plaka, gelis_no, region)
        VALUES (%s, %s, %s, %s)
        """
        params = (
            data['tarih'], data['plaka'], data['gelis_no'], region
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_topping_kirim/dayibasi', methods=['POST'])
def add_traktor_gelis_pmi_topping_kirim_dayibasi():
    data = request.get_json()
    required_fields = ['traktor_gelis_pmi_topping_kirim_id', 'dayibasi_adi', 'bohca_sayisi']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        cursor.execute("SELECT region FROM traktor_gelis_pmi_topping_kirim WHERE id = %s", (data['traktor_gelis_pmi_topping_kirim_id'],))
        kart_region = cursor.fetchone()
        if not kart_region:
            return jsonify({'message': 'Kart kaydı bulunamadı.'}), 404
        if kart_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı: Bu kart farklı bir bölgeye ait.'}), 403
        sql = """
        INSERT INTO traktor_gelis_pmi_topping_kirim_dayibasi (traktor_gelis_pmi_topping_kirim_id, dayibasi_adi, bohca_sayisi)
        VALUES (%s, %s, %s)
        """
        params = (
            data['traktor_gelis_pmi_topping_kirim_id'], data['dayibasi_adi'], data['bohca_sayisi']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş dayıbaşı kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_topping_kirim_agirlik', methods=['POST'])
def add_traktor_gelis_pmi_topping_kirim_agirlik():
    data = request.get_json()
    required_fields = ['traktor_gelis_pmi_topping_kirim_id', 'agirlik', 'created_at']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        cursor.execute("SELECT region FROM traktor_gelis_pmi_topping_kirim WHERE id = %s", (data['traktor_gelis_pmi_topping_kirim_id'],))
        kart_region = cursor.fetchone()
        if not kart_region:
            return jsonify({'message': 'Kart kaydı bulunamadı.'}), 404
        if kart_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı: Bu kart farklı bir bölgeye ait.'}), 403
        sql = """
        INSERT INTO traktor_gelis_pmi_topping_kirim_agirlik (traktor_gelis_pmi_topping_kirim_id, agirlik, created_at)
        VALUES (%s, %s, %s)
        """
        params = (
            data['traktor_gelis_pmi_topping_kirim_id'], data['agirlik'], data['created_at']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş ağırlık kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_pmi_topping_kirim_agirlik/<int:agirlik_id>', methods=['PUT'])
def update_traktor_gelis_pmi_topping_kirim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    region = data.get('region')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - agirlik_id'den kart_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT traktor_gelis_pmi_topping_kirim_id FROM traktor_gelis_pmi_topping_kirim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        kart_id = agirlik_record[0]
        cursor.execute("SELECT region FROM traktor_gelis_pmi_topping_kirim WHERE id = %s", (kart_id,))
        kart_region = cursor.fetchone()
        if not kart_region or kart_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("UPDATE traktor_gelis_pmi_topping_kirim_agirlik SET agirlik = %s WHERE id = %s", (agirlik, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        region = request.args.get('region')
        if region:
            cursor.execute("SELECT * FROM traktor_gelis_pmi_topping_kirim WHERE region = %s ORDER BY tarih DESC, plaka, gelis_no DESC", (region,))
        else:
            cursor.execute("SELECT * FROM traktor_gelis_pmi_topping_kirim ORDER BY tarih DESC, plaka, gelis_no DESC")
        kartlar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        for kart in kartlar:
            cursor.execute("SELECT * FROM traktor_gelis_pmi_topping_kirim_dayibasi WHERE traktor_gelis_pmi_topping_kirim_id = %s", (kart['id'],))
            dayibasilari = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['dayibasilari'] = dayibasilari
            kart['toplam_bohca'] = sum([d['bohca_sayisi'] for d in dayibasilari]) if dayibasilari else 0
            cursor.execute("SELECT id, agirlik, created_at FROM traktor_gelis_pmi_topping_kirim_agirlik WHERE traktor_gelis_pmi_topping_kirim_id = %s ORDER BY id", (kart['id'],))
            agirliklar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['agirliklar'] = agirliklar
            if agirliklar:
                kart['ortalama_agirlik'] = sum([a['agirlik'] for a in agirliklar]) / len(agirliklar)
                # Toplam KG = Tüm ağırlıkların toplamı (ortalama * bohça değil!)
                kart['toplam_kg'] = sum([a['agirlik'] for a in agirliklar])
            else:
                kart['ortalama_agirlik'] = 0
                kart['toplam_kg'] = 0
        return jsonify(kartlar)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        sql = """
        INSERT INTO traktor_gelis_izmir_kirim (tarih, plaka, gelis_no, region)
        VALUES (%s, %s, %s, %s)
        """
        params = (
            data['tarih'], data['plaka'], data['gelis_no'], region
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        region = request.args.get('region')
        if region:
            cursor.execute("SELECT * FROM traktor_gelis_izmir_kirim WHERE region = %s ORDER BY id DESC", (region,))
        else:
            cursor.execute("SELECT * FROM traktor_gelis_izmir_kirim ORDER BY id DESC")
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

# --- IZMIR KIRIM yeni sistem için ---
@app.route('/api/traktor_gelis_izmir_kirim/dayibasi', methods=['GET', 'POST', 'OPTIONS'])
def handle_traktor_dayibasi():
    if request.method == 'OPTIONS':
        # Preflight request için response
        response = jsonify({'message': 'Preflight request accepted'})
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        return response, 200
    elif request.method == 'POST':
        data = request.get_json()
        required_fields = ['traktor_gelis_izmir_kirim_id', 'dayibasi_adi', 'bohca_sayisi']
        if not all(field in data for field in required_fields):
            return jsonify({'message': 'Eksik alanlar var.'}), 400
        conn = get_db_connection()
        if not conn:
            return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
        try:
            cursor = conn.cursor()
            region = data.get('region')
            if not region:
                return jsonify({'message': 'region parametresi zorunludur.'}), 400
            # Bölge kontrolü
            cursor.execute("SELECT region FROM traktor_gelis_izmir_kirim WHERE id = %s", (data['traktor_gelis_izmir_kirim_id'],))
            kart_region = cursor.fetchone()
            if not kart_region:
                return jsonify({'message': 'Kart kaydı bulunamadı.'}), 404
            if kart_region[0] != region:
                return jsonify({'message': 'Bölge uyuşmazlığı: Bu kart farklı bir bölgeye ait.'}), 403
            sql = """
            INSERT INTO traktor_gelis_izmir_kirim_dayibasi (traktor_gelis_izmir_kirim_id, dayibasi_adi, bohca_sayisi)
            VALUES (%s, %s, %s)
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
    elif request.method == 'GET':
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
    region = data.get('region')
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        cursor.execute("SELECT region FROM traktor_gelis_izmir_kirim WHERE id = %s", (data['traktor_gelis_izmir_kirim_id'],))
        kart_region = cursor.fetchone()
        if not kart_region:
            return jsonify({'message': 'Kart kaydı bulunamadı.'}), 404
        if kart_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı: Bu kart farklı bir bölgeye ait.'}), 403
        sql = """
        INSERT INTO traktor_gelis_izmir_kirim_agirlik (traktor_gelis_izmir_kirim_id, agirlik, created_at)
        VALUES (%s, %s, %s)
        """
        params = (
            data['traktor_gelis_izmir_kirim_id'], data['agirlik'], data['created_at']
        )
        cursor.execute(sql, params)
        conn.commit()
        return jsonify({'message': 'Traktör geliş ağırlık kaydı başarıyla eklendi.'}), 201
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_izmir_kirim_agirlik/<int:agirlik_id>', methods=['PUT'])
def update_traktor_gelis_izmir_kirim_agirlik(agirlik_id):
    data = request.get_json()
    agirlik = data.get('agirlik')
    region = data.get('region')
    if agirlik is None:
        return jsonify({'message': 'agirlik zorunludur.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü - agirlik_id'den kart_id'yi bul, sonra region'ı kontrol et
        cursor.execute("SELECT traktor_gelis_izmir_kirim_id FROM traktor_gelis_izmir_kirim_agirlik WHERE id = %s", (agirlik_id,))
        agirlik_record = cursor.fetchone()
        if not agirlik_record:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        kart_id = agirlik_record[0]
        cursor.execute("SELECT region FROM traktor_gelis_izmir_kirim WHERE id = %s", (kart_id,))
        kart_region = cursor.fetchone()
        if not kart_region or kart_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("UPDATE traktor_gelis_izmir_kirim_agirlik SET agirlik = %s WHERE id = %s", (agirlik, agirlik_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Ağırlık kaydı bulunamadı.'}), 404
        return jsonify({'message': 'Ağırlık başarıyla güncellendi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
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
        region = request.args.get('region')
        if region:
            cursor.execute("SELECT * FROM traktor_gelis_izmir_kirim WHERE region = %s ORDER BY tarih DESC, plaka, gelis_no DESC", (region,))
        else:
            cursor.execute("SELECT * FROM traktor_gelis_izmir_kirim ORDER BY tarih DESC, plaka, gelis_no DESC")
        kartlar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        for kart in kartlar:
            cursor.execute("SELECT * FROM traktor_gelis_izmir_kirim_dayibasi WHERE traktor_gelis_izmir_kirim_id = %s", (kart['id'],))
            dayibasilari = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['dayibasilari'] = dayibasilari
            kart['toplam_bohca'] = sum([d['bohca_sayisi'] for d in dayibasilari]) if dayibasilari else 0
            cursor.execute("SELECT id, agirlik, created_at FROM traktor_gelis_izmir_kirim_agirlik WHERE traktor_gelis_izmir_kirim_id = %s ORDER BY id", (kart['id'],))
            agirliklar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['agirliklar'] = agirliklar
            if agirliklar:
                kart['ortalama_agirlik'] = sum([a['agirlik'] for a in agirliklar]) / len(agirliklar)
                # Toplam KG = Tüm ağırlıkların toplamı (ortalama * bohça değil!)
                kart['toplam_kg'] = sum([a['agirlik'] for a in agirliklar])
            else:
                kart['ortalama_agirlik'] = 0
                kart['toplam_kg'] = 0
        return jsonify(kartlar)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()


# Sergi oluşturma veya güncelleme
@app.route('/api/sergi_kiriz', methods=['POST'])
def add_or_update_sergi_kiriz():
    data = request.get_json()
    required_fields = ['sergi_no', 'sepet_sayisi', 'traktor_gelis_izmir_id']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Eksik alanlar var.'}), 400
    
    if data['sepet_sayisi'] <= 0 or data['sepet_sayisi'] > 150:
        return jsonify({'message': 'Sepet sayısı 1-150 arasında olmalıdır.'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Mevcut sergiyi kontrol et
        cursor.execute("SELECT id, toplam_sepet FROM sergi_kiriz WHERE sergi_no = %s", (data['sergi_no'],))
        sergi = cursor.fetchone()
        
        if sergi:
            # Var olan sergiye ekleme yap
            sergi_id = sergi['id'] if isinstance(sergi, dict) else sergi[0]
            current_sepet = sergi['toplam_sepet'] if isinstance(sergi, dict) else sergi[1]
            new_total = current_sepet + data['sepet_sayisi']
            
            if new_total > 150:
                remaining = 150 - current_sepet
                return jsonify({
                    'message': f'Bu sergiye en fazla {remaining} sepet eklenebilir. Toplam kapasite: 150',
                    'remaining': remaining
                }), 400
            
            # Sergiyi güncelle
            cursor.execute("""
                UPDATE sergi_kiriz 
                SET toplam_sepet = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (new_total, sergi_id))
            
            # Dağıtım kaydı ekle
            cursor.execute("""
                INSERT INTO sergi_sepet_dagitim 
                (sergi_id, traktor_gelis_izmir_kirim_id, sepet_sayisi)
                VALUES (%s, %s, %s)
            """, (sergi_id, data['traktor_gelis_izmir_id'], data['sepet_sayisi']))
            
            message = f'Sergi {data["sergi_no"]} güncellendi. Yeni toplam: {new_total}/150'
        else:
            # Yeni sergi oluştur
            cursor.execute("""
                INSERT INTO sergi_kiriz (sergi_no, toplam_sepet)
                VALUES (%s, %s)
                RETURNING id
            """, (data['sergi_no'], data['sepet_sayisi']))
            result = cursor.fetchone()
            sergi_id = result['id'] if isinstance(result, dict) else result[0]
            
            # Dağıtım kaydı ekle
            cursor.execute("""
                INSERT INTO sergi_sepet_dagitim 
                (sergi_id, traktor_gelis_izmir_kirim_id, sepet_sayisi)
                VALUES (%s, %s, %s)
            """, (sergi_id, data['traktor_gelis_izmir_id'], data['sepet_sayisi']))
            
            message = f'Sergi {data["sergi_no"]} oluşturuldu. Toplam sepet: {data["sepet_sayisi"]}/150'
        
        conn.commit()
        return jsonify({'message': message}), 201
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

# Tamamlanmamış sergileri listeleme
@app.route('/api/sergi_kiriz/incomplete', methods=['GET'])
def get_incomplete_sergi_kiriz():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, sergi_no, toplam_sepet, 
                   (150 - toplam_sepet) as kalan_kapasite
            FROM sergi_kiriz
            WHERE toplam_sepet < 150
            ORDER BY sergi_no
        """)
        
        columns = [column[0] for column in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return jsonify(results)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()
# Bu endpoint'i Python API dosyanıza ekleyin
@app.route('/api/sergi_kiriz/<int:sergi_no>/detay', methods=['GET'])
def get_sergi_detay(sergi_no):
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Sergi bilgilerini getir
        cursor.execute("""
            SELECT id, sergi_no, toplam_sepet,
                   (150 - toplam_sepet) as kalan_kapasite,
                   CASE WHEN toplam_sepet >= 150 THEN 1 ELSE 0 END as sergi_dolu
            FROM sergi_kiriz 
            WHERE sergi_no = %s
        """, (sergi_no,))
        
        sergi = cursor.fetchone()
        if not sergi:
            return jsonify({'message': f'Sergi {sergi_no} bulunamadı.'}), 404
        
        sergi_dict = dict(zip([col[0] for col in cursor.description], sergi))
        
        # Bu sergiye katkıda bulunan traktörleri getir
        cursor.execute("""
            SELECT 
                t.id as traktor_id,
                t.plaka,
                t.tarih,
                d.sepet_sayisi as bu_traktorden_sepet
            FROM sergi_sepet_dagitim d
            JOIN traktor_gelis_izmir_kirim t ON d.traktor_gelis_izmir_kirim_id = t.id
            WHERE d.sergi_id = %s
            ORDER BY t.tarih DESC, t.plaka
        """, (sergi_dict['id'],))
        
        dagitimlar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        
        # Her traktör için ortalama ağırlık hesapla
        for dagitim in dagitimlar:
            cursor.execute("""
                SELECT AVG(agirlik) as ortalama_agirlik
                FROM traktor_gelis_izmir_kirim_agirlik 
                WHERE traktor_gelis_izmir_kirim_id = %s
            """, (dagitim['traktor_id'],))
            
            agirlik_result = cursor.fetchone()
            ortalama_agirlik = agirlik_result[0] if agirlik_result and agirlik_result[0] else 0
            dagitim['toplam_kg'] = dagitim['bu_traktorden_sepet'] * ortalama_agirlik
        
        # Sonucu birleştir
        result = {
            'sergi_no': sergi_dict['sergi_no'],
            'toplam_sepet': sergi_dict['toplam_sepet'],
            'kalan_kapasite': sergi_dict['kalan_kapasite'],
            'sergi_dolu': sergi_dict['sergi_dolu'],
            'dagitimlar': dagitimlar
        }
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/traktor_gelis_izmir_kirim/summary_with_sergi', methods=['GET'])
def get_traktor_gelis_izmir_kirim_summary_with_sergi():
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        
        # 1. Tüm traktör kartlarını getir
        region = request.args.get('region')
        if region:
            cursor.execute("""
                SELECT id, tarih, plaka, gelis_no 
                FROM traktor_gelis_izmir_kirim 
                WHERE region = %s
                ORDER BY tarih DESC, plaka, gelis_no DESC
            """, (region,))
        else:
            cursor.execute("""
            SELECT id, tarih, plaka, gelis_no 
            FROM traktor_gelis_izmir_kirim 
            ORDER BY tarih DESC, plaka, gelis_no DESC
        """)
        kartlar = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
        
        # 2. Her kart için detayları doldur
        for kart in kartlar:
            # Dayıbaşıları getir
            cursor.execute("""
                SELECT id, dayibasi_adi, bohca_sayisi 
                FROM traktor_gelis_izmir_kirim_dayibasi 
                WHERE traktor_gelis_izmir_kirim_id = %s
            """, (kart['id'],))
            kart['dayibasilari'] = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            kart['toplam_bohca'] = sum([d['bohca_sayisi'] for d in kart['dayibasilari']]) if kart['dayibasilari'] else 0
            
            # Ağırlıkları getir
            cursor.execute("""
                SELECT id, agirlik, created_at 
                FROM traktor_gelis_izmir_kirim_agirlik 
                WHERE traktor_gelis_izmir_kirim_id = %s 
                ORDER BY id
            """, (kart['id'],))
            kart['agirliklar'] = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            
            # Ortalama ağırlık hesapla
            if kart['agirliklar']:
                kart['ortalama_agirlik'] = sum([a['agirlik'] for a in kart['agirliklar']]) / len(kart['agirliklar'])
            else:
                kart['ortalama_agirlik'] = 0
            
            # Toplam kg hesapla
            kart['toplam_kg'] = kart['toplam_bohca'] * kart['ortalama_agirlik']
            
            # Sergileri getir (GÜNCELLENMİŞ KISIM)
            cursor.execute("""
                SELECT 
                    s.id,
                    s.sergi_no,
                    d.sepet_sayisi as bu_traktorden_sepet,
                    s.toplam_sepet as sergi_toplam_sepet,
                    (150 - s.toplam_sepet) as sergi_kalan_kapasite,
                    CASE WHEN s.toplam_sepet >= 150 THEN 1 ELSE 0 END as sergi_dolu
                FROM sergi_sepet_dagitim d
                JOIN sergi_kiriz s ON d.sergi_id = s.id
                WHERE d.traktor_gelis_izmir_kirim_id = %s
                ORDER BY s.sergi_no
            """, (kart['id'],))
            kart['sergiler'] = [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
            
            # Toplam sergi sepet sayısını hesapla (bu traktörün tüm sergilere eklediği sepetler)
            kart['toplam_sergi_sepet'] = sum([s['bu_traktorden_sepet'] for s in kart['sergiler']]) if kart['sergiler'] else 0
        
        return jsonify(kartlar)
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()
#-----------------------------------------------------------------------------------------
@app.route('/api/scv_sera/<int:sera_id>', methods=['PATCH'])
def update_scv_sera_bitis_tarihi(sera_id):
    data = request.get_json()
    soldurma_bitis_tarihi = data.get('soldurma_bitis_tarihi')
    region = data.get('region')
    if not soldurma_bitis_tarihi:
        return jsonify({'message': 'soldurma_bitis_tarihi gerekli.'}), 400
    if not region:
        return jsonify({'message': 'region parametresi zorunludur.'}), 400
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    try:
        cursor = conn.cursor()
        # Bölge kontrolü
        cursor.execute("SELECT region FROM scv_sera WHERE id = %s", (sera_id,))
        sera_region = cursor.fetchone()
        if not sera_region:
            return jsonify({'message': 'Sera kaydı bulunamadı.'}), 404
        if sera_region[0] != region:
            return jsonify({'message': 'Bölge uyuşmazlığı.'}), 403
        cursor.execute("UPDATE scv_sera SET soldurma_bitis_tarihi = %s WHERE id = %s", (soldurma_bitis_tarihi, sera_id))
        conn.commit()
        return jsonify({'message': 'Soldurma bitiş tarihi güncellendi.'})
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

# JTI SCV Kutulama Summary
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
            cursor.execute("SELECT id, value FROM jti_scv_kutulama_kuru_kg WHERE dayibasi_id = %s ORDER BY id", r['dayibasi_id'])
            r['kuruKgList'] = [{'value': row.value} for row in cursor.fetchall()]
            cursor.execute("SELECT id, value FROM jti_scv_kutulama_sera_yas_kg WHERE dayibasi_id = %s ORDER BY id", r['dayibasi_id'])
            r['seraYasKgList'] = [{'value': row.value} for row in cursor.fetchall()]
            r['toplamKuruKg'] = sum([kg['value'] or 0 for kg in r['kuruKgList']])
            r['toplamYasKg'] = sum([kg['value'] or 0 for kg in r['seraYasKgList']])
            r['yasKuruOrani'] = r['toplamKuruKg'] > 0 and (r['toplamYasKg'] / r['toplamKuruKg']) or 0
            r['departman'] = 'JTI SCV'
            r['kutu_sayisi'] = len(r['kuruKgList'])
        return jsonify(results)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

# PMI SCV Kutulama Summary

# PMI TOPPING Kutulama Summary
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
            cursor.execute("SELECT id, value FROM pmi_topping_kutulama_kuru_kg WHERE dayibasi_id = %s ORDER BY id", r['dayibasi_id'])
            r['kuruKgList'] = [{'value': row.value} for row in cursor.fetchall()]
            cursor.execute("SELECT id, value FROM pmi_topping_kutulama_sera_yas_kg WHERE dayibasi_id = %s ORDER BY id", r['dayibasi_id'])
            r['seraYasKgList'] = [{'value': row.value} for row in cursor.fetchall()]
            r['toplamKuruKg'] = sum([kg['value'] or 0 for kg in r['kuruKgList']])
            r['toplamYasKg'] = sum([kg['value'] or 0 for kg in r['seraYasKgList']])
            r['yasKuruOrani'] = r['toplamKuruKg'] > 0 and (r['toplamYasKg'] / r['toplamKuruKg']) or 0
            r['departman'] = 'PMI Topping'
            r['kutu_sayisi'] = len(r['kuruKgList'])
        return jsonify(results)
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn: conn.close()

# --- Admin Authentication ve Kullanıcı Yönetimi Endpoint'leri ---
#-----------------------------------------------------------------------------------------------------
import hashlib

def hash_password(password):
    """Şifreyi hash'le (basit MD5, production'da bcrypt kullanılmalı)"""
    return hashlib.md5(password.encode()).hexdigest()

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin girişi"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Kullanıcı adı ve şifre gerekli.'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        hashed_password = hash_password(password)
        
        # Önce user_type kolonunun var olup olmadığını kontrol et
        # Basit bir try-except ile kontrol et
        has_user_type = False
        try:
            # Direkt olarak user_type kolonunu sorgula
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'admin_users' 
                AND column_name = 'user_type'
            """)
            result = cursor.fetchone()
            has_user_type = result is not None
        except Exception as e:
            print(f"Kolon kontrolü hatası: {e}")
            import traceback
            print(traceback.format_exc())
            has_user_type = False
        
        # Kullanıcıyı sorgula - user_type kolonu varsa dahil et
        if has_user_type:
            try:
                cursor.execute("""
                    SELECT id, username, name, surname, is_super_admin, user_type
                    FROM admin_users 
                    WHERE username = %s AND password = %s
                """, (username, hashed_password))
            except Exception as e:
                # user_type kolonu varsa ama sorgu başarısız olursa, kolonsuz dene
                print(f"user_type ile sorgu hatası: {e}")
                cursor.execute("""
                    SELECT id, username, name, surname, is_super_admin
                    FROM admin_users 
                    WHERE username = %s AND password = %s
                """, (username, hashed_password))
                has_user_type = False
        else:
            # user_type kolonu yoksa, sadece diğer kolonları seç
            cursor.execute("""
                SELECT id, username, name, surname, is_super_admin
                FROM admin_users 
                WHERE username = %s AND password = %s
            """, (username, hashed_password))
        
        user = cursor.fetchone()
        if not user:
            return jsonify({'message': 'Kullanıcı adı veya şifre hatalı.'}), 401
        
        # Kullanıcının erişebileceği bölgeleri al
        cursor.execute("""
            SELECT region_code 
            FROM user_regions 
            WHERE admin_user_id = %s
        """, (user['id'],))
        regions = [row['region_code'] for row in cursor.fetchall()]
        
        # user_type varsa kullan, yoksa varsayılan olarak 'admin'
        user_type = None
        if has_user_type:
            try:
                user_type_value = user.get('user_type')
                if user_type_value is not None and str(user_type_value).strip():
                    # Değer varsa ve boş değilse kullan
                    user_type = str(user_type_value).strip().lower()
                else:
                    # NULL veya boş değer - veritabanından tekrar kontrol et
                    cursor.execute("SELECT user_type FROM admin_users WHERE id = %s", (user['id'],))
                    db_user_type = cursor.fetchone()
                    if db_user_type and db_user_type.get('user_type') and str(db_user_type['user_type']).strip():
                        user_type = str(db_user_type['user_type']).strip().lower()
                    else:
                        # Hala NULL veya boş ise, varsayılan olarak admin
                        user_type = 'admin'
                        print(f"⚠️ User {username} (ID: {user['id']}) için user_type NULL/boş, varsayılan 'admin' kullanılıyor")
            except Exception as e:
                print(f"user_type okuma hatası: {e}")
                import traceback
                print(traceback.format_exc())
                user_type = 'admin'
        else:
            # user_type kolonu yok - varsayılan olarak admin
            user_type = 'admin'
        
        # Debug log - detaylı
        print(f"=== LOGIN DEBUG ===")
        print(f"Username: {username}")
        print(f"User ID: {user['id']}")
        print(f"Has user_type column: {has_user_type}")
        print(f"User Type from DB: {user_type}")
        print(f"Regions: {regions}")
        print(f"===================")
        
        return jsonify({
            'message': 'Giriş başarılı.',
            'user': {
                'id': user['id'],
                'username': user['username'],
                'name': user['name'],
                'surname': user['surname'],
                'is_super_admin': bool(user['is_super_admin']),
                'user_type': user_type,  # Mutlaka bir değer döndür
                'regions': regions
            }
        }), 200
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Admin login hatası: {e}")
        print(f"Detaylar: {error_details}")
        return jsonify({'message': f'Giriş sırasında bir hata oluştu: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/users', methods=['GET'])
def get_admin_users():
    """Tüm admin kullanıcılarını listele"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, username, name, surname, is_super_admin, COALESCE(user_type, 'admin') as user_type, created_at
            FROM admin_users
            ORDER BY created_at DESC
        """)
        
        users = []
        for row in cursor.fetchall():
            # RealDictCursor kullanıldığı için row zaten bir dictionary
            user_dict = dict(row)
            # Her kullanıcının bölgelerini al
            cursor.execute("""
                SELECT region_code 
                FROM user_regions 
                WHERE admin_user_id = %s
            """, (user_dict['id'],))
            regions = cursor.fetchall()
            user_dict['regions'] = [r['region_code'] for r in regions]
            user_dict['is_super_admin'] = bool(user_dict['is_super_admin'])
            user_dict['user_type'] = user_dict.get('user_type') or 'admin'
            users.append(user_dict)
        
        return jsonify(users), 200
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Admin users listeleme hatası: {e}")
        print(f"Detaylar: {error_details}")
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/users', methods=['POST'])
def create_admin_user():
    """Yeni admin kullanıcısı oluştur"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    name = data.get('name', '')
    surname = data.get('surname', '')
    is_super_admin = data.get('is_super_admin', False)
    user_type = data.get('user_type', 'admin')  # admin, supervisor, bolge_muduru
    regions = data.get('regions', [])
    
    if not username or not password:
        return jsonify({'message': 'Kullanıcı adı ve şifre gerekli.'}), 400
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Kullanıcı adı kontrolü
        cursor.execute("SELECT id FROM admin_users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({'message': 'Bu kullanıcı adı zaten kullanılıyor.'}), 409
        
        # Kullanıcıyı oluştur
        hashed_password = hash_password(password)
        cursor.execute("""
            INSERT INTO admin_users (username, password, name, surname, is_super_admin, user_type)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (username, hashed_password, name, surname, 1 if is_super_admin else 0, user_type))
        
        result = cursor.fetchone()
        user_id = result['id']
        
        # Super admin ise tüm bölgelere erişim ver
        if is_super_admin:
            all_regions = ['ADY_DOGU', 'ADY_BATI', 'MAN', 'MAR']
            for region in all_regions:
                cursor.execute("""
                    INSERT INTO user_regions (admin_user_id, region_code)
                    VALUES (%s, %s)
                """, (user_id, region))
        else:
            # Belirtilen bölgelere erişim ver
            for region in regions:
                cursor.execute("""
                    INSERT INTO user_regions (admin_user_id, region_code)
                    VALUES (%s, %s)
                """, (user_id, region))
        
        conn.commit()
        return jsonify({'message': 'Kullanıcı başarıyla oluşturuldu.', 'user_id': user_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
def update_admin_user(user_id):
    """Admin kullanıcısını güncelle"""
    data = request.get_json()
    name = data.get('name')
    surname = data.get('surname')
    password = data.get('password')
    is_super_admin = data.get('is_super_admin', False)
    user_type = data.get('user_type', 'admin')
    regions = data.get('regions', [])
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Kullanıcıyı güncelle
        if password:
            hashed_password = hash_password(password)
            cursor.execute("""
                UPDATE admin_users 
                SET name = %s, surname = %s, password = %s, is_super_admin = %s, user_type = %s
                WHERE id = %s
            """, (name, surname, hashed_password, 1 if is_super_admin else 0, user_type, user_id))
        else:
            cursor.execute("""
                UPDATE admin_users 
                SET name = %s, surname = %s, is_super_admin = %s, user_type = %s
                WHERE id = %s
            """, (name, surname, 1 if is_super_admin else 0, user_type, user_id))
        
        # Mevcut bölge yetkilerini sil
        cursor.execute("DELETE FROM user_regions WHERE admin_user_id = %s", (user_id,))
        
        # Yeni bölge yetkilerini ekle
        if is_super_admin:
            all_regions = ['ADY_DOGU', 'ADY_BATI', 'MAN', 'MAR']
            for region in all_regions:
                cursor.execute("""
                    INSERT INTO user_regions (admin_user_id, region_code)
                    VALUES (%s, %s)
                """, (user_id, region))
        else:
            for region in regions:
                cursor.execute("""
                    INSERT INTO user_regions (admin_user_id, region_code)
                    VALUES (%s, %s)
                """, (user_id, region))
        
        conn.commit()
        return jsonify({'message': 'Kullanıcı başarıyla güncellendi.'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
def delete_admin_user(user_id):
    """Admin kullanıcısını sil"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admin_users WHERE id = %s", (user_id,))
        conn.commit()
        
        if cursor.rowcount == 0:
            return jsonify({'message': 'Kullanıcı bulunamadı.'}), 404
        
        return jsonify({'message': 'Kullanıcı başarıyla silindi.'}), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"PMI Topping Dizim Summary hatası: {error_trace}")
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/regions', methods=['GET'])
def get_all_regions():
    """Tüm bölgeleri listele"""
    regions = [
        {'code': 'ADY_DOGU', 'name': 'Adıyaman Doğu'},
        {'code': 'ADY_BATI', 'name': 'Adıyaman Batı'},
        {'code': 'MAN', 'name': 'Manisa'},
        {'code': 'MAR', 'name': 'Mardin'}
    ]
    return jsonify(regions), 200

@app.route('/api/admin/region-stats/<region_code>', methods=['GET'])
def get_region_stats(region_code):
    """Bölge istatistiklerini getir - bölge bazlı filtreleme ile"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        stats = {
            'region_code': region_code,
            'total_kg': 0,
            'total_sepet': 0,
            'total_kutu': 0,
            'total_kutu_kg': 0
        }
        
        if region_code == 'ALL':
            # Genel toplam - tüm bölgeler
            # SCV Kutulama toplamları
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(toplam_kuru_kg), 0) as total_kg,
                    COUNT(*) as total_kutu
                FROM scv_kutulama
            """)
            scv_result = cursor.fetchone()
            if scv_result:
                stats['total_kutu_kg'] += float(scv_result['total_kg'] or 0)
                stats['total_kutu'] += int(scv_result['total_kutu'] or 0)
            
            # İzmir Kutulama toplamları
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(toplam_kuru_kg), 0) as total_kg,
                    COUNT(*) as total_kutu
                FROM izmir_kutulama
            """)
            izmir_result = cursor.fetchone()
            if izmir_result:
                stats['total_kutu_kg'] += float(izmir_result['total_kg'] or 0)
                stats['total_kutu'] += int(izmir_result['total_kutu'] or 0)
            
            # FCV Kırım toplamları (sepet sayısı)
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(boca_sayisi), 0) as total_sepet
                FROM fcv_kirim_gunluk
            """)
            fcv_result = cursor.fetchone()
            if fcv_result:
                stats['total_sepet'] += int(fcv_result['total_sepet'] or 0)
            
            # İzmir Kırım toplamları
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(toplam_bohca), 0) as total_sepet,
                    COALESCE(SUM(toplam_kg), 0) as total_kg
                FROM traktor_gelis_izmir_kirim
            """)
            izmir_kirim_result = cursor.fetchone()
            if izmir_kirim_result:
                stats['total_sepet'] += int(izmir_kirim_result['total_sepet'] or 0)
                stats['total_kg'] += float(izmir_kirim_result['total_kg'] or 0)
        else:
            # Belirli bir bölge için - region kolonuna göre filtrele
            # SCV Kutulama toplamları
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(toplam_kuru_kg), 0) as total_kg,
                    COUNT(*) as total_kutu
                FROM scv_kutulama
                WHERE region = %s
            """, (region_code,))
            scv_result = cursor.fetchone()
            if scv_result:
                stats['total_kutu_kg'] += float(scv_result['total_kg'] or 0)
                stats['total_kutu'] += int(scv_result['total_kutu'] or 0)
            
            # İzmir Kutulama toplamları
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(toplam_kuru_kg), 0) as total_kg,
                    COUNT(*) as total_kutu
                FROM izmir_kutulama
                WHERE region = %s
            """, (region_code,))
            izmir_result = cursor.fetchone()
            if izmir_result:
                stats['total_kutu_kg'] += float(izmir_result['total_kg'] or 0)
                stats['total_kutu'] += int(izmir_result['total_kutu'] or 0)
            
            # FCV Kırım toplamları
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(boca_sayisi), 0) as total_sepet
                FROM fcv_kirim_gunluk
                WHERE region = %s
            """, (region_code,))
            fcv_result = cursor.fetchone()
            if fcv_result:
                stats['total_sepet'] += int(fcv_result['total_sepet'] or 0)
            
            # İzmir Kırım toplamları
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(toplam_bohca), 0) as total_sepet,
                    COALESCE(SUM(toplam_kg), 0) as total_kg
                FROM traktor_gelis_izmir_kirim
                WHERE region = %s
            """, (region_code,))
            izmir_kirim_result = cursor.fetchone()
            if izmir_kirim_result:
                stats['total_sepet'] += int(izmir_kirim_result['total_sepet'] or 0)
                stats['total_kg'] += float(izmir_kirim_result['total_kg'] or 0)
        
        return jsonify(stats), 200
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Bölge istatistikleri hatası: {e}")
        print(f"Detaylar: {error_details}")
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/region-details/<region_code>', methods=['GET'])
def get_region_details(region_code):
    """Bölge detay verilerini getir (tablolar ve grafikler için) - bölge bazlı filtreleme ile"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        result = {
            'region_code': region_code,
            'kirim_data': [],
            'kutulama_data': [],
            'sergi_data': [],
            'summary': {
                'total_kg': 0,
                'total_sepet': 0,
                'total_kutu': 0,
                'total_kutu_kg': 0
            }
        }
        
        if region_code == 'ALL':
            # Genel toplam - tüm bölgeler
            # Kırım verileri
            cursor.execute("""
                SELECT 
                    id, tarih, plaka, toplam_bohca, toplam_kg
                FROM traktor_gelis_izmir_kirim
                ORDER BY tarih DESC
                LIMIT 100
            """)
            result['kirim_data'] = cursor.fetchall()
            
            # Kutulama verileri
            cursor.execute("""
                SELECT 
                    id, tarih, dayibasi, toplam_kuru_kg, kutular
                FROM izmir_kutulama
                ORDER BY tarih DESC
                LIMIT 100
            """)
            result['kutulama_data'] = cursor.fetchall()
            
            # SCV Kutulama verileri
            cursor.execute("""
                SELECT 
                    id, tarih, dayibasi, toplam_kuru_kg, kutular
                FROM scv_kutulama
                ORDER BY tarih DESC
                LIMIT 100
            """)
            scv_kutulama = cursor.fetchall()
            result['kutulama_data'].extend(scv_kutulama)
            
            # Sergi verileri
            cursor.execute("""
                SELECT 
                    id, sergi_no, toplam_sepet, created_at
                FROM sergi_kiriz
                ORDER BY created_at DESC
                LIMIT 100
            """)
            result['sergi_data'] = cursor.fetchall()
        else:
            # Belirli bir bölge için - region kolonuna göre filtrele
            # İzmir Kırım verileri
            cursor.execute("""
                SELECT 
                    id, tarih, plaka, toplam_bohca, toplam_kg
                FROM traktor_gelis_izmir_kirim
                WHERE region = %s
                ORDER BY tarih DESC
                LIMIT 100
            """, (region_code,))
            result['kirim_data'] = cursor.fetchall()
            
            # JTI SCV Kırım verileri
            cursor.execute("""
                SELECT 
                    t.id, t.tarih, t.plaka,
                    COALESCE(SUM(td.bohca_sayisi), 0) as toplam_bohca,
                    COALESCE(SUM(ta.agirlik), 0) as toplam_kg
                FROM traktor_gelis_jti_kirim t
                LEFT JOIN traktor_gelis_jti_kirim_dayibasi td ON t.id = td.traktor_gelis_jti_kirim_id
                LEFT JOIN traktor_gelis_jti_kirim_agirlik ta ON t.id = ta.traktor_gelis_jti_kirim_id
                WHERE t.region = %s
                GROUP BY t.id, t.tarih, t.plaka
                ORDER BY t.tarih DESC
                LIMIT 100
            """, (region_code,))
            jti_kirim = cursor.fetchall()
            result['kirim_data'].extend(jti_kirim)
            
            # PMI SCV Kırım verileri
            cursor.execute("""
                SELECT 
                    t.id, t.tarih, t.plaka,
                    COALESCE(SUM(td.bohca_sayisi), 0) as toplam_bohca,
                    COALESCE(SUM(ta.agirlik), 0) as toplam_kg
                FROM traktor_gelis_pmi_kirim t
                LEFT JOIN traktor_gelis_pmi_kirim_dayibasi td ON t.id = td.traktor_gelis_pmi_kirim_id
                LEFT JOIN traktor_gelis_pmi_kirim_agirlik ta ON t.id = ta.traktor_gelis_pmi_kirim_id
                WHERE t.region = %s
                GROUP BY t.id, t.tarih, t.plaka
                ORDER BY t.tarih DESC
                LIMIT 100
            """, (region_code,))
            pmi_kirim = cursor.fetchall()
            result['kirim_data'].extend(pmi_kirim)
            
            # İzmir Kutulama verileri
            cursor.execute("""
                SELECT 
                    id, tarih, dayibasi, toplam_kuru_kg, kutular
                FROM izmir_kutulama
                WHERE region = %s
                ORDER BY tarih DESC
                LIMIT 100
            """, (region_code,))
            result['kutulama_data'] = cursor.fetchall()
            
            # SCV Kutulama verileri
            cursor.execute("""
                SELECT 
                    id, tarih, dayibasi, toplam_kuru_kg, kutular
                FROM scv_kutulama
                WHERE region = %s
                ORDER BY tarih DESC
                LIMIT 100
            """, (region_code,))
            scv_kutulama = cursor.fetchall()
            result['kutulama_data'].extend(scv_kutulama)
        
        # Özet istatistikler
        if result['kirim_data']:
            result['summary']['total_sepet'] = sum([float(row.get('toplam_bohca', 0) or 0) for row in result['kirim_data']])
            result['summary']['total_kg'] = sum([float(row.get('toplam_kg', 0) or 0) for row in result['kirim_data']])
        
        if result['kutulama_data']:
            result['summary']['total_kutu_kg'] = sum([float(row.get('toplam_kuru_kg', 0) or 0) for row in result['kutulama_data']])
            # Kutu sayısını kutular JSON'undan hesapla
            for row in result['kutulama_data']:
                try:
                    kutular_str = row.get('kutular', '[]') or '[]'
                    if isinstance(kutular_str, str):
                        kutular = json.loads(kutular_str)
                    else:
                        kutular = kutular_str
                    result['summary']['total_kutu'] += len([k for k in kutular if k and k > 0])
                except:
                    pass
        
        return jsonify(result), 200
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Bölge detay hatası: {e}")
        print(f"Detaylar: {error_details}")
        return jsonify({'message': f'Hata: {e}'}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/clear-all-data', methods=['POST'])
def clear_all_data():
    """Users tablosu hariç tüm tabloları temizle (test için)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Tüm tabloları al (users hariç)
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name != 'users'
            ORDER BY table_name
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        
        if not tables:
            return jsonify({'message': 'Temizlenecek tablo bulunamadı.'}), 404
        
        # Foreign key constraint'lerini geçici olarak devre dışı bırak
        cursor.execute("SET session_replication_role = 'replica';")
        
        cleared_tables = []
        errors = []
        
        # Her tabloyu temizle
        for table in tables:
            try:
                cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
                cleared_tables.append(table)
            except Exception as e:
                errors.append(f"{table}: {str(e)}")
        
        # Foreign key constraint'lerini tekrar aktif et
        cursor.execute("SET session_replication_role = 'origin';")
        
        conn.commit()
        
        result = {
            'message': f'{len(cleared_tables)} tablo temizlendi.',
            'cleared_tables': cleared_tables,
            'total_tables': len(tables),
            'errors': errors if errors else None
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Veritabanı temizleme hatası: {error_trace}")
        if conn:
            conn.rollback()
            # Foreign key constraint'lerini tekrar aktif et
            try:
                cursor.execute("SET session_replication_role = 'origin';")
            except:
                pass
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/admin/clear-dizim-data', methods=['POST'])
def clear_dizim_data():
    """Tüm dizim kayıtlarını siler (dayıbaşı, günlük, ağırlık, yaprak)"""
    conn = get_db_connection()
    if not conn:
        return jsonify({'message': 'Veritabanı bağlantı hatası.'}), 500
    
    try:
        cursor = conn.cursor()
        
        # Dizim tablolarını temizle (foreign key sırasına göre)
        tables = [
            'jti_scv_dizim_yaprak',
            'jti_scv_dizim_agirlik',
            'jti_scv_dizim_gunluk',
            'jti_scv_dizim_dayibasi_table',
            'pmi_scv_dizim_yaprak',
            'pmi_scv_dizim_agirlik',
            'pmi_scv_dizim_gunluk',
            'pmi_scv_dizim_dayibasi_table',
            'pmi_topping_dizim_yaprak',
            'pmi_topping_dizim_agirlik',
            'pmi_topping_dizim_gunluk',
            'pmi_topping_dizim_dayibasi_table'
        ]
        
        deleted_counts = {}
        for table in tables:
            cursor.execute(f"DELETE FROM {table}")
            deleted_counts[table] = cursor.rowcount
        
        conn.commit()
        
        return jsonify({
            'message': 'Tüm dizim kayıtları başarıyla silindi.',
            'deleted_counts': deleted_counts
        }), 200
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Dizim verileri silme hatası: {error_trace}")
        if conn:
            conn.rollback()
        return jsonify({'message': f'Hata: {str(e)}', 'trace': error_trace}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print(" Veritabanı bağlantısı kontrol ediliyor...")
    if initialize_db():
        ensure_kutulama_alan_column()
        ensure_scv_sera_new_columns()
        ensure_scv_dizim_region_columns()
        ensure_scv_kirim_region_columns()
        ensure_scv_kutulama_region_column()
        ensure_scv_sera_region_column()
        ensure_fcv_region_columns()
        ensure_sevkiyat_region_column()
        ensure_scv_sera_yerleri_region_column()
        print("🚀 Flask uygulaması başlatılıyor...")
        #app.run(debug=True, port=5000)
        port = int(os.environ.get("PORT", 5000))
        app.run(debug=True, host="0.0.0.0", port=port)

    else:
        print("❌ Veritabanı bağlantısı kurulamadı. Uygulama başlatılamıyor.")
        print("\n🔧 Sorun giderme adımları:")
        print("1. PostgreSQL veritabanı bağlantı URL'ini kontrol edin")
        print("2. Veritabanı sunucusunun erişilebilir olduğundan emin olun")
        print("3. Kullanıcı adı ve şifrenin doğru olduğunu kontrol edin")
        print("4. Firewall ayarlarını kontrol edin")
        print("5. 'pip install psycopg2-binary' ile psycopg2'nin yüklü olduğundan emin olun")