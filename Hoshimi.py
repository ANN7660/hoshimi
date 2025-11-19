#!/usr/bin/env python3
import os, json, threading, http.server, socketserver, asyncio, datetime, re, random, time
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select, Modal, TextInput
from collections import defaultdict

# === Keep Alive ===
def keep_alive():
    port = int(os.environ.get("PORT", 8080))
    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    with socketserver.TCPServer(("", port), QuietHandler) as httpd:
        print(f"[keep-alive] HTTP running on port {port}")
        httpd.serve_forever()
threading.Thread(target=keep_alive, daemon=True).start()

# === Data ===
DATA_FILE = "hoshimi_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "config": {}, 
        "tickets": {}, 
        "invites": {}, 
        "roles_invites": {}, 
        "temp_vocs": {}, 
        "user_invites": {}, 
        "allowed_links": {},
        "warnings": {},
        "economy": {},
        "giveaways": {},
        "reaction_roles": {},
        "auto_responses": {},
        "suggestions": {},
        "logs": {},
        "backups": {},
        "premium_users": {},
        "ai_settings": {},
        "custom_commands": {},
        "levels": {},
        "badges": {},
        "antispam": {},
        "antiraid": {},
        "automod": {}
    }

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

data = load_data()

def get_conf(gid, key, default=None):
    return data.get("config", {}).get(str(gid), {}).get(key, default)

def set_conf(gid, key, value):
    data.setdefault("config", {}).setdefault(str(gid), {})[key] = value
    save_data(data)

# === Bot Init ===
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="+", intents=intents, help_command=None)

# === Anti-Spam System ===
message_history = defaultdict(list)

@bot.event
async def on_ready():
    print(f"✨ Bot connecté: {bot.user} 🌸")
    await bot.change_presence(activity=discord.Game(name="✨ +help | Mode Kawaii 💖"))
    check_giveaways.start()
    auto_backup.start()
    
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            data["invites"][str(guild.id)] = {inv.code: inv.uses for inv in invites}
            save_data(data)
        except:
            pass

# === LOGGING SYSTEM ===
async def log_action(guild, action_type, **kwargs):
    log_channel_id = get_conf(guild.id, "logs_channel")
    if not log_channel_id:
        return
    
    log_channel = guild.get_channel(log_channel_id)
    if not log_channel:
        return
    
    colors = {
        "member_join": 0x00ff00,
        "member_leave": 0xff0000,
        "message_delete": 0xff6347,
        "message_edit": 0xffa500,
        "member_ban": 0xff0000,
        "member_unban": 0x00ff00,
        "member_kick": 0xff6347,
        "channel_create": 0x00ff00,
        "channel_delete": 0xff0000,
        "role_create": 0x00ff00,
        "role_delete": 0xff0000,
        "warning": 0xffa500,
        "mute": 0xff6347,
        "unmute": 0x00ff00
    }
    
    e = discord.Embed(
        title=f"📋 Log: {action_type.replace('_', ' ').title()}",
        color=colors.get(action_type, 0xff69b4),
        timestamp=datetime.datetime.utcnow()
    )
    
    for key, value in kwargs.items():
        e.add_field(name=key.replace('_', ' ').title(), value=str(value), inline=True)
    
    e.set_footer(text=f"✨ Logs du serveur 💖")
    
    try:
        await log_channel.send(embed=e)
        
        # Save to database
        gid = str(guild.id)
        data.setdefault("logs", {}).setdefault(gid, [])
        data["logs"][gid].append({
            "type": action_type,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "data": kwargs
        })
        save_data(data)
    except:
        pass

# === AUTO BACKUP ===
@tasks.loop(hours=24)
async def auto_backup():
    for guild in bot.guilds:
        gid = str(guild.id)
        if get_conf(guild.id, "auto_backup"):
            try:
                backup_data = {
                    "guild_name": guild.name,
                    "guild_id": guild.id,
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "channels": [{"name": c.name, "type": str(c.type), "position": c.position} for c in guild.channels],
                    "roles": [{"name": r.name, "color": r.color.value, "permissions": r.permissions.value} for r in guild.roles],
                    "config": data.get("config", {}).get(gid, {})
                }
                
                data.setdefault("backups", {}).setdefault(gid, [])
                data["backups"][gid].append(backup_data)
                
                # Keep only last 7 backups
                if len(data["backups"][gid]) > 7:
                    data["backups"][gid] = data["backups"][gid][-7:]
                
                save_data(data)
            except:
                pass

# === GIVEAWAY LOOP ===
@tasks.loop(seconds=30)
async def check_giveaways():
    now = datetime.datetime.utcnow()
    to_end = []
    
    for msg_id, gdata in data.get("giveaways", {}).items():
        end_time = datetime.datetime.fromisoformat(gdata["end_time"])
        if now >= end_time:
            to_end.append(msg_id)
    
    for msg_id in to_end:
        gdata = data["giveaways"][msg_id]
        guild = bot.get_guild(int(gdata["guild"]))
        if guild:
            channel = guild.get_channel(gdata["channel"])
            if channel:
                try:
                    msg = await channel.fetch_message(int(msg_id))
                    reaction = discord.utils.get(msg.reactions, emoji="🎉")
                    if reaction:
                        users = [user async for user in reaction.users() if not user.bot]
                        if users:
                            winner = random.choice(users)
                            e = discord.Embed(title="🎉 Giveaway Terminé ! 🎉", color=0xff69b4)
                            e.description = f"**🏆 Gagnant:** {winner.mention}\n**🎀 Prix:** {gdata['prize']}\n\n💖 Félicitations !"
                            await channel.send(embed=e)
                        else:
                            await channel.send("❌ Aucun participant au giveaway ! 💔")
                except:
                    pass
        
        del data["giveaways"][msg_id]
        save_data(data)

# === EVENTS ===
@bot.event
async def on_member_join(member):
    # Anti-raid check
    gid = str(member.guild.id)
    if get_conf(member.guild.id, "antiraid_enabled"):
        current_time = time.time()
        data.setdefault("antiraid", {}).setdefault(gid, {"joins": []})
        
        # Clean old joins
        data["antiraid"][gid]["joins"] = [j for j in data["antiraid"][gid]["joins"] if current_time - j < 60]
        data["antiraid"][gid]["joins"].append(current_time)
        
        # Check if raid (5+ joins in 60 seconds)
        if len(data["antiraid"][gid]["joins"]) >= 5:
            try:
                await member.kick(reason="🛡️ Protection anti-raid")
                await log_action(member.guild, "antiraid", member=member.mention, reason="Raid détecté")
                return
            except:
                pass
    
    # Auto-role
    auto_role_id = get_conf(member.guild.id, "auto_role")
    if auto_role_id:
        auto_role = member.guild.get_role(auto_role_id)
        if auto_role:
            try:
                await member.add_roles(auto_role)
            except:
                pass
    
    # Welcome embed
    wc = get_conf(member.guild.id, "welcome_embed_channel")
    if wc:
        ch = member.guild.get_channel(wc)
        if ch:
            e = discord.Embed(
                title=f"🌸 Bienvenue {member.display_name} ! 🌸",
                description=f"✨ Bienvenue {member.mention} ! Tu es le **{member.guild.member_count}ème** membre ! 💖\n\nAmuse-toi bien sur le serveur ! 🌸",
                color=0xff69b4
            )
            e.set_thumbnail(url=member.display_avatar.url)
            e.set_image(url="https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExc3o4NGljeWVlcXh2Y3FtajF4M2pndTEyeWh1ZXR3YXVhMG9tZjkydCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Xl0oVz3eb9mfu/giphy.gif")
            e.add_field(name="💫 Membre", value=member.mention, inline=True)
            e.add_field(name="🎉 Total", value=f"**{member.guild.member_count}** membres 💖", inline=True)
            e.set_footer(text=f"✨ {member.guild.name} 💖", icon_url=member.guild.icon.url if member.guild.icon else None)
            await ch.send(f"🎊 {member.mention} 🎊", embed=e)
    
    await log_action(member.guild, "member_join", membre=member.mention, id=member.id)

@bot.event
async def on_member_remove(member):
    lc = get_conf(member.guild.id, "leave_embed_channel")
    if lc:
        ch = member.guild.get_channel(lc)
        if ch:
            e = discord.Embed(
                title=f"👋 Au revoir {member.display_name}",
                description=f"🌸 {member.mention} a quitté le serveur... 💔\n\nOn espère te revoir bientôt ! ✨",
                color=0x9370db
            )
            e.set_thumbnail(url=member.display_avatar.url)
            e.add_field(name="👋 Membre", value=member.mention, inline=True)
            e.add_field(name="😢 Membres restants", value=f"**{member.guild.member_count}** 💔", inline=True)
            e.set_footer(text=f"✨ Au revoir", icon_url=member.guild.icon.url if member.guild.icon else None)
            await ch.send(embed=e)
    
    await log_action(member.guild, "member_leave", membre=member.display_name, id=member.id)

