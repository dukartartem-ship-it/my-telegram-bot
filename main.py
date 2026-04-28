import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice
import time
import json
import os
from datetime import datetime
from collections import defaultdict
import random
import string

# ==============================================
# ФИЛЬТР ПРОВЕРКИ ПРОФИЛЯ
# ==============================================
def profile_required(message):
    """Проверяет, заполнен ли профиль пользователя"""
    user_id = str(message.from_user.id)
    if user_id in users_data:
        profile = users_data[user_id]
        # Проверяем, что и пол, и возраст указаны
        if profile.get("gender") is not None and profile.get("age") is not None:
            return True
    return False

import requests  # Добавь этот импорт

# ==============================================
# ЗАЩИТА ОТ FLOOD WAIT
# ==============================================
from telebot import apihelper

# Увеличиваем таймауты (Telegram иногда тупит)
apihelper.READ_TIMEOUT = 30
apihelper.CONNECT_TIMEOUT = 15

# Функция для обработки ошибки 429 (Too Many Requests)
def flood_handler(exception):
    """Обработчик flood wait - ждем и пробуем снова"""
    try:
        # Пробуем вытащить время ожидания из ответа Telegram
        error_text = str(exception)
        if '429' in error_text:
            # Пытаемся найти время ожидания в ответе
            import re
            wait_time = 5  # По умолчанию ждем 5 секунд
            
            # Ищем паттерн "retry after X seconds"
            match = re.search(r'retry after (\d+)', error_text.lower())
            if match:
                wait_time = int(match.group(1)) + 1  # +1 для надежности
            
            print(f"⚠️ Flood wait! Ждем {wait_time} секунд...")
            time.sleep(wait_time)
            return True  # Говорим, что можно повторить запрос
    except:
        time.sleep(3)  # Если не смогли распарсить - ждем 3 секунды
        return True
    
    return False

# Устанавливаем обработчик
apihelper.FLOOD_CONTROL_HANDLER = flood_handler

# Функция для безопасной отправки сообщений
def safe_send_message(chat_id, text, parse_mode=None, reply_markup=None, retry=3):
    """Безопасная отправка с повторными попытками"""
    for attempt in range(retry):
        try:
            return bot.send_message(
                chat_id, 
                text, 
                parse_mode=parse_mode, 
                reply_markup=reply_markup,
                timeout=10
            )
        except Exception as e:
            if '429' in str(e) or 'Too Many Requests' in str(e):
                print(f"⚠️ Flood wait на попытке {attempt+1}, ждем...")
                time.sleep(5 * (attempt + 1))  # Увеличиваем время ожидания с каждой попыткой
            elif attempt == retry - 1:
                print(f"❌ Не удалось отправить сообщение: {e}")
                return None
            else:
                time.sleep(2)
    return None

# Функция для безопасной отправки с картинкой
def safe_send_photo(chat_id, photo, caption=None, parse_mode=None, reply_markup=None, retry=3):
    """Безопасная отправка фото с повторными попытками"""
    for attempt in range(retry):
        try:
            return bot.send_photo(
                chat_id,
                photo,
                caption=caption,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                timeout=15  # Фото может грузиться дольше
            )
        except Exception as e:
            if '429' in str(e) or 'Too Many Requests' in str(e):
                print(f"⚠️ Flood wait при отправке фото на попытке {attempt+1}")
                time.sleep(5 * (attempt + 1))
            elif attempt == retry - 1:
                print(f"❌ Не удалось отправить фото: {e}")
                # Пробуем отправить без фото
                try:
                    return bot.send_message(chat_id, caption, parse_mode=parse_mode, reply_markup=reply_markup)
                except:
                    pass
                return None
            else:
                time.sleep(2)
    return None

# ==============================================
# ТВОИ ДАННЫЕ
# ==============================================
TOKEN = '8615517752:AAF0ADC5YhKgIONtOKMUEKgxBwc2aKpFdPs'  # Твой токен
ADMIN_USERNAME = 'cntrlxx'  # Твой username

bot = telebot.TeleBot(TOKEN)

# ==============================================
# КАРТИНКИ ДЛЯ РАЗНЫХ СООБЩЕНИЙ
# ==============================================
IMAGES = {
    "main": "https://i.imgur.com/9qXjZ5k.jpg",        # Главное меню
    "search": "https://i.imgur.com/L7q8kYt.jpg",      # Поиск собеседника
    "chat_start": "https://i.imgur.com/W4qZ9mN.jpg",  # Начало чата
    "chat_end": "https://i.imgur.com/r5kL8pV.jpg",     # Завершение чата
    "profile": "https://i.imgur.com/K2nYx7M.jpg",      # Профиль
    "premium": "https://i.imgur.com/H3jL9tR.jpg",      # Premium меню
    "stats": "https://i.imgur.com/B8vN4wX.jpg",        # Статистика
    "top": "https://i.imgur.com/F5dQ1sZ.jpg",          # Топ пользователей
    "stories": "https://i.imgur.com/X6mR2cV.jpg",      # Истории
    "help": "https://i.imgur.com/J7nK3pL.jpg",         # Помощь
    "filters": "https://i.imgur.com/Y8tU5oA.jpg",      # Фильтры
    "timeout": "https://i.imgur.com/Q9vE2rB.jpg",      # Таймаут поиска
    "report": "https://i.imgur.com/P5sH1jW.jpg",       # Жалоба
    "register": "https://i.imgur.com/D3mR6kZ.jpg",     # Регистрация
    "ref": "https://i.imgur.com/1nX9c4L.jpg",          # Рефералка
    "warning": "https://i.imgur.com/V8wZ2fT.jpg",      # Предупреждение
}

# ==============================================
# БАЗА ДАННЫХ
# ==============================================

APP_DATA_DIR = os.path.join(os.path.expanduser('~'), 'Documents', 'anon_bot_data')
os.makedirs(APP_DATA_DIR, exist_ok=True)

