# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import json
import os

from bot import logger
from bot.utils import (
    load_settings,
    get_setting,
    check_user_permissions,
    format_balance
)

class ActivityCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='activity', description="Показать статистику посещений контента за период")
    @app_commands.describe(period="Период (week, month или число дней, например: 14)")
    async def user_activity_command(self, interaction: discord.Interaction, period: str = "week"):
        """Показать количество посещенных контентов за период"""
        if not await check_user_permissions(interaction):
            return
        
        if period.isdigit():
            days = int(period)
        else:
            days = 7 if period.lower() == "week" else 30

        await interaction.response.defer(ephemeral=False)
        guild_id = interaction.guild.id if interaction.guild else None
        
        try:
            stats = await logger.get_attendance_stats_async(days, guild_id=guild_id)
            user_id_str = str(interaction.user.id)
            
            if user_id_str in stats:
                user_data = stats[user_id_str]
                total_count = user_data['call'] + user_data['zvz'] + user_data['roum']
                organizer_count = user_data.get('organizer', 0)
                
                reply_text = f"📊 {interaction.user.mention}, за последние {days} дн. вы посетили **{total_count}** контентов "
                if organizer_count > 0:
                    reply_text += f"*(в {organizer_count} из них вы были организатором)*:\n"
                else:
                    reply_text += ":\n"
                    
                reply_text += f"• **Call**: {user_data['call']}\n"
                reply_text += f"• **ZvZ**: {user_data['zvz']}\n"
                reply_text += f"• **Roum**: {user_data['roum']}"
                
                await interaction.followup.send(content=reply_text)
            else:
                await interaction.followup.send(content=f"📊 {interaction.user.mention}, за последние {days} дн. посещений не найдено.")
                
        except Exception as e:
            await interaction.followup.send(content=f"❌ Ошибка при подсчете: {e}")

    @app_commands.command(name='activity_all', description="Статистика посещений всех участников за период")
    @app_commands.describe(period="Период (week, month или число дней, например: 14)")
    @app_commands.default_permissions(administrator=True)
    async def activity_all_command(self, interaction: discord.Interaction, period: str = "week"):
        """Статистика посещений всех участников за период"""
        if period.isdigit():
            days = int(period)
        else:
            days = 7 if period.lower() == "week" else 30
            
        await interaction.response.send_message(f"⏳ Собираю общую статистику за {days} дн. ...")
        guild_id = interaction.guild.id if interaction.guild else None
        
        try:
            stats = await logger.get_attendance_stats_async(days, guild_id=guild_id)
            if not stats:
                return await interaction.edit_original_response(content=f"📊 За последние {days} дн. посещений не найдено.")
                
            # Подсчитываем total для сортировки
            for user_id, user_data in stats.items():
                user_data['total'] = user_data['call'] + user_data['zvz'] + user_data['roum']
                
            sorted_stats = sorted(stats.values(), key=lambda x: x['total'], reverse=True)
            
            lines = [f"📊 **Топ активности за {days} дн.:**\n```text"]
            for item in sorted_stats[:20]:
                organizer_text = f"(Орг: {item.get('organizer', 0)})" if item.get('organizer', 0) > 0 else ""
                prefix = f"• {item['total']} {organizer_text}"
                prefix_padded = prefix.ljust(15) + " — "
                nick_padded = item['nick'].ljust(15)
                call_pad = str(item['call']).rjust(2)
                zvz_pad = str(item['zvz']).rjust(2)
                roum_pad = str(item['roum']).rjust(2)
                lines.append(f"{prefix_padded}{nick_padded} [ Call: {call_pad} | ZvZ: {zvz_pad} | Roum: {roum_pad} ]")
                
            if len(sorted_stats) > 20:
                lines.append(f"\n...и еще {len(sorted_stats) - 20} участников.")
                
            lines.append("```")
            await interaction.edit_original_response(content="\n".join(lines))
            
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Ошибка: {e}")

    @app_commands.command(name='update_grev', description="Синхронизация таблицы Грев и опциональный импорт лога сундука")
    @app_commands.describe(file="Файл лога сундука .txt")
    @app_commands.default_permissions(administrator=True)
    async def update_grev_command(self, interaction: discord.Interaction, file: discord.Attachment = None):
        """Синхронизация таблицы Грев и опциональный импорт лога сундука"""
        await interaction.response.defer()
        guild_id = interaction.guild.id if interaction.guild else None
        try:
            txt_content = None
            if file:
                if not file.filename.endswith('.txt'):
                    return await interaction.followup.send(content="❌ Пожалуйста, прикрепите текстовый файл лога (.txt)")
                
                file_bytes = await file.read()
                
                # Декодирование байтов лога с перебором кодировок
                encodings = ['utf-8-sig', 'utf-8', 'cp1251', 'ansi']
                decoded = None
                for enc in encodings:
                    try:
                        decoded = file_bytes.decode(enc)
                        break
                    except UnicodeDecodeError:
                        continue
                        
                if decoded is None:
                    return await interaction.followup.send(content="❌ Не удалось декодировать файл лога ни в одной из стандартных кодировок.")
                txt_content = decoded
                
            new_tx = await logger.sync_grev_data_async(txt_content, guild_id=guild_id)
            
            if file:
                await interaction.followup.send(content=f"✅ Синхронизация Грев завершена! Обработано новых транзакций из лога: **{new_tx}**")
            else:
                await interaction.followup.send(content="✅ Синхронизация Грев завершена! Данные ID Discord и ручных правок балансов обновлены.")
        except Exception as e:
            await interaction.followup.send(content=f"❌ Ошибка при обновлении балансов Грев: {e}")

    @app_commands.command(name='check_grev', description="Просмотр балансов Грев")
    @app_commands.describe(user="Discord-пользователь для проверки")
    async def check_grev_command(self, interaction: discord.Interaction, user: discord.Member = None):
        """Просмотр балансов Грев"""
        if not await check_user_permissions(interaction):
            return
            
        await interaction.response.defer()
        guild_id = interaction.guild.id if interaction.guild else None
        try:
            # Сначала синхронизируем с Google Таблицей для получения актуальной информации
            await logger.sync_grev_data_async(None, guild_id=guild_id)
            
            STATE_FILE = f"state_{guild_id}.json" if guild_id else "state.json"
            state = {
                "balances": {},
                "discord_ids": {},
                "player_last_tx": {}
            }
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    
            if user:
                user_id_str = str(user.id)
                found_nick = None
                discord_ids_map = state.get("discord_ids", {})
                for nick, d_id in discord_ids_map.items():
                    if str(d_id) == user_id_str:
                        found_nick = nick
                        break
                        
                if found_nick:
                    balance = state.get("balances", {}).get(found_nick, 0)
                    status_warning = ""
                    if balance < 0:
                        status_warning = " (🚨 отрицательный, требуется пополнить!)"
                    elif balance < 100:
                        status_warning = " (⚠️ мало)"
                    
                    msg = f"👤 Пользователь: {user.mention}\n"
                    msg += f"🎮 Игровой ник: `{found_nick}`\n"
                    msg += f"💰 Баланс Грев: **{balance}** монет{status_warning}"
                    await interaction.followup.send(content=msg)
                else:
                    await interaction.followup.send(content=f"❌ Игровой ник для пользователя {user.mention} не найден в таблице Грев.")
            else:
                balances_map = state.get("balances", {})
                discord_ids_map = state.get("discord_ids", {})
                
                if not balances_map:
                    return await interaction.followup.send(content="ℹ️ Таблица Грев пока пуста.")
                    
                debtors = []
                others = []
                
                for nick, balance in balances_map.items():
                    d_id = discord_ids_map.get(nick, "").strip()
                    if balance < 100:
                        debtors.append((nick, balance, d_id))
                    else:
                        others.append((nick, balance, d_id))
                        
                debtors.sort(key=lambda x: x[1])
                others.sort(key=lambda x: x[1], reverse=True)
                
                message_parts = ["📢 **Актуальный отчет по балансам «Грев»** (данные обновлены из Google Sheets)\n"]
                
                if debtors:
                    message_parts.append("🚨 **ВНИМАНИЕ! Баланс меньше 100 или отрицательный (требуется пополнение):**")
                    for nick, balance, d_id in debtors:
                        status_emoji = "🚨" if balance < 0 else "⚠️"
                        if d_id:
                            message_parts.append(f"- {status_emoji} <@{d_id}> (ник: `{nick}`, баланс: **{balance}** монет)")
                        else:
                            message_parts.append(f"- {status_emoji} игроку `{nick}` (баланс: **{balance}** монет) — *нет Discord ID*")
                    message_parts.append("") # пустая строка-разделитель
                else:
                    message_parts.append("✅ Нет игроков с низким или отрицательным балансом!\n")
                    
                others_lines = []
                if others:
                    current_line_parts = []
                    current_line_len = 0
                    for nick, balance, _ in others:
                        item = f"`{nick}` ({balance})"
                        if current_line_len + len(item) + 2 > 100:
                            others_lines.append(", ".join(current_line_parts))
                            current_line_parts = [item]
                            current_line_len = len(item)
                        else:
                            current_line_parts.append(item)
                            current_line_len += len(item) + 2
                    if current_line_parts:
                        others_lines.append(", ".join(current_line_parts))
                        
                if others:
                    message_parts.append("✅ **Остальные игроки (баланс в норме):**")
                    message_parts.extend(others_lines)
                else:
                    message_parts.append("ℹ️ Нет игроков с балансом >= 100 монет.")
                    
                chunks = []
                current_chunk = []
                current_len = 0
                for line in message_parts:
                    if current_len + len(line) + 1 > 1900:
                        chunks.append("\n".join(current_chunk))
                        current_chunk = [line]
                        current_len = len(line)
                    else:
                        current_chunk.append(line)
                        current_len += len(line) + 1
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    
                for i, chunk in enumerate(chunks):
                    chunk_clean = chunk.rstrip(", ")
                    await interaction.followup.send(content=chunk_clean)
        except Exception as e:
            await interaction.followup.send(content=f"❌ Ошибка при получении балансов Грев: {e}")

async def setup(bot):
    await bot.add_cog(ActivityCog(bot))