@bot.event
async def on_message_delete(message):
    if message.author.bot or not message.guild:
        return
    
    await log_action(
        message.guild, 
        "message_delete",
        auteur=message.author.mention,
        salon=message.channel.mention,
        contenu=message.content[:100] if message.content else "Aucun contenu"
    )

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or not before.guild or before.content == after.content:
        return
    
    await log_action(
        before.guild,
        "message_edit",
        auteur=before.author.mention,
        salon=before.channel.mention,
        avant=before.content[:100],
        après=after.content[:100]
    )

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return
    
    gid = str(message.guild.id)
    uid = str(message.author.id)
    
    # Anti-spam
    if get_conf(message.guild.id, "antispam_enabled"):
        current_time = time.time()
        message_history[message.author.id].append(current_time)
        message_history[message.author.id] = [t for t in message_history[message.author.id] if current_time - t < 5]
        
        if len(message_history[message.author.id]) > 5:
            try:
                await message.delete()
                await message.channel.send(f"🛡️ {message.author.mention}, arrête de spam ! 💔", delete_after=5)
                return
            except:
                pass
    
    # AutoMod - Bad words
    if get_conf(message.guild.id, "automod_enabled"):
        bad_words = get_conf(message.guild.id, "bad_words", [])
        for word in bad_words:
            if word.lower() in message.content.lower():
                try:
                    await message.delete()
                    await message.channel.send(f"🚫 {message.author.mention}, langage inapproprié ! 💔", delete_after=5)
                    await log_action(message.guild, "automod", membre=message.author.mention, raison="Mot interdit détecté")
                    return
                except:
                    pass
    
    # Link filter
    allowed_channels = data.get("allowed_links", {}).get(gid, [])
    if message.channel.id not in allowed_channels:
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        if re.search(url_pattern, message.content):
            await message.delete()
            await message.channel.send(f"❌ {message.author.mention}, les liens sont interdits ici !", delete_after=5)
            return
    
    # Level system
    if get_conf(message.guild.id, "level_system_enabled"):
        data.setdefault("levels", {}).setdefault(gid, {})
        data["levels"][gid].setdefault(uid, {"xp": 0, "level": 1, "messages": 0})
        
        xp_gain = random.randint(10, 25)
        data["levels"][gid][uid]["xp"] += xp_gain
        data["levels"][gid][uid]["messages"] += 1
        
        current_level = data["levels"][gid][uid]["level"]
        xp_needed = current_level * 100
        
        if data["levels"][gid][uid]["xp"] >= xp_needed:
            data["levels"][gid][uid]["level"] += 1
            data["levels"][gid][uid]["xp"] = 0
            
            lvl_channel_id = get_conf(message.guild.id, "level_channel")
            if lvl_channel_id:
                lvl_channel = message.guild.get_channel(lvl_channel_id)
                if lvl_channel:
                    e = discord.Embed(
                        title="🎉 Level Up ! 🎉",
                        description=f"🌸 {message.author.mention} est maintenant **niveau {data['levels'][gid][uid]['level']}** ! 💖",
                        color=0xff69b4
                    )
                    await lvl_channel.send(embed=e)
        
        save_data(data)
    
    # Custom commands
    custom_cmds = data.get("custom_commands", {}).get(gid, {})
    for trigger, response in custom_cmds.items():
        if message.content.lower() == trigger.lower():
            await message.channel.send(response)
            return
    
    # Auto responses
    auto_resp = data.get("auto_responses", {}).get(gid, {})
    for trigger, response in auto_resp.items():
        if trigger.lower() in message.content.lower():
            await message.channel.send(f"{response}")
            break
    
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    gid = str(member.guild.id)
    trigger_channel_id = get_conf(member.guild.id, "voc_trigger_channel")
    
    if after.channel and after.channel.id == trigger_channel_id:
        category = after.channel.category
        new_channel = await member.guild.create_voice_channel(
            name=f"🌸 Vocal de {member.display_name}",
            category=category
        )
        await member.move_to(new_channel)
        
        data.setdefault("temp_vocs", {})[str(new_channel.id)] = {
            "owner": str(member.id),
            "guild": gid
        }
        save_data(data)
    
    if before.channel and str(before.channel.id) in data.get("temp_vocs", {}):
        if len(before.channel.members) == 0:
            await before.channel.delete()
            del data["temp_vocs"][str(before.channel.id)]
            save_data(data)


# === CONFIG PANEL (INTERACTIF COMPLET) ===
from discord.ui import View, Button, Select

class _ChannelButton(Button):
    def __init__(self, label, style, key):
        super().__init__(label=label, style=style)
        self.key = key

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"🔎 Veuillez mentionner le salon pour configurer **{self.label}**\nEx : `#general`", ephemeral=True)

