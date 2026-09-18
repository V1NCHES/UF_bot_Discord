# -*- coding: utf-8 -*-
import json
import os
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

from bot.utils import (
    check_permissions,
    load_call_from_cache,
    save_call_to_cache
)
from bot import ui, logger

async def template_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    if not os.path.exists('calls_cache.json') or os.path.getsize('calls_cache.json') == 0:
        return []
    try:
        with open('calls_cache.json', 'r', encoding='utf-8') as f:
            cache = json.load(f)
    except:
        return []
        
    choices = []
    for c_id, data in cache.items():
        name = data.get('template_name') or f"Шаблон {c_id}"
        display_label = f"{name} ({c_id})"
        if current.lower() in display_label.lower():
            choices.append(app_commands.Choice(name=display_label[:100], value=c_id))
            
    return choices[:25]

class CallsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='call', description="Создание обычного сбора через окно")
    @app_commands.describe(
        ping_role="Роль для пинга (необязательно)",
        title="Свой заголовок сбора (необязательно)",
        duration="Длительность контента в минутах (необязательно)",
        template_id="ID шаблона сбора для копирования (необязательно)",
        roles="Список ролей через запятую или точку с запятой с указанием количества мест (необязательно)"
    )
    async def create_call(self, interaction: discord.Interaction, ping_role: discord.Role = None, title: str = None, duration: int = None, template_id: str = None, roles: str = None):
        if not await check_permissions(interaction, 'call'): return
        await interaction.response.defer(ephemeral=False)
        
        prefill_desc = None
        prefill_roles = None
        prefill_link = None
        required_role = None
        
        active_calls = self.bot.active_calls
        
        if template_id:
            original_call = None
            for c_data in active_calls.values():
                if c_data.get('id') == template_id:
                    original_call = c_data
                    break
                    
            if not original_call:
                original_call = load_call_from_cache(template_id, interaction.guild)
                
            if original_call:
                prefill_desc = original_call.get('description')
                if 'slot_limits' in original_call and original_call.get('slot_limits'):
                    prefill_roles = "\n".join(f"{i+1}. {label};{original_call['slot_limits'][i]}" for i, label in enumerate(original_call['slot_labels']))
                else:
                    prefill_roles = "\n".join(f"{i+1}. {label}" for i, label in enumerate(original_call['slot_labels']))
                prefill_link = original_call.get('link')
                required_role = original_call.get('required_role')
                if not title:
                    title = original_call.get('title')
                if not duration:
                    duration = original_call.get('duration')
                if not ping_role:
                    ping_role = original_call.get('ping_role')
            else:
                await interaction.channel.send(f"⚠️ Шаблон с ID `{template_id}` не найден в активных сборах или кэше! Будет создан обычный сбор.")

        if roles:
            import re
            parts = re.split(r'[,;\n]', roles)
            prefill_roles = "\n".join(f"{i+1}. {part.strip()}" for i, part in enumerate(parts) if part.strip())

        view = ui.StartCallView(
            required_role=required_role, 
            active_calls=active_calls, 
            call_type='call', 
            ping_role=ping_role, 
            title=title, 
            duration=duration,
            prefill_desc=prefill_desc,
            prefill_roles=prefill_roles,
            prefill_link=prefill_link
        )
        await interaction.followup.send(f"Привет, {interaction.user.mention}! Нажми на кнопку ниже, чтобы настроить новый сбор.", view=view)

    @create_call.autocomplete('template_id')
    async def create_call_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await template_autocomplete(interaction, current)

    @app_commands.command(name='zvz', description="Создание сбора ZvZ через окно")
    @app_commands.describe(
        ping_role="Роль для пинга (необязательно)",
        title="Свой заголовок сбора (необязательно)",
        duration="Длительность контента в минутах (необязательно)",
        template_id="ID шаблона сбора для ZvZ (необязательно)",
        roles="Список ролей через запятую или точку с запятой с указанием количества (необязательно)"
    )
    async def create_zvz(self, interaction: discord.Interaction, ping_role: discord.Role = None, title: str = None, duration: int = None, template_id: str = None, roles: str = None):
        if not await check_permissions(interaction, 'zvz'): return
        await interaction.response.defer(ephemeral=False)
        
        prefill_desc = None
        prefill_roles = None
        prefill_link = None
        required_role = None
        
        active_calls = self.bot.active_calls
        
        if template_id:
            original_call = None
            for c_data in active_calls.values():
                if c_data.get('id') == template_id:
                    original_call = c_data
                    break
                    
            if not original_call:
                original_call = load_call_from_cache(template_id, interaction.guild)
                
            if original_call:
                prefill_desc = original_call.get('description')
                if 'slot_limits' in original_call and original_call.get('slot_limits'):
                    prefill_roles = "\n".join(f"{i+1}. {label};{original_call['slot_limits'][i]}" for i, label in enumerate(original_call['slot_labels']))
                else:
                    prefill_roles = "\n".join(f"{i+1}. {label}" for i, label in enumerate(original_call['slot_labels']))
                prefill_link = original_call.get('link')
                required_role = original_call.get('required_role')
                if not title:
                    title = original_call.get('title')
                if not duration:
                    duration = original_call.get('duration')
                if not ping_role:
                    ping_role = original_call.get('ping_role')
            else:
                await interaction.channel.send(f"⚠️ Шаблон с ID `{template_id}` не найден в активных сборах или кэше! Будет создан обычный сбор.")

        if roles:
            import re
            parts = re.split(r'[,;\n]', roles)
            prefill_roles = "\n".join(f"{i+1}. {part.strip()}" for i, part in enumerate(parts) if part.strip())

        view = ui.StartCallView(
            required_role=required_role, 
            active_calls=active_calls, 
            call_type='zvz', 
            ping_role=ping_role, 
            title=title, 
            duration=duration,
            prefill_desc=prefill_desc,
            prefill_roles=prefill_roles,
            prefill_link=prefill_link
        )
        await interaction.followup.send(f"Привет, {interaction.user.mention}! Нажми на кнопку ниже, чтобы настроить ZvZ сбор.", view=view)

    @create_zvz.autocomplete('template_id')
    async def create_zvz_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await template_autocomplete(interaction, current)

    @app_commands.command(name='roum', description="Создание сбора Roum через окно")
    @app_commands.describe(
        ping_role="Роль для пинга (необязательно)",
        title="Свой заголовок сбора (необязательно)",
        duration="Длительность контента в минутах (необязательно)",
        template_id="ID шаблона сбора для Roum (необязательно)",
        roles="Список ролей через запятую или точку с запятой с указанием количества (необязательно)"
    )
    async def create_roum(self, interaction: discord.Interaction, ping_role: discord.Role = None, title: str = None, duration: int = None, template_id: str = None, roles: str = None):
        if not await check_permissions(interaction, 'roum'): return
        await interaction.response.defer(ephemeral=False)
        
        prefill_desc = None
        prefill_roles = None
        prefill_link = None
        required_role = None
        
        active_calls = self.bot.active_calls
        
        if template_id:
            original_call = None
            for c_data in active_calls.values():
                if c_data.get('id') == template_id:
                    original_call = c_data
                    break
                    
            if not original_call:
                original_call = load_call_from_cache(template_id, interaction.guild)
                
            if original_call:
                prefill_desc = original_call.get('description')
                if 'slot_limits' in original_call and original_call.get('slot_limits'):
                    prefill_roles = "\n".join(f"{i+1}. {label};{original_call['slot_limits'][i]}" for i, label in enumerate(original_call['slot_labels']))
                else:
                    prefill_roles = "\n".join(f"{i+1}. {label}" for i, label in enumerate(original_call['slot_labels']))
                prefill_link = original_call.get('link')
                required_role = original_call.get('required_role')
                if not title:
                    title = original_call.get('title')
                if not duration:
                    duration = original_call.get('duration')
                if not ping_role:
                    ping_role = original_call.get('ping_role')
            else:
                await interaction.channel.send(f"⚠️ Шаблон с ID `{template_id}` не найден в активных сборах или кэше! Будет создан обычный сбор.")

        if roles:
            import re
            parts = re.split(r'[,;\n]', roles)
            prefill_roles = "\n".join(f"{i+1}. {part.strip()}" for i, part in enumerate(parts) if part.strip())

        view = ui.StartCallView(
            required_role=required_role, 
            active_calls=active_calls, 
            call_type='roum', 
            ping_role=ping_role, 
            title=title, 
            duration=duration,
            prefill_desc=prefill_desc,
            prefill_roles=prefill_roles,
            prefill_link=prefill_link
        )
        await interaction.followup.send(f"Привет, {interaction.user.mention}! Нажми на кнопку ниже, чтобы настроить Roum сбор.", view=view)

    @create_roum.autocomplete('template_id')
    async def create_roum_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        return await template_autocomplete(interaction, current)

    @app_commands.command(name='copy_call', description="Копирование обычного сбора по ID")
    @app_commands.describe(call_id="ID сбора, который нужно скопировать")
    async def copy_call(self, interaction: discord.Interaction, call_id: str):
        if not await check_permissions(interaction, 'call'): return
        await interaction.response.defer(ephemeral=False)
        
        active_calls = self.bot.active_calls
        original_call = None
        for c_data in active_calls.values():
            if c_data.get('id') == call_id:
                original_call = c_data
                break
                
        if not original_call:
            original_call = load_call_from_cache(call_id, interaction.guild)
            
        if not original_call:
            return await interaction.followup.send(f"❌ Сбор с ID `{call_id}` не найден в активных сборах или кэше!", ephemeral=True)
            
        if 'slot_limits' in original_call and original_call.get('slot_limits'):
            roles_text = "\n".join(f"{i+1}. {label};{original_call['slot_limits'][i]}" for i, label in enumerate(original_call['slot_labels']))
        else:
            roles_text = "\n".join(f"{i+1}. {label}" for i, label in enumerate(original_call['slot_labels']))
        
        view = ui.StartCallView(
            required_role=original_call.get('required_role'),
            active_calls=active_calls,
            call_type='call',
            ping_role=original_call.get('ping_role'),
            title=original_call.get('title'),
            duration=original_call.get('duration'),
            prefill_desc=original_call.get('description'),
            prefill_roles=roles_text,
            prefill_link=original_call.get('link')
        )
        await interaction.followup.send(
            f"📋 Копия сбора `{call_id}` готова! Нажмите на кнопку ниже, чтобы настроить и запустить новый сбор (все поля предзаполнены).", 
            view=view
        )

    @app_commands.command(name='copy_zvz', description="Копирование ZvZ сбора по ID")
    @app_commands.describe(call_id="ID сбора, который нужно скопировать")
    async def copy_zvz(self, interaction: discord.Interaction, call_id: str):
        if not await check_permissions(interaction, 'zvz'): return
        await interaction.response.defer(ephemeral=False)
        
        active_calls = self.bot.active_calls
        original_call = None
        for c_data in active_calls.values():
            if c_data.get('id') == call_id:
                original_call = c_data
                break
                
        if not original_call:
            original_call = load_call_from_cache(call_id, interaction.guild)
            
        if not original_call:
            return await interaction.followup.send(f"❌ Сбор с ID `{call_id}` не найден в активных сборах или кэше!", ephemeral=True)
            
        if 'slot_limits' in original_call:
            roles_text = "\n".join(f"{i+1}. {label};{original_call['slot_limits'][i]}" for i, label in enumerate(original_call['slot_labels']))
        else:
            roles_text = "\n".join(f"{i+1}. {label}" for i, label in enumerate(original_call['slot_labels']))
        
        view = ui.StartCallView(
            required_role=original_call.get('required_role'),
            active_calls=active_calls,
            call_type='zvz',
            ping_role=original_call.get('ping_role'),
            title=original_call.get('title'),
            duration=original_call.get('duration'),
            prefill_desc=original_call.get('description'),
            prefill_roles=roles_text,
            prefill_link=original_call.get('link')
        )
        await interaction.followup.send(
            f"📋 Копия ZvZ сбора `{call_id}` готова! Нажмите на кнопку ниже, чтобы настроить и запустить новый сбор (все поля предзаполнены).", 
            view=view
        )

    @app_commands.command(name='copy_roum', description="Копирование Roum сбора по ID")
    @app_commands.describe(call_id="ID сбора, который нужно скопировать")
    async def copy_roum(self, interaction: discord.Interaction, call_id: str):
        if not await check_permissions(interaction, 'roum'): return
        await interaction.response.defer(ephemeral=False)
        
        active_calls = self.bot.active_calls
        original_call = None
        for c_data in active_calls.values():
            if c_data.get('id') == call_id:
                original_call = c_data
                break
                
        if not original_call:
            original_call = load_call_from_cache(call_id, interaction.guild)
            
        if not original_call:
            return await interaction.followup.send(f"❌ Сбор с ID `{call_id}` не найден в активных сборах или кэше!", ephemeral=True)
            
        if 'slot_limits' in original_call and original_call.get('slot_limits'):
            roles_text = "\n".join(f"{i+1}. {label};{original_call['slot_limits'][i]}" for i, label in enumerate(original_call['slot_labels']))
        else:
            roles_text = "\n".join(f"{i+1}. {label}" for i, label in enumerate(original_call['slot_labels']))
        
        view = ui.StartCallView(
            required_role=original_call.get('required_role'),
            active_calls=active_calls,
            call_type='roum',
            ping_role=original_call.get('ping_role'),
            title=original_call.get('title'),
            duration=original_call.get('duration'),
            prefill_desc=original_call.get('description'),
            prefill_roles=roles_text,
            prefill_link=original_call.get('link')
        )
        await interaction.followup.send(
            f"📋 Копия Roum сбора `{call_id}` готова! Нажмите на кнопку ниже, чтобы настроить и запустить новый сбор (все поля предзаполнены).", 
            view=view
        )

    @app_commands.command(name='add_player', description="Добавить игрока на роль в сборе (с выбором пользователя в строке)")
    @app_commands.describe(
        role_number="Номер роли в сборе (например: 1, 2, 3...)",
        player="Участник сервера, которого нужно записать",
        call_id="ID сбора (необязательно, если команда вводится в канале или ветке сбора)"
    )
    async def add_player(self, interaction: discord.Interaction, role_number: int, player: discord.Member, call_id: str = None):
        await interaction.response.defer(ephemeral=False)
        active_calls = self.bot.active_calls

        call_data = None
        if call_id:
            for c in active_calls.values():
                if c.get('id') == call_id:
                    call_data = c
                    break
        else:
            call_data = active_calls.get(interaction.channel_id)

        if not call_data:
            return await interaction.followup.send("❌ Активный сбор не найден в этом канале/ветке. Укажите `call_id` сбора.", ephemeral=True)

        # Проверка прав: организатор или админ
        if interaction.user != call_data['organizer'] and not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send("❌ Только организатор сбора или администратор может добавлять игроков.", ephemeral=True)

        idx = role_number - 1
        if not (0 <= idx < len(call_data['slots'])):
            return await interaction.followup.send(f"❌ Неверный номер роли! Доступны слоты от 1 до {len(call_data['slots'])}.", ephemeral=True)

        # Проверяем, не записан ли игрок уже в этот сбор
        is_already = any(player in s if isinstance(s, list) else player == s for s in call_data['slots'])
        if is_already:
            return await interaction.followup.send(f"⚠️ {player.display_name} уже записан в этот сбор!", ephemeral=True)

        # Запись в слот
        slot = call_data['slots'][idx]
        role_name = call_data['slot_labels'][idx]
        if isinstance(slot, list):
            limits = call_data.get('slot_limits')
            limit = limits[idx] if (limits and len(limits) > idx) else 999
            if len(slot) >= limit:
                return await interaction.followup.send(f"⚠️ Роль **{role_name}** уже полностью заполнена ({limit} из {limit})!", ephemeral=True)
            slot.append(player)
        else:
            if slot is not None:
                return await interaction.followup.send(f"⚠️ Слот {role_number} (**{role_name}**) уже занят другим игроком!", ephemeral=True)
            call_data['slots'][idx] = player

        await ui.sync_messages(self.bot, call_data, active_calls)
        asyncio.create_task(logger.save_data_async(call_data))

        success_msg = f"✅ Игрок {player.mention} добавлен на роль **{role_name}** (Слот {role_number})"
        await interaction.followup.send(success_msg)

        # Дублируем уведомление в ветку, если команда вызвана не из ветки
        if call_data.get('thread_id') and interaction.channel_id != call_data.get('thread_id'):
            thread = self.bot.get_channel(call_data['thread_id'])
            if thread:
                try:
                    await thread.send(success_msg)
                except: pass

    @app_commands.command(name='remove_player', description="Снять игрока со слота сбора")
    @app_commands.describe(
        role_number="Номер роли в сборе (например: 1, 2, 3...)",
        player="Игрок для снятия (необязательно для одиночных слотов)",
        call_id="ID сбора (необязательно, если команда вводится в канале или ветке сбора)"
    )
    async def remove_player(self, interaction: discord.Interaction, role_number: int, player: discord.Member = None, call_id: str = None):
        await interaction.response.defer(ephemeral=False)
        active_calls = self.bot.active_calls

        call_data = None
        if call_id:
            for c in active_calls.values():
                if c.get('id') == call_id:
                    call_data = c
                    break
        else:
            call_data = active_calls.get(interaction.channel_id)

        if not call_data:
            return await interaction.followup.send("❌ Активный сбор не найден в этом канале/ветке. Укажите `call_id` сбора.", ephemeral=True)

        if interaction.user != call_data['organizer'] and not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send("❌ Только организатор сбора или администратор может убирать игроков.", ephemeral=True)

        idx = role_number - 1
        if not (0 <= idx < len(call_data['slots'])):
            return await interaction.followup.send(f"❌ Неверный номер роли! Доступны слоты от 1 до {len(call_data['slots'])}.", ephemeral=True)

        slot = call_data['slots'][idx]
        role_name = call_data['slot_labels'][idx]
        removed_name = ""

        if isinstance(slot, list):
            if not slot:
                return await interaction.followup.send(f"⚠️ Слот {role_number} (**{role_name}**) уже пуст!", ephemeral=True)
            if player:
                if player in slot:
                    slot.remove(player)
                    removed_name = player.display_name
                else:
                    return await interaction.followup.send(f"⚠️ Игрок {player.display_name} не найден в слоте {role_number}!", ephemeral=True)
            else:
                removed_p = slot.pop()
                removed_name = removed_p.display_name
        else:
            if slot is None:
                return await interaction.followup.send(f"⚠️ Слот {role_number} (**{role_name}**) уже пуст!", ephemeral=True)
            if player and slot != player:
                return await interaction.followup.send(f"⚠️ В слоте {role_number} записан другой игрок ({slot.display_name})!", ephemeral=True)
            removed_name = slot.display_name
            call_data['slots'][idx] = None

        await ui.sync_messages(self.bot, call_data, active_calls)
        asyncio.create_task(logger.save_data_async(call_data))

        success_msg = f"❌ {removed_name} убран с роли **{role_name}** (Слот {role_number})"
        await interaction.followup.send(success_msg)

        if call_data.get('thread_id') and interaction.channel_id != call_data.get('thread_id'):
            thread = self.bot.get_channel(call_data['thread_id'])
            if thread:
                try:
                    await thread.send(success_msg)
                except: pass

async def setup(bot):
    await bot.add_cog(CallsCog(bot))
