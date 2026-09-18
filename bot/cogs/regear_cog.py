# -*- coding: utf-8 -*-
import os
import json
import time
import random
import string
import re
import discord
from discord.ext import commands
from discord import app_commands

from bot.utils import (
    load_settings,
    save_settings,
    get_setting,
    set_setting,
    check_user_permissions
)

# --- СПИСКИ ЭКИПИРОВКИ ДЛЯ АВТОДОПОЛНЕНИЯ (ALBION ONLINE) ---

WEAPONS_LIST = [
    # Мечи
    "Палаш", "Двуручный меч", "Парные мечи", "Кларент", "Меч резни", "Галатины", "Королевский меч", "Клинок бесконечности",
    # Топоры
    "Боевой топор", "Большой топор", "Алебарда", "Зов падальщика", "Адская коса", "Медвежьи лапы", "Топор разрушителя", "Жнец кристального сердца",
    # Молоты
    "Кузнечные молоты", "Большой молот", "Молот полюса", "Гробничный молот", "Страж рощи", "Молот правосудия", "Длань правосудия",
    # Булавы
    "Булава", "Тяжелая булава", "Моргенштерн", "Бедокур", "Инкубаторская булава (кувалда инкуба)", "Камбрийская булава", "Клятвохранитель",
    # Копья
    "Копье", "Пика", "Глефа", "Цапля", "Копье охотника за духом", "Копье Троицы", "Рассветная пика",
    # Кинжалы
    "Кинжал", "Парные кинжалы", "Когти", "Кровопускатель", "Смертоносный выпад", "Истязатель", "Клыки демона",
    # Боевые перчатки
    "Боевые перчатки", "Боевые наручи", "Шипастые рукавицы", "Разрушители", "Адские длани", "Рукавицы Авалона", "Идущие-по-звездам",
    # Боевые шесты
    "Боевой шест", "Двуострый посох", "Посох железной воли", "Посох черного монаха", "Коса душ", "Посох равновесия", "Искатель Грааля",
    # Огненные посохи
    "Огненный посох", "Большой огненный посох", "Адский посох", "Посох лесного пожара", "Посох серного огня", "Посох пылающего рассвета", "Песнь рассвета",
    # Морозные посохи
    "Морозный посох", "Большой морозный посох", "Ледяной посох", "Посох инея", "Посох града", "Призма вечного холода", "Морозный осколок",
    # Проклятые посохи
    "Проклятый посох", "Большой проклятый посох", "Демонический посох", "Посох обречения", "Проклятый череп", "Посох призывателя теней", "Посох проклятия",
    # Мистические посохи
    "Мистический посох", "Большой мистический посох", "Загадочный посох", "Посох ведьмы", "Посох черной дыры", "Зловещий посох", "Астральный посох",
    # Луки
    "Лук", "Длинный лук", "Боевой лук", "Лук шепота", "Плачущий лук", "Лук Бадона", "Туманный пронзатель",
    # Арбалеты
    "Арбалет", "Тяжелый арбалет", "Легкий арбалет", "Плачущий арбалет", "Осадный арбалет", "Арбалет творца", "Самострелы",
    # Посохи природы
    "Посох природы", "Большой посох природы", "Дикий посох", "Друидский посох", "Посох порчи", "Посох железного корня", "Древожитель",
    # Священные посохи
    "Священный посох", "Большой священный посох", "Божественный посох", "Посох жизни", "Посох падших", "Посох искупления", "Благодатный посох",
    # Посохи оборотня
    "Посох скрывающейся тени (Пантера)", "Посох лешего (Энт)", "Посох искаженного духа (Птица)", "Посох лунного зверя (Оборотень)", "Посох зова крови (Медведь)", "Посох пробуждения земли (Голем)"
]

OFFHANDS_LIST = [
    # Щиты
    "Щит", "Лицевой щит", "Саркофаг", "Щит защитника", "Астральный эгида",
    # Факелы
    "Факел", "Могильная свеча", "Рог охотника", "Корень природы", "Звездный оракул",
    # Фолианты
    "Книга заклинаний", "Око тайн", "Череп-трофей", "Искаженный визирь", "Небесный свиток"
]