class ChannelSelect(Select):
    def __init__(self, placeholder, channels, target_key):
        options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in channels]
        if not options:
            options = [discord.SelectOption(label="Aucun salon disponible", value="0", description="Créez des salons d'abord")]
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)
        self.target_key = target_key

    async def callback(self, interaction: discord.Interaction):
        chosen_id = self.values[0]
        if chosen_id == "0":
            await interaction.response.send_message("❌ Aucun salon sélectionnable.", ephemeral=True)
            return
        guild = interaction.guild
        try:
            cid = int(chosen_id)
            set_conf(guild.id, self.target_key, cid)
            save_data(data)
            await interaction.response.send_message(f"✅ Salon configuré pour **{self.target_key}** : <#{cid}>", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur lors de la configuration : {e}", ephemeral=True)

class MainConfigView(View):
    def __init__(self, guild):
        super().__init__(timeout=600)
        self.guild = guild

        # Top-level buttons
        self.add_item(Button(label="🎛️ Configuration des Salons", style=discord.ButtonStyle.primary, custom_id="cfg_channels"))
        self.add_item(Button(label="🛡️ Outils Modération Avancée", style=discord.ButtonStyle.danger, custom_id="cfg_moderation"))
        self.add_item(Button(label="📝 Logs Détaillés", style=discord.ButtonStyle.secondary, custom_id="cfg_logs"))
        self.add_item(Button(label="💾 Backup Serveur", style=discord.ButtonStyle.success, custom_id="cfg_backup"))
        self.add_item(Button(label="🤖 IA & Automatisation", style=discord.ButtonStyle.primary, custom_id="cfg_ai"))
        self.add_item(Button(label="💎 Premium / VIP", style=discord.ButtonStyle.success, custom_id="cfg_premium"))
        self.add_item(Button(label="🎨 Personnalisation", style=discord.ButtonStyle.secondary, custom_id="cfg_customize"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow users with manage_guild permission to use the panel
        if interaction.user.guild_permissions.manage_guild:
            return True
        await interaction.response.send_message("❌ Tu dois avoir la permission `Manage Guild` pour utiliser ce panneau.", ephemeral=True)
        return False

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

    @discord.ui.button(label="🎛️ Configuration des Salons", style=discord.ButtonStyle.primary, custom_id="cfg_channels")
    async def b_channels(self, button: Button, interaction: discord.Interaction):
        channels = [c for c in interaction.guild.channels if isinstance(c, discord.TextChannel)]
        view = View(timeout=300)
        view.add_item(ChannelSelect("Choisis le salon de bienvenue", channels, "welcome_embed_channel"))
        view.add_item(ChannelSelect("Choisis le salon de départ", channels, "leave_embed_channel"))
        view.add_item(ChannelSelect("Choisis le salon de logs", channels, "logs_channel"))
        view.add_item(ChannelSelect("Choisis le salon de suggestions", channels, "suggestion_channel"))
        view.add_item(ChannelSelect("Choisis le salon de level-up", channels, "level_channel"))
        await interaction.response.send_message("🌸 Sélectionne le salon à configurer :", view=view, ephemeral=True)

    @discord.ui.button(label="🛡️ Outils Modération Avancée", style=discord.ButtonStyle.danger, custom_id="cfg_moderation")
    async def b_mod(self, button: Button, interaction: discord.Interaction):
        view = View(timeout=300)
        view.add_item(Button(label="Toggle Anti-Spam", style=discord.ButtonStyle.primary, custom_id="toggle_antispam_cfg"))
        view.add_item(Button(label="Toggle Anti-Raid", style=discord.ButtonStyle.primary, custom_id="toggle_antiraid_cfg"))
        view.add_item(Button(label="Toggle AutoMod", style=discord.ButtonStyle.primary, custom_id="toggle_automod_cfg"))
        view.add_item(Button(label="Configurer Badwords (commande)", style=discord.ButtonStyle.secondary, custom_id="info_badwords"))
        await interaction.response.send_message("🛡️ Outils de modération avancés — Utilisez les boutons ci-dessous :", view=view, ephemeral=True)

    @discord.ui.button(label="📝 Logs Détaillés", style=discord.ButtonStyle.secondary, custom_id="cfg_logs")
    async def b_logs(self, button: Button, interaction: discord.Interaction):
        view = View(timeout=300)
        view.add_item(Button(label="Activer/Désactiver Logs", style=discord.ButtonStyle.success, custom_id="toggle_logs_cfg"))
        view.add_item(Button(label="Exporter Logs (JSON)", style=discord.ButtonStyle.secondary, custom_id="export_logs_cfg"))
        await interaction.response.send_message("📝 Gestion des logs — Choisis une action :", view=view, ephemeral=True)

    @discord.ui.button(label="💾 Backup Serveur", style=discord.ButtonStyle.success, custom_id="cfg_backup")
    async def b_backup(self, button: Button, interaction: discord.Interaction):
        view = View(timeout=300)
        view.add_item(Button(label="Créer Backup Maintenant", style=discord.ButtonStyle.success, custom_id="create_backup_cfg"))
        view.add_item(Button(label="Toggle Backup Auto (24h)", style=discord.ButtonStyle.primary, custom_id="toggle_backup_cfg"))
        view.add_item(Button(label="Voir Backups", style=discord.ButtonStyle.secondary, custom_id="list_backups_cfg"))
        await interaction.response.send_message("💾 Gestion des backups — Choisis une action :", view=view, ephemeral=True)

    @discord.ui.button(label="🤖 IA & Automatisation", style=discord.ButtonStyle.primary, custom_id="cfg_ai")
    async def b_ai(self, button: Button, interaction: discord.Interaction):
        view = View(timeout=300)
        view.add_item(Button(label="Toggle AI Chat", style=discord.ButtonStyle.success, custom_id="toggle_ai_chat"))
        view.add_item(Button(label="Toggle AI AutoResponses", style=discord.ButtonStyle.primary, custom_id="toggle_ai_autoresp"))
        view.add_item(Button(label="Toggle AI Auto-Moderation", style=discord.ButtonStyle.danger, custom_id="toggle_ai_automod"))
        await interaction.response.send_message("🤖 IA & Automatisation — Choisis une option :", view=view, ephemeral=True)

    @discord.ui.button(label="💎 Premium / VIP", style=discord.ButtonStyle.success, custom_id="cfg_premium")
    async def b_premium(self, button: Button, interaction: discord.Interaction):
        view = View(timeout=300)
        view.add_item(Button(label="Voir Avantages Premium", style=discord.ButtonStyle.primary, custom_id="show_premium"))
        view.add_item(Button(label="Gérer Membres Premium", style=discord.ButtonStyle.success, custom_id="manage_premium"))
        view.add_item(Button(label="Boutique Premium", style=discord.ButtonStyle.secondary, custom_id="premium_shop_cfg"))
        await interaction.response.send_message("💎 Gestion Premium — Choisis une action :", view=view, ephemeral=True)

    @discord.ui.button(label="🎨 Personnalisation", style=discord.ButtonStyle.secondary, custom_id="cfg_customize")
    async def b_customize(self, button: Button, interaction: discord.Interaction):
        view = View(timeout=300)
        view.add_item(Button(label="Changer Préfix (commande)", style=discord.ButtonStyle.primary, custom_id="info_change_prefix"))
        view.add_item(Button(label="Créer Commande Custom", style=discord.ButtonStyle.success, custom_id="info_create_cmd"))
        view.add_item(Button(label="Gérer Auto-Réponses", style=discord.ButtonStyle.secondary, custom_id="info_manage_autoresp"))
        await interaction.response.send_message("🎨 Personnalisation — Informations et commandes disponibles :", view=view, ephemeral=True)

# Commande +config remplaçante (interactif)
@bot.command(name="config")
@commands.has_permissions(manage_guild=True)
async def config_cmd(ctx):
    conf = data.get("config", {}).get(str(ctx.guild.id), {})
    e = discord.Embed(title="⚙️ Panel de Configuration Interactif - Hoshimi", color=0xff69b4)
    e.description = "🌸 Utilise les boutons ci-dessous pour configurer rapidement ton serveur. Seuls les membres avec `Manage Guild` peuvent interagir."
    status_lines = []
    if conf.get("welcome_embed_channel"): status_lines.append(f"✅ Bienvenue : <#{conf['welcome_embed_channel']}>")
    if conf.get("leave_embed_channel"): status_lines.append(f"✅ Départ : <#{conf['leave_embed_channel']}>")
    if conf.get("logs_channel"): status_lines.append(f"✅ Logs : <#{conf['logs_channel']}>")
    if conf.get("level_channel"): status_lines.append(f"✅ Level Channel : <#{conf['level_channel']}>")
    if conf.get("auto_backup"): status_lines.append("✅ Backup Auto : Activé")
    if conf.get("antispam_enabled"): status_lines.append("✅ Anti-Spam : Activé")
    if conf.get("antiraid_enabled"): status_lines.append("✅ Anti-Raid : Activé")
    if conf.get("automod_enabled"): status_lines.append("✅ Automod : Activé")

    if status_lines:
        e.add_field(name="🔎 Configuration actuelle", value="\\n".join(status_lines), inline=False)
    else:
        e.add_field(name="🔎 Configuration actuelle", value="Aucune configuration détectée.", inline=False)

    view = MainConfigView(ctx.guild)
    await ctx.send(embed=e, view=view)


# === BACKUP SYSTEM ===
@bot.command(name="backup")
@commands.has_permissions(administrator=True)
async def backup(ctx):
    gid = str(ctx.guild.id)
    
    msg = await ctx.send("💾 Création du backup en cours... 🌸")
    
    try:
        backup_data = {
            "guild_name": ctx.guild.name,
            "guild_id": ctx.guild.id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "channels": [
                {
                    "name": c.name,
                    "type": str(c.type),
                    "position": c.position,
                    "category": c.category.name if c.category else None
                } for c in ctx.guild.channels
            ],
            "roles": [
                {
                    "name": r.name,
                    "color": r.color.value,
                    "permissions": r.permissions.value,
                    "position": r.position
                } for r in ctx.guild.roles if not r.is_default()
            ],
            "config": data.get("config", {}).get(gid, {})
        }
        
        data.setdefault("backups", {}).setdefault(gid, [])
        backup_id = len(data["backups"][gid]) + 1
        backup_data["id"] = backup_id
        data["backups"][gid].append(backup_data)
        
        # Keep only last 10 backups
        if len(data["backups"][gid]) > 10:
            data["backups"][gid] = data["backups"][gid][-10:]
        
        save_data(data)
        
        e = discord.Embed(title="✅ Backup Créé !", color=0x00ff00)
        e.description = f"💾 Backup **#{backup_id}** créé avec succès ! 🌸"
        e.add_field(name="📊 Salons", value=f"{len(backup_data['channels'])} salons", inline=True)
        e.add_field(name="🎭 Rôles", value=f"{len(backup_data['roles'])} rôles", inline=True)
        e.add_field(name="🕐 Date", value=datetime.datetime.utcnow().strftime("%d/%m/%Y %H:%M"), inline=True)
        e.set_footer(text="✨ Utilise +listbackups pour voir tous les backups 💖")
        
        await msg.edit(content=None, embed=e)
        
    except Exception as error:
        await msg.edit(content=f"❌ Erreur lors du backup: {str(error)} 💔")

@bot.command(name="listbackups")
@commands.has_permissions(administrator=True)
async def list_backups(ctx):
    gid = str(ctx.guild.id)
    backups = data.get("backups", {}).get(gid, [])
    
    if not backups:
        await ctx.send("❌ Aucun backup disponible ! Utilise `+backup` pour en créer un ! 💔")
        return
    
    e = discord.Embed(title="💾 Liste des Backups 📦", color=0xff69b4)
    
    for backup in backups[-5:]:  # Show last 5 backups
        timestamp = datetime.datetime.fromisoformat(backup["timestamp"])
        e.add_field(
            name=f"📦 Backup #{backup['id']}",
            value=f"📅 Date: {timestamp.strftime('%d/%m/%Y %H:%M')}\n📊 {len(backup['channels'])} salons, {len(backup['roles'])} rôles",
            inline=False
        )
    
    e.set_footer(text="✨ Utilise +restorebackup <id> pour restaurer 💖")
    await ctx.send(embed=e)

@bot.command(name="togglebackup")
@commands.has_permissions(administrator=True)
async def toggle_backup(ctx):
    current = get_conf(ctx.guild.id, "auto_backup", False)
    set_conf(ctx.guild.id, "auto_backup", not current)
    
    status = "activé ✅" if not current else "désactivé ❌"
    await ctx.send(f"💾 Backup automatique {status} ! {'Les backups seront créés toutes les 24h 🌸' if not current else '💔'}")

# === LEVEL SYSTEM ===
@bot.command(name="togglelevels")
@commands.has_permissions(manage_guild=True)
async def toggle_levels(ctx):
    current = get_conf(ctx.guild.id, "level_system_enabled", False)
    set_conf(ctx.guild.id, "level_system_enabled", not current)
    
    status = "activé ✅" if not current else "désactivé ❌"
    await ctx.send(f"⭐ Système de niveaux {status} ! 💖")

@bot.command(name="setlevelchannel")
@commands.has_permissions(manage_guild=True)
async def set_level_channel(ctx, channel: discord.TextChannel):
    set_conf(ctx.guild.id, "level_channel", channel.id)
    await ctx.send(f"✅ Les annonces de level up seront envoyées dans {channel.mention} ! 🎉")

@bot.command(name="rank")
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    user_data = data.get("levels", {}).get(gid, {}).get(uid, {"xp": 0, "level": 1, "messages": 0})
    
    e = discord.Embed(title=f"⭐ Rang de {member.display_name}", color=0xff69b4)
    e.set_thumbnail(url=member.display_avatar.url)
    
    e.add_field(name="📊 Niveau", value=f"**{user_data['level']}** 🌸", inline=True)
    e.add_field(name="💫 XP", value=f"**{user_data['xp']}/{user_data['level'] * 100}** ✨", inline=True)
    e.add_field(name="💬 Messages", value=f"**{user_data['messages']}** 💖", inline=True)
    
    # Progress bar
    progress = int((user_data['xp'] / (user_data['level'] * 100)) * 10)
    bar = "█" * progress + "░" * (10 - progress)
    e.add_field(name="📈 Progression", value=f"`{bar}` {int((user_data['xp'] / (user_data['level'] * 100)) * 100)}%", inline=False)
    
    # Calculate rank
    all_users = data.get("levels", {}).get(gid, {})
    sorted_users = sorted(all_users.items(), key=lambda x: (x[1]['level'], x[1]['xp']), reverse=True)
    rank = next((i for i, (u, _) in enumerate(sorted_users, 1) if u == uid), "N/A")
    
    e.add_field(name="🏆 Classement", value=f"**#{rank}** sur {len(all_users)} membres 💖", inline=False)
    
    e.set_footer(text="✨ Continue à envoyer des messages pour gagner de l'XP ! 💖")
    await ctx.send(embed=e)

@bot.command(name="leaderboard", aliases=["lb", "top"])
async def leaderboard(ctx):
    gid = str(ctx.guild.id)
    all_users = data.get("levels", {}).get(gid, {})
    
    if not all_users:
        await ctx.send("❌ Aucune donnée de niveau disponible ! 💔")
        return
    
    sorted_users = sorted(all_users.items(), key=lambda x: (x[1]['level'], x[1]['xp']), reverse=True)[:10]
    
    e = discord.Embed(title="🏆 Classement du Serveur 🏆", color=0xff69b4)
    
    medals = ["🥇", "🥈", "🥉"]
    
    for i, (uid, data_user) in enumerate(sorted_users, 1):
        member = ctx.guild.get_member(int(uid))
        if member:
            medal = medals[i-1] if i <= 3 else f"#{i}"
            e.add_field(
                name=f"{medal} {member.display_name}",
                value=f"⭐ Niveau {data_user['level']} • 💫 {data_user['xp']} XP • 💬 {data_user['messages']} messages",
                inline=False
            )
    
    e.set_footer(text="✨ Continue à participer pour monter dans le classement ! 💖")
    await ctx.send(embed=e)

@bot.command(name="setxp")
@commands.has_permissions(administrator=True)
async def set_xp(ctx, member: discord.Member, xp: int):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    data.setdefault("levels", {}).setdefault(gid, {}).setdefault(uid, {"xp": 0, "level": 1, "messages": 0})
    data["levels"][gid][uid]["xp"] = xp
    save_data(data)
    
    await ctx.send(f"✅ XP de {member.mention} définie à **{xp}** ! 💖")

@bot.command(name="setlevel")
@commands.has_permissions(administrator=True)
async def set_level(ctx, member: discord.Member, level: int):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    data.setdefault("levels", {}).setdefault(gid, {}).setdefault(uid, {"xp": 0, "level": 1, "messages": 0})
    data["levels"][gid][uid]["level"] = level
    save_data(data)
    
    await ctx.send(f"✅ Niveau de {member.mention} défini à **{level}** ! 💖")

# === PROTECTION SYSTEMS ===
@bot.command(name="toggleantispam")
@commands.has_permissions(manage_guild=True)
async def toggle_antispam(ctx):
    current = get_conf(ctx.guild.id, "antispam_enabled", False)
    set_conf(ctx.guild.id, "antispam_enabled", not current)
    
    status = "activé ✅" if not current else "désactivé ❌"
    await ctx.send(f"🛡️ Anti-spam {status} ! 💖")

@bot.command(name="toggleantiraid")
@commands.has_permissions(manage_guild=True)
async def toggle_antiraid(ctx):
    current = get_conf(ctx.guild.id, "antiraid_enabled", False)
    set_conf(ctx.guild.id, "antiraid_enabled", not current)
    
    status = "activé ✅" if not current else "désactivé ❌"
    await ctx.send(f"🛡️ Anti-raid {status} ! {'Les nouveaux membres seront surveillés 🌸' if not current else '💔'}")

@bot.command(name="toggleautomod")
@commands.has_permissions(manage_guild=True)
async def toggle_automod(ctx):
    current = get_conf(ctx.guild.id, "automod_enabled", False)
    set_conf(ctx.guild.id, "automod_enabled", not current)
    
    status = "activé ✅" if not current else "désactivé ❌"
    await ctx.send(f"🤖 Auto-modération {status} ! 💖")

@bot.command(name="addbadword")
@commands.has_permissions(manage_guild=True)
async def add_bad_word(ctx, *, word: str):
    gid = str(ctx.guild.id)
    bad_words = get_conf(ctx.guild.id, "bad_words", [])
    
    if word.lower() not in [w.lower() for w in bad_words]:
        bad_words.append(word.lower())
        set_conf(ctx.guild.id, "bad_words", bad_words)
        await ctx.send(f"✅ Mot interdit ajouté: `{word}` 🚫")
    else:
        await ctx.send(f"❌ Ce mot est déjà dans la liste ! 💔")

@bot.command(name="removebadword")
@commands.has_permissions(manage_guild=True)
async def remove_bad_word(ctx, *, word: str):
    bad_words = get_conf(ctx.guild.id, "bad_words", [])
    bad_words = [w for w in bad_words if w.lower() != word.lower()]
    set_conf(ctx.guild.id, "bad_words", bad_words)
    await ctx.send(f"✅ Mot retiré de la liste: `{word}` 💖")

@bot.command(name="listbadwords")
@commands.has_permissions(manage_guild=True)
async def list_bad_words(ctx):
    bad_words = get_conf(ctx.guild.id, "bad_words", [])
    
    if not bad_words:
        await ctx.send("✨ Aucun mot interdit configuré ! 🌸")
        return
    
    e = discord.Embed(title="🚫 Mots Interdits", color=0xff69b4)
    e.description = "```\n" + "\n".join(bad_words) + "\n```"
    e.set_footer(text=f"✨ {len(bad_words)} mot(s) interdit(s) 💖")
    await ctx.send(embed=e)

# === PREMIUM SYSTEM ===
@bot.command(name="premium")
async def premium(ctx, member: discord.Member = None):
    member = member or ctx.author
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    is_premium = data.get("premium_users", {}).get(gid, {}).get(uid, False)
    
    e = discord.Embed(title="💎 Statut Premium", color=0xffd700 if is_premium else 0xff69b4)
    e.set_thumbnail(url=member.display_avatar.url)
    
    if is_premium:
        e.description = f"✨ {member.mention} est un membre **PREMIUM** ! 💎"
        e.add_field(name="🎁 Avantages", value=(
            "• 💰 Bonus d'économie x2\n"
            "• ⭐ XP bonus x1.5\n"
            "• 🎨 Couleur de nom personnalisée\n"
            "• 🏆 Badge premium exclusif\n"
            "• 🎫 Accès prioritaire aux tickets\n"
            "• 🌸 Et plus encore !"
        ), inline=False)
    else:
        e.description = f"🌸 {member.mention} n'est pas premium"
        e.add_field(name="💫 Devenir Premium", value="Contacte un administrateur pour obtenir le statut premium ! 💖", inline=False)
    
    e.set_footer(text="✨ Système Premium 💖")
    await ctx.send(embed=e)

@bot.command(name="setpremium")
@commands.has_permissions(administrator=True)
async def set_premium(ctx, member: discord.Member, status: bool = True):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    data.setdefault("premium_users", {}).setdefault(gid, {})[uid] = status
    save_data(data)
    
    if status:
        await ctx.send(f"💎 {member.mention} est maintenant **PREMIUM** ! 🎉")
    else:
        await ctx.send(f"✨ Statut premium retiré à {member.mention} 💔")

# === CUSTOM COMMANDS ===
@bot.command(name="addcommand")
@commands.has_permissions(manage_guild=True)
async def add_command(ctx, trigger: str, *, response: str):
    gid = str(ctx.guild.id)
    data.setdefault("custom_commands", {}).setdefault(gid, {})[trigger] = response
    save_data(data)
    
    e = discord.Embed(title="✅ Commande Personnalisée Créée", color=0xff69b4)
    e.add_field(name="🎀 Commande", value=f"`{trigger}`", inline=False)
    e.add_field(name="💬 Réponse", value=response[:100], inline=False)
    e.set_footer(text="✨ Utilise cette commande dans le chat ! 💖")
    await ctx.send(embed=e)

@bot.command(name="removecommand")
@commands.has_permissions(manage_guild=True)
async def remove_command(ctx, trigger: str):
    gid = str(ctx.guild.id)
    if gid in data.get("custom_commands", {}) and trigger in data["custom_commands"][gid]:
        del data["custom_commands"][gid][trigger]
        save_data(data)
        await ctx.send(f"✅ Commande `{trigger}` supprimée ! 💖")
    else:
        await ctx.send(f"❌ Commande `{trigger}` introuvable ! 💔")

@bot.command(name="listcommands")
async def list_commands(ctx):
    gid = str(ctx.guild.id)
    commands_list = data.get("custom_commands", {}).get(gid, {})
    
    if not commands_list:
        await ctx.send("✨ Aucune commande personnalisée ! 🌸")
        return
    
    e = discord.Embed(title="🎨 Commandes Personnalisées", color=0xff69b4)
    
    for i, (trigger, response) in enumerate(list(commands_list.items())[:10], 1):
        e.add_field(
            name=f"{i}. `{trigger}`",
            value=response[:50] + "..." if len(response) > 50 else response,
            inline=False
        )
    
    e.set_footer(text=f"✨ {len(commands_list)} commande(s) 💖")
    await ctx.send(embed=e)

# === BADGES SYSTEM ===
@bot.command(name="badges")
async def badges(ctx, member: discord.Member = None):
    member = member or ctx.author
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    user_badges = data.get("badges", {}).get(gid, {}).get(uid, [])
    
    e = discord.Embed(title=f"🏆 Badges de {member.display_name}", color=0xff69b4)
    e.set_thumbnail(url=member.display_avatar.url)
    
    all_badges = {
        "welcome": {"emoji": "🌸", "name": "Bienvenue", "description": "Premier message sur le serveur"},
        "active": {"emoji": "⭐", "name": "Actif", "description": "100+ messages envoyés"},
        "veteran": {"emoji": "👑", "name": "Vétéran", "description": "Membre depuis 30+ jours"},
        "helper": {"emoji": "💖", "name": "Helper", "description": "A aidé d'autres membres"},
        "premium": {"emoji": "💎", "name": "Premium", "description": "Membre premium"},
        "booster": {"emoji": "🚀", "name": "Booster", "description": "Boost le serveur"},
        "inviter": {"emoji": "🎀", "name": "Inviteur", "description": "10+ invitations"},
        "chatty": {"emoji": "💬", "name": "Bavard", "description": "500+ messages"},
        "legendary": {"emoji": "🔥", "name": "Légendaire", "description": "Niveau 50+"}
    }
    
    if user_badges:
        badge_text = []
        for badge_id in user_badges:
            if badge_id in all_badges:
                badge = all_badges[badge_id]
                badge_text.append(f"{badge['emoji']} **{badge['name']}** - {badge['description']}")
        
        if badge_text:
            e.description = "\n".join(badge_text)
        else:
            e.description = "✨ Aucun badge débloqué pour le moment ! 🌸"
    else:
        e.description = "✨ Aucun badge débloqué ! Continue à participer pour en débloquer ! 💖"
    
    e.set_footer(text="✨ Collection de badges 💖")
    await ctx.send(embed=e)

@bot.command(name="givebadge")
@commands.has_permissions(administrator=True)
async def give_badge(ctx, member: discord.Member, badge_id: str):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    data.setdefault("badges", {}).setdefault(gid, {}).setdefault(uid, [])
    
    if badge_id not in data["badges"][gid][uid]:
        data["badges"][gid][uid].append(badge_id)
        save_data(data)
        await ctx.send(f"🏆 Badge `{badge_id}` donné à {member.mention} ! 💖")
    else:
        await ctx.send(f"❌ {member.mention} a déjà ce badge ! 💔")

# === REACTION ROLES ===
@bot.command(name="reactionrole")
@commands.has_permissions(manage_roles=True)
async def reaction_role(ctx, message_id: int, emoji: str, role: discord.Role):
    gid = str(ctx.guild.id)
    
    try:
        message = await ctx.channel.fetch_message(message_id)
        await message.add_reaction(emoji)
        
        data.setdefault("reaction_roles", {}).setdefault(gid, {})[str(message_id)] = {
            "channel": ctx.channel.id,
            "roles": data.get("reaction_roles", {}).get(gid, {}).get(str(message_id), {}).get("roles", {})
        }
        data["reaction_roles"][gid][str(message_id)]["roles"][emoji] = role.id
        save_data(data)
        
        await ctx.send(f"✅ Rôle réaction créé ! Réagis avec {emoji} pour obtenir {role.mention} ! 💖")
    except:
        await ctx.send("❌ Message introuvable ! 💔")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.member.bot:
        return
    
    gid = str(payload.guild_id)
    msg_id = str(payload.message_id)
    
    rr_data = data.get("reaction_roles", {}).get(gid, {}).get(msg_id, {})
    if rr_data:
        emoji_str = str(payload.emoji)
        role_id = rr_data.get("roles", {}).get(emoji_str)
        
        if role_id:
            guild = bot.get_guild(payload.guild_id)
            role = guild.get_role(role_id)
            if role and payload.member:
                try:
                    await payload.member.add_roles(role)
                except:
                    pass

@bot.event
async def on_raw_reaction_remove(payload):
    gid = str(payload.guild_id)
    msg_id = str(payload.message_id)
    
    rr_data = data.get("reaction_roles", {}).get(gid, {}).get(msg_id, {})
    if rr_data:
        emoji_str = str(payload.emoji)
        role_id = rr_data.get("roles", {}).get(emoji_str)
        
        if role_id:
            guild = bot.get_guild(payload.guild_id)
            member = guild.get_member(payload.user_id)
            role = guild.get_role(role_id)
            
            if role and member and not member.bot:
                try:
                    await member.remove_roles(role)
                except:
                    pass

# === ADVANCED MODERATION ===
@bot.command(name="masswarn")
@commands.has_permissions(administrator=True)
async def mass_warn(ctx, role: discord.Role, *, reason: str):
    warned = 0
    for member in role.members:
        gid = str(ctx.guild.id)
        uid = str(member.id)
        
        data.setdefault("warnings", {}).setdefault(gid, {}).setdefault(uid, [])
        data["warnings"][gid][uid].append({
            "reason": reason,
            "moderator": str(ctx.author.id),
            "date": datetime.datetime.utcnow().isoformat()
        })
        warned += 1
        
        try:
            await member.send(f"⚠️ Tu as reçu un avertissement sur **{ctx.guild.name}**\n💭 Raison: {reason}")
        except:
            pass
    
    save_data(data)
    await ctx.send(f"✅ **{warned}** membres du rôle {role.mention} ont été avertis ! 💖")

@bot.command(name="nuke")
@commands.has_permissions(administrator=True)
async def nuke(ctx):
    confirm_msg = await ctx.send("💣 **ATTENTION !** Cette commande va supprimer et recréer ce salon !\nRéagis avec ✅ pour confirmer (30s)")
    await confirm_msg.add_reaction("✅")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == "✅" and reaction.message.id == confirm_msg.id
    
    try:
        await bot.wait_for("reaction_add", timeout=30.0, check=check)
        
        channel_position = ctx.channel.position
        new_channel = await ctx.channel.clone()
        await ctx.channel.delete()
        await new_channel.edit(position=channel_position)
        
        e = discord.Embed(title="💣 Salon Nuke ! 💣", description="🌸 Le salon a été nettoyé ! 💖", color=0xff69b4)
        e.set_image(url="https://media.giphy.com/media/HhTXt43pk1I1W/giphy.gif")
        await new_channel.send(embed=e)
        
    except asyncio.TimeoutError:
        await confirm_msg.edit(content="❌ Commande annulée (temps écoulé) 💔")

@bot.command(name="massban")
@commands.has_permissions(administrator=True)
async def mass_ban(ctx, *members: discord.Member):
    banned = 0
    for member in members:
        try:
            await member.ban(reason=f"Mass ban par {ctx.author}")
            banned += 1
        except:
            pass
    
    await ctx.send(f"🔨 **{banned}** membre(s) banni(s) ! 💔")

@bot.command(name="lockall")
@commands.has_permissions(administrator=True)
async def lockall(ctx):
    locked = 0
    for channel in ctx.guild.text_channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)
            locked += 1
        except:
            pass
    
    await ctx.send(f"🔒 **{locked}** salon(s) verrouillé(s) ! 💖")

@bot.command(name="unlockall")
@commands.has_permissions(administrator=True)
async def unlockall(ctx):
    unlocked = 0
    for channel in ctx.guild.text_channels:
        try:
            await channel.set_permissions(ctx.guild.default_role, send_messages=True)
            unlocked += 1
        except:
            pass
    
    await ctx.send(f"🔓 **{unlocked}** salon(s) déverrouillé(s) ! 💖")

# === AI FEATURES (Simulation) ===
@bot.command(name="aichat")
async def ai_chat(ctx, *, question: str):
    # Simulated AI responses
    responses = [
        f"🌸 C'est une excellente question ! Voici ce que je pense : {question[:50]}... 💖",
        f"✨ Intéressant ! D'après mes données kawaii, je dirais que... 🌸",
        f"💖 Hmm, laisse-moi réfléchir... Je pense que c'est lié à... 💭",
        f"🎀 Bonne question ! En analysant ça, je dirais... ✨",
        f"🌸 D'un point de vue kawaii, c'est fascinant ! 💖"
    ]
    
    e = discord.Embed(title="🤖 IA Hoshimi", color=0xff69b4)
    e.add_field(name="💭 Ta question", value=question, inline=False)
    e.add_field(name="✨ Ma réponse", value=random.choice(responses), inline=False)
    e.set_footer(text="✨ IA Kawaii en développement 💖")
    await ctx.send(embed=e)

# === HELP COMMAND (Updated) ===
@bot.command(name="help")
async def help_cmd(ctx):
    e = discord.Embed(title="🌸 Commandes Hoshimi Kawaii 🌸", color=0xff69b4)
    e.set_thumbnail(url="https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExc3o4NGljeWVlcXh2Y3FtajF4M2pndTEyeWh1ZXR3YXVhMG9tZjkydCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Xl0oVz3eb9mfu/giphy.gif")
    
    e.add_field(name="⚙️ Configuration", value=(
        "`+config` Panel de configuration interactif\n"
        "`+setwelcome #channel <embed/text>` Bienvenue\n"
        "`+setleave #channel <embed/text>` Départ\n"
        "`+setlogs #channel` Logs\n"
        "`+rolejoin @role` Rôle auto"
    ), inline=False)
    
    e.add_field(name="🛡️ Modération Avancée", value=(
        "`+warn @user <raison>` Avertir\n"
        "`+masswarn @role <raison>` Warn en masse\n"
        "`+massban @user1 @user2...` Ban en masse\n"
        "`+nuke` Recréer le salon\n"
        "`+lockall` / `+unlockall` Verrouiller tout\n"
        "`+clear <nombre>` Supprimer messages"
    ), inline=False)
    
    e.add_field(name="🔒 Protection", value=(
        "`+toggleantispam` Anti-spam\n"
        "`+toggleantiraid` Anti-raid\n"
        "`+toggleautomod` Auto-modération\n"
        "`+addbadword <mot>` Ajouter mot interdit\n"
        "`+listbadwords` Voir mots interdits"
    ), inline=False)
    
    e.add_field(name="⭐ Système de Niveaux", value=(
        "`+togglelevels` Activer/désactiver\n"
        "`+rank [@user]` Voir son rang\n"
        "`+leaderboard` Classement\n"
        "`+setxp @user <xp>` Définir XP\n"
        "`+setlevel @user <level>` Définir niveau"
    ), inline=False)
    
    e.add_field(name="💾 Backup & Logs", value=(
        "`+backup` Créer backup\n"
        "`+listbackups` Voir backups\n"
        "`+togglebackup` Backup auto 24h\n"
        "`+setlogs #channel` Logs détaillés"
    ), inline=False)
    
    e.add_field(name="💎 Premium", value=(
        "`+premium [@user]` Voir statut\n"
        "`+setpremium @user` Donner premium\n"
        "`+badges [@user]` Voir badges\n"
        "`+givebadge @user <id>` Donner badge"
    ), inline=False)
    
    e.add_field(name="🎨 Personnalisation", value=(
        "`+addcommand <nom> <réponse>` Commande custom\n"
        "`+listcommands` Voir commandes\n"
        "`+addresponse <trigger> <réponse>` Auto-réponse\n"
        "`+listresponses` Voir réponses"
    ), inline=False)
    
    e.add_field(name="🎭 Rôles", value=(
        "`+reactionrole <msg_id> <emoji> @role` Rôle réaction\n"
        "`+roleinvite <nb> @role` Rôle par invitations"
    ), inline=False)
    
    e.add_field(name="🤖 IA & Fun", value=(
        "`+aichat <question>` Parler à l'IA\n"
        "`+8ball <question>` Boule magique\n"
        "`+love @user1 @user2` % d'amour\n"
        "`+meme` Meme aléatoire"
    ), inline=False)
    
    e.add_field(name="💰 Économie", value=(
        "`+balance` / `+daily` / `+pay`\n"
        "`+shop` / `+buy <item>`"
    ), inline=False)
    
    e.add_field(name="🎁 Giveaways", value=(
        "`+gstart <durée> <prix>` Créer\n"
        "`+gend <id>` / `+greroll <id>`"
    ), inline=False)
    
    e.add_field(name="ℹ️ Infos", value=(
        "`+serverinfo` / `+userinfo`\n"
        "`+avatar` / `+invites`"
    ), inline=False)
    
    e.set_footer(text="✨ Bot kawaii ultra complet ! 💖", icon_url=ctx.bot.user.avatar.url if ctx.bot.user.avatar else None)
    await ctx.send(embed=e)

# === ORIGINAL COMMANDS (Kept) ===
@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message: str):
    await ctx.message.delete()
    await ctx.send(message)

@bot.command(name="embed")
@commands.has_permissions(manage_messages=True)
async def embed_say(ctx, *, message: str):
    await ctx.message.delete()
    e = discord.Embed(description=message, color=0xff69b4)
    await ctx.send(embed=e)

@bot.command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild
    e = discord.Embed(title=f"🏰 Infos Serveur", color=0xff69b4)
    if guild.icon:
        e.set_thumbnail(url=guild.icon.url)
    e.add_field(name="💫 Nom", value=f"**{guild.name}**", inline=True)
    e.add_field(name="🆔 ID", value=f"`{guild.id}`", inline=True)
    e.add_field(name="👑 Propriétaire", value=guild.owner.mention if guild.owner else "Inconnu", inline=True)
    e.add_field(name="👥 Membres", value=f"**{guild.member_count}** 💖", inline=True)
    e.add_field(name="💬 Salons", value=f"**{len(guild.channels)}** 🌸", inline=True)
    e.add_field(name="🎭 Rôles", value=f"**{len(guild.roles)}** 🎀", inline=True)
    e.add_field(name="📅 Créé le", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    e.add_field(name="🌟 Niveau Boost", value=f"**Niveau {guild.premium_tier}** 💫", inline=True)
    e.set_footer(text="✨ Infos du serveur 💖")
    await ctx.send(embed=e)

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    e = discord.Embed(title=f"👤 Infos de {member.display_name}", color=0xff69b4)
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="💫 Nom", value=f"**{member.name}**", inline=True)
    e.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
    e.add_field(name="💬 Surnom", value=member.display_name, inline=True)
    e.add_field(name="📅 Compte créé", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
    e.add_field(name="🎉 A rejoint", value=member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "Inconnu", inline=True)
    e.add_field(name="🎭 Rôles", value=f"**{len(member.roles)-1}** rôles 💖", inline=True)
    if member.premium_since:
        e.add_field(name="💎 Boost depuis", value=member.premium_since.strftime("%d/%m/%Y"), inline=True)
    e.set_footer(text="✨ Infos utilisateur 💖")
    await ctx.send(embed=e)

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    e = discord.Embed(title=f"🖼️ Avatar de {member.display_name}", color=0xff69b4)
    e.set_image(url=member.display_avatar.url)
    e.add_field(name="🔗 Lien", value=f"[Clique ici !]({member.display_avatar.url})", inline=False)
    e.set_footer(text="✨ Avatar 💖")
    await ctx.send(embed=e)

@bot.command(name="poll")
async def poll(ctx, *, question: str):
    e = discord.Embed(title="📊 Sondage", description=f"**{question}**", color=0xff69b4)
    e.add_field(name="💕 Comment voter", value="Réagis avec 👍 pour OUI ou 👎 pour NON !", inline=False)
    e.set_footer(text=f"✨ Sondage créé par {ctx.author.display_name} 💖", icon_url=ctx.author.display_avatar.url)
    msg = await ctx.send(embed=e)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.command(name="roleinvite")
@commands.has_permissions(manage_roles=True)
async def role_invite(ctx, invites_needed: int, role: discord.Role):
    gid = str(ctx.guild.id)
    data.setdefault("roles_invites", {})[gid] = {"invites": invites_needed, "role": role.id}
    save_data(data)
    e = discord.Embed(title="✅ Rôle d'Invitation Configuré", color=0xff69b4)
    e.description = f"🌸 Les membres qui invitent **{invites_needed}** personnes recevront {role.mention} ! 💖"
    e.set_footer(text="✨ Système d'invitations configuré 💖")
    await ctx.send(embed=e)

@bot.command(name="invites")
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author
    gid = str(ctx.guild.id)
    uid = str(member.id)
    invite_count = data.get("user_invites", {}).get(gid, {}).get(uid, 0)
    e = discord.Embed(title=f"💌 Invitations de {member.display_name}", color=0xff69b4)
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="🎀 Invitations Totales", value=f"**{invite_count}** invitations 🌟", inline=False)
    role_config = data.get("roles_invites", {}).get(gid, {})
    if role_config:
        required = role_config.get("invites", 0)
        if invite_count >= required:
            e.add_field(name="👑 Statut", value=f"**TU AS LE RÔLE !** 🎉", inline=False)
        else:
            remaining = required - invite_count
            e.add_field(name="📊 Progression", value=f"Plus que **{remaining}** invitation(s) ! 💕", inline=False)
    e.set_footer(text="✨ Invitations 💖")
    await ctx.send(embed=e)

@bot.command(name="allowlink")
@commands.has_permissions(manage_channels=True)
async def allow_link(ctx, channel: discord.TextChannel):
    gid = str(ctx.guild.id)
    data.setdefault("allowed_links", {}).setdefault(gid, [])
    if channel.id not in data["allowed_links"][gid]:
        data["allowed_links"][gid].append(channel.id)
        save_data(data)
    await ctx.send(f"✅ Les liens sont autorisés dans {channel.mention} ! 💖")

@bot.command(name="disallowlink")
@commands.has_permissions(manage_channels=True)
async def disallow_link(ctx, channel: discord.TextChannel):
    gid = str(ctx.guild.id)
    if gid in data.get("allowed_links", {}) and channel.id in data["allowed_links"][gid]:
        data["allowed_links"][gid].remove(channel.id)
        save_data(data)
    await ctx.send(f"✅ Les liens sont bloqués dans {channel.mention} ! 💖")

@bot.command(name="ticket")
async def ticket(ctx):
    category = discord.utils.get(ctx.guild.categories, name="🎫 Tickets")
    if not category:
        category = await ctx.guild.create_category("🎫 Tickets")
    ticket_channel = await ctx.guild.create_text_channel(name=f"ticket-{ctx.author.name}", category=category, topic=f"Ticket de {ctx.author.display_name} 💖")
    await ticket_channel.set_permissions(ctx.guild.default_role, read_messages=False)
    await ticket_channel.set_permissions(ctx.author, read_messages=True, send_messages=True)
    e = discord.Embed(title="🎫 Ticket Créé", color=0xff69b4)
    e.description = f"🌸 Bienvenue {ctx.author.mention} ! Un staff va venir t'aider ! 💖\n\n🚪 Utilise `+close` pour fermer ce ticket."
    e.set_thumbnail(url=ctx.author.display_avatar.url)
    e.set_footer(text="✨ Ticket 💖")
    await ticket_channel.send(f"🎀 {ctx.author.mention} 🎀", embed=e)
    await ctx.send(f"✅ Ton ticket a été créé ! Va dans {ticket_channel.mention} ! 💖")

@bot.command(name="close")
async def close_ticket(ctx):
    if "ticket-" in ctx.channel.name:
        await ctx.send("🚪 Ce ticket va se fermer dans **5 secondes** ! 💖")
        await asyncio.sleep(5)
        await ctx.channel.delete()
    else:
        await ctx.send("❌ Cette commande ne fonctionne que dans les tickets ! 💔")

@bot.command(name="ticketpanel")
@commands.has_permissions(manage_guild=True)
async def ticket_panel(ctx):
    e = discord.Embed(title="🎫 Panel de Tickets", color=0xff69b4)
    e.description = f"🌸 **Besoin d'aide ?**\n\nClique sur le bouton ci-dessous pour créer un ticket ! 💖"
    e.set_footer(text="✨ Support disponible 24/7 💖")
    
    class TicketButton(Button):
        def __init__(self):
            super().__init__(label="🎫 Créer un Ticket", style=discord.ButtonStyle.primary, emoji="🎀")
        async def callback(self, interaction: discord.Interaction):
            category = discord.utils.get(interaction.guild.categories, name="🎫 Tickets")
            if not category:
                category = await interaction.guild.create_category("🎫 Tickets")
            ticket_channel = await interaction.guild.create_text_channel(name=f"ticket-{interaction.user.name}", category=category, topic=f"Ticket de {interaction.user.display_name} 💖")
            await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)
            await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            ticket_e = discord.Embed(title="🎫 Ticket Créé", color=0xff69b4)
            ticket_e.description = f"🌸 Bienvenue {interaction.user.mention} ! Un staff va venir t'aider ! 💖\n\n🚪 Utilise `+close` pour fermer ce ticket."
            ticket_e.set_thumbnail(url=interaction.user.display_avatar.url)
            ticket_e.set_footer(text="✨ Ticket 💖")
            await ticket_channel.send(f"🎀 {interaction.user.mention} 🎀", embed=ticket_e)
            await interaction.response.send_message(f"✅ Ton ticket a été créé dans {ticket_channel.mention} ! 💖", ephemeral=True)
    view = View(timeout=None)
    view.add_item(TicketButton())
    await ctx.send(embed=e, view=view)

