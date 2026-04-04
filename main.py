import os
import sys
import asyncio
import json
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

# ==================== SISTEMA DE PERSISTÊNCIA ====================
class PainelManager:
    def __init__(self):
        self.paineis_ativos = {}
        self.arquivo_backup = "paineis_backup.json"
        self.carregar_backup()
    
    def salvar_backup(self):
        """Salva os painéis ativos em um arquivo JSON"""
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
        """Carrega os painéis do arquivo de backup"""
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
        """Adiciona um painel à lista de ativos"""
        if guild_id not in self.paineis_ativos:
            self.paineis_ativos[guild_id] = []
        
        painel = {
            'canal_id': canal_id,
            'mensagem_id': mensagem_id,
            'tipo': tipo,
            'criado_em': str(discord.utils.utcnow())
        }
        
        self.paineis_ativos[guild_id].append(painel)
        self.salvar_backup()
    
    def remover_painel(self, guild_id, mensagem_id):
        """Remove um painel da lista"""
        if guild_id in self.paineis_ativos:
            self.paineis_ativos[guild_id] = [
                p for p in self.paineis_ativos[guild_id] 
                if p['mensagem_id'] != mensagem_id
            ]
            
            if not self.paineis_ativos[guild_id]:
                del self.paineis_ativos[guild_id]
            
            self.salvar_backup()
    
    async def restaurar_paineis(self, bot):
        """Restaura todos os painéis após o bot reiniciar"""
        print("\n🔄 Restaurando painéis ativos...")
        print("-" * 40)
        
        total_restaurados = 0
        total_erros = 0
        
        for guild_id, paineis in self.paineis_ativos.items():
            guild = bot.get_guild(guild_id)
            if not guild:
                print(f"⚠️ Servidor {guild_id} não encontrado")
                total_erros += len(paineis)
                continue
            
            for painel in paineis:
                try:
                    canal = guild.get_channel(painel['canal_id'])
                    if canal:
                        try:
                            mensagem = await canal.fetch_message(painel['mensagem_id'])
                            
                            # Verifica se a mensagem ainda existe e tem os componentes
                            if mensagem and mensagem.components:
                                print(f"✅ Painel restaurado: {guild.name} - #{canal.name} (Tipo: {painel['tipo']})")
                                total_restaurados += 1
                            else:
                                print(f"⚠️ Mensagem do painel não encontrada ou sem componentes em {guild.name}")
                                total_erros += 1
                        except discord.NotFound:
                            print(f"❌ Mensagem {painel['mensagem_id']} não encontrada em {guild.name}")
                            total_erros += 1
                    else:
                        print(f"❌ Canal não encontrado em {guild.name}")
                        total_erros += 1
                except Exception as e:
                    print(f"❌ Erro ao restaurar painel em {guild.name}: {e}")
                    total_erros += 1
        
        print("-" * 40)
        print(f"📊 Painéis restaurados: {total_restaurados} | Erros: {total_erros}")
        return total_restaurados

painel_manager = PainelManager()

# ==================== FUNÇÃO DE BOAS-VINDAS ====================
async def dar_cargo_visitante(member):
    """Dá o cargo de Visitante para o membro"""
    cargo_nome = "🙋‍♂️ | Visitante"
    cargo = discord.utils.get(member.guild.roles, name=cargo_nome)
    
    if cargo:
        try:
            await member.add_roles(cargo)
            print(f"✅ Cargo '{cargo_nome}' dado para {member.name}")
            return True
        except discord.Forbidden:
            print(f"❌ Sem permissão para dar o cargo {cargo_nome}")
            return False
        except Exception as e:
            print(f"❌ Erro ao dar cargo: {e}")
            return False
    else:
        print(f"⚠️ Cargo '{cargo_nome}' não encontrado no servidor!")
        return False

