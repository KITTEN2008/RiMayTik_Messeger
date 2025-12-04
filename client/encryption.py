"""
RiMayTik Messenger - Система шифрования клиента
Сквозное шифрование (E2EE) с Perfect Forward Secrecy
"""

from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding, x25519
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import constant_time
from cryptography.hazmat.backends import default_backend
import os
import base64
import secrets
import json
import time
import hashlib
from typing import Dict, Tuple, Optional
import uuid

class RiMayTikEncryptionEngine:
    """Движок шифрования RiMayTik"""
    
    def __init__(self, security_level: int = 2):
        self.security_level = security_level  # 1-базовый, 2-стандартный, 3-максимальный
        self.backend = default_backend()
        self.identity_keys = None
        self.ephemeral_keys = None
        self.session_keys = {}  # user -> (send_key, receive_key, ratchet_state)
        self.key_store = {}  # Хранилище ключей
        
        # Инициализация с учетом уровня безопасности
        self._setup_security_level()
    
    def _setup_security_level(self):
        """Настройка параметров безопасности в зависимости от уровня"""
        self.security_params = {
            1: {  # Базовый
                "rsa_key_size": 2048,
                "ec_curve": ec.SECP256R1,
                "kdf_iterations": 100000,
                "key_rotation_hours": 24
            },
            2: {  # Стандартный (рекомендуемый)
                "rsa_key_size": 3072,
                "ec_curve": ec.SECP384R1,
                "kdf_iterations": 200000,
                "key_rotation_hours": 12
            },
            3: {  # Максимальный
                "rsa_key_size": 4096,
                "ec_curve": ec.SECP521R1,
                "kdf_iterations": 500000,
                "key_rotation_hours": 6
            }
        }
    
    def generate_identity_keypair(self):
        """Генерация пары ключей идентификации RiMayTik"""
        params = self.security_params[self.security_level]
        
        self.identity_keys = {
            'private': rsa.generate_private_key(
                public_exponent=65537,
                key_size=params["rsa_key_size"],
                backend=self.backend
            ),
            'public': None
        }
        self.identity_keys['public'] = self.identity_keys['private'].public_key()
        
        print(f"RiMayTik: Сгенерированы ключи идентификации ({params['rsa_key_size']} бит)")
    
    def generate_ephemeral_keypair(self):
        """Генерация временной пары ключей для Perfect Forward Secrecy"""
        params = self.security_params[self.security_level]
        
        self.ephemeral_keys = {
            'private': ec.generate_private_key(
                params["ec_curve"](),
                backend=self.backend
            ),
            'public': None
        }
        self.ephemeral_keys['public'] = self.ephemeral_keys['private'].public_key()
    
    def get_public_key_pem(self) -> str:
        """Получение публичного ключа в формате PEM"""
        if not self.identity_keys:
            self.generate_identity_keypair()
        
        return self.identity_keys['public'].public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    def get_ephemeral_public_key_pem(self) -> str:
        """Получение временного публичного ключа"""
        if not self.ephemeral_keys:
            self.generate_ephemeral_keypair()
        
        return self.ephemeral_keys['public'].public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    def derive_shared_secret(self, peer_public_key_pem: str) -> bytes:
        """Вычисление общего секрета по схеме ECDH"""
        try:
            peer_public_key = serialization.load_pem_public_key(
                peer_public_key_pem.encode(),
                backend=self.backend
            )
            
            shared_secret = self.ephemeral_keys['private'].exchange(
                ec.ECDH(),
                peer_public_key
            )
            
            # Используем HKDF для получения ключа
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b'rimaytik_key_derivation',
                backend=self.backend
            )
            
            return hkdf.derive(shared_secret)
            
        except Exception as e:
            raise ValueError(f"RiMayTik: Ошибка вычисления общего секрета: {e}")
    
    def encrypt_message(self, message: str, recipient_public_key_pem: str) -> Dict:
        """
        Шифрование сообщения с использованием двойного ратача RiMayTik
        1. ECDH для общего секрета
        2. HKDF для сессионных ключей
        3. AES-256-GCM для шифрования
        """
        try:
            # Генерация новых временных ключей для каждого сообщения
            self.generate_ephemeral_keypair()
            
            # Вычисление общего секрета
            shared_secret = self.derive_shared_secret(recipient_public_key_pem)
            
            # Генерация сессионных ключей
            salt = os.urandom(16)
            info = b'rimaytik_message_encryption'
            
            hkdf = HKDF(
                algorithm=hashes.SHA512(),
                length=64,  # 32 для ключа шифрования, 32 для MAC
                salt=salt,
                info=info,
                backend=self.backend
            )
            
            key_material = hkdf.derive(shared_secret)
            encryption_key = key_material[:32]
            mac_key = key_material[32:]
            
            # Шифрование сообщения
            iv = os.urandom(12)  # 96 бит для GCM
            cipher = Cipher(
                algorithms.AES(encryption_key),
                modes.GCM(iv),
                backend=self.backend
            )
            encryptor = cipher.encryptor()
            
            # Дополнительные аутентифицированные данные
            metadata = json.dumps({
                "system": "RiMayTik",
                "timestamp": time.time(),
                "security_level": self.security_level
            }).encode()
            encryptor.authenticate_additional_data(metadata)
            
            ciphertext = encryptor.update(message.encode()) + encryptor.finalize()
            
            # Вычисление HMAC для целостности
            hmac = hashlib.blake2b(
                ciphertext + iv + metadata,
                key=mac_key,
                digest_size=32
            ).digest()
            
            # Подпись сообщения
            signature = self.sign_data(ciphertext + iv + hmac)
            
            return {
                "ciphertext": base64.b64encode(ciphertext).decode(),
                "iv": base64.b64encode(iv).decode(),
                "salt": base64.b64encode(salt).decode(),
                "ephemeral_public_key": self.get_ephemeral_public_key_pem(),
                "hmac": base64.b64encode(hmac).decode(),
                "metadata": base64.b64encode(metadata).decode(),
                "signature": signature,
                "algorithm": "RiMayTik-ECDH-AES256-GCM-BLAKE2b",
                "message_id": f"rimaytik_{uuid.uuid4().hex}",
                "timestamp": time.time()
            }
            
        except Exception as e:
            raise ValueError(f"RiMayTik: Ошибка шифрования: {e}")
    
    def decrypt_message(self, encrypted_data: Dict, sender_public_key_pem: str) -> str:
        """Дешифрование сообщения RiMayTik"""
        try:
            # Загрузка временного публичного ключа отправителя
            sender_ephemeral_key = serialization.load_pem_public_key(
                encrypted_data["ephemeral_public_key"].encode(),
                backend=self.backend
            )
            
            # Вычисление общего секрета
            shared_secret = self.ephemeral_keys['private'].exchange(
                ec.ECDH(),
                sender_ephemeral_key
            )
            
            # Восстановление сессионных ключей
            salt = base64.b64decode(encrypted_data["salt"])
            info = b'rimaytik_message_encryption'
            
            hkdf = HKDF(
                algorithm=hashes.SHA512(),
                length=64,
                salt=salt,
                info=info,
                backend=self.backend
            )
            
            key_material = hkdf.derive(shared_secret)
            encryption_key = key_material[:32]
            mac_key = key_material[32:]
            
            # Декодирование компонентов
            ciphertext = base64.b64decode(encrypted_data["ciphertext"])
            iv = base64.b64decode(encrypted_data["iv"])
            hmac = base64.b64decode(encrypted_data["hmac"])
            metadata = base64.b64decode(encrypted_data["metadata"])
            
            # Проверка HMAC
            expected_hmac = hashlib.blake2b(
                ciphertext + iv + metadata,
                key=mac_key,
                digest_size=32
            ).digest()
            
            if not constant_time.bytes_eq(hmac, expected_hmac):
                raise ValueError("RiMayTik: Неверная проверка целостности")
            
            # Проверка подписи
            if not self.verify_signature(
                ciphertext + iv + hmac,
                encrypted_data["signature"],
                sender_public_key_pem
            ):
                raise ValueError("RiMayTik: Неверная цифровая подпись")
            
            # Дешифрование
            cipher = Cipher(
                algorithms.AES(encryption_key),
                modes.GCM(iv, hmac),
                backend=self.backend
            )
            decryptor = cipher.decryptor()
            decryptor.authenticate_additional_data(metadata)
            
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Обновление ключей (ратач)
            self._ratchet_keys(sender_public_key_pem, shared_secret)
            
            return plaintext.decode('utf-8')
            
        except Exception as e:
            raise ValueError(f"RiMayTik: Ошибка дешифрования: {e}")
    
    def sign_data(self, data: bytes) -> str:
        """Подпись данных с использованием ключа идентификации"""
        if not self.identity_keys:
            self.generate_identity_keypair()
        
        signature = self.identity_keys['private'].sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode()
    
    def verify_signature(self, data: bytes, signature: str, public_key_pem: str) -> bool:
        """Проверка цифровой подписи"""
        try:
            public_key = serialization.load_pem_public_key(
                public_key_pem.encode(),
                backend=self.backend
            )
            
            public_key.verify(
                base64.b64decode(signature),
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except:
            return False
    
    def _ratchet_keys(self, user: str, new_shared_secret: bytes):
        """Обновление ключей по схеме двойного ратача"""
        if user not in self.session_keys:
            self.session_keys[user] = {
                'chain_key_send': new_shared_secret,
                'chain_key_receive': new_shared_secret,
                'message_number': 0
            }
        else:
            # Генерация новых ключей из цепочки
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=64,
                salt=None,
                info=b'rimaytik_ratchet',
                backend=self.backend
            )
            
            new_keys = hkdf.derive(self.session_keys[user]['chain_key_send'])
            self.session_keys[user]['chain_key_send'] = new_keys[:32]
            self.session_keys[user]['chain_key_receive'] = new_keys[32:]
            self.session_keys[user]['message_number'] += 1
    
    def export_keys(self, password: str) -> str:
        """Экспорт ключей с защитой паролем"""
        if not self.identity_keys:
            raise ValueError("RiMayTik: Ключи не сгенерированы")
        
        # Сериализация приватного ключа
        private_key_pem = self.identity_keys['private'].private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(
                password.encode()
            )
        )
        
        keys_data = {
            "private_key": private_key_pem.decode(),
            "public_key": self.get_public_key_pem(),
            "security_level": self.security_level,
            "exported_at": time.time(),
            "system": "RiMayTik Messenger"
        }
        
        return json.dumps(keys_data)
    
    def import_keys(self, encrypted_keys_json: str, password: str):
        """Импорт ключей из защищенного файла"""
        try:
            keys_data = json.loads(encrypted_keys_json)
            
            self.identity_keys = {
                'private': serialization.load_pem_private_key(
                    keys_data["private_key"].encode(),
                    password=password.encode(),
                    backend=self.backend
                ),
                'public': None
            }
            self.identity_keys['public'] = self.identity_keys['private'].public_key()
            
            self.security_level = keys_data.get("security_level", 2)
            self._setup_security_level()
            
            print("RiMayTik: Ключи успешно импортированы")
            
        except Exception as e:
            raise ValueError(f"RiMayTik: Ошибка импорта ключей: {e}")