@bot.command(name="setupvoc")
@commands.has_permissions(manage_channels=True)
async def setup_voc(ctx, channel: discord.VoiceChannel):
    set_conf(ctx.guild.id, "voc_trigger_channel", channel.id)
    await ctx.send(f"✅ {channel.mention} est maintenant le trigger pour les vocaux temporaires ! 💖")

@bot.command(name="createvoc")
@commands.has_permissions(manage_channels=True)
async def create_voc(ctx):
    category = discord.utils.get(ctx.guild.categories, name="🎤 Vocaux")
    if not category:
        category = await ctx.guild.create_category("🎤 Vocaux")
    trigger_channel = await ctx.guild.create_voice_channel(name="➕ Créer un Vocal 💖", category=category)
    set_conf(ctx.guild.id, "voc_trigger_channel", trigger_channel.id)
    await ctx.send(f"✅ Vocal trigger créé ! Rejoins-le pour créer ton propre vocal ! 💖")

@bot.command(name="shop")
async def shop(ctx):
    items = {
        "🎀": {"name": "Badge Kawaii", "price": 500},
        "🌸": {"name": "Fleur", "price": 300},
        "💖": {"name": "Coeur", "price": 1000},
        "⭐": {"name": "Étoile", "price": 750},
        "🦄": {"name": "Licorne", "price": 2000}
    }
    e = discord.Embed(title="🏪 Boutique", color=0xff69b4)
    for emoji, item in items.items():
        e.add_field(name=f"{emoji} **{item['name']}**", value=f"💰 **{item['price']}** 💵", inline=False)
    e.set_footer(text="✨ Utilise +buy <item> 💖")
    await ctx.send(embed=e)

