# modules/config_painel.py
import discord
from discord.ext import commands
from discord import app_commands, ui, ButtonStyle, SelectOption
import json
import os
import asyncio
import re

CONFIG_FILE = "config.json"

class ConfigView(ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    # Aqui virão os botões e métodos da View

class ConfigCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_cache = {}  # Cache das configs para acesso rápido
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.config_cache = json.load(f)

    def save_config(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.config_cache, f, indent=4, ensure_ascii=False)

async def setup(bot):
    await bot.add_cog(ConfigCog(bot))
