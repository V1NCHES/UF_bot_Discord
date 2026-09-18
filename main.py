# -*- coding: utf-8 -*-
import asyncio
import os
import time
import discord
from discord.ext import commands
from bot import config, ui, logger
from bot.utils import (
    load_settings,
    save_settings,
    get_setting,
    set_setting,
    get_allowed_channel_ids
)

# Инициализируем бота с необходимыми правами
bot = commands.Bot(command_prefix='!', intents=config.get_intents())
bot.active_calls = {}

async def migrate_settings_if_needed():
    settings = load_settings()
    keys_to_migrate = [
        "withdraw_channel_id", "withdraw_role_id", "roum_role_id", "zvz_channel_id", 
        "zvz_role_id", "user_channel_ids", "call_channel_ids", "roum_channel_ids", 
        "objectives_channel_id", "objectives_pinned_msg_id", "save_role_id",
        "spreadsheet_url", "spreadsheet_id", "sheet_config"
    ]
    has_flat = any(k in settings for k in keys_to_migrate)
    if not has_flat:
        return
        
    print("Обнаружены плоские настройки. Выполняем миграцию...")
    main_guild_id = None
    
    # Сначала пытаемся найти подходящую гильдию по наличию каналов
    for g in bot.guilds:
        for k in ["withdraw_channel_id", "objectives_channel_id"]:
            cid = settings.get(k)
            if cid and g.get_channel(cid) is not None:
                main_guild_id = g.id
                break
        if main_guild_id:
            break
            
        for k in ["call_channel_ids", "roum_channel_ids", "user_channel_ids"]:
            cids = settings.get(k)
            if isinstance(cids, list):
                for cid in cids:
                    if g.get_channel(cid) is not None:
                        main_guild_id = g.id
                        break
            if main_guild_id:
                break
        if main_guild_id:
            break
            
    if not main_guild_id and len(bot.guilds) == 1:
        main_guild_id = bot.guilds[0].id
        
    if main_guild_id:
        g_str = str(main_guild_id)
        if "guilds" not in settings:
            settings["guilds"] = {}
        if g_str not in settings["guilds"]:
            settings["guilds"][g_str] = {}
            
        for k in keys_to_migrate:
            if k in settings:
                settings["guilds"][g_str][k] = settings.pop(k)
                
        save_settings(settings)
        print(f"Настройки успешно мигрированы для гильдии {main_guild_id}")
    else:
        print("Не удалось определить гильдию для миграции настроек.")

async def check_event_start_times():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            now_unix = int(time.time())
            
            # Обходим копию активных сборов
            for msg_id, call_data in list(bot.active_calls.items()):
                # Обрабатываем только главные ID сборов, чтобы избежать повторений
                if msg_id != call_data.get('main_msg_id'):
                    continue
                    
                event_time = call_data.get('event_time') or call_data.get('created_at')
                created_at = call_data.get('created_at')
                if event_time and not call_data.get('paused'):
                    if created_at and (event_time - created_at < 900):
                        call_data['warning_pinged'] = True
                    # 0. Напоминание за 15 минут до начала (900 секунд)
                    if now_unix >= event_time - 900 and not call_data.get('warning_pinged'):
                        call_data['warning_pinged'] = True
                        participants = [u.mention for u in call_data['slots'] if u is not None]
                        if participants:
                            mentions_str = " ".join(participants)
                            content = f"⚠️ {mentions_str}\n⚔️ **Напоминание: контент {call_data.get('description', '')} начнется через 15 минут! Готовьтесь!**"
                        else:
                            content = f"⚠️ **Напоминание: контент {call_data.get('description', '')} начнется через 15 минут!** (Участников нет)"
                        try:
                            thread_id = call_data.get('thread_id')
                            if thread_id:
                                thread = bot.get_channel(thread_id)
                                if thread:
                                    await thread.send(content)
                                else:
                                    channel = bot.get_channel(call_data['main_channel_id'])
                                    if channel:
                                        await channel.send(content)
                        except Exception as e:
                            print(f"Ошибка отправки пинга-напоминания: {e}")
                        asyncio.create_task(logger.save_data_async(call_data))

                    # 1. Пинг участников, когда контент начался
                    if now_unix >= event_time and not call_data.get('start_pinged'):
                        call_data['start_pinged'] = True
                        
                        participants = [u.mention for u in call_data['slots'] if u is not None]
                        if participants:
                            mentions_str = " ".join(participants)
                            content = f"🔔 {mentions_str}\n⚔️ **Контент {call_data.get('description', '')} начался! Все в бой!**"
                        else:
                            content = f"🔔 **Контент {call_data.get('description', '')} начался!** (Участников нет)"
                            
                        try:
                            thread_id = call_data.get('thread_id')
                            if thread_id:
                                thread = bot.get_channel(thread_id)
                                if thread:
                                    await thread.send(content)
                                else:
                                    channel = bot.get_channel(call_data['main_channel_id'])
                                    if channel:
                                        await channel.send(content)
                        except Exception as e:
                            print(f"Ошибка отправки пинга старта контента: {e}")
                            
                        asyncio.create_task(logger.save_data_async(call_data))
                        
                    # 2. Автоматическое завершение сбора по указанному времени конца или через 1 час (3600 секунд)
                    duration = call_data.get('duration')
                    end_offset = duration * 60 if duration else 3600
                    if now_unix >= event_time + end_offset:
                        try:
                            await ui.auto_finish_call(bot, call_data, bot.active_calls)
                        except Exception as e:
                            print(f"Ошибка автозавершения сбора {call_data.get('id')}: {e}")
                            
        except Exception as e:
            print(f"Ошибка в check_event_start_times: {e}")
            
        await asyncio.sleep(30)

async def periodic_memory_cleanup():
    """Фоновая периодическая оптимизация RAM (каждые 30 минут) для стабильной работы на Discloud"""
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            await asyncio.sleep(1800)  # 30 минут
            from bot.cogs.system_cog import perform_cleanup
            res = perform_cleanup(bot)
            print(f"[Auto-Memory] Очистка RAM завершена. Текущий RSS: {res['after_mb']:.2f} МБ (освобождено {res['freed_mb']:.2f} МБ)")
        except Exception as e:
            print(f"Ошибка в periodic_memory_cleanup: {e}")

@bot.event
async def on_ready():
    # Очищаем локальные дубликаты с серверов, оставляя только единые глобальные команды
    for guild in bot.guilds:
        try:
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
        except Exception as e:
            print(f"Ошибка очистки локальных команд для гильдии {guild.id}: {e}")
            
    await bot.tree.sync()
    print(f'Бот {bot.user} запущен! Slash команды успешно синхронизированы без дубликатов.')
    await migrate_settings_if_needed()
    asyncio.create_task(check_event_start_times())
    asyncio.create_task(periodic_memory_cleanup())

async def load_extensions():
    extensions = [
        'bot.cogs.general_cog',
        'bot.cogs.objectives_cog',
        'bot.cogs.calls_cog',
        'bot.cogs.config_cog',
        'bot.cogs.balance_cog',
        'bot.cogs.activity_cog',
        'bot.cogs.ava_portal_cog',
        'bot.cogs.system_cog',
        'bot.cogs.voice_cog',
        # 'bot.cogs.regear_cog'  # Временно отключено по запросу
    ]
    for ext in extensions:
        try:
            await bot.load_extension(ext)
            print(f"Ког {ext} успешно загружен.")
        except Exception as e:
            print(f"Ошибка загрузки кога {ext}: {e}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(config.TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