HEADGEAR_LIST = [
    # Латные
    "Шлем солдата", "Шлем рыцаря", "Шлем хранителя", "Могильный шлем", "Демонический шлем", "Шлем вершителя", "Шлем доблести", "Сумеречный шлем", "Королевский шлем",
    # Кожаные
    "Капюшон наемника", "Капюшон охотника", "Капюшон убийцы", "Капюшон лазутчика", "Капюшон призрака", "Адский капюшон", "Капюшон упорства", "Капюшон мглы", "Королевский капюшон",
    # Тканевые
    "Колпак ученого", "Колпак клирика", "Колпак чародея", "Дьявольский колпак", "Колпак сектанта", "Колпак друида", "Колпак чистоты", "Колпак ткача фей", "Королевский колпак"
]

ARMOR_LIST = [
    # Латные
    "Броня солдата", "Броня рыцаря", "Броня хранителя", "Могильная броня", "Демоническая броня", "Броня вершителя", "Броня доблести", "Сумеречная броня", "Королевская броня",
    # Кожаные
    "Куртка наемника", "Куртка охотника", "Куртка убийцы", "Куртка лазутчика", "Куртка призрака", "Адская куртка", "Куртка упорства", "Куртка мглы", "Королевская куртка",
    # Тканевые
    "Мантия ученого", "Мантия клирика", "Мантия чародея", "Дьявольская мантия", "Мантия сектанта", "Мантия друида", "Мантия чистоты", "Мантия ткача фей", "Королевская мантия"
]

FOOTWEAR_LIST = [
    # Латные
    "Сапоги солдата", "Сапоги рыцаря", "Сапоги хранителя", "Могильные сапоги", "Демонические сапоги", "Сапоги вершителя", "Сапоги доблести", "Сумеречные сапоги", "Королевские сапоги",
    # Кожаные
    "Ботинки наемника", "Ботинки охотника", "Ботинки убийцы", "Ботинки лазутчика", "Ботинки призрака", "Адские ботинки", "Ботинки упорства", "Ботинки мглы", "Королевские ботинки",
    # Тканевые
    "Сандалии ученого", "Сандалии клирика", "Сандалии чародея", "Дьявольские сандалии", "Сандалии сектанта", "Сандалии друида", "Сандалии чистоты", "Сандалии ткача фей", "Королевские сандалии"
]

CAPES_LIST = [
    "Обычный плащ",
    "Плащ Лимхурста", "Плащ Мартлока", "Плащ Тетфорда", "Плащ Форта Стерлинг", "Плащ Бриджвоча", "Плащ Кэрлеона", "Плащ Бресилиена",
    "Плащ Нежити", "Плащ Демона", "Плащ Морганы", "Плащ Хранителя", "Плащ Еретика", "Авалонский плащ"
]


