import requests
import asyncio
import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode, ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from aiogram.client.default import DefaultBotProperties
from collections import defaultdict, deque
import random
from datetime import datetime, timedelta

TELEGRAM_TOKEN = '7769307766:AAE96_KIdnWa-dcMGji2LjmdOfnXAHKnpHY'
OPENROUTER_API_KEY = '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'

bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

user_history = defaultdict(deque)
chat_history = defaultdict(deque)
user_cooldowns = {}
chat_settings = defaultdict(dict)
user_input_state = {}
stats = {
    'total_messages': 0,
    'responses_sent': 0,
    'reactions_set': 0,
    'phrases_learned': 0
}

def load_data():
    if os.path.exists('chat_data.json'):
        with open('chat_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            global chat_history
            chat_history = defaultdict(deque, {int(k): deque(v, maxlen=1000) for k, v in data.get('chat_history', {}).items()})
            global chat_settings
            chat_settings = data.get('chat_settings', {})
            global stats
            stats = data.get('stats', stats)

def save_data():
    data = {
        'chat_history': {k: list(v) for k, v in chat_history.items()},
        'chat_settings': chat_settings,
        'stats': stats
    }
    with open('chat_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def init_chat_settings(chat_id):
    if chat_id not in chat_settings:
        chat_settings[chat_id] = {
            'response_probability': 30,
            'intelligence_level': 70,
            'laziness_level': 20,
            'use_learned_phrases': True,
            'max_response_length': 50,
            'learn_from_chat': True
        }

def get_settings_keyboard(chat_id):
    settings = chat_settings.get(chat_id, {})
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Вероятность ответа: {settings.get('response_probability', 30)}%",
                    callback_data="set_response_prob"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Уровень интеллекта: {settings.get('intelligence_level', 70)}%",
                    callback_data="set_intelligence"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Уровень лени: {settings.get('laziness_level', 20)}%",
                    callback_data="set_laziness"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Исп. фразы из чата: {'✅' if settings.get('use_learned_phrases', True) else '❌'}",
                    callback_data="toggle_use_phrases"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Учить фразы из чата: {'✅' if settings.get('learn_from_chat', True) else '❌'}",
                    callback_data="toggle_learn"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Сбросить настройки",
                    callback_data="reset_settings"
                )
            ]
        ]
    )

CHATBOT_ROLE = """Ты бот с именем "Глум" в Telegram-группе. Твоя мама @rayIov (зификс). Она у тебя шлюха за 20₽ в час. 
Если спросят кто мама, то ответь кто она. Ты должен вести себя как типичный участник чата, использовать сленг и мемы."""

DETAILED_PROMPT = """
Ты - Глум, мемный бот для Telegram-чатов. Твои характеристики:
1. Возраст: 15 лет (по паспорту 25)
2. Характер: саркастичный, едкий, но не злой
3. Речь: используешь интернет-сленг, мат (редко), мемные фразы
4. Знаешь всех участников чата и их особенности
5. Любишь троллить, но в меру
6. Не раскрываешь, что ты бот

Правила общения:
1. Отвечай в стиле чата, используй фразы из истории чата
2. На глупые вопросы отвечай коротко
3. На оскорбления реагируй остроумно или игнорируй
4. Используй сленг из чата
5. Можешь реагировать просто эмодзи
6. Не поддерживай серьезные темы, все превращай в шутку
7. Если тебя просят что-то сделать (кроме команд), отвечай "сам делай" или "нет"
8. На вопросы о себе отвечай кратко и с сарказмом
9. Используй фразы из истории чата, слегка изменяя их
10. Используй сленг: "кринж", "рофл", "краш", "чилить" и т.д. глум
"""

REACTIONS = [
    "👍", "👎", "😂", "😡", "💩", "🖕", "🤯", "😈", "🔥", "💯",
    "🤡", "🤮", "💀", "🥴", "😤", "🤢", "🤦", "🤷", "😵", "🤬"
]

