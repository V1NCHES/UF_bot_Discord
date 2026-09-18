import discord
import os
import logger
import config

def get_setting(settings, guild_id, key, default=None):
    if guild_id:
        g_str = str(guild_id)
        if "guilds" in settings and g_str in settings["guilds"]:
            if key in settings["guilds"][g_str]:
                return settings["guilds"][g_str][key]
        return default
    return settings.get(key, default)

def generate_combined_call_message(call_data, include_ping=True):
    """Генерация единого текстового сообщения сбора (заголовок, пинг и состав)"""
    content = ""
    # 1. Пинг в самом начале
    if include_ping:
        ping_role = call_data.get('ping_role')
        if ping_role:
            if hasattr(ping_role, 'is_default') and (ping_role.is_default() or ping_role.name in ["@everyone", "everyone"]):
                content += "@everyone\n\n"
            else:
                content += f"{ping_role.mention}\n\n"
                
    # 2. Текстовый заголовок сбора
    default_title = "⚔️ Сбор на выезд"
    if call_data.get('call_type') == 'zvz':
        default_title = "⚔️ Сбор на ZvZ"
    elif call_data.get('call_type') == 'roum':
        default_title = "⚔️ Сбор на Roum"
        
    title = call_data.get('title') or default_title
    if call_data.get('paused'):
        title = f"⏸️ {title} (ПРИОСТАНОВЛЕН)"

    content += f"**{title}**\n"
    content += f"{call_data['description']}\n\n"
    
    content += f"**Организатор**\n"
    content += f"{call_data['organizer'].mention}\n\n"
    
    if call_data.get('event_time'):
        t_unix = call_data['event_time']
        from datetime import datetime, timezone, timedelta
        dt_utc = datetime.fromtimestamp(t_unix, tz=timezone.utc)
        dt_msk = dt_utc.astimezone(timezone(timedelta(hours=3)))
        
        duration = call_data.get('duration')
        content += f"**Время контента**\n"
        if duration:
            end_unix = t_unix + duration * 60
            dt_end_utc = datetime.fromtimestamp(end_unix, tz=timezone.utc)
            dt_end_msk = dt_end_utc.astimezone(timezone(timedelta(hours=3)))
            content += (
                f"⏰ **Начало (МСК):** {dt_msk.strftime('%d.%m.%Y в %H:%M')}\n"
                f"🏁 **Конец (МСК):** {dt_end_msk.strftime('%d.%m.%Y в %H:%M')}\n"
                f"🌐 **UTC:** {dt_utc.strftime('%H:%M')} — {dt_end_utc.strftime('%H:%M')}\n"
                f"⏳ **До начала:** <t:{t_unix}:R> (длительность: {duration} мин.)\n\n"
            )
        else:
            content += (
                f"⏰ **МСК:** {dt_msk.strftime('%d.%m.%Y в %H:%M')}\n"
                f"🌐 **UTC:** {dt_utc.strftime('%H:%M')}\n"
                f"⏳ **До начала:** <t:{t_unix}:R> (<t:{t_unix}:F>)\n\n"
            )
            
    if call_data.get('required_role'):
        content += f"**Нужная роль**\n"
        content += f"{call_data['required_role'].mention}\n\n"
        
    content += f"ID: {call_data['id']} • Нажмите на кнопку нужной роли\n\n"
    
    # 3. Перечисление ролей (Состав группы)
    content += "**Состав группы**\n"
    for i, user in enumerate(call_data['slots']):
        label = call_data['slot_labels'][i]
        mention = user.mention if user else "---"
        content += f"**{i+1}.** {label} — {mention}\n"
        
    return content

async def auto_finish_call(client, call_data, active_calls):
    """Автоматическое завершение сбора через час после начала"""
    import asyncio
    from datetime import datetime
    import logger
    
    call_id = call_data['id']
    
    call_data['finished'] = True
    
    # 1. Обновляем главное сообщение (отключаем кнопки, меняем заголовок)
    main_msg_id = call_data.get('main_msg_id')
    main_channel_id = call_data.get('main_channel_id')
    
    if main_msg_id and main_channel_id:
        channel = client.get_channel(main_channel_id)
        if channel:
            try:
                msg = await channel.fetch_message(main_msg_id)
                content = generate_combined_call_message(call_data, include_ping=True)
                if not content.startswith("✅"):
                    content = "✅ **Сбор завершен (Автоматически)**\n\n" + content
                
                # Создаем отключенную версию кнопок
                view = CallRoleView(call_data, active_calls)
                for item in view.children:
                    item.disabled = True
                
                await msg.edit(content=content, embed=None, view=view)
            except Exception as e:
                print(f"Ошибка автозавершения главного сообщения: {e}")
    
    # 2. Обновляем сообщение в ветке
    thread_msg_id = call_data.get('thread_msg_id')
    thread_id = call_data.get('thread_id')
    if thread_msg_id and thread_id:
        thread = client.get_channel(thread_id)
        if thread:
            try:
                msg = await thread.fetch_message(thread_msg_id)
                content = generate_combined_call_message(call_data, include_ping=False)
                if not content.startswith("✅"):
                    content = "✅ **Сбор завершен (Автоматически)**\n\n" + content
                    
                view = CallRoleView(call_data, active_calls)
                for item in view.children:
                    item.disabled = True
                await msg.edit(content=content, embed=None, view=view)
            except Exception as e:
                print(f"Ошибка автозавершения сообщения в ветке: {e}")
                
    # 3. Сохраняем отчет в Excel/Google Sheets
    asyncio.create_task(logger.save_data_async(call_data))
    
    # 4. Удаляем из активных сборов
    keys_to_delete = [k for k, v in active_calls.items() if v.get('id') == call_id]
    for k in keys_to_delete:
        active_calls.pop(k, None)
        
    # 5. Формируем отчет в формате таблицы
    date_now = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary = f"🏁 **Сбор `{call_id}` автоматически завершен и сохранен в таблицу!** *(прошел 1 час после начала)*\n"
    summary += f"```\n{call_id}\t{date_now}\n"
    summary += f"Организатор\t{call_data['organizer'].display_name}\n"
    
    has_participants = False
    for user in call_data['slots']:
        if user:
            summary += f"{user.id}\t{user.display_name}\n"
            has_participants = True
    
    if not has_participants:
        summary += "(Участников нет)\n"
    summary += "```"
    
    if thread_id:
        thread = client.get_channel(thread_id)
        if thread:
            try:
                await thread.send(summary)
            except: pass
    elif main_channel_id:
        channel = client.get_channel(main_channel_id)
        if channel:
            try:
                await channel.send(summary)
            except: pass