@bot.command(name="buy")
async def buy(ctx, item: str):
    items = {
        "badge": {"emoji": "🎀", "name": "Badge Kawaii", "price": 500},
        "fleur": {"emoji": "🌸", "name": "Fleur", "price": 300},
        "coeur": {"emoji": "💖", "name": "Coeur", "price": 1000},
        "étoile": {"emoji": "⭐", "name": "Étoile", "price": 750},
        "licorne": {"emoji": "🦄", "name": "Licorne", "price": 2000}
    }
    item = item.lower()
    if item not in items:
        await ctx.send(f"❌ Cet item n'existe pas ! Utilise `+shop` 💔")
        return
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    data.setdefault("economy", {}).setdefault(gid, {})
    user_money = data["economy"][gid].get(uid, 0)
    item_data = items[item]
    if user_money < item_data["price"]:
        await ctx.send(f"❌ Tu n'as que **{user_money}** 💵 mais cet item coûte **{item_data['price']}** 💵 ! 💔")
        return
    data["economy"][gid][uid] = user_money - item_data["price"]
    save_data(data)
    e = discord.Embed(title="✅ Achat Réussi !", color=0xff69b4)
    e.description = f"🌸 {ctx.author.mention} a acheté **{item_data['name']}** {item_data['emoji']} ! 💖"
    e.add_field(name="💰 Prix", value=f"**{item_data['price']}** 💵", inline=True)
    e.add_field(name="💎 Restant", value=f"**{data['economy'][gid][uid]}** 💵", inline=True)
    e.set_footer(text="✨ Merci pour ton achat ! 💖")
    await ctx.send(embed=e)

