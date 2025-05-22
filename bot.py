import os
import discord
from discord.ext import tasks, commands
from discord import app_commands
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, select

# Configurações de ambiente
TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("URL_DO_BANCO_DE_DADOS")

# Configurações do Discord
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = 1373298275700047963
EMBED_CHANNEL = 1373300281730924624
ADMIN_CHANNEL = 1374559903414227155
RANKING_CHANNEL = 1374656368979480617

# Configuração do banco de dados com SQLAlchemy Async
Base = declarative_base()

class Coleta(Base):
    __tablename__ = "coletas"
    usuario_id = Column(String, primary_key=True)
    nome = Column(String)
    caixas = Column(Integer)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# Função para salvar/atualizar coleta no banco
async def salvar_coleta(uid, nome, caixas):
    async with async_session() as session:
        coleta = await session.get(Coleta, uid)
        if coleta:
            coleta.caixas += caixas
        else:
            coleta = Coleta(usuario_id=uid, nome=nome, caixas=caixas)
            session.add(coleta)
        await session.commit()

# Modal para registrar coleta
class ColetaModal(discord.ui.Modal, title="Registrar Coleta"):
    nome = discord.ui.TextInput(label="Nome", required=True)
    usuario_id = discord.ui.TextInput(label="ID", required=True)
    caixas = discord.ui.TextInput(label="Quantidade de Caixas", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.usuario_id.value
        nome = self.nome.value
        caixas = int(self.caixas.value)

        await salvar_coleta(uid, nome, caixas)

        admin_channel = bot.get_channel(ADMIN_CHANNEL)
        if admin_channel:
            await admin_channel.send(
                f"Nova coleta registrada:\n**Nome:** {nome}\n**ID:** {uid}\n**Caixas:** {caixas}"
            )

        await interaction.response.send_message("Coleta registrada com sucesso!", ephemeral=True)

# View com botão para registrar coleta
class ColetaView(discord.ui.View):
    @discord.ui.button(label="REGISTRAR COLETA", style=discord.ButtonStyle.success)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ColetaModal())

# Comando para enviar embed com botão
@bot.tree.command(name="enviar_embed", description="Envia embed de coleta", guild=discord.Object(id=GUILD_ID))
async def enviar_embed(interaction: discord.Interaction):
    embed = discord.Embed(
        title="**REGISTRO DE COLETAS**",
        description="Clique no botão abaixo para registrar sua coleta!",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/684/684908.png")
    embed.set_footer(text="Sistema automatizado de registro")

    channel = bot.get_channel(EMBED_CHANNEL)
    if channel:
        await channel.send(embed=embed, view=ColetaView())
        await interaction.response.send_message("Embed enviada!", ephemeral=True)
    else:
        await interaction.response.send_message("Canal não encontrado.", ephemeral=True)

# Tarefa para atualizar ranking a cada 5 minutos
@tasks.loop(minutes=5)
async def ranking_updater():
    async with async_session() as session:
        result = await session.execute(
            select(Coleta).order_by(Coleta.caixas.desc()).limit(10)
        )
        ranking = result.scalars().all()

    lines = []
    for i, coleta in enumerate(ranking, start=1):
        lines.append(f"**{i}. {coleta.nome}** (ID: {coleta.usuario_id}) — {coleta.caixas} caixas")

    embed = discord.Embed(
        title="**🏆 RANKING DE COLETA 🏆**",
        description="\n".join(lines) if lines else "Nenhum dado registrado ainda.",
        color=discord.Color.blue()
    )

    channel = bot.get_channel(RANKING_CHANNEL)
    if channel:
        async for msg in channel.history(limit=1):
            await msg.edit(embed=embed)
            break
        else:
            await channel.send(embed=embed)

@bot.event
async def on_ready():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"Bot online como {bot.user}")
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    ranking_updater.start()

bot.run(TOKEN)