class RoleButton(discord.ui.Button):
    """Кнопка для выбора конкретной роли"""
    def __init__(self, label, slot_idx, active_calls):
        super().__init__(label=label, style=discord.ButtonStyle.secondary, custom_id=f"role_btn_{slot_idx}")
        self.slot_idx = slot_idx
        self.active_calls = active_calls

    async def callback(self, interaction: discord.Interaction):
        call_data = self.active_calls.get(interaction.message.id)
        if not call_data:
            return await interaction.response.send_message("Сбор не найден.", ephemeral=True)

        # Вспомогательная функция для отправки уведомления в ветку
        async def send_to_thread(content):
            if interaction.message.thread:
                await interaction.message.thread.send(content)
            elif isinstance(interaction.channel, discord.Thread):
                await interaction.channel.send(content)
            else:
                await interaction.response.send_message(content, ephemeral=True)

        if call_data.get('required_role') and call_data['required_role'] not in interaction.user.roles:
            return await send_to_thread(f"⚠️ {interaction.user.mention}, у вас нет роли {call_data['required_role'].mention}!")

        status_msg = ""
        if call_data['slots'][self.slot_idx] == interaction.user:
            call_data['slots'][self.slot_idx] = None
            status_msg = f"❌ {interaction.user.display_name} выписался из слота **{call_data['slot_labels'][self.slot_idx]}**"
        else:
            if call_data['slots'][self.slot_idx] is not None:
                return await send_to_thread(f"⚠️ {interaction.user.mention}, это место уже занято другим игроком!")
            
            if interaction.user in call_data['slots']:
                return await send_to_thread(f"⚠️ {interaction.user.mention}, вы уже записаны на другую роль! Сначала выпишитесь из неё.")

            if call_data.get('paused'):
                return await send_to_thread(f"⚠️ {interaction.user.mention}, запись временно приостановлена организатором!")

            call_data['slots'][self.slot_idx] = interaction.user
            status_msg = f"✅ {interaction.user.display_name} записался на роль **{call_data['slot_labels'][self.slot_idx]}**"

        # Сразу обновляем сообщение, чтобы бот казался мгновенным
        is_main = (interaction.message.id == call_data.get('main_msg_id'))
        combined_content = generate_combined_call_message(call_data, include_ping=is_main)
        
        # 1. Редактируем сообщение с комбинированным содержимым
        new_view = CallRoleView(call_data, self.active_calls)
        await interaction.response.edit_message(content=combined_content, view=new_view)

        # Сохраняем данные в фоне (не блокируя интерфейс)
        import asyncio
        asyncio.create_task(logger.save_data_async(call_data))
        
        # Затем пробуем обновить другое сообщение (если мы в ветке - обновляем главное, и наоборот)
        try:
            target_msg_id = None
            if interaction.message.id == call_data.get('main_msg_id'):
                target_msg_id = call_data.get('thread_msg_id')
                target_is_main = False
            else:
                target_msg_id = call_data.get('main_msg_id')
                target_is_main = True
                
            if target_msg_id:
                channel = interaction.client.get_channel(interaction.channel_id)
                # Если мы в ветке, главное сообщение в родительском канале
                if isinstance(interaction.channel, discord.Thread):
                    channel = interaction.channel.parent
                
                # Если мы в главном канале, сообщение ветки в самой ветке
                if interaction.message.thread:
                    channel = interaction.message.thread

                if channel:
                    # Редактируем целевое сообщение
                    target_msg = await channel.fetch_message(target_msg_id)
                    target_combined = generate_combined_call_message(call_data, include_ping=target_is_main)
                    target_view = CallRoleView(call_data, self.active_calls)
                    await target_msg.edit(content=target_combined, view=target_view)
        except Exception as e:
            print(f"Ошибка синхронизации: {e}")
        
        # Отправляем уведомление в ветку (если мы не ответили им ранее как ошибкой)
        if status_msg:
            if interaction.message.thread:
                await interaction.message.thread.send(status_msg)
            elif isinstance(interaction.channel, discord.Thread):
                await interaction.channel.send(status_msg)