@bot.command(name="setwelcome")
@commands.has_permissions(manage_guild=True)
async def set_welcome(ctx, channel: discord.TextChannel, type: str = "embed"):
    if type.lower() == "embed":
        set_conf(ctx.guild.id, "welcome_embed_channel", channel.id)
        e = discord.Embed(title="✅ Bienvenue Configurée", color=0xff69b4)
        e.description = f"🌸 La bienvenue (embed) a été configurée dans {channel.mention} ! 💖"
        await ctx.send(embed=e)
    elif type.lower() == "text":
        set_conf(ctx.guild.id, "welcome_text_channel", channel.id)
        e = discord.Embed(title="✅ Bienvenue Configurée", color=0xff69b4)
        e.description = f"🌸 La bienvenue (texte) a été configurée dans {channel.mention} ! 💖"
        await ctx.send(embed=e)

@bot.command(name="setleave")
@commands.has_permissions(manage_guild=True)
async def set_leave(ctx, channel: discord.TextChannel, type: str = "embed"):
    if type.lower() == "embed":
        set_conf(ctx.guild.id, "leave_embed_channel", channel.id)
        e = discord.Embed(title="✅ Au Revoir Configuré", color=0xff69b4)
        e.description = f"🌸 Les messages d'au revoir (embed) sont maintenant dans {channel.mention} ! 💖"
        await ctx.send(embed=e)
    elif type.lower() == "text":
        set_conf(ctx.guild.id, "leave_text_channel", channel.id)
        e = discord.Embed(title="✅ Au Revoir Configuré", color=0xff69b4)
        e.description = f"🌸 Les messages d'au revoir (texte) sont maintenant dans {channel.mention} ! 💖"
        await ctx.send(embed=e)

