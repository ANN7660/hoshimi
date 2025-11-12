#!/usr/bin/env python3
import os, json, threading, http.server, socketserver, asyncio, datetime, re, random
import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select, Modal, TextInput

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
DATA_FILE = "hoshikuzu_data.json"

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
        "levels": {},
        "economy": {},
        "giveaways": {},
        "reaction_roles": {},
        "auto_responses": {},
        "suggestions": {}
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
EMOJI = "<a:caarrow:1433143710094196997>"

@bot.event
async def on_ready():
    print(f"✅ Bot connecté: {bot.user}")
    await bot.change_presence(activity=discord.Game(name="hoshikuzu | +help"))
    check_giveaways.start()
    
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            data["invites"][str(guild.id)] = {inv.code: inv.uses for inv in invites}
            save_data(data)
        except:
            pass

# === HELP ===
@bot.command(name="help")
async def help_cmd(ctx):
    e = discord.Embed(title="🌿 Commandes Hoshikuzu", color=0x2ecc71)
    
    e.add_field(name="📊 Configuration", value=(
        "`+config` - Configuration actuelle\n"
        "`+setwelcome #channel <embed/text>` - Bienvenue\n"
        "`+setleave #channel <embed/text>` - Au revoir\n"
        "`+setlogs #channel` - Logs\n"
        "`+setinvitation #channel` - Logs invitations\n"
        "`+setsuggestion #channel` - Salon suggestions"
    ), inline=False)
    
    e.add_field(name="👥 Invitations", value=(
        "`+roleinvite <nb> @role` - Rôle par invitations\n"
        "`+invites [@user]` - Voir les invitations"
    ), inline=False)
    
    e.add_field(name="🔒 Modération", value=(
        "`+warn @user <raison>` - Avertir\n"
        "`+warnings @user` - Voir avertissements\n"
        "`+clearwarns @user` - Effacer avertissements\n"
        "`+kick @user <raison>` - Expulser\n"
        "`+ban @user <raison>` - Bannir\n"
        "`+mute @user <durée>` - Mute (ex: 10m, 1h)\n"
        "`+unmute @user` - Unmute\n"
        "`+clear <nombre>` - Supprimer messages\n"
        "`+lock` / `+unlock` - Verrouiller salon\n"
        "`+slowmode <secondes>` - Mode lent"
    ), inline=False)
    
    e.add_field(name="🎮 Niveaux & XP", value=(
        "`+rank [@user]` - Voir son niveau\n"
        "`+leaderboard` - Top niveaux serveur\n"
        "`+setlevelrole <niveau> @role` - Rôle par niveau"
    ), inline=False)
    
    e.add_field(name="💰 Économie", value=(
        "`+balance [@user]` - Voir son argent\n"
        "`+daily` - Bonus journalier\n"
        "`+pay @user <montant>` - Donner argent\n"
        "`+shop` - Boutique du serveur\n"
        "`+buy <item>` - Acheter un item"
    ), inline=False)
    
    e.add_field(name="🎁 Giveaways", value=(
        "`+gstart <durée> <prix>` - Créer giveaway\n"
        "`+gend <message_id>` - Terminer giveaway\n"
        "`+greroll <message_id>` - Retirer gagnant"
    ), inline=False)
    
    e.add_field(name="🎭 Rôles Réactions", value=(
        "`+reactionrole` - Créer menu rôles\n"
        "`+addrr <msg_id> <emoji> @role` - Ajouter rôle"
    ), inline=False)
    
    e.add_field(name="🎫 Tickets", value=(
        "`+ticket` - Créer ticket\n"
        "`+ticketpanel` - Panel tickets\n"
        "`+close` - Fermer ticket"
    ), inline=False)
    
    e.add_field(name="🔊 Vocaux", value=(
        "`+createvoc` - Créer vocal trigger\n"
        "`+setupvoc #channel` - Configurer vocal"
    ), inline=False)
    
    e.add_field(name="🔗 Liens", value=(
        "`+allowlink #channel` - Autoriser liens\n"
        "`+disallowlink #channel` - Bloquer liens"
    ), inline=False)
    
    e.add_field(name="🤖 Auto-réponses", value=(
        "`+addresponse <trigger> <réponse>` - Ajouter\n"
        "`+listresponses` - Voir toutes\n"
        "`+delresponse <trigger>` - Supprimer"
    ), inline=False)
    
    e.add_field(name="💡 Suggestions", value=(
        "`+suggest <suggestion>` - Faire suggestion\n"
        "`+acceptsugg <id>` - Accepter\n"
        "`+denysugg <id>` - Refuser"
    ), inline=False)
    
    e.add_field(name="🎲 Fun", value=(
        "`+8ball <question>` - Boule magique\n"
        "`+coinflip` - Pile ou face\n"
        "`+dice` - Lancer dé\n"
        "`+love @user1 @user2` - % d'amour\n"
        "`+meme` - Meme aléatoire"
    ), inline=False)
    
    e.add_field(name="ℹ️ Utilitaire", value=(
        "`+serverinfo` - Infos serveur\n"
        "`+userinfo [@user]` - Infos utilisateur\n"
        "`+avatar [@user]` - Avatar\n"
        "`+poll <question>` - Sondage"
    ), inline=False)
    
    await ctx.send(embed=e)

