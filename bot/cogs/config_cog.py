# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import re

from bot.utils import (
    load_settings,
    save_settings,
    get_setting,
    set_setting,
    remove_setting,
    get_allowed_channel_ids
)

class ConfigCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='config_call', description="Настройка каналов для сборов Call (добавление/удаление)")
    @app_commands.default_permissions(administrator=True)
    async def config_call(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        settings = load_settings()
        guild_id = interaction.guild.id if interaction.guild else None
        channel_ids = get_allowed_channel_ids(settings, 'call', guild_id)
        
        if channel:
            if channel.id in channel_ids:
                channel_ids.remove(channel.id)
                action = f"❌ Канал {channel.mention} удален из списка разрешенных для Call."
            else:
                channel_ids.append(channel.id)
                action = f"✅ Канал {channel.mention} добавлен в список разрешенных для Call."
            
            set_setting(settings, guild_id, 'call_channel_ids', channel_ids)
            remove_setting(settings, guild_id, 'call_channel_id')
        else:
            remove_setting(settings, guild_id, 'call_channel_ids')
            remove_setting(settings, guild_id, 'call_channel_id')
            action = "✅ Все ограничения по каналам для Call сняты (команда доступна везде)."
            channel_ids = []
            
        save_settings(settings)
        
        valid_channels = [cid for cid in channel_ids if interaction.guild.get_channel(cid) is not None]
        if valid_channels:
            mentions = ", ".join([f"<#{cid}>" for cid in valid_channels])
            msg = f"{action}\nТекущие разрешенные каналы: {mentions}"
        else:
            msg = action
            
        await interaction.response.send_message(msg)

    @app_commands.command(name='config_zvz', description="Настройка каналов и роли для ZvZ")
    @app_commands.default_permissions(administrator=True)
    async def config_zvz(self, interaction: discord.Interaction, channel: discord.TextChannel = None, role: discord.Role = None):
        settings = load_settings()
        guild_id = interaction.guild.id if interaction.guild else None
        msg = []
        
        if role:
            set_setting(settings, guild_id, 'zvz_role_id', role.id)
            msg.append(f"Минимальная роль установлена: {role.mention}")
        
        if channel:
            channel_ids = get_allowed_channel_ids(settings, 'zvz', guild_id)
            if channel.id in channel_ids:
                channel_ids.remove(channel.id)
                msg.append(f"Канал {channel.mention} удален из списка разрешенных.")
            else:
                channel_ids.append(channel.id)
                msg.append(f"Канал {channel.mention} добавлен в список разрешенных.")
            
            set_setting(settings, guild_id, 'zvz_channel_ids', channel_ids)
            remove_setting(settings, guild_id, 'zvz_channel_id')
            
        if channel is None and role is None:
            remove_setting(settings, guild_id, 'zvz_channel_ids')
            remove_setting(settings, guild_id, 'zvz_channel_id')
            remove_setting(settings, guild_id, 'zvz_role_id')
            msg.append("Все ограничения по каналам и роли для ZvZ сняты.")
            
        save_settings(settings)
        
        channel_ids = [cid for cid in get_allowed_channel_ids(settings, 'zvz', guild_id) if interaction.guild.get_channel(cid) is not None]
        role_id = get_setting(settings, guild_id, 'zvz_role_id')
        
        state_info = []
        if channel_ids:
            mentions = ", ".join([f"<#{cid}>" for cid in channel_ids])
            state_info.append(f"• Разрешенные каналы: {mentions}")
        else:
            state_info.append("• Разрешенные каналы: все (ограничений нет)")
            
        if role_id:
            r = interaction.guild.get_role(role_id)
            if r:
                state_info.append(f"• Минимальная роль: {r.mention}")
            else:
                state_info.append("• Минимальная роль: не настроена")
        else:
            state_info.append("• Минимальная роль: нет ограничений")
            
        await interaction.response.send_message(
            f"✅ **Настройки ZvZ обновлены:**\n" + "\n".join(msg) + "\n\n**Текущий статус:**\n" + "\n".join(state_info)
        )

    @app_commands.command(name='config_roum', description="Настройка каналов и роли для Roum")
    @app_commands.default_permissions(administrator=True)
    async def config_roum(self, interaction: discord.Interaction, channel: discord.TextChannel = None, role: discord.Role = None):
        settings = load_settings()
        guild_id = interaction.guild.id if interaction.guild else None
        msg = []
        
        if role:
            set_setting(settings, guild_id, 'roum_role_id', role.id)
            msg.append(f"Минимальная роль установлена: {role.mention}")
        
        if channel:
            channel_ids = get_allowed_channel_ids(settings, 'roum', guild_id)
            if channel.id in channel_ids:
                channel_ids.remove(channel.id)
                msg.append(f"Канал {channel.mention} удален из списка разрешенных.")
            else:
                channel_ids.append(channel.id)
                msg.append(f"Канал {channel.mention} добавлен в список разрешенных.")
            
            set_setting(settings, guild_id, 'roum_channel_ids', channel_ids)
            remove_setting(settings, guild_id, 'roum_channel_id')
            
        if channel is None and role is None:
            remove_setting(settings, guild_id, 'roum_channel_ids')
            remove_setting(settings, guild_id, 'roum_channel_id')
            remove_setting(settings, guild_id, 'roum_role_id')
            msg.append("Все ограничения по каналам и роли для Roum сняты.")
            
        save_settings(settings)
        
        channel_ids = [cid for cid in get_allowed_channel_ids(settings, 'roum', guild_id) if interaction.guild.get_channel(cid) is not None]
        role_id = get_setting(settings, guild_id, 'roum_role_id')
        
        state_info = []
        if channel_ids:
            mentions = ", ".join([f"<#{cid}>" for cid in channel_ids])
            state_info.append(f"• Разрешенные каналы: {mentions}")
        else:
            state_info.append("• Разрешенные каналы: все (ограничений нет)")
            
        if role_id:
            r = interaction.guild.get_role(role_id)
            if r:
                state_info.append(f"• Минимальная роль: {r.mention}")
            else:
                state_info.append("• Минимальная роль: не настроена")
        else:
            state_info.append("• Минимальная роль: нет ограничений")
            
        await interaction.response.send_message(
            f"✅ **Настройки Roum обновлены:**\n" + "\n".join(msg) + "\n\n**Текущий статус:**\n" + "\n".join(state_info)
        )

    @app_commands.command(name='config_user', description="Настройка разрешенных каналов и роли для обычных пользователей")
    @app_commands.describe(channel="Канал для команд (переключатель)", role="Минимальная роль для обычных команд (ограничение)")
    @app_commands.default_permissions(administrator=True)
    async def config_user(self, interaction: discord.Interaction, channel: discord.TextChannel = None, role: discord.Role = None):
        settings = load_settings()
        guild_id = interaction.guild.id if interaction.guild else None
        msg = []
        
        if role is not None:
            set_setting(settings, guild_id, 'user_role_id', role.id)
            msg.append(f"Минимальная роль для обычных пользователей установлена: {role.mention}")
            
        if channel is not None:
            channel_ids = get_allowed_channel_ids(settings, 'user', guild_id)
            if channel.id in channel_ids:
                channel_ids.remove(channel.id)
                msg.append(f"Канал {channel.mention} удален из списка разрешенных для обычных пользователей.")
            else:
                channel_ids.append(channel.id)
                msg.append(f"Канал {channel.mention} добавлен в список разрешенных для обычных пользователей.")
            set_setting(settings, guild_id, 'user_channel_ids', channel_ids)
            remove_setting(settings, guild_id, 'user_channel_id')
            
        if channel is None and role is None:
            remove_setting(settings, guild_id, 'user_channel_ids')
            remove_setting(settings, guild_id, 'user_channel_id')
            remove_setting(settings, guild_id, 'user_role_id')
            msg.append("Все ограничения по каналам и роли для обычных пользователей сняты.")
            
        save_settings(settings)
        
        channel_ids = [cid for cid in get_allowed_channel_ids(settings, 'user', guild_id) if interaction.guild.get_channel(cid) is not None]
        role_id = get_setting(settings, guild_id, 'user_role_id')
        
        state_info = []
        if channel_ids:
            mentions = ", ".join([f"<#{cid}>" for cid in channel_ids])
            state_info.append(f"• Разрешенные каналы: {mentions}")
        else:
            state_info.append("• Разрешенные каналы: все (ограничений нет)")
            
        if role_id:
            r = interaction.guild.get_role(role_id)
            if r:
                state_info.append(f"• Минимальная роль: {r.mention}")
            else:
                state_info.append("• Минимальная роль: не настроена")
        else:
            state_info.append("• Минимальная роль: нет ограничений")
            
        await interaction.response.send_message(
            f"✅ **Настройки доступа обновлены:**\n" + "\n".join(msg) + "\n\n**Текущий статус:**\n" + "\n".join(state_info)
        )

    @app_commands.command(name='config_sheet', description="Настройка ссылки на Google Таблицу для определенной таблицы")
    @app_commands.describe(
        table_type="Тип таблицы, которую вы хотите настроить",
        url="Полная ссылка на Google Таблицу (включая gid, если нужно)"
    )
    @app_commands.choices(table_type=[
        app_commands.Choice(name="Call сборы", value="call"),
        app_commands.Choice(name="ZvZ сборы", value="zvz"),
        app_commands.Choice(name="Roum сборы", value="roum"),
        app_commands.Choice(name="UF участники", value="uf"),
        app_commands.Choice(name="Balance баланс", value="balance"),
        app_commands.Choice(name="LogBalance лог выводов", value="LogBalance"),
        app_commands.Choice(name="LogSplit лог сплитов", value="LogSplit"),
    ])
    @app_commands.default_permissions(administrator=True)
    async def config_sheet(self, interaction: discord.Interaction, table_type: app_commands.Choice[str], url: str):
        settings = load_settings()
        guild_id = interaction.guild.id if interaction.guild else None
        
        match_id = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if not match_id:
            return await interaction.response.send_message("❌ Неверный формат ссылки на Google Таблицу. Ссылка должна содержать '/spreadsheets/d/ID'.", ephemeral=True)
        
        spreadsheet_id = match_id.group(1)
        match_gid = re.search(r'[#&?]gid=([0-9]+)', url)
        gid = match_gid.group(1) if match_gid else None
        
        sheet_config = get_setting(settings, guild_id, 'sheet_config', {})
        sheet_config[table_type.value] = {
            'url': url,
            'spreadsheet_id': spreadsheet_id,
            'gid': gid
        }
        set_setting(settings, guild_id, 'sheet_config', sheet_config)
        
        if table_type.value == 'balance':
            set_setting(settings, guild_id, 'spreadsheet_url', url)
            set_setting(settings, guild_id, 'spreadsheet_id', spreadsheet_id)
            
        save_settings(settings)
        
        gid_msg = f", ID листа (gid): `{gid}`" if gid else ""
        await interaction.response.send_message(f"✅ Ссылка для **{table_type.name}** обновлена!\nID таблицы: `{spreadsheet_id}`{gid_msg}")

    @app_commands.command(name='set_withdraw', description="Настройка канала и роли для заявок на вывод")
    @app_commands.default_permissions(administrator=True)
    async def set_withdraw(self, interaction: discord.Interaction, channel: discord.TextChannel = None, role: discord.Role = None):
        settings = load_settings()
        guild_id = interaction.guild.id if interaction.guild else None
        msg = []
        if channel:
            set_setting(settings, guild_id, 'withdraw_channel_id', channel.id)
            msg.append(f"Канал установлен: {channel.mention}")
        else:
            remove_setting(settings, guild_id, 'withdraw_channel_id')
            msg.append("Ограничение канала снято.")
            
        if role:
            set_setting(settings, guild_id, 'withdraw_role_id', role.id)
            msg.append(f"Роль для пинга установлена: {role.mention}")
        else:
            remove_setting(settings, guild_id, 'withdraw_role_id')
            msg.append("Ограничение по роли снято.")
            
        save_settings(settings)
        await interaction.response.send_message("✅ **Настройки вывода обновлены:**\n" + "\n".join(msg))

    @app_commands.command(name='save_role', description="Настройка роли, участники которой могут сохранять шаблоны сборов")
    @app_commands.describe(role="Упоминание роли (оставьте пустым для удаления ограничения по роли)")
    @app_commands.default_permissions(administrator=True)
    async def save_role_command(self, interaction: discord.Interaction, role: discord.Role = None):
        settings = load_settings()
        guild_id = interaction.guild.id if interaction.guild else None
        if role:
            set_setting(settings, guild_id, 'save_role_id', role.id)
            save_settings(settings)
            await interaction.response.send_message(f"✅ Роль для сохранения шаблонов успешно настроена: {role.mention}. Теперь сохранять шаблоны могут администраторы и пользователи с этой ролью.")
        else:
            remove_setting(settings, guild_id, 'save_role_id')
            save_settings(settings)
            await interaction.response.send_message("✅ Ограничение по роли для сохранения шаблонов снято. Теперь сохранять шаблоны сборов могут только администраторы.")

    @app_commands.command(name='info_ad', description="Справка по командам администратора")
    @app_commands.default_permissions(administrator=True)
    async def admin_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        admin_commands = (
            "**`/config_call [#channel]`**\n"
            "Настроить канал для команды `/call`.\n\n"
            "**`/config_zvz [#channel] [@role]`**\n"
            "Настроить канал и минимальную роль для `/zvz`.\n\n"
            "**`/config_roum [#channel] [@role]`**\n"
            "Настроить канал и минимальную роль для `/roum`.\n\n"
            "**`/config_user [#channel] [@role]`**\n"
            "Настроить канал и минимальную роль для обычных пользовательских команд.\n\n"
            "**`/config_sheet [URL]`**\n"
            "Настроить ссылку на Google Таблицу.\n\n"
            "**`/config_obj_channel [#channel]`**\n"
            "Настроить канал для отслеживания игровых объектов.\n\n"
            "**`/uf`**\n"
            "Синхронизация участников (показывает ливнувших) + Сортировка.\n\n"
            "**`/balance_update`**\n"
            "Добавление новых участников в баланс.\n\n"
            "**`/balance_archive`**\n"
            "Архивация, очистка контента и сортировка балансов.\n\n"
            "**`/split`**\n"
            "Начисление долей за контент через окно:\n"
            " - Строка 1: Название сплита\n"
            " - Строка 2: Организатор\n"
            " - Строка 3+: ID Ник Сумма (один на строку)\n\n"
            "**`/balance_uf`**\n"
            "Список всех балансов (таблица).\n\n"
            "**`/balance_uf_teg`**\n"
            "Пинг всех участников с балансом > 1 000 000.\n\n"
            "**`/withdraw_money [ID]`**\n"
            "Обнулить баланс пользователя.\n\n"
            "**`/activity_all [week/month]`**\n"
            "Общая статистика активности.\n\n"
            "**`/set_withdraw [#channel] [@role]`**\n"
            "Настроить канал и роль для уведомлений о выводе.\n\n"
            "**`/update_grev [file]`**\n"
            "Синхронизация таблицы «Грев» и опциональный импорт лога сундука.\n\n"
            "**`/check_grev [user]`**\n"
            "Просмотр балансов «Грев» (пинг должников с балансом < 100).\n\n"
            "**🌀 АВАЛОНСКИЕ ПОРТАЛЫ:**\n"
            "• **`/ava_portal_sync`** — Синхронизировать порталы Авалона с Google Таблицей."
        )

        embed = discord.Embed(
            title="📂 United Force Bot — Панель Администратора",
            color=discord.Color.red(),
            description="**🛠️ КОМАНДЫ УПРАВЛЕНИЯ:**\n\n" + admin_commands
        )
        
        embed.set_footer(text="По всем вопросам обращайтесь к администраторам.")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
