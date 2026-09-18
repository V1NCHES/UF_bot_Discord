# -*- coding: utf-8 -*-
import os
import json
import time
import random
import string
import asyncio
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands
from discord import app_commands

from bot.constants import ALBION_LOCATIONS
from bot.utils import (
    load_settings,
    save_settings,
    get_setting,
    set_setting,
    check_user_permissions
)

def load_objectives():
    if os.path.exists('objectives.json'):
        try:
            with open('objectives.json', 'r', encoding='utf-8') as f:
                objs = json.load(f)
            now = int(time.time())
            filtered = [o for o in objs if now < o['time']]
            if len(filtered) != len(objs):
                save_objectives(filtered)
            return filtered
        except:
            return []
    return []

def save_objectives(objs):
    with open('objectives.json', 'w', encoding='utf-8') as f:
        json.dump(objs, f, ensure_ascii=False, indent=4)

BIOME_ALLOWED_RESOURCES = {
    'forest': ['wood', 'hide'],
    'swamp': ['fiber', 'hide', 'wood'],
    'steppe': ['fiber', 'hide', 'ore'],
    'highland': ['wood', 'ore'],
    'mountain': ['fiber', 'ore'],
}

RESOURCE_TYPE_MAP = {
    'волокно': 'fiber', 'fiber': 'fiber',
    'древесина': 'wood', 'wood': 'wood',
    'кожа': 'hide', 'hide': 'hide',
    'руда': 'ore', 'ore': 'ore',
    'камень': 'rock', 'rock': 'rock', 'stone': 'rock'
}

RESOURCE_RU_NAMES = {
    'fiber': 'Волокно (Fiber)',
    'wood': 'Древесина (Wood)',
    'hide': 'Кожа (Hide)',
    'ore': 'Руда (Ore)',
    'rock': 'Камень (Rock)'
}

BIOME_RU_NAMES = {
    'forest': 'Лес (Forest)',
    'swamp': 'Болото (Swamp)',
    'steppe': 'Степь (Steppe)',
    'highland': 'Хайленд (Highland)',
    'mountain': 'Горы (Mountain)'
}

RESOURCE_TIER_ALLOWED_LOCATION_TIERS = {
    '4.4': [5, 6],
    '5.4': [5, 6, 7],
    '6.4': [6, 7, 8],
    '7.4': [7, 8],
    '8.4': [8],
}

def parse_location_info(location_name: str):
    if not location_name:
        return None, None
    loc_clean = location_name.strip().lower()
    for val, name in ALBION_LOCATIONS:
        if loc_clean == val.lower() or loc_clean == name.lower():
            tier = None
            if name.startswith("V "): tier = 5
            elif name.startswith("VI "): tier = 6
            elif name.startswith("VII "): tier = 7
            elif name.startswith("VIII "): tier = 8
            elif name.startswith("💀 "): tier = 8
            
            biome = None
            if "🌲" in name: biome = "forest"
            elif "🐉" in name: biome = "swamp"
            elif "🐈" in name: biome = "steppe"
            elif "🗻" in name: biome = "highland"
            elif "❄" in name: biome = "mountain"
            
            return tier, biome
    return None, None

def get_max_objective_minutes(obj_type: str, tier: str) -> int:
    t_lower = (obj_type or "").lower()
    tier_lower = (tier or "").lower()
    
    # 1. Сундуки
    if "сундук" in t_lower or "chest" in t_lower:
        if "маленьк" in tier_lower or "small" in tier_lower:
            return 5
        elif "средн" in tier_lower or "medium" in tier_lower:
            return 20
        elif "золот" in tier_lower or "gold" in tier_lower or "больш" in tier_lower or "large" in tier_lower:
            return 40
        return 40
        
    # 2. Ядра / Сферы
    elif "ядро" in t_lower or "core" in t_lower or "сфер" in t_lower or "sphere" in t_lower:
        if "зелен" in tier_lower or "green" in tier_lower:
            return 5
        elif "син" in tier_lower or "blue" in tier_lower:
            return 15
        elif "фиолет" in tier_lower or "purple" in tier_lower:
            return 40
        elif "золот" in tier_lower or "gold" in tier_lower:
            return 120
        return 120
        
    # 3. Вихри
    elif "вихрь" in t_lower or "vortex" in t_lower:
        if "зелен" in tier_lower or "green" in tier_lower:
            return 15
        elif "син" in tier_lower or "blue" in tier_lower:
            return 45
        elif "фиолет" in tier_lower or "purple" in tier_lower:
            return 120
        elif "золот" in tier_lower or "gold" in tier_lower:
            return 240
        return 240
        
    # 4. Ресурсы
    else:
        if "4.4" in tier_lower or tier_lower == ".4" or tier_lower == "4":
            return 60
        elif "5.4" in tier_lower or tier_lower == ".5" or tier_lower == "5":
            return 120
        elif "6.4" in tier_lower or tier_lower == ".6" or tier_lower == "6":
            return 240
        elif "7.4" in tier_lower or tier_lower == ".7" or tier_lower == "7":
            return 480
        elif "8.4" in tier_lower or tier_lower == ".8" or tier_lower == "8":
            return 960
        return 960