async def sync_messages(client, call_data, active_calls):
    """Синхронное обновление главного сообщения и сообщения в ветке"""
    view = CallRoleView(call_data, active_calls)
    
    # 1. Обновляем главное сообщение
    try:
        main_msg_id = call_data.get('main_msg_id')
        main_channel_id = call_data.get('main_channel_id')
        if main_msg_id and main_channel_id:
            channel = client.get_channel(main_channel_id)
            if channel:
                try:
                    msg = await channel.fetch_message(main_msg_id)
                    content = generate_combined_call_message(call_data, include_ping=True)
                    if call_data.get('finished'):
                        content = "✅ **Сбор завершен**\n\n" + content
                    await msg.edit(content=content, embed=None, view=view)
                except: pass
    except Exception as e:
        print(f"Ошибка синхронизации главного сообщения: {e}")

    # 2. Обновляем сообщение в ветке
    try:
        thread_msg_id = call_data.get('thread_msg_id')
        thread_id = call_data.get('thread_id')
        if thread_msg_id and thread_id:
            thread = client.get_channel(thread_id)
            if thread:
                try:
                    msg = await thread.fetch_message(thread_msg_id)
                    content = generate_combined_call_message(call_data, include_ping=False)
                    if call_data.get('finished'):
                        content = "✅ **Сбор завершен**\n\n" + content
                    await msg.edit(content=content, embed=None, view=view)
                except: pass
    except Exception as e:
        print(f"Ошибка синхронизации сообщения в ветке: {e}")

class SaveTemplateModal(discord.ui.Modal, title="Сохранение шаблона сбора"):
    template_name = discord.ui.TextInput(
        label="Название шаблона (для удобства поиска)",
        placeholder="например: Суета Суббота",
        required=True,
        max_length=50
    )
    
    def __init__(self, call_data):
        super().__init__()
        self.call_data = call_data
        
    async def on_submit(self, interaction: discord.Interaction):
        try:
            from main import save_call_to_cache
            self.call_data['template_name'] = self.template_name.value
            save_call_to_cache(self.call_data)
            await interaction.response.send_message(f"💾 Шаблон сбора `{self.template_name.value}` (ID `{self.call_data['id']}`) успешно сохранен!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка при сохранении шаблона: {e}", ephemeral=True)

class SaveCallButton(discord.ui.Button):
    """Кнопка для сохранения шаблона сбора"""
    def __init__(self, active_calls):
        super().__init__(label="💾 Сохранить", style=discord.ButtonStyle.secondary, custom_id="save_call_template")
        self.active_calls = active_calls

    async def callback(self, interaction: discord.Interaction):
        call_data = self.active_calls.get(interaction.message.id)
        if not call_data:
            return await interaction.response.send_message("Сбор не найден.", ephemeral=True)
            
        # Проверяем права (администратор или роль для сохранения)
        import json
        settings = {}
        if os.path.exists('settings.json'):
            try:
                with open('settings.json', 'r') as f:
                    settings = json.load(f)
            except: pass
            
        guild_id = interaction.guild.id if interaction.guild else None
        save_role_id = get_setting(settings, guild_id, 'save_role_id')
        is_allowed = interaction.user.guild_permissions.administrator
        
        save_role = None
        if save_role_id and interaction.guild:
            save_role = interaction.guild.get_role(save_role_id)
            
        if not is_allowed and save_role:
            if save_role in interaction.user.roles:
                is_allowed = True
                
        if not is_allowed:
            role_mention = save_role.mention if save_role else "Администратор"
            return await interaction.response.send_message(f"❌ Сохранять шаблоны могут только администраторы или пользователи с ролью {role_mention}!", ephemeral=True)
            
        # Открываем модалку для ввода названия шаблона
        await interaction.response.send_modal(SaveTemplateModal(call_data))

class FinishButton(discord.ui.Button):
    """Кнопка для завершения сбора"""
    def __init__(self, active_calls):
        super().__init__(label="Завершить", style=discord.ButtonStyle.success, custom_id="finish_call")
        self.active_calls = active_calls

    async def callback(self, interaction: discord.Interaction):
        call_data = self.active_calls.get(interaction.message.id)
        if not call_data:
            return await interaction.response.send_message("Сбор не найден.", ephemeral=True)
        
        if interaction.user != call_data['organizer']:
            return await interaction.response.send_message("Только организатор может завершить сбор!", ephemeral=True)

        call_data['finished'] = True
        
        for item in self.view.children:
            item.disabled = True
        
        is_main = (interaction.message.id == call_data.get('main_msg_id'))
        content = generate_combined_call_message(call_data, include_ping=is_main)
        if not content.startswith("✅"):
            content = "✅ **Сбор завершен**\n\n" + content
        
        await interaction.response.edit_message(content=content, embed=None, view=self.view)
        
        # Синхронизируем завершение со вторым сообщением
        try:
            target_msg_id = call_data.get('thread_msg_id') if is_main else call_data.get('main_msg_id')
            if target_msg_id:
                channel = interaction.client.get_channel(interaction.channel_id)
                if isinstance(interaction.channel, discord.Thread):
                    channel = interaction.channel.parent
                if interaction.message.thread:
                    channel = interaction.message.thread
                if channel:
                    target_msg = await channel.fetch_message(target_msg_id)
                    target_content = generate_combined_call_message(call_data, include_ping=not is_main)
                    if not target_content.startswith("✅"):
                        target_content = "✅ **Сбор завершен**\n\n" + target_content
                    # Отключаем кнопки и для второго сообщения
                    target_view = CallRoleView(call_data, self.active_calls)
                    for item in target_view.children:
                        item.disabled = True
                    await target_msg.edit(content=target_content, embed=None, view=target_view)
        except Exception as e:
            print(f"Ошибка автозавершения второго сообщения: {e}")
        
        if interaction.message.id in self.active_calls:
            # Итоговое сохранение в фоне
            import asyncio
            asyncio.create_task(logger.save_data_async(call_data))
            
            # Удаляем из активных
            call_id = call_data['id']
            keys_to_delete = [k for k, v in self.active_calls.items() if v.get('id') == call_id]
            for k in keys_to_delete:
                self.active_calls.pop(k, None)
            
            # Формируем отчет в формате таблицы
            from datetime import datetime
            date_now = datetime.now().strftime("%Y-%m-%d %H:%M")
            summary = "🏁 **Сбор завершен и сохранен в таблицу!**\n"
            summary += f"```\n{call_data['id']}\t{date_now}\n"
            summary += f"Организатор\t{call_data['organizer'].display_name}\n"
            
            has_participants = False
            for user in call_data['slots']:
                if user:
                    summary += f"{user.id}\t{user.display_name}\n"
                    has_participants = True
            
            if not has_participants:
                summary += "(Участников нет)\n"
            summary += "```"

            if interaction.message.thread:
                await interaction.message.thread.send(summary)
            else:
                await interaction.channel.send(summary)

