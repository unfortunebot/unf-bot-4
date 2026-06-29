import discord
from discord import app_commands
from discord.ext import commands
import requests

# --- AYARLAR ---
BOT_TOKEN = "BURAYA_DISCORD_BOT_TOKENINI_YAZ"
FIVEM_SERVER_API = "https://servers-frontend.fivem.net/api/servers/single/r6z8vx" 
EKIP_ISMI = "UNFORTUNE"
SUNUCU_ISMI = "PGUN"
# ---------------

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())
        
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

def get_fivem_players():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(FIVEM_SERVER_API, headers=headers, timeout=7)
        if response.status_code == 200:
            data = response.json()
            players = data.get("Data", {}).get("players", [])
            return players
    except Exception as e:
        print(f"FiveM API Hatası: {e}")
    return None

def detect_teams(players):
    teams = {}
    sivil_count = 0
    separators = [" ", " | ", " x ", " X ", "-", "・", "]", "["]
    
    for player in players:
        name = player.get("name", "").strip()
        if not name:
            continue
            
        found_team = None
        for sep in separators:
            if sep in name:
                parts = name.split(sep)
                possible_tag = parts[0].replace("[", "").replace("]", "").strip()
                if 2 < len(possible_tag) < 12 and not possible_tag.isdigit():
                    found_team = possible_tag
                    break
                    
        if found_team:
            team_key = found_team.upper() 
            if team_key not in teams:
                teams[team_key] = []
            teams[team_key].append(player)
        else:
            sivil_count += 1
            
    return teams, sivil_count

@bot.event
async def on_ready():
    print(f'🟢 Bot başarıyla aktif oldu: {bot.user}')

@bot.tree.command(name="aktif-ekipler", description="PGUN sunucusunda aktif olan ekipleri ve üye sayılarını listeler.")
async def aktif_ekipler(interaction: discord.Interaction):
    await interaction.response.defer()
    
    players = get_fivem_players()
    if players is None:
        await interaction.followup.send("❌ Sunucu verilerine şu an ulaşılamıyor. FiveM API yoğun olabilir, lütfen az sonra tekrar deneyin.")
        return

    teams, sivil_count = detect_teams(players)
    sorted_teams = sorted(teams.items(), key=lambda x: len(x[1]), reverse=True)
    
    embed = discord.Embed(
        title="» Aktif Ekipler", 
        description=f"**{SUNUCU_ISMI} PVP** • Toplam `{len(players)}` oyuncu aktif.", 
        color=discord.Color.from_rgb(47, 49, 54)
    )
    
    description_text = f"1.  **sivil** — *{sivil_count} kişi*\n"
    
    count = 2
    for team_name, team_players in sorted_teams:
        if len(team_players) >= 2: 
            description_text += f"{count}.  **{team_name.lower()}** — *{len(team_players)} kişi*\n"
            count += 1
            
    embed.description += "\n\n" + description_text
    embed.set_footer(text=f"Sayfa 1/1 • Toplam {count-1} ekip tespit edildi")
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="◀ Önceki", disabled=True, style=discord.ButtonStyle.gray))
    view.add_item(discord.ui.Button(label="Sonraki ▶", disabled=True, style=discord.ButtonStyle.gray))
    
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="ekipid", description="İsmini girdiğiniz ekibin aktif oyuncularını ve oyun içi ID'lerini listeler.")
@app_commands.describe(ekip_ismi="Sorgulamak istediğiniz ekibin adını girin (Örn: unfortune veya mdpvp)")
async def ekip_id(interaction: discord.Interaction, ekip_ismi: str):
    await interaction.response.defer()
    
    players = get_fivem_players()
    if players is None:
        await interaction.followup.send("❌ Sunucu verileri çekilemedi.")
        return
        
    ekip_players = []
    for player in players:
        if ekip_ismi.lower() in player.get("name", "").lower():
            ekip_players.append(player)
            
    if not ekip_players:
        await interaction.followup.send(f"❌ `{ekip_ismi}` ekibine ait şu anda oyunda aktif kimse bulunamadı.")
        return
        
    embed = discord.Embed(
        title=f"» Arama Sonucu / {ekip_ismi.lower()}",
        description=f"**{SUNUCU_ISMI} PVP**",
        color=discord.Color.blue()
    )
    
    player_list_text = ""
    select_options = []
    
    for idx, p in enumerate(ekip_players, start=1):
        p_name = p.get("name")
        p_id = p.get("id")
        player_list_text += f"{idx}.  **{p_name}** *(ID: {p_id})*\n"
        
        if idx <= 25:
            select_options.append(discord.SelectOption(
                label=f"{p_name[:25]}", 
                value=f"{p_id}", 
                description=f"ID: {p_id} detaylarını gör"
            ))

    embed.description += "\n\n" + player_list_text
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Giriş Yap ↗", url="https://cfx.re/join/r6z8vx", style=discord.ButtonStyle.link))
    
    if select_options:
        select_menu = discord.ui.Select(placeholder="DETAYLI SORGU İÇİN OYUNCU SEÇİNİZ (İLK 25)", options=select_options)
        
        async def select_callback(inter: discord.Interaction):
            selected_id = select_menu.values[0]
            await inter.response.send_message(f"🔍 Seçilen Oyuncunun Sunucu ID'si: `{selected_id}`", ephemeral=True)
            
        select_menu.callback = select_callback
        view.add_item(select_menu)
        
    await interaction.followup.send(embed=embed, view=view)

bot.run(BOT_TOKEN)