# === CONFIG ===
@bot.command(name="config")
@commands.has_permissions(manage_guild=True)
async def config_cmd(ctx):
    conf = data.get("config", {}).get(str(ctx.guild.id), {})
    e = discord.Embed(title="⚙️ Configuration", color=0x3498db)
    
    for key in ["logs_channel", "welcome_embed_channel", "welcome_text_channel", 
                "leave_embed_channel", "leave_text_channel", "invitation_channel", 
                "suggestion_channel", "voc_trigger_channel", "auto_role"]:
        val = conf.get(key)
        if val:
            name = key.replace("_channel", "").replace("_", " ").title()
            if "role" in key:
                e.add_field(name=name, value=f"<@&{val}>", inline=False)
            else:
                e.add_field(name=name, value=f"<#{val}>", inline=False)
    
    await ctx.send(embed=e)

# === CONFIGURATION COMMANDS ===
@bot.command(name="setwelcome")
@commands.has_permissions(manage_guild=True)
async def set_welcome(ctx, channel: discord.TextChannel, type: str = "embed"):
    if type.lower() == "embed":
        set_conf(ctx.guild.id, "welcome_embed_channel", channel.id)
        await ctx.send(f"✅ Bienvenue (embed) → {channel.mention}")
    elif type.lower() == "text":
        set_conf(ctx.guild.id, "welcome_text_channel", channel.id)
        await ctx.send(f"✅ Bienvenue (texte) → {channel.mention}")

@bot.command(name="setleave")
@commands.has_permissions(manage_guild=True)
async def set_leave(ctx, channel: discord.TextChannel, type: str = "embed"):
    if type.lower() == "embed":
        set_conf(ctx.guild.id, "leave_embed_channel", channel.id)
        await ctx.send(f"✅ Au revoir (embed) → {channel.mention}")
    elif type.lower() == "text":
        set_conf(ctx.guild.id, "leave_text_channel", channel.id)
        await ctx.send(f"✅ Au revoir (texte) → {channel.mention}")

@bot.command(name="setlogs")
@commands.has_permissions(manage_guild=True)
async def set_logs(ctx, channel: discord.TextChannel):
    set_conf(ctx.guild.id, "logs_channel", channel.id)
    await ctx.send(f"✅ Logs → {channel.mention}")

@bot.command(name="setinvitation")
@commands.has_permissions(manage_guild=True)
async def set_invitation(ctx, channel: discord.TextChannel):
    set_conf(ctx.guild.id, "invitation_channel", channel.id)
    await ctx.send(f"✅ Invitations → {channel.mention}")

@bot.command(name="setsuggestion")
@commands.has_permissions(manage_guild=True)
async def set_suggestion(ctx, channel: discord.TextChannel):
    set_conf(ctx.guild.id, "suggestion_channel", channel.id)
    await ctx.send(f"✅ Suggestions → {channel.mention}")

# === MODERATION ===
@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason: str = "Aucune raison"):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    data.setdefault("warnings", {}).setdefault(gid, {}).setdefault(uid, [])
    data["warnings"][gid][uid].append({
        "reason": reason,
        "moderator": str(ctx.author.id),
        "date": datetime.datetime.utcnow().isoformat()
    })
    save_data(data)
    
    warn_count = len(data["warnings"][gid][uid])
    e = discord.Embed(title="⚠️ Avertissement", color=0xe74c3c)
    e.add_field(name="Membre", value=member.mention, inline=True)
    e.add_field(name="Raison", value=reason, inline=True)
    e.add_field(name="Total", value=f"{warn_count} avertissement(s)", inline=True)
    await ctx.send(embed=e)
    
    try:
        await member.send(f"⚠️ Tu as reçu un avertissement sur **{ctx.guild.name}**\nRaison: {reason}")
    except:
        pass

@bot.command(name="warnings")
async def warnings(ctx, member: discord.Member):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    warns = data.get("warnings", {}).get(gid, {}).get(uid, [])
    
    if not warns:
        await ctx.send(f"✅ {member.mention} n'a aucun avertissement")
        return
    
    e = discord.Embed(title=f"⚠️ Avertissements de {member.display_name}", color=0xe74c3c)
    for i, w in enumerate(warns, 1):
        e.add_field(
            name=f"#{i}",
            value=f"**Raison:** {w['reason']}\n**Date:** {w['date'][:10]}",
            inline=False
        )
    await ctx.send(embed=e)

