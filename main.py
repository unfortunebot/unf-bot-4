import discord
from discord import app_commands
from discord.ext import commands
import requests
from flask import Flask
from threading import Thread
import os
import sys

# --- WEB SUNUCU (RENDER WEB SERVICE UYUMLU) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot 7/24 Aktif!", 200

@app.route('/health')
def health():
    return "OK", 200

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
# --------------------------------

# --- AYARLAR ---
FIVEM_IP = "185.137.98.64"
FIVEM_PORT = "30120"  
FIVEM_SERVER_API = "https://servers-frontend.fivem.net/api/servers/single/r6z8vx"

EKIP_ISMI = "UNFORTUNE"
SUNUCU_ISMI = "PGUN"

BOT_TOKEN = os.environ.get("DISCORD_TOKEN")
if not BOT_TOKEN or BOT_TOKEN == "BURAYA_TOKENI_YAPISTIR":
    BOT_TOKEN = "BURAYA_TOKENI_YAPISTIR"
# ---------------

class MyBot(commands.Bot):
    def __init__(self):
        bot_intents = discord.Intents.default()
        bot_intents.message_content = True
        super().__init__(command_prefix="!", intents=bot_intents)
        
    async def setup_hook(self):
        await self.tree.sync()

bot = MyBot()

def get_fivem_players():
    try:
        url = f"http://{FIVEM_IP}:{FIVEM_PORT}/players.json"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"IP üzerinden players.json çekilemedi: {e}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        response = requests.get(FIVEM_SERVER_API, headers=headers, timeout=4)
        if response.status_code == 200:
            data = response.json()
            return data.get("Data", {}).get("players", [])
    except Exception as e:
        print(f"Yedek FiveM API bağlantısı başarısız oldu: {e}")
        
    return None

def get_dynamic_identifiers():
    try:
        url = f"http://{FIVEM_IP}:{FIVEM_PORT}/dynamic.json"
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return response.json().get("clients", [])
    except Exception as e:
        print(f"dynamic.json çekilemedi: {e}")
    return []

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
    print(f'🟢 Bot Render üzerinde ve Discord\'da başarıyla aktif oldu: {bot.user}')

@bot.tree.command(name="aktif-ekipler", description="PGUN sunucusunda aktif olan ekipleri listeler.")
async def aktif_ekipler(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        players = get_fivem_players()
        if players is None:
            await interaction.followup.send("❌ Sunucu verilerine ulaşılamadı. Lütfen sunucu durumunu kontrol edin.")
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
        embed.set_footer(text=f"Toplam {count-1} ekip tespit edildi")
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="◀ Önceki", disabled=True, style=discord.ButtonStyle.gray))
        view.add_item(discord.ui.Button(label="Sonraki ▶", disabled=True, style=discord.ButtonStyle.gray))
        
        await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
        print(f"aktif-ekipler hatası: {e}")
        await interaction.followup.send("❌ Komut işlenirken bir hata oluştu.")

@bot.tree.command(name="ekipid", description="İsmini girdiğiniz ekibin aktif oyuncularını ve ID'lerini listeler.")
@app_commands.describe(ekip_ismi="Sorgulamak istediğiniz ekibin adını girin")
async def ekip_id(interaction: discord.Interaction, ekip_ismi: str):
    await interaction.response.defer()
    try:
        players = get_fivem_players()
        if players is None:
            await interaction.followup.send("❌ Sunucu verileri çekilemedi.")
            return
            
        ekip_players = []
        for player in players:
            if ekip_ismi.lower() in player.get("name", "").lower():
                ekip_players.append(player)
                
        if not ekip_players:
            await interaction.followup.send(f"❌ `{ekip_ismi}` ekibine ait aktif oyuncu bulunamadı.")
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
                    value=f"{p_id}"
                ))

        embed.description += "\n\n" + player_list_text
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Giriş Yap ↗", url=f"https://cfx.re/join/{FIVEM_IP}:{FIVEM_PORT}", style=discord.ButtonStyle.link))
        
        if select_options:
            select_menu = discord.ui.Select(placeholder="DETAYLI SORGU İÇİN OYUNCU SEÇİNİZ", options=select_options)
            async def select_callback(inter: discord.Interaction):
                await inter.response.send_message(f"🔍 Seçilen Oyuncunun Sunucu ID'si: `{select_menu.values[0]}`", ephemeral=True)
            select_menu.callback = select_callback
            view.add_item(select_menu)
            
        await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
        print(f"ekipid hatası: {e}")
        await interaction.followup.send("❌ Komut işlenirken bir hata oluştu.")


