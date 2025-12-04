"""
RiMayTik Messenger - Графический интерфейс пользователя
Мощный и безопасный GUI на Tkinter
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, font
import asyncio
import threading
from datetime import datetime
import json
import base64
from PIL import Image, ImageTk
import os
import sys

# Добавляем путь для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from client.main import RiMayTikClient
from client.encryption import RiMayTikEncryptionEngine
from shared.protocol import RiMayTikMessage, RiMayTikMessageType

class RiMayTikUI:
    """Главный класс графического интерфейса RiMayTik"""
    
    def __init__(self):
        self.client = None
        self.async_loop = None
        self.connected = False
        
        # Настройка основного окна
        self.root = tk.Tk()
        self.root.title("RiMayTik Messenger - Безопасный чат")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        
        # Настройка иконки (если есть)
        try:
            self.root.iconbitmap('rimaytik_icon.ico')
        except:
            pass
        
        # Шрифты
        self.fonts = {
            'title': ('Segoe UI', 16, 'bold'),
            'heading': ('Segoe UI', 12, 'bold'),
            'normal': ('Segoe UI', 10),
            'small': ('Segoe UI', 9),
            'monospace': ('Consolas', 10)
        }
        
        # Цветовая схема
        self.colors = {
            'primary': '#2C3E50',
            'secondary': '#3498DB',
            'accent': '#2ECC71',
            'danger': '#E74C3C',
            'warning': '#F39C12',
            'light': '#ECF0F1',
            'dark': '#2C3E50',
            'background': '#FFFFFF',
            'chat_bg': '#F8F9FA',
            'user_message': '#DCF8C6',
            'contact_message': '#FFFFFF',
            'online': '#2ECC71',
            'offline': '#95A5A6',
            'typing': '#F39C12'
        }
        
        # Стили для ttk
        self.setup_styles()
        
        # Данные интерфейса
        self.current_chat = None
        self.messages = {}
        self.contacts = []
        self.online_users = []
        self.unread_counts = {}
        
        # Запуск интерфейса
        self.setup_ui()
        self.show_login_screen()
        
    def setup_styles(self):
        """Настройка стилей ttk"""
        style = ttk.Style()
        
        # Настраиваем стили для разных элементов
        style.configure('Rimaytik.TFrame', background=self.colors['background'])
        style.configure('Rimaytik.TLabel', background=self.colors['background'])
        style.configure('Rimaytik.TButton', font=self.fonts['normal'])
        
        # Стиль для вкладок
        style.configure('Rimaytik.TNotebook', background=self.colors['primary'])
        style.configure('Rimaytik.TNotebook.Tab', 
                       background=self.colors['light'],
                       foreground=self.colors['dark'],
                       padding=[10, 5])
        
    def setup_ui(self):
        """Настройка основного интерфейса"""
        # Главный контейнер
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)
        
        # Панель статуса
        self.status_bar = ttk.Frame(self.main_container, height=30, style='Rimaytik.TFrame')
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(
            self.status_bar, 
            text="RiMayTik Messenger - Не подключено",
            style='Rimaytik.TLabel'
        )
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        self.security_status = ttk.Label(
            self.status_bar,
            text="🔒 Безопасность: Неактивна",
            style='Rimaytik.TLabel'
        )
        self.security_status.pack(side=tk.RIGHT, padx=10)
        
        # Основная рабочая область
        self.workspace = ttk.Frame(self.main_container, style='Rimaytik.TFrame')
        self.workspace.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Создаем фреймы для разных экранов
        self.login_frame = None
        self.register_frame = None
        self.main_chat_frame = None
        
    def show_login_screen(self):
        """Показать экран входа"""
        self.clear_workspace()
        
        self.login_frame = ttk.Frame(self.workspace, style='Rimaytik.TFrame')
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        title_frame = ttk.Frame(self.login_frame, style='Rimaytik.TFrame')
        title_frame.pack(pady=50)
        
        logo_label = ttk.Label(
            title_frame,
            text="🔐 RiMayTik Messenger",
            font=self.fonts['title'],
            foreground=self.colors['primary'],
            style='Rimaytik.TLabel'
        )
        logo_label.pack()
        
        subtitle_label = ttk.Label(
            title_frame,
            text="Безопасный обмен сообщениями со сквозным шифрованием",
            font=self.fonts['small'],
            foreground=self.colors['secondary'],
            style='Rimaytik.TLabel'
        )
        subtitle_label.pack(pady=5)
        
        # Форма входа
        form_frame = ttk.Frame(self.login_frame, style='Rimaytik.TFrame')
        form_frame.pack(pady=30)
        
        # Поле для сервера
        ttk.Label(
            form_frame,
            text="Сервер:",
            font=self.fonts['normal'],
            style='Rimaytik.TLabel'
        ).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.server_entry = ttk.Entry(form_frame, width=30, font=self.fonts['normal'])
        self.server_entry.grid(row=0, column=1, pady=5, padx=10)
        self.server_entry.insert(0, "127.0.0.1:8888")
        
        # Поле для имени пользователя
        ttk.Label(
            form_frame,
            text="Имя пользователя:",
            font=self.fonts['normal'],
            style='Rimaytik.TLabel'
        ).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.username_entry = ttk.Entry(form_frame, width=30, font=self.fonts['normal'])
        self.username_entry.grid(row=1, column=1, pady=5, padx=10)
        
        # Поле для пароля
        ttk.Label(
            form_frame,
            text="Пароль:",
            font=self.fonts['normal'],
            style='Rimaytik.TLabel'
        ).grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.password_entry = ttk.Entry(form_frame, width=30, show="•", font=self.fonts['normal'])
        self.password_entry.grid(row=2, column=1, pady=5, padx=10)
        
        # Кнопки
        button_frame = ttk.Frame(self.login_frame, style='Rimaytik.TFrame')
        button_frame.pack(pady=20)
        
        login_button = ttk.Button(
            button_frame,
            text="Войти",
            command=self.on_login,
            width=15
        )
        login_button.pack(side=tk.LEFT, padx=5)
        
        register_button = ttk.Button(
            button_frame,
            text="Регистрация",
            command=self.show_register_screen,
            width=15
        )
        register_button.pack(side=tk.LEFT, padx=5)
        
        exit_button = ttk.Button(
            button_frame,
            text="Выход",
            command=self.root.quit,
            width=15
        )
        exit_button.pack(side=tk.LEFT, padx=5)
        
        # Информация о безопасности
        security_info = ttk.Label(
            self.login_frame,
            text="🔐 Все сообщения защищены сквозным шифрованием\n"
                 "🔑 Ваши ключи хранятся только на вашем устройстве\n"
                 "🚀 Быстрая и безопасная передача сообщений",
            font=self.fonts['small'],
            foreground=self.colors['dark'],
            justify=tk.CENTER,
            style='Rimaytik.TLabel'
        )
        security_info.pack(pady=30)
        
        # Связываем Enter с входом
        self.password_entry.bind('<Return>', lambda e: self.on_login())
        
    def show_register_screen(self):
        """Показать экран регистрации"""
        self.clear_workspace()
        
        self.register_frame = ttk.Frame(self.workspace, style='Rimaytik.TFrame')
        self.register_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        title_frame = ttk.Frame(self.register_frame, style='Rimaytik.TFrame')
        title_frame.pack(pady=30)
        
        logo_label = ttk.Label(
            title_frame,
            text="📝 Регистрация в RiMayTik",
            font=self.fonts['title'],
            foreground=self.colors['primary'],
            style='Rimaytik.TLabel'
        )
        logo_label.pack()
        
        # Форма регистрации
        form_frame = ttk.Frame(self.register_frame, style='Rimaytik.TFrame')
        form_frame.pack(pady=20)
        
        row = 0
        
        # Сервер
        ttk.Label(
            form_frame,
            text="Сервер:",
            font=self.fonts['normal'],
            style='Rimaytik.TLabel'
        ).grid(row=row, column=0, sticky=tk.W, pady=5)
        
        self.reg_server_entry = ttk.Entry(form_frame, width=30, font=self.fonts['normal'])
        self.reg_server_entry.grid(row=row, column=1, pady=5, padx=10)
        self.reg_server_entry.insert(0, "127.0.0.1:8888")
        row += 1
        
        # Имя пользователя
        ttk.Label(
            form_frame,
            text="Имя пользователя:",
            font=self.fonts['normal'],
            style='Rimaytik.TLabel'
        ).grid(row=row, column=0, sticky=tk.W, pady=5)
        
        self.reg_username_entry = ttk.Entry(form_frame, width=30, font=self.fonts['normal'])
        self.reg_username_entry.grid(row=row, column=1, pady=5, padx=10)
        row += 1
        
        # Отображаемое имя
        ttk.Label(
            form_frame,
            text="Отображаемое имя:",
            font=self.fonts['normal'],
            style='Rimaytik.TLabel'
        ).grid(row=row, column=0, sticky=tk.W, pady=5)
        
        self.reg_display_entry = ttk.Entry(form_frame, width=30, font=self.fonts['normal'])
        self.reg_display_entry.grid(row=row, column=1, pady=5, padx=10)
        row += 1
        
        # Пароль
        ttk.Label(
            form_frame,
            text="Пароль:",
            font=self.fonts['normal'],
            style='Rimaytik.TLabel'
        ).grid(row=row, column=0, sticky=tk.W, pady=5)
        
        self.reg_password_entry = ttk.Entry(form_frame, width=30, show="•", font=self.fonts['normal'])
        self.reg_password_entry.grid(row=row, column=1, pady=5, padx=10)
        row += 1
        
        # Подтверждение пароля
        ttk.Label(
            form_frame,
            text="Подтвердите пароль:",
            font=self.fonts['normal'],
            style='Rimaytik.TLabel'
        ).grid(row=row, column=0, sticky=tk.W, pady=5)
        
        self.reg_confirm_entry = ttk.Entry(form_frame, width=30, show="•", font=self.fonts['normal'])
        self.reg_confirm_entry.grid(row=row, column=1, pady=5, padx=10)
        row += 1
        
        # Уровень безопасности
        ttk.Label(
            form_frame,
            text="Уровень безопасности:",
            font=self.fonts['normal'],
            style='Rimaytik.TLabel'
        ).grid(row=row, column=0, sticky=tk.W, pady=5)
        
        self.security_var = tk.StringVar(value="2")
        security_frame = ttk.Frame(form_frame)
        security_frame.grid(row=row, column=1, sticky=tk.W, pady=5, padx=10)
        
        ttk.Radiobutton(
            security_frame,
            text="Базовый (быстрее)",
            variable=self.security_var,
            value="1"
        ).pack(anchor=tk.W)
        
        ttk.Radiobutton(
            security_frame,
            text="Стандартный (рекомендуется)",
            variable=self.security_var,
            value="2"
        ).pack(anchor=tk.W)
        
        ttk.Radiobutton(
            security_frame,
            text="Максимальный (надежнее)",
            variable=self.security_var,
            value="3"
        ).pack(anchor=tk.W)
        
        # Кнопки
        button_frame = ttk.Frame(self.register_frame, style='Rimaytik.TFrame')
        button_frame.pack(pady=20)
        
        register_button = ttk.Button(
            button_frame,
            text="Зарегистрироваться",
            command=self.on_register,
            width=20
        )
        register_button.pack(side=tk.LEFT, padx=5)
        
        back_button = ttk.Button(
            button_frame,
            text="Назад",
            command=self.show_login_screen,
            width=20
        )
        back_button.pack(side=tk.LEFT, padx=5)
        
        # Связываем Enter с регистрацией
        self.reg_confirm_entry.bind('<Return>', lambda e: self.on_register())
        
    def show_main_chat(self):
        """Показать основной интерфейс чата"""
        self.clear_workspace()
        
        self.main_chat_frame = ttk.Frame(self.workspace, style='Rimaytik.TFrame')
        self.main_chat_frame.pack(fill=tk.BOTH, expand=True)
        
        # Разделитель панелей
        paned_window = ttk.PanedWindow(self.main_chat_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Левая панель - контакты
        self.left_panel = ttk.Frame(paned_window, width=300, style='Rimaytik.TFrame')
        
        # Заголовок контактов
        contacts_header = ttk.Frame(self.left_panel, height=40, style='Rimaytik.TFrame')
        contacts_header.pack(fill=tk.X, padx=10, pady=10)
        
        contacts_label = ttk.Label(
            contacts_header,
            text="Контакты",
            font=self.fonts['heading'],
            style='Rimaytik.TLabel'
        )
        contacts_label.pack(side=tk.LEFT)
        
        # Кнопка обновления
        refresh_button = ttk.Button(
            contacts_header,
            text="🔄",
            width=3,
            command=self.refresh_contacts
        )
        refresh_button.pack(side=tk.RIGHT)
        
        # Список контактов
        contacts_container = ttk.Frame(self.left_panel, style='Rimaytik.TFrame')
        contacts_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Treeview для контактов
        self.contacts_tree = ttk.Treeview(
            contacts_container,
            columns=('status', 'name', 'security'),
            show='tree headings',
            height=20
        )
        
        # Настройка колонок
        self.contacts_tree.column('#0', width=0, stretch=tk.NO)  # Скрытая колонка
        self.contacts_tree.column('status', width=30, anchor=tk.CENTER)
        self.contacts_tree.column('name', width=200, anchor=tk.W)
        self.contacts_tree.column('security', width=50, anchor=tk.CENTER)
        
        # Заголовки
        self.contacts_tree.heading('status', text='', anchor=tk.CENTER)
        self.contacts_tree.heading('name', text='Имя', anchor=tk.W)
        self.contacts_tree.heading('security', text='🔒', anchor=tk.CENTER)
        
        # Scrollbar
        contacts_scroll = ttk.Scrollbar(
            contacts_container,
            orient=tk.VERTICAL,
            command=self.contacts_tree.yview
        )
        self.contacts_tree.configure(yscrollcommand=contacts_scroll.set)
        
        self.contacts_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        contacts_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Привязка событий
        self.contacts_tree.bind('<<TreeviewSelect>>', self.on_contact_select)
        
        # Кнопки управления контактами
        contacts_buttons = ttk.Frame(self.left_panel, style='Rimaytik.TFrame')
        contacts_buttons.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        add_button = ttk.Button(
            contacts_buttons,
            text="➕ Добавить",
            command=self.add_contact_dialog
        )
        add_button.pack(side=tk.LEFT, padx=2)
        
        remove_button = ttk.Button(
            contacts_buttons,
            text="🗑️ Удалить",
            command=self.remove_contact
        )
        remove_button.pack(side=tk.LEFT, padx=2)
        
        paned_window.add(self.left_panel, weight=1)
        
        # Правая панель - чат
        self.right_panel = ttk.Frame(paned_window, style='Rimaytik.TFrame')
        
        # Заголовок чата
        self.chat_header = ttk.Frame(self.right_panel, height=40, style='Rimaytik.TFrame')
        self.chat_header.pack(fill=tk.X, padx=10, pady=10)
        
        self.chat_title = ttk.Label(
            self.chat_header,
            text="Выберите контакт для начала общения",
            font=self.fonts['heading'],
            style='Rimaytik.TLabel'
        )
        self.chat_title.pack(side=tk.LEFT)
        
        # Область сообщений
        self.messages_frame = ttk.Frame(self.right_panel, style='Rimaytik.TFrame')
        self.messages_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Text widget для сообщений
        self.chat_text = tk.Text(
            self.messages_frame,
            wrap=tk.WORD,
            font=self.fonts['normal'],
            bg=self.colors['chat_bg'],
            state=tk.DISABLED,
            padx=10,
            pady=10
        )
        
        # Scrollbar для чата
        chat_scroll = ttk.Scrollbar(
            self.messages_frame,
            orient=tk.VERTICAL,
            command=self.chat_text.yview
        )
        self.chat_text.configure(yscrollcommand=chat_scroll.set)
        
        self.chat_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Панель ввода сообщения
        input_frame = ttk.Frame(self.right_panel, style='Rimaytik.TFrame')
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        
        # Кнопки в панели ввода
        buttons_frame = ttk.Frame(input_frame, style='Rimaytik.TFrame')
        buttons_frame.pack(fill=tk.X, pady=(0, 5))
        
        emoji_button = ttk.Button(
            buttons_frame,
            text="😊",
            width=3,
            command=self.show_emoji_picker
        )
        emoji_button.pack(side=tk.LEFT, padx=2)
        
        file_button = ttk.Button(
            buttons_frame,
            text="📎",
            width=3,
            command=self.send_file_dialog
        )
        file_button.pack(side=tk.LEFT, padx=2)
        
        encrypt_button = ttk.Button(
            buttons_frame,
            text="🔒",
            width=3,
            command=self.toggle_encryption_info
        )
        encrypt_button.pack(side=tk.LEFT, padx=2)
        
        clear_button = ttk.Button(
            buttons_frame,
            text="🗑️ Очистить",
            command=self.clear_chat
        )
        clear_button.pack(side=tk.RIGHT, padx=2)
        
        # Поле ввода сообщения
        self.message_entry = tk.Text(
            input_frame,
            height=3,
            wrap=tk.WORD,
            font=self.fonts['normal'],
            padx=10,
            pady=5
        )
        self.message_entry.pack(fill=tk.X, pady=(0, 5))
        
        # Связываем Ctrl+Enter для отправки
        self.message_entry.bind('<Control-Return>', lambda e: self.send_message())
        
        # Кнопка отправки
        send_button = ttk.Button(
            input_frame,
            text="Отправить сообщение",
            command=self.send_message,
            width=20
        )
        send_button.pack(side=tk.RIGHT)
        
        paned_window.add(self.right_panel, weight=3)
        
        # Нижняя панель - информация
        info_frame = ttk.Frame(self.main_chat_frame, style='Rimaytik.TFrame')
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Информация о пользователе
        user_info = ttk.Label(
            info_frame,
            text=f"👤 {self.client.display_name} ({self.client.username}) | "
                 f"🔒 Уровень защиты: {self.client.security_level}/3",
            font=self.fonts['small'],
            style='Rimaytik.TLabel'
        )
        user_info.pack(side=tk.LEFT)
        
        # Кнопка настроек
        settings_button = ttk.Button(
            info_frame,
            text="⚙️ Настройки",
            command=self.show_settings,
            width=15
        )
        settings_button.pack(side=tk.RIGHT)
        
        # Кнопка выхода
        logout_button = ttk.Button(
            info_frame,
            text="🚪 Выход",
            command=self.on_logout,
            width=15
        )
        logout_button.pack(side=tk.RIGHT, padx=5)
        
    def on_login(self):
        """Обработка нажатия кнопки входа"""
        server = self.server_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not all([server, username, password]):
            messagebox.showerror("Ошибка", "Заполните все поля")
            return
        
        try:
            server_host, server_port = server.split(":")
            server_port = int(server_port)
        except:
            server_host = server
            server_port = 8888
        
        # Показать индикатор загрузки
        self.show_loading("Подключение к RiMayTik...")
        
        # Запуск асинхронного подключения в отдельном потоке
        threading.Thread(
            target=self.async_login,
            args=(server_host, server_port, username, password),
            daemon=True
        ).start()
    
    def async_login(self, host, port, username, password):
        """Асинхронный вход"""
        if not self.async_loop:
            self.async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.async_loop)
        
        async def do_login():
            self.client = RiMayTikClient(host, port)
            
            if await self.client.connect():
                if await self.client.login(username, password):
                    self.connected = True
                    
                    # Обновляем интерфейс в основном потоке
                    self.root.after(0, self.on_login_success)
                    
                    # Запускаем получение сообщений
                    asyncio.create_task(self.client.receive_messages())
                    
                    # Запрашиваем список пользователей
                    await self.client.request_online_users()
                    
                    # Цикл обновления интерфейса
                    while self.connected:
                        await asyncio.sleep(1)
                        self.root.after(0, self.update_ui)
                        
                    return True
                else:
                    self.root.after(0, lambda: self.on_login_error("Неверные учетные данные"))
            else:
                self.root.after(0, lambda: self.on_login_error("Не удалось подключиться к серверу"))
            return False
        
        try:
            self.async_loop.run_until_complete(do_login())
        except Exception as e:
            self.root.after(0, lambda: self.on_login_error(str(e)))
    
    def on_login_success(self):
        """Успешный вход"""
        self.hide_loading()
        self.show_main_chat()
        self.update_status(f"Подключено как {self.client.username}")
        self.update_security_status(f"🔒 Безопасность: Уровень {self.client.security_level}")
        
        # Показать приветственное сообщение
        messagebox.showinfo(
            "RiMayTik Messenger",
            f"Добро пожаловать, {self.client.display_name}!\n\n"
            "Ваши сообщения защищены сквозным шифрованием. "
            "Только вы и получатель можете их прочитать."
        )
    
    def on_login_error(self, error):
        """Ошибка при входе"""
        self.hide_loading()
        messagebox.showerror("Ошибка входа", f"Не удалось войти:\n{error}")
    
    def on_register(self):
        """Обработка регистрации"""
        server = self.reg_server_entry.get().strip()
        username = self.reg_username_entry.get().strip()
        display_name = self.reg_display_entry.get().strip() or username
        password = self.reg_password_entry.get().strip()
        confirm = self.reg_confirm_entry.get().strip()
        
        if not all([server, username, password, confirm]):
            messagebox.showerror("Ошибка", "Заполните все обязательные поля")
            return
        
        if password != confirm:
            messagebox.showerror("Ошибка", "Пароли не совпадают")
            return
        
        if len(password) < 8:
            messagebox.showerror("Ошибка", "Пароль должен быть не менее 8 символов")
            return
        
        try:
            server_host, server_port = server.split(":")
            server_port = int(server_port)
        except:
            server_host = server
            server_port = 8888
        
        security_level = int(self.security_var.get())
        
        # Показать индикатор загрузки
        self.show_loading("Регистрация в RiMayTik...")
        
        # Запуск асинхронной регистрации
        threading.Thread(
            target=self.async_register,
            args=(server_host, server_port, username, display_name, password, security_level),
            daemon=True
        ).start()
    
    def async_register(self, host, port, username, display_name, password, security_level):
        """Асинхронная регистрация"""
        if not self.async_loop:
            self.async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.async_loop)
        
        async def do_register():
            self.client = RiMayTikClient(host, port)
            
            if await self.client.connect():
                # Устанавливаем уровень безопасности
                self.client.security_level = security_level
                self.client.encryption.security_level = security_level
                
                if await self.client.register():
                    self.connected = True
                    
                    # Обновляем интерфейс
                    self.root.after(0, self.on_register_success)
                    
                    # Запускаем получение сообщений
                    asyncio.create_task(self.client.receive_messages())
                    
                    # Цикл обновления интерфейса
                    while self.connected:
                        await asyncio.sleep(1)
                        self.root.after(0, self.update_ui)
                        
                    return True
                else:
                    self.root.after(0, lambda: self.on_register_error("Ошибка регистрации"))
            else:
                self.root.after(0, lambda: self.on_register_error("Не удалось подключиться к серверу"))
            return False
        
        try:
            self.async_loop.run_until_complete(do_register())
        except Exception as e:
            self.root.after(0, lambda: self.on_register_error(str(e)))
    
    def on_register_success(self):
        """Успешная регистрация"""
        self.hide_loading()
        self.show_main_chat()
        self.update_status(f"Зарегистрирован как {self.client.username}")
        self.update_security_status(f"🔒 Безопасность: Уровень {self.client.security_level}")
        
        messagebox.showinfo(
            "Регистрация успешна",
            f"Поздравляем, {self.client.display_name}!\n\n"
            "Вы успешно зарегистрировались в RiMayTik Messenger.\n"
            "Ваши ключи безопасности сгенерированы и сохранены.\n\n"
            "Рекомендуем экспортировать ключи в безопасное место."
        )
    
    def on_register_error(self, error):
        """Ошибка при регистрации"""
        self.hide_loading()
        messagebox.showerror("Ошибка регистрации", f"Не удалось зарегистрироваться:\n{error}")
    
    def on_contact_select(self, event):
        """Выбор контакта в списке"""
        selection = self.contacts_tree.selection()
        if selection:
            item = self.contacts_tree.item(selection[0])
            username = item['values'][1]
            self.open_chat(username)
    
    def open_chat(self, username):
        """Открыть чат с пользователем"""
        self.current_chat = username
        
        # Обновляем заголовок
        display_name = username
        for user in self.online_users:
            if user['username'] == username:
                display_name = user.get('display_name', username)
                break
        
        self.chat_title.config(text=f"💬 Чат с {display_name}")
        
        # Очищаем область сообщений
        self.chat_text.config(state=tk.NORMAL)
        self.chat_text.delete(1.0, tk.END)
        
        # Загружаем историю сообщений
        if username in self.messages:
            for msg in self.messages[username]:
                self.display_message(msg)
        
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)
        
        # Сбрасываем счетчик непрочитанных
        if username in self.unread_counts:
            self.unread_counts[username] = 0
            self.update_contact_display(username)
    
    def send_message(self):
        """Отправить сообщение"""
        if not self.current_chat:
            messagebox.showwarning("Нет контакта", "Выберите контакт для отправки сообщения")
            return
        
        message = self.message_entry.get("1.0", tk.END).strip()
        if not message:
            return
        
        # Отправляем сообщение
        threading.Thread(
            target=self.async_send_message,
            args=(self.current_chat, message),
            daemon=True
        ).start()
        
        # Очищаем поле ввода
        self.message_entry.delete("1.0", tk.END)
        
        # Отображаем сообщение локально
        self.display_own_message(message)
    
    def async_send_message(self, recipient, message):
        """Асинхронная отправка сообщения"""
        async def do_send():
            await self.client.send_direct_message(recipient, message)
        
        if self.async_loop:
            asyncio.run_coroutine_threadsafe(do_send(), self.async_loop)
    
    def display_message(self, message_data):
        """Отображение сообщения в чате"""
        self.chat_text.config(state=tk.NORMAL)
        
        # Форматирование времени
        timestamp = datetime.fromisoformat(message_data['timestamp']).strftime("%H:%M")
        
        # Разный стиль для своих и чужих сообщений
        if message_data['direction'] == 'outgoing':
            bg_color = self.colors['user_message']
            align = 'right'
            sender = "Вы"
        else:
            bg_color = self.colors['contact_message']
            align = 'left'
            sender = message_data.get('sender', 'Неизвестно')
        
        # Вставка сообщения
        self.chat_text.insert(tk.END, f"{timestamp} - {sender}:\n", 'timestamp')
        self.chat_text.insert(tk.END, f"{message_data['message']}\n\n", 'message')
        
        # Теги для форматирования
        self.chat_text.tag_config('timestamp', font=(self.fonts['normal'][0], self.fonts['normal'][1], 'italic'))
        self.chat_text.tag_config('message', 
                                 background=bg_color,
                                 relief=tk.RAISED,
                                 borderwidth=1,
                                 lmargin1=20,
                                 lmargin2=20,
                                 rmargin=20,
                                 spacing3=5)
        
        self.chat_text.config(state=tk.DISABLED)
        self.chat_text.see(tk.END)
    
    def display_own_message(self, message):
        """Отображение своего сообщения (локально)"""
        message_data = {
            'direction': 'outgoing',
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'encrypted': True
        }
        
        if self.current_chat not in self.messages:
            self.messages[self.current_chat] = []
        self.messages[self.current_chat].append(message_data)
        
        self.display_message(message_data)
    
    def add_contact_dialog(self):
        """Диалог добавления контакта"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить контакт")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Центрирование
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(
            dialog,
            text="Добавить нового контакта",
            font=self.fonts['heading']
        ).pack(pady=20)
        
        ttk.Label(dialog, text="Имя пользователя:").pack(pady=5)
        
        contact_entry = ttk.Entry(dialog, width=30)
        contact_entry.pack(pady=5)
        contact_entry.focus()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        def add_contact():
            username = contact_entry.get().strip()
            if username:
                if username == self.client.username:
                    messagebox.showerror("Ошибка", "Нельзя добавить самого себя")
                else:
                    # Отправляем запрос
                    threading.Thread(
                        target=self.async_add_contact,
                        args=(username,),
                        daemon=True
                    ).start()
                    dialog.destroy()
        
        ttk.Button(
            button_frame,
            text="Добавить",
            command=add_contact
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Отмена",
            command=dialog.destroy
        ).pack(side=tk.LEFT, padx=5)
        
        dialog.bind('<Return>', lambda e: add_contact())
    
    def async_add_contact(self, username):
        """Асинхронное добавление контакта"""
        async def do_add():
            await self.client.send_contact_request(username)
        
        if self.async_loop:
            asyncio.run_coroutine_threadsafe(do_add(), self.async_loop)
    
    def remove_contact(self):
        """Удаление выбранного контакта"""
        selection = self.contacts_tree.selection()
        if selection:
            item = self.contacts_tree.item(selection[0])
            username = item['values'][1]
            
            if messagebox.askyesno("Удаление контакта", f"Удалить {username} из контактов?"):
                # Удаляем из интерфейса
                self.contacts_tree.delete(selection[0])
                
                # Удаляем из данных
                self.contacts = [c for c in self.contacts if c['username'] != username]
                
                if self.current_chat == username:
                    self.current_chat = None
                    self.chat_title.config(text="Выберите контакт для начала общения")
                    self.chat_text.config(state=tk.NORMAL)
                    self.chat_text.delete(1.0, tk.END)
                    self.chat_text.config(state=tk.DISABLED)
    
    def refresh_contacts(self):
        """Обновить список контактов"""
        if self.client:
            threading.Thread(
                target=self.async_refresh_contacts,
                daemon=True
            ).start()
    
    def async_refresh_contacts(self):
        """Асинхронное обновление контактов"""
        async def do_refresh():
            await self.client.request_online_users()
        
        if self.async_loop:
            asyncio.run_coroutine_threadsafe(do_refresh(), self.async_loop)
    
    def show_emoji_picker(self):
        """Показать палитру эмодзи"""
        emojis = ["😊", "😂", "😍", "🤔", "😎", "🥳", "👍", "👎", "❤️", "🔥", "✨", "🎉"]
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Эмодзи")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        
        # Создаем сетку эмодзи
        for i, emoji in enumerate(emojis):
            btn = ttk.Button(
                dialog,
                text=emoji,
                width=3,
                command=lambda e=emoji: self.insert_emoji(e, dialog)
            )
            btn.grid(row=i//4, column=i%4, padx=2, pady=2)
        
        # Центрирование
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
    
    def insert_emoji(self, emoji, dialog):
        """Вставить эмодзи в поле сообщения"""
        self.message_entry.insert(tk.INSERT, emoji)
        dialog.destroy()
    
    def send_file_dialog(self):
        """Диалог отправки файла"""
        filename = filedialog.askopenfilename(
            title="Выберите файл для отправки",
            filetypes=[
                ("Все файлы", "*.*"),
                ("Изображения", "*.png *.jpg *.jpeg *.gif"),
                ("Документы", "*.pdf *.doc *.docx *.txt"),
                ("Архивы", "*.zip *.rar *.7z")
            ]
        )
        
        if filename:
            # В реальной реализации здесь было бы шифрование и отправка файла
            messagebox.showinfo("Отправка файла", 
                f"Файл {os.path.basename(filename)} будет зашифрован и отправлен.\n"
                "Эта функция находится в разработке.")
    
    def toggle_encryption_info(self):
        """Показать/скрыть информацию о шифровании"""
        info = (
            "🔐 Информация о шифровании:\n\n"
            f"Уровень защиты: {self.client.security_level}/3\n"
            "Алгоритмы:\n"
            "  • RSA для обмена ключами\n"
            "  • AES-256-GCM для шифрования\n"
            "  • Perfect Forward Secrecy\n"
            "  • Двойной ратач\n\n"
            "Все сообщения защищены сквозным шифрованием."
        )
        messagebox.showinfo("Безопасность RiMayTik", info)
    
    def clear_chat(self):
        """Очистить текущий чат"""
        if self.current_chat and messagebox.askyesno("Очистка чата", 
                                                    "Очистить историю текущего чата?"):
            self.chat_text.config(state=tk.NORMAL)
            self.chat_text.delete(1.0, tk.END)
            self.chat_text.config(state=tk.DISABLED)
            
            if self.current_chat in self.messages:
                self.messages[self.current_chat] = []
    
    def show_settings(self):
        """Показать настройки"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Настройки RiMayTik")
        dialog.geometry("500x400")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Вкладка безопасности
        security_frame = ttk.Frame(notebook)
        
        ttk.Label(
            security_frame,
            text="Настройки безопасности",
            font=self.fonts['heading']
        ).pack(pady=10)
        
        # Экспорт ключей
        ttk.Button(
            security_frame,
            text="🔑 Экспорт ключей",
            command=self.export_keys_dialog,
            width=20
        ).pack(pady=10)
        
        # Импорт ключей
        ttk.Button(
            security_frame,
            text="📥 Импорт ключей",
            command=self.import_keys_dialog,
            width=20
        ).pack(pady=10)
        
        # Смена пароля
        ttk.Button(
            security_frame,
            text="🔐 Сменить пароль",
            command=self.change_password_dialog,
            width=20
        ).pack(pady=10)
        
        notebook.add(security_frame, text="Безопасность")
        
        # Вкладка внешнего вида
        appearance_frame = ttk.Frame(notebook)
        
        ttk.Label(
            appearance_frame,
            text="Настройки внешнего вида",
            font=self.fonts['heading']
        ).pack(pady=10)
        
        # Выбор темы
        ttk.Label(appearance_frame, text="Тема:").pack(pady=5)
        
        theme_var = tk.StringVar(value="light")
        ttk.Radiobutton(
            appearance_frame,
            text="Светлая",
            variable=theme_var,
            value="light"
        ).pack()
        
        ttk.Radiobutton(
            appearance_frame,
            text="Темная",
            variable=theme_var,
            value="dark"
        ).pack()
        
        notebook.add(appearance_frame, text="Внешний вид")
        
        # Вкладка уведомлений
        notifications_frame = ttk.Frame(notebook)
        
        ttk.Label(
            notifications_frame,
            text="Настройки уведомлений",
            font=self.fonts['heading']
        ).pack(pady=10)
        
        # Чекбоксы уведомлений
        sound_var = tk.BooleanVar(value=True)
        popup_var = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(
            notifications_frame,
            text="Звуковые уведомления",
            variable=sound_var
        ).pack(anchor=tk.W, pady=5)
        
        ttk.Checkbutton(
            notifications_frame,
            text="Всплывающие уведомления",
            variable=popup_var
        ).pack(anchor=tk.W, pady=5)
        
        notebook.add(notifications_frame, text="Уведомления")
        
        # Кнопки диалога
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(
            button_frame,
            text="Сохранить",
            command=dialog.destroy
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Отмена",
            command=dialog.destroy
        ).pack(side=tk.LEFT, padx=5)
        
        # Центрирование
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
    
    def export_keys_dialog(self):
        """Диалог экспорта ключей"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Экспорт ключей")
        dialog.geometry("400x250")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(
            dialog,
            text="Экспорт ключей безопасности",
            font=self.fonts['heading']
        ).pack(pady=20)
        
        ttk.Label(dialog, text="Пароль для защиты ключей:").pack(pady=5)
        
        password_entry = ttk.Entry(dialog, width=30, show="•")
        password_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Подтверждение пароля:").pack(pady=5)
        
        confirm_entry = ttk.Entry(dialog, width=30, show="•")
        confirm_entry.pack(pady=5)
        
        def export():
            password = password_entry.get()
            confirm = confirm_entry.get()
            
            if password != confirm:
                messagebox.showerror("Ошибка", "Пароли не совпадают")
                return
            
            if len(password) < 6:
                messagebox.showerror("Ошибка", "Пароль должен быть не менее 6 символов")
                return
            
            try:
                # Экспорт ключей
                keys_json = self.client.encryption.export_keys(password)
                
                # Сохранение в файл
                filename = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON файлы", "*.json"), ("Все файлы", "*.*")],
                    initialfile=f"rimaytik_keys_{self.client.username}.json"
                )
                
                if filename:
                    with open(filename, 'w') as f:
                        f.write(keys_json)
                    
                    messagebox.showinfo(
                        "Успех",
                        f"Ключи экспортированы в файл:\n{filename}\n\n"
                        "⚠️ Храните этот файл в безопасном месте!"
                    )
                    dialog.destroy()
                    
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать ключи:\n{str(e)}")
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(
            button_frame,
            text="Экспорт",
            command=export
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Отмена",
            command=dialog.destroy
        ).pack(side=tk.LEFT, padx=5)
        
        # Центрирование
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
        
        password_entry.focus()
    
    def import_keys_dialog(self):
        """Диалог импорта ключей"""
        messagebox.showinfo("Импорт ключей", 
            "Эта функция находится в разработке.\n\n"
            "Для импорта ключей выберите файл с экспортированными ключами.")
    
    def change_password_dialog(self):
        """Диалог смены пароля"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Смена пароля")
        dialog.geometry("400x300")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(
            dialog,
            text="Смена пароля",
            font=self.fonts['heading']
        ).pack(pady=20)
        
        # Старый пароль
        ttk.Label(dialog, text="Текущий пароль:").pack(pady=5)
        old_entry = ttk.Entry(dialog, width=30, show="•")
        old_entry.pack(pady=5)
        
        # Новый пароль
        ttk.Label(dialog, text="Новый пароль:").pack(pady=5)
        new_entry = ttk.Entry(dialog, width=30, show="•")
        new_entry.pack(pady=5)
        
        # Подтверждение
        ttk.Label(dialog, text="Подтверждение:").pack(pady=5)
        confirm_entry = ttk.Entry(dialog, width=30, show="•")
        confirm_entry.pack(pady=5)
        
        def change():
            old = old_entry.get()
            new = new_entry.get()
            confirm = confirm_entry.get()
            
            if new != confirm:
                messagebox.showerror("Ошибка", "Новые пароли не совпадают")
                return
            
            if len(new) < 8:
                messagebox.showerror("Ошибка", "Новый пароль должен быть не менее 8 символов")
                return
            
            # В реальной реализации здесь была бы смена пароля на сервере
            messagebox.showinfo("Смена пароля", 
                "Смена пароля находится в разработке.\n"
                "В текущей версии обратитесь к администратору сервера.")
            dialog.destroy()
        
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(
            button_frame,
            text="Сменить",
            command=change
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Отмена",
            command=dialog.destroy
        ).pack(side=tk.LEFT, padx=5)
        
        # Центрирование
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
    
    def on_logout(self):
        """Выход из системы"""
        if messagebox.askyesno("Выход", "Вы уверены, что хотите выйти из RiMayTik?"):
            self.connected = False
            
            if self.client:
                # Асинхронный выход
                async def do_logout():
                    await self.client.logout()
                
                if self.async_loop:
                    asyncio.run_coroutine_threadsafe(do_logout(), self.async_loop)
            
            # Возврат к экрану входа
            self.show_login_screen()
            self.update_status("RiMayTik Messenger - Не подключено")
            self.update_security_status("🔒 Безопасность: Неактивна")
    
    def update_ui(self):
        """Обновление интерфейса"""
        if not self.client:
            return
        
        # Обновление списка контактов
        self.update_contacts_list()
        
        # Проверка новых сообщений
        self.check_new_messages()
        
        # Обновление статуса соединения
        if self.client.connected:
            self.update_status(f"RiMayTik - {self.client.username} | Онлайн")
        else:
            self.update_status("RiMayTik - Не подключено")
    
    def update_contacts_list(self):
        """Обновление списка контактов"""
        # Очищаем текущий список
        for item in self.contacts_tree.get_children():
            self.contacts_tree.delete(item)
        
        # Добавляем онлайн пользователей
        online_usernames = [user['username'] for user in self.online_users]
        
        for user in self.online_users:
            if user['username'] != self.client.username:
                status_icon = "🟢"  # Онлайн
                display_name = user.get('display_name', user['username'])
                security_icon = "🔒" if user.get('security_level', 1) >= 2 else "⚠️"
                
                # Проверяем непрочитанные сообщения
                unread = self.unread_counts.get(user['username'], 0)
                if unread > 0:
                    display_name = f"{display_name} ({unread})"
                
                self.contacts_tree.insert(
                    '',
                    tk.END,
                    values=(status_icon, display_name, security_icon),
                    tags=('online',)
                )
        
        # Добавляем оффлайн контакты
        for contact in self.contacts:
            if contact['username'] not in online_usernames and contact['username'] != self.client.username:
                status_icon = "⚫"  # Оффлайн
                display_name = contact.get('display_name', contact['username'])
                security_icon = "🔒" if contact.get('security_level', 1) >= 2 else "⚠️"
                
                # Проверяем непрочитанные сообщения
                unread = self.unread_counts.get(contact['username'], 0)
                if unread > 0:
                    display_name = f"{display_name} ({unread})"
                
                self.contacts_tree.insert(
                    '',
                    tk.END,
                    values=(status_icon, display_name, security_icon),
                    tags=('offline',)
                )
        
        # Настройка цветов для статусов
        self.contacts_tree.tag_configure('online', background=self.colors['light'])
        self.contacts_tree.tag_configure('offline', background=self.colors['background'])
    
    def update_contact_display(self, username):
        """Обновление отображения конкретного контакта"""
        for item in self.contacts_tree.get_children():
            values = self.contacts_tree.item(item)['values']
            if len(values) > 1 and values[1].startswith(username):
                # Обновляем отображаемое имя
                display_name = values[1].split(' (')[0]  # Убираем счетчик непрочитанных
                unread = self.unread_counts.get(username, 0)
                
                if unread > 0:
                    display_name = f"{display_name} ({unread})"
                
                self.contacts_tree.item(item, values=(values[0], display_name, values[2]))
                break
    
    def check_new_messages(self):
        """Проверка новых сообщений"""
        if not self.client:
            return
        
        # Проверяем историю сообщений клиента
        for msg in self.client.message_history:
            if msg['direction'] == 'incoming':
                sender = msg['from']
                
                # Проверяем, есть ли уже это сообщение
                message_exists = False
                if sender in self.messages:
                    for existing in self.messages[sender]:
                        if existing['message'] == msg['message'] and \
                           existing['timestamp'] == msg['timestamp']:
                            message_exists = True
                            break
                
                if not message_exists:
                    # Добавляем сообщение
                    if sender not in self.messages:
                        self.messages[sender] = []
                    
                    self.messages[sender].append(msg)
                    
                    # Обновляем счетчик непрочитанных
                    if sender != self.current_chat:
                        if sender not in self.unread_counts:
                            self.unread_counts[sender] = 0
                        self.unread_counts[sender] += 1
                        
                        # Обновляем отображение контакта
                        self.update_contact_display(sender)
                        
                        # Уведомление
                        self.show_notification(sender, msg['message'])
                    
                    # Если чат открыт, отображаем сообщение
                    if sender == self.current_chat:
                        self.display_message(msg)
    
    def show_notification(self, sender, message):
        """Показать уведомление о новом сообщении"""
        # Всплывающее уведомление (если окно не активно)
        if not self.root.focus_get():
            try:
                # Для Windows
                from win10toast import ToastNotifier
                toaster = ToastNotifier()
                toaster.show_toast(
                    f"RiMayTik: Новое сообщение от {sender}",
                    message[:50] + ("..." if len(message) > 50 else ""),
                    duration=5,
                    threaded=True
                )
            except:
                # Просто выводим в консоль
                print(f"Новое сообщение от {sender}: {message[:50]}...")
    
    def update_status(self, text):
        """Обновление текста статус-бара"""
        self.status_label.config(text=text)
    
    def update_security_status(self, text):
        """Обновление статуса безопасности"""
        self.security_status.config(text=text)
    
    def show_loading(self, message):
        """Показать индикатор загрузки"""
        self.loading_window = tk.Toplevel(self.root)
        self.loading_window.title("RiMayTik")
        self.loading_window.geometry("300x150")
        self.loading_window.resizable(False, False)
        self.loading_window.transient(self.root)
        self.loading_window.grab_set()
        
        # Центрирование
        self.loading_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - self.loading_window.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - self.loading_window.winfo_height()) // 2
        self.loading_window.geometry(f"+{x}+{y}")
        
        ttk.Label(
            self.loading_window,
            text=message,
            font=self.fonts['normal']
        ).pack(pady=40)
        
        # Индикатор прогресса
        self.loading_progress = ttk.Progressbar(
            self.loading_window,
            mode='indeterminate',
            length=200
        )
        self.loading_progress.pack(pady=10)
        self.loading_progress.start()
    
    def hide_loading(self):
        """Скрыть индикатор загрузки"""
        if hasattr(self, 'loading_window'):
            self.loading_progress.stop()
            self.loading_window.destroy()
    
    def clear_workspace(self):
        """Очистить рабочую область"""
        for widget in self.workspace.winfo_children():
            widget.destroy()
        
        self.login_frame = None
        self.register_frame = None
        self.main_chat_frame = None
    
    def run(self):
        """Запуск главного цикла"""
        self.root.mainloop()

def main():
    """Точка входа GUI"""
    app = RiMayTikUI()
    app.run()

if __name__ == "__main__":
    main()