DATA_FILE = os.path.join(APP_DATA_DIR, 'users_data.json')
PREMIUM_FILE = os.path.join(APP_DATA_DIR, 'premium_data.json')
STORIES_FILE = os.path.join(APP_DATA_DIR, 'stories_data.json')
MEDIA_DIR = os.path.join(APP_DATA_DIR, 'chat_media')
os.makedirs(MEDIA_DIR, exist_ok=True)

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_premium():
    if os.path.exists(PREMIUM_FILE):
        try:
            with open(PREMIUM_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_premium(data):
    try:
        with open(PREMIUM_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_stories():
    if os.path.exists(STORIES_FILE):
        try:
            with open(STORIES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_stories(data):
    try:
        with open(STORIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def save_media_file(file_id, file_type, chat_id, sender_id):
    """Скачивает и сохраняет медиафайл"""
    try:
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        chat_media_dir = os.path.join(MEDIA_DIR, chat_id)
        os.makedirs(chat_media_dir, exist_ok=True)
        
        timestamp = int(time.time())
        extension = file_info.file_path.split('.')[-1] if '.' in file_info.file_path else 'dat'
        filename = f"{timestamp}_{sender_id}_{file_type}.{extension}"
        filepath = os.path.join(chat_media_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(downloaded_file)
        
        return filepath
    except Exception as e:
        print(f"Ошибка сохранения медиа: {e}")
        return None

# Загружаем данные
users_data = load_data()
premium_data = load_premium()
stories_data = load_stories()
waiting_list = []
active_chats = {}
chat_messages = defaultdict(list)
ADMIN_IDS = []

# Словарь для отслеживания уникальных приглашений (защита от накрутки)
invited_users = defaultdict(set)  # {inviter_id: {user_id1, user_id2, ...}}

# ==============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================================

def generate_ref_code(user_id):
    return f"ref_{user_id}_{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"

def send_with_image(chat_id, text, image_key, parse_mode='Markdown', reply_markup=None):
    """Отправляет сообщение с картинкой сверху"""
    try:
        if image_key in IMAGES:
            bot.send_photo(
                chat_id,
                IMAGES[image_key],
                caption=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        else:
            bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        print(f"Ошибка отправки с картинкой: {e}")
        bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)

def edit_with_image(message, new_text, image_key, parse_mode='Markdown', reply_markup=None):
    """Редактирует сообщение, меняя картинку и текст"""
    try:
        if image_key in IMAGES:
            bot.delete_message(message.chat.id, message.message_id)
            send_with_image(message.chat.id, new_text, image_key, parse_mode, reply_markup)
        else:
            bot.edit_message_text(new_text, message.chat.id, message.message_id, 
                                 parse_mode=parse_mode, reply_markup=reply_markup)
    except Exception as e:
        print(f"Ошибка редактирования: {e}")
        try:
            bot.edit_message_text(new_text, message.chat.id, message.message_id,
                                 parse_mode=parse_mode, reply_markup=reply_markup)
        except:
            send_with_image(message.chat.id, new_text, image_key, parse_mode, reply_markup)

def get_user_profile(user_id):
    user_id = str(user_id)
    if user_id not in users_data:
        users_data[user_id] = {
            "username": None,
            "first_seen": time.time(),
            "gender": None,
            "age": None,
            "dialogs": 0,
            "messages_sent": 0,
            "total_chat_time": 0,
            "ref_code": generate_ref_code(user_id),
            "invited_count": 0,
            "invited_unique_count": 0,  # Новый ключ
            "reactions_received": {"❤️": 0, "🔥": 0, "🥶": 0, "💩": 0},
            "state": "none",
            "partner_id": None,
            "chat_id": None,
            "search_start_time": 0,
            "filters": {
                "gender": "any",
                "age": [],
                "interests": [],
                "country": "any"
            },
            "banned": False,
            "story_temp": {}
        }
        save_data(users_data)
    else:
        # ДЛЯ СТАРЫХ ПОЛЬЗОВАТЕЛЕЙ: добавляем недостающие ключи
        if "invited_unique_count" not in users_data[user_id]:
            users_data[user_id]["invited_unique_count"] = users_data[user_id].get("invited_count", 0)
        
        if "received_5_invites_reward" not in users_data[user_id]:
            users_data[user_id]["received_5_invites_reward"] = False
            
        save_data(users_data)
    
    return users_data[user_id]

def check_premium(user_id):
    user_id = str(user_id)
    if user_id in premium_data:
        expiry = premium_data[user_id].get("expiry", 0)
        if expiry > time.time() or premium_data[user_id].get("forever", False):
            return True
    return False

def add_premium_hours(user_id, hours):
    user_id = str(user_id)
    now = time.time()
    
    if user_id in premium_data:
        current_expiry = premium_data[user_id].get("expiry", now)
        if current_expiry > now:
            new_expiry = current_expiry + (hours * 3600)
        else:
            new_expiry = now + (hours * 3600)
    else:
        new_expiry = now + (hours * 3600)
    
    premium_data[user_id] = {
        "expiry": new_expiry,
        "forever": False
    }
    save_premium(premium_data)
    return new_expiry

def add_premium_days(user_id, days):
    """Добавляет Premium на указанное количество дней"""
    return add_premium_hours(user_id, days * 24)

def check_and_give_weekly_premium(inviter_id):
    """Проверяет, достиг ли пригласивший 5 уникальных приглашений и выдаёт неделю Premium"""
    inviter_id = str(inviter_id)
    
    # Получаем количество уникальных приглашенных
    unique_count = users_data[inviter_id].get("invited_unique_count", 0)
    
    # Проверяем, достиг ли пользователь порога в 5 и не получал ли уже награду за этот порог
    if unique_count >= 5 and not users_data[inviter_id].get("received_5_invites_reward", False):
        # Выдаём неделю Premium
        expiry = add_premium_days(inviter_id, 7)
        
        # Отмечаем, что награда получена
        users_data[inviter_id]["received_5_invites_reward"] = True
        save_data(users_data)
        
        # Уведомляем пользователя
        try:
            send_with_image(
                int(inviter_id),
                "🎉 *ТЫ ПОЛУЧИЛ НЕДЕЛЮ PREMIUM!*\n\n"
                "🔥 Ты пригласил 5 друзей и получил награду!\n"
                f"📅 Premium активен до: {datetime.fromtimestamp(expiry).strftime('%d.%m.%Y %H:%M')}\n\n"
                "✨ Теперь тебе доступны все функции Premium:"
                "\n• Выбор пола собеседника"
                "\n• Информация о возрасте"
                "\n• Возврат собеседника"
                "\n• Бесплатное обнуление рейтинга",
                "premium"
            )
        except:
            pass
        
        # Уведомляем админа
        global ADMIN_ID
        if ADMIN_ID:
            try:
                username = users_data[inviter_id].get("username", "без username")
                bot.send_message(
                    ADMIN_ID,
                    f"👑 *НОВАЯ НАГРАДА!*\n\n"
                    f"👤 Пользователь @{username} (ID: `{inviter_id}`)\n"
                    f"🎉 Пригласил 5 друзей и получил неделю Premium!\n"
                    f"👥 Всего приглашено: {unique_count}",
                    parse_mode='Markdown'
                )
            except:
                pass
        
        return True
    return False

def process_referral(inviter_id, new_user_id):
    """Обрабатывает реферальный переход с защитой от накрутки"""
    inviter_id = str(inviter_id)
    new_user_id = str(new_user_id)
    
    # ЗАЩИТА ОТ НАКРУТКИ:
    # 1. Нельзя пригласить самого себя
    if inviter_id == new_user_id:
        return False, "self"
    
    # 2. Проверяем, не приглашал ли уже этот пользователь данного реферала
    if new_user_id in invited_users[inviter_id]:
        return False, "already_invited"
    
    # 3. Проверяем, не пытается ли пользователь накрутить через смену username
    # (у нас уже есть проверка по user_id, так что это безопасно)
    
    # 4. Добавляем в список приглашенных
    invited_users[inviter_id].add(new_user_id)
    
    # Увеличиваем счетчик уникальных приглашений
    users_data[inviter_id]["invited_count"] = users_data[inviter_id].get("invited_count", 0) + 1
    users_data[inviter_id]["invited_unique_count"] = users_data[inviter_id].get("invited_unique_count", 0) + 1
    save_data(users_data)
    
    # Добавляем 2 часа Premium за приглашение
    add_premium_hours(inviter_id, 2)
    
    # Проверяем, не достиг ли пользователь 5 приглашений
    check_and_give_weekly_premium(inviter_id)
    
    # Уведомляем пригласившего
    try:
        bot.send_message(
            int(inviter_id),
            "🎉 *Новый друг!*\n\n"
            f"👤 По твоей ссылке зарегистрировался новый пользователь!\n"
            f"⏱ Ты получил +2 часа Premium\n"
            f"👥 Всего приглашено: {users_data[inviter_id]['invited_unique_count']}",
            parse_mode='Markdown'
        )
    except:
        pass
    
    return True, "success"

def cleanup_old_stories():
    """Удаляет истории старше 24 часов"""
    current_time = time.time()
    initial_count = len(stories_data)
    
    for story_id in list(stories_data.keys()):
        if current_time - stories_data[story_id]["time"] > 86400:
            del stories_data[story_id]
    
    if initial_count != len(stories_data):
        save_stories(stories_data)
        print(f"🧹 Очищено {initial_count - len(stories_data)} старых историй")

def try_find_pair():
    global waiting_list, active_chats
    
    current_time = time.time()
    # Проверяем таймаут (3 минуты)
    for user_id in waiting_list[:]:
        user_data = users_data.get(user_id, {})
        search_start = user_data.get("search_start_time", 0)
        
        if search_start > 0 and current_time - search_start > 180:
            waiting_list.remove(user_id)
            users_data[user_id]["state"] = "none"
            users_data[user_id]["search_start_time"] = 0
            save_data(users_data)
            
            try:
                send_with_image(
                    int(user_id),
                    "⏱ *Не можем подобрать собеседника*\n\nПопробуй позже",
                    "timeout",
                    reply_markup=main_keyboard()
                )
            except:
                pass
    
    # Поиск пары
    while len(waiting_list) >= 2:
        user1 = waiting_list.pop(0)
        user2 = waiting_list.pop(0)
        
        if user1 not in waiting_list and user2 not in waiting_list:
            chat_id = f"{user1}_{user2}_{int(time.time())}"
            active_chats[chat_id] = {
                "user1": user1,
                "user2": user2,
                "created_at": time.time()
            }
            
            users_data[user1]["state"] = "chatting"
            users_data[user1]["partner_id"] = user2
            users_data[user1]["chat_id"] = chat_id
            users_data[user1]["search_start_time"] = 0
            
            users_data[user2]["state"] = "chatting"
            users_data[user2]["partner_id"] = user1
            users_data[user2]["chat_id"] = chat_id
            users_data[user2]["search_start_time"] = 0
            
            users_data[user1]["dialogs"] += 1
            users_data[user2]["dialogs"] += 1
            save_data(users_data)
            
            send_chat_start_message(user1, user2)
            send_chat_start_message(user2, user1)

def send_chat_start_message(user_id, partner_id):
    partner_data = users_data.get(partner_id, {})
    has_premium = check_premium(int(user_id))
    
    if has_premium and partner_data.get("gender"):
        gender_text = "👨 Парень" if partner_data["gender"] == "male" else "👩 Девушка"
        age_text = partner_data.get("age", "не указан")
        info_text = f"\n👤 {gender_text}\n📅 Возраст: {age_text}"
    else:
        info_text = "\n👤 Пол: не указан\n📅 Возраст: не указан"
    
    send_with_image(
        int(user_id),
        f"💬 *Собеседник найден!*{info_text}\n\n/stop - выйти\n/next - следующий",
        "chat_start",
        reply_markup=in_chat_keyboard()
    )

def leave_chat_by_id(user_id, notify=True, voluntarily=True):
    """
    Завершает чат
    voluntarily=True - пользователь сам вышел
    voluntarily=False - пользователя кикнули (собеседник вышел)
    """
    user_id = str(user_id)
    
    for chat_id, chat in list(active_chats.items()):
        if chat["user1"] == user_id or chat["user2"] == user_id:
            partner_id = chat["user2"] if chat["user1"] == user_id else chat["user1"]
            
            duration = int(time.time() - chat["created_at"])
            minutes = duration // 60
            seconds = duration % 60
            time_str = f"{minutes} мин {seconds} сек" if minutes > 0 else f"{seconds} сек"
            
            # Добавляем время к общему счетчику пользователя
            users_data[user_id]["total_chat_time"] = users_data[user_id].get("total_chat_time", 0) + duration
            users_data[partner_id]["total_chat_time"] = users_data[partner_id].get("total_chat_time", 0) + duration
            save_data(users_data)
            
            # Сообщение для того, кто завершил диалог
            if voluntarily:
                # Пользователь сам вышел
                keyboard = InlineKeyboardMarkup(row_width=4)
                keyboard.add(
                    InlineKeyboardButton("❤️", callback_data=f"react_{partner_id}_❤️"),
                    InlineKeyboardButton("🔥", callback_data=f"react_{partner_id}_🔥"),
                    InlineKeyboardButton("🥶", callback_data=f"react_{partner_id}_🥶"),
                    InlineKeyboardButton("💩", callback_data=f"react_{partner_id}_💩")
                )
                keyboard.row(
                    InlineKeyboardButton("👮 Жалоба", callback_data=f"report_{partner_id}"),
                    InlineKeyboardButton("🔄 Вернуть", callback_data=f"return_{partner_id}")
                )
                
                send_with_image(
                    int(user_id),
                    f"✅ *Ты завершил диалог*\n\n⏱ Время: {time_str}\n\nОцени собеседника:",
                    "chat_end",
                    reply_markup=keyboard
                )
                
                # Сообщение для партнера (собеседник вышел)
                if notify:
                    send_with_image(
                        int(partner_id),
                        f"👋 *Собеседник завершил диалог*\n\n⏱ Время: {time_str}",
                        "chat_end"
                    )
            else:
                # Пользователя завершили (собеседник вышел)
                send_with_image(
                    int(user_id),
                    f"👋 *Собеседник завершил диалог*\n\n⏱ Время: {time_str}",
                    "chat_end"
                )
                
                # Для партнера (который вышел) отправим другое сообщение
                if notify:
                    keyboard = InlineKeyboardMarkup(row_width=4)
                    keyboard.add(
                        InlineKeyboardButton("❤️", callback_data=f"react_{user_id}_❤️"),
                        InlineKeyboardButton("🔥", callback_data=f"react_{user_id}_🔥"),
                        InlineKeyboardButton("🥶", callback_data=f"react_{user_id}_🥶"),
                        InlineKeyboardButton("💩", callback_data=f"react_{user_id}_💩")
                    )
                    keyboard.row(
                        InlineKeyboardButton("👮 Жалоба", callback_data=f"report_{user_id}"),
                        InlineKeyboardButton("🔄 Вернуть", callback_data=f"return_{user_id}")
                    )
                    
                    send_with_image(
                        int(partner_id),
                        f"✅ *Ты завершил диалог*\n\n⏱ Время: {time_str}\n\nОцени собеседника:",
                        "chat_end",
                        reply_markup=keyboard
                    )
            
            del active_chats[chat_id]
            
            for uid in [user_id, partner_id]:
                if uid in users_data:
                    users_data[uid]["state"] = "none"
                    users_data[uid]["partner_id"] = None
                    users_data[uid]["chat_id"] = None
            
            save_data(users_data)
            break

# ==============================================
# КЛАВИАТУРЫ
# ==============================================

def main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔍 НАЙТИ СОБЕСЕДНИКА"))
    keyboard.row(KeyboardButton("👤 Профиль"), KeyboardButton("📊 Статистика"))
    keyboard.row(KeyboardButton("⚙️ Фильтр поиска"), KeyboardButton("⭐ Премиум"))
    keyboard.row(KeyboardButton("🔝 Топ"), KeyboardButton("📸 Истории"))
    keyboard.row(KeyboardButton("❓ Помощь"))
    return keyboard

def profile_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📊 Моя статистика", callback_data="my_stats"),
        InlineKeyboardButton("🔗 Реферальная ссылка", callback_data="ref_link")
    )
    keyboard.add(
        InlineKeyboardButton("👤 Изменить пол", callback_data="edit_gender"),
        InlineKeyboardButton("📅 Изменить возраст", callback_data="edit_age")
    )
    return keyboard

def premium_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("⭐ 1 день - 35 ⭐", callback_data="premium_day"),
        InlineKeyboardButton("⭐ 5 дней - 100 ⭐", callback_data="premium_5days"),
        InlineKeyboardButton("⭐ Месяц - 225 ⭐", callback_data="premium_month"),
        InlineKeyboardButton("💎 Навсегда - 500 ⭐", callback_data="premium_forever"),
        InlineKeyboardButton("🧹 Обнулить рейтинг - 25 ⭐", callback_data="premium_reset"),
        InlineKeyboardButton("🎁 Бесплатный премиум", callback_data="free_premium")
    )
    return keyboard

def in_chat_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("❌ Выйти из чата"), KeyboardButton("⚠️ Пожаловаться"))
    keyboard.add(KeyboardButton("👤 Профиль"))
    return keyboard

def admin_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📊 Общая статистика"), KeyboardButton("📋 Жалобы"))
    keyboard.add(KeyboardButton("📝 История чатов"), KeyboardButton("👥 Управление"))
    keyboard.add(KeyboardButton("💎 Выдать Premium"), KeyboardButton("📜 Список Premium"))
    keyboard.add(KeyboardButton("🔙 Выйти из админки"))
    return keyboard

# ==============================================
# КОМАНДЫ
# ==============================================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    global ADMIN_ID
    
    # Определяем ID админа при первом запуске
    if message.from_user.username == ADMIN_USERNAME:
        ADMIN_ID = user_id
        if str(user_id) not in ADMIN_IDS:
            ADMIN_IDS.append(str(user_id))
    
    profile = get_user_profile(user_id)
    profile["username"] = message.from_user.username
    users_data[str(user_id)]["state"] = "none"
    save_data(users_data)
    
    # Рефералка
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            inviter_id = args[1].split("_")[1]
            
            # Проверяем, что приглашающий существует
            if inviter_id in users_data:
                # Проверяем, что приглашенный - НОВЫЙ пользователь
                if str(user_id) not in users_data or users_data[str(user_id)].get("first_seen", 0) > time.time() - 10:
                    # Обрабатываем реферальный переход с защитой от накрутки
                    result, reason = process_referral(inviter_id, user_id)
                    
                    if result:
                        send_with_image(
                            message.chat.id,
                            "🎉 *Ты пришел по ссылке!*\n\n"
                            "Твой друг получил +2 часа Premium",
                            "ref"
                        )
                    else:
                        if reason == "self":
                            send_with_image(
                                message.chat.id,
                                "❌ *Нельзя пригласить самого себя*",
                                "warning"
                            )
                        elif reason == "already_invited":
                            send_with_image(
                                message.chat.id,
                                "❌ *Этот пользователь уже был приглашен*",
                                "warning"
                            )
                else:
                    send_with_image(
                        message.chat.id,
                        "🔙 *С возвращением!*",
                        "main"
                    )
            else:
                send_with_image(
                    message.chat.id,
                    "🎉 *Ты пришел по ссылке!*",
                    "ref"
                )
                
        except Exception as e:
            print(f"Ошибка рефералки: {e}")
            send_with_image(
                message.chat.id,
                "🎉 *Ты пришел по ссылке!*",
                "ref"
            )
    
    # Регистрация - если пол не указан, показываем клавиатуру выбора пола
    if profile.get("gender") is None:
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("👨 Парень", callback_data="reg_male"),
            InlineKeyboardButton("👩 Девушка", callback_data="reg_female")
        )
        send_with_image(
            message.chat.id,
            "👋 *Привет! Для использования бота нужно указать свой пол и возраст.*\n\nВыбери свой пол:",
            "register",
            reply_markup=keyboard
        )
        return
    
    # Если возраст не указан
    if profile.get("age") is None:
        users_data[str(user_id)]["state"] = "waiting_age"
        save_data(users_data)
        bot.send_message(message.chat.id, "📅 *Напиши свой возраст (от 11 до 99)*:", parse_mode='Markdown')
        return
    
    # Если всё заполнено - показываем главное меню
    send_with_image(
        message.chat.id,
        "🎭 *Анонимный чат*\n\nВыбери действие:",
        "main",
        reply_markup=main_keyboard()
    )

# Обработчик для всех сообщений (кроме /start и колбэков регистрации)
@bot.message_handler(func=lambda m: not profile_required(m) and m.text != '/start')
def force_profile(message):
    """Заставляет пользователя заполнить профиль"""
    user_id = str(message.from_user.id)
    
    # Проверяем, что именно не заполнено
    if user_id not in users_data or users_data[user_id].get("gender") is None:
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("👨 Парень", callback_data="reg_male"),
            InlineKeyboardButton("👩 Девушка", callback_data="reg_female")
        )
        send_with_image(
            message.chat.id,
            "❌ *Сначала нужно указать свой пол!*\n\nВыбери пол:",
            "register",
            reply_markup=keyboard
        )
    elif users_data[user_id].get("age") is None:
        users_data[user_id]["state"] = "waiting_age"
        save_data(users_data)
        bot.send_message(message.chat.id, "📅 *Напиши свой возраст (от 11 до 99)*:", parse_mode='Markdown')
    else:
        # Если всё ок (такого не должно быть, но на всякий случай)
        send_with_image(message.chat.id, "🎭 Добро пожаловать!", "main", reply_markup=main_keyboard())