class DeleteButton(discord.ui.Button):
    """Кнопка для удаления сбора"""
    def __init__(self, active_calls):
        super().__init__(label="Удалить", style=discord.ButtonStyle.danger, custom_id="delete_call")
        self.active_calls = active_calls

    async def callback(self, interaction: discord.Interaction):
        call_data = self.active_calls.get(interaction.message.id)
        if not call_data:
            try:
                await interaction.message.delete()
            except: pass
            return
        
        if interaction.user != call_data['organizer'] and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Только организатор или администратор может удалить сбор!", ephemeral=True)

        # Очищаем данные в таблицах перед удалением
        import asyncio
        asyncio.create_task(logger.clear_data_async(call_data))
        call_id = call_data['id']
        keys_to_delete = [k for k, v in self.active_calls.items() if v.get('id') == call_id]
        for k in keys_to_delete:
            self.active_calls.pop(k, None)
            
        # Удаляем сообщение в главном канале
        main_msg_id = call_data.get('main_msg_id')
        main_channel_id = call_data.get('main_channel_id')
        if main_channel_id and main_msg_id:
            channel = interaction.client.get_channel(main_channel_id)
            if channel:
                try:
                    msg = await channel.fetch_message(main_msg_id)
                    await msg.delete()
                except: pass
                    
        # Удаляем сообщение в ветке
        thread_msg_id = call_data.get('thread_msg_id')
        thread_id = call_data.get('thread_id')
        if thread_id and thread_msg_id:
            thread = interaction.client.get_channel(thread_id)
            if thread:
                try:
                    msg = await thread.fetch_message(thread_msg_id)
                    await msg.delete()
                except: pass

class ManageButton(discord.ui.Button):
    """Кнопка для открытия меню управления"""
    def __init__(self, active_calls):
        super().__init__(label="🔧 Управление", style=discord.ButtonStyle.secondary, custom_id="manage_call")
        self.active_calls = active_calls

    async def callback(self, interaction: discord.Interaction):
        call_data = self.active_calls.get(interaction.message.id)
        if not call_data:
            return await interaction.response.send_message("Сбор не найден.", ephemeral=True)
        
        if interaction.user != call_data['organizer']:
            return await interaction.response.send_message("Только организатор может управлять сбором!", ephemeral=True)

        view = OrganizerMenuView(interaction.message, call_data, self.active_calls)
        
        if interaction.message.thread:
            await interaction.message.thread.send("🛠 **Меню управления сбором:**", view=view)
            await interaction.response.send_message("✅ Меню управления отправлено в ветку обсуждения!", ephemeral=True)
        elif isinstance(interaction.channel, discord.Thread):
            await interaction.channel.send("🛠 **Меню управления сбором:**", view=view)
            await interaction.response.defer() # Просто подтверждаем взаимодействие
        else:
            await interaction.response.send_message("Меню управления сбором:", view=view, ephemeral=True)

class EditDescriptionModal(discord.ui.Modal, title="Редактирование описания"):
    description_input = discord.ui.TextInput(
        label="Описание сбора",
        style=discord.TextStyle.paragraph,
        placeholder="Введите новый текст...",
        required=True
    )

    def __init__(self, original_message, call_data, active_calls):
        super().__init__()
        self.original_message = original_message
        self.call_data = call_data
        self.active_calls = active_calls
        self.description_input.default = call_data['description']

    async def on_submit(self, interaction: discord.Interaction):
        self.call_data['description'] = self.description_input.value
        # Сначала отвечаем на взаимодействие
        await interaction.response.edit_message(content="✅ Описание обновлено!", view=None)
        # Потом синхронизируем
        await sync_messages(interaction.client, self.call_data, self.active_calls)
        
        if self.original_message.thread:
            await self.original_message.thread.send(f"📝 Организатор изменил описание сбора.")

