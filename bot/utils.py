# -*- coding: utf-8 -*-
import os
import json
import discord
from bot.config import SPREADSHEET_ID

def load_settings():
    if os.path.exists('settings.json'):
        try:
            with open('settings.json', 'r') as f:
                return json.load(f)
        except: return {}
    return {}

def save_settings(settings):
    with open('settings.json', 'w') as f:
        json.dump(settings, f)

def get_setting(settings, guild_id, key, default=None):
    if guild_id:
        g_str = str(guild_id)
        if "guilds" in settings and g_str in settings["guilds"]:
            if key in settings["guilds"][g_str]:
                return settings["guilds"][g_str][key]
        return default
    return settings.get(key, default)

def set_setting(settings, guild_id, key, value):
    if guild_id:
        g_str = str(guild_id)
        if "guilds" not in settings:
            settings["guilds"] = {}
        if g_str not in settings["guilds"]:
            settings["guilds"][g_str] = {}
        settings["guilds"][g_str][key] = value
    else:
        settings[key] = value

def remove_setting(settings, guild_id, key):
    if guild_id:
        g_str = str(guild_id)
        if "guilds" in settings and g_str in settings["guilds"]:
            settings["guilds"][g_str].pop(key, None)
    else:
        settings.pop(key, None)

def get_allowed_channel_ids(settings, call_type, guild_id=None):
    val = get_setting(settings, guild_id, f"{call_type}_channel_ids")
    if isinstance(val, list):
        return [int(x) for x in val]
    val_old = get_setting(settings, guild_id, f"{call_type}_channel_id")
    if val_old:
        return [int(val_old)]
    return []

def format_balance(val):
    if val is None:
        return "0"
    try:
        clean = str(val).replace(' ', '').replace(',', '').replace('\xa0', '').strip()
        if not clean:
            return "0"
        num = int(float(clean))
    except (ValueError, TypeError):
        return str(val)
    
    abs_num = abs(num)
    sign = "-" if num < 0 else ""
    
    if abs_num >= 1000000:
        val_m = abs_num / 1000000
        return f"{sign}{val_m:.4f}".rstrip('0').rstrip('.') + "m"
    elif abs_num >= 1000:
        val_k = abs_num / 1000
        return f"{sign}{val_k:.3f}".rstrip('0').rstrip('.') + "k"
    else:
        return f"{sign}{abs_num}"

async def check_user_permissions(interaction: discord.Interaction):
    """Проверка разрешений для обычных пользовательских команд"""
    if interaction.user.guild_permissions.administrator:
        return True
        
    settings = load_settings()
    guild_id = interaction.guild.id if interaction.guild else None
    
    # 1. Проверка каналов доступа
    channel_ids = [cid for cid in get_allowed_channel_ids(settings, 'user', guild_id) if interaction.guild.get_channel(cid) is not None]
    if channel_ids and interaction.channel.id not in channel_ids:
        mentions = ", ".join([f"<#{cid}>" for cid in channel_ids])
        msg = f"❌ Эта команда доступна только в каналах: {mentions}"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
        return False
        
    # 2. Проверка роли для общего пользования (user_role_id)
    role_id = get_setting(settings, guild_id, 'user_role_id')
    if role_id:
        required_role = interaction.guild.get_role(role_id)
        if required_role:
            user_top_role = interaction.user.top_role
            if user_top_role.position < required_role.position:
                msg = f"❌ У вас недостаточно прав. Требуется роль не ниже {required_role.mention}"
                if interaction.response.is_done():
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)
                return False
                
    return True

async def check_permissions(interaction: discord.Interaction, call_type: str):
    if interaction.user.guild_permissions.administrator:
        return True
        
    settings = load_settings()
    guild_id = interaction.guild.id if interaction.guild else None
    
    channel_ids = [cid for cid in get_allowed_channel_ids(settings, call_type, guild_id) if interaction.guild.get_channel(cid) is not None]
    if channel_ids and interaction.channel.id not in channel_ids:
        mentions = ", ".join([f"<#{cid}>" for cid in channel_ids])
        msg = f"❌ Эта команда доступна только в каналах: {mentions}"
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
        return False
        
    role_id = get_setting(settings, guild_id, f'{call_type}_role_id')
    if role_id:
        required_role = interaction.guild.get_role(role_id)
        if required_role:
            user_top_role = interaction.user.top_role
            if user_top_role.position < required_role.position:
                msg = f"❌ У вас недостаточно прав. Требуется роль не ниже {required_role.mention}"
                if interaction.response.is_done():
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    await interaction.response.send_message(msg, ephemeral=True)
                return False
                
    return True

