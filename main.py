import os
import sys
import asyncio
import json
from datetime import datetime
from aiohttp import web
import discord
from discord.ext import commands

# ==================== KEEP-ALIVE SERVER (PORTA 10000) ====================
class KeepAliveServer:
    def __init__(self):
        self.app = None
        self.runner = None
        self.site = None
        self.bot = None
    
    async def start(self):
        try:
            self.app = web.Application()
            
            async def handle_home(request):
                return web.Response(
                    text=f"✅ Bot ONLINE - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
                    content_type='text/plain'
                )
            
            async def handle_health(request):
                return web.json_response({
                    "status": "online",
                    "timestamp": datetime.now().isoformat(),
                    "bot": self.bot.user.name if self.bot and self.bot.user else "Conectando..."
                })
            
            self.app.router.add_get('/', handle_home)
            self.app.router.add_get('/health', handle_health)
            
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            # Usa a porta definida pelo ambiente ou 10000 (Render geralmente usa 10000)
            port = int(os.environ.get('PORT', 10000))
            self.site = web.TCPSite(self.runner, '0.0.0.0', port)
            await self.site.start()
            
            print(f"🌐 Keep-alive rodando na porta {port}")
            
        except Exception as e:
            print(f"⚠️ Erro ao iniciar servidor keep-alive: {e}")
    
    async def stop(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
    
    def set_bot(self, bot):
        self.bot = bot

# Criar instância do keep-alive
keep_alive = KeepAliveServer()

# ==================== CONFIGURAÇÃO DO BOT ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ==================== SISTEMA DE PERSISTÊNCIA ====================
class PainelManager:
    def __init__(self):
        self.paineis_ativos = {}
        self.arquivo_backup = "paineis_backup.json"
        self.carregar_backup()
    
    def salvar_backup(self):
        try:
            dados = {}
            for guild_id, paineis in self.paineis_ativos.items():
                dados[str(guild_id)] = paineis
            with open(self.arquivo_backup, 'w', encoding='utf-8') as f:
                json.dump(dados, f, indent=4, ensure_ascii=False)
            print(f"✅ Backup dos painéis salvo: {len(self.paineis_ativos)} servidores")
        except Exception as e:
            print(f"❌ Erro ao salvar backup: {e}")
    
    def carregar_backup(self):
        try:
            if os.path.exists(self.arquivo_backup):
                with open(self.arquivo_backup, 'r', encoding='utf-8') as f:
                    dados = json.load(f)
                for guild_id, paineis in dados.items():
                    self.paineis_ativos[int(guild_id)] = paineis
                print(f"✅ Backup carregado: {len(self.paineis_ativos)} servidores com painéis")
        except Exception as e:
            print(f"❌ Erro ao carregar backup: {e}")
    
    def adicionar_painel(self, guild_id, canal_id, mensagem_id, tipo):
        if guild_id not in self.paineis_ativos:
            self.paineis_ativos[guild_id] = []
        # Evita duplicatas
        for p in self.paineis_ativos[guild_id]:
            if p['mensagem_id'] == mensagem_id:
                return False
        painel = {
            'canal_id': canal_id,
            'mensagem_id': mensagem_id,
            'tipo': tipo,
            'criado_em': str(discord.utils.utcnow())
        }
        self.paineis_ativos[guild_id].append(painel)
        self.salvar_backup()
        return True
    
    def remover_painel(self, guild_id, mensagem_id):
        if guild_id in self.paineis_ativos:
            original_len = len(self.paineis_ativos[guild_id])
            self.paineis_ativos[guild_id] = [p for p in self.paineis_ativos[guild_id] if p['mensagem_id'] != mensagem_id]
            if not self.paineis_ativos[guild_id]:
                del self.paineis_ativos[guild_id]
            if len(self.paineis_ativos.get(guild_id, [])) != original_len:
                self.salvar_backup()
                return True
        return False
    
    async def restaurar_paineis(self, bot):
        print("\n🔄 Verificando painéis ativos...")
        total = 0
        for guild_id, paineis in self.paineis_ativos.items():
            guild = bot.get_guild(guild_id)
            if not guild:
                continue
            for painel in paineis:
                try:
                    canal = guild.get_channel(painel['canal_id'])
                    if canal:
                        await canal.fetch_message(painel['mensagem_id'])
                        total += 1
                except:
                    pass
        print(f"📊 {total} painéis ativos restaurados da memória")

painel_manager = PainelManager()

# ==================== FUNÇÕES DE BOAS-VINDAS ====================
async def dar_cargo_visitante(member):
    cargo_nome = "🙋‍♂️ | Visitante"
    cargo = discord.utils.get(member.guild.roles, name=cargo_nome)
    if not cargo:
        try:
            cargo = await member.guild.create_role(name=cargo_nome, reason="Cargo automático para novos membros")
            print(f"✅ Cargo '{cargo_nome}' criado")
        except Exception as e:
            print(f"❌ Erro ao criar cargo: {e}")
            return False
    try:
        await member.add_roles(cargo)
        print(f"✅ Cargo '{cargo_nome}' dado para {member.name}")
        return True
    except Exception as e:
        print(f"❌ Erro ao dar cargo: {e}")
        return False

async def enviar_mensagem_boas_vindas(member):
    canal_nome = "📤・bem-vindo"
    canal = discord.utils.get(member.guild.text_channels, name=canal_nome)
    if not canal:
        try:
            overwrites = {
                member.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                member.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            canal = await member.guild.create_text_channel(canal_nome, overwrites=overwrites)
            print(f"✅ Canal '{canal_nome}' criado")
        except Exception as e:
            print(f"❌ Erro ao criar canal: {e}")
            return False
    embed = discord.Embed(
        title="🎉 SEJA BEM-VINDO! 🎉",
        description=f"Olá {member.mention}! Bem-vindo ao servidor!",
        color=discord.Color.green()
    )
    embed.add_field(name="📌 PRIMEIRO PASSO", value=f"Por favor, vá até o canal **{canal_nome}** para fazer seu set!", inline=False)
    embed.add_field(name="🎮 DICA", value="Lá você poderá escolher quem te recrutou!", inline=False)
    embed.set_footer(text="Espero que goste! 🚀")
    embed.set_thumbnail(url=member.display_avatar.url)
    try:
        await canal.send(embed=embed)
        print(f"✅ Mensagem de boas-vindas enviada para {member.name}")
        return True
    except Exception as e:
        print(f"❌ Erro ao enviar mensagem: {e}")
        return False

# ==================== CARREGAR MÓDULOS ====================
async def carregar_modulos():
    modules = ['modules.sets', 'modules.painel_rec', 'modules.hierarquia', 'modules.cargos', 'modules.limpeza']
    print("\n📦 Carregando módulos:")
    for module in modules:
        try:
            await bot.load_extension(module)
            print(f"✅ {module}")
        except Exception as e:
            print(f"❌ {module}: {e}")

# ==================== EVENTOS ====================
@bot.event
async def on_ready():
    print(f"\n🎉 Bot conectado como: {bot.user.name}")
    print(f"📊 Servidores: {len(bot.guilds)}")
    keep_alive.set_bot(bot)
    await painel_manager.restaurar_paineis(bot)
    await bot.change_presence(activity=discord.Game(name="!ajuda | 🚀"))
    print("="*50)

@bot.event
async def on_member_join(member):
    print(f"\n👤 Novo membro: {member.name}")
    await dar_cargo_visitante(member)
    await enviar_mensagem_boas_vindas(member)

@bot.event
async def setup_hook():
    await carregar_modulos()

# ==================== COMANDOS ÚTEIS ====================
@bot.command(name="salvar_paineis")
@commands.has_permissions(administrator=True)
async def salvar_paineis(ctx):
    painel_manager.salvar_backup()
    await ctx.send("✅ Painéis salvos")

@bot.command(name="listar_paineis")
@commands.has_permissions(administrator=True)
async def listar_paineis(ctx):
    guild_id = ctx.guild.id
    if guild_id not in painel_manager.paineis_ativos:
        await ctx.send("📭 Nenhum painel ativo")
        return
    paineis = painel_manager.paineis_ativos[guild_id]
    embed = discord.Embed(title="📋 Painéis Ativos", description=f"Total: {len(paineis)}")
    for i, p in enumerate(paineis, 1):
        embed.add_field(name=f"#{i}", value=f"Tipo: {p['tipo']}\nCanal: <#{p['canal_id']}>", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="testar")
@commands.has_permissions(administrator=True)
async def testar_boas_vindas(ctx, membro: discord.Member = None):
    membro = membro or ctx.author
    await ctx.send(f"🔄 Testando para {membro.mention}...")
    await dar_cargo_visitante(membro)
    await enviar_mensagem_boas_vindas(membro)
    await ctx.send("✅ Teste concluído")

# ==================== FUNÇÃO PRINCIPAL ====================
async def main():
    print("\n" + "="*50)
    print("🚀 INICIANDO BOT DISCORD - JUGADORES")
    print("="*50)
    
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ DISCORD_TOKEN não encontrado!")
        sys.exit(1)
    
    # Iniciar servidor keep-alive (não bloqueia)
    asyncio.create_task(keep_alive.start())
    
    # Pequena pausa para evitar race condition
    await asyncio.sleep(1)
    
    # Iniciar bot
    try:
        await bot.start(TOKEN)
    except Exception as e:
        print(f"❌ Erro ao iniciar bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Bot finalizado")
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        sys.exit(1)