class AddSlotModal(discord.ui.Modal, title="Добавление новой роли"):
    label_input = discord.ui.TextInput(
        label="Названия ролей (каждая с новой строки)",
        style=discord.TextStyle.paragraph,
        placeholder="1. Арбалет\n2. Саппорт\n...",
        required=True
    )

    def __init__(self, original_message, call_data, active_calls):
        super().__init__()
        self.original_message = original_message
        self.call_data = call_data
        self.active_calls = active_calls

    async def on_submit(self, interaction: discord.Interaction):
        import re
        lines = self.label_input.value.split('\n')
        new_labels = []
        for line in lines:
            line = line.strip()
            if not line: continue
            clean_label = re.sub(r'^\d+[\.\)\s]*', '', line).strip()
            if clean_label:
                new_labels.append(clean_label)
        
        if not new_labels:
            return await interaction.response.send_message("Неверный формат ролей!", ephemeral=True)

        for label in new_labels:
            self.call_data['slot_labels'].append(label)
            self.call_data['slots'].append(None)
        
        # Сначала отвечаем на взаимодействие
        added_text = ", ".join(new_labels)
        await interaction.response.edit_message(content=f"✅ Роли добавлены: {added_text}", view=None)

        import asyncio
        asyncio.create_task(logger.save_data_async(self.call_data))
        
        # Потом синхронизируем
        await sync_messages(interaction.client, self.call_data, self.active_calls)
        
        if self.original_message.thread:
            await self.original_message.thread.send(f"➕ Организатор добавил новые роли: **{added_text}**")

class DeleteSlotModal(discord.ui.Modal, title="Удаление роли"):
    index_input = discord.ui.TextInput(
        label="Номер роли для удаления",
        placeholder="Введите цифру (1, 2, ...)",
        required=True,
        min_length=1,
        max_length=2
    )

    def __init__(self, original_message, call_data, active_calls):
        super().__init__()
        self.original_message = original_message
        self.call_data = call_data
        self.active_calls = active_calls

    async def on_submit(self, interaction: discord.Interaction):
        try:
            idx = int(self.index_input.value) - 1
            if 0 <= idx < len(self.call_data['slots']):
                removed_label = self.call_data['slot_labels'].pop(idx)
                self.call_data['slots'].pop(idx)
                
                import asyncio
                asyncio.create_task(logger.save_data_async(self.call_data))
                
                # Сначала отвечаем на взаимодействие
                await interaction.response.edit_message(content=f"✅ Роль '{removed_label}' удалена!", view=None)
                # Потом синхронизируем
                await sync_messages(interaction.client, self.call_data, self.active_calls)
                
                if self.original_message.thread:
                    await self.original_message.thread.send(f"➖ Организатор удалил роль: **{removed_label}**")
            else:
                await interaction.response.send_message("Неверный номер роли!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Введите число!", ephemeral=True)

class EditLinkModal(discord.ui.Modal, title="Изменение ссылки"):
    link_input = discord.ui.TextInput(
        label="Ссылка на голосовой канал",
        placeholder="https://discord.gg/...",
        required=False
    )

    def __init__(self, call_data):
        super().__init__()
        self.call_data = call_data
        if self.call_data.get('link'):
            self.link_input.default = self.call_data['link']

    async def on_submit(self, interaction: discord.Interaction):
        self.call_data['link'] = self.link_input.value if self.link_input.value else None
        await interaction.response.edit_message(content=f"✅ Ссылка обновлена!", view=None)
        await sync_messages(interaction.client, self.call_data, self.active_calls)

class CreateCallModal(discord.ui.Modal, title="Создание нового сбора"):
    description_input = discord.ui.TextInput(
        label="Описание сбора",
        style=discord.TextStyle.paragraph,
        placeholder="Введите цель сбора и требования...",
        required=True
    )
    link_input = discord.ui.TextInput(
        label="Ссылка на войс (можно пропустить)",
        placeholder="https://discord.gg/...",
        required=False
    )
    roles_input = discord.ui.TextInput(
        label="Список ролей (каждая с новой строки)",
        style=discord.TextStyle.paragraph,
        placeholder="1. Арбалет\n2. Лук\n3. Хилл",
        default="1. Боец\n2. Боец\n3. Боец\n4. Боец\n5. Боец",
        required=True
    )
    time_input = discord.ui.TextInput(
        label="Время контента (МСК, например: 20:00)",
        placeholder="20:00 или 19.05 20:00",
        required=False
    )
    date_input = discord.ui.TextInput(
        label="Дата (ДД.ММ, например: 19.05, необяз.)",
        placeholder="Сегодня, если оставить пустым",
        required=False
    )

    def __init__(self, required_role, active_calls, prompt_message=None, call_type='call', ping_role=None, title=None, duration=None, prefill_desc=None, prefill_roles=None, prefill_link=None):
        super().__init__()
        self.required_role = required_role
        self.active_calls = active_calls
        self.prompt_message = prompt_message
        self.call_type = call_type
        self.ping_role = ping_role
        self.custom_title = title
        self.duration = duration
        if prefill_desc:
            self.description_input.default = prefill_desc
        if prefill_roles:
            self.roles_input.default = prefill_roles
        if prefill_link:
            self.link_input.default = prefill_link

    async def on_submit(self, interaction: discord.Interaction):
        import re
        import random
        import string
        import logger
        import asyncio
        from main import parse_msk_time

        # Парсим время и дату
        event_time = None
        if self.time_input.value:
            try:
                event_time = parse_msk_time(self.time_input.value, self.date_input.value)
            except ValueError:
                return await interaction.response.send_message(
                    "❌ Неверный формат времени или даты! Пожалуйста, укажите в формате:\n"
                    "• Время: `ЧЧ:ММ` (например: `20:00`)\n"
                    "• Дата (необяз.): `ДД.ММ` (например: `19.05`)",
                    ephemeral=True
                )

        # Парсим роли из текстового поля
        roles_text = self.roles_input.value
        labels = []
        for line in roles_text.split('\n'):
            line = line.strip()
            if not line: continue
            # Убираем нумерацию типа "1. ", "1) " или просто цифры в начале
            clean_label = re.sub(r'^\d+[\.\)\s]*', '', line).strip()
            if clean_label:
                labels.append(clean_label)
        
        if not labels:
            labels = ["Участник"]

        import time
        created_at = int(time.time())
        
        warning_pinged = False
        start_pinged = False
        if not event_time:
            warning_pinged = True
            start_pinged = True
        elif event_time - created_at < 900:
            warning_pinged = True

        call_id = ''.join(random.choices(string.digits, k=10))
        
        call_data = {
            'organizer': interaction.user,
            'description': self.description_input.value,
            'slots': [None] * len(labels),
            'slot_labels': labels,
            'required_role': self.required_role,
            'ping_role': self.ping_role,
            'id': call_id,
            'link': self.link_input.value if self.link_input.value and "http" in self.link_input.value else None,
            'main_channel_id': interaction.channel_id,
            'guild_id': interaction.guild.id if interaction.guild else None,
            'call_type': self.call_type,
            'event_time': event_time,
            'created_at': created_at,
            'warning_pinged': warning_pinged,
            'start_pinged': start_pinged,
            'title': self.custom_title,
            'duration': self.duration
        }
        
        view = CallRoleView(call_data, self.active_calls)
        combined_content = generate_combined_call_message(call_data, include_ping=True)
        
        # Отправляем единое сообщение сбора
        message = await interaction.channel.send(content=combined_content, view=view)
        
        self.active_calls[message.id] = call_data
        call_data['main_msg_id'] = message.id
        
        # Создаем ветку
        try:
            thread = await message.create_thread(name=f"Сбор {call_id}", auto_archive_duration=1440)
            call_data['thread_id'] = thread.id
            
            # В ветке отправляем единое сообщение (без пинга)
            thread_combined_content = generate_combined_call_message(call_data, include_ping=False)
            thread_msg = await thread.send(content=thread_combined_content, view=CallRoleView(call_data, self.active_calls))
            
            call_data['thread_msg_id'] = thread_msg.id
            
            self.active_calls[thread_msg.id] = call_data
            self.active_calls[thread.id] = call_data # Добавляем ID ветки для команд
        except Exception as e:
            print(f"Ошибка создания ветки: {e}")
        
        # Сохраняем данные в Excel/Sheets
        asyncio.create_task(logger.save_data_async(call_data))
        
        # Отвечаем на модалку (невидимо для других)
        await interaction.response.send_message(f"✅ Сбор `{call_id}` успешно создан!", ephemeral=True)
        
        # Удаляем сообщение-приглашение
        if self.prompt_message:
            try:
                await self.prompt_message.delete()
            except: pass

