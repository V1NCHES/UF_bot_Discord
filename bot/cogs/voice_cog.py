# -*- coding: utf-8 -*-
import time
import re
import discord
from discord.ext import commands
from discord import app_commands

def format_duration(seconds: float) -> str:
    secs = int(seconds)
    if secs < 60:
        return f"{secs} сек."
    mins = secs // 60
    hours = mins // 60
    mins %= 60
    if hours > 0:
        return f"{hours} ч. {mins} мин."
    return f"{mins} мин."

def get_call_target_vc(guild: discord.Guild, call_data: dict) -> discord.VoiceChannel:
    """Определяет целевой голосовой канал сбора по ссылке или по организатору"""
    link = call_data.get('link')
    if link:
        match = re.search(r'channels/\d+/(\d+)', link)
        if match:
            ch = guild.get_channel(int(match.group(1)))
            if isinstance(ch, discord.VoiceChannel):
                return ch

    organizer = call_data.get('organizer')
    if organizer:
        m = guild.get_member(organizer.id)
        if m and m.voice and m.voice.channel:
            return m.voice.channel

    return None

def get_call_participants(call_data: dict) -> list[discord.Member]:
    """Возвращает уникальный список всех записанных участников сбора"""
    participants = []
    for slot in call_data.get('slots', []):
        if isinstance(slot, list):
            for u in slot:
                if u and u not in participants:
                    participants.append(u)
        elif slot and slot not in participants:
            participants.append(slot)
    return participants

def update_call_voice_stats(guild: discord.Guild, call_data: dict, member: discord.Member, before_ch, after_ch):
    """Обновляет статистику нахождения игрока в войсе для конкретного сбора"""
    target_vc = get_call_target_vc(guild, call_data)
    vt = call_data.setdefault('voice_tracking', {})
    stats = vt.setdefault(member.id, {
        'total_seconds': 0.0,
        'joined_at': None,
        'is_in_vc': False
    })
    now = time.time()

    # Считаем, что игрок в нужном войсе, если он зашел в target_vc (или в любой войс, если target_vc не определен)
    in_target_after = after_ch is not None and (target_vc is None or after_ch.id == target_vc.id)
    in_target_before = before_ch is not None and (target_vc is None or before_ch.id == target_vc.id)

    if in_target_after and not stats['is_in_vc']:
        stats['is_in_vc'] = True
        stats['joined_at'] = now
    elif not in_target_after and stats['is_in_vc']:
        if stats['joined_at']:
            stats['total_seconds'] += (now - stats['joined_at'])
        stats['is_in_vc'] = False
        stats['joined_at'] = None

