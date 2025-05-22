import os
import discord
from discord.ext import tasks, commands
from discord import app_commands
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, select
from fastapi import FastAPI
import uvicorn
import asyncio

# --------------------
# Configurações
# --------------------

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("URL_DO_BANCO_DE_DADOS")
GUILD_ID = int(os.getenv("GUILD_ID", "1373298275700047963"))
EMBED_CHANNEL = int(os.getenv("EMBED_CHANNEL", "1373300281730924624"))
ADMIN_CHANNEL = int(os.getenv("ADMIN_CHANNEL", "1374559903414227155"))
RANKING_CHANNEL = int(os.getenv("RANKING_CHANNEL", "1374656368979480617"))
CARGO_REQUEST_CHANNEL = int(os.getenv("CARGO_REQUEST_CHANNEL", "1373308437684813865"))
VENDA_CHANNEL = int(os.getenv("VENDA_CHANNEL", "1373305755465158677"))
VENDA_ADMIN_CHANNEL = int(os.getenv("VENDA_ADMIN_CHANNEL", "1374613709770723440"))
WILLIAN_USER_ID = int(os.getenv("WILLIAN_USER_ID", "0"))  # substitua se quiser

# --------------------
# Discord Bot Setup
# --------------------

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
Base = declarative_base()

# --------------------
# DB Models
# --------------------

class Coleta(Base):
    __tablename__ = "coletas"
    usuario_id = Column(String, primary_key=True)
    nome = Column(String)
    caixas = Column(Integer)

class Venda(Base):
    __tablename__ = "vendas"
    usuario_id = Column(String, primary_key=True)
    nome = Column(String)
    descricao = Column(String)
    entregue = Column(String)
    valor = Column(Integer)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# --------------------
# Funções DB
# --------------------

async def salvar_coleta(uid, nome, caixas):
    async with async_session() as session:
        coleta = await session.get(Coleta, uid)
        if coleta:
            coleta.caixas += caixas
        else:
            coleta = Coleta(usuario_id=uid, nome=nome, caixas=caixas)
            session.add(coleta)
        await session.commit()

async def salvar_venda(uid, nome, descricao, entregue, valor):
    async with async_session() as session:
        venda = await session.get(Venda, uid)
        if venda:
            venda.descricao = descricao
            venda.entregue = entregue
            venda.valor = valor
        else:
            venda = Venda(usuario_id=uid, nome=nome, descricao=descricao, entregue=entregue, valor=valor)
            session.add(venda)
        await session.commit()

# --------------------
# Modals e Views
# --------------------

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

class VendaModal(discord.ui.Modal, title="Registrar Venda de Munição"):
    nome = discord.ui.TextInput(label="Nome", required=True)
    usuario_id = discord.ui.TextInput(label="ID", required=True)
    descricao = discord.ui.TextInput(label="Descrição da Venda", required=True, style=discord.TextStyle.paragraph)
    entregue = discord.ui.TextInput(label="Venda entregue? (Sim/Não)", required=True)
    valor = discord.ui.TextInput(label="Valor total da venda (número)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.usuario_id.value
        nome = self.nome.value
        descricao = self.descricao.value
        entregue = self.entregue.value.strip().capitalize()
        valor = int(self.valor.value)
        await salvar_venda(uid, nome, descricao, entregue, valor)

        admin_channel = bot.get_channel(VENDA_ADMIN_CHANNEL)
        if admin_channel:
            await admin_channel.send(
                f"Nova venda registrada:\n**Nome:** {nome}\n**ID:** {uid}\n**Descrição:** {descricao}\n**Entregue:** {entregue}\n**Valor:** {valor}"
            )
        await interaction.response.send_message("Venda registrada com sucesso!", ephemeral=True)

class ColetaView(discord.ui.View):
    @discord.ui.button(label="REGISTRAR COLETA", style=discord.ButtonStyle.success)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ColetaModal())

