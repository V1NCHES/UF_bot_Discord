# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
import discord

# Загружаем переменные окружения из корня
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
SPREADSHEET_ID = "1Ey0TKDDNRs5bZfaswPzgFpTFja1URcgayOMEBGj8Yek"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env_creds = os.getenv('CREDENTIALS_FILE', 'credentials.json')
if os.path.isabs(_env_creds):
    CREDENTIALS_FILE = _env_creds
else:
    _root_creds = os.path.join(BASE_DIR, _env_creds)
    if os.path.exists(_root_creds):
        CREDENTIALS_FILE = _root_creds
    else:
        _cwd_creds = os.path.join(os.getcwd(), _env_creds)
        CREDENTIALS_FILE = _cwd_creds if os.path.exists(_cwd_creds) else _root_creds

def get_intents():
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.voice_states = True
    return intents
