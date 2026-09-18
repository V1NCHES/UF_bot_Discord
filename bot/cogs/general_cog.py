# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import asyncio

from bot import logger
from bot.utils import load_settings, get_setting, get_allowed_channel_ids, check_user_permissions, format_balance
from bot import ui

class GeneralCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Бот {self.bot.user} запущен! Cogs успешно загружены и синхронизированы.')

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
            
        active_calls = self.bot.active_calls
        
        # !+ Команда (ручное добавление организатором)
        if message.content.startswith('!+'):
            if not isinstance(message.channel, discord.Thread): return
            call_data = active_calls.get(message.channel.id)
            if not call_data: return
            
            if message.author != call_data['organizer'] and not message.author.guild_permissions.administrator:
                return await message.channel.send("❌ Только организатор может использовать эту команду.", delete_after=5)

            try:
                content = message.content[2:].strip()
                import re
                match = re.match(r'^(\d+)', content)
                if not match: return
                
                slot_idx = int(match.group(1)) - 1
                user_part = content[len(match.group(1)):].strip()
                
                member = None
                if message.mentions:
                    member = message.mentions[0]
                else:
                    user_match = re.search(r'(\d{17,20})', user_part)
                    if user_match:
                        member = message.guild.get_member(int(user_match.group(1)))
                
                if not member:
                    return await message.channel.send("❌ Укажите пользователя (@упоминание или ID).", delete_after=5)
                
                if not (0 <= slot_idx < len(call_data['slots'])):
                    return await message.channel.send(f"❌ Неверный номер слота! (1-{len(call_data['slots'])})", delete_after=5)
                    
                is_multi = isinstance(call_data['slots'][slot_idx], list)
                if is_multi:
                    slot_list = call_data['slots'][slot_idx]
                    limits = call_data.get('slot_limits')
                    limit = limits[slot_idx] if (limits and len(limits) > slot_idx) else 999
                    
                    already = any(member in s if isinstance(s, list) else member == s for s in call_data['slots'])
                    if already:
                        return await message.channel.send(f"⚠️ {member.display_name} уже записан!", delete_after=5)
                    if len(slot_list) >= limit:
                        return await message.channel.send(f"⚠️ Роль {slot_idx+1} уже заполнена ({limit} из {limit})!", delete_after=5)
                    slot_list.append(member)
                else:
                    if call_data['slots'][slot_idx] is not None:
                        return await message.channel.send(f"⚠️ Слот {slot_idx+1} уже занят!", delete_after=5)
                    already = any(member in s if isinstance(s, list) else member == s for s in call_data['slots'])
                    if already:
                        return await message.channel.send(f"⚠️ {member.display_name} уже записан!", delete_after=5)
                    call_data['slots'][slot_idx] = member

                await ui.sync_messages(self.bot, call_data, active_calls)
                asyncio.create_task(logger.save_data_async(call_data))
                
                await message.channel.send(f"✅ {member.mention} добавлен на роль **{call_data['slot_labels'][slot_idx]}** (Слот {slot_idx+1})")
                await message.delete()
                return
            except Exception as e:
                print(f"Ошибка в !+: {e}")

        # !- Команда (ручное удаление организатором)
        if message.content.startswith('!-'):
            if not isinstance(message.channel, discord.Thread): return
            call_data = active_calls.get(message.channel.id)
            if not call_data: return
            
            if message.author != call_data['organizer'] and not message.author.guild_permissions.administrator:
                return await message.channel.send("❌ Только организатор может использовать эту команду.", delete_after=5)

            try:
                content = message.content[2:].strip()
                import re
                match = re.match(r'^(\d+)', content)
                if not match: return
                
                slot_idx = int(match.group(1)) - 1
                
                if not (0 <= slot_idx < len(call_data['slots'])):
                    return await message.channel.send(f"❌ Неверный номер слота! (1-{len(call_data['slots'])})", delete_after=5)
                    
                is_multi = isinstance(call_data['slots'][slot_idx], list)
                removed_name = ""
                if is_multi:
                    slot_list = call_data['slots'][slot_idx]
                    if not slot_list:
                        return await message.channel.send(f"⚠️ Слот {slot_idx+1} уже пуст!", delete_after=5)
                    target_member = None
                    if message.mentions:
                        target_member = message.mentions[0]
                    elif user_part:
                        user_match = re.search(r'(\d{17,20})', user_part)
                        if user_match:
                            target_member = message.guild.get_member(int(user_match.group(1)))
                    if target_member:
                        if target_member in slot_list:
                            slot_list.remove(target_member)
                            removed_name = target_member.display_name
                        else:
                            return await message.channel.send(f"⚠️ Игрок не найден в слоте {slot_idx+1}!", delete_after=5)
                    else:
                        removed_user = slot_list.pop()
                        removed_name = removed_user.display_name
                else:
                    member = call_data['slots'][slot_idx]
                    if member is None:
                        return await message.channel.send(f"⚠️ Слот {slot_idx+1} уже пуст!", delete_after=5)
                    call_data['slots'][slot_idx] = None
                    removed_name = member.display_name

                await ui.sync_messages(self.bot, call_data, active_calls)
                asyncio.create_task(logger.save_data_async(call_data))
                
                await message.channel.send(f"❌ {removed_name} убран со слота {slot_idx+1}")
                await message.delete()
                return
            except Exception as e:
                print(f"Ошибка в !-: {e}")

        # .+ и .- Команды (самозапись/самовыписка участников)
        if message.content.startswith('.+') or message.content.startswith('.-'):
            if not isinstance(message.channel, discord.Thread): return
            call_data = active_calls.get(message.channel.id)
            if not call_data: return
            
            action = message.content[:2]
            try:
                slot_idx = int(message.content[2:].strip()) - 1
                if 0 <= slot_idx < len(call_data['slots']):
                    status_msg = ""
                    is_multi = isinstance(call_data['slots'][slot_idx], list)
                    if action == '.+':
                        already = any(message.author in s if isinstance(s, list) else message.author == s for s in call_data['slots'])
                        if is_multi:
                            slot_list = call_data['slots'][slot_idx]
                            limits = call_data.get('slot_limits')
                            limit = limits[slot_idx] if (limits and len(limits) > slot_idx) else 999
                            if already:
                                status_msg = f"⚠️ {message.author.mention}, вы уже записаны в этот сбор!"
                            elif len(slot_list) >= limit:
                                status_msg = f"⚠️ {message.author.mention}, эта роль уже полностью заполнена ({limit} из {limit})!"
                            else:
                                slot_list.append(message.author)
                                status_msg = f"✅ {message.author.display_name} записался на роль **{call_data['slot_labels'][slot_idx]}**"
                                asyncio.create_task(logger.save_data_async(call_data))
                        else:
                            if call_data['slots'][slot_idx] is None:
                                if not already:
                                    call_data['slots'][slot_idx] = message.author
                                    status_msg = f"✅ {message.author.display_name} записался на роль **{call_data['slot_labels'][slot_idx]}**"
                                    asyncio.create_task(logger.save_data_async(call_data))
                                else:
                                    status_msg = f"⚠️ {message.author.mention}, вы уже записаны в этот сбор!"
                            else:
                                status_msg = f"⚠️ {message.author.mention}, этот слот уже занят!"
                    elif action == '.-':
                        if is_multi:
                            slot_list = call_data['slots'][slot_idx]
                            if message.author in slot_list:
                                slot_list.remove(message.author)
                                status_msg = f"❌ {message.author.display_name} выписался из слота **{call_data['slot_labels'][slot_idx]}**"
                                asyncio.create_task(logger.save_data_async(call_data))
                        else:
                            if call_data['slots'][slot_idx] == message.author:
                                call_data['slots'][slot_idx] = None
                                status_msg = f"❌ {message.author.display_name} выписался из слота **{call_data['slot_labels'][slot_idx]}**"
                                asyncio.create_task(logger.save_data_async(call_data))
                    
                    if status_msg:
                        await message.channel.send(status_msg, delete_after=5)
                        await ui.sync_messages(self.bot, call_data, active_calls)
                    
                    await message.delete()
            except Exception: pass

    @app_commands.command(name='info', description="Список всех доступных команд")
    async def show_bot_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        settings = load_settings()
        guild_id = interaction.guild.id if interaction.guild else None
        sheet_url = get_setting(settings, guild_id, 'spreadsheet_url', "https://docs.google.com/spreadsheets/d/1Ey0TKDDNRs5bZfaswPzgFpTFja1URcgayOMEBGj8Yek/edit?usp=sharing")

        embed = discord.Embed(
            title="📚 Доступные команды",
            description=f"Список команд для управления сборами и событиями.\n\n🔗 [**Таблица с данными (Google Sheets)**]({sheet_url})",
            color=discord.Color.blue()
        )
        
        user_commands = (
            "**`/call`, `/zvz`, `/roum`**\n"
            "Создать соответствующий сбор через окно настроек.\n\n"
            "**`/balance [user]`**\n"
            "Показать ваш текущий баланс или баланс пользователя.\n\n"
            "**`.+[номер]` / `.-[номер]`**\n"
            "Запись/выписка в ветке сбора (например: `.+1`).\n\n"
            "**`/withdrawal_request`**\n"
            "Подать заявку на вывод средств.\n\n"
            "**`/activity [дни]`**\n"
            "Ваша статистика посещений за период.\n\n"
            "**`/info`**\n"
            "Это сообщение.\n\n"
            "**⚔️ СИСТЕМА ОБЪЕКТОВ:**\n"
            "• **`/obj_list`** — Просмотреть список активных объектов.\n"
            "• **`/obj_add`** — Добавить объект на карту (Ядро, Вихрь, Ресурс).\n\n"
            "**🌀 АВАЛОНСКИЕ ПОРТАЛЫ:**\n"
            "• **`/ava_portal [location]`** — Узнать тир, сундуки и лут в авалоне."
        )
        embed.add_field(name="👥 ДЛЯ ВСЕХ УЧАСТНИКОВ", value=user_commands, inline=False)

        organizer_commands = (
            "**`!+[номер] [user]`**\n"
            "Добавить игрока на слот (в ветке).\n\n"
            "**`!-[номер]`**\n"
            "Убрать игрока со слота (в ветке)."
        )
        embed.add_field(name="🎖️ ДЛЯ ОРГАНИЗАТОРОВ", value=organizer_commands, inline=False)
        
        call_channels = [cid for cid in get_allowed_channel_ids(settings, 'call', guild_id) if interaction.guild.get_channel(cid) is not None]
        zvz_channels = [cid for cid in get_allowed_channel_ids(settings, 'zvz', guild_id) if interaction.guild.get_channel(cid) is not None]
        roum_channels = [cid for cid in get_allowed_channel_ids(settings, 'roum', guild_id) if interaction.guild.get_channel(cid) is not None]
        user_channels = [cid for cid in get_allowed_channel_ids(settings, 'user', guild_id) if interaction.guild.get_channel(cid) is not None]
        
        call_ch_mention = ", ".join([f"<#{cid}>" for cid in call_channels]) if call_channels else "все"
        zvz_ch_mention = ", ".join([f"<#{cid}>" for cid in zvz_channels]) if zvz_channels else "все"
        roum_ch_mention = ", ".join([f"<#{cid}>" for cid in roum_channels]) if roum_channels else "все"
        user_ch_mention = ", ".join([f"<#{cid}>" for cid in user_channels]) if user_channels else "все"
        
        zvz_role_id = get_setting(settings, guild_id, 'zvz_role_id')
        roum_role_id = get_setting(settings, guild_id, 'roum_role_id')
        user_role_id = get_setting(settings, guild_id, 'user_role_id')
        
        zvz_role = interaction.guild.get_role(zvz_role_id) if zvz_role_id else None
        roum_role = interaction.guild.get_role(roum_role_id) if roum_role_id else None
        user_role = interaction.guild.get_role(user_role_id) if user_role_id else None
        
        zvz_mention = zvz_role.mention if zvz_role else "не настроена"
        roum_mention = roum_role.mention if roum_role else "не настроена"
        user_role_mention = user_role.mention if user_role else "нет ограничений"
        
        settings_field = (
            f"• **Каналы Call:** {call_ch_mention}\n"
            f"• **Каналы ZvZ:** {zvz_ch_mention}\n"
            f"• **Минимальная роль ZvZ:** {zvz_mention}\n"
            f"• **Каналы Roum:** {roum_ch_mention}\n"
            f"• **Минимальная роль Roum:** {roum_mention}\n"
            f"• **Пользовательские каналы:** {user_ch_mention}\n"
            f"• **Минимальная роль пользователей:** {user_role_mention}"
        )
        embed.add_field(name="⚙️ НАСТРОЙКИ ДОСТУПА", value=settings_field, inline=False)

        if interaction.user.guild_permissions.administrator:
            embed.add_field(name="🔑 АДМИНИСТРАТОР", value="Используйте **`/info_ad`** для просмотра админ-команд.", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)
async def setup(bot):
    await bot.add_cog(GeneralCog(bot))