async def enviar_mensagem_boas_vindas(member):
    """Envia mensagem de boas-vindas para o membro"""
    canal_nome = "🚨・pedir-set"
    canal = discord.utils.get(member.guild.text_channels, name=canal_nome)
    
    if canal:
        embed = discord.Embed(
            title="🎉 SEJA BEM-VINDO! 🎉",
            description=f"Olá {member.mention}! Bem-vindo ao servidor!",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📌 PRIMEIRO PASSO",
            value=f"Por favor, vá até o canal **{canal_nome}** para fazer seu set!",
            inline=False
        )
        
        embed.add_field(
            name="🎮 DICA",
            value="Lá você poderá escolher seus jogos e cargos!",
            inline=False
        )
        
        embed.set_footer(text="Aproveite sua estadia! 🚀")
        embed.set_thumbnail(url=member.display_avatar.url)
        
        try:
            await canal.send(embed=embed)
            print(f"✅ Mensagem de boas-vindas enviada para {member.name}")
            return True
        except Exception as e:
            print(f"❌ Erro ao enviar mensagem: {e}")
            return False
    else:
        print(f"⚠️ Canal '{canal_nome}' não encontrado!")
        return False

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
            
            # Se o módulo tiver o painel_manager, injeta ele
            if hasattr(bot.get_cog(module.split('.')[-1].title()), 'set_painel_manager'):
                cog = bot.get_cog(module.split('.')[-1].title())
                cog.set_painel_manager(painel_manager)
                
        except Exception as e:
            print(f"❌ {module} - Erro: {e}")
    
    print("-" * 40)

# ==================== EVENTOS DO BOT ====================
@bot.event
async def on_ready():
    print(f"\n🎉 Bot conectado como: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"📊 Servidores: {len(bot.guilds)}")
    
    # Restaurar painéis após reconectar
    await painel_manager.restaurar_paineis(bot)
    
    print("="*60)

@bot.event
async def on_member_join(member):
    """Evento executado quando um novo membro entra no servidor"""
    print(f"\n👤 Novo membro entrou: {member.name}")
    
    # Dar cargo de visitante
    await dar_cargo_visitante(member)
    
    # Enviar mensagem de boas-vindas
    await enviar_mensagem_boas_vindas(member)

@bot.event
async def setup_hook():
    """Hook executado antes do bot iniciar"""
    await carregar_modulos()

# ==================== COMANDOS DE GERENCIAMENTO ====================
@bot.command(name="salvar_paineis")
@commands.has_permissions(administrator=True)
async def salvar_paineis_manual(ctx):
    """Salva manualmente os painéis ativos"""
    painel_manager.salvar_backup()
    await ctx.send("✅ Painéis salvos com sucesso!")

@bot.command(name="listar_paineis")
@commands.has_permissions(administrator=True)
async def listar_paineis(ctx):
    """Lista todos os painéis ativos no servidor"""
    guild_id = ctx.guild.id
    
    if guild_id not in painel_manager.paineis_ativos:
        await ctx.send("📭 Nenhum painel ativo encontrado neste servidor!")
        return
    
    paineis = painel_manager.paineis_ativos[guild_id]
    embed = discord.Embed(
        title="📋 Painéis Ativos",
        description=f"Total: {len(paineis)} painéis",
        color=discord.Color.blue()
    )
    
    for i, painel in enumerate(paineis, 1):
        embed.add_field(
            name=f"Painel #{i}",
            value=f"Tipo: {painel['tipo']}\nCanal: <#{painel['canal_id']}>\nCriado: {painel['criado_em']}",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name="testar")
@commands.has_permissions(administrator=True)
async def testar_boas_vindas(ctx, membro: discord.Member = None):
    """Comando para testar as boas-vindas (apenas admins)"""
    if membro is None:
        membro = ctx.author
    
    await ctx.send(f"🔄 Testando sistema para {membro.mention}...")
    await dar_cargo_visitante(membro)
    await enviar_mensagem_boas_vindas(membro)
    await ctx.send("✅ Teste concluído!")

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
