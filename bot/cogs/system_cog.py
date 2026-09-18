# -*- coding: utf-8 -*-
import os
import gc
import time
import psutil
import discord
from discord.ext import commands
from discord import app_commands

BOT_START_TIME = time.time()
DISCLOUD_RAM_LIMIT_MB = 100.0

def get_memory_info():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    rss_mb = mem_info.rss / (1024 * 1024)
    vms_mb = mem_info.vms / (1024 * 1024)
    percent = (rss_mb / DISCLOUD_RAM_LIMIT_MB) * 100.0
    return {
        'rss_mb': rss_mb,
        'vms_mb': vms_mb,
        'percent': percent
    }

def format_uptime(seconds: float) -> str:
    secs = int(seconds)
    days = secs // 86400
    secs %= 86400
    hours = secs // 3600
    secs %= 3600
    mins = secs // 60
    secs %= 60
    parts = []
    if days > 0:
        parts.append(f"{days} д.")
    if hours > 0 or days > 0:
        parts.append(f"{hours} ч.")
    parts.append(f"{mins} мин.")
    parts.append(f"{secs} сек.")
    return " ".join(parts)

def perform_cleanup(bot) -> dict:
    """Выполняет полную очистку неактивных сборов, сброс кэшей и сборку мусора"""
    mem_before = get_memory_info()['rss_mb']
    
    # 1. Очистка старых / завершенных сборов из active_calls
    now = time.time()
    removed_calls_count = 0
    if hasattr(bot, 'active_calls') and isinstance(bot.active_calls, dict):
        keys_to_remove = []
        for k, call_data in list(bot.active_calls.items()):
            # Удаляем если явно помечен finished
            if call_data.get('finished'):
                keys_to_remove.append(k)
                continue
            # Или если контент завершился более 3 часов назад
            event_time = call_data.get('event_time') or call_data.get('created_at')
            duration = call_data.get('duration') or 60
            if event_time and (now >= event_time + (duration * 60) + 10800):
                keys_to_remove.append(k)
        
        for k in keys_to_remove:
            bot.active_calls.pop(k, None)
        removed_calls_count = len(keys_to_remove)

    # 2. Вызов сборщика мусора Python
    unreachable = gc.collect()
    
    # 3. Замер после
    mem_after = get_memory_info()['rss_mb']
    freed_mb = max(0.0, mem_before - mem_after)
    
    return {
        'before_mb': mem_before,
        'after_mb': mem_after,
        'freed_mb': freed_mb,
        'unreachable': unreachable,
        'removed_calls': removed_calls_count
    }