@bot.command(name="clearwarns")
@commands.has_permissions(manage_messages=True)
async def clear_warns(ctx, member: discord.Member):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    if gid in data.get("warnings", {}) and uid in data["warnings"][gid]:
        del data["warnings"][gid][uid]
        save_data(data)
        await ctx.send(f"✅ Avertissements de {member.mention} effacés")
    else:
        await ctx.send(f"ℹ️ {member.mention} n'a aucun avertissement")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "Aucune raison"):
    await member.kick(reason=reason)
    e = discord.Embed(title="👢 Membre expulsé", color=0xe67e22)
    e.add_field(name="Membre", value=member.mention)
    e.add_field(name="Raison", value=reason)
    await ctx.send(embed=e)

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "Aucune raison"):
    await member.ban(reason=reason)
    e = discord.Embed(title="🔨 Membre banni", color=0xc0392b)
    e.add_field(name="Membre", value=member.mention)
    e.add_field(name="Raison", value=reason)
    await ctx.send(embed=e)

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, duration: str = "10m"):
    # Créer ou récupérer le rôle Muted
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted", color=0x818386)
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, speak=False)
    
    await member.add_roles(muted_role)
    
    # Parser durée
    time_convert = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    duration_seconds = int(duration[:-1]) * time_convert.get(duration[-1], 60)
    
    await ctx.send(f"🔇 {member.mention} a été mute pour {duration}")
    
    await asyncio.sleep(duration_seconds)
    await member.remove_roles(muted_role)
    await ctx.send(f"🔊 {member.mention} n'est plus mute")

@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        await ctx.send(f"🔊 {member.mention} n'est plus mute")
    else:
        await ctx.send(f"ℹ️ {member.mention} n'est pas mute")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🗑️ {amount} messages supprimés")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Salon verrouillé")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Salon déverrouillé")

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"⏱️ Mode lent: {seconds}s")

# === LEVELS & XP ===
@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return
    
    gid = str(message.guild.id)
    uid = str(message.author.id)
    
    # XP System
    data.setdefault("levels", {}).setdefault(gid, {}).setdefault(uid, {"xp": 0, "level": 1})
    data["levels"][gid][uid]["xp"] += random.randint(15, 25)
    
    xp = data["levels"][gid][uid]["xp"]
    level = data["levels"][gid][uid]["level"]
    xp_needed = level * 100
    
    if xp >= xp_needed:
        data["levels"][gid][uid]["level"] += 1
        data["levels"][gid][uid]["xp"] = 0
        save_data(data)
        
        e = discord.Embed(title="🎉 Level UP!", color=0xf1c40f)
        e.description = f"{message.author.mention} est maintenant niveau **{level + 1}** !"
        await message.channel.send(embed=e)
    else:
        save_data(data)
    
    # Link filter
    allowed_channels = data.get("allowed_links", {}).get(gid, [])
    if message.channel.id not in allowed_channels:
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        if re.search(url_pattern, message.content):
            await message.delete()
            await message.channel.send(f"❌ {message.author.mention}, liens interdits !", delete_after=5)
            return
    
    # Auto responses
    auto_resp = data.get("auto_responses", {}).get(gid, {})
    for trigger, response in auto_resp.items():
        if trigger.lower() in message.content.lower():
            await message.channel.send(response)
            break
    
    await bot.process_commands(message)

@bot.command(name="rank")
async def rank(ctx, member: discord.Member = None):
    member = member or ctx.author
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    user_data = data.get("levels", {}).get(gid, {}).get(uid, {"xp": 0, "level": 1})
    
    e = discord.Embed(title=f"📊 Rank de {member.display_name}", color=0x9b59b6)
    e.add_field(name="Niveau", value=f"**{user_data['level']}**", inline=True)
    e.add_field(name="XP", value=f"**{user_data['xp']}** / {user_data['level'] * 100}", inline=True)
    e.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=e)

@bot.command(name="leaderboard")
async def leaderboard(ctx):
    gid = str(ctx.guild.id)
    levels = data.get("levels", {}).get(gid, {})
    
    sorted_users = sorted(levels.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)[:10]
    
    e = discord.Embed(title="🏆 Top 10 Niveaux", color=0xf39c12)
    for i, (uid, udata) in enumerate(sorted_users, 1):
        user = ctx.guild.get_member(int(uid))
        if user:
            e.add_field(
                name=f"#{i} - {user.display_name}",
                value=f"Niveau **{udata['level']}** | XP: {udata['xp']}",
                inline=False
            )
    await ctx.send(embed=e)

