"""
RiMayTik Messenger - Протокол обмена сообщениями
"""

import json
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import time
import uuid

class RiMayTikMessageType(Enum):
    """Типы сообщений в RiMayTik Messenger"""
    # Аутентификация
    RIMAYTIK_REGISTER = "rimaytik_register"
    RIMAYTIK_LOGIN = "rimaytik_login"
    RIMAYTIK_LOGOUT = "rimaytik_logout"
    
    # Обмен ключами
    RIMAYTIK_KEY_EXCHANGE = "rimaytik_key_exchange"
    RIMAYTIK_KEY_VERIFY = "rimaytik_key_verify"
    
    # Сообщения
    RIMAYTIK_DIRECT_MESSAGE = "rimaytik_direct_message"
    RIMAYTIK_GROUP_MESSAGE = "rimaytik_group_message"
    RIMAYTIK_SYSTEM_MESSAGE = "rimaytik_system_message"
    
    # Управление
    RIMAYTIK_ONLINE_USERS = "rimaytik_online_users"
    RIMAYTIK_USER_STATUS = "rimaytik_user_status"
    RIMAYTIK_CONTACT_REQUEST = "rimaytik_contact_request"
    RIMAYTIK_CONTACT_ACCEPT = "rimaytik_contact_accept"
    
    # Файлы
    RIMAYTIK_FILE_TRANSFER_REQUEST = "rimaytik_file_request"
    RIMAYTIK_FILE_TRANSFER_DATA = "rimaytik_file_data"
    
    # Безопасность
    RIMAYTIK_SECURITY_ALERT = "rimaytik_security_alert"
    RIMAYTIK_ENCRYPTION_INIT = "rimaytik_encryption_init"
    
    # Ошибки
    RIMAYTIK_ERROR = "rimaytik_error"
    RIMAYTIK_SUCCESS = "rimaytik_success"

@dataclass
class RiMayTikMessage:
    """Сообщение протокола RiMayTik"""
    type: RiMayTikMessageType
    data: Dict[str, Any]
    sender: Optional[str] = None
    receiver: Optional[str] = None
    message_id: Optional[str] = None
    timestamp: Optional[float] = None
    signature: Optional[str] = None
    
    def __post_init__(self):
        if not self.message_id:
            self.message_id = f"rimaytik_{uuid.uuid4().hex}"
        if not self.timestamp:
            self.timestamp = time.time()
    
    def to_json(self) -> str:
        """Конвертация в JSON"""
        return json.dumps({
            "protocol": "RiMayTik v1.0",
            "message_id": self.message_id,
            "type": self.type.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "timestamp": self.timestamp,
            "data": self.data,
            "signature": self.signature
        }, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str):
        """Создание из JSON"""
        try:
            data = json.loads(json_str)
            
            if data.get("protocol") != "RiMayTik v1.0":
                raise ValueError("Неверная версия протокола RiMayTik")
            
            return cls(
                message_id=data.get("message_id"),
                type=RiMayTikMessageType(data["type"]),
                sender=data.get("sender"),
                receiver=data.get("receiver"),
                timestamp=data.get("timestamp"),
                data=data["data"],
                signature=data.get("signature")
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ValueError(f"Ошибка парсинга сообщения RiMayTik: {e}")

class RiMayTikEncryptionProtocol:
    """Протокол шифрования RiMayTik"""
    
    @staticmethod
    def create_handshake(username: str, public_key: str, security_level: int = 2) -> Dict:
        """Создание рукопожатия RiMayTik"""
        return {
            "system": "RiMayTik Messenger",
            "version": "1.0.0",
            "username": username,
            "public_key": public_key,
            "security_level": security_level,
            "timestamp": time.time(),
            "features": ["e2ee", "forward_secrecy", "message_signing"]
        }
    
    @staticmethod
    def create_key_exchange(ephemeral_public_key: str, encrypted_session_key: str) -> Dict:
        """Создание обмена ключами RiMayTik"""
        return {
            "ephemeral_key": ephemeral_public_key,
            "encrypted_session_key": encrypted_session_key,
            "algorithm": "X25519-AES-256-GCM",
            "timestamp": time.time()
        }
    
    @staticmethod
    def create_security_alert(alert_type: str, description: str, severity: str = "medium") -> Dict:
        """Создание оповещения безопасности RiMayTik"""
        return {
            "alert_id": f"rimaytik_alert_{uuid.uuid4().hex[:8]}",
            "type": alert_type,
            "description": description,
            "severity": severity,
            "timestamp": time.time(),
            "recommendation": "Проверьте безопасность соединения"
        }

class RiMayTikContact:
    """Контакт в RiMayTik Messenger"""
    
    def __init__(self, username: str, display_name: str = None, public_key: str = None):
        self.username = username
        self.display_name = display_name or username
        self.public_key = public_key
        self.status = "offline"
        self.security_level = 2
        self.trusted = False
        self.last_seen = None
        
    def to_dict(self) -> Dict:
        return {
            "username": self.username,
            "display_name": self.display_name,
            "status": self.status,
            "security_level": self.security_level,
            "trusted": self.trusted,
            "last_seen": self.last_seen
        }

class RiMayTikSystemMessage:
    """Системные сообщения RiMayTik"""
    
    WELCOME = "Добро пожаловать в RiMayTik Messenger! Ваши сообщения защищены сквозным шифрованием."
    SECURITY_ACTIVATED = "Защита RiMayTik активирована. Все сообщения шифруются."
    NEW_CONTACT = "Новый контакт добавлен в RiMayTik."
    ENCRYPTION_VERIFIED = "Шифрование RiMayTik проверено и активно."
    SESSION_RENEWED = "Сессия безопасности RiMayTik обновлена."
    
    @staticmethod
    def get_welcome_message(username: str) -> str:
        return f"👋 {username}, добро пожаловать в RiMayTik Messenger!\n\n" \
               "✅ Ваши сообщения защищены сквозным шифрованием\n" \
               "🔒 Только вы и получатель можете читать сообщения\n" \
               "🚀 Начните безопасное общение!"