class MemoryActionView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.bot = bot

    @discord.ui.button(label="Очистить память", style=discord.ButtonStyle.danger, emoji="🧹")
    async def clean_memory_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Только администраторы могут очищать память.", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        res = perform_cleanup(self.bot)
        
        embed = discord.Embed(
            title="🧹 Память успешно оптимизирована",
            color=discord.Color.green()
        )
        embed.add_field(name="📉 Освобождено", value=f"`{res['freed_mb']:.2f} МБ`", inline=True)
        embed.add_field(name="📊 Текущая RAM", value=f"`{res['after_mb']:.2f} МБ` / 100 МБ ({res['after_mb']:.1f}%)", inline=True)
        embed.add_field(name="🗑️ Очищено объектов GC", value=f"`{res['unreachable']}`", inline=True)
        embed.add_field(name="📋 Удалено устаревших сборов", value=f"`{res['removed_calls']}` ключей", inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

class SystemCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='memory', description="Мониторинг оперативной памяти (RAM) и состояния бота")
    async def memory_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        
        mem = get_memory_info()
        uptime = format_uptime(time.time() - BOT_START_TIME)
        
        active_calls_count = 0
        unique_calls = set()
        if hasattr(self.bot, 'active_calls'):
            active_calls_count = len(self.bot.active_calls)
            for v in self.bot.active_calls.values():
                if isinstance(v, dict) and 'id' in v:
                    unique_calls.add(v['id'])
                    
        # Цветовая индикация нагрузки
        if mem['rss_mb'] < 50.0:
            color = discord.Color.green()
            status_text = "🟢 Отличное (низкое потребление)"
        elif mem['rss_mb'] < 80.0:
            color = discord.Color.gold()
            status_text = "🟡 Умеренное"
        else:
            color = discord.Color.red()
            status_text = "🔴 Высокое (близко к лимиту 100 МБ!)"

        embed = discord.Embed(
            title="🖥️ Состояние системы и памяти",
            description=f"**Статус контейнера Discloud:** {status_text}",
            color=color
        )
        
        bar_len = 15
        filled = int(bar_len * (min(100.0, mem['percent']) / 100.0))
        progress_bar = "█" * filled + "░" * (bar_len - filled)
        
        embed.add_field(
            name="💾 Оперативная память (RAM)",
            value=(
                f"`[{progress_bar}]` **{mem['percent']:.1f}%**\n"
                f"• **Использовано (RSS):** `{mem['rss_mb']:.2f} МБ` / `{DISCLOUD_RAM_LIMIT_MB:.0f} МБ`\n"
                f"• **Виртуальная (VMS):** `{mem['vms_mb']:.2f} МБ`"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Процесс и кэш",
            value=(
                f"• **Аптайм бота:** {uptime}\n"
                f"• **Серверов (Guilds):** {len(self.bot.guilds)}\n"
                f"• **Активных сборов:** {len(unique_calls)} шт. ({active_calls_count} ссылок в кэше)\n"
                f"• **Сборщик мусора (GC):** {gc.get_count()}"
            ),
            inline=False
        )
        
        embed.set_footer(text="Лимит хостинга Discloud: 100 МБ RAM")
        
        view = MemoryActionView(self.bot)
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name='clean_memory', description="Принудительная очистка памяти и завершенных сборов (Админ)")
    @app_commands.default_permissions(administrator=True)
    async def clean_memory_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        
        res = perform_cleanup(self.bot)
        
        embed = discord.Embed(
            title="🧹 Память успешно очищена",
            color=discord.Color.green()
        )
        embed.add_field(name="📉 Освобождено памяти", value=f"**{res['freed_mb']:.2f} МБ**", inline=True)
        embed.add_field(name="📊 Текущая RAM", value=f"`{res['after_mb']:.2f} МБ` / 100 МБ", inline=True)
        embed.add_field(name="🗑️ Сборщик мусора", value=f"Очищено {res['unreachable']} объектов", inline=True)
        embed.add_field(name="📋 Завершённые сборы", value=f"Удалено {res['removed_calls']} ключей", inline=True)
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name='table_status', description="Проверка статуса подключения к Google Таблицам и локальному Excel")
    async def table_status_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        from bot import config, logger
        import os

        embed = discord.Embed(
            title="📊 Статус логирования в таблицы",
            color=discord.Color.blue()
        )

        # 1. Проверка Google Sheets
        cred_path = config.CREDENTIALS_FILE
        if not os.path.exists(cred_path):
            embed.add_field(
                name="Google Таблицы",
                value="🔴 Файл `credentials.json` не найден в папке бота.",
                inline=False
            )
        else:
            try:
                client = logger.get_gspread_client(force_refresh=True)
                if not client:
                    raise Exception("Не удалось инициализировать gspread клиент")
                sheet_id = logger.get_spreadsheet_id(interaction.guild_id)
                sp = client.open_by_key(sheet_id)
                embed.add_field(
                    name="Google Таблицы",
                    value=f"🟢 **Подключено успешно!**\n• Таблица: `{sp.title}`\n• ID: `{sheet_id[:15]}...`",
                    inline=False
                )
            except Exception as e:
                err_str = str(e)
                if "invalid_grant" in err_str or "Invalid JWT Signature" in err_str:
                    diag = (
                        "🔴 **Ошибка авторизации Google API (Invalid JWT Signature):**\n"
                        "Ключ в `credentials.json` устарел или был удален в Google Cloud Console.\n"
                        "👉 **Как исправить:**\n"
                        "1. Зайдите в Google Cloud Console -> IAM & Admin -> Service Accounts.\n"
                        "2. Выберите сервисный аккаунт (`bot-dis@bot-discortd.iam.gserviceaccount.com`).\n"
                        "3. Перейдите во вкладку **Keys** -> **Add Key** -> **Create new key** (JSON).\n"
                        "4. Скачайте файл и замените им `credentials.json` в папке бота."
                    )
                else:
                    diag = f"🔴 **Ошибка Google API:** `{err_str[:300]}`"
                embed.add_field(name="Google Таблицы", value=diag, inline=False)

        # 2. Проверка локального Excel
        local_file = getattr(logger, 'LOCAL_EXCEL_FILE', 'calls_log.xlsx')
        if os.path.exists(local_file):
            size_kb = os.path.getsize(local_file) / 1024
            mtime = time.strftime('%d.%m.%Y %H:%M:%S', time.localtime(os.path.getmtime(local_file)))
            embed.add_field(
                name="Локальный Excel (Резервный)",
                value=f"🟢 **Активен (`{local_file}`)**\n• Размер: `{size_kb:.1f} КБ`\n• Изменен: `{mtime}`\n• Сюда автоматически дублируются все сборы!",
                inline=False
            )
        else:
            embed.add_field(
                name="Локальный Excel (Резервный)",
                value=f"⚪ Файл `{local_file}` будет создан автоматически при первом сборе.",
                inline=False
            )

        embed.set_footer(text="United Force • Диагностика логирования")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name='export_calls', description="Скачать локальный файл Excel (calls_log.xlsx) со всеми записями сборов")
    async def export_calls_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        from bot import logger
        import os

        local_file = getattr(logger, 'LOCAL_EXCEL_FILE', 'calls_log.xlsx')
        if not os.path.exists(local_file):
            return await interaction.followup.send("⚠️ Файл `calls_log.xlsx` пока не создан. Он появится после создания хотя бы одного сбора.", ephemeral=True)

        try:
            file_to_send = discord.File(local_file, filename="calls_log.xlsx")
            await interaction.followup.send("📁 **Локальный файл с записями сборов:**", file=file_to_send)
        except Exception as e:
            await interaction.followup.send(f"❌ Ошибка отправки файла: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SystemCog(bot))

