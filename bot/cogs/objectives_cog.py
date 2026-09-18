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

def parse_objective_time(time_str: str) -> int:
    import time
    from datetime import datetime, timezone, timedelta
    import re
    
    time_str = time_str.strip()
    
    if time_str.isdigit():
        minutes = int(time_str)
        return int(time.time()) + minutes * 60
        
    match = re.match(r'^(\d{1,2})[:.-](\d{2})$', time_str)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2))
        
        now_utc = datetime.now(timezone.utc)
        dt = now_utc.replace(hour=hours, minute=minutes, second=0, microsecond=0)
        
        if dt < now_utc:
            dt += timedelta(days=1)
            
        return int(dt.timestamp())
        
    raise ValueError("❌ Неверный формат времени! Укажите количество минут (например, `23`) или UTC время (например, `15:40`).")

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
        time_left="Время до открытия (минут: '23' или UTC время: '15:40')",
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
            
        try:
            spawn_time = parse_objective_time(time_left)
        except ValueError as err:
            return await interaction.response.send_message(str(err), ephemeral=True)
            
        await interaction.response.defer(ephemeral=False)
        
        obj_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        
        screenshot_url = None
        if screenshot:
            screenshot_url = screenshot.url
            
        loc = location.strip() if location else "Рядом"
        
        t_tier = tier.strip() if tier else ""
        t_val = type.value
        if not t_tier and ("сундук" in t_val.lower() or "chest" in t_val.lower()):
            t_tier = "Золотой"
            
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
            
        await interaction.followup.send(embed=embed)

    @obj_add.autocomplete('tier')
    async def obj_tier_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        selected_type = interaction.namespace.type or ""
        st_lower = selected_type.lower()
        
        options = []
        if "ядро" in st_lower or "core" in st_lower or "сфер" in st_lower or "sphere" in st_lower or "вихрь" in st_lower or "vortex" in st_lower:
            options = ["Зеленое", "Синее", "Фиолетовое", "Золотое"]
        elif "сундук" in st_lower or "chest" in st_lower:
            options = ["Маленький", "Средний", "Золотой"]
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
