import os
import discord
from discord.ext import commands
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String

# --------------------
# Configurações
# --------------------

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("URL_DO_BANCO_DE_DADOS")
ADMIN_CHANNEL = int(os.getenv("ADMIN_CHANNEL", "1374559903414227155"))
VENDA_ADMIN_CHANNEL = int(os.getenv("VENDA_ADMIN_CHANNEL", "1374613709770723440"))

# --------------------
# Setup Discord Bot
# --------------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

Base = declarative_base()

# --------------------
# Modelos de Banco de Dados
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
# Funções para salvar no DB
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
# Modals
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

# --------------------
# Comandos para abrir os modais
# --------------------

@bot.command(name="coleta")
async def cmd_coleta(ctx):
    await ctx.send_modal(ColetaModal())

@bot.command(name="venda")
async def cmd_venda(ctx):
    await ctx.send_modal(VendaModal())

# --------------------
# Evento de inicialização
# --------------------

@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}!")

# --------------------
# Rodar o bot
# --------------------

bot.run(TOKEN)