@bot.message_handler(commands=['stop'])
def stop_search(message):
    user_id = str(message.from_user.id)
    if user_id in waiting_list:
        waiting_list.remove(user_id)
        users_data[user_id]["state"] = "none"
        users_data[user_id]["search_start_time"] = 0
        save_data(users_data)
        bot.send_message(message.chat.id, "⏹ *Поиск остановлен*", parse_mode='Markdown', 
                        reply_markup=main_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ Ты не в поиске")

@bot.message_handler(commands=['next'])
def next_chat(message):
    user_id = message.from_user.id
    leave_chat_by_id(user_id, notify=True)
    
    user_id_str = str(user_id)
    if user_id_str not in waiting_list:
        waiting_list.append(user_id_str)
        users_data[user_id_str]["state"] = "waiting"
        users_data[user_id_str]["search_start_time"] = time.time()
        save_data(users_data)
        
        send_with_image(
            message.chat.id,
            "🔍 *Ищем следующего...*\n/stop - отменить",
            "search"
        )
        try_find_pair()

@bot.message_handler(commands=['cancel'])
def cancel_story(message):
    """Отмена создания истории"""
    user_id = str(message.from_user.id)
    if users_data[user_id].get("state") == "adding_story":
        users_data[user_id]["state"] = "none"
        if "story_temp" in users_data[user_id]:
            del users_data[user_id]["story_temp"]
        save_data(users_data)
        bot.send_message(message.chat.id, "❌ Создание истории отменено", 
                        reply_markup=main_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ Нечего отменять")

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    user_id = m.from_user.id
    p = get_user_profile(user_id)
    reg = datetime.fromtimestamp(p["first_seen"]).strftime('%d.%m.%Y')
    r = p["reactions_received"]
    line = f"❤️ {r['❤️']}  🔥 {r['🔥']}  🥶 {r['🥶']}  💩 {r['💩']}"
    
    # Данные пользователя
    gender_text = "👨 Парень" if p.get("gender") == "male" else "👩 Девушка" if p.get("gender") == "female" else "Не указан"
    age_text = p.get("age", "Не указан")
    
    premium = "✅ Есть" if check_premium(user_id) else "❌ Нет"
    
    text = f"""
👻 *Твой профиль*

👤 Пол: {gender_text}
📅 Возраст: {age_text}
📅 Регистрация: {reg}
💬 Диалогов: {p['dialogs']}
📨 Сообщений: {p['messages_sent']}
👥 Приглашено: {p['invited_unique_count']} (уникальных)

🎭 *Реакции:* {line}

⭐ *Premium:* {premium}
    """
    
    send_with_image(m.chat.id, text, "profile", reply_markup=profile_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔍 НАЙТИ СОБЕСЕДНИКА")
def find(m):
    user_id = str(m.from_user.id)
    
    if users_data[user_id].get("state") == "chatting":
        bot.send_message(m.chat.id, "❌ Ты уже в чате! Используй /next")
        return
    
    if user_id in waiting_list:
        bot.send_message(m.chat.id, "🔍 *Ты уже в поиске!*\n/stop - отменить поиск", parse_mode='Markdown')
        return
    
    waiting_list.append(user_id)
    users_data[user_id]["state"] = "waiting"
    users_data[user_id]["search_start_time"] = time.time()
    save_data(users_data)
    
    f = users_data[user_id]["filters"]
    gender = "👨 Парень" if f["gender"] == "male" else "👩 Девушка" if f["gender"] == "female" else "⚪ Любой"
    
    send_with_image(
        m.chat.id,
        f"🔍 *Подбираем собеседника...*\n{gender}\n\n/stop - отменить поиск",
        "search"
    )
    try_find_pair()

@bot.message_handler(func=lambda m: m.text == "⚙️ Фильтр поиска")
def filters(m):
    user_id = str(m.from_user.id)
    f = users_data[user_id]["filters"]
    
    gender = "👨 Парень" if f["gender"] == "male" else "👩 Девушка" if f["gender"] == "female" else "⚪ Любой"
    age = ", ".join(f["age"]) if f["age"] else "любой"
    interests = ", ".join(f["interests"]) if f["interests"] else "нет"
    country = f["country"] if f["country"] != "any" else "любая"
    
    text = f"⚙️ *Фильтры*\n👤 {gender}\n📅 {age}\n🎯 {interests}\n🌍 {country}\n\nВыбери:"
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("👤 Пол", callback_data="f_gender"),
        InlineKeyboardButton("📅 Возраст", callback_data="f_age"),
        InlineKeyboardButton("🎯 Интересы", callback_data="f_interests"),
        InlineKeyboardButton("🌍 Страна", callback_data="f_country"),
        InlineKeyboardButton("❌ Сбросить", callback_data="f_reset")
    )
    
    send_with_image(m.chat.id, text, "filters", reply_markup=keyboard)

@bot.message_handler(func=lambda m: m.text == "⭐ Премиум")
def premium(m):
    p = get_user_profile(m.from_user.id)
    
    # АКЦИЯ: цены уменьшены вдвое
    text = f"""
╔════════════════╗
║     💎 PREMIUM  ║
╚════════════════╝

🎁 *АКЦИЯ К ОТКРЫТИЮ!* 
🔥 Все цены уменьшены в 2 раза!

🌟 *Преимущества PREMIUM:*
• 👤 Выбор пола собеседника
• 📅 Видеть возраст собеседника
• 🔄 Вернуть собеседника
• 🆓 *Бесплатное обнуление рейтинга*
• ⭐ И другие функции

💎 *Тарифы (АКЦИЯ!):*
⭐ 1 день — 35 ⭐
⭐ 5 дней — 100 ⭐
⭐ Месяц — 225 ⭐
💎 Навсегда — 500 ⭐

🆓 *Обнуление рейтинга без PREMIUM:*
💰 25 ⭐ за раз

🎁 *Бесплатный PREMIUM:* 
• +2 часа за друга
• 5 друзей = НЕДЕЛЯ PREMIUM!

👥 Приглашено: {p['invited_unique_count']}
🎯 До награды: {max(0, 5 - p['invited_unique_count'])} друзей
    """
    
    send_with_image(m.chat.id, text, "premium", reply_markup=premium_keyboard())

@bot.message_handler(func=lambda m: m.text == "🔝 Топ")
def top(m):
    users = []
    for uid, data in users_data.items():
        if uid.isdigit() and data.get("total_chat_time", 0) > 0:
            chat_time = data.get("total_chat_time", 0)
            hours = chat_time // 3600
            minutes = (chat_time % 3600) // 60
            time_str = f"{hours}ч {minutes}м"
            
            name = data.get("username")
            if not name:
                name = f"Аноним_{uid[-4:]}"
            users.append((uid, name, chat_time, time_str))
    
    users.sort(key=lambda x: x[2], reverse=True)
    
    prizes = ["7 дней Premium", "5 дней Premium", "3 дня Premium"]
    
    # Формируем текст для всех пользователей (БЕЗ Markdown)
    text = "🏆 ТОП ПОЛЬЗОВАТЕЛЕЙ\n\n"
    
    for i, (uid, name, chat_time, time_str) in enumerate(users[:10], 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} {name}\n⏱ {time_str}\n"
        if i <= 3:
            text += f"🎁 {prizes[i-1]}\n"
        text += "\n"
    
    # Отправляем всем без Markdown
    try:
        bot.send_message(m.chat.id, text)
    except Exception as e:
        print(f"Ошибка отправки топа: {e}")
    
    # Для админа отдельно отправляем ID (только если это админ)
    if str(m.from_user.id) in ADMIN_IDS:
        admin_text = "👑 ID ПОБЕДИТЕЛЕЙ\n\n"
        for i, (uid, name, chat_time, time_str) in enumerate(users[:3], 1):
            admin_text += f"{i}. {name}\n   ID: {uid}\n   ⏱ {time_str}\n\n"
        
        try:
            bot.send_message(m.chat.id, admin_text)
        except Exception as e:
            print(f"Ошибка отправки админского топа: {e}")

@bot.message_handler(func=lambda m: m.text == "📊 Статистика")
def stats(m):
    p = get_user_profile(m.from_user.id)
    r = p["reactions_received"]
    line = f"❤️ {r['❤️']}  🔥 {r['🔥']}  🥶 {r['🥶']}  💩 {r['💩']}"
    
    chat_time = p.get("total_chat_time", 0)
    hours = chat_time // 3600
    minutes = (chat_time % 3600) // 60
    time_str = f"{hours}ч {minutes}м"
    
    text = f"""
📊 *Статистика*

💬 Диалогов: {p['dialogs']}
📨 Сообщений: {p['messages_sent']}
⏱ Время в чатах: {time_str}
👥 Приглашено (уникальных): {p['invited_unique_count']}

🎭 {line}
    """
    
    send_with_image(m.chat.id, text, "stats")

@bot.message_handler(func=lambda m: m.text == "📸 Истории")
def stories_menu(m):
    """Главное меню историй"""
    user_id = m.from_user.id
    uid = str(user_id)
    
    current_time = time.time()
    
    all_stories = []
    my_stories = []
    
    for story_id, story in stories_data.items():
        if current_time - story["time"] <= 86400:
            all_stories.append(story_id)
            if story["user_id"] == uid:
                my_stories.append(story_id)
    
    # Очищаем старые истории
    for story_id in list(stories_data.keys()):
        if current_time - stories_data[story_id]["time"] > 86400:
            del stories_data[story_id]
    save_stories(stories_data)
    
    text = f"📸 *Анонимные истории*\n\n"
    text += f"📊 Всего историй: {len(all_stories)}\n"
    text += f"👤 Твоих историй: {len(my_stories)}\n"
    text += f"⏱ Исчезают через 24 часа\n\n"
    text += "📖 *Можно читать любые истории, даже свои!*\n"
    text += "👁 Просмотры считаются только в первый раз\n\n"
    text += "Выбери действие:"
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📝 Добавить историю", callback_data="story_add"),
        InlineKeyboardButton("👀 Читать историю", callback_data="story_read")
    )
    
    send_with_image(m.chat.id, text, "stories", reply_markup=keyboard)

@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help(m):
    text = """
❓ *Помощь*

🔍 Найти собеседника
👤 Профиль
⚙️ Фильтры
⭐ Премиум
🔝 Топ
📸 Истории

*В чате:*
/stop - выйти
/next - следующий

*Реферальная система:*
• За друга → +2 часа Premium
• 5 друзей → НЕДЕЛЯ Premium!
    """
    
    send_with_image(m.chat.id, text, "help")

@bot.message_handler(func=lambda m: m.text == "❌ Выйти из чата")
def leave(m):
    leave_chat_by_id(m.from_user.id)
    bot.send_message(m.chat.id, "✅ Ты вышел", reply_markup=main_keyboard())

@bot.message_handler(func=lambda m: m.text == "⚠️ Пожаловаться")
def report(m):
    user_id = str(m.from_user.id)
    for chat in active_chats.values():
        if chat["user1"] == user_id or chat["user2"] == user_id:
            partner = chat["user2"] if chat["user1"] == user_id else chat["user1"]
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("🤬 Маты", callback_data=f"rep_{partner}_swear"),
                InlineKeyboardButton("🔞 Порно", callback_data=f"rep_{partner}_porn"),
                InlineKeyboardButton("💔 Суицид", callback_data=f"rep_{partner}_suicide"),
                InlineKeyboardButton("📢 Спам", callback_data=f"rep_{partner}_spam"),
                InlineKeyboardButton("❌ Отмена", callback_data="rep_cancel")
            )
            send_with_image(m.chat.id, "👮 *Причина:*", "report", reply_markup=keyboard)
            return
    bot.send_message(m.chat.id, "❌ Ты не в чате")