class VendaView(discord.ui.View):
    @discord.ui.button(label="REGISTRAR VENDA", style=discord.ButtonStyle.primary)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VendaModal())

# --------------------
# Comandos Slash
# --------------------

@bot.tree.command(name="enviar_embed_coleta", description="Envia embed de coleta", guild=discord.Object(id=GUILD_ID))
async def enviar_embed_coleta(interaction: discord.Interaction):
    embed = discord.Embed(
        title="**REGISTRO DE COLETAS**",
        description="Clique no botão abaixo para registrar sua coleta!",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/684/684908.png")
    embed.set_footer(text="Sistema automatizado de registro")

    channel = bot.get_channel(EMBED_CHANNEL)
    if channel:
        await channel.send(embed=embed, view=ColetaView())
        await interaction.response.send_message("Embed de coleta enviada!", ephemeral=True)
    else:
        await interaction.response.send_message("Canal não encontrado.", ephemeral=True)

@bot.tree.command(name="enviar_embed_venda", description="Envia embed de venda", guild=discord.Object(id=GUILD_ID))
async def enviar_embed_venda(interaction: discord.Interaction):
    embed = discord.Embed(
    title="**REGISTRO DE VENDAS DE MUNIÇÃO**",
    description="Clique no botão abaixo para registrar sua venda!",
    color=discord.Color.red()
)
embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/684/684908.png")
embed.set_footer(text="Sistema automatizado de registro")
import os
import discord
from discord.ext import tasks, commands
from discord import app_commands
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, select
from fastapi import FastAPI
import uvicorn
import asyncio

# --------------------
# Configurações
# --------------------

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("URL_DO_BANCO_DE_DADOS")
GUILD_ID = int(os.getenv("GUILD_ID", "1373298275700047963"))
EMBED_CHANNEL = int(os.getenv("EMBED_CHANNEL", "1373300281730924624"))
ADMIN_CHANNEL = int(os.getenv("ADMIN_CHANNEL", "1374559903414227155"))
RANKING_CHANNEL = int(os.getenv("RANKING_CHANNEL", "1374656368979480617"))
CARGO_REQUEST_CHANNEL = int(os.getenv("CARGO_REQUEST_CHANNEL", "1373308437684813865"))
VENDA_CHANNEL = int(os.getenv("VENDA_CHANNEL", "1373305755465158677"))
VENDA_ADMIN_CHANNEL = int(os.getenv("VENDA_ADMIN_CHANNEL", "1374613709770723440"))
WILLIAN_USER_ID = int(os.getenv("WILLIAN_USER_ID", "0"))  # substitua se quiser

# --------------------
# Discord Bot Setup
# --------------------

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
Base = declarative_base()

# --------------------
# DB Models
# --------------------

class Coleta(Base):
    __tablename__ = "coletas"
    usuario_id = Column(String, primary_key=True)
    nome = Column(String)
    caixas = Column(Integer)

class Venda(Base):
    __tablename__ = "vendas"
    usuario_id = Column(String, primary_key=True)
    nome = Column(String)
    descricao = Column(String)
    entregue = Column(String)
    valor = Column(Integer)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# --------------------
# Funções DB
# --------------------

async def salvar_coleta(uid, nome, caixas):
    async with async_session() as session:
        coleta = await session.get(Coleta, uid)
        if coleta:
            coleta.caixas += caixas
        else:
            coleta = Coleta(usuario_id=uid, nome=nome, caixas=caixas)
            session.add(coleta)
        await session.commit()

async def salvar_venda(uid, nome, descricao, entregue, valor):
    async with async_session() as session:
        venda = await session.get(Venda, uid)
        if venda:
            venda.descricao = descricao
            venda.entregue = entregue
            venda.valor = valor
        else:
            venda = Venda(usuario_id=uid, nome=nome, descricao=descricao, entregue=entregue, valor=valor)
            session.add(venda)
        await session.commit()

# --------------------
# Modals e Views
# --------------------

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

class VendaModal(discord.ui.Modal, title="Registrar Venda de Munição"):
    nome = discord.ui.TextInput(label="Nome", required=True)
    usuario_id = discord.ui.TextInput(label="ID", required=True)
    descricao = discord.ui.TextInput(label="Descrição da Venda", required=True, style=discord.TextStyle.paragraph)
    entregue = discord.ui.TextInput(label="Venda entregue? (Sim/Não)", required=True)
    valor = discord.ui.TextInput(label="Valor total da venda (número)", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        uid = self.usuario_id.value
        nome = self.nome.value
        descricao = self.descricao.value
        entregue = self.entregue.value.strip().capitalize()
        valor = int(self.valor.value)
        await salvar_venda(uid, nome, descricao, entregue, valor)

        admin_channel = bot.get_channel(VENDA_ADMIN_CHANNEL)
        if admin_channel:
            await admin_channel.send(
                f"Nova venda registrada:\n**Nome:** {nome}\n**ID:** {uid}\n**Descrição:** {descricao}\n**Entregue:** {entregue}\n**Valor:** {valor}"
            )
        await interaction.response.send_message("Venda registrada com sucesso!", ephemeral=True)

class ColetaView(discord.ui.View):
    @discord.ui.button(label="REGISTRAR COLETA", style=discord.ButtonStyle.success)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ColetaModal())

class VendaView(discord.ui.View):
    @discord.ui.button(label="REGISTRAR VENDA", style=discord.ButtonStyle.primary)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VendaModal())

