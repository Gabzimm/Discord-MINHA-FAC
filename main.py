import os
import sys
import asyncio
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands

# ==================== CONFIGURAÇÃO DO KEEP-ALIVE ====================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot está ONLINE!"

class KeepAlive:
    def __init__(self):
        self.server_thread = None
        
    def start(self):
        """Inicia o servidor Flask em uma thread separada"""
        port = int(os.environ.get('PORT', 8080))
        
        def run():
            app.run(host='0.0.0.0', port=port, debug=False)
        
        self.server_thread = Thread(target=run)
        self.server_thread.daemon = True
        self.server_thread.start()
        print(f"🌐 Servidor keep-alive rodando na porta {port}")

keep_alive = KeepAlive()

# ==================== CONFIGURAÇÃO DO BOT ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ==================== CARREGAR MÓDULOS ====================
async def carregar_modulos():
    """Carrega todos os módulos do bot"""
    modules = [
        'modules.sets',
        'modules.painel_rec', 
        'modules.hierarquia',
        'modules.cargos'
    ]
    
    print("\n📦 Carregando módulos:")
    print("-" * 40)
    
    for module in modules:
        try:
            await bot.load_extension(module)
            print(f"✅ {module} - Carregado com sucesso!")
        except Exception as e:
            print(f"❌ {module} - Erro: {e}")
    
    print("-" * 40)

# ==================== EVENTOS DO BOT ====================
@bot.event
async def on_ready():
    print(f"\n🎉 Bot conectado como: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"📊 Servidores: {len(bot.guilds)}")
    print("="*60)

@bot.event
async def setup_hook():
    """Hook executado antes do bot iniciar"""
    await carregar_modulos()

# ==================== FUNÇÃO PRINCIPAL ====================
async def main():
    print("\n" + "="*60)
    print("🚀 INICIANDO BOT DISCORD - JUGADORES")
    print("="*60)
    
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("\n❌ DISCORD_TOKEN não encontrado!")
        print("\n📌 Configure a variável de ambiente DISCORD_TOKEN")
        sys.exit(1)
    
    # Iniciar keep-alive
    try:
        print("\n🌐 Iniciando servidor keep-alive...")
        await asyncio.to_thread(keep_alive.start)
    except Exception as e:
        print(f"⚠️ Erro no keep-alive: {e}")
    
    # Conectar ao Discord
    print("\n🔗 Conectando ao Discord...")
    
    try:
        await bot.start(TOKEN)
    except discord.LoginFailure:
        print("\n❌ Token inválido! Verifique o DISCORD_TOKEN")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro ao conectar: {e}")
        sys.exit(1)

# ==================== EXECUÇÃO ====================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Bot finalizado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        sys.exit(1)