class RiMayTikKeyManager:
    """Менеджер ключей RiMayTik"""
    
    def __init__(self):
        self.trusted_keys = {}  # user -> public_key
        self.key_verifications = {}  # user -> verification_status
        self.key_expiry = {}  # user -> expiry_timestamp
    
    def add_trusted_key(self, username: str, public_key: str, fingerprint: str = None):
        """Добавление доверенного ключа"""
        self.trusted_keys[username] = {
            "key": public_key,
            "fingerprint": fingerprint or self.calculate_fingerprint(public_key),
            "added_at": time.time(),
            "verified": False
        }
    
    def verify_key_fingerprint(self, username: str, fingerprint: str) -> bool:
        """Проверка отпечатка ключа"""
        if username in self.trusted_keys:
            stored_fingerprint = self.trusted_keys[username]["fingerprint"]
            if fingerprint == stored_fingerprint:
                self.trusted_keys[username]["verified"] = True
                return True
        return False
    
    @staticmethod
    def calculate_fingerprint(public_key_pem: str) -> str:
        """Вычисление отпечатка ключа"""
        key_hash = hashlib.sha256(public_key_pem.encode()).digest()
        return ':'.join(f'{b:02x}' for b in key_hash[:16])
    
    def get_security_status(self, username: str) -> Dict:
        """Получение статуса безопасности для пользователя"""
        if username in self.trusted_keys:
            key_info = self.trusted_keys[username]
            return {
                "has_key": True,
                "verified": key_info["verified"],
                "fingerprint": key_info["fingerprint"],
                "key_age_days": (time.time() - key_info["added_at"]) / 86400,
                "security_level": "high" if key_info["verified"] else "medium"
            }
        return {"has_key": False, "security_level": "low"}

def generate_rimaytik_system_alert(alert_type: str, details: str) -> Dict:
    """Генерация системного оповещения RiMayTik"""
    alerts = {
        "encryption_active": "🔐 Шифрование RiMayTik активно. Сообщения защищены.",
        "new_contact": "👥 Новый контакт. Проверьте отпечаток ключа.",
        "key_verified": "✅ Ключ верифицирован. Безопасное соединение установлено.",
        "security_breach": "⚠️ Возможная угроза безопасности. Проверьте соединение.",
        "forward_secrecy": "🔄 Perfect Forward Secrecy активирован."
    }
    
    return {
        "type": alert_type,
        "message": alerts.get(alert_type, "Системное оповещение RiMayTik"),
        "details": details,
        "timestamp": time.time(),
        "priority": "high" if alert_type in ["security_breach"] else "medium"
    }