# === ECONOMY ===
@bot.command(name="balance", aliases=["bal"])
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    money = data.get("economy", {}).get(gid, {}).get(uid, 0)
    
    e = discord.Embed(title=f"💰 Balance de {member.display_name}", color=0x27ae60)
    e.add_field(name="Argent", value=f"**{money}** 💵")
    await ctx.send(embed=e)

@bot.command(name="daily")
async def daily(ctx):
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    
    data.setdefault("economy", {}).setdefault(gid, {})
    data["economy"][gid][uid] = data["economy"][gid].get(uid, 0) + 100
    save_data(data)
    
    await ctx.send(f"💰 {ctx.author.mention} a reçu **100** 💵 !")

@bot.command(name="pay")
async def pay(ctx, member: discord.Member, amount: int):
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    target_uid = str(member.id)
    
    data.setdefault("economy", {}).setdefault(gid, {})
    
    if data["economy"][gid].get(uid, 0) < amount:
        await ctx.send("❌ Tu n'as pas assez d'argent !")
        return
    
    data["economy"][gid][uid] = data["economy"][gid].get(uid, 0) - amount
    data["economy"][gid][target_uid] = data["economy"][gid].get(target_uid, 0) + amount
    save_data(data)
    
    await ctx.send(f"💸 {ctx.author.mention} a donné **{amount}** 💵 à {member.mention}")

# === GIVEAWAYS ===
@bot.command(name="gstart")
@commands.has_permissions(manage_guild=True)
async def gstart(ctx, duration: str, *, prize: str):
    # Parser durée
    time_convert = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    duration_seconds = int(duration[:-1]) * time_convert.get(duration[-1], 60)
    
    end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=duration_seconds)
    
    e = discord.Embed(title="🎁 GIVEAWAY", color=0xe91e63)
    e.description = f"**Prix:** {prize}\n**Durée:** {duration}\n**Réagis avec 🎉 pour participer !**"
    e.set_footer(text=f"Se termine le {end_time.strftime('%d/%m/%Y à %H:%M')}")
    
    msg = await ctx.send(embed=e)
    await msg.add_reaction("🎉")
    
    gid = str(ctx.guild.id)
    data.setdefault("giveaways", {})[str(msg.id)] = {
        "channel": ctx.channel.id,
        "prize": prize,
        "end_time": end_time.isoformat(),
        "guild": gid
    }
    save_data(data)

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
                            e = discord.Embed(title="🎉 Giveaway terminé !", color=0x2ecc71)
                            e.description = f"**Gagnant:** {winner.mention}\n**Prix:** {gdata['prize']}"
                            await channel.send(embed=e)
                        else:
                            await channel.send("❌ Aucun participant au giveaway")
                except:
                    pass
        
        del data["giveaways"][msg_id]
        save_data(data)

# === REACTION ROLES ===
@bot.command(name="reactionrole")
@commands.has_permissions(manage_roles=True)
async def reaction_role(ctx):
    e = discord.Embed(title="🎭 Choisis tes rôles !", description="Réagis pour obtenir un rôle", color=0x3498db)
    msg = await ctx.send(embed=e)
    
    gid = str(ctx.guild.id)
    data.setdefault("reaction_roles", {})[str(msg.id)] = {"guild": gid, "roles": {}}
    save_data(data)
    
    await ctx.send(f"✅ Menu créé ! Utilise `+addrr {msg.id} <emoji> @role`")

@bot.command(name="addrr")
@commands.has_permissions(manage_roles=True)
async def add_rr(ctx, message_id: str, emoji: str, role: discord.Role):
    if message_id not in data.get("reaction_roles", {}):
        await ctx.send("❌ Message introuvable")
        return
    
    data["reaction_roles"][message_id]["roles"][emoji] = role.id
    save_data(data)
    
    try:
        msg = await ctx.channel.fetch_message(int(message_id))
        await msg.add_reaction(emoji)
        await ctx.send(f"✅ {emoji} → {role.mention}")
    except:
        await ctx.send("❌ Erreur")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    
    msg_id = str(payload.message_id)
    
    # Reaction roles
    if msg_id in data.get("reaction_roles", {}):
        rr_data = data["reaction_roles"][msg_id]
        emoji = str(payload.emoji)
        
        if emoji in rr_data["roles"]:
            guild = bot.get_guild(payload.guild_id)
            role = guild.get_role(rr_data["roles"][emoji])
            member = guild.get_member(payload.user_id)
            
            if role and member:
                await member.add_roles(role)
    
    # Tickets
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    
    panel_id = get_conf(guild.id, "ticket_panel")
    if panel_id and payload.message_id == panel_id and str(payload.emoji) == "🎫":
        member = guild.get_member(payload.user_id)
        if not member:
            return
        
        existing = discord.utils.get(guild.text_channels, name=f"ticket-{member.name}")
        if existing:
            return
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        
        ticket_channel = await guild.create_text_channel(f"ticket-{member.name}", overwrites=overwrites)
        e = discord.Embed(title="🎫 Ticket créé", description=f"{member.mention}, explique ton problème ici.", color=0x2ecc71)
        await ticket_channel.send(embed=e, view=TicketView())

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return
    
    msg_id = str(payload.message_id)
    
    # Reaction roles
    if msg_id in data.get("reaction_roles", {}):
        rr_data = data["reaction_roles"][msg_id]
        emoji = str(payload.emoji)
        
        if emoji in rr_data["roles"]:
            guild = bot.get_guild(payload.guild_id)
            role = guild.get_role(rr_data["roles"][emoji])
            member = guild.get_member(payload.user_id)
            
            if role and member:
                await member.remove_roles(role)

