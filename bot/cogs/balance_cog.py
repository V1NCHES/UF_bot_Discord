# -*- coding: utf-8 -*-
import io
import re
import discord
from discord.ext import commands
from discord import app_commands

from bot import logger
from bot.utils import (
    load_settings,
    get_setting,
    check_user_permissions,
    format_balance
)

class SplitModal(discord.ui.Modal, title="Начисление долей за контент"):
    text_input = discord.ui.TextInput(
        label="Данные сплита (ID Ник Сумма построчно)",
        style=discord.TextStyle.paragraph,
        placeholder="Строка 1 (Название)\nСтрока 2 (Организатор)\nID Ник Сумма\nID Ник Сумма",
        required=True,
        max_length=4000
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            guild_id = interaction.guild.id if interaction.guild else None
            backup_buffer, backup_filename = await logger.export_balance_sheet_async(guild_id=guild_id)
            if backup_buffer:
                await interaction.channel.send("📦 Резервная копия таблицы Balance перед изменением:", file=discord.File(fp=backup_buffer, filename=backup_filename))
                backup_buffer.close()
            
            success_users, missing = await logger.add_content_shares_async(
                self.text_input.value,
                interaction.user.id,
                interaction.user.display_name,
                guild_id=guild_id
            )
            
            response = f"✅ **Успешно добавлено долей в новый столбец ({len(success_users)}):**\n"
            if success_users:
                response += "\n".join(success_users[:15])
                if len(success_users) > 15:
                    response += f"\n...и еще {len(success_users) - 15} чел."
            
            if missing:
                response += f"\n\n⚠️ **Не найдены в таблице ({len(missing)}):**\n"
                response += "\n".join(missing[:15])
                if len(missing) > 15:
                    response += f"\n...и еще {len(missing) - 15} чел."
                
            await interaction.followup.send(content=response)
        except Exception as e:
            await interaction.followup.send(content=f"❌ Ошибка при выполнении команды: {e}")
            print(f"Ошибка /split в SplitModal: {e}")

class BalanceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='split', description="Добавление долей за контент в таблицу Balance")
    @app_commands.default_permissions(administrator=True)
    async def split_command(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SplitModal())

    @app_commands.command(name='balance_uf', description="Показать таблицу балансов участников")
    @app_commands.default_permissions(administrator=True)
    async def show_balance_uf(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        try:
            guild_id = interaction.guild.id if interaction.guild else None
            data = await logger.get_balance_uf_async(guild_id=guild_id)
            if not data or len(data) <= 2:
                await interaction.followup.send(content="❌ Данные не найдены или таблица пуста.")
                return

            user_rows = []
            for r in data[2:]:
                if len(r) >= 3 and r[0].isdigit():
                    user_rows.append(r)
                    
            if not user_rows:
                await interaction.followup.send(content="❌ В таблице пока нет записей о балансах участников.")
                return

            lines = []
            lines.append(f"{'ID':<20} | {'Никнейм':<20} | {'Баланс':<10}")
            lines.append("-" * 56)
            for r in user_rows:
                u_id = r[0]
                nick = r[1]
                bal = format_balance(r[2])
                lines.append(f"{u_id:<20} | {nick:<20} | {bal:<10}")

            full_text = "📊 **Таблица балансов участников:**\n```text\n" + "\n".join(lines) + "\n```"
            
            if len(full_text) > 1900:
                buffer = io.BytesIO("\n".join(lines).encode('utf-8'))
                await interaction.channel.send("📄 Список слишком длинный, отправляю файлом:", file=discord.File(fp=buffer, filename="balance_uf.txt"))
                buffer.close()
                await interaction.followup.send(content="📄 Список отправлен файлом выше.")
            else:
                await interaction.followup.send(content=full_text)
                
        except Exception as e:
            await interaction.followup.send(content=f"❌ Ошибка: {e}")

    @app_commands.command(name='balance_uf_teg', description="Пинг всех участников с балансом > 1 000 000")
    @app_commands.default_permissions(administrator=True)
    async def balance_uf_teg(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        try:
            guild_id = interaction.guild.id if interaction.guild else None
            data = await logger.get_balance_uf_async(guild_id=guild_id)
            if not data or len(data) <= 2:
                await interaction.followup.send(content="❌ Данные не найдены или таблица пуста.")
                return

            ping_lines = []
            for r in data[2:]:
                if len(r) >= 3 and r[0].isdigit():
                    u_id = r[0]
                    nick = r[1]
                    bal_str = r[2]
                    
                    try:
                        clean = bal_str.replace(' ', '').replace(',', '').replace('\xa0', '')
                        balance_val = int(float(clean))
                    except (ValueError, TypeError):
                        balance_val = 0
                        
                    if balance_val > 1000000:
                        formatted_bal = format_balance(bal_str)
                        ping_lines.append(f"<@{u_id}> | {u_id} | {nick} | баланс: {formatted_bal}")

            if not ping_lines:
                await interaction.followup.send(content="ℹ️ Нет участников с балансом более 1 000 000.")
                return

            first_chunk = "📊 **Список участников с балансом > 1 000 000:**\n"
            current_msg = first_chunk
            messages_to_send = []
            
            for line in ping_lines:
                if len(current_msg) + len(line) + 2 > 1900:
                    messages_to_send.append(current_msg)
                    current_msg = ""
                current_msg += line + "\n"
            if current_msg:
                messages_to_send.append(current_msg)
                
            await interaction.followup.send(content=messages_to_send[0])
            
            for msg in messages_to_send[1:]:
                await interaction.channel.send(content=msg)
                
        except Exception as e:
            await interaction.followup.send(content=f"❌ Ошибка: {e}")

    @app_commands.command(name='balance', description="Показать личный баланс пользователя")
    @app_commands.describe(user="Упоминание или ID пользователя (необязательно)")
    async def show_my_balance(self, interaction: discord.Interaction, user: str = None):
        if not await check_user_permissions(interaction): return
        if user:
            match = re.search(r'\d+', user)
            target_id = int(match.group(0)) if match else None
            if not target_id:
                return await interaction.response.send_message("❌ Неверный формат пользователя. Укажите ID или упоминание.", ephemeral=True)
            mention_str = f"<@{target_id}>"
        else:
            target_id = interaction.user.id
            mention_str = interaction.user.mention

        await interaction.response.defer()
        guild_id = interaction.guild.id if interaction.guild else None
        balance = await logger.get_user_balance_async(target_id, guild_id=guild_id)
        
        if balance is not None:
            await interaction.followup.send(f"💰 {mention_str}, баланс: **{format_balance(balance)}**")
        else:
            await interaction.followup.send(f"❌ {mention_str}, ID (`{target_id}`) не найден в таблице балансов.")

    @app_commands.command(name='uf', description="Сохранение новых участников сервера в Google Таблицу UF")
    @app_commands.default_permissions(administrator=True)
    async def save_all_members(self, interaction: discord.Interaction):
        await interaction.response.send_message("⏳ Сверяю список участников с таблицей... это может занять некоторое время.")
        
        try:
            all_members = []
            if interaction.guild:
                try:
                    async for member in interaction.guild.fetch_members(limit=None):
                        if not member.bot:
                            all_members.append(member)
                except Exception as fetch_err:
                    print(f"[Предупреждение] fetch_members не удался ({fetch_err}), используем кэш гильдии.")
                    all_members = [m for m in interaction.guild.members if not m.bot]
            
            guild_id = interaction.guild.id if interaction.guild else None
            new_members, total_in_sheet, missing_from_discord = await logger.save_members_to_uf_async(all_members, guild_id=guild_id)
            
            header = f"✅ Всего в таблице: **{total_in_sheet}**\n"
            full_msg = header
            
            if new_members:
                added_list_str = "\n".join([f"• `{m.id}` — {m.display_name}" for m in new_members[:15]])
                if len(new_members) > 15:
                    added_list_str += f"\n...и еще {len(new_members) - 15} чел."
                full_msg += f"\n🆕 **Добавлено новых:**\n{added_list_str}"
            else:
                full_msg += "\n✅ Новых участников не обнаружено."

            if missing_from_discord:
                missing_list_str = "\n".join([f"• {m['nick']} (`{m['id']}`)" for m in missing_from_discord[:15]])
                if len(missing_from_discord) > 15:
                    missing_list_str += f"\n...и еще {len(missing_from_discord) - 15} чел."
                full_msg += f"\n\n⚠️ **Нет в Discord, но есть в таблице:**\n{missing_list_str}"

            await logger.sort_uf_sheet_async(guild_id=guild_id)
            full_msg += "\n\n✨ Список UF отсортирован по алфавиту."

            await interaction.edit_original_response(content=full_msg)
            
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Произошла ошибка при сохранении: {e}")
            print(f"Ошибка /uf: {e}")

    @app_commands.command(name='balance_update', description="Обновление таблицы Balance новыми участниками")
    @app_commands.default_permissions(administrator=True)
    async def balance_update_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("⏳ Сверяю список участников с таблицей Balance...")
        try:
            guild_id = interaction.guild.id if interaction.guild else None
            backup_buffer, backup_filename = await logger.export_balance_sheet_async(guild_id=guild_id)
            if backup_buffer:
                await interaction.channel.send("📦 Резервная копия Balance:", file=discord.File(fp=backup_buffer, filename=backup_filename))
                backup_buffer.close()

            all_members = []
            async for member in interaction.guild.fetch_members(limit=None):
                if not member.bot:
                    all_members.append(member)
            
            new_count = await logger.update_balance_rows_async(all_members, guild_id=guild_id)
            await interaction.edit_original_response(content=f"✅ Обновление Balance завершено! Добавлено новых участников: **{new_count}**")
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Ошибка при обновлении Balance: {e}")

    @app_commands.command(name='balance_archive', description="Архивация балансов (C->D, очистка контента)")
    @app_commands.default_permissions(administrator=True)
    async def balance_archive_command(self, interaction: discord.Interaction):
        await interaction.response.send_message("⏳ Архивация балансов и очистка контента... Это может занять время.")
        try:
            guild_id = interaction.guild.id if interaction.guild else None
            backup_buffer, backup_filename = await logger.export_balance_sheet_async(guild_id=guild_id)
            if backup_buffer:
                await interaction.channel.send("📦 Резервная копия Balance ПЕРЕД архивацией:", file=discord.File(fp=backup_buffer, filename=backup_filename))
                backup_buffer.close()

            success = await logger.archive_balance_sheet_async(guild_id=guild_id)
            if success:
                await interaction.edit_original_response(content="✅ Архивация завершена! Текущие балансы перенесены в архив, контентные столбцы очищены.")
            else:
                await interaction.edit_original_response(content="❌ Ошибка при выполнении архивации в таблице.")
                
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Ошибка: {e}")

    @app_commands.command(name='withdraw_money', description="Обнуление баланса пользователя (снятие денег)")
    @app_commands.describe(user="ID или упоминание пользователя")
    @app_commands.default_permissions(administrator=True)
    async def withdraw_money_command(self, interaction: discord.Interaction, user: str):
        match = re.search(r'\d+', user)
        target_id = match.group(0) if match else user

        await interaction.response.send_message(f"⏳ Обрабатываю снятие для ID `{target_id}`...")
        try:
            guild_id = interaction.guild.id if interaction.guild else None
            backup_buffer, backup_filename = await logger.export_balance_sheet_async(guild_id=guild_id)
            if backup_buffer:
                await interaction.channel.send("📦 Резервная копия Balance перед снятием:", file=discord.File(fp=backup_buffer, filename=backup_filename))
                backup_buffer.close()

            old_balance = await logger.withdraw_user_balance_async(target_id, interaction.user.id, interaction.user.display_name, guild_id=guild_id)
            if old_balance is not None:
                await interaction.edit_original_response(content=f"✅ **Успешное снятие!**\n👤 Пользователь: <@{target_id}>\n💰 Баланс был: **{format_balance(old_balance)}**\n📉 Текущий баланс: **0**")
            else:
                await interaction.edit_original_response(content=f"❌ Пользователь с ID `{target_id}` не найден в таблице.")
        except Exception as e:
            await interaction.edit_original_response(content=f"❌ Ошибка: {e}")

    @app_commands.command(name='withdrawal_request', description="Заявка на вывод средств")
    async def withdrawal_request(self, interaction: discord.Interaction):
        if not await check_user_permissions(interaction): return
        user_id = interaction.user.id
        guild_id = interaction.guild.id if interaction.guild else None
        await interaction.response.defer()
        balance = await logger.get_user_balance_async(user_id, guild_id=guild_id)
        
        try:
            clean_bal = str(balance).replace(' ', '').replace(',', '').replace('\xa0', '').strip() if balance else "0"
            bal_float = float(clean_bal)
        except:
            bal_float = 0
            
        if balance is None or bal_float <= 0:
            return await interaction.followup.send(f"❌ {interaction.user.mention}, у вас нет средств для вывода или вы не найдены в таблице.")

        settings = load_settings()
        channel_id = get_setting(settings, guild_id, 'withdraw_channel_id')
        role_id = get_setting(settings, guild_id, 'withdraw_role_id')
        
        if not channel_id:
            return await interaction.followup.send("❌ Канал для вывода не настроен администратором.")
        
        channel = interaction.guild.get_channel(channel_id) if guild_id else self.bot.get_channel(channel_id)
        if not channel:
            return await interaction.followup.send("❌ Не удалось найти канал для вывода.")
        
        role = interaction.guild.get_role(role_id) if role_id and interaction.guild else None
        role_mention = role.mention if role else "@everyone"
        
        formatted_bal = format_balance(balance)
        embed = discord.Embed(
            title="💰 Заявка на вывод средств",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Пользователь", value=f"{interaction.user.mention} ({interaction.user.display_name})", inline=False)
        embed.add_field(name="ID", value=f"`{interaction.user.id}`", inline=True)
        embed.add_field(name="Текущий баланс", value=f"**{formatted_bal}**", inline=True)
        
        await channel.send(content=f"🔔 {role_mention} Новая заявка!", embed=embed)
        await interaction.followup.send(f"✅ {interaction.user.mention}, ваша заявка на вывод (**{formatted_bal}**) отправлена в соответствующий канал.")

async def setup(bot):
    await bot.add_cog(BalanceCog(bot))