class AssignPlayerModal(discord.ui.Modal, title="Добавление игрока на роль"):
    slot_input = discord.ui.TextInput(
        label="Номер роли (из списка)",
        placeholder="Например: 1, 2...",
        required=True
    )
    user_input = discord.ui.TextInput(
        label="Игрок (ID или Упоминание)",
        placeholder="Перетащите игрока или вставьте его ID",
        required=True
    )

    def __init__(self, original_message, call_data, active_calls):
        super().__init__()
        self.original_message = original_message
        self.call_data = call_data
        self.active_calls = active_calls

    async def on_submit(self, interaction: discord.Interaction):
        import re
        try:
            idx = int(self.slot_input.value) - 1
            if not (0 <= idx < len(self.call_data['slots'])):
                return await interaction.response.send_message("❌ Неверный номер роли!", ephemeral=True)
            
            # Пытаемся найти пользователя
            user_str = self.user_input.value
            user_id = None
            if user_str.isdigit():
                user_id = int(user_str)
            else:
                match = re.search(r'<@!?(\d+)>', user_str)
                if match:
                    user_id = int(match.group(1))
            
            if not user_id:
                return await interaction.response.send_message("❌ Не удалось распознать ID игрока. Используйте цифры или @упоминание.", ephemeral=True)
            
            member = interaction.guild.get_member(user_id)
            if not member:
                # Попробуем fetch если не в кеше
                try:
                    member = await interaction.guild.fetch_member(user_id)
                except:
                    return await interaction.response.send_message("❌ Игрок не найден на этом сервере!", ephemeral=True)
            
            # Проверяем не занят ли он уже
            if member in self.call_data['slots']:
                return await interaction.response.send_message(f"⚠️ {member.display_name} уже записан в этот сбор!", ephemeral=True)

            # Записываем
            self.call_data['slots'][idx] = member
            
            import logger
            import asyncio
            asyncio.create_task(logger.save_data_async(self.call_data))
            
            # Сначала отвечаем на взаимодействие
            msg = f"✅ Игрок {member.mention} добавлен на роль **{self.call_data['slot_labels'][idx]}**"
            await interaction.response.edit_message(content=msg, view=None)

            # Потом синхронизируем
            await sync_messages(interaction.client, self.call_data, self.active_calls)
            
            if self.original_message.thread:
                await self.original_message.thread.send(msg)
                
        except ValueError:
            await interaction.response.send_message("❌ Введите число в поле номера роли!", ephemeral=True)