# ==============================================
# АДМИНКА
# ==============================================

@bot.message_handler(func=lambda m: m.text and m.text.isdigit() and len(m.text) > 5)
def admin_login(m):
    user_id = str(m.from_user.id)
    if m.text == user_id:
        if user_id not in ADMIN_IDS:
            ADMIN_IDS.append(user_id)
        users_data[user_id]["state"] = "admin"
        save_data(users_data)
        bot.send_message(m.chat.id, "👑 *Админ-панель*", parse_mode='Markdown', 
                        reply_markup=admin_keyboard())

@bot.message_handler(func=lambda m: m.text == "📊 Общая статистика" and str(m.from_user.id) in ADMIN_IDS)
def admin_stats_general(m):
    total_users = len([u for u in users_data if u.isdigit()])
    premium_users = len([u for u in premium_data if check_premium(int(u))])
    active_now = len(active_chats) * 2 + len(waiting_list)
    
    # Статистика по рефералам
    users_with_5_plus = 0
    for uid, data in users_data.items():
        if uid.isdigit() and data.get("invited_unique_count", 0) >= 5:
            users_with_5_plus += 1
    
    text = f"""
👑 *ОБЩАЯ СТАТИСТИКА*

👥 Всего пользователей: {total_users}
⭐ Premium: {premium_users}
💬 Активных сейчас: {active_now}
🔄 В поиске: {len(waiting_list)}
💭 В чатах: {len(active_chats) * 2}

📊 *Рефералы:*
👥 Пригласили 5+ друзей: {users_with_5_plus}
    """
    bot.send_message(m.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📋 Жалобы" and str(m.from_user.id) in ADMIN_IDS)
def admin_reports(m):
    if "reports" not in users_data or not users_data["reports"]:
        bot.send_message(m.chat.id, "📭 Нет жалоб")
        return
    
    text = "🚨 *Жалобы*\n\n"
    for i, r in enumerate(users_data["reports"][-10:], 1):
        time = datetime.fromtimestamp(r["time"]).strftime('%H:%M %d.%m')
        text += f"{i}. От: {r['from_user']}\n   На: {r['on_user']}\n   {r['reason']} ({time})\n\n"
    
    bot.send_message(m.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📝 История чатов" and str(m.from_user.id) in ADMIN_IDS)
def admin_history_list(m):
    if not chat_messages:
        bot.send_message(m.chat.id, "📭 Нет истории чатов")
        return
    
    text = "📝 *ПОСЛЕДНИЕ ЧАТЫ*\n\n"
    for chat_id in list(chat_messages.keys())[-10:]:
        if chat_id in active_chats:
            status = "🟢 активен"
            users = f"{active_chats[chat_id]['user1'][:6]}... и {active_chats[chat_id]['user2'][:6]}..."
        else:
            status = "🔴 завершен"
            users = "неизвестно"
        
        msg_count = len(chat_messages.get(chat_id, []))
        media_count = sum(1 for m in chat_messages[chat_id] if m["type"] != 'text')
        
        text += f"`{chat_id}`\n"
        text += f"{users}\n"
        text += f"📊 Сообщений: {msg_count} | 🎬 Медиа: {media_count}\n"
        text += f"📁 Папка: `{chat_id}`\n"
        text += f"Статус: {status}\n\n"
    
    text += "\nДля просмотра: /history [id_чата]"
    bot.send_message(m.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "👥 Управление" and str(m.from_user.id) in ADMIN_IDS)
def admin_users_manage(m):
    text = """
👥 *УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ*

*Команды:*
/ban [id] - заблокировать
/unban [id] - разблокировать
/add_premium [id] [часы] - выдать Premium
/premium_forever [id] - вечный Premium

*Поиск:*
/find [username или id]
    """
    bot.send_message(m.chat.id, text, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "💎 Выдать Premium" and str(m.from_user.id) in ADMIN_IDS)
def admin_give_premium(m):
    bot.send_message(m.chat.id, 
        "💎 *Выдача Premium*\n\n/add_premium [id] [часы]\n/premium_forever [id]",
        parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "📜 Список Premium" and str(m.from_user.id) in ADMIN_IDS)
def admin_premium_list(m):
    premium_users = []
    for uid, data in premium_data.items():
        if uid in users_data:
            username = users_data[uid].get("username", "без имени")
            if data.get("forever"):
                premium_users.append(f"💎 {username} (ID: {uid}) - НАВСЕГДА")
            elif data.get("expiry", 0) > time.time():
                expiry = datetime.fromtimestamp(data["expiry"]).strftime('%d.%m.%Y %H:%M')
                premium_users.append(f"⭐ {username} (ID: {uid}) - до {expiry}")
    
    if not premium_users:
        bot.send_message(m.chat.id, "📭 Нет пользователей с Premium")
        return
    
    text = "💎 *ПОЛЬЗОВАТЕЛИ С PREMIUM*\n\n"
    text += "\n".join(premium_users)
    
    for i in range(0, len(text), 4000):
        bot.send_message(m.chat.id, text[i:i+4000], parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == "🔙 Выйти из админки" and str(m.from_user.id) in ADMIN_IDS)
def admin_exit(m):
    user_id = str(m.from_user.id)
    users_data[user_id]["state"] = "none"
    save_data(users_data)
    bot.send_message(m.chat.id, "✅ Вышел из админки", reply_markup=main_keyboard())

# ==============================================
# КОЛЛБЭКИ
# ==============================================

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    uid = str(user_id)
    data = call.data
    
    # ==============================================
    # РЕДАКТИРОВАНИЕ ПРОФИЛЯ
    # ==============================================
    
    if data == "edit_gender":
        current_gender = users_data[uid].get("gender", "none")
        
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("👨 Парень" + (" ✅" if current_gender == "male" else ""), callback_data="set_profile_gender_male"),
            InlineKeyboardButton("👩 Девушка" + (" ✅" if current_gender == "female" else ""), callback_data="set_profile_gender_female")
        )
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="profile_back"))
        
        edit_with_image(
            call.message,
            "👤 *Изменить пол*\n\nВыбери свой пол:",
            "profile",
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("set_profile_gender_"):
        new_gender = data.replace("set_profile_gender_", "")
        users_data[uid]["gender"] = new_gender
        save_data(users_data)
        
        current_gender = new_gender
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("👨 Парень" + (" ✅" if current_gender == "male" else ""), callback_data="set_profile_gender_male"),
            InlineKeyboardButton("👩 Девушка" + (" ✅" if current_gender == "female" else ""), callback_data="set_profile_gender_female")
        )
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="profile_back"))
        
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id, f"✅ Пол изменен")
        return
    
    if data == "edit_age":
        current_age = users_data[uid].get("age", 0)
        
        kb = InlineKeyboardMarkup(row_width=4)
        ages = list(range(11, 22)) + ["22+"]
        row = []
        for i, age in enumerate(ages):
            age_str = str(age)
            status = " ✅" if (age == current_age or (age == "22+" and current_age and current_age >= 22)) else ""
            btn = InlineKeyboardButton(f"{age}{status}", callback_data=f"set_profile_age_{age}")
            row.append(btn)
            if len(row) == 4 or i == len(ages)-1:
                kb.row(*row)
                row = []
        
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="profile_back"))
        
        edit_with_image(
            call.message,
            "📅 *Изменить возраст*\n\nВыбери свой возраст:",
            "profile",
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("set_profile_age_"):
        age_value = data.replace("set_profile_age_", "")
        
        if age_value == "22+":
            users_data[uid]["age"] = 22
        else:
            users_data[uid]["age"] = int(age_value)
        save_data(users_data)
        
        current_age = users_data[uid]["age"]
        
        kb = InlineKeyboardMarkup(row_width=4)
        ages = list(range(11, 22)) + ["22+"]
        row = []
        for i, age in enumerate(ages):
            age_str = str(age)
            status = " ✅" if (age == current_age or (age == "22+" and current_age >= 22)) else ""
            btn = InlineKeyboardButton(f"{age}{status}", callback_data=f"set_profile_age_{age}")
            row.append(btn)
            if len(row) == 4 or i == len(ages)-1:
                kb.row(*row)
                row = []
        
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="profile_back"))
        
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id, f"✅ Возраст изменен")
        return
    
    if data == "profile_back":
        p = users_data[uid]
        reg = datetime.fromtimestamp(p["first_seen"]).strftime('%d.%m.%Y')
        r = p["reactions_received"]
        line = f"❤️ {r['❤️']}  🔥 {r['🔥']}  🥶 {r['🥶']}  💩 {r['💩']}"
        
        gender_text = "👨 Парень" if p.get("gender") == "male" else "👩 Девушка" if p.get("gender") == "female" else "Не указан"
        age_text = p.get("age", "Не указан")
        
        premium = "✅ Есть" if check_premium(user_id) else "❌ Нет"
        
        text = f"""
👻 *Твой профиль*

👤 Пол: {gender_text}
📅 Возраст: {age_text}
📅 Регистрация: {reg}
💬 Диалогов: {p['dialogs']}
📨 Сообщений: {p['messages_sent']}
👥 Приглашено: {p['invited_unique_count']}

🎭 *Реакции:* {line}

⭐ *Premium:* {premium}
        """
        
        try:
            edit_with_image(call.message, text, "profile", reply_markup=profile_keyboard())
        except:
            send_with_image(user_id, text, "profile", reply_markup=profile_keyboard())
        bot.answer_callback_query(call.id)
        return
    
    # ==============================================
    # PREMIUM КНОПКИ - ПЕРЕХОД К ОПЛАТЕ (АКЦИЯ: ЦЕНЫ УМЕНЬШЕНЫ)
    # ==============================================
    
    if data in ["premium_day", "premium_5days", "premium_month", "premium_forever"]:
        names = {"premium_day": "1 день", "premium_5days": "5 дней", 
                "premium_month": "месяц", "premium_forever": "навсегда"}
        # АКЦИЯ: цены уменьшены вдвое
        stars = {"premium_day": 35, "premium_5days": 100, "premium_month": 225, "premium_forever": 500}
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton(f"⭐ Оплатить {stars[data]} звезд", callback_data=f"pay_premium_{data}"),
            InlineKeyboardButton("🔙 Назад", callback_data="premium_show")
        )
        
        try:
            edit_with_image(
                call.message,
                f"💎 *Premium {names[data]}*\n\n"
                f"💰 Стоимость (АКЦИЯ!): {stars[data]} ⭐\n\n"
                f"✨ *Преимущества:*\n"
                f"• Бесплатное обнуление рейтинга\n"
                f"• Выбор пола собеседника\n"
                f"• Информация о возрасте\n"
                f"• Функция вернуть собеседника\n\n"
                f"Нажми кнопку для оплаты:",
                "premium",
                reply_markup=keyboard
            )
        except:
            send_with_image(
                user_id,
                f"💎 *Premium {names[data]}*\n\n"
                f"💰 Стоимость (АКЦИЯ!): {stars[data]} ⭐\n\n"
                f"Нажми кнопку для оплаты:",
                "premium",
                reply_markup=keyboard
            )
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("pay_premium_"):
        plan = data.replace("pay_premium_", "")
        names = {"premium_day": "1 день", "premium_5days": "5 дней", 
                "premium_month": "месяц", "premium_forever": "навсегда"}
        # АКЦИЯ: цены уменьшены вдвое
        stars = {"premium_day": 35, "premium_5days": 100, "premium_month": 225, "premium_forever": 500}
        
        # Создаем массив с ценой
        prices = [LabeledPrice(label=f"Premium {names[plan]}", amount=stars[plan])]
        
        # Отправляем счет
        bot.send_invoice(
            user_id,
            title=f"⭐ Premium {names[plan]}",
            description=f"Доступ ко всем премиум-функциям на {names[plan]}",
            invoice_payload=f"premium_{plan}",
            provider_token="",
            currency="XTR",
            prices=prices,
            start_parameter="premium_payment"
        )
        
        bot.answer_callback_query(call.id)
        return
    
    # ==============================================
    # БЕСКОНЕЧНАЯ ПРОКРУТКА ИСТОРИЙ
    # ==============================================
    
    if data.startswith("story_next_"):
        current_story_id = data.replace("story_next_", "")
        current_time = time.time()
        
        available_stories = []
        for story_id, story in stories_data.items():
            if current_time - story["time"] <= 86400:
                available_stories.append(story_id)
        
        if not available_stories:
            send_with_image(
                user_id,
                "😴 *Нет историй*\n\nДобавь свою первую историю!",
                "stories",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("📝 Добавить историю", callback_data="story_add")
                )
            )
            bot.answer_callback_query(call.id)
            return
        
        if current_story_id in available_stories:
            current_index = available_stories.index(current_story_id)
            next_index = (current_index + 1) % len(available_stories)
            story_id = available_stories[next_index]
        else:
            story_id = random.choice(available_stories)
        
        story = stories_data[story_id]
        
        if "views" not in story:
            story["views"] = []
        
        is_first_view = user_id not in story["views"]
        if is_first_view:
            story["views"].append(user_id)
        save_stories(stories_data)
        
        story_time = datetime.fromtimestamp(story["time"]).strftime('%H:%M %d.%m')
        author = "Твоя история" if story["user_id"] == uid else "История"
        
        text = f"📖 *{author}*\n\n"
        text += f"_{story['text']}_\n\n"
        text += f"⏱ {story_time}\n"
        text += f"👁 Просмотров: {len(story.get('views', []))}"
        
        if is_first_view:
            text += f"\n✨ Это твой первый просмотр!"
        
        keyboard = InlineKeyboardMarkup(row_width=3)
        keyboard.add(
            InlineKeyboardButton("⏪ В меню", callback_data="story_back"),
            InlineKeyboardButton("▶️ Следующая", callback_data=f"story_next_{story_id}"),
            InlineKeyboardButton("📝 Добавить", callback_data="story_add")
        )
        
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
        
        if story.get("photo"):
            try:
                bot.send_photo(
                    user_id,
                    story["photo"],
                    caption=text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except:
                send_with_image(
                    user_id,
                    text + "\n\n❌ Фото не загрузилось",
                    "stories",
                    reply_markup=keyboard
                )
        else:
            send_with_image(
                user_id,
                text,
                "stories",
                reply_markup=keyboard
            )
        
        bot.answer_callback_query(call.id)
        return
    
    # ==============================================
    # АНОНИМНЫЕ ИСТОРИИ
    # ==============================================
    
    if data == "story_add":
        current_time = time.time()
        
        user_stories_today = 0
        for story in stories_data.values():
            if story["user_id"] == uid and current_time - story["time"] <= 86400:
                user_stories_today += 1
        
        if user_stories_today >= 3:
            bot.answer_callback_query(call.id, "❌ Максимум 3 истории в день!", show_alert=True)
            return
        
        users_data[uid]["state"] = "adding_story"
        users_data[uid]["story_temp"] = {}
        save_data(users_data)
        
        try:
            edit_with_image(
                call.message,
                "📝 *Добавление истории*\n\n"
                "Напиши текст истории (до 500 символов):\n"
                "Или /cancel для отмены",
                "stories"
            )
        except:
            send_with_image(
                user_id,
                "📝 *Добавление истории*\n\n"
                "Напиши текст истории (до 500 символов):\n"
                "Или /cancel для отмены",
                "stories"
            )
        bot.answer_callback_query(call.id)
        return

    elif data == "story_read":
        current_time = time.time()
        
        available_stories = []
        for story_id, story in stories_data.items():
            if current_time - story["time"] <= 86400:
                available_stories.append(story_id)
        
        if not available_stories:
            bot.answer_callback_query(call.id, "😴 Нет историй", show_alert=True)
            return
        
        story_id = random.choice(available_stories)
        story = stories_data[story_id]
        
        if "views" not in story:
            story["views"] = []
        
        is_first_view = user_id not in story["views"]
        if is_first_view:
            story["views"].append(user_id)
        save_stories(stories_data)
        
        story_time = datetime.fromtimestamp(story["time"]).strftime('%H:%M %d.%m')
        author = "Твоя история" if story["user_id"] == uid else "История"
        
        text = f"📖 *{author}*\n\n"
        text += f"_{story['text']}_\n\n"
        text += f"⏱ {story_time}\n"
        text += f"👁 Просмотров: {len(story.get('views', []))}"
        
        if is_first_view:
            text += f"\n✨ Это твой первый просмотр!"
        
        keyboard = InlineKeyboardMarkup(row_width=3)
        keyboard.add(
            InlineKeyboardButton("⏪ В меню", callback_data="story_back"),
            InlineKeyboardButton("▶️ Следующая", callback_data=f"story_next_{story_id}"),
            InlineKeyboardButton("📝 Добавить", callback_data="story_add")
        )
        
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
        
        if story.get("photo"):
            try:
                bot.send_photo(
                    user_id,
                    story["photo"],
                    caption=text,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
            except:
                send_with_image(
                    user_id,
                    text + "\n\n❌ Фото не загрузилось",
                    "stories",
                    reply_markup=keyboard
                )
        else:
            send_with_image(
                user_id,
                text,
                "stories",
                reply_markup=keyboard
            )
        
        bot.answer_callback_query(call.id)
        return

    elif data == "story_back":
        current_time = time.time()
        
        all_stories = []
        my_stories = []
        
        for story_id, story in stories_data.items():
            if current_time - story["time"] <= 86400:
                all_stories.append(story_id)
                if story["user_id"] == uid:
                    my_stories.append(story_id)
        
        for story_id in list(stories_data.keys()):
            if current_time - stories_data[story_id]["time"] > 86400:
                del stories_data[story_id]
        save_stories(stories_data)
        
        text = f"📸 *Анонимные истории*\n\n"
        text += f"📊 Всего историй: {len(all_stories)}\n"
        text += f"👤 Твоих историй: {len(my_stories)}\n"
        text += f"⏱ Исчезают через 24 часа\n\n"
        text += "📖 *Можно читать любые истории, даже свои!*\n"
        text += "👁 Просмотры считаются только в первый раз\n\n"
        text += "Выбери действие:"
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("📝 Добавить историю", callback_data="story_add"),
            InlineKeyboardButton("👀 Читать историю", callback_data="story_read")
        )
        
        try:
            bot.delete_message(user_id, call.message.message_id)
        except:
            pass
        
        send_with_image(
            user_id,
            text,
            "stories",
            reply_markup=keyboard
        )
        
        bot.answer_callback_query(call.id)
        return
    
    # Регистрация
    if data == "reg_male" or data == "reg_female":
        users_data[uid]["gender"] = "male" if data == "reg_male" else "female"
        save_data(users_data)
        bot.edit_message_text("📅 *Напиши возраст (11-99)*:", user_id, call.message.message_id,
                            parse_mode='Markdown')
        users_data[uid]["state"] = "waiting_age"
        save_data(users_data)
        bot.answer_callback_query(call.id)
        return
    
    # Реакции
    if data.startswith("react_"):
        parts = data.split("_")
        target = parts[1]
        react = parts[2]
        
        if target in users_data:
            users_data[target]["reactions_received"][react] += 1
            save_data(users_data)
            bot.answer_callback_query(call.id, f"✅ {react}")
            bot.edit_message_text(f"✅ Ты поставил {react}", user_id, call.message.message_id)
        return
    
    # Вернуть
    if data.startswith("return_"):
        target = data.replace("return_", "")
        if not check_premium(user_id):
            send_with_image(
                user_id,
                "🔒 *Нужен Premium*",
                "premium",
                reply_markup=premium_keyboard()
            )
            bot.answer_callback_query(call.id)
            return
        
        if target in users_data and users_data[target]["state"] == "none":
            chat_id = f"{uid}_{target}_{int(time.time())}"
            active_chats[chat_id] = {"user1": uid, "user2": target, "created_at": time.time()}
            
            users_data[uid]["state"] = "chatting"
            users_data[uid]["partner_id"] = target
            users_data[uid]["chat_id"] = chat_id
            
            users_data[target]["state"] = "chatting"
            users_data[target]["partner_id"] = uid
            users_data[target]["chat_id"] = chat_id
            save_data(users_data)
            
            bot.send_message(user_id, "✅ *Чат восстановлен*", parse_mode='Markdown',
                           reply_markup=in_chat_keyboard())
            bot.send_message(int(target), "🔄 *Собеседник вернулся*", parse_mode='Markdown',
                           reply_markup=in_chat_keyboard())
            bot.answer_callback_query(call.id, "✅ Ок")
        else:
            bot.answer_callback_query(call.id, "❌ Занят")
        return
    
    # Жалобы
    if data.startswith("rep_"):
        parts = data.split("_")
        target = parts[1]
        reason_code = parts[2]
        
        reasons = {"swear": "🤬 Маты", "porn": "🔞 Порно", "suicide": "💔 Суицид", "spam": "📢 Спам"}
        reason = reasons.get(reason_code, reason_code)
        
        if "reports" not in users_data:
            users_data["reports"] = []
        
        users_data["reports"].append({
            "from_user": uid, "on_user": target, "reason": reason, "time": time.time()
        })
        save_data(users_data)
        
        bot.answer_callback_query(call.id, "✅ Отправлено")
        bot.edit_message_text("✅ Жалоба отправлена", user_id, call.message.message_id)
        return
    
    if data == "rep_cancel":
        bot.edit_message_text("❌ Отменено", user_id, call.message.message_id)
        bot.answer_callback_query(call.id)
        return
    
    # Профиль
    if data == "my_stats":
        p = get_user_profile(user_id)
        r = p["reactions_received"]
        line = f"❤️ {r['❤️']}  🔥 {r['🔥']}  🥶 {r['🥶']}  💩 {r['💩']}"
        
        chat_time = p.get("total_chat_time", 0)
        hours = chat_time // 3600
        minutes = (chat_time % 3600) // 60
        time_str = f"{hours}ч {minutes}м"
        
        text = f"""
📊 *Подробная статистика*

💬 Диалогов: {p['dialogs']}
📨 Сообщений: {p['messages_sent']}
⏱ Время в чатах: {time_str}
👥 Приглашено (уникальных): {p['invited_unique_count']}

🎭 {line}
        """
        send_with_image(user_id, text, "stats")
        bot.answer_callback_query(call.id)
        return
    
    if data == "ref_link":
        p = get_user_profile(user_id)
        link = f"https://t.me/{bot.get_me().username}?start={p['ref_code']}"
        
        text = f"""
🔗 *Твоя реферальная ссылка*

`{link}`

👥 Приглашено уникальных: {p['invited_unique_count']}
⏱ Часов премиума: {p['invited_unique_count'] * 2}
🎯 До награды (5 друзей): {max(0, 5 - p['invited_unique_count'])} друзей
        """
        send_with_image(user_id, text, "ref")
        bot.answer_callback_query(call.id)
        return
    
    # Фильтры
    if data == "f_gender":
        if not check_premium(user_id):
            keyboard = InlineKeyboardMarkup(row_width=1)
            keyboard.add(
                InlineKeyboardButton("⭐ Купить Premium", callback_data="premium_show"),
                InlineKeyboardButton("🔙 Назад", callback_data="back_filters")
            )
            edit_with_image(
                call.message,
                "🔒 *Выбор пола доступен только с PREMIUM!*",
                "filters",
                reply_markup=keyboard
            )
            bot.answer_callback_query(call.id)
            return
        
        cur = users_data[uid]["filters"]["gender"]
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("👨 Парень" + (" ✅" if cur == "male" else ""), callback_data="set_gender_male"),
            InlineKeyboardButton("👩 Девушка" + (" ✅" if cur == "female" else ""), callback_data="set_gender_female"),
            InlineKeyboardButton("⚪ Любой" + (" ✅" if cur == "any" else ""), callback_data="set_gender_any")
        )
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_filters"))
        edit_with_image(
            call.message,
            "👤 *Пол для поиска* (PREMIUM)",
            "filters",
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("set_gender_"):
        if not check_premium(user_id):
            bot.answer_callback_query(call.id, "❌ Нужен Premium!")
            return
        
        g = data.replace("set_gender_", "")
        users_data[uid]["filters"]["gender"] = g
        save_data(users_data)
        
        cur = g
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("👨 Парень" + (" ✅" if cur == "male" else ""), callback_data="set_gender_male"),
            InlineKeyboardButton("👩 Девушка" + (" ✅" if cur == "female" else ""), callback_data="set_gender_female"),
            InlineKeyboardButton("⚪ Любой" + (" ✅" if cur == "any" else ""), callback_data="set_gender_any")
        )
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_filters"))
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id, f"✅ Пол фильтра: {'парень' if g=='male' else 'девушка' if g=='female' else 'любой'}")
        return
    
    if data == "f_age":
        ages = ["8-10", "11-13", "14-16", "17-19", "20-22", "22+"]
        cur = users_data[uid]["filters"]["age"]
        kb = InlineKeyboardMarkup(row_width=2)
        for a in ages:
            status = " ✅" if a in cur else ""
            kb.add(InlineKeyboardButton(f"{a}{status}", callback_data=f"set_age_{a}"))
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_filters"))
        edit_with_image(
            call.message,
            "📅 *Возраст для поиска*",
            "filters",
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("set_age_"):
        a = data.replace("set_age_", "")
        if a in users_data[uid]["filters"]["age"]:
            users_data[uid]["filters"]["age"].remove(a)
        else:
            users_data[uid]["filters"]["age"].append(a)
        save_data(users_data)
        
        ages = ["8-10", "11-13", "14-16", "17-19", "20-22", "22+"]
        cur = users_data[uid]["filters"]["age"]
        kb = InlineKeyboardMarkup(row_width=2)
        for a2 in ages:
            status = " ✅" if a2 in cur else ""
            kb.add(InlineKeyboardButton(f"{a2}{status}", callback_data=f"set_age_{a2}"))
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_filters"))
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id)
        return
    
    if data == "f_interests":
        ints = ["🎮 Игры", "🎬 Фильмы", "🎵 Музыка", "📚 Книги", "🐱 Животные", 
                "📱 Соц-сети", "💻 Программирование", "💕 Флирт", "📸 Обмен фото", "💬 Общая"]
        cur = users_data[uid]["filters"]["interests"]
        kb = InlineKeyboardMarkup(row_width=2)
        for i in ints:
            status = " ✅" if i in cur else ""
            kb.add(InlineKeyboardButton(f"{i}{status}", callback_data=f"set_int_{i}"))
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_filters"))
        edit_with_image(
            call.message,
            "🎯 *Интересы для поиска*",
            "filters",
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("set_int_"):
        i = data.replace("set_int_", "")
        if i in users_data[uid]["filters"]["interests"]:
            users_data[uid]["filters"]["interests"].remove(i)
        else:
            users_data[uid]["filters"]["interests"].append(i)
        save_data(users_data)
        
        ints = ["🎮 Игры", "🎬 Фильмы", "🎵 Музыка", "📚 Книги", "🐱 Животные", 
                "📱 Соц-сети", "💻 Программирование", "💕 Флирт", "📸 Обмен фото", "💬 Общая"]
        cur = users_data[uid]["filters"]["interests"]
        kb = InlineKeyboardMarkup(row_width=2)
        for i2 in ints:
            status = " ✅" if i2 in cur else ""
            kb.add(InlineKeyboardButton(f"{i2}{status}", callback_data=f"set_int_{i2}"))
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_filters"))
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id)
        return
    
    if data == "f_country":
        countries = ["🇷🇺 Россия", "🇺🇦 Украина", "🇰🇿 Казахстан", "🇵🇱 Польша", "🇧🇾 Беларусь", "🌍 Любая"]
        cur = users_data[uid]["filters"]["country"]
        kb = InlineKeyboardMarkup(row_width=2)
        for c in countries:
            if c == "🌍 Любая":
                txt = "🌍 Любая" + (" ✅" if cur == "any" else "")
                kb.add(InlineKeyboardButton(txt, callback_data="set_country_any"))
            else:
                txt = c + (" ✅" if cur == c else "")
                kb.add(InlineKeyboardButton(txt, callback_data=f"set_country_{c}"))
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_filters"))
        edit_with_image(
            call.message,
            "🌍 *Страна для поиска*",
            "filters",
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)
        return
    
    if data.startswith("set_country_"):
        c = data.replace("set_country_", "")
        if c == "any":
            users_data[uid]["filters"]["country"] = "any"
        else:
            users_data[uid]["filters"]["country"] = c
        save_data(users_data)
        
        countries = ["🇷🇺 Россия", "🇺🇦 Украина", "🇰🇿 Казахстан", "🇵🇱 Польша", "🇧🇾 Беларусь", "🌍 Любая"]
        cur = users_data[uid]["filters"]["country"]
        kb = InlineKeyboardMarkup(row_width=2)
        for c2 in countries:
            if c2 == "🌍 Любая":
                txt = "🌍 Любая" + (" ✅" if cur == "any" else "")
                kb.add(InlineKeyboardButton(txt, callback_data="set_country_any"))
            else:
                txt = c2 + (" ✅" if cur == c2 else "")
                kb.add(InlineKeyboardButton(txt, callback_data=f"set_country_{c2}"))
        kb.add(InlineKeyboardButton("🔙 Назад", callback_data="back_filters"))
        bot.edit_message_reply_markup(user_id, call.message.message_id, reply_markup=kb)
        bot.answer_callback_query(call.id, f"✅ {c}")
        return
    
    if data == "f_reset":
        users_data[uid]["filters"] = {"gender": "any", "age": [], "interests": [], "country": "any"}
        save_data(users_data)
        bot.answer_callback_query(call.id, "✅ Сброшено")
        filters(call.message)
        return
    
    if data == "back_filters":
        f = users_data[uid]["filters"]
        
        gender = "👨 Парень" if f["gender"] == "male" else "👩 Девушка" if f["gender"] == "female" else "⚪ Любой"
        age = ", ".join(f["age"]) if f["age"] else "любой"
        interests = ", ".join(f["interests"]) if f["interests"] else "нет"
        country = f["country"] if f["country"] != "any" else "любая"
        
        text = f"⚙️ *Фильтры*\n👤 {gender}\n📅 {age}\n🎯 {interests}\n🌍 {country}\n\nВыбери:"
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("👤 Пол", callback_data="f_gender"),
            InlineKeyboardButton("📅 Возраст", callback_data="f_age"),
            InlineKeyboardButton("🎯 Интересы", callback_data="f_interests"),
            InlineKeyboardButton("🌍 Страна", callback_data="f_country"),
            InlineKeyboardButton("❌ Сбросить", callback_data="f_reset")
        )
        
        edit_with_image(call.message, text, "filters", reply_markup=keyboard)
        bot.answer_callback_query(call.id)
        return
    
    if data == "premium_show":
        p = get_user_profile(user_id)
        text = f"""
╔════════════════╗
║     💎 PREMIUM  ║
╚════════════════╝

🎁 *АКЦИЯ К ОТКРЫТИЮ!* 
🔥 Все цены уменьшены в 2 раза!

🌟 *Преимущества:*
• Выбор пола собеседника
• Возраст и данные собеседника
• Вернуть собеседника
• Обнуление рейтинга

💎 *Тарифы (АКЦИЯ!):*
⭐ 1 день — 35 ⭐
⭐ 5 дней — 100 ⭐
⭐ Месяц — 225 ⭐
💎 Навсегда — 500 ⭐

🎁 *Бесплатно:* 
• +2 часа за друга
• 5 друзей = НЕДЕЛЯ PREMIUM!

👥 Приглашено: {p['invited_unique_count']}
🎯 До награды: {max(0, 5 - p['invited_unique_count'])} друзей
        """
        try:
            edit_with_image(call.message, text, "premium", reply_markup=premium_keyboard())
        except:
            send_with_image(user_id, text, "premium", reply_markup=premium_keyboard())
        bot.answer_callback_query(call.id)
        return
    
    # Premium - Обнуление рейтинга
    if data == "premium_reset":
        has_premium = check_premium(user_id)
        
        if has_premium:
            users_data[uid]["reactions_received"] = {"❤️": 0, "🔥": 0, "🥶": 0, "💩": 0}
            save_data(users_data)
            bot.send_message(
                user_id, 
                "✅ *Рейтинг успешно обнулен!*\n\n"
                "Твои реакции сброшены до нуля.",
                parse_mode='Markdown'
            )
            bot.answer_callback_query(call.id, "✅ Рейтинг обнулен")
        else:
            # Отправляем счет на 25 звезд (АКЦИЯ)
            prices = [LabeledPrice(label="Обнуление рейтинга", amount=25)]
            
            bot.send_invoice(
                user_id,
                title="⭐ Обнуление рейтинга",
                description="Сбросить все полученные реакции до нуля",
                invoice_payload="premium_reset",
                provider_token="",
                currency="XTR",
                prices=prices,
                start_parameter="reset_payment"
            )
            bot.answer_callback_query(call.id)
        return
    
    if data == "free_premium":
        p = get_user_profile(user_id)
        link = f"https://t.me/{bot.get_me().username}?start={p['ref_code']}"
        
        text = f"""
🎁 *Бесплатный Premium*

• Пригласи друга → +2 часа Premium
• 5 друзей → НЕДЕЛЯ Premium!

🔗 `{link}`

👥 Приглашено уникальных: {p['invited_unique_count']}
⏱ Часов премиума: {p['invited_unique_count'] * 2}
🎯 До награды (5 друзей): {max(0, 5 - p['invited_unique_count'])} друзей
        """
        send_with_image(user_id, text, "ref")
        bot.answer_callback_query(call.id)
        return