def parse_objective_time(time_str: str, max_minutes: int = None) -> int:
    import time
    from datetime import datetime, timezone, timedelta
    import re
    
    time_str = time_str.strip()
    now_utc = datetime.now(timezone.utc)
    target_dt = None
    
    if time_str.isdigit():
        minutes = int(time_str)
        if minutes <= 0:
            raise ValueError("❌ Время в минутах должно быть больше 0!")
        target_dt = now_utc + timedelta(minutes=minutes)
    else:
        dt_match = re.match(r'^(\d{1,2})[\./-](\d{1,2})(?:[\./-](\d{2,4}))?\s+(\d{1,2})[:.-](\d{2})$', time_str)
        if dt_match:
            day = int(dt_match.group(1))
            month = int(dt_match.group(2))
            year_str = dt_match.group(3)
            year = int(year_str) if year_str else now_utc.year
            if year < 100: year += 2000
            hours = int(dt_match.group(4))
            minutes = int(dt_match.group(5))
            try:
                target_dt = datetime(year, month, day, hours, minutes, tzinfo=timezone.utc)
            except ValueError:
                raise ValueError("❌ Некорректная дата или время!")
        else:
            t_match = re.match(r'^(\d{1,2})[:.-](\d{2})(?:[:.-](\d{2}))?$', time_str)
            if t_match:
                hours = int(t_match.group(1))
                minutes = int(t_match.group(2))
                if hours > 23 or minutes > 59:
                    raise ValueError("❌ Некорректное время! Часы от 00 до 23, минуты от 00 до 59.")
                
                candidate_dt = now_utc.replace(hour=hours, minute=minutes, second=0, microsecond=0)
                
                if candidate_dt <= now_utc:
                    candidate_tomorrow = candidate_dt + timedelta(days=1)
                    if max_minutes:
                        diff_min = (candidate_tomorrow - now_utc).total_seconds() / 60
                        if diff_min <= max_minutes:
                            target_dt = candidate_tomorrow
                        else:
                            passed_min = int((now_utc - candidate_dt).total_seconds() / 60)
                            raise ValueError(
                                f"❌ Указанное время {hours:02d}:{minutes:02d} UTC уже прошло сегодня ({passed_min} мин. назад).\n"
                                f"Завтрашнее время {hours:02d}:{minutes:02d} UTC превышает макс. время открытия ({max_minutes} мин.)."
                            )
                    else:
                        target_dt = candidate_tomorrow
                else:
                    target_dt = candidate_dt
            else:
                raise ValueError(
                    "❌ Неверный формат времени!\n"
                    "• Укажите количество минут (например, `23`)\n"
                    "• Или UTC время (например, `15:40`)\n"
                    "• Или дату и UTC время (например, `18.09 15:40`)."
                )
                
    total_seconds = int((target_dt - now_utc).total_seconds())
    if total_seconds <= 0:
        raise ValueError("❌ Указанное время уже прошло!")
        
    minutes_left = total_seconds / 60
    if max_minutes and minutes_left > max_minutes:
        raise ValueError(
            f"❌ Время до открытия ({int(minutes_left)} мин.) превышает максимально допустимое "
            f"для этого объекта ({max_minutes} мин.)!"
        )
        
    return int(target_dt.timestamp())