class PauseButton(discord.ui.Button):
    """Кнопка для паузы/возобновления записи"""
    def __init__(self, original_message, call_data, active_calls):
        is_paused = call_data.get('paused', False)
        super().__init__(
            label="Возобновить" if is_paused else "Пауза", 
            style=discord.ButtonStyle.success if is_paused else discord.ButtonStyle.secondary,
            emoji="▶️" if is_paused else "⏸️"
        )
        self.original_message = original_message
        self.call_data = call_data
        self.active_calls = active_calls

    async def callback(self, interaction: discord.Interaction):
        self.call_data['paused'] = not self.call_data.get('paused', False)
        
        # Обновляем вид кнопок в главном сообщении
        new_view = CallRoleView(self.call_data, self.active_calls)
        is_main = (self.original_message.id == self.call_data.get('main_msg_id'))
        combined_content = generate_combined_call_message(self.call_data, include_ping=is_main)
        await self.original_message.edit(content=combined_content, view=new_view)
        
        # Обновляем саму кнопку в меню управления
        status = "приостановлена" if self.call_data['paused'] else "возобновлена"
        await interaction.response.edit_message(content=f"✅ Запись {status}!", view=OrganizerMenuView(self.original_message, self.call_data, self.active_calls))
        
        if self.original_message.thread:
            await self.original_message.thread.send(f"📢 Организатор {status} запись в этот сбор.")

class StartCallView(discord.ui.View):
    """Начальная кнопка для открытия модалки создания сбора"""
    def __init__(self, required_role, active_calls, call_type='call', ping_role=None, title=None, duration=None, prefill_desc=None, prefill_roles=None, prefill_link=None):
        super().__init__(timeout=600)
        self.required_role = required_role
        self.active_calls = active_calls
        self.call_type = call_type
        self.ping_role = ping_role
        self.custom_title = title
        self.duration = duration
        self.prefill_desc = prefill_desc
        self.prefill_roles = prefill_roles
        self.prefill_link = prefill_link

    @discord.ui.button(label="Настроить сбор", style=discord.ButtonStyle.primary, emoji="📝")
    async def start_setup(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreateCallModal(
            self.required_role, 
            self.active_calls, 
            interaction.message, 
            self.call_type, 
            ping_role=self.ping_role,
            title=self.custom_title,
            duration=self.duration,
            prefill_desc=self.prefill_desc,
            prefill_roles=self.prefill_roles,
            prefill_link=self.prefill_link
        ))