@bot.command(name="setlogs")
@commands.has_permissions(manage_guild=True)
async def set_logs(ctx, channel: discord.TextChannel):
    set_conf(ctx.guild.id, "logs_channel", channel.id)
    e = discord.Embed(title="✅ Logs Configurés", color=0xff69b4)
    e.description = f"🌸 Les logs sont maintenant dans {channel.mention} ! 💖"
    await ctx.send(embed=e)

@bot.command(name="setinvitation")
@commands.has_permissions(manage_guild=True)
async def set_invitation(ctx, channel: discord.TextChannel):
    set_conf(ctx.guild.id, "invitation_channel", channel.id)
    e = discord.Embed(title="✅ Invitations Configurées", color=0xff69b4)
    e.description = f"🌸 Les invitations seront trackées dans {channel.mention} ! 💖"
    await ctx.send(embed=e)

@bot.command(name="setsuggestion")
@commands.has_permissions(manage_guild=True)
async def set_suggestion(ctx, channel: discord.TextChannel):
    set_conf(ctx.guild.id, "suggestion_channel", channel.id)
    e = discord.Embed(title="✅ Suggestions Configurées", color=0xff69b4)
    e.description = f"🌸 Les suggestions iront dans {channel.mention} ! 💖"
    await ctx.send(embed=e)