# ==============================================
# ОБРАБОТЧИКИ ПЛАТЕЖЕЙ
# ==============================================

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout(pre_checkout_query):
    """Подтверждение платежа перед списанием"""
    try:
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
        print(f"✅ Платеж подтвержден: {pre_checkout_query.id}")
    except Exception as e:
        print(f"❌ Ошибка подтверждения платежа: {e}")
        bot.answer_pre_checkout_query(
            pre_checkout_query.id, 
            ok=False, 
            error_message="Произошла ошибка. Попробуйте позже."
        )

@bot.message_handler(content_types=['successful_payment'])
def handle_successful_payment(message):
    """Обработка успешного платежа"""
    user_id = message.from_user.id
    uid = str(user_id)
    payload = message.successful_payment.invoice_payload
    
    print(f"💰 Успешный платеж: {payload} от пользователя {user_id}")
    
    if payload == "premium_premium_day":
        result = add_premium_hours(user_id, 24)
        duration_text = f"до {datetime.fromtimestamp(result).strftime('%d.%m.%Y %H:%M')}"
        bot.send_message(
            user_id,
            f"✅ *Оплата принята!*\n\n"
            f"💎 Premium 1 день активирован!\n"
            f"📅 Действует: {duration_text}",
            parse_mode='Markdown'
        )
        
    elif payload == "premium_premium_5days":
        result = add_premium_hours(user_id, 120)
        duration_text = f"до {datetime.fromtimestamp(result).strftime('%d.%m.%Y %H:%M')}"
        bot.send_message(
            user_id,
            f"✅ *Оплата принята!*\n\n"
            f"💎 Premium 5 дней активирован!\n"
            f"📅 Действует: {duration_text}",
            parse_mode='Markdown'
        )
        
    elif payload == "premium_premium_month":
        result = add_premium_hours(user_id, 720)
        duration_text = f"до {datetime.fromtimestamp(result).strftime('%d.%m.%Y %H:%M')}"
        bot.send_message(
            user_id,
            f"✅ *Оплата принята!*\n\n"
            f"💎 Premium месяц активирован!\n"
            f"📅 Действует: {duration_text}",
            parse_mode='Markdown'
        )
        
    elif payload == "premium_premium_forever":
        premium_data[uid] = {
            "expiry": 0,
            "forever": True
        }
        save_premium(premium_data)
        bot.send_message(
            user_id,
            f"✅ *Оплата принята!*\n\n"
            f"💎 Premium навсегда активирован!",
            parse_mode='Markdown'
        )
        
    elif payload == "premium_reset":
        users_data[uid]["reactions_received"] = {"❤️": 0, "🔥": 0, "🥶": 0, "💩": 0}
        save_data(users_data)
        bot.send_message(
            user_id,
            "✅ *Оплата принята!*\n\n"
            "Твой рейтинг успешно обнулен.",
            parse_mode='Markdown'
        )