# --- TAKILMA PROBLEMİ FIXLENMİŞ ID SORGU SİSTEMİ ---
@bot.tree.command(name="idsorgu", description="Sunucudaki bir oyuncuyu detaylı sorgular.")
@app_commands.describe(
    sorgu_turu="Sorgu türünü seçin (id, steam, discord)",
    deger="Aranacak değeri girin (Örn ID için: 748, Steam için: hex adresi)"
)
@app_commands.choices(sorgu_turu=[
    app_commands.Choice(name="id", value="id"),
    app_commands.Choice(name="steam", value="steam"),
    app_commands.Choice(name="discord", value="discord")
])
async def id_sorgu(interaction: discord.Interaction, sorgu_turu: str, deger: str):
    await interaction.response.defer()
    
    try:
        players = get_fivem_players()
        if players is None:
            await interaction.followup.send("❌ Sunucu verilerine şu anda erişilemiyor. Lütfen az sonra tekrar deneyin.")
            return

        target_player = None
        deger_clean = deger.strip().lower()
        dynamic_clients = get_dynamic_identifiers()

        for p in players:
            p_id_str = str(p.get("id"))
            p_identifiers = p.get("identifiers", [])
            if not p_identifiers:
                for dc in dynamic_clients:
                    if str(dc.get("id")) == p_id_str:
                        p_identifiers = dc.get("identifiers", [])
                        p["identifiers"] = p_identifiers
                        break

            if sorgu_turu == "id":
                if p_id_str == deger_clean:
                    target_player = p
                    break
            elif sorgu_turu == "steam":
                for ident in p_identifiers:
                    if ident.startswith("steam:") and deger_clean in ident.lower():
                        target_player = p
                        break
                if target_player: break
            elif sorgu_turu == "discord":
                for ident in p_identifiers:
                    if ident.startswith("discord:") and deger_clean in ident.lower():
                        target_player = p
                        break
                if target_player: break

        if not target_player:
            for dc in dynamic_clients:
                p_identifiers = dc.get("identifiers", [])
                dc_id_str = str(dc.get("id"))
                
                if sorgu_turu == "id" and dc_id_str == deger_clean:
                    target_player = dc
                    break
                elif sorgu_turu == "steam":
                    for ident in p_identifiers:
                        if ident.startswith("steam:") and deger_clean in ident.lower():
                            target_player = dc
                            break
                    if target_player: break
                elif sorgu_turu == "discord":
                    for ident in p_identifiers:
                        if ident.startswith("discord:") and deger_clean in ident.lower():
                            target_player = dc
                            break
                    if target_player: break

        if not target_player:
            await interaction.followup.send(f"❌ Belirtilen kriterlere uygun (`{sorgu_turu}: {deger}`) aktif bir oyuncu sunucuda bulunamadı.")
            return

        p_id = target_player.get("id", "Bilinmiyor")
        p_name = target_player.get("name", "Bilinmiyor")
        p_ping = target_player.get("ping", "0")
        
        steam_hex = "Bulunamadı"
        license_id = "Bulunamadı"
        discord_id = "Bulunamadı"
        discord_mention = "Bulunamadı"

        for ident in target_player.get("identifiers", []):
            if ident.startswith("steam:"):
                steam_hex = ident.replace("steam:", "")
            elif ident.startswith("license:"):
                license_id = ident.replace("license:", "")
                if len(license_id) > 15:
                    license_id = f"{license_id[:15]}..."
            elif ident.startswith("discord:"):
                discord_id = ident.replace("discord:", "")
                discord_mention = f"<@{discord_id}>"

        embed = discord.Embed(
            title=f"» Oyuncu Profilili / {SUNUCU_ISMI} PVP",
            color=discord.Color.from_rgb(140, 71, 243)
        )
        
        info_text = (
            f"```md\n"
            f"ID         : {p_id}\n"
            f"İsim       : {p_name}\n"
            f"Ping       : {p_ping} ms\n"
            f"Steam Hex  : {steam_hex}\n"
            f"Lisans     : {license_id}\n"
            f"Discord ID : {discord_id}\n"
            f"```"
        )
        embed.description = info_text
        
        embed.add_field(name="🔗 Discord Hesabı:", value=discord_mention, inline=False)
        embed.add_field(name="Oyuncunun Yanına Git", value="Sunucuya hızlı bağlanmak için butonu kullanabilirsin.", inline=False)
        
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Sunucuya Bağlan ↗", 
            url=f"https://cfx.re/join/{FIVEM_IP}:{FIVEM_PORT}", 
            style=discord.ButtonStyle.link
        ))
        
        embed.set_thumbnail(url="https://images.gamebanana.com/img/ico/sprays/5cfa320092289.png") 

        await interaction.followup.send(embed=embed, view=view)
    except Exception as e:
        print(f"idsorgu komutunda kritik hata oluştu: {e}")
        await interaction.followup.send("❌ Sorgu yapılırken beklenmeyen bir hata oluştu veya sunucu API'si zaman aşımına uğradı.")


# --- RENDER WEB SERVICE BAŞLATICI SİSTEMİ ---
def run_bot():
    try:
        bot.run(BOT_TOKEN)
    except Exception as e:
        print(f"Bot Başlatma Hatası: {e}")
        sys.exit(1)

if __name__ == "__main__":
    bot_thread = Thread(target=run_bot)
    bot_thread.daemon = True
    bot_thread.start()
    
    run_web()