# --------------------
# Comandos Slash
# --------------------

@bot.tree.command(name="enviar_embed_coleta", description="Envia embed de coleta", guild=discord.Object(id=GUILD_ID))
async def enviar_embed_coleta(interaction: discord.Interaction):
    embed = discord.Embed(
        title="**REGISTRO DE COLETAS**",
        description="Clique no botão abaixo para registrar sua coleta!",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/684/684908.png")
    embed.set_footer(text="Sistema automatizado de registro")

    channel = bot.get_channel(EMBED_CHANNEL)
    if channel:
        await channel.send(embed=embed, view=ColetaView())
        await interaction.response.send_message("Embed de coleta enviada!", ephemeral=True)
    else:
        await interaction.response.send_message("Canal não encontrado.", ephemeral=True)

@bot.tree.command(name="enviar_embed_venda", description="Envia embed de venda", guild=discord.Object(id=GUILD_ID))
async def enviar_embed_venda(interaction: discord.Interaction):
    embed = discord.Embed(
        title="**REGISTRO DE VENDAS DE MUNIÇÃO**",
        description="Clique no botão abaixo para registrar sua venda!",
        color=discord.Color.red()
    )
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/684/684908.png")
    embed.set_footer(text="Sistema automatizado de registro")

    channel = bot.get_channel(VENDA_CHANNEL)
    if channel:
        await channel.send(embed=embed, view=VendaView())
        await interaction.response.send_message("Embed de venda enviada!", ephemeral=True)
    else:
        await interaction.response.send_message("Canal não encontrado.", ephemeral=True)

# --------------------
# Ranking updater
# --------------------

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
        color=discord.Color.red()
    )

    channel = bot.get_channel(RANKING_CHANNEL)
    if channel:
        async for msg in channel.history(limit=1):
            await msg.edit(embed=embed)
            break
        else:
            await channel.send(embed=embed)

# --------------------
# Eventos
# --------------------

@bot.event
async def on_ready():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"Bot online como {bot.user}")
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    ranking_updater.start()

# --------------------
# FastAPI Setup
# --------------------

app = FastAPI()

@app.get("/")
async def root():
    return {"status": "Bot rodando!"}

@app.get("/ping")
async def ping():
    return {"message": "pong"}

# --------------------
# Run bot e FastAPI juntos
# --------------------

async def start_bot():
    await bot.start(TOKEN)

async def main():
    porta = int(os.getenv("PORTA", 8000))

if __name__ == "__main__":
