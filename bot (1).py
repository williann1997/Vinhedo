
import discord
from discord.ext import tasks, commands
from discord import app_commands
import json
import os

TOKEN = os.getenv("DISCORD_TOKEN")
assert TOKEN, "Erro: DISCORD_TOKEN não está configurado."

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = 1373298275700047963
EMBED_CHANNEL = 1373300281730924624
ADMIN_CHANNEL = 1374559903414227155
RANKING_CHANNEL = 1374656368979480617

DATA_FILE = "ranking.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

class ColetaModal(discord.ui.Modal, title="Registrar Coleta"):
    nome = discord.ui.TextInput(label="Nome", required=True)
    usuario_id = discord.ui.TextInput(label="ID", required=True)
    caixas = discord.ui.TextInput(label="Quantidade de Caixas", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        data = load_data()
        uid = self.usuario_id.value
        nome = self.nome.value
        try:
            caixas = int(self.caixas.value)
            if caixas <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "Por favor, insira um número válido e positivo para a quantidade de caixas.",
                ephemeral=True
            )
            return

        if uid in data:
            data[uid]["caixas"] += caixas
        else:
            data[uid] = {"nome": nome, "caixas": caixas}

        save_data(data)

        admin_channel = bot.get_channel(ADMIN_CHANNEL)
        if admin_channel:
            await admin_channel.send(
                f"Nova coleta registrada:\n**Nome:** {nome}\n**ID:** {uid}\n**Caixas:** {caixas}"
            )
        else:
            print(f"Canal admin com ID {ADMIN_CHANNEL} não encontrado.")

        await interaction.response.send_message("Coleta registrada com sucesso!", ephemeral=True)

class ColetaView(discord.ui.View):
    @discord.ui.button(label="REGISTRAR COLETA", style=discord.ButtonStyle.success)
    async def registrar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ColetaModal())

@bot.event
async def on_ready():
    print(f"Bot online como {bot.user}")
    synced = await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Comandos sincronizados: {len(synced)}")
    ranking_updater.start()

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
        print(f"Canal com ID {EMBED_CHANNEL} não encontrado.")
        await interaction.response.send_message("Canal não encontrado.", ephemeral=True)

@tasks.loop(minutes=5)
async def ranking_updater():
    data = load_data()
    ranking = sorted(data.items(), key=lambda x: x[1]["caixas"], reverse=True)

    lines = []
    for i, (uid, info) in enumerate(ranking[:10], start=1):
        lines.append(f"**{i}. {info['nome']}** (ID: {uid}) — {info['caixas']} caixas")

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
    else:
        print(f"Canal ranking com ID {RANKING_CHANNEL} não encontrado.")

bot.run(TOKEN)