# === AUTO RESPONSES ===
@bot.command(name="addresponse")
@commands.has_permissions(manage_guild=True)
async def add_response(ctx, trigger: str, *, response: str):
    gid = str(ctx.guild.id)
    data.setdefault("auto_responses", {}).setdefault(gid, {})[trigger.lower()] = response
    save_data(data)
    await ctx.send(f"✅ Auto-réponse ajoutée: `{trigger}` → {response}")

@bot.command(name="listresponses")
async def list_responses(ctx):
    gid = str(ctx.guild.id)
    responses = data.get("auto_responses", {}).get(gid, {})
    
    if not responses:
        await ctx.send("ℹ️ Aucune auto-réponse configurée")
        return
    
    e = discord.Embed(title="🤖 Auto-réponses", color=0x3498db)
    for trigger, response in responses.items():
        e.add_field(name=f"Trigger: {trigger}", value=response, inline=False)
    await ctx.send(embed=e)

@bot.command(name="delresponse")
@commands.has_permissions(manage_guild=True)
async def del_response(ctx, trigger: str):
    gid = str(ctx.guild.id)
    if gid in data.get("auto_responses", {}) and trigger.lower() in data["auto_responses"][gid]:
        del data["auto_responses"][gid][trigger.lower()]
        save_data(data)
        await ctx.send(f"✅ Auto-réponse `{trigger}` supprimée")
    else:
        await ctx.send(f"❌ Auto-réponse `{trigger}` introuvable")

# === SUGGESTIONS ===
@bot.command(name="suggest")
async def suggest(ctx, *, suggestion: str):
    sugg_channel_id = get_conf(ctx.guild.id, "suggestion_channel")
    if not sugg_channel_id:
        await ctx.send("❌ Aucun salon de suggestions configuré. Utilise `+setsuggestion #channel`")
        return
    
    channel = ctx.guild.get_channel(sugg_channel_id)
    if not channel:
        await ctx.send("❌ Salon de suggestions introuvable")
        return
    
    e = discord.Embed(title="💡 Nouvelle suggestion", color=0x3498db)
    e.description = suggestion
    e.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    e.set_footer(text=f"ID: {ctx.message.id}")
    
    msg = await channel.send(embed=e)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    
    gid = str(ctx.guild.id)
    data.setdefault("suggestions", {}).setdefault(gid, {})[str(ctx.message.id)] = {
        "message_id": msg.id,
        "author": ctx.author.id,
        "suggestion": suggestion,
        "status": "pending"
    }
    save_data(data)
    
    await ctx.send(f"✅ Suggestion envoyée dans {channel.mention}")

@bot.command(name="acceptsugg")
@commands.has_permissions(manage_guild=True)
async def accept_sugg(ctx, suggestion_id: str):
    gid = str(ctx.guild.id)
    
    if suggestion_id not in data.get("suggestions", {}).get(gid, {}):
        await ctx.send("❌ Suggestion introuvable")
        return
    
    sugg_data = data["suggestions"][gid][suggestion_id]
    sugg_channel_id = get_conf(ctx.guild.id, "suggestion_channel")
    channel = ctx.guild.get_channel(sugg_channel_id)
    
    if channel:
        try:
            msg = await channel.fetch_message(sugg_data["message_id"])
            e = msg.embeds[0]
            e.color = 0x2ecc71
            e.title = "✅ Suggestion acceptée"
            await msg.edit(embed=e)
            
            data["suggestions"][gid][suggestion_id]["status"] = "accepted"
            save_data(data)
            
            await ctx.send("✅ Suggestion acceptée")
        except:
            await ctx.send("❌ Erreur lors de la mise à jour")