@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason: str = "Aucune raison"):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    data.setdefault("warnings", {}).setdefault(gid, {}).setdefault(uid, [])
    data["warnings"][gid][uid].append({"reason": reason, "moderator": str(ctx.author.id), "date": datetime.datetime.utcnow().isoformat()})
    save_data(data)
    warn_count = len(data["warnings"][gid][uid])
    e = discord.Embed(title="⚠️ Avertissement", color=0xff69b4)
    e.add_field(name="💫 Membre", value=member.mention, inline=True)
    e.add_field(name="📝 Raison", value=reason, inline=True)
    e.add_field(name="📊 Total", value=f"**{warn_count}** avertissement(s) 🌸", inline=True)
    e.set_footer(text="✨ Sois plus gentil(le) la prochaine fois 💖")
    await ctx.send(embed=e)
    await log_action(ctx.guild, "warning", membre=member.mention, raison=reason, modérateur=ctx.author.mention)
    try:
        await member.send(f"⚠️ Tu as reçu un avertissement sur **{ctx.guild.name}** ✨\n💭 Raison: {reason}\n💖 Sois plus gentil(le) !")
    except:
        pass

@bot.command(name="warnings")
async def warnings(ctx, member: discord.Member):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    warns = data.get("warnings", {}).get(gid, {}).get(uid, [])
    if not warns:
        await ctx.send(f"✨ {member.mention} n'a aucun avertissement ! 💖")
        return
    e = discord.Embed(title=f"⚠️ Avertissements de {member.display_name}", color=0xff69b4)
    for i, w in enumerate(warns, 1):
        e.add_field(name=f"📋 #{i}", value=f"**💭 Raison:** {w['reason']}\n**📅 Date:** {w['date'][:10]}", inline=False)
    e.set_footer(text="✨ Essaye d'être plus gentil(le) 💖")
    await ctx.send(embed=e)

@bot.command(name="clearwarns")
@commands.has_permissions(manage_messages=True)
async def clear_warns(ctx, member: discord.Member):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    if gid in data.get("warnings", {}) and uid in data["warnings"][gid]:
        del data["warnings"][gid][uid]
        save_data(data)
        await ctx.send(f"✨ Avertissements de {member.mention} effacés ! 💖")
    else:
        await ctx.send(f"🌸 {member.mention} n'a aucun avertissement ! ✨")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "Aucune raison"):
    await member.kick(reason=reason)
    e = discord.Embed(title="👢 Membre expulsé", color=0xff69b4)
    e.add_field(name="💫 Membre", value=member.mention)
    e.add_field(name="💭 Raison", value=reason)
    e.set_footer(text="✨ Bye bye 👋💖")
    await ctx.send(embed=e)
    await log_action(ctx.guild, "member_kick", membre=member.display_name, raison=reason, modérateur=ctx.author.mention)

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "Aucune raison"):
    """Bannir un membre et logger l'action proprement."""
    try:
        await member.ban(reason=reason)
    except Exception as e:
        await ctx.send(f"❌ Impossible de bannir {member.mention} : {e}")
        return

    e = discord.Embed(title="🔨 Membre banni", color=0xff1493)
    e.add_field(name="💫 Membre", value=member.mention)
    e.add_field(name="💭 Raison", value=reason)
    e.set_footer(text="✨ Au revoir 👋💔")
    await ctx.send(embed=e)

    # Log the ban action in the configured logs channel (if any)
    await log_action(
        ctx.guild,
        "member_ban",
        membre=member.display_name,
        raison=reason,
        modérateur=ctx.author.mention
    )
if __name__ == "__main__":
    TOKEN = os.environ.get("DISCORD_TOKEN")
    
    if not TOKEN:
        print("❌ DISCORD_TOKEN manquant dans les variables d'environnement.")
        exit(1)

    print("🚀 Démarrage du bot Hoshikuzu...")
    
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ Token invalide.")
    except Exception as e:
        print(f"❌ Erreur fatale : {e}")