def load_regears():
    if os.path.exists('regears.json'):
        try:
            with open('regears.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки regears.json: {e}")
            return []
    return []

def save_regears(regears):
    try:
        with open('regears.json', 'w', encoding='utf-8') as f:
            json.dump(regears, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения regears.json: {e}")

class RegearRejectModal(discord.ui.Modal):
    def __init__(self, bot, regear_id, message):
        super().__init__(title=f"Отклонение заявки {regear_id}")
        self.bot = bot
        self.regear_id = regear_id
        self.message = message
        
        self.reason_input = discord.ui.TextInput(
            label="Причина отклонения",
            placeholder="Например: Не тот тир / Нет скриншота смерти",
            required=True,
            max_length=200
        )
        self.add_item(self.reason_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        reason = self.reason_input.value
        
        regears = load_regears()
        found = None
        for r in regears:
            if r['id'].lower() == self.regear_id.lower():
                found = r
                break
                
        if not found:
            return await interaction.followup.send(f"❌ Заявка `{self.regear_id}` не найдена!", ephemeral=True)
            
        found['status'] = '❌ Отклонено'
        found['reason'] = reason
        save_regears(regears)
        
        # Обновляем эмбед сообщения
        embed = self.message.embeds[0]
        new_embed = discord.Embed(
            title=embed.title,
            description=f"👤 **Игрок:** <@{found['user_id']}>\n📊 **Статус:** ❌ Отклонено (Отклонил: {interaction.user.mention})\n💬 **Причина:** {reason}",
            color=discord.Color.red()
        )
        for field in embed.fields:
            new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
        new_embed.set_footer(text=embed.footer.text)
        new_embed.timestamp = embed.timestamp
        if embed.image:
            new_embed.set_image(url=embed.image.url)
            
        await self.message.edit(embed=new_embed, view=None)
        
        # Уведомляем игрока в ЛС
        try:
            user = self.bot.get_user(found['user_id'])
            if not user:
                user = await self.bot.fetch_user(found['user_id'])
            if user:
                dm_embed = discord.Embed(
                    title="❌ Заявка на регир отклонена",
                    description=f"Ваша заявка **{found['id']}** ({found['role']}) была отклонена.\n💬 **Причина:** {reason}",
                    color=discord.Color.red()
                )
                await user.send(embed=dm_embed)
        except Exception as e:
            print(f"Не удалось отправить ЛС пользователю {found['user_id']}: {e}")
            
        await interaction.followup.send(f"❌ Заявка `{self.regear_id}` отклонена!", ephemeral=True)

class RegearPersistentView(discord.ui.View):
    def __init__(self, bot, status='⏳ Ожидание'):
        super().__init__(timeout=None)
        self.bot = bot
        self.status = status
        
        if status == '✅ Одобрено':
            for child in list(self.children):
                if child.custom_id in ["regear_approve_btn", "regear_reject_btn"]:
                    self.remove_item(child)
        elif status in ['❌ Отклонено', '📦 Выдано']:
            self.clear_items()

    @discord.ui.button(label="Одобрить", style=discord.ButtonStyle.green, custom_id="regear_approve_btn", emoji="✅")
    async def approve_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ У вас нет прав администратора (офицера)!", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        
        embed = interaction.message.embeds[0]
        footer_text = embed.footer.text if embed.footer else ""
        match = re.search(r"ID(?:\s+заявки)?:?\s*([A-Z0-9]+)", footer_text)
        if not match:
            return await interaction.followup.send("❌ Не удалось определить ID заявки из эмбеда!", ephemeral=True)
            
        regear_id = match.group(1)
        regears = load_regears()
        found = None
        for r in regears:
            if r['id'].lower() == regear_id.lower():
                found = r
                break
                
        if not found:
            return await interaction.followup.send(f"❌ Заявка `{regear_id}` не найдена в базе!", ephemeral=True)
            
        found['status'] = '✅ Одобрено'
        found['reason'] = None
        save_regears(regears)
        
        # Обновляем эмбед сообщения
        new_embed = discord.Embed(
            title=embed.title,
            description=f"👤 **Игрок:** <@{found['user_id']}>\n📊 **Статус:** ✅ Одобрено (Одобрил: {interaction.user.mention})",
            color=discord.Color.green()
        )
        for field in embed.fields:
            new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
        new_embed.set_footer(text=embed.footer.text)
        new_embed.timestamp = embed.timestamp
        if embed.image:
            new_embed.set_image(url=embed.image.url)
            
        view = RegearPersistentView(self.bot, status='✅ Одобрено')
        await interaction.message.edit(embed=new_embed, view=view)
        
        # Уведомляем игрока в ЛС
        try:
            user = self.bot.get_user(found['user_id'])
            if not user:
                user = await self.bot.fetch_user(found['user_id'])
            if user:
                dm_embed = discord.Embed(
                    title="✅ Заявка на регир одобрена!",
                    description=f"Ваша заявка **{found['id']}** ({found['role']}) была одобрена офицером!",
                    color=discord.Color.green()
                )
                await user.send(embed=dm_embed)
        except Exception as e:
            print(f"Не удалось отправить ЛС пользователю {found['user_id']}: {e}")
            
        await interaction.followup.send(f"✅ Заявка `{regear_id}` успешно одобрена!", ephemeral=True)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.red, custom_id="regear_reject_btn", emoji="❌")
    async def reject_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ У вас нет прав администратора (офицера)!", ephemeral=True)
            
        embed = interaction.message.embeds[0]
        footer_text = embed.footer.text if embed.footer else ""
        match = re.search(r"ID(?:\s+заявки)?:?\s*([A-Z0-9]+)", footer_text)
        if not match:
            return await interaction.response.send_message("❌ Не удалось определить ID заявки из эмбеда!", ephemeral=True)
            
        regear_id = match.group(1)
        
        # Открываем модальное окно
        await interaction.response.send_modal(RegearRejectModal(self.bot, regear_id, interaction.message))

    @discord.ui.button(label="Выдано", style=discord.ButtonStyle.blurple, custom_id="regear_issued_btn", emoji="📦")
    async def issued_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ У вас нет прав администратора (офицера)!", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        
        embed = interaction.message.embeds[0]
        footer_text = embed.footer.text if embed.footer else ""
        match = re.search(r"ID(?:\s+заявки)?:?\s*([A-Z0-9]+)", footer_text)
        if not match:
            return await interaction.followup.send("❌ Не удалось определить ID заявки из эмбеда!", ephemeral=True)
            
        regear_id = match.group(1)
        regears = load_regears()
        found = None
        for r in regears:
            if r['id'].lower() == regear_id.lower():
                found = r
                break
                
        if not found:
            return await interaction.followup.send(f"❌ Заявка `{regear_id}` не найдена в базе!", ephemeral=True)
            
        found['status'] = '📦 Выдано'
        save_regears(regears)
        
        # Обновляем эмбед сообщения
        new_embed = discord.Embed(
            title=embed.title,
            description=f"👤 **Игрок:** <@{found['user_id']}>\n📊 **Статус:** 📦 Выдано (Выдал: {interaction.user.mention})",
            color=discord.Color.blue()
        )
        for field in embed.fields:
            new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
        new_embed.set_footer(text=embed.footer.text)
        new_embed.timestamp = embed.timestamp
        if embed.image:
            new_embed.set_image(url=embed.image.url)
            
        await interaction.message.edit(embed=new_embed, view=None)
        
        # Уведомляем игрока в ЛС
        try:
            user = self.bot.get_user(found['user_id'])
            if not user:
                user = await self.bot.fetch_user(found['user_id'])
            if user:
                dm_embed = discord.Embed(
                    title="📦 Регир выдан!",
                    description=f"Ваш регир по заявке **{found['id']}** ({found['role']}) был успешно выдан!",
                    color=discord.Color.blue()
                )
                await user.send(embed=dm_embed)
        except Exception as e:
            print(f"Не удалось отправить ЛС пользователю {found['user_id']}: {e}")
            
        await interaction.followup.send(f"📦 Заявка `{regear_id}` успешно переведена в статус 'Выдано'!", ephemeral=True)

class RegearCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='config_regear_channel', description="Настройка канала для уведомлений по регирам (Админ)")
    @app_commands.describe(channel="Канал для публикации логов новых региров")
    async def config_regear_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Настройка доступна только администраторам сервера!", ephemeral=True)
            
        settings = load_settings()
        guild_id = interaction.guild.id if interaction.guild else None
        set_setting(settings, guild_id, 'regear_channel_id', channel.id)
        save_settings(settings)
        
        await interaction.response.send_message(f"✅ Канал для уведомлений по регирам успешно установлен: {channel.mention}", ephemeral=True)

    @app_commands.command(name='regear', description="Подать заявку на регир экипировки")
    @app_commands.describe(
        role="Ваша игровая роль в рейде",
        weapon="Ваше оружие / билд (например: Булава хранителя / Тяж мейс)",
        offhand="Левая рука (если применимо)",
        head="Голова (например: Капюшон солдата)",
        chest="Тело (например: Броня хранителя)",
        shoes="Ноги (например: Сандалии ученого)",
        cape="Плащ (например: Плащ Мартлока)",
        screenshot="Скриншот смерти / предметов"
    )
    @app_commands.choices(role=[
        app_commands.Choice(name="🛡️ Танк (Tank)", value="Танк (Tank)"),
        app_commands.Choice(name="💚 Хил (Healer)", value="Хил (Healer)"),
        app_commands.Choice(name="⚔️ ДД Ближний (Melee DPS)", value="ДД Ближний (Melee DPS)"),
        app_commands.Choice(name="🏹 ДД Дальний (Ranged DPS)", value="ДД Дальний (Ranged DPS)"),
        app_commands.Choice(name="🔮 Саппорт (Support)", value="Саппорт (Support)"),
        app_commands.Choice(name="🐾 Боевой маунт (Battle Mount)", value="Боевой маунт (Battle Mount)")
    ])
    async def regear_request(
        self,
        interaction: discord.Interaction,
        role: app_commands.Choice[str],
        weapon: str,
        offhand: str = None,
        head: str = None,
        chest: str = None,
        shoes: str = None,
        cape: str = None,
        screenshot: discord.Attachment = None
    ):
        if not await check_user_permissions(interaction):
            return
            
        settings = load_settings()
        guild_id = interaction.guild.id if interaction.guild else None
        channel_id = get_setting(settings, guild_id, 'regear_channel_id')
        
        target_channel = None
        if channel_id:
            target_channel = interaction.guild.get_channel(channel_id)
            
        # Если канал не настроен, шлем в текущий канал
        if not target_channel:
            target_channel = interaction.channel
            
        await interaction.response.defer(ephemeral=True)
        
        regear_id = "R" + "".join(random.choices(string.ascii_uppercase + string.digits, k=3))
        screenshot_url = screenshot.url if screenshot else None
        
        def val_or_none(val):
            return val if (val and val.strip()) else "Не указано"
            
        embed = discord.Embed(
            title=f"🛡️ ЗАЯВКА НА РЕГИР: [{regear_id}]",
            description=f"👤 **Игрок:** {interaction.user.mention}\n📊 **Статус:** ⏳ Ожидание",
            color=discord.Color.orange()
        )
        embed.add_field(name="🎖️ Роль", value=role.value, inline=True)
        embed.add_field(name="⚔️ Оружие", value=weapon, inline=True)
        embed.add_field(name="🛡️ Левая рука", value=val_or_none(offhand), inline=True)
        embed.add_field(name="🪖 Голова", value=val_or_none(head), inline=True)
        embed.add_field(name="👕 Тело", value=val_or_none(chest), inline=True)
        embed.add_field(name="👢 Ноги", value=val_or_none(shoes), inline=True)
        embed.add_field(name="🧥 Плащ", value=val_or_none(cape), inline=True)
        embed.set_footer(text=f"ID заявки: {regear_id} • Отправлено")
        embed.timestamp = discord.utils.utcnow()
        
        if screenshot_url:
            embed.set_image(url=screenshot_url)
            
        msg = None
        warning_msg = ""
        try:
            view = RegearPersistentView(self.bot)
            msg = await target_channel.send(embed=embed, view=view)
            if not channel_id:
                warning_msg = "\n⚠️ *Канал уведомлений о регирах не настроен! Заявка отправлена в этот канал.*"
        except Exception as e:
            return await interaction.followup.send(f"❌ Не удалось отправить заявку в канал: {e}", ephemeral=True)
            
        new_regear = {
            'id': regear_id,
            'user_id': interaction.user.id,
            'user_name': interaction.user.display_name,
            'role': role.value,
            'weapon': weapon,
            'offhand': offhand,
            'head': head,
            'chest': chest,
            'shoes': shoes,
            'cape': cape,
            'screenshot_url': screenshot_url,
            'timestamp': int(time.time()),
            'status': '⏳ Ожидание',
            'msg_id': msg.id if msg else None,
            'channel_id': msg.channel.id if msg else None,
            'reason': None
        }
        
        regears = load_regears()
        regears.append(new_regear)
        save_regears(regears)
        
        await interaction.followup.send(f"✅ Ваша заявка на регир **{regear_id}** успешно отправлена!{warning_msg}", ephemeral=True)

    # --- АВТОДОПОЛНЕНИЯ ДЛЯ ПАРАМЕТРОВ КОМАНДЫ REGEAR ---

    @regear_request.autocomplete('weapon')
    async def regear_weapon_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        current_lower = current.lower().strip()
        choices = []
        for w in WEAPONS_LIST:
            if not current_lower or current_lower in w.lower():
                choices.append(app_commands.Choice(name=w, value=w))
                if len(choices) >= 25:
                    break
        return choices

    @regear_request.autocomplete('offhand')
    async def regear_offhand_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        current_lower = current.lower().strip()
        choices = []
        for o in OFFHANDS_LIST:
            if not current_lower or current_lower in o.lower():
                choices.append(app_commands.Choice(name=o, value=o))
                if len(choices) >= 25:
                    break
        return choices

    @regear_request.autocomplete('head')
    async def regear_head_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        current_lower = current.lower().strip()
        choices = []
        for h in HEADGEAR_LIST:
            if not current_lower or current_lower in h.lower():
                choices.append(app_commands.Choice(name=h, value=h))
                if len(choices) >= 25:
                    break
        return choices

    @regear_request.autocomplete('chest')
    async def regear_chest_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        current_lower = current.lower().strip()
        choices = []
        for a in ARMOR_LIST:
            if not current_lower or current_lower in a.lower():
                choices.append(app_commands.Choice(name=a, value=a))
                if len(choices) >= 25:
                    break
        return choices

    @regear_request.autocomplete('shoes')
    async def regear_shoes_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        current_lower = current.lower().strip()
        choices = []
        for f in FOOTWEAR_LIST:
            if not current_lower or current_lower in f.lower():
                choices.append(app_commands.Choice(name=f, value=f))
                if len(choices) >= 25:
                    break
        return choices

    @regear_request.autocomplete('cape')
    async def regear_cape_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        current_lower = current.lower().strip()
        choices = []
        for c in CAPES_LIST:
            if not current_lower or current_lower in c.lower():
                choices.append(app_commands.Choice(name=c, value=c))
                if len(choices) >= 25:
                    break
        return choices

    @app_commands.command(name='regear_approve', description="Одобрить заявку на регир (Админ)")
    @app_commands.describe(id="ID заявки (например: R3X9)")
    async def regear_approve(self, interaction: discord.Interaction, id: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ У вас нет прав на выполнение этой команды!", ephemeral=True)
            
        regears = load_regears()
        found = None
        for r in regears:
            if r['id'].lower() == id.strip().lower():
                found = r
                break
                
        if not found:
            return await interaction.response.send_message(f"❌ Заявка с ID `{id}` не найдена!", ephemeral=True)
            
        if found['status'] == '✅ Одобрено':
            return await interaction.response.send_message(f"⚠️ Заявка `{id}` уже одобрена!", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        
        found['status'] = '✅ Одобрено'
        found['reason'] = None
        save_regears(regears)
        
        # Обновляем сообщение с эмбедом
        if found.get('msg_id') and found.get('channel_id'):
            try:
                channel = self.bot.get_channel(found['channel_id'])
                if channel:
                    msg = await channel.fetch_message(found['msg_id'])
                    if msg and msg.embeds:
                        old_embed = msg.embeds[0]
                        embed = discord.Embed(
                            title=old_embed.title,
                            description=f"👤 **Игрок:** <@{found['user_id']}>\n📊 **Статус:** ✅ Одобрено (Одобрил: {interaction.user.mention})",
                            color=discord.Color.green()
                        )
                        for f in old_embed.fields:
                            embed.add_field(name=f.name, value=f.value, inline=f.inline)
                        embed.set_footer(text=old_embed.footer.text)
                        embed.timestamp = old_embed.timestamp
                        if old_embed.image:
                            embed.set_image(url=old_embed.image.url)
                        await msg.edit(embed=embed, view=RegearPersistentView(self.bot, status='✅ Одобрено'))
            except Exception as e:
                print(f"Не удалось обновить сообщение регира {id}: {e}")
                
        # Пробуем уведомить пользователя в ЛС
        try:
            user = self.bot.get_user(found['user_id'])
            if not user:
                user = await self.bot.fetch_user(found['user_id'])
            if user:
                dm_embed = discord.Embed(
                    title=f"✅ Заявка на регир одобрена!",
                    description=f"Ваша заявка **{found['id']}** ({found['role']}) была успешно одобрена офицером!",
                    color=discord.Color.green()
                )
                await user.send(embed=dm_embed)
        except Exception:
            pass
            
        await interaction.followup.send(f"✅ Заявка на регир `{id}` успешно одобрена!", ephemeral=True)

    @app_commands.command(name='regear_reject', description="Отклонить заявку на регир (Админ)")
    @app_commands.describe(id="ID заявки (например: R3X9)", reason="Причина отклонения")
    async def regear_reject(self, interaction: discord.Interaction, id: str, reason: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ У вас нет прав на выполнение этой команды!", ephemeral=True)
            
        regears = load_regears()
        found = None
        for r in regears:
            if r['id'].lower() == id.strip().lower():
                found = r
                break
                
        if not found:
            return await interaction.response.send_message(f"❌ Заявка с ID `{id}` не найдена!", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        
        found['status'] = f"❌ Отклонено"
        found['reason'] = reason
        save_regears(regears)
        
        # Обновляем сообщение с эмбедом
        if found.get('msg_id') and found.get('channel_id'):
            try:
                channel = self.bot.get_channel(found['channel_id'])
                if channel:
                    msg = await channel.fetch_message(found['msg_id'])
                    if msg and msg.embeds:
                        old_embed = msg.embeds[0]
                        embed = discord.Embed(
                            title=old_embed.title,
                            description=f"👤 **Игрок:** <@{found['user_id']}>\n📊 **Статус:** ❌ Отклонено (Отклонил: {interaction.user.mention})\n💬 **Причина:** {reason}",
                            color=discord.Color.red()
                        )
                        for f in old_embed.fields:
                            embed.add_field(name=f.name, value=f.value, inline=f.inline)
                        embed.set_footer(text=old_embed.footer.text)
                        embed.timestamp = old_embed.timestamp
                        if old_embed.image:
                            embed.set_image(url=old_embed.image.url)
                        await msg.edit(embed=embed, view=None)
            except Exception as e:
                print(f"Не удалось обновить сообщение регира {id}: {e}")
                
        # Пробуем уведомить пользователя в ЛС
        try:
            user = self.bot.get_user(found['user_id'])
            if not user:
                user = await self.bot.fetch_user(found['user_id'])
            if user:
                dm_embed = discord.Embed(
                    title=f"❌ Заявка на регир отклонена",
                    description=f"Ваша заявка **{found['id']}** ({found['role']}) была отклонена.\n💬 **Причина:** {reason}",
                    color=discord.Color.red()
                )
                await user.send(embed=dm_embed)
        except Exception:
            pass
            
        await interaction.followup.send(f"❌ Заявка на регир `{id}` отклонена по причине: `{reason}`", ephemeral=True)

    @app_commands.command(name='regear_summary', description="Сводный отчет по одобренным регирам (За месяц / N дней)")
    @app_commands.describe(days="Количество дней для аналитики (по умолчанию: 30)")
    async def regear_summary(self, interaction: discord.Interaction, days: int = 30):
        if not await check_user_permissions(interaction):
            return
            
        await interaction.response.defer(ephemeral=False)
        
        regears = load_regears()
        now = int(time.time())
        limit = now - (days * 86400)
        
        period_regears = [r for r in regears if r.get('timestamp', 0) >= limit]
        
        if not period_regears:
            return await interaction.followup.send(f"ℹ️ За последние {days} дней заявок на региры не найдено.")
            
        user_stats = {}
        pending_count = 0
        rejected_count = 0
        issued_count = 0
        
        for r in period_regears:
            status = r.get('status', '')
            if 'ожид' in status.lower() or 'pending' in status.lower():
                pending_count += 1
                continue
            if 'отклон' in status.lower() or 'reject' in status.lower():
                rejected_count += 1
                continue
            if 'выдан' in status.lower() or 'issued' in status.lower():
                issued_count += 1
            
            uid = r.get('user_id')
            uname = r.get('user_name', 'Неизвестно')
            role_name = r.get('role', 'Другое')
            
            if uid not in user_stats:
                user_stats[uid] = {
                    'name': uname,
                    'approved': 0,
                    'roles': {}
                }
                
            user_stats[uid]['approved'] += 1
            user_stats[uid]['roles'][role_name] = user_stats[uid]['roles'].get(role_name, 0) + 1
            
        embed = discord.Embed(
            title=f"📊 Сводка по регирам за последние {days} дней",
            color=discord.Color.from_str("#7D00FF")
        )
        
        desc = ""
        active_regeared_players = 0
        
        for uid, stats in user_stats.items():
            if stats['approved'] == 0:
                continue
            active_regeared_players += 1
            desc += f"👤 **{stats['name']}** (<@{uid}>) — Всего: **{stats['approved']}**\n"
            for r_name, r_cnt in stats['roles'].items():
                desc += f"  • {r_name}: **{r_cnt}**\n"
            desc += "\n"
            
        if not desc:
            desc = "*Нет одобренных или выданных региров за данный период.*"
            
        embed.description = desc
        
        embed.add_field(name="⏳ В ожидании", value=str(pending_count), inline=True)
        embed.add_field(name="❌ Отклонено", value=str(rejected_count), inline=True)
        embed.add_field(name="📦 Выдано", value=str(issued_count), inline=True)
        embed.add_field(name="👥 Игроков компенсировано", value=str(active_regeared_players), inline=True)
        
        embed.set_footer(text="United Force • Статистика компенсаций")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    cog = RegearCog(bot)
    await bot.add_cog(cog)
    bot.add_view(RegearPersistentView(bot))