@bot.command(name="denysugg")
@commands.has_permissions(manage_guild=True)
async def deny_sugg(ctx, suggestion_id: str):
    gid = str(ctx.guild.id)
    
    if suggestion_id not in data.get("suggestions", {}).get(gid, {}):
        await ctx.send("❌ Suggestion introuvable")
        return
    
    sugg_data = data["suggestions"][gid][suggestion_id]
    sugg_channel_id = get_conf(ctx.guild.id, "suggestion_channel")
    channel = ctx.guild.get_channel(sugg_channel_id)
    
    if channel:
        try:
            msg = await channel.fetch_message(sugg_data["message_id"])
            e = msg.embeds[0]
            e.color = 0xe74c3c
            e.title = "❌ Suggestion refusée"
            await msg.edit(embed=e)
            
            data["suggestions"][gid][suggestion_id]["status"] = "denied"
            save_data(data)
            
            await ctx.send("✅ Suggestion refusée")
        except:
            await ctx.send("❌ Erreur lors de la mise à jour")

# === FUN COMMANDS ===
@bot.command(name="8ball")
async def eight_ball(ctx, *, question: str):
    responses = [
        "Oui, absolument!", "C'est certain.", "Sans aucun doute.",
        "Oui, définitivement.", "Compte là-dessus.", "Probablement.",
        "Les signes pointent vers oui.", "Peut-être.", "Demande plus tard.",
        "Je ne peux pas prédire maintenant.", "Concentre-toi et redemande.",
        "N'y compte pas.", "Ma réponse est non.", "Mes sources disent non.",
        "Les perspectives ne sont pas bonnes.", "Très douteux."
    ]
    e = discord.Embed(title="🎱 Boule magique", color=0x9b59b6)
    e.add_field(name="Question", value=question, inline=False)
    e.add_field(name="Réponse", value=random.choice(responses), inline=False)
    await ctx.send(embed=e)

@bot.command(name="coinflip")
async def coinflip(ctx):
    result = random.choice(["Pile 🪙", "Face 🎭"])
    await ctx.send(f"**{result}**")

@bot.command(name="dice")
async def dice(ctx):
    result = random.randint(1, 6)
    await ctx.send(f"🎲 Tu as obtenu: **{result}**")

@bot.command(name="love")
async def love(ctx, user1: discord.Member, user2: discord.Member):
    percentage = random.randint(0, 100)
    
    if percentage < 25:
        emoji = "💔"
        message = "Aucune chance..."
    elif percentage < 50:
        emoji = "❤️"
        message = "Peut-être..."
    elif percentage < 75:
        emoji = "💕"
        message = "Bonne compatibilité!"
    else:
        emoji = "💖"
        message = "Match parfait!"
    
    e = discord.Embed(title="💘 Calculateur d'amour", color=0xe91e63)
    e.description = f"{user1.mention} + {user2.mention}\n\n{emoji} **{percentage}%** {emoji}\n{message}"
    await ctx.send(embed=e)

@bot.command(name="meme")
async def meme(ctx):
    memes = [
        "https://i.imgflip.com/30b1gx.jpg",
        "https://i.imgflip.com/1bgw.jpg",
        "https://i.imgflip.com/23ls.jpg"
    ]
    e = discord.Embed(title="😂 Meme aléatoire", color=0xf39c12)
    e.set_image(url=random.choice(memes))
    await ctx.send(embed=e)

# === UTILITY COMMANDS ===
@bot.command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild
    e = discord.Embed(title=f"📊 Infos sur {guild.name}", color=0x3498db)
    e.set_thumbnail(url=guild.icon.url if guild.icon else None)
    e.add_field(name="👑 Propriétaire", value=guild.owner.mention, inline=True)
    e.add_field(name="👥 Membres", value=guild.member_count, inline=True)
    e.add_field(name="📅 Créé le", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    e.add_field(name="💬 Salons texte", value=len(guild.text_channels), inline=True)
    e.add_field(name="🔊 Salons vocaux", value=len(guild.voice_channels), inline=True)
    e.add_field(name="🎭 Rôles", value=len(guild.roles), inline=True)
    await ctx.send(embed=e)

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    e = discord.Embed(title=f"👤 Infos sur {member.display_name}", color=0x9b59b6)
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="📛 Nom", value=str(member), inline=True)
    e.add_field(name="🆔 ID", value=member.id, inline=True)
    e.add_field(name="📅 Compte créé", value=member.created_at.strftime("%d/%m/%Y"), inline=False)
    e.add_field(name="📥 A rejoint", value=member.joined_at.strftime("%d/%m/%Y"), inline=False)
    e.add_field(name="🎭 Rôles", value=f"{len(member.roles)} rôles", inline=True)
    await ctx.send(embed=e)

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    e = discord.Embed(title=f"🖼️ Avatar de {member.display_name}", color=0x3498db)
    e.set_image(url=member.display_avatar.url)
    await ctx.send(embed=e)