def format_obj_name(obj_type: str, obj_tier: str) -> str:
    t_lower = obj_type.lower()
    r_tier = str(obj_tier).strip() if obj_tier else ""
    
    emoji = ""
    gender = "neuter"
    
    if "ядро" in t_lower or "core" in t_lower or "сфер" in t_lower or "sphere" in t_lower:
        ru_base, en_base = "Ядро", "Core"
        gender = "neuter"
        emoji = "🔮"
    elif "вихрь" in t_lower or "vortex" in t_lower:
        ru_base, en_base = "Вихрь", "Vortex"
        gender = "masculine"
        emoji = "🌀"
    elif "волокно" in t_lower or "fiber" in t_lower:
        ru_base, en_base = "Волокно", "Fiber"
        emoji = "🌻"
        gender = "neuter"
    elif "древесина" in t_lower or "wood" in t_lower:
        ru_base, en_base = "Древесина", "Wood"
        emoji = "🌲"
        gender = "feminine"
    elif "шкуры" in t_lower or "hide" in t_lower or "кожа" in t_lower:
        ru_base, en_base = "Кожа", "Hide"
        emoji = "🐈"
        gender = "feminine"
    elif "руда" in t_lower or "ore" in t_lower:
        ru_base, en_base = "Руда", "Ore"
        emoji = "⛏"
        gender = "feminine"
    elif "камень" in t_lower or "rock" in t_lower:
        ru_base, en_base = "Камень", "Rock"
        emoji = "🗿"
        gender = "masculine"
    elif "ресурс" in t_lower or "node" in t_lower:
        ru_base, en_base = "Ресурс", "Resource"
        gender = "masculine"
    elif "сундук" in t_lower or "chest" in t_lower:
        ru_base, en_base = "Сундук", "Chest"
        emoji = "🎁"
        gender = "masculine"
    else:
        ru_base = obj_type.split('(')[0].strip()
        en_base = "Other"
        gender = "neuter"
        
    if not r_tier:
        prefix = f"{emoji} " if emoji else ""
        return f"{prefix}{ru_base} ({en_base})"
        
    tier_lower = r_tier.lower()
    is_mapped = False
    
    if "зелен" in tier_lower or "green" in tier_lower:
        if gender == "masculine":
            ru_color = "Зеленый"
        elif gender == "feminine":
            ru_color = "Зеленая"
        elif gender == "plural":
            ru_color = "Зеленые"
        else:
            ru_color = "Зеленое"
        en_color = "Green"
        is_mapped = True
    elif "син" in tier_lower or "blue" in tier_lower:
        if gender == "masculine":
            ru_color = "Синий"
        elif gender == "feminine":
            ru_color = "Синяя"
        elif gender == "plural":
            ru_color = "Синие"
        else:
            ru_color = "Синее"
        en_color = "Blue"
        is_mapped = True
    elif "фиолет" in tier_lower or "purple" in tier_lower:
        if gender == "masculine":
            ru_color = "Фиолетовый"
        elif gender == "feminine":
            ru_color = "Фиолетовая"
        elif gender == "plural":
            ru_color = "Фиолетовые"
        else:
            ru_color = "Фиолетовое"
        en_color = "Purple"
        is_mapped = True
    elif "золот" in tier_lower or "gold" in tier_lower:
        if gender == "masculine":
            ru_color = "Золотой"
        elif gender == "feminine":
            ru_color = "Золотая"
        elif gender == "plural":
            ru_color = "Золотые"
        else:
            ru_color = "Золотое"
        en_color = "Gold"
        is_mapped = True
    elif "маленьк" in tier_lower or "small" in tier_lower:
        ru_color = "Маленький"
        en_color = "Small"
        is_mapped = True
    elif "средн" in tier_lower or "medium" in tier_lower:
        ru_color = "Средний"
        en_color = "Medium"
        is_mapped = True
    else:
        ru_color, en_color = r_tier, r_tier
        
    prefix = f"{emoji} " if emoji else ""
    if is_mapped:
        return f"{prefix}{ru_base} {ru_color} ({en_base} {en_color})"
    else:
        return f"{prefix}{ru_base} {r_tier} ({en_base} {r_tier})"

