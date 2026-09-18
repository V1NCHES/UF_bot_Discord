# -*- coding: utf-8 -*-
import os
import json
import asyncio
import discord
from discord.ext import commands
from discord import app_commands

from bot.utils import check_user_permissions, load_settings, get_setting

def load_ava_portals():
    if os.path.exists('ava_portals_cache.json'):
        try:
            with open('ava_portals_cache.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка при загрузке ava_portals_cache.json: {e}")
            return []
    return []

class AvaPortalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.portals = load_ava_portals()

    @app_commands.command(name='ava_portal', description="Информация о локации Авалонского портала")
    @app_commands.describe(location="Название аволонской локации (например: Fynitos-Ezatam)")
    async def ava_portal(self, interaction: discord.Interaction, location: str):
        if not await check_user_permissions(interaction):
            return
            
        loc_clean = location.strip().lower()
        found = None
        for p in self.portals:
            if p['location'].lower() == loc_clean:
                found = p
                break
                
        if not found:
            return await interaction.response.send_message(
                f"❌ Локация `{location}` не найдена! Убедитесь, что выбрали локацию из выпадающего списка.",
                ephemeral=True
            )
            
        raw_contents = found['contents']
        contents_list = [c.strip() for c in raw_contents.split(',') if c.strip()]
        formatted_contents = ""
        for i, c in enumerate(contents_list):
            if i < len(contents_list) - 1:
                formatted_contents += f"{c}, \n"
            else:
                formatted_contents += f"{c}"

        description_text = (
            f"📍 **Тир локации** {found['tier']}\n"
            f"📦 **Размер сундуков**\n{found['size']}\n"
            f"✨ **Содержимое**\n{formatted_contents}"
        )

        embed = discord.Embed(
            title=f"🌀 Авалонский портал: {found['location']}",
            description=description_text,
            color=discord.Color.from_str("#00FFD8")
        )
        embed.set_footer(text="United Force • База данных Авалона")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message(embed=embed)

    @ava_portal.autocomplete('location')
    async def ava_portal_location_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        current_lower = current.lower().strip()
        
        choices = []
        for p in self.portals:
            loc_name = p['location']
            if not current_lower or current_lower in loc_name.lower():
                choices.append(app_commands.Choice(name=loc_name, value=loc_name))
                if len(choices) >= 25:
                    break
        return choices

    @app_commands.command(name='ava_portal_sync', description="Синхронизация базы данных Авалонских порталов с Google Sheets (Админ)")
    async def ava_portal_sync(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ У вас нет прав для выполнения этой команды!", ephemeral=True)
            
        await interaction.response.defer(ephemeral=True)
        
        try:
            from bot.logger import get_gspread_client
            from bot import config
            
            def do_sync():
                client = get_gspread_client()
                if not client:
                    raise ConnectionError("Не удалось авторизоваться в Google Sheets")
                sheet = client.open_by_key(config.SPREADSHEET_ID).get_worksheet_by_id(1107253052)
                rows = sheet.get_all_values()
                
                new_data = []
                for row in rows[1:]:
                    if len(row) >= 4 and row[0].strip():
                        new_data.append({
                            'location': row[0].strip(),
                            'tier': row[1].strip(),
                            'size': row[2].strip(),
                            'contents': row[3].strip()
                        })
                with open('ava_portals_cache.json', 'w', encoding='utf-8') as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=4)
                return new_data
                
            loop = asyncio.get_running_loop()
            self.portals = await loop.run_in_executor(None, do_sync)
            
            await interaction.followup.send(f"✅ База данных порталов Авалона успешно синхронизирована! Загружено {len(self.portals)} локаций.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Ошибка синхронизации с Google Таблицей: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AvaPortalCog(bot))