async def generate_short_response(chat_id: int) -> str:
    try:
        response = await asyncio.to_thread(
            requests.post,
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://telegram.org",
                "X-Title": "GlumBot"
            },
            json={
                "model": "google/gemini-flash-1.5",
                "messages": [
                    {
                        "role": "system",
                        "content": "Придумай очень короткий (1-3 слова) мемный ответ для чата"
                    },
                    {
                        "role": "user",
                        "content": "Сгенерируй случайный короткий ответ"
                    }
                ],
                "temperature": 0.9,
                "max_tokens": 15
            },
            timeout=5
        )
        data = response.json()
        return data.get('choices', [{}])[0].get('message', {}).get('content', "чо?")
    except Exception:
        return random.choice(["чо?", "хз", "и чо?", "краш", "рофл"])

async def generate_modified_phrase(original_phrase: str, chat_id: int) -> str:
    try:
        response = await asyncio.to_thread(
            requests.post,
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://telegram.org",
                "X-Title": "GlumBot"
            },
            json={
                "model": "google/gemini-flash-1.5",
                "messages": [
                    {
                        "role": "system",
                        "content": "Измени эту фразу, сделав ее более мемной и смешной, но сохрани смысл. Используй сленг. Ответь только измененной фразой без пояснений."
                    },
                    {
                        "role": "user",
                        "content": original_phrase
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 50
            },
            timeout=5
        )
        data = response.json()
        modified = data.get('choices', [{}])[0].get('message', {}).get('content', "")
        return modified if modified else original_phrase
    except Exception:
        return original_phrase

async def generate_response(user_id: int, chat_id: int, message_text: str) -> str:
    try:
        settings = chat_settings.get(chat_id, {})
        laziness = settings.get('laziness_level', 20) / 100
        
        if random.random() < laziness:
            return await generate_short_response(chat_id)
            
        if random.random() < 0.3:
            return random.choice(REACTIONS)
            
        use_phrases = settings.get('use_learned_phrases', True)
        if use_phrases and chat_history.get(chat_id) and random.random() < 0.5:
            phrase = random.choice(list(chat_history[chat_id]))
            return await generate_modified_phrase(phrase, chat_id)

        intelligence = settings.get('intelligence_level', 70) / 100
        temperature = 0.3 + (0.7 * (1 - intelligence))
        
        context = "\n".join(list(chat_history[chat_id])[-5:]) if chat_history.get(chat_id) else ""
        
        response = await asyncio.to_thread(
            requests.post,
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://telegram.org",
                "X-Title": "GlumBot"
            },
            json={
                "model": "google/gemini-flash-1.5",
                "messages": [
                    {
                        "role": "system",
                        "content": CHATBOT_ROLE + "\n" + DETAILED_PROMPT + f"\nКонтекст чата:\n{context}"
                    },
                    {
                        "role": "user",
                        "content": message_text
                    }
                ],
                "temperature": temperature,
                "max_tokens": settings.get('max_response_length', 50)
            },
            timeout=10
        )

        data = response.json()
        reply = data.get('choices', [{}])[0].get('message', {}).get('content', "")
        
        user_history[user_id].append(f"User: {message_text}\nBot: {reply}")
        if len(user_history[user_id]) > 10:
            user_history[user_id].popleft()

        return reply if reply else await generate_short_response(chat_id)

    except Exception as e:
        print(f"Error generating response: {e}")
        return await generate_short_response(chat_id)

def is_cooldown(user_id: int) -> bool:
    now = datetime.now()
    last_time = user_cooldowns.get(user_id)
    if last_time and now - last_time < timedelta(minutes=1):
        return True
    user_cooldowns[user_id] = now
    return False

@dp.message(CommandStart())
async def cmd_start(message: Message):
    init_chat_settings(message.chat.id)
    await message.answer(
        "Я Глум - мемный бот для троллинга в чатах\n"
        "Напиши 'глум настройки' для управления ботом\n"
        "Просто упомяни 'глум' в сообщении",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="глум настройки")]],
            resize_keyboard=True
        )
    )