async def update_objectives_dashboard(guild):
    settings = load_settings()
    channel_id = get_setting(settings, guild.id, 'objectives_channel_id')
    if not channel_id:
        return
        
    channel = guild.get_channel(channel_id)
    if not channel:
        return
        
    objs = load_objectives()
    now = int(time.time())
    objs = [o for o in objs if now < o['time']]
    
    embed = discord.Embed(
        title="⚔️ АКТИВНЫЕ ОБЪЕКТЫ ALBION ONLINE ⚔️",
        color=discord.Color.from_str("#7D00FF")
    )
    
    desc = (
        "🗺️ Актуальный список игровых целей на карте:\n"
        "🌀 — Вихри\n"
        "🔮 — Ядра\n"
        "💎 — Ресурсы .4\n"
        "🎁 — Сундуки\n\n"
        "🔄 *Автоматическое обновление каждую минуту.*"
    )
    
    if not objs:
        desc += "\n\n*На данный момент активных объектов нет. Вы можете добавить цель с помощью команды `/obj_add`.*"
    else:
        desc += "\n\n"
        for i, o in enumerate(objs):
            time_left = o['time'] - now
            status = "⏳ Ожидание" if time_left > 0 else "🔥 Активен"
            
            obj_name = format_obj_name(o['type'], o['tier'])
            desc += f" - {obj_name} [{o['id']}]\n"
            desc += f"📍 Локация: {o['location']}\n"
            desc += f"⏰ Открытие: <t:{o['time']}:R> (<t:{o['time']}:T>)\n"
            desc += f"👤 Нашел: <@{o['author_id']}>\n"
            desc += f"📊 Статус: {status}"
            
            if o.get('screenshot_url'):
                desc += f"\n [Фото ссылка]({o['screenshot_url']})"
                
            if i < len(objs) - 1:
                desc += "\n\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
                
    embed.description = desc
    embed.set_footer(text="Discord Bot UF • Автообновление")
    embed.timestamp = discord.utils.utcnow()
    
    pinned_msg_id = get_setting(settings, guild.id, 'objectives_pinned_msg_id')
    msg = None
    if pinned_msg_id:
        try:
            msg = await channel.fetch_message(pinned_msg_id)
        except:
            msg = None
            
    if msg:
        try:
            await msg.edit(embed=embed)
        except Exception as e:
            print(f"Ошибка обновления закрепленного сообщения: {e}")
            msg = None
            
    if not msg:
        try:
            msg = await channel.send(embed=embed)
            try:
                await msg.pin()
            except Exception as pin_err:
                print(f"Не удалось закрепить сообщение: {pin_err}")
            set_setting(settings, guild.id, 'objectives_pinned_msg_id', msg.id)
            save_settings(settings)
        except Exception as e:
            print(f"Ошибка отправки нового закрепленного сообщения: {e}")

class ObjectivesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        asyncio.create_task(self.check_objectives_loop())

    async def check_objectives_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now = int(time.time())
                settings = load_settings()
                
                # --- Логика ежедневного сброса в 13:00 МСК ---
                tz_msk = timezone(timedelta(hours=3))
                now_msk = datetime.now(timezone.utc).astimezone(tz_msk)
                today_str = now_msk.strftime('%Y-%m-%d')
                
                if now_msk.hour >= 13:
                    settings_changed = False
                    for guild in self.bot.guilds:
                        guild_id_str = str(guild.id)
                        guild_settings = settings.get("guilds", {}).get(guild_id_str, {})
                        if not guild_settings:
                            continue
                        channel_id = guild_settings.get('objectives_channel_id')
                        if not channel_id:
                            continue
                        
                        last_reset = guild_settings.get('last_1300_msg_date')
                        if last_reset != today_str:
                            print(f"[{guild_id_str}] Наступило 13:00 МСК. Пересоздаем закрепленное сообщение...")
                            # 1. Открепляем старое сообщение
                            old_pinned_id = guild_settings.get('objectives_pinned_msg_id')
                            if old_pinned_id:
                                channel = guild.get_channel(channel_id)
                                if channel:
                                    try:
                                        old_msg = await channel.fetch_message(old_pinned_id)
                                        await old_msg.unpin()
                                        print(f"[{guild_id_str}] Старое сообщение успешно откреплено.")
                                    except Exception as unpin_err:
                                        print(f"[{guild_id_str}] Не удалось открепить старое сообщение: {unpin_err}")
                            
                            # 2. Сбрасываем ID закрепленного сообщения и сохраняем дату сброса
                            set_setting(settings, guild.id, 'objectives_pinned_msg_id', None)
                            set_setting(settings, guild.id, 'last_1300_msg_date', today_str)
                            settings_changed = True
                    if settings_changed:
                        save_settings(settings)
                        settings = load_settings()
                
                objs = load_objectives()
                changed = False
                active_objs = []
                
                for o in objs:
                    if now >= o['time']:
                        changed = True
                        print(f"Объект {o['id']} ({o['type']}) удален как прошедший по времени.")
                        continue
                    active_objs.append(o)
                    
                if changed:
                    save_objectives(active_objs)
                    objs = active_objs
                    changed = False
                    
                # Проверяем предупреждающие пинги (за 15 минут) для каждой гильдии
                for o in objs:
                    if now >= o['time'] - 900 and now < o['time']:
                        pinged_guilds = o.setdefault('warning_pinged_guilds', [])
                        if o.get('warning_pinged') and not pinged_guilds:
                            for g in self.bot.guilds:
                                pinged_guilds.append(str(g.id))
                        
                        for guild in self.bot.guilds:
                            guild_id_str = str(guild.id)
                            if guild_id_str not in pinged_guilds:
                                channel_id = get_setting(settings, guild.id, 'objectives_channel_id')
                                if channel_id:
                                    channel = guild.get_channel(channel_id)
                                    if channel:
                                        embed = discord.Embed(
                                            title=f"⏳ СКОРО ОТКРЫТИЕ: {format_obj_name(o['type'], o['tier'])}",
                                            description=(
                                                f"📍 **Локация:** {o['location']}\n"
                                                f"⏰ **Открытие через 15 минут!** (<t:{o['time']}:R>)\n"
                                                f"👤 **Обнаружил:** <@{o['author_id']}>"
                                            ),
                                            color=discord.Color.gold()
                                        )
                                        if o.get('screenshot_url'):
                                            embed.set_image(url=o['screenshot_url'])
                                        try:
                                            await channel.send(content="@here", embed=embed)
                                        except Exception as err:
                                            print(f"Ошибка отправки пинга объекта в гильдии {guild.id}: {err}")
                                pinged_guilds.append(guild_id_str)
                                changed = True
                                
                if changed:
                    save_objectives(objs)
                    
                # Периодически обновляем дашборд для всех гильдий каждую минуту
                for g in self.bot.guilds:
                    try:
                        await update_objectives_dashboard(g)
                    except Exception as e:
                        print(f"Ошибка периодического обновления дашборда для гильдии {g.id}: {e}")
                        
            except Exception as e:
                print(f"Ошибка в check_objectives_loop: {e}")
                
            await asyncio.sleep(60)

    @app_commands.command(name='config_obj_channel', description="Настройка канала для отслеживания игровых объектов")
    @app_commands.describe(channel="Канал для публикации отчетов по объектам")
    async def config_obj_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Настройка доступна только администраторам сервера!", ephemeral=True)
            
        settings = load_settings()
        guild_id = interaction.guild.id if interaction.guild else None
        set_setting(settings, guild_id, 'objectives_channel_id', channel.id)
        set_setting(settings, guild_id, 'objectives_pinned_msg_id', None)
        save_settings(settings)
        
        await interaction.response.send_message(f"✅ Канал для отслеживания объектов успешно установлен: {channel.mention}", ephemeral=True)
        await update_objectives_dashboard(interaction.guild)

    @app_commands.command(name='obj_add', description="Добавление игрового объекта на карту")
    @app_commands.describe(
        type="Тип объекта (например: Ядро, Вихрь, Ресурсный узел)",
        time_left="Время: в минутах ('23') или UTC время ('15:40' или '18.09 15:40')",
        tier="Тир/цвет объекта (необязательно; например: 8.4, Зеленое, Синее)",
        location="Название локации/карты (необязательно)",
        screenshot="Скриншот объекта (необязательно)"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="🔮 Ядро / Сфера (Core)", value="Ядро (Core)"),
        app_commands.Choice(name="🌀 Вихрь (Vortex)", value="Вихрь (Vortex)"),
        app_commands.Choice(name="🎁 Сундук (Chest)", value="Сундук (Chest)"),
        app_commands.Choice(name="🌻 Волокно (Fiber)", value="Волокно (Fiber)"),
        app_commands.Choice(name="🌲 Древесина (Wood)", value="Древесина (Wood)"),
        app_commands.Choice(name="🐈 Кожа (Hide)", value="Кожа (Hide)"),
        app_commands.Choice(name="⛏ Руда (Ore)", value="Руда (Ore)"),
        app_commands.Choice(name="🗿 Камень (Rock)", value="Камень (Rock)"),
        app_commands.Choice(name="Другое (Other)", value="Другое")
    ])
    async def obj_add(
        self,
        interaction: discord.Interaction,
        type: app_commands.Choice[str],
        time_left: str,
        tier: str = None,
        location: str = None,
        screenshot: discord.Attachment = None
    ):
        if not await check_user_permissions(interaction): return
        
        settings = load_settings()
        guild_id = interaction.guild.id if interaction.guild else None
        channel_id = get_setting(settings, guild_id, 'objectives_channel_id')
        if not channel_id:
            return await interaction.response.send_message(
                "❌ Канал для объектов не настроен! Администратор должен настроить его командой `/config_obj_channel`.",
                ephemeral=True
            )
            
        loc = location.strip() if location else "Рядом"
        t_tier = tier.strip() if tier else ""
        t_val = type.value
        if not t_tier and ("сундук" in t_val.lower() or "chest" in t_val.lower()):
            t_tier = "Золотой"
            
        t_val_lower = t_val.lower()
        t_tier_lower = t_tier.lower()
        
        # 1. Проверка камня (Rock) на .4 зачарование
        is_rock = "камень" in t_val_lower or "rock" in t_val_lower
        is_dot4 = ".4" in t_tier_lower or t_tier in ["4.4", "5.4", "6.4", "7.4", "8.4"]
        if is_rock and is_dot4:
            return await interaction.response.send_message(
                "❌ У камня (Rock) не бывает .4 зачарования!",
                ephemeral=True
            )
            
        # Определяем тир и биом локации
        loc_tier, loc_biome = parse_location_info(loc)
        
        # 2. Проверка биома для ресурсов
        res_key = None
        for key in ['волокно', 'fiber', 'древесина', 'wood', 'кожа', 'hide', 'руда', 'ore', 'камень', 'rock']:
            if key in t_val_lower:
                res_key = RESOURCE_TYPE_MAP[key]
                break
                
        if res_key and loc_biome:
            allowed_res = BIOME_ALLOWED_RESOURCES.get(loc_biome, [])
            if res_key not in allowed_res:
                allowed_str = ", ".join([RESOURCE_RU_NAMES.get(r, r) for r in allowed_res])
                return await interaction.response.send_message(
                    f"❌ Ресурс **{RESOURCE_RU_NAMES.get(res_key, t_val)}** не встречается в биоме **{BIOME_RU_NAMES.get(loc_biome, loc_biome)}**!\n"
                    f"Разрешенные ресурсы в этом биоме: {allowed_str}.",
                    ephemeral=True
                )
                
        # 3. Проверка тира локации для .4 ресурсов
        if t_tier in RESOURCE_TIER_ALLOWED_LOCATION_TIERS and loc_tier:
            allowed_loc_tiers = RESOURCE_TIER_ALLOWED_LOCATION_TIERS[t_tier]
            if loc_tier not in allowed_loc_tiers:
                allowed_str = ", ".join([f"Tier {t}" for t in allowed_loc_tiers])
                return await interaction.response.send_message(
                    f"❌ Ресурс **{t_tier}** не может появляться в локации **Tier {loc_tier}**!\n"
                    f"Разрешенные тиры локаций для {t_tier}: {allowed_str}.",
                    ephemeral=True
                )
                
        # 4. Проверка и парсинг времени с учетом максимального лимита
        max_mins = get_max_objective_minutes(t_val, t_tier)
        try:
            spawn_time = parse_objective_time(time_left, max_minutes=max_mins)
        except ValueError as err:
            return await interaction.response.send_message(str(err), ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        
        obj_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        
        screenshot_url = None
        if screenshot:
            screenshot_url = screenshot.url
            
        new_obj = {
            'id': obj_id,
            'type': type.value,
            'tier': t_tier,
            'location': loc,
            'time': spawn_time,
            'author_id': interaction.user.id,
            'screenshot_url': screenshot_url,
            'warning_pinged': False
        }
        
        objs = load_objectives()
        objs.append(new_obj)
        objs.sort(key=lambda x: x['time'])
        save_objectives(objs)
        
        await update_objectives_dashboard(interaction.guild)
        
        embed = discord.Embed(
            title=f"✅ ОБЪЕКТ ДОБАВЛЕН: {format_obj_name(type.value, t_tier)}",
            description=(
                f"🆔 **ID:** {obj_id}\n"
                f"🔹 **Тир/Цвет:** {t_tier if t_tier else 'Не указан'}\n"
                f"📍 **Локация:** {loc}\n"
                f"⏰ **Открытие через:** <t:{spawn_time}:R> (<t:{spawn_time}:T>)\n"
                f"👤 **Нашел:** {interaction.user.mention}"
            ),
            color=discord.Color.green()
        )
        if screenshot_url:
            embed.set_image(url=screenshot_url)
            
        await interaction.followup.send(embed=embed, ephemeral=True)

    @obj_add.autocomplete('tier')
    async def obj_tier_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        selected_type = interaction.namespace.type or ""
        st_lower = selected_type.lower()
        
        options = []
        if "ядро" in st_lower or "core" in st_lower or "сфер" in st_lower or "sphere" in st_lower or "вихрь" in st_lower or "vortex" in st_lower:
            options = ["Зеленое", "Синее", "Фиолетовое", "Золотое"]
        elif "сундук" in st_lower or "chest" in st_lower:
            options = ["Маленький", "Средний", "Золотой"]
        elif "камень" in st_lower or "rock" in st_lower:
            options = []
        else:
            options = ["8.4", "7.4", "6.4", "5.4", "4.4"]
            
        choices = []
        for opt in options:
            if current.lower() in opt.lower():
                choices.append(app_commands.Choice(name=opt, value=opt))
        return choices[:25]

    @obj_add.autocomplete('location')
    async def obj_location_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        choices = []
        current_lower = current.lower()
        
        if not current_lower:
            choices.append(app_commands.Choice(name="📍 Оставить без названия (Рядом)", value="Рядом"))
            for val, name in ALBION_LOCATIONS[:24]:
                choices.append(app_commands.Choice(name=name, value=val))
            return choices
            
        for val, name in ALBION_LOCATIONS:
            if current_lower in val.lower() or current_lower in name.lower():
                choices.append(app_commands.Choice(name=name, value=val))
                if len(choices) >= 25:
                    break
        return choices

    @app_commands.command(name='obj_list', description="Вывод списка всех активных объектов")
    async def obj_list(self, interaction: discord.Interaction):
        if not await check_user_permissions(interaction): return
        
        objs = load_objectives()
        if not objs:
            return await interaction.response.send_message("ℹ️ Активных объектов на карте сейчас нет.", ephemeral=True)
            
        embed = discord.Embed(
            title="⚔️ Список активных объектов ⚔️",
            color=discord.Color.from_str("#7D00FF")
        )
        
        now = int(time.time())
        
        desc = ""
        for i, o in enumerate(objs):
            time_left = o['time'] - now
            status = "⏳ Ожидание" if time_left > 0 else "🔥 Активен"
            
            obj_name = format_obj_name(o['type'], o['tier'])
            desc += f" - {obj_name} [{o['id']}]\n"
            desc += f"📍 Локация: {o['location']}\n"
            desc += f"⏰ Открытие: <t:{o['time']}:R> (<t:{o['time']}:T>)\n"
            desc += f"👤 Нашел: <@{o['author_id']}>\n"
            desc += f"📊 Статус: {status}"
            
            if o.get('screenshot_url'):
                desc += f"\n [Фото ссылка]({o['screenshot_url']})"
                
            if i < len(objs) - 1:
                desc += "\n\n⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯\n\n"
                
        embed.description = desc
        embed.set_footer(text="United Force • Список игровых целей")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ObjectivesCog(bot))