class OrganizerMenuView(discord.ui.View):
    """Меню управления для организатора"""
    def __init__(self, original_message, call_data, active_calls):
        super().__init__(timeout=600)
        self.original_message = original_message
        self.call_data = call_data
        self.active_calls = active_calls
        # Добавляем кнопку паузы
        self.add_item(PauseButton(original_message, call_data, active_calls))

    @discord.ui.button(label="Добавить игрока", style=discord.ButtonStyle.success, emoji="👤")
    async def assign_player(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AssignPlayerModal(self.original_message, self.call_data, self.active_calls))

    @discord.ui.button(label="Изменить текст", style=discord.ButtonStyle.primary)
    async def edit_text(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditDescriptionModal(self.original_message, self.call_data, self.active_calls))

    @discord.ui.button(label="Добавить роль", style=discord.ButtonStyle.success)
    async def add_slot(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddSlotModal(self.original_message, self.call_data, self.active_calls))

    @discord.ui.button(label="Удалить роль", style=discord.ButtonStyle.danger)
    async def delete_slot(self, interaction: discord.Interaction, button: discord.ui.Button):
        if len(self.call_data['slots']) <= 1:
            return await interaction.response.send_message("Нельзя удалить последнюю роль!", ephemeral=True)
        await interaction.response.send_modal(DeleteSlotModal(self.original_message, self.call_data, self.active_calls))

    @discord.ui.button(label="Изменить ссылку", style=discord.ButtonStyle.secondary)
    async def edit_link(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditLinkModal(self.call_data))

    @discord.ui.button(label="Позвать в войс", style=discord.ButtonStyle.success)
    async def summon_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        participants = [user for user in self.call_data['slots'] if user is not None]
        
        if not participants:
            return await interaction.response.send_message("В сборе пока никто не участвует!", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        
        # Получаем актуальные данные о членах сервера для проверки voice_state
        members = []
        for p in participants:
            m = interaction.guild.get_member(p.id)
            if not m:
                try:
                    m = await interaction.guild.fetch_member(p.id)
                except:
                    m = p
            members.append(m)
            
        # Определяем целевой голосовой канал
        organizer_member = interaction.guild.get_member(self.call_data['organizer'].id)
        organizer_vc = organizer_member.voice.channel if (organizer_member and organizer_member.voice) else None
        
        link_vc = None
        link = self.call_data.get('link')
        if link:
            import re
            match = re.search(r'channels/\d+/(\d+)', link)
            if match:
                try:
                    link_vc = interaction.guild.get_channel(int(match.group(1)))
                except:
                    pass
                    
        target_vc = link_vc or organizer_vc
        missing_members = []
        
        if target_vc:
            # Есть конкретный целевой войс — пингуем тех, кто не в нем
            for m in members:
                if not hasattr(m, 'voice') or m.voice is None or m.voice.channel != target_vc:
                    missing_members.append(m)
        elif link:
            # Есть ссылка, но конкретный войс-канал не найден в дискорде — пингуем тех, кто вообще не в войсе
            for m in members:
                if not hasattr(m, 'voice') or m.voice is None or m.voice.channel is None:
                    missing_members.append(m)
        else:
            # Нет ни ссылки, ни войса организатора — пингуем всех
            missing_members = members
            
        if not missing_members:
            return await interaction.followup.send("🔊 Все участники уже находятся в голосовом канале!", ephemeral=True)
            
        mentions_str = " ".join([m.mention for m in missing_members])
        
        if target_vc:
            summon_msg = f"📢 {mentions_str}\n**Все в голосовой канал {target_vc.mention}!**"
        else:
            summon_msg = f"📢 {mentions_str}\n**Все в голосовой канал!**"
            
        if link:
            summon_msg += f"\n🔗 **Заходите сюда:** {link}"
            
        # Отправляем в ветку, если она есть, иначе в канал
        if self.original_message.thread:
            await self.original_message.thread.send(summon_msg)
        else:
            await self.original_message.channel.send(summon_msg)
            
        await interaction.followup.send(f"✅ Оповещены отсутствующие участники ({len(missing_members)} чел.)!", ephemeral=True)

    @discord.ui.button(label="📨 ЛС Участникам", style=discord.ButtonStyle.secondary)
    async def dm_summon(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Эта функция доступна только администраторам сервера!", ephemeral=True)
            
        participants = [user for user in self.call_data['slots'] if user is not None]
        if not participants:
            return await interaction.response.send_message("В сборе пока никто не участвует!", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        
        # Получаем актуальные данные о членах сервера для проверки voice_state
        members = []
        for p in participants:
            member = interaction.guild.get_member(p.id)
            if not member:
                try:
                    member = await interaction.guild.fetch_member(p.id)
                except:
                    member = p
            members.append(member)
            
        # Определяем целевой голосовой канал
        organizer_member = interaction.guild.get_member(self.call_data['organizer'].id)
        organizer_vc = organizer_member.voice.channel if (organizer_member and organizer_member.voice) else None
        
        link_vc = None
        link = self.call_data.get('link')
        if link:
            import re
            match = re.search(r'channels/\d+/(\d+)', link)
            if match:
                try:
                    link_vc = interaction.guild.get_channel(int(match.group(1)))
                except:
                    pass
                    
        target_vc = link_vc or organizer_vc
        missing_members = []
        
        if target_vc:
            # Есть конкретный целевой войс — пингуем тех, кто не в нем
            for m in members:
                if not hasattr(m, 'voice') or m.voice is None or m.voice.channel != target_vc:
                    missing_members.append(m)
        elif link:
            # Есть ссылка, но конкретный войс-канал не найден в дискорде — пингуем тех, кто вообще не в войсе
            for m in members:
                if not hasattr(m, 'voice') or m.voice is None or m.voice.channel is None:
                    missing_members.append(m)
        else:
            # Нет ни ссылки, ни войса организатора — пингуем всех
            missing_members = members
            
        if not missing_members:
            return await interaction.followup.send("🔊 Все участники уже находятся в голосовом канале!", ephemeral=True)
            
        # Готовим сообщение для ЛС
        organizer = self.call_data['organizer']
        title = self.call_data.get('title') or "⚔️ Сбор на выезд"
        desc = self.call_data.get('description') or ""
        
        # Получаем ссылку на сообщение или ветку
        jump_url = None
        if self.original_message.thread:
            jump_url = self.original_message.thread.jump_url
        else:
            jump_url = self.original_message.jump_url
            
        dm_content = (
            f"🔔 **Вас зовут на контент!**\n\n"
            f"**Сбор:** {title}\n"
            f"**Описание:** {desc}\n"
            f"**Организатор:** {organizer.display_name}\n"
        )
        if link:
            dm_content += f"🔗 **Голосовой канал:** {link}\n"
        else:
            dm_content += f"🔗 **Ссылка на сбор:** {jump_url}\n"
            
        success_list = []
        fail_list = []
        
        for member in missing_members:
            try:
                await member.send(dm_content)
                success_list.append(member)
            except Exception:
                fail_list.append(member)
                
        # Составляем отчет (без пингов, ники каждый с новой строки)
        report_msg = "📨 **Отчет о рассылке личных сообщений:**\n"
        if success_list:
            report_msg += f"✅ **Успешно отправлено ({len(success_list)}):**\n" + "\n".join([f"{m.display_name}" for m in success_list]) + "\n"
        if fail_list:
            report_msg += f"❌ **Не удалось отправить ({len(fail_list)} - закрыты ЛС):**\n" + "\n".join([f"{m.display_name}" for m in fail_list]) + "\n"
            
        # Отправляем в ветку, если она есть, иначе в канал
        if self.original_message.thread:
            await self.original_message.thread.send(report_msg)
        else:
            await self.original_message.channel.send(report_msg)
            
        await interaction.followup.send(f"✅ Рассылка ЛС завершена! Успешно: {len(success_list)}, ошибка: {len(fail_list)}.", ephemeral=True)

class CallRoleView(discord.ui.View):
    """Вид с кнопками ролей под основным сообщением"""
    def __init__(self, call_data, active_calls):
        super().__init__(timeout=None)
        self.active_calls = active_calls
        # Кнопки ролей (максимум 21 кнопка, чтобы вписаться в лимит Discord из 25 компонентов с учетом 4 кнопок управления)
        is_paused = call_data.get('paused', False)
        slots_limit = 25 - 4
        for i, label in enumerate(call_data['slot_labels'][:slots_limit]):
            btn = RoleButton(label=label, slot_idx=i, active_calls=active_calls)
            if is_paused:
                btn.disabled = True
            
            # Если слот занят - помечаем синим (primary)
            if call_data['slots'][i] is not None:
                btn.style = discord.ButtonStyle.primary
            else:
                btn.style = discord.ButtonStyle.secondary
                
            self.add_item(btn)
        
        # Кнопки управления (в новый ряд, если кнопок много)
        self.add_item(FinishButton(active_calls=active_calls))
        self.add_item(DeleteButton(active_calls=active_calls))
        self.add_item(ManageButton(active_calls=active_calls))
        self.add_item(SaveCallButton(active_calls=active_calls))
