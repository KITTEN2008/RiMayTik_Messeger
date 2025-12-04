"""
RiMayTik Messenger - Основной сервер
Сервер с минимальной метаинформацией и E2E шифрованием
"""

import asyncio
import json
import hashlib
import ssl
from datetime import datetime
from database import RiMayTikDatabase
from shared.protocol import RiMayTikMessage, RiMayTikMessageType

class RiMayTikServer:
    """Основной сервер RiMayTik Messenger"""
    
    def __init__(self, host='0.0.0.0', port=8888, ssl_cert=None, ssl_key=None):
        self.host = host
        self.port = port
        self.ssl_context = None
        
        if ssl_cert and ssl_key:
            self.ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            self.ssl_context.load_cert_chain(certfile=ssl_cert, keyfile=ssl_key)
            print("RiMayTik: SSL/TLS активирован")
        
        self.db = RiMayTikDatabase()
        self.clients = {}  # username -> (writer, public_key, session_token)
        self.online_users = set()
        self.message_queue = asyncio.Queue()
        
        print(f"""
╔═══════════════════════════════════════════╗
║      RiMayTik Messenger Server v1.0       ║
║          Безопасный обмен сообщениями     ║
╚═══════════════════════════════════════════╝
        """)
    
    async def handle_client(self, reader, writer):
        """Обработка подключения клиента RiMayTik"""
        addr = writer.get_extra_info('peername')
        client_ip = addr[0]
        
        print(f"RiMayTik: Новое подключение от {client_ip}")
        
        current_user = None
        session_token = None
        
        try:
            while True:
                # Чтение данных с таймаутом
                try:
                    data = await asyncio.wait_for(reader.read(8192), timeout=30)
                except asyncio.TimeoutError:
                    print(f"RiMayTik: Таймаут от {client_ip}")
                    break
                
                if not data:
                    break
                
                try:
                    message = RiMayTikMessage.from_json(data.decode())
                    
                    # Обработка в зависимости от типа сообщения
                    response = await self.process_rimaytik_message(
                        message, writer, client_ip
                    )
                    
                    if response:
                        writer.write(response.encode())
                        await writer.drain()
                        
                except (json.JSONDecodeError, ValueError) as e:
                    error_msg = RiMayTikMessage(
                        type=RiMayTikMessageType.RIMAYTIK_ERROR,
                        data={"error": f"Некорректное сообщение RiMayTik: {str(e)}"}
                    )
                    writer.write(error_msg.to_json().encode())
                    await writer.drain()
                    
        except ConnectionError:
            print(f"RiMayTik: Клиент отключился: {current_user or client_ip}")
        except Exception as e:
            print(f"RiMayTik: Ошибка обработки клиента: {e}")
        finally:
            # Очистка при отключении
            if current_user:
                await self.handle_user_logout(current_user)
            
            writer.close()
            await writer.wait_closed()
            print(f"RiMayTik: Соединение закрыто: {current_user or client_ip}")
    
    async def process_rimaytik_message(self, message: RiMayTikMessage, writer, client_ip: str):
        """Обработка входящих сообщений RiMayTik"""
        if message.type == RiMayTikMessageType.RIMAYTIK_REGISTER:
            return await self.handle_rimaytik_register(message.data, writer, client_ip)
        
        elif message.type == RiMayTikMessageType.RIMAYTIK_LOGIN:
            return await self.handle_rimaytik_login(message.data, writer, client_ip)
        
        elif message.type == RiMayTikMessageType.RIMAYTIK_KEY_EXCHANGE:
            return await self.handle_rimaytik_key_exchange(message)
        
        elif message.type == RiMayTikMessageType.RIMAYTIK_DIRECT_MESSAGE:
            return await self.handle_rimaytik_direct_message(message)
        
        elif message.type == RiMayTikMessageType.RIMAYTIK_ONLINE_USERS:
            return await self.handle_rimaytik_online_users(message.sender)
        
        elif message.type == RiMayTikMessageType.RIMAYTIK_CONTACT_REQUEST:
            return await self.handle_rimaytik_contact_request(message)
        
        elif message.type == RiMayTikMessageType.RIMAYTIK_LOGOUT:
            return await self.handle_rimaytik_logout(message.sender)
        
        return None
    
    async def handle_rimaytik_register(self, data, writer, client_ip: str):
        """Обработка регистрации в RiMayTik"""
        username = data.get("username")
        display_name = data.get("display_name")
        public_key = data.get("public_key")
        password = data.get("password")
        security_level = data.get("security_level", 2)
        
        if not all([username, public_key, password]):
            return RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_ERROR,
                data={"error": "Недостаточно данных для регистрации RiMayTik"}
            ).to_json()
        
        # Проверка длины пароля
        if len(password) < 8:
            return RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_ERROR,
                data={"error": "Пароль должен быть не менее 8 символов"}
            ).to_json()
        
        user_id = self.db.register_rimaytik_user(
            username, display_name, public_key, password
        )
        
        if user_id:
            # Создание сессии
            session_token = hashlib.sha256(
                f"{username}{public_key}{datetime.now().timestamp()}".encode()
            ).hexdigest()[:32]
            
            self.db.create_rimaytik_session(
                user_id, session_token, f"RiMayTik Client {client_ip}", 
                client_ip, expires_hours=24
            )
            
            self.clients[username] = (writer, public_key, session_token)
            self.online_users.add(username)
            
            # Отправляем приветственное сообщение
            welcome_msg = RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_SYSTEM_MESSAGE,
                data={
                    "message": f"Добро пожаловать в RiMayTik Messenger, {display_name or username}!",
                    "system_info": {
                        "users_online": len(self.online_users),
                        "security_level": security_level,
                        "session_token": session_token
                    }
                }
            )
            
            # Рассылаем обновление списка онлайн
            await self.broadcast_rimaytik_online_users()
            
            # Получаем статистику
            stats = self.db.get_rimaytik_system_stats()
            
            return RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_SUCCESS,
                data={
                    "success": True,
                    "user_id": user_id,
                    "session_token": session_token,
                    "message": "Регистрация в RiMayTik успешна",
                    "stats": stats,
                    "online_users": len(self.online_users)
                }
            ).to_json()
        else:
            return RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_ERROR,
                data={"error": "Имя пользователя уже занято в RiMayTik"}
            ).to_json()
    
    async def handle_rimaytik_login(self, data, writer, client_ip: str):
        """Обработка входа в RiMayTik"""
        username = data.get("username")
        password = data.get("password")
        session_token = data.get("session_token")
        
        if session_token:
            # Попытка восстановления сессии
            user_id = self.db.validate_rimaytik_session(session_token)
            if user_id:
                # Получаем информацию о пользователе
                self.cursor.execute(
                    "SELECT username, public_key FROM rimaytik_users WHERE id = ?",
                    (user_id,)
                )
                user_data = self.cursor.fetchone()
                
                if user_data:
                    username = user_data[0]
                    public_key = user_data[1]
                    
                    self.clients[username] = (writer, public_key, session_token)
                    self.online_users.add(username)
                    
                    await self.broadcast_rimaytik_online_users()
                    
                    return RiMayTikMessage(
                        type=RiMayTikMessageType.RIMAYTIK_SUCCESS,
                        data={
                            "success": True,
                            "message": "Сессия RiMayTik восстановлена",
                            "username": username,
                            "session_token": session_token
                        }
                    ).to_json()
        
        # Обычная аутентификация
        user_id = self.db.authenticate_rimaytik_user(username, password)
        
        if user_id:
            public_key = self.db.get_rimaytik_public_key(username)
            
            # Создание новой сессии
            session_token = hashlib.sha256(
                f"{username}{public_key}{datetime.now().timestamp()}".encode()
            ).hexdigest()[:32]
            
            self.db.create_rimaytik_session(
                user_id, session_token, f"RiMayTik Client {client_ip}", 
                client_ip, expires_hours=24
            )
            
            self.clients[username] = (writer, public_key, session_token)
            self.online_users.add(username)
            self.db.update_rimaytik_last_seen(user_id)
            
            await self.broadcast_rimaytik_online_users()
            
            return RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_SUCCESS,
                data={
                    "success": True,
                    "user_id": user_id,
                    "session_token": session_token,
                    "public_key": public_key,
                    "message": "Вход в RiMayTik успешен"
                }
            ).to_json()
        else:
            return RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_ERROR,
                data={"error": "Неверные учетные данные RiMayTik"}
            ).to_json()
    
    async def handle_rimaytik_key_exchange(self, message: RiMayTikMessage):
        """Обработка обмена ключами RiMayTik"""
        target_user = message.data.get("target_user")
        
        if target_user in self.clients:
            target_writer, target_public_key, _ = self.clients[target_user]
            
            # Пересылаем запрос обмена ключами
            forward_msg = RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_KEY_EXCHANGE,
                sender=message.sender,
                data=message.data
            )
            
            target_writer.write(forward_msg.to_json().encode())
            await target_writer.drain()
            
            return RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_SUCCESS,
                data={"status": "key_exchange_forwarded"}
            ).to_json()
        
        return RiMayTikMessage(
            type=RiMayTikMessageType.RIMAYTIK_ERROR,
            data={"error": "Пользователь не онлайн в RiMayTik"}
        ).to_json()
    
    async def handle_rimaytik_direct_message(self, message: RiMayTikMessage):
        """Обработка прямых сообщений RiMayTik"""
        recipient = message.receiver
        message_id = message.message_id
        encrypted_data = message.data.get("encrypted_data")
        
        if not all([recipient, message_id, encrypted_data]):
            return RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_ERROR,
                data={"error": "Неполные данные сообщения RiMayTik"}
            ).to_json()
        
        if recipient in self.clients:
            recipient_writer, _, _ = self.clients[recipient]
            
            # Логируем метаданные (без содержимого!)
            message_hash = hashlib.sha256(
                json.dumps(encrypted_data).encode()
            ).hexdigest()
            
            self.db.log_rimaytik_message(
                message_id, message.sender, recipient, message_hash
            )
            
            # Пересылаем зашифрованное сообщение
            forward_msg = RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_DIRECT_MESSAGE,
                sender=message.sender,
                receiver=recipient,
                message_id=message_id,
                data={
                    "encrypted_data": encrypted_data,
                    "timestamp": message.timestamp,
                    "message_id": message_id
                }
            )
            
            recipient_writer.write(forward_msg.to_json().encode())
            await recipient_writer.drain()
            
            # Подтверждение отправителю
            return RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_SUCCESS,
                data={
                    "status": "delivered",
                    "message_id": message_id,
                    "timestamp": datetime.now().timestamp()
                }
            ).to_json()
        
        return RiMayTikMessage(
            type=RiMayTikMessageType.RIMAYTIK_ERROR,
            data={
                "error": "Получатель не в сети",
                "message_id": message_id,
                "suggestion": "Сообщение будет доставлено при следующем входе"
            }
        ).to_json()
    
    async def handle_rimaytik_online_users(self, requester: str):
        """Отправка списка онлайн пользователей"""
        online_users = self.db.get_rimaytik_online_users()
        
        return RiMayTikMessage(
            type=RiMayTikMessageType.RIMAYTIK_ONLINE_USERS,
            data={
                "users": online_users,
                "total_online": len(online_users),
                "server_time": datetime.now().isoformat()
            }
        ).to_json()
    
    async def handle_rimaytik_contact_request(self, message: RiMayTikMessage):
        """Обработка запроса на добавление контакта"""
        target_user = message.data.get("target_user")
        
        if target_user in self.clients:
            target_writer, _, _ = self.clients[target_user]
            
            forward_msg = RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_CONTACT_REQUEST,
                sender=message.sender,
                data={
                    "request_id": f"rimaytik_req_{hashlib.md5(message.sender.encode()).hexdigest()[:8]}",
                    "sender_display_name": self.db.get_rimaytik_display_name(message.sender),
                    "message": message.data.get("message", "Хочу добавить вас в контакты RiMayTik"),
                    "timestamp": datetime.now().timestamp()
                }
            )
            
            target_writer.write(forward_msg.to_json().encode())
            await target_writer.drain()
            
            return RiMayTikMessage(
                type=RiMayTikMessageType.RIMAYTIK_SUCCESS,
                data={"status": "contact_request_sent"}
            ).to_json()
        
        return RiMayTikMessage(
            type=RiMayTikMessageType.RIMAYTIK_ERROR,
            data={"error": "Пользователь не найден в RiMayTik"}
        ).to_json()
    
    async def handle_rimaytik_logout(self, username: str):
        """Обработка выхода из системы"""
        await self.handle_user_logout(username)
        
        return RiMayTikMessage(
            type=RiMayTikMessageType.RIMAYTIK_SUCCESS,
            data={"message": "Вы вышли из RiMayTik Messenger"}
        ).to_json()
    
    async def handle_user_logout(self, username: str):
        """Обработка отключения пользователя"""
        if username in self.clients:
            del self.clients[username]
            self.online_users.discard(username)
            
            # Обновляем статус в базе
            self.cursor.execute("""
                UPDATE rimaytik_users 
                SET status = 'offline', last_seen = CURRENT_TIMESTAMP 
                WHERE username = ?
            """, (username,))
            self.conn.commit()
            
            await self.broadcast_rimaytik_online_users()
            print(f"RiMayTik: Пользователь вышел: {username}")
    
    async def broadcast_rimaytik_online_users(self):
        """Рассылка обновленного списка онлайн пользователей"""
        online_users = self.db.get_rimaytik_online_users()
        
        update_msg = RiMayTikMessage(
            type=RiMayTikMessageType.RIMAYTIK_ONLINE_USERS,
            data={
                "users": online_users,
                "total_online": len(online_users),
                "update_time": datetime.now().isoformat()
            }
        ).to_json()
        
        for username, (writer, _, _) in self.clients.items():
            try:
                writer.write(update_msg.encode())
                await writer.drain()
            except:
                continue
    
    async def start(self):
        """Запуск сервера RiMayTik"""
        if self.ssl_context:
            server = await asyncio.start_server(
                self.handle_client,
                self.host,
                self.port,
                ssl=self.ssl_context
            )
            print(f"RiMayTik: Защищенный сервер запущен на {self.host}:{self.port} (SSL/TLS)")
        else:
            server = await asyncio.start_server(
                self.handle_client,
                self.host,
                self.port
            )
            print(f"RiMayTik: Сервер запущен на {self.host}:{self.port}")
        
        # Запуск фоновых задач
        asyncio.create_task(self.monitor_system_stats())
        
        # Отображение баннера
        stats = self.db.get_rimaytik_system_stats()
        print(f"""
╔═══════════════════════════════════════════╗
║         Статистика RiMayTik:             ║
║  👥 Всего пользователей: {stats['total_users']:4}          ║
║  🟢 Онлайн сейчас: {stats['online_users']:4}             ║
║  💬 Всего сообщений: {stats['total_messages']:4}         ║
║  🔑 Активных сессий: {stats['active_sessions']:4}        ║
╚═══════════════════════════════════════════╝
        """)
        
        print("RiMayTik: Сервер готов к работе. Ожидание подключений...")
        
        async with server:
            await server.serve_forever()
    
    async def monitor_system_stats(self):
        """Мониторинг статистики системы"""
        while True:
            await asyncio.sleep(60)  # Каждую минуту
            stats = self.db.get_rimaytik_system_stats()
            
            if stats['online_users'] > 0:
                print(f"RiMayTik: Статистика - Онлайн: {stats['online_users']}, "
                      f"Сообщений: {stats['total_messages']}")

def main():
    """Точка входа сервера RiMayTik"""
    import argparse
    
    parser = argparse.ArgumentParser(description='RiMayTik Messenger Server')
    parser.add_argument('--host', default='0.0.0.0', help='Хост сервера')
    parser.add_argument('--port', type=int, default=8888, help='Порт сервера')
    parser.add_argument('--ssl-cert', help='SSL сертификат')
    parser.add_argument('--ssl-key', help='SSL приватный ключ')
    
    args = parser.parse_args()
    
    server = RiMayTikServer(
        host=args.host,
        port=args.port,
        ssl_cert=args.ssl_cert,
        ssl_key=args.ssl_key
    )
    
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\nRiMayTik: Сервер остановлен пользователем")
    except Exception as e:
        print(f"RiMayTik: Ошибка запуска сервера: {e}")

if __name__ == "__main__":
    main()