class VoicePingView(discord.ui.View):
    def __init__(self, missing_members: list[discord.Member], target_vc: discord.VoiceChannel, call_link: str = None):
        super().__init__(timeout=300)
        self.missing_members = missing_members
        self.target_vc = target_vc
        self.call_link = call_link

    @discord.ui.button(label="Позвать отсутствующих", style=discord.ButtonStyle.danger, emoji="📢")
    async def ping_missing(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.missing_members:
            return await interaction.response.send_message("Все участники уже находятся в голосовом канале!", ephemeral=True)

        mentions_str = " ".join([m.mention for m in self.missing_members])
        if self.target_vc:
            text = f"📢 {mentions_str}\n⚔️ **Все в голосовой канал {self.target_vc.mention}!**"
        else:
            text = f"📢 {mentions_str}\n⚔️ **Все в голосовой канал сбора!**"

        if self.call_link:
            text += f"\n🔗 {self.call_link}"

        await interaction.channel.send(text)
        await interaction.response.send_message("✅ Оповещение отправлено в канал!", ephemeral=True)

class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Слушатель переходов между голосовыми каналами для учета времени"""
        if member.bot:
            return

        if not hasattr(self.bot, 'active_calls') or not self.bot.active_calls:
            return

        # Проверяем все активные уникальные сборы
        seen_calls = set()
        for call_data in list(self.bot.active_calls.values()):
            if not isinstance(call_data, dict):
                continue
            c_id = call_data.get('id')
            if not c_id or c_id in seen_calls:
                continue
            seen_calls.add(c_id)

            participants = get_call_participants(call_data)
            p_ids = {p.id for p in participants}

            if member.id in p_ids:
                update_call_voice_stats(member.guild, call_data, member, before.channel, after.channel)

    @app_commands.command(name='voice_check', description="Проверить присутствие участников сбора в голосовом канале и время в войсе")
    @app_commands.describe(call_id="ID сбора (необязательно, если вызвано в ветке или канале сбора)")
    async def voice_check(self, interaction: discord.Interaction, call_id: str = None):
        await interaction.response.defer(ephemeral=False)
        active_calls = getattr(self.bot, 'active_calls', {})

        call_data = None
        if call_id:
            for c in active_calls.values():
                if isinstance(c, dict) and c.get('id') == call_id:
                    call_data = c
                    break
        else:
            call_data = active_calls.get(interaction.channel_id)

        if not call_data:
            return await interaction.followup.send("❌ Активный сбор не найден. Укажите `call_id` или вызывайте команду в ветке сбора.", ephemeral=True)

        guild = interaction.guild
        participants = get_call_participants(call_data)
        if not participants:
            return await interaction.followup.send("⚠️ В этом сборе пока нет записанных участников!", ephemeral=True)

        target_vc = get_call_target_vc(guild, call_data)
        vt = call_data.setdefault('voice_tracking', {})
        now = time.time()

        in_vc_list = []
        missing_list = []
        stats_list = []

        for p in participants:
            # Получаем актуального участника сервера
            m = guild.get_member(p.id)
            if not m:
                try:
                    m = await guild.fetch_member(p.id)
                except:
                    m = p

            p_stats = vt.setdefault(m.id, {
                'total_seconds': 0.0,
                'joined_at': None,
                'is_in_vc': False
            })

            # Проверяем фактическое нахождение прямо сейчас
            is_currently_in = False
            if hasattr(m, 'voice') and m.voice and m.voice.channel:
                if target_vc is None or m.voice.channel.id == target_vc.id:
                    is_currently_in = True

            # Синхронизируем флаг с фактом
            if is_currently_in:
                if not p_stats['is_in_vc']:
                    p_stats['is_in_vc'] = True
                    p_stats['joined_at'] = now
                session_sec = now - (p_stats['joined_at'] or now)
                current_total = p_stats['total_seconds'] + session_sec
                in_vc_list.append((m, session_sec, current_total))
            else:
                if p_stats['is_in_vc']:
                    if p_stats['joined_at']:
                        p_stats['total_seconds'] += (now - p_stats['joined_at'])
                    p_stats['is_in_vc'] = False
                    p_stats['joined_at'] = None
                current_total = p_stats['total_seconds']
                missing_list.append((m, current_total))

            stats_list.append((m, is_currently_in, current_total))

        # Сортировка по общему времени
        stats_list.sort(key=lambda x: x[2], reverse=True)

        # Формируем Embed
        title = call_data.get('title') or "Сбор"
        desc = f"**Сбор:** `{call_data.get('id')}` — **{title}**\n"
        if target_vc:
            desc += f"**Целевой войс:** {target_vc.mention}\n"
        else:
            desc += "**Целевой войс:** *(не привязан, учитывается любой войс)*\n"

        desc += f"**Участников:** {len(participants)} чел. (В войсе: `{len(in_vc_list)}`, Отсутствуют: `{len(missing_list)}`)\n"

        embed = discord.Embed(
            title="🎙️ Проверка присутствия в голосовом канале",
            description=desc,
            color=discord.Color.green() if not missing_list else discord.Color.orange()
        )

        # 1. В войсе сейчас
        if in_vc_list:
            lines = [f"🟢 {m.mention} — `{format_duration(curr)}` в канале (всего: `{format_duration(tot)}`)" for m, curr, tot in in_vc_list]
            embed.add_field(name=f"🟢 В войсе прямо сейчас ({len(in_vc_list)})", value="\n".join(lines[:20]), inline=False)
        else:
            embed.add_field(name="🟢 В войсе прямо сейчас (0)", value="*Никого нет в голосовом канале*", inline=False)

        # 2. Отсутствуют
        if missing_list:
            lines = []
            for m, tot in missing_list:
                if tot > 0:
                    lines.append(f"🔴 {m.mention} — *(был {format_duration(tot)}, сейчас вышел)*")
                else:
                    lines.append(f"🔴 {m.mention} — *(не заходил)*")
            embed.add_field(name=f"🔴 Отсутствуют ({len(missing_list)})", value="\n".join(lines[:20]), inline=False)

        # 3. Общая статистика по времени
        time_lines = []
        for rank, (m, in_vc, tot) in enumerate(stats_list[:15], 1):
            icon = "🟢" if in_vc else "⚪"
            time_lines.append(f"`{rank}.` {icon} **{m.display_name}** — `{format_duration(tot)}`")
        if time_lines:
            embed.add_field(name="⏱️ Общее время в войсе (Топ)", value="\n".join(time_lines), inline=False)

        embed.set_footer(text="United Force • ZvZ Voice Tracker")

        missing_members_only = [m for m, _ in missing_list]
        view = VoicePingView(missing_members_only, target_vc, call_data.get('link'))
        await interaction.followup.send(embed=embed, view=view)

def generate_voice_finish_report(guild: discord.Guild, call_data: dict) -> discord.Embed:
    """Генерирует финальный отчет посещаемости войса при завершении сбора"""
    participants = get_call_participants(call_data)
    if not participants:
        return None

    target_vc = get_call_target_vc(guild, call_data)
    vt = call_data.get('voice_tracking', {})
    now = time.time()

    records = []
    for p in participants:
        stats = vt.get(p.id, {'total_seconds': 0.0, 'joined_at': None, 'is_in_vc': False})
        tot = stats['total_seconds']
        if stats.get('is_in_vc') and stats.get('joined_at'):
            tot += (now - stats['joined_at'])
        records.append((p, tot))

    records.sort(key=lambda x: x[1], reverse=True)

    embed = discord.Embed(
        title=f"📊 Итоговая статистика голосового канала • Сбор {call_data.get('id')}",
        description=f"Контент завершен. Сводка присутствия участников в войсе:\n" +
                    (f"**Голосовой канал:** {target_vc.mention}\n" if target_vc else ""),
        color=discord.Color.blue()
    )

    lines = []
    for rank, (p, tot) in enumerate(records, 1):
        if tot >= 300: # Более 5 минут
            icon = "🟢"
        elif tot > 0:
            icon = "🟡"
        else:
            icon = "🔴"
        lines.append(f"`{rank}.` {icon} {p.mention} — **{format_duration(tot)}**")

    embed.add_field(name=f"👥 Посещаемость ({len(records)} участников)", value="\n".join(lines[:25]), inline=False)
    embed.set_footer(text="United Force • Фиксация времени голосового канала")
    return embed

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))
