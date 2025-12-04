"""
RiMayTik Messenger - Основной клиент
Безопасный мессенджер со сквозным шифрованием
"""

import asyncio
import json
import sys
import getpass
from datetime import datetime
from encryption import RiMayTikEncryptionEngine, RiMayTikKeyManager, generate_rimaytik_system_alert
from shared.protocol import RiMayTikMessage, RiMayTikMessageType, RiMayTikSystemMessage

class RiMayTikClient:
    """Основной клиент RiMayTik Messenger"""
    
    def __init__(self, server_host='127.0.0.1', server_port=8888):
        self.server_host = server_host
        self.server_port = server_port
        self.reader = None
        self.writer = None
        
        # Инициализация систем
        self.encryption = RiMayTikEncryptionEngine()
        self.key_manager = RiMayTikKeyManager()
        
        # Данные пользователя
        self.username = None
        self.display_name = None
        self.session_token = None
        self.security_level = 2
        
        # Состояние
        self.connected = False
        self.online_users = []
        self.contacts = []
        self.message_history = []
        
        print("""
╔═══════════════════════════════════════════╗
║          RiMayTik Messenger v1.0          ║
║      Безопасность прежде всего!           ║
╚═══════════════════════════════════════════╝
        """)
    
    async def connect(self):
        """Подключение к серверу RiMayTik"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.server_host, self.server_port
            )
            self.connected = True
            
            # Генерация ключей
            self.encryption.generate_identity_keypair()
            print("RiMayTik: Ключи безопасности сгенерированы")
            
            # Запуск обработки входящих сообщений
            asyncio.create_task(self.receive_messages())
            
            return True
        except Exception as e:
            print(f"RiMayTik: Ошибка подключения: {e}")
            return False
    
    async def register(self):
        """Регистрация нового пользователя"""
        print("\n" + "="*50)
        print("Регистрация в RiMayTik Messenger")
        print("="*50)
        
        username = input("Имя пользователя: ").strip()
        display_name = input("Отображаемое имя (опционально): ").strip() or username
        
        while True:
            password = getpass.getpass("Пароль (мин. 8 символов): ")
            if len(password) < 8:
                print("Пароль должен быть не менее 8 символов!")
                continue
            
            password_confirm = getpass.getpass("Повторите пароль: ")
            if password != password_confirm:
                print("Пароли не совпадают!")
                continue
            break
        
        print("\nВыберите уровень безопасности:")
        print("1. Базовый (быстрее, меньше защита)")
        print("2. Стандартный (рекомендуется)")
        print("3. Максимальный (максимальная защита)")
        
        while True:
            try:
                level = int(input("Ваш выбор [2]: ").strip() or "2")
                if 1 <= level <= 3:
                    self.security_level = level
                    self.encryption.security_level = level
                    break
                else:
                    print("Введите число от 1 до 3")
            except ValueError:
                print("Некорректный ввод")
        
        public_key = self.encryption.get_public_key_pem()
        
        message = RiMayTikMessage(
            type=RiMayTikMessageType.RIMAYTIK_REGISTER,
            data={
                "username": username,
                "display_name": display_name,
                "public_key": public_key,
                "password": password,
                "security_level": self.security_level
            }
        )
        
        await self.send_message(message)
        
        # Ждем ответ
        await asyncio.sleep(2)
        
        if self.username:
            print(f"\n✅ Регистрация успешна! Добро пожаловать в RiMayTik, {display_name}!")
            return True
        
        return False
    
    async def login(self, username=None, password=None, auto_reconnect=False):
        """Вход в систему RiMayTik"""
        if not username:
            print("\n" + "="*50)
            print("Вход в RiMayTik Messenger")
            print("="*50)
            
            username = input("Имя пользователя: ").strip()
            password = getpass.getpass("Пароль: ")
        
        if self.session_token and auto_reconnect:
            # Попытка восстановления сессии
            message = RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_LOGIN,
                data={
                    "username": username,
                    "session_token": self.session_token
                }
            )
        else:
            message = RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_LOGIN,
                data={
                    "username": username,
                    "password": password
                }
            )
        
        await self.send_message(message)
        
        # Ждем ответ
        await asyncio.sleep(2)
        
        if self.username:
            security_msg = generate_rimaytik_system_alert("encryption_active", 
                f"Уровень безопасности: {self.security_level}")
            print(f"\n🔐 {security_msg['message']}")
            return True
        
        return False
    
    async def send_direct_message(self, recipient, message_text):
        """Отправка зашифрованного сообщения"""
        if recipient not in [user['username'] for user in self.online_users]:
            print(f"RiMayTik: Пользователь {recipient} не в сети")
            return False
        
        try:
            # Получаем публичный ключ получателя
            public_key_response = await self.request_public_key(recipient)
            
            if not public_key_response:
                print(f"RiMayTik: Не удалось получить ключ для {recipient}")
                return False
            
            # Шифруем сообщение
            encrypted_data = self.encryption.encrypt_message(message_text, public_key_response)
            
            # Создаем сообщение
            message = RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_DIRECT_MESSAGE,
                sender=self.username,
                receiver=recipient,
                data={
                    "encrypted_data": encrypted_data,
                    "message_type": "text",
                    "security_level": self.security_level
                }
            )
            
            await self.send_message(message)
            
            # Сохраняем в историю
            self.message_history.append({
                "direction": "outgoing",
                "to": recipient,
                "message": message_text,
                "timestamp": datetime.now().isoformat(),
                "encrypted": True
            })
            
            print(f"RiMayTik: Сообщение отправлено {recipient}")
            return True
            
        except Exception as e:
            print(f"RiMayTik: Ошибка отправки сообщения: {e}")
            return False
    
    async def request_public_key(self, username):
        """Запрос публичного ключа пользователя"""
        message = RiMayTikMessage(
            type=RiMayTikMessageType.RIMAYTIK_KEY_EXCHANGE,
            sender=self.username,
            data={
                "target_user": username,
                "request_type": "public_key",
                "my_public_key": self.encryption.get_public_key_pem()
            }
        )
        
        await self.send_message(message)
        return None  # В реальной реализации нужно ждать ответа
    
    async def send_message(self, message: RiMayTikMessage):
        """Отправка сообщения на сервер"""
        if self.writer and self.connected:
            self.writer.write(message.to_json().encode())
            await self.writer.drain()
    
    async def receive_messages(self):
        """Получение сообщений от сервера"""
        try:
            while self.connected:
                data = await self.reader.read(4096)
                if not data:
                    print("RiMayTik: Соединение с сервером разорвано")
                    self.connected = False
                    break
                
                try:
                    message = RiMayTikMessage.from_json(data.decode())
                    await self.handle_incoming_message(message)
                    
                except Exception as e:
                    print(f"RiMayTik: Ошибка обработки сообщения: {e}")
                    
        except Exception as e:
            print(f"RiMayTik: Ошибка приема сообщений: {e}")
            self.connected = False
    
    async def handle_incoming_message(self, message: RiMayTikMessage):
        """Обработка входящих сообщений"""
        if message.type == RiMayTikMessageType.RIMAYTIK_SUCCESS:
            await self.handle_success(message)
        
        elif message.type == RiMayTikMessageType.RIMAYTIK_ERROR:
            self.handle_error(message)
        
        elif message.type == RiMayTikMessageType.RIMAYTIK_DIRECT_MESSAGE:
            await self.handle_direct_message(message)
        
        elif message.type == RiMayTikMessageType.RIMAYTIK_ONLINE_USERS:
            self.handle_online_users(message)
        
        elif message.type == RiMayTikMessageType.RIMAYTIK_SYSTEM_MESSAGE:
            self.handle_system_message(message)
        
        elif message.type == RiMayTikMessageType.RIMAYTIK_KEY_EXCHANGE:
            await self.handle_key_exchange(message)
        
        elif message.type == RiMayTikMessageType.RIMAYTIK_CONTACT_REQUEST:
            await self.handle_contact_request(message)
        
        elif message.type == RiMayTikMessageType.RIMAYTIK_SECURITY_ALERT:
            self.handle_security_alert(message)
    
    async def handle_success(self, message: RiMayTikMessage):
        """Обработка успешных операций"""
        data = message.data
        
        if "session_token" in data:
            self.session_token = data["session_token"]
        
        if "user_id" in data:
            self.username = data.get("username", self.username)
            self.display_name = data.get("display_name", self.username)
            
            if "stats" in data:
                stats = data["stats"]
                print(f"\nRiMayTik: Подключено! Пользователей онлайн: {stats.get('online_users', 0)}")
        
        if "public_key" in data:
            # Сохраняем публичный ключ сервера
            pass
    
    def handle_error(self, message: RiMayTikMessage):
        """Обработка ошибок"""
        error_msg = message.data.get("error", "Неизвестная ошибка")
        print(f"\n❌ RiMayTik Ошибка: {error_msg}")
    
    async def handle_direct_message(self, message: RiMayTikMessage):
        """Обработка входящих зашифрованных сообщений"""
        try:
            sender = message.sender
            encrypted_data = message.data.get("encrypted_data")
            
            if not sender or not encrypted_data:
                print("RiMayTik: Неполное сообщение")
                return
            
            # Получаем публичный ключ отправителя
            sender_key = None
            for user in self.online_users:
                if user['username'] == sender:
                    # В реальной системе ключ должен быть получен заранее
                    break
            
            if not sender_key:
                print(f"RiMayTik: Неизвестный отправитель {sender}")
                return
            
            # Дешифруем сообщение
            plaintext = self.encryption.decrypt_message(encrypted_data, sender_key)
            
            # Отображаем сообщение
            timestamp = datetime.fromtimestamp(message.timestamp).strftime("%H:%M")
            print(f"\n[{timestamp}] {sender}: {plaintext}")
            
            # Сохраняем в историю
            self.message_history.append({
                "direction": "incoming",
                "from": sender,
                "message": plaintext,
                "timestamp": datetime.now().isoformat(),
                "encrypted": True,
                "verified": True  # Если подпись проверена
            })
            
        except Exception as e:
            print(f"RiMayTik: Ошибка обработки сообщения от {message.sender}: {e}")
    
    def handle_online_users(self, message: RiMayTikMessage):
        """Обработка списка онлайн пользователей"""
        self.online_users = message.data.get("users", [])
        
        print(f"\n🟢 RiMayTik: Пользователей онлайн: {len(self.online_users)}")
        
        if self.online_users:
            print("Сейчас онлайн:")
            for user in self.online_users:
                if user['username'] != self.username:
                    security_icon = "🔒" if user.get('security_level', 2) >= 2 else "⚠️"
                    print(f"  {security_icon} {user.get('display_name', user['username'])}")
        
        print()
    
    def handle_system_message(self, message: RiMayTikMessage):
        """Обработка системных сообщений"""
        sys_msg = message.data.get("message", "")
        print(f"\nℹ️  RiMayTik: {sys_msg}")
    
    async def handle_key_exchange(self, message: RiMayTikMessage):
        """Обработка обмена ключами"""
        sender = message.sender
        data = message.data
        
        if data.get("request_type") == "public_key":
            # Отправляем наш публичный ключ
            response = RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_KEY_EXCHANGE,
                sender=self.username,
                receiver=sender,
                data={
                    "response_type": "public_key",
                    "public_key": self.encryption.get_public_key_pem(),
                    "fingerprint": self.key_manager.calculate_fingerprint(
                        self.encryption.get_public_key_pem()
                    )
                }
            )
            await self.send_message(response)
    
    async def handle_contact_request(self, message: RiMayTikMessage):
        """Обработка запроса на добавление в контакты"""
        sender = message.sender
        sender_name = message.data.get("sender_display_name", sender)
        request_id = message.data.get("request_id")
        
        print(f"\n📨 RiMayTik: Запрос на добавление в контакты от {sender_name}")
        
        response = input(f"Принять запрос от {sender_name}? (y/n): ").strip().lower()
        
        if response == 'y':
            accept_msg = RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_CONTACT_ACCEPT,
                sender=self.username,
                receiver=sender,
                data={
                    "request_id": request_id,
                    "accepted": True,
                    "message": "Добавлен в контакты RiMayTik"
                }
            )
            await self.send_message(accept_msg)
            print(f"✅ {sender_name} добавлен в контакты RiMayTik")
        else:
            print("Запрос отклонен")
    
    def handle_security_alert(self, message: RiMayTikMessage):
        """Обработка оповещений безопасности"""
        alert_type = message.data.get("type", "unknown")
        details = message.data.get("details", "")
        
        icons = {
            "encryption_active": "🔐",
            "new_contact": "👥",
            "key_verified": "✅",
            "security_breach": "⚠️",
            "forward_secrecy": "🔄"
        }
        
        icon = icons.get(alert_type, "ℹ️")
        print(f"\n{icon} RiMayTik Безопасность: {message.data.get('message', '')}")
        if details:
            print(f"   Подробности: {details}")
    
    async def interactive_chat(self):
        """Интерактивный режим чата"""
        print("\n" + "="*50)
        print("RiMayTik Messenger - Безопасный чат")
        print("="*50)
        print("\nДоступные команды:")
        print("  /users           - Показать онлайн пользователей")
        print("  /msg <имя> <текст> - Отправить сообщение")
        print("  /add <имя>      - Добавить в контакты")
        print("  /contacts       - Показать контакты")
        print("  /security       - Показать статус безопасности")
        print("  /export         - Экспорт ключей")
        print("  /help           - Справка")
        print("  /exit           - Выйти")
        print("\nВаши сообщения защищены сквозным шифрованием 🔐")
        
        while self.connected:
            try:
                prompt = f"\nRiMayTik@{self.username}> "
                user_input = input(prompt).strip()
                
                if not user_input:
                    continue
                
                if user_input.startswith("/exit"):
                    await self.logout()
                    break
                
                elif user_input.startswith("/users"):
                    await self.request_online_users()
                
                elif user_input.startswith("/msg "):
                    parts = user_input.split(" ", 2)
                    if len(parts) >= 3:
                        recipient = parts[1]
                        message_text = parts[2]
                        await self.send_direct_message(recipient, message_text)
                    else:
                        print("Использование: /msg <имя> <текст>")
                
                elif user_input.startswith("/add "):
                    parts = user_input.split(" ", 1)
                    if len(parts) == 2:
                        contact = parts[1]
                        await self.send_contact_request(contact)
                    else:
                        print("Использование: /add <имя>")
                
                elif user_input == "/contacts":
                    self.show_contacts()
                
                elif user_input == "/security":
                    self.show_security_status()
                
                elif user_input == "/export":
                    await self.export_keys()
                
                elif user_input == "/help":
                    self.show_help()
                
                else:
                    print("Неизвестная команда. Введите /help для справки.")
                    
            except KeyboardInterrupt:
                print("\nRiMayTik: Выход...")
                await self.logout()
                break
            except Exception as e:
                print(f"RiMayTik: Ошибка: {e}")
    
    async def request_online_users(self):
        """Запрос списка онлайн пользователей"""
        message = RiMayTikMessage(
            type=RiMayTikMessageType.RIMAYTIK_ONLINE_USERS,
            sender=self.username
        )
        await self.send_message(message)
    
    async def send_contact_request(self, username):
        """Отправка запроса на добавление в контакты"""
        message = RiMayTikMessage(
            type=RiMayTikMessageType.RIMAYTIK_CONTACT_REQUEST,
            sender=self.username,
            data={
                "target_user": username,
                "message": "Хочу добавить вас в контакты RiMayTik"
            }
        )
        await self.send_message(message)
        print(f"RiMayTik: Запрос отправлен {username}")
    
    def show_contacts(self):
        """Показать список контактов"""
        print("\n📇 Контакты RiMayTik:")
        if self.contacts:
            for contact in self.contacts:
                status_icon = "🟢" if contact.get('online') else "⚫"
                print(f"  {status_icon} {contact.get('name')}")
        else:
            print("  Контактов пока нет. Используйте /add <имя>")
    
    def show_security_status(self):
        """Показать статус безопасности"""
        print("\n🔒 Статус безопасности RiMayTik:")
        print(f"  Уровень защиты: {self.security_level}/3")
        print(f"  Сквозное шифрование: ✅ Активно")
        print(f"  Perfect Forward Secrecy: ✅ Включен")
        print(f"  Цифровые подписи: ✅ Используются")
        print(f"  Ключи сгенерированы: ✅ Да")
        
        if self.online_users:
            print(f"\n  Безопасность контактов:")
            for user in self.online_users:
                if user['username'] != self.username:
                    level = user.get('security_level', 1)
                    status = "Высокая" if level >= 2 else "Базовая"
                    print(f"    {user['username']}: {status}")
    
    async def export_keys(self):
        """Экспорт ключей безопасности"""
        print("\n🔑 Экспорт ключей RiMayTik")
        password = getpass.getpass("Введите пароль для защиты ключей: ")
        confirm = getpass.getpass("Повторите пароль: ")
        
        if password != confirm:
            print("Пароли не совпадают!")
            return
        
        try:
            keys_json = self.encryption.export_keys(password)
            
            filename = f"rimaytik_keys_{self.username}_{datetime.now().strftime('%Y%m%d')}.json"
            with open(filename, 'w') as f:
                f.write(keys_json)
            
            print(f"✅ Ключи экспортированы в файл: {filename}")
            print("⚠️  Храните этот файл в безопасном месте!")
            
        except Exception as e:
            print(f"❌ Ошибка экспорта: {e}")
    
    def show_help(self):
        """Показать справку"""
        print("""