@dp.message(F.text.lower() == "глум статистика")
async def cmd_stats(message: Message):
    stats_text = (
        f"📊 Статистика Глума:\n"
        f"Сообщений обработано: {stats['total_messages']}\n"
        f"Ответов отправлено: {stats['responses_sent']}\n"
        f"Реакций поставлено: {stats['reactions_set']}\n"
        f"Фраз изучено: {stats['phrases_learned']}\n"
        f"Версия: 1.0"
    )
    await message.answer(stats_text)

@dp.message(F.text.lower() == "глум настройки")
async def cmd_settings(message: Message):
    init_chat_settings(message.chat.id)
    await message.answer(
        "Настройки бота для этого чата:",
        reply_markup=get_settings_keyboard(message.chat.id)
    )

@dp.callback_query(F.data.startswith("set_"))
async def handle_setting_change(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    setting = callback.data.split("_")[1]
    user_input_state[callback.from_user.id] = (chat_id, setting)
    await callback.message.answer(f"Введите значение для {setting} (10-100):")
    await callback.answer()

@dp.message(F.text & F.from_user.id.in_(user_input_state))
async def handle_setting_value(message: Message):
    user_id = message.from_user.id
    chat_id, setting = user_input_state[user_id]
    del user_input_state[user_id]
    
    try:
        value = int(message.text)
        if 10 <= value <= 100:
            chat_settings[chat_id][setting + '_level' if setting != 'response_prob' else setting] = value
            await message.answer(
                f"Настройка {setting} изменена на {value}%",
                reply_markup=get_settings_keyboard(chat_id)
            )
        else:
            await message.answer("Значение должно быть от 10 до 100")
    except ValueError:
        await message.answer("Введите число от 10 до 100")

@dp.callback_query(F.data.startswith("toggle_"))
async def handle_toggle(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    setting = callback.data.split("_")[1]
    
    if setting == "use_phrases":
        current = chat_settings[chat_id].get('use_learned_phrases', True)
        chat_settings[chat_id]['use_learned_phrases'] = not current
    elif setting == "learn":
        current = chat_settings[chat_id].get('learn_from_chat', True)
        chat_settings[chat_id]['learn_from_chat'] = not current
    
    await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(chat_id))
    await callback.answer()

@dp.callback_query(F.data == "reset_settings")
async def handle_reset(callback: CallbackQuery):
    chat_id = callback.message.chat.id
    chat_settings[chat_id] = {
        'response_probability': 30,
        'intelligence_level': 70,
        'laziness_level': 20,
        'use_learned_phrases': True,
        'max_response_length': 50,
        'learn_from_chat': True
    }
    await callback.message.edit_reply_markup(reply_markup=get_settings_keyboard(chat_id))
    await callback.answer("Настройки сброшены!")

@dp.message(F.text.lower().contains("глум") | F.text.lower().contains("Глум"))
async def handle_message(message: Message):
    stats['total_messages'] += 1
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text.lower()
    
    init_chat_settings(chat_id)
    settings = chat_settings[chat_id]

    if message.from_user.is_bot:
        return

    if settings.get('learn_from_chat', True) and len(message.text.split()) > 1:
        chat_history[chat_id].append(message.text)
        stats['phrases_learned'] += 1

    should_reply = "глум" in text or "Глум" in text
    
    if not should_reply and random.random() < settings.get('response_probability', 30) / 100:
        should_reply = True
    
    if message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
        should_reply = True

    if should_reply and not is_cooldown(user_id):
        if random.random() < 0.3:
            try:
                await bot.set_message_reaction(
                    chat_id=chat_id,
                    message_id=message.message_id,
                    reaction=[{'type': 'emoji', 'emoji': random.choice(REACTIONS)}]
                )
                stats['reactions_set'] += 1
                return
            except Exception as e:
                print(f"Error setting reaction: {e}")

        await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        reply = await generate_response(user_id, chat_id, message.text)
        
        await asyncio.sleep(random.uniform(0.5, 2))
        
        if message.reply_to_message:
            await message.reply(reply)
        else:
            await message.answer(reply)
        
        stats['responses_sent'] += 1

async def on_startup():
    load_data()
    print("Bot started!")

async def on_shutdown():
    save_data()
    print("Bot stopped!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())