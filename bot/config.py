# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
import discord

# Загружаем переменные окружения из корня
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
SPREADSHEET_ID = "1Ey0TKDDNRs5bZfaswPzgFpTFja1URcgayOMEBGj8Yek"
CREDENTIALS_FILE = "credentials.json"

def get_intents():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.voice_states = True
    return intents