@bot.command(name="poll")
@commands.has_permissions(manage_messages=True)
async def poll(ctx, *, question: str):
    e = discord.Embed(title="📊 Sondage", description=question, color=0x3498db)
    e.set_footer(text=f"Sondage créé par {ctx.author.display_name}")
    msg = await ctx.send(embed=e)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

# === INVITATIONS SYSTEM ===
@bot.command(name="roleinvite")
@commands.has_permissions(manage_guild=True)
async def role_invite(ctx, nombre: int, role: discord.Role):
    gid = str(ctx.guild.id)
    data.setdefault("roles_invites", {}).setdefault(gid, {})[str(nombre)] = role.id
    save_data(data)
    await ctx.send(f"✅ {nombre} invitations → {role.mention}")

@bot.command(name="invites")
async def invites_cmd(ctx, member: discord.Member = None):
    member = member or ctx.author
    gid = str(ctx.guild.id)
    invites_count = data.get("user_invites", {}).get(gid, {}).get(str(member.id), 0)
    
    e = discord.Embed(title=f"📊 Invitations de {member.display_name}", color=0x3498db)
    e.add_field(name="Total", value=f"**{invites_count}** invitation(s)")
    e.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=e)

@bot.event
async def on_member_join(member):
    guild = member.guild
    gid = str(guild.id)
    
    # Auto role
    auto_role_id = get_conf(guild.id, "auto_role")
    if auto_role_id:
        role = guild.get_role(auto_role_id)
        if role:
            try:
                await member.add_roles(role)
            except:
                pass
    
    # Welcome embed
    embed_channel_id = get_conf(guild.id, "welcome_embed_channel")
    if embed_channel_id:
        channel = guild.get_channel(embed_channel_id)
        if channel:
            e = discord.Embed(title="🎉 Bienvenue !", description=f"**{member.mention}** vient de rejoindre **{guild.name}** !", color=0x2ecc71)
            e.set_thumbnail(url=member.display_avatar.url)
            e.set_footer(text=f"Nous sommes maintenant {guild.member_count} membres !")
            await channel.send(embed=e)
    
    # Welcome text
    text_channel_id = get_conf(guild.id, "welcome_text_channel")
    if text_channel_id:
        channel = guild.get_channel(text_channel_id)
        if channel:
            await channel.send(f"<a:caarrow:1433143710094196997> Bienvenue {member.mention} sur **{guild.name}**\n<a:caarrow:1433143710094196997> Nous sommes maintenant **{guild.member_count}** membres !")
    
    # Track invites
    try:
        new_invites = {inv.code: inv.uses for inv in await guild.invites()}
        old_invites = data.get("invites", {}).get(gid, {})
        
        inviter = None
        for code, uses in new_invites.items():
            if old_invites.get(code, 0) < uses:
                inviter_inv = discord.utils.get(await guild.invites(), code=code)
                if inviter_inv and inviter_inv.inviter:
                    inviter = inviter_inv.inviter
                break
        
        data["invites"][gid] = new_invites
        save_data(data)
        
        if inviter:
            data.setdefault("user_invites", {}).setdefault(gid, {})
            uid = str(inviter.id)
            data["user_invites"][gid][uid] = data["user_invites"][gid].get(uid, 0) + 1
            invite_count = data["user_invites"][gid][uid]
            save_data(data)
            
            inv_channel_id = get_conf(guild.id, "invitation_channel")
            if inv_channel_id:
                inv_channel = guild.get_channel(inv_channel_id)
                if inv_channel:
                    await inv_channel.send(f"🎉 {member.mention} a été invité par {inviter.mention} qui a maintenant **{invite_count}** invitation(s) !")
            
            # Role rewards
            roles_invites = data.get("roles_invites", {}).get(gid, {})
            for count_str, role_id in roles_invites.items():
                if invite_count >= int(count_str):
                    role = guild.get_role(role_id)
                    if role and role not in inviter.roles:
                        await inviter.add_roles(role)
    except Exception as e:
        print(f"Erreur invitations: {e}")

@bot.event
async def on_member_remove(member):
    guild = member.guild
    
    # Leave embed
    embed_channel_id = get_conf(guild.id, "leave_embed_channel")
    if embed_channel_id:
        channel = guild.get_channel(embed_channel_id)
        if channel:
            e = discord.Embed(title="👋 Au revoir", description=f"**{member.display_name}** a quitté le serveur.", color=0xe74c3c)
            e.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=e)
    
    # Leave text
    text_channel_id = get_conf(guild.id, "leave_text_channel")
    if text_channel_id:
        channel = guild.get_channel(text_channel_id)
        if channel:
            await channel.send(f"😢 **{member.display_name}** a quitté le serveur.")