# ==============================================
# АДМИН-КОМАНДЫ
# ==============================================

@bot.message_handler(commands=['add_premium', 'addrPremium', 'addpremium'])
def cmd_add_premium(m):
    user_id = str(m.from_user.id)
    
    if user_id not in ADMIN_IDS:
        bot.reply_to(m, "❌ У тебя нет прав админа")
        return
    
    parts = m.text.split()
    if len(parts) < 3:
        bot.reply_to(m, "❌ Использование: /add_premium [id] [часы]\nПример: /add_premium 5033681321 24")
        return
    
    try:
        target = parts[1]
        hours = int(parts[2])
        
        if target not in users_data:
            bot.reply_to(m, f"❌ Пользователь с ID {target} не найден")
            return
        
        result = add_premium_hours(target, hours)
        
        if result:
            bot.reply_to(
                m, 
                f"✅ Premium на {hours}ч успешно выдан пользователю {target}\n"
                f"📅 Действует до: {datetime.fromtimestamp(result).strftime('%d.%m.%Y %H:%M')}"
            )
            
            try:
                bot.send_message(
                    int(target), 
                    f"🎁 *Тебе выдан PREMIUM на {hours} часов!*\n\n"
                    f"📅 Действует до: {datetime.fromtimestamp(result).strftime('%d.%m.%Y %H:%M')}\n\n"
                    f"🔥 ТЕПЕРЬ ТЕБЕ ДОСТУПНО:\n"
                    f"• Выбор пола собеседника\n"
                    f"• Информация о возрасте собеседника\n"
                    f"• Функция вернуть собеседника\n"
                    f"• Обнуление рейтинга",
                    parse_mode='Markdown'
                )
                bot.reply_to(m, f"✅ Пользователь {target} уведомлен")
            except Exception as e:
                bot.reply_to(m, f"⚠️ Премиум выдан, но не удалось уведомить пользователя: {e}")
        else:
            bot.reply_to(m, "❌ Ошибка при выдаче премиума")
            
    except ValueError:
        bot.reply_to(m, "❌ Часы должны быть числом")
    except Exception as e:
        bot.reply_to(m, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['premium_forever', 'premiumforever'])