def parse_msk_time(time_str: str, date_str: str = None) -> int:
    from datetime import datetime, timedelta, timezone
    import re
    
    time_str = time_str.strip()
    now_utc = datetime.now(timezone.utc)
    tz_msk = timezone(timedelta(hours=3))
    now_msk = now_utc.astimezone(tz_msk)
    
    parsed_date = None
    if date_str:
        date_str = date_str.strip()
        match_d1 = re.match(r'^(\d{1,2})[:.-](\d{1,2})$', date_str)
        if match_d1:
            day = int(match_d1.group(1))
            month = int(match_d1.group(2))
            parsed_date = (day, month, now_msk.year)
        else:
            match_d2 = re.match(r'^(\d{1,2})[:.-](\d{1,2})[:.-](\d{2,4})$', date_str)
            if match_d2:
                day = int(match_d2.group(1))
                month = int(match_d2.group(2))
                year = int(match_d2.group(3))
                if year < 100:
                    year += 2000
                parsed_date = (day, month, year)
    
    match_combined2 = re.match(r'^(\d{1,2})[:.-](\d{1,2})\s+(\d{1,2})[:.-](\d{2})$', time_str)
    if match_combined2:
        day = int(match_combined2.group(1))
        month = int(match_combined2.group(2))
        hours = int(match_combined2.group(3))
        minutes = int(match_combined2.group(4))
        dt = now_msk.replace(month=month, day=day, hour=hours, minute=minutes, second=0, microsecond=0)
        return int(dt.timestamp())
        
    match_combined3 = re.match(r'^(\d{1,2})[:.-](\d{1,2})[:.-](\d{2,4})\s+(\d{1,2})[:.-](\d{2})$', time_str)
    if match_combined3:
        day = int(match_combined3.group(1))
        month = int(match_combined3.group(2))
        year = int(match_combined3.group(3))
        if year < 100:
            year += 2000
        hours = int(match_combined3.group(4))
        minutes = int(match_combined3.group(5))
        dt = datetime(year, month, day, hours, minutes, tzinfo=tz_msk)
        return int(dt.timestamp())

    match_t = re.match(r'^(\d{1,2})[:.-](\d{2})$', time_str)
    if match_t:
        hours = int(match_t.group(1))
        minutes = int(match_t.group(2))
        if parsed_date:
            day, month, year = parsed_date
            dt = datetime(year, month, day, hours, minutes, tzinfo=tz_msk)
            return int(dt.timestamp())
        else:
            dt = now_msk.replace(hour=hours, minute=minutes, second=0, microsecond=0)
            if dt < now_msk:
                dt += timedelta(days=1)
            return int(dt.timestamp())
            
    raise ValueError("Неверный формат времени")

def save_call_to_cache(call_data):
    try:
        cache = {}
        if os.path.exists('calls_cache.json') and os.path.getsize('calls_cache.json') > 0:
            try:
                with open('calls_cache.json', 'r', encoding='utf-8') as f:
                    cache = json.load(f)
            except Exception as read_err:
                print(f"Предупреждение при чтении кэша: {read_err}. Создаем новый.")
        
        c_id = call_data['id']
        cache[c_id] = {
            'id': c_id,
            'template_name': call_data.get('template_name'),
            'call_type': call_data.get('call_type', 'call'),
            'title': call_data.get('title'),
            'description': call_data.get('description'),
            'slot_labels': call_data.get('slot_labels', []),
            'slot_limits': call_data.get('slot_limits', []),
            'required_role_id': call_data['required_role'].id if call_data.get('required_role') else None,
            'ping_role_id': call_data['ping_role'].id if call_data.get('ping_role') else None,
            'link': call_data.get('link'),
            'duration': call_data.get('duration')
        }
        
        with open('calls_cache.json', 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения сбора в кэш: {e}")

def load_call_from_cache(call_id, guild):
    try:
        if not os.path.exists('calls_cache.json') or os.path.getsize('calls_cache.json') == 0:
            return None
            
        with open('calls_cache.json', 'r', encoding='utf-8') as f:
            cache = json.load(f)
            
        data = cache.get(call_id)
        if not data:
            return None
            
        required_role = None
        if data.get('required_role_id') and guild:
            required_role = guild.get_role(data['required_role_id'])
            
        ping_role = None
        if data.get('ping_role_id') and guild:
            ping_role = guild.get_role(data['ping_role_id'])
            
        return {
            'id': data['id'],
            'template_name': data.get('template_name'),
            'call_type': data.get('call_type', 'call'),
            'title': data.get('title'),
            'description': data.get('description'),
            'slot_labels': data.get('slot_labels', []),
            'slot_limits': data.get('slot_limits', []),
            'required_role': required_role,
            'ping_role': ping_role,
            'link': data.get('link'),
            'duration': data.get('duration')
        }
    except Exception as e:
        print(f"Ошибка загрузки сбора из кэша: {e}")
        return None
