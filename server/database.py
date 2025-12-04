"""
RiMayTik Messenger - Серверная база данных
Система безопасного обмена сообщениями
"""

import sqlite3
import bcrypt
import hashlib
import json
from datetime import datetime

class RiMayTikDatabase:
    def __init__(self, db_path="rimaytik_users.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.init_system_info()
    
    def init_system_info(self):
        """Инициализация информации о системе RiMayTik"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_info (
                id INTEGER PRIMARY KEY,
                system_name TEXT DEFAULT 'RiMayTik Messenger',
                version TEXT DEFAULT '1.0.0',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.cursor.execute("SELECT COUNT(*) FROM system_info")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute("""
                INSERT INTO system_info (system_name, version) 
                VALUES ('RiMayTik Messenger', '1.0.0')
            """)
            self.conn.commit()
    
    def create_tables(self):
        """Создание таблиц базы данных RiMayTik"""
        # Таблица пользователей RiMayTik
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS rimaytik_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                display_name TEXT,
                public_key TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                last_seen TIMESTAMP,
                status TEXT DEFAULT 'offline',
                security_level INTEGER DEFAULT 2,  # 1=базовый, 2=стандартный, 3=максимальный
                CONSTRAINT rimaytik_username_unique UNIQUE(username)
            )
        """)
        
        # Таблица контактов пользователей
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS rimaytik_contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                contact_id INTEGER NOT NULL,
                alias TEXT,
                trusted BOOLEAN DEFAULT FALSE,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES rimaytik_users(id),
                FOREIGN KEY (contact_id) REFERENCES rimaytik_users(id),
                CONSTRAINT rimaytik_unique_contact UNIQUE(user_id, contact_id)
            )
        """)
        
        # Таблица метаданных сообщений (E2E шифрование - содержимое не хранится)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS rimaytik_messages_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_uuid TEXT UNIQUE NOT NULL,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                conversation_hash TEXT NOT NULL,
                message_type TEXT DEFAULT 'text',  # text, file, image
                encrypted_size INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                delivered BOOLEAN DEFAULT FALSE,
                read BOOLEAN DEFAULT FALSE,
                self_destruct INTEGER,  # секунд до самоуничтожения
                FOREIGN KEY (sender_id) REFERENCES rimaytik_users(id),
                FOREIGN KEY (receiver_id) REFERENCES rimaytik_users(id)
            )
        """)
        
        # Таблица сессий безопасности
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS rimaytik_security_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                device_info TEXT,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES rimaytik_users(id)
            )
        """)
        
        self.conn.commit()
    
    def register_rimaytik_user(self, username, display_name, public_key, password):
        """Регистрация нового пользователя в RiMayTik"""
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        try:
            self.cursor.execute("""
                INSERT INTO rimaytik_users 
                (username, display_name, public_key, password_hash, status)
                VALUES (?, ?, ?, ?, 'online')
            """, (username, display_name or username, public_key, password_hash))
            
            user_id = self.cursor.lastrowid
            self.conn.commit()
            
            # Создание системного сообщения
            self.cursor.execute("""
                INSERT INTO rimaytik_messages_meta 
                (message_uuid, sender_id, receiver_id, conversation_hash, message_type)
                VALUES (?, 0, ?, ?, 'system')
            """, (f"welcome_{user_id}", user_id, hashlib.sha256(f"welcome_{user_id}".encode()).hexdigest()))
            
            self.conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            return None
    
    def authenticate_rimaytik_user(self, username, password):
        """Аутентификация пользователя RiMayTik"""
        self.cursor.execute("""
            SELECT id, password_hash FROM rimaytik_users 
            WHERE username = ? AND status != 'banned'
        """, (username,))
        result = self.cursor.fetchone()
        
        if result and bcrypt.checkpw(password.encode(), result[1].encode()):
            user_id = result[0]
            # Обновляем время последнего входа
            self.cursor.execute("""
                UPDATE rimaytik_users 
                SET last_login = CURRENT_TIMESTAMP, status = 'online'
                WHERE id = ?
            """, (user_id,))
            self.conn.commit()
            return user_id
        return None
    
    def get_rimaytik_public_key(self, username):
        """Получение публичного ключа пользователя"""
        self.cursor.execute("""
            SELECT public_key FROM rimaytik_users 
            WHERE username = ? AND status = 'online'
        """, (username,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def get_rimaytik_display_name(self, username):
        """Получение отображаемого имени пользователя"""
        self.cursor.execute("""
            SELECT display_name FROM rimaytik_users 
            WHERE username = ?
        """, (username,))
        result = self.cursor.fetchone()
        return result[0] if result else username
    
    def get_rimaytik_online_users(self):
        """Получение списка онлайн пользователей RiMayTik"""
        self.cursor.execute("""
            SELECT username, display_name, security_level 
            FROM rimaytik_users 
            WHERE status = 'online' 
            AND last_seen > datetime('now', '-5 minutes')
            ORDER BY display_name
        """)
        return [
            {
                "username": row[0],
                "display_name": row[1],
                "security_level": row[2]
            }
            for row in self.cursor.fetchall()
        ]
    
    def update_rimaytik_last_seen(self, user_id):
        """Обновление времени последней активности"""
        self.cursor.execute("""
            UPDATE rimaytik_users 
            SET last_seen = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (user_id,))
        self.conn.commit()
    
    def log_rimaytik_message(self, message_uuid, sender, receiver, message_hash, message_type="text"):
        """Логирование метаданных сообщения RiMayTik"""
        try:
            conversation_hash = hashlib.sha256(
                f"{sender}_{receiver}".encode()
            ).hexdigest()
            
            self.cursor.execute("""
                INSERT INTO rimaytik_messages_meta 
                (message_uuid, sender_id, receiver_id, conversation_hash, message_type)
                VALUES (?, 
                    (SELECT id FROM rimaytik_users WHERE username = ?),
                    (SELECT id FROM rimaytik_users WHERE username = ?),
                    ?, ?)
            """, (message_uuid, sender, receiver, conversation_hash, message_type))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Ошибка логирования сообщения RiMayTik: {e}")
            return False
    
    def add_rimaytik_contact(self, user_id, contact_username, alias=None):
        """Добавление контакта в RiMayTik"""
        try:
            self.cursor.execute("""
                SELECT id FROM rimaytik_users WHERE username = ?
            """, (contact_username,))
            contact = self.cursor.fetchone()
            
            if contact:
                self.cursor.execute("""
                    INSERT OR IGNORE INTO rimaytik_contacts 
                    (user_id, contact_id, alias, trusted)
                    VALUES (?, ?, ?, TRUE)
                """, (user_id, contact[0], alias or contact_username))
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка добавления контакта RiMayTik: {e}")
        return False
    
    def get_rimaytik_contacts(self, user_id):
        """Получение списка контактов пользователя"""
        self.cursor.execute("""
            SELECT u.username, u.display_name, u.status, c.alias, c.trusted
            FROM rimaytik_contacts c
            JOIN rimaytik_users u ON c.contact_id = u.id
            WHERE c.user_id = ?
            ORDER BY u.display_name
        """, (user_id,))
        return self.cursor.fetchall()
    
    def create_rimaytik_session(self, user_id, token, device_info, ip_address, expires_hours=24):
        """Создание сессии безопасности RiMayTik"""
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        self.cursor.execute("""
            INSERT INTO rimaytik_security_sessions 
            (user_id, session_token, device_info, ip_address, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, token, device_info, ip_address, expires_at))
        self.conn.commit()
        return token
    
    def validate_rimaytik_session(self, token):
        """Проверка валидности сессии"""
        self.cursor.execute("""
            SELECT user_id FROM rimaytik_security_sessions 
            WHERE session_token = ? 
            AND active = TRUE 
            AND expires_at > CURRENT_TIMESTAMP
        """, (token,))
        result = self.cursor.fetchone()
        return result[0] if result else None
    
    def get_rimaytik_system_stats(self):
        """Получение статистики системы RiMayTik"""
        stats = {}
        
        # Количество пользователей
        self.cursor.execute("SELECT COUNT(*) FROM rimaytik_users")
        stats['total_users'] = self.cursor.fetchone()[0]
        
        # Количество онлайн пользователей
        self.cursor.execute("""
            SELECT COUNT(*) FROM rimaytik_users 
            WHERE status = 'online'
        """)
        stats['online_users'] = self.cursor.fetchone()[0]
        
        # Количество сообщений
        self.cursor.execute("SELECT COUNT(*) FROM rimaytik_messages_meta")
        stats['total_messages'] = self.cursor.fetchone()[0]
        
        # Количество сессий
        self.cursor.execute("""
            SELECT COUNT(*) FROM rimaytik_security_sessions 
            WHERE active = TRUE
        """)
        stats['active_sessions'] = self.cursor.fetchone()[0]
        
        return stats