def cmd_premium_forever(m):
    user_id = str(m.from_user.id)
    
    if user_id not in ADMIN_IDS:
        bot.reply_to(m, "❌ У тебя нет прав админа")
        return
    
    parts = m.text.split()
    if len(parts) < 2:
        bot.reply_to(m, "❌ Использование: /premium_forever [id]\nПример: /premium_forever 5033681321")
        return
    
    target = parts[1]
    
    if target not in users_data:
        bot.reply_to(m, f"❌ Пользователь с ID {target} не найден")
        return
    
    try:
        premium_data[target] = {
            "expiry": 0,
            "forever": True
        }
        save_premium(premium_data)
        
        bot.reply_to(
            m, 
            f"✅ Вечный PREMIUM успешно выдан пользователю {target}\n"
            f"💎 Действует: НАВСЕГДА"
        )
        
        try:
            bot.send_message(
                int(target), 
                f"💎 *Тебе выдан ВЕЧНЫЙ PREMIUM!*\n\n"
                f"🔥 ТЕПЕРЬ ТЕБЕ ДОСТУПНО:\n"
                f"• Выбор пола собеседника\n"
                f"• Информация о возрасте собеседника\n"
                f"• Функция вернуть собеседника\n"
                f"• Обнуление рейтинга",
                parse_mode='Markdown'
            )
            bot.reply_to(m, f"✅ Пользователь {target} уведомлен")
        except Exception as e:
            bot.reply_to(m, f"⚠️ Премиум выдан, но не удалось уведомить пользователя: {e}")
            
    except Exception as e:
        bot.reply_to(m, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['ban'])
def cmd_ban(m):
    user_id = str(m.from_user.id)
    if user_id not in ADMIN_IDS:
        return
    
    parts = m.text.split()
    if len(parts) < 2:
        bot.send_message(m.chat.id, "❌ /ban [id]")
        return
    
    target = parts[1]
    if target in users_data:
        users_data[target]["banned"] = True
        save_data(users_data)
        bot.send_message(m.chat.id, f"✅ {target} заблокирован")
        try:
            bot.send_message(int(target), "🚫 Ты заблокирован")
        except:
            pass

