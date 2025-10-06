# name: MaxliAFK
# version: 1.0.0
# developer: @YouRooni (Maxli Dev)
# id: maxli_afk
# min-maxli: 30
 
import time
from core.config import get_module_setting, register_module_settings

# --- Глобальные переменные ---
IS_AFK = False
AFK_REASON = ""
AFK_START_TIME = 0
LAST_NOTIFIED = {}
MODULE_ID = "maxli_afk"

# --- Настройка модуля ---
register_module_settings(MODULE_ID, {
    "afk_message": {
        "default": "Я сейчас AFK.\nПричина: {reason}\nОтсутствую уже: {duration}",
        "description": "Шаблон AFK сообщения. Доступные переменные: {reason}, {duration}."
    },
    "timeout": {
        "default": 300,
        "description": "Таймаут (в секундах) для повторной отправки AFK сообщения в одном чате."
    }
})


def format_duration(seconds):
    seconds = int(seconds)
    if seconds < 60: return f"{seconds} сек."
    minutes, secs = divmod(seconds, 60)
    if minutes < 60: return f"{minutes} мин. {secs} сек."
    hours, minutes = divmod(minutes, 60)
    return f"{hours} ч. {minutes} мин."


async def afk_command(api, message, args):
    """Включить режим AFK."""
    global IS_AFK, AFK_REASON, AFK_START_TIME, LAST_NOTIFIED
    reason = " ".join(args) if args else "без причины"
    IS_AFK = True
    AFK_REASON = reason
    AFK_START_TIME = time.time()
    LAST_NOTIFIED.clear()
    await api.edit(message, f"✅ Режим AFK включен.\nПричина: {reason}")


async def unafk_command(api, message, args):
    """Выключить режим AFK."""
    global IS_AFK
    if not IS_AFK:
        await api.edit(message, "ℹ️ Вы и так не в режиме AFK.")
        return
    duration = format_duration(time.time() - AFK_START_TIME)
    IS_AFK = False
    await api.edit(message, f"✅ Режим AFK выключен. Вы отсутствовали: {duration}")


async def afk_watcher(api, message):
    """Обрабатывает все сообщения для автоответа в режиме AFK."""
    if not IS_AFK: return

    sender_id = getattr(message, "sender", None)
    if not sender_id: return

    my_id = str(getattr(api.me, "id", "-1"))
    if str(sender_id) == my_id: return

    chat_id = getattr(message, 'chat_id', None)
    if not chat_id: chat_id = await api.await_chat_id(message)
    if not chat_id: return
    
    # 1. Проверяем, является ли чат личными сообщениями (chat_id > 0)
    is_pm = int(chat_id) > 0
    
    # 2. Проверяем, является ли сообщение ответом на наше сообщение
    is_reply_to_me = False
    reply_info = getattr(message, 'reply_to_message', None)
    if isinstance(reply_info, dict): # Убеждаемся, что это словарь
        # --- ФИНАЛЬНОЕ ИСПРАВЛЕНИЕ ---
        # Используем .get() для словаря вместо getattr()
        reply_sender_id = reply_info.get('sender')
        if reply_sender_id and str(reply_sender_id) == my_id:
            is_reply_to_me = True

    # 3. Проверяем, упомянули ли нас по имени в групповом чате
    message_text = getattr(message, "text", "") or ""
    my_name = getattr(api.me, "name", " अनोळखी ")
    is_mentioned = (not is_pm) and (my_name.lower() in message_text.lower())

    # Срабатываем, если это ЛС, ИЛИ ответ нам, ИЛИ упоминание.
    if not (is_pm or is_reply_to_me or is_mentioned):
        return

    timeout = int(get_module_setting(MODULE_ID, "timeout", 300))
    current_time = time.time()
    
    if current_time - LAST_NOTIFIED.get(chat_id, 0) < timeout: return

    duration = format_duration(current_time - AFK_START_TIME)
    template = get_module_setting(MODULE_ID, "afk_message")
    reply_text = template.format(reason=AFK_REASON, duration=duration)
    
    await api.reply(message, reply_text)
    
    LAST_NOTIFIED[chat_id] = current_time


async def register(api):
    api.register_command("afk", afk_command)
    api.register_command("unafk", unafk_command)
    api.register_watcher(afk_watcher)