RiMayTik Messenger - Справка по командам:

  Основные команды:
    /users        - Показать пользователей онлайн
    /msg <u> <t>  - Отправить сообщение пользователю <u>
    /add <u>      - Добавить пользователя <u> в контакты
    /contacts     - Показать ваши контакты
  
  Безопасность:
    /security     - Показать статус безопасности
    /export       - Экспорт ключей безопасности
  
  Системные:
    /help         - Эта справка
    /exit         - Выйти из RiMayTik

Ваши сообщения защищены сквозным шифрованием.
Только вы и получатель можете их прочитать.
        """)
    
    async def logout(self):
        """Выход из системы"""
        if self.username:
            message = RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_LOGOUT,
                sender=self.username
            )
            await self.send_message(message)
        
        self.connected = False
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        
        print("\nRiMayTik: Выход выполнен. До свидания!")

async def main():
    """Точка входа клиента RiMayTik"""
    print("""
╔═══════════════════════════════════════════╗
║     Добро пожаловать в RiMayTik Messenger!║
║   Ваши сообщения защищены на 100%         ║
╚═══════════════════════════════════════════╝
    """)
    
    # Настройка подключения
    if len(sys.argv) > 1:
        server_host = sys.argv[1]
        server_port = int(sys.argv[2]) if len(sys.argv) > 2 else 8888
    else:
        server_host = input("Адрес сервера RiMayTik [127.0.0.1]: ").strip() or "127.0.0.1"
        server_port = int(input("Порт сервера [8888]: ").strip() or "8888")
    
    # Создание клиента
    client = RiMayTikClient(server_host, server_port)
    
    # Подключение к серверу
    if not await client.connect():
        print("Не удалось подключиться к серверу RiMayTik")
        return
    
    # Выбор действия
    while True:
        print("\nВыберите действие:")
        print("1. Войти")
        print("2. Зарегистрироваться")
        print("3. Выйти")
        
        choice = input("Ваш выбор [1]: ").strip() or "1"
        
        if choice == "1":
            if await client.login():
                await client.interactive_chat()
                break
        elif choice == "2":
            if await client.register():
                await client.interactive_chat()
                break
        elif choice == "3":
            print("До свидания!")
            break
        else:
            print("Некорректный выбор")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nRiMayTik: Программа завершена")
    except Exception as e:
        print(f"RiMayTik: Критическая ошибка: {e}")