@bot.message_handler(commands=['unban'])
def cmd_unban(m):
    user_id = str(m.from_user.id)
    if user_id not in ADMIN_IDS:
        return
    
    parts = m.text.split()
    if len(parts) < 2:
        bot.send_message(m.chat.id, "❌ /unban [id]")
        return
    
    target = parts[1]
    if target in users_data:
        users_data[target]["banned"] = False
        save_data(users_data)
        bot.send_message(m.chat.id, f"✅ {target} разблокирован")

@bot.message_handler(commands=['find'])
def cmd_find(m):
    user_id = str(m.from_user.id)
    if user_id not in ADMIN_IDS:
        return
    
    parts = m.text.split()
    if len(parts) < 2:
        bot.send_message(m.chat.id, "❌ /find [username или id]")
        return
    
    query = parts[1].lower()
    
    found = []
    for uid, data in users_data.items():
        if uid.isdigit():
            if query in uid or (data.get("username") and query in data["username"].lower()):
                username = data.get("username", "нет username")
                banned = "🚫" if data.get("banned") else "✅"
                premium = "⭐" if check_premium(int(uid)) else "❌"
                dialogs = data.get("dialogs", 0)
                invited = data.get("invited_unique_count", 0)
                found.append(f"{banned}{premium} {username} (ID: {uid}) - {dialogs} диалогов, пригласил: {invited}")
    
    if not found:
        bot.send_message(m.chat.id, "❌ Ничего не найдено")
        return
    
    text = "🔍 *РЕЗУЛЬТАТЫ ПОИСКА*\n\n"
    text += "\n".join(found[:20])
    bot.send_message(m.chat.id, text, parse_mode='Markdown')

@bot.message_handler(commands=['history'])
def cmd_history(m):
    user_id = str(m.from_user.id)
    if user_id not in ADMIN_IDS:
        return
    
    parts = m.text.split()
    if len(parts) < 2:
        bot.send_message(m.chat.id, "❌ /history [id_чата]\n\nСписок чатов в 'История чатов'")
        return
    
    chat_id = parts[1]
    if chat_id not in chat_messages:
        bot.send_message(m.chat.id, "❌ Чат не найден")
        return
    
    chat_media_dir = os.path.join(MEDIA_DIR, chat_id)
    
    text = f"📝 *ИСТОРИЯ ЧАТА {chat_id}*\n\n"
    text += f"📁 Медиафайлы сохранены в: `{chat_media_dir}`\n\n"
    
    for msg in chat_messages[chat_id][-100:]:
        time_str = datetime.fromtimestamp(msg["timestamp"]).strftime('%H:%M:%S')
        sender = msg["sender"][:6] + "..."
        
        if msg["type"] == "text":
            content = msg.get("content", "")[:100]
            text += f"📝 [{time_str}] {sender}: {content}\n"
        else:
            filepath = msg.get("filepath", "не сохранен")
            filename = os.path.basename(filepath) if filepath != "не сохранен" else "не сохранен"
            text += f"🎬 [{time_str}] {sender}: [{msg['type']}] - {filename}\n"
    
    for i in range(0, len(text), 4000):
        bot.send_message(m.chat.id, text[i:i+4000], parse_mode='Markdown')
    
    if os.path.exists(chat_media_dir):
        files = os.listdir(chat_media_dir)
        if files:
            media_text = f"📸 *МЕДИАФАЙЛЫ ЧАТА*\n\nВсего файлов: {len(files)}\n"
            bot.send_message(m.chat.id, media_text, parse_mode='Markdown')

@bot.message_handler(commands=['addrPremium'])
def cmd_add_premium_alt(m):
    m.text = m.text.replace('/addrPremium', '/add_premium')
    cmd_add_premium(m)

# ==============================================
# ОБРАБОТЧИК СООБЩЕНИЙ
# ==============================================

@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'video_note', 'document', 'audio', 'voice', 'sticker'])
def handle_all(m):
    user_id = m.from_user.id
    uid = str(user_id)
    
    if uid not in users_data:
        start(m)
        return
    
    if users_data[uid].get("banned"):
        bot.reply_to(m, "🚫 Ты заблокирован")
        return
    
    # Добавление истории
    if users_data[uid].get("state") == "adding_story":
        if m.text == '/cancel':
            users_data[uid]["state"] = "none"
            if "story_temp" in users_data[uid]:
                del users_data[uid]["story_temp"]
            save_data(users_data)
            bot.reply_to(m, "❌ Отменено", reply_markup=main_keyboard())
            return
        
        if "story_text" in users_data[uid].get("story_temp", {}):
            if m.content_type == 'photo':
                story_text = users_data[uid]["story_temp"]["story_text"]
                photo_id = m.photo[-1].file_id
                
                story_id = f"story_{int(time.time())}_{uid}_{random.randint(1000, 9999)}"
                
                stories_data[story_id] = {
                    "user_id": uid,
                    "text": story_text,
                    "photo": photo_id,
                    "time": time.time(),
                    "views": []
                }
                save_stories(stories_data)
                
                users_data[uid]["state"] = "none"
                del users_data[uid]["story_temp"]
                save_data(users_data)
                
                bot.reply_to(
                    m, 
                    "✅ *История опубликована!*\n\n"
                    "Она будет доступна 24 часа",
                    parse_mode='Markdown',
                    reply_markup=main_keyboard()
                )
            elif m.content_type == 'text' and m.text.lower() in ['пропустить', '-', 'нет', 'skip']:
                story_text = users_data[uid]["story_temp"]["story_text"]
                
                story_id = f"story_{int(time.time())}_{uid}_{random.randint(1000, 9999)}"
                
                stories_data[story_id] = {
                    "user_id": uid,
                    "text": story_text,
                    "photo": None,
                    "time": time.time(),
                    "views": []
                }
                save_stories(stories_data)
                
                users_data[uid]["state"] = "none"
                del users_data[uid]["story_temp"]
                save_data(users_data)
                
                bot.reply_to(
                    m, 
                    "✅ *История опубликована!*\n\n"
                    "Она будет доступна 24 часа",
                    parse_mode='Markdown',
                    reply_markup=main_keyboard()
                )
            else:
                bot.reply_to(
                    m,
                    "📸 *Отправь фото* или напиши 'пропустить' чтобы опубликовать без фото\n"
                    "Или /cancel для отмены",
                    parse_mode='Markdown'
                )
            return
        
        if m.content_type == 'text':
            story_text = m.text.strip()
            
            if len(story_text) > 500:
                bot.reply_to(m, "❌ Текст слишком длинный! Максимум 500 символов.")
                return
            
            if len(story_text) < 10:
                bot.reply_to(m, "❌ Слишком коротко! Напиши хотя бы 10 символов.")
                return
            
            if "story_temp" not in users_data[uid]:
                users_data[uid]["story_temp"] = {}
            users_data[uid]["story_temp"]["story_text"] = story_text
            save_data(users_data)
            
            bot.reply_to(
                m,
                "📸 *Отлично!*\n\n"
                "Теперь можешь отправить фото к истории (необязательно)\n"
                "Или напиши 'пропустить' чтобы опубликовать без фото",
                parse_mode='Markdown'
            )
        else:
            bot.reply_to(m, "❌ Сначала отправь текст истории (до 500 символов)")
        return
    
    # Ввод возраста
    if users_data[uid].get("state") == "waiting_age":
        if m.content_type != 'text':
            bot.reply_to(m, "❌ Напиши число")
            return
        
        try:
            age = int(m.text)
            if 11 <= age <= 99:
                users_data[uid]["age"] = age
                users_data[uid]["state"] = "none"
                save_data(users_data)
                bot.reply_to(m, "✅ *Готово!*", parse_mode='Markdown', reply_markup=main_keyboard())
            else:
                bot.reply_to(m, "❌ От 11 до 99")
        except:
            bot.reply_to(m, "❌ Введи число")
        return
    
    # В поиске
    if uid in waiting_list:
        bot.reply_to(m, "🔍 Ты в поиске. /stop - отменить")
        return
    
    # В админке - игнорируем обычные сообщения
    if users_data[uid].get("state") == "admin":
        return
    
    # В чате
    for chat_id, chat in active_chats.items():
        if chat["user1"] == uid or chat["user2"] == uid:
            partner = chat["user2"] if chat["user1"] == uid else chat["user1"]
            
            users_data[uid]["messages_sent"] += 1
            save_data(users_data)
            
            if chat_id not in chat_messages:
                chat_messages[chat_id] = []
            
            msg_data = {
                "sender": uid, 
                "type": m.content_type, 
                "timestamp": time.time(),
                "filepath": None
            }
            
            if m.content_type == 'text':
                msg_data["content"] = m.text
                bot.send_message(int(partner), m.text)
                
            elif m.content_type == 'photo':
                file_id = m.photo[-1].file_id
                msg_data["content"] = file_id
                filepath = save_media_file(file_id, 'photo', chat_id, uid)
                msg_data["filepath"] = filepath
                bot.send_photo(int(partner), file_id)
                
            elif m.content_type == 'video':
                file_id = m.video.file_id
                msg_data["content"] = file_id
                filepath = save_media_file(file_id, 'video', chat_id, uid)
                msg_data["filepath"] = filepath
                bot.send_video(int(partner), file_id)
                
            elif m.content_type == 'video_note':
                file_id = m.video_note.file_id
                msg_data["content"] = file_id
                msg_data["type"] = 'video_note'
                filepath = save_media_file(file_id, 'video_note', chat_id, uid)
                msg_data["filepath"] = filepath
                bot.send_video_note(int(partner), file_id)
                
            elif m.content_type == 'voice':
                file_id = m.voice.file_id
                msg_data["content"] = file_id
                filepath = save_media_file(file_id, 'voice', chat_id, uid)
                msg_data["filepath"] = filepath
                bot.send_voice(int(partner), file_id)
                
            elif m.content_type == 'sticker':
                file_id = m.sticker.file_id
                msg_data["content"] = file_id
                filepath = save_media_file(file_id, 'sticker', chat_id, uid)
                msg_data["filepath"] = filepath
                bot.send_sticker(int(partner), file_id)
                
            elif m.content_type == 'document':
                file_id = m.document.file_id
                msg_data["content"] = file_id
                msg_data["file_name"] = m.document.file_name
                filepath = save_media_file(file_id, 'document', chat_id, uid)
                msg_data["filepath"] = filepath
                bot.send_document(int(partner), file_id)
            
            chat_messages[chat_id].append(msg_data)
            return
    
    # Не в чате и не в поиске
    bot.reply_to(m, "ℹ️ Используй кнопки", reply_markup=main_keyboard())

# ==============================================
# ЗАПУСК
# ==============================================

if __name__ == '__main__':
    print("╔════════════════════════╗")
    print("║   🤖 БОТ ЗАПУЩЕН       ║")
    print("╚════════════════════════╝")
    print(f"👤 Админ: @{ADMIN_USERNAME}")
    print(f"📁 Данные: {APP_DATA_DIR}")
    
    cleanup_old_stories()
    
    for uid, data in users_data.items():
        if uid.isdigit() and data.get("username") == ADMIN_USERNAME:
            ADMIN_IDS.append(uid)
            ADMIN_ID = int(uid)
            print(f"👑 Админ ID: {uid}")
    
    print("\n🔥 АКЦИЯ К ОТКРЫТИЮ: Все цены уменьшены в 2 раза!")
    print("🎁 Новая механика: 5 друзей = неделя Premium!")
    print("🛡 Защита от накрутки рефералов активирована!")
    
    bot.infinity_polling()