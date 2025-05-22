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