# === LINK MANAGEMENT ===
@bot.command(name="allowlink")
@commands.has_permissions(manage_guild=True)
async def allow_link(ctx, channel: discord.TextChannel):
    gid = str(ctx.guild.id)
    data.setdefault("allowed_links", {}).setdefault(gid, [])
    if channel.id not in data["allowed_links"][gid]:
        data["allowed_links"][gid].append(channel.id)
        save_data(data)
        await ctx.send(f"✅ Liens autorisés dans {channel.mention}")
    else:
        await ctx.send(f"ℹ️ Liens déjà autorisés dans {channel.mention}")

@bot.command(name="disallowlink")
@commands.has_permissions(manage_guild=True)
async def disallow_link(ctx, channel: discord.TextChannel):
    gid = str(ctx.guild.id)
    if gid in data.get("allowed_links", {}) and channel.id in data["allowed_links"][gid]:
        data["allowed_links"][gid].remove(channel.id)
        save_data(data)
        await ctx.send(f"✅ Liens bloqués dans {channel.mention}")
    else:
        await ctx.send(f"ℹ️ Liens déjà bloqués dans {channel.mention}")

# === TICKETS ===
class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        close_btn = Button(label="Fermer", style=discord.ButtonStyle.red, emoji="🔒")
        close_btn.callback = self.close_ticket
        self.add_item(close_btn)
    
    async def close_ticket(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔒 Ticket fermé dans 5s...", ephemeral=True)
        await asyncio.sleep(5)
        await interaction.channel.delete()

@bot.command(name="ticket")
async def ticket(ctx):
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        ctx.guild.me: discord.PermissionOverwrite(read_messages=True)
    }
    channel = await ctx.guild.create_text_channel(name=f"ticket-{ctx.author.name}", overwrites=overwrites)
    e = discord.Embed(title="🎫 Ticket ouvert", description=f"{ctx.author.mention}, explique ton problème.", color=0x2ecc71)
    await channel.send(embed=e, view=TicketView())
    await ctx.send(f"✅ Ticket créé: {channel.mention}", delete_after=5)

@bot.command(name="ticketpanel")
@commands.has_permissions(manage_guild=True)
async def ticket_panel(ctx):
    e = discord.Embed(title="🎫 Support", description="Réagis avec 🎫 pour ouvrir un ticket !", color=0x2ecc71)
    msg = await ctx.send(embed=e)
    await msg.add_reaction("🎫")
    set_conf(ctx.guild.id, "ticket_panel", msg.id)
    await ctx.send("✅ Panel créé !")

@bot.command(name="close")
async def close_ticket(ctx):
    if ctx.channel.name.startswith("ticket-"):
        await ctx.send("🔒 Fermeture dans 5s...")
        await asyncio.sleep(5)
        await ctx.channel.delete()
    else:
        await ctx.send("❌ Commande réservée aux tickets")

# === VOCAL TEMPORAIRE ===
@bot.command(name="createvoc")
@commands.has_permissions(manage_guild=True)
async def create_voc(ctx):
    voc = await ctx.guild.create_voice_channel(name="🔊 Créer un voc", category=ctx.channel.category)
    set_conf(ctx.guild.id, "voc_trigger_channel", voc.id)
    await ctx.send(f"✅ Vocal trigger créé: {voc.mention}")

@bot.command(name="setupvoc")
@commands.has_permissions(manage_guild=True)
async def setup_voc(ctx, channel: discord.VoiceChannel):
    set_conf(ctx.guild.id, "voc_trigger_channel", channel.id)
    await channel.edit(name="🔊 Créer un voc")
    await ctx.send(f"✅ Vocal trigger: {channel.mention}")

@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild
    gid = str(guild.id)
    
    # Create temp vocal
    trigger_id = get_conf(guild.id, "voc_trigger_channel")
    if trigger_id and after.channel and after.channel.id == trigger_id:
        voc = await guild.create_voice_channel(name=f"🔊 {member.display_name}", category=after.channel.category)
        data.setdefault("temp_vocs", {})[str(voc.id)] = {"owner": member.id, "created": datetime.datetime.utcnow().isoformat()}
        save_data(data)
        await member.move_to(voc)
    
    # Delete empty temp vocal
    if before.channel:
        if str(before.channel.id) in data.get("temp_vocs", {}) and len(before.channel.members) == 0:
            await before.channel.delete()
            del data["temp_vocs"][str(before.channel.id)]
            save_data(data)

# === RUN BOT ===
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("❌ ERREUR: Variable DISCORD_TOKEN manquante !")
        exit(1)
    
    print("🚀 Démarrage de Hoshikuzu...")
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ Token invalide !")
    except Exception as e:
        print(f"❌ Erreur: {e}")