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

@bot.event
async def on_ready():
    print(f"✨ Bot connecté: {bot.user} 🌸")
    await bot.change_presence(activity=discord.Game(name="✨ +help 💖"))
    check_giveaways.start()
    
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            data["invites"][str(guild.id)] = {inv.code: inv.uses for inv in invites}
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
    
    # Welcome text
    wt = get_conf(member.guild.id, "welcome_text_channel")
    if wt:
        ch = member.guild.get_channel(wt)
        if ch:
            messages = [
                f"✨ Bienvenue {member.mention} ! Content de te voir ici ! 🌸",
                f"🎀 {member.mention} a rejoint ! Bienvenue ! 💖",
                f"🌸 {member.mention} est arrivé ! Amuse-toi bien ! ✨",
            ]
            await ch.send(random.choice(messages))

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

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return
    
    gid = str(message.guild.id)
    
    # Link filter
    allowed_channels = data.get("allowed_links", {}).get(gid, [])
    if message.channel.id not in allowed_channels:
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        if re.search(url_pattern, message.content):
            await message.delete()
            await message.channel.send(f"❌ {message.author.mention}, les liens sont interdits ici !", delete_after=5)
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

# === HELP ===
@bot.command(name="help")
async def help_cmd(ctx):
    e = discord.Embed(title="🌸 Commandes Hoshimi Kawaii 🌸", color=0xff69b4)
    e.set_thumbnail(url="https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExc3o4NGljeWVlcXh2Y3FtajF4M2pndTEyeWh1ZXR3YXVhMG9tZjkydCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Xl0oVz3eb9mfu/giphy.gif")
    
    e.add_field(name="⚙️ Configuration", value=(
        "`+config` Configuration actuelle\n"
        "`+setwelcome #channel <embed/text>` Message de bienvenue\n"
        "`+setleave #channel <embed/text>` Message de départ\n"
        "`+setlogs #channel` Salon de logs\n"
        "`+setinvitation #channel` Logs invitations\n"
        "`+setsuggestion #channel` Salon suggestions\n"
        "`+rolejoin @role` Rôle automatique à l'arrivée"
    ), inline=False)
    
    e.add_field(name="👥 Invitations", value=(
        "`+roleinvite <nb> @role` Rôle par invitations\n"
        "`+invites [@user]` Voir les invitations"
    ), inline=False)
    
    e.add_field(name="🛡️ Modération", value=(
        "`+warn @user <raison>` Avertir\n"
        "`+warnings @user` Voir avertissements\n"
        "`+clearwarns @user` Effacer avertissements\n"
        "`+kick @user <raison>` Expulser\n"
        "`+ban @user <raison>` Bannir\n"
        "`+mute @user <durée>` Mute\n"
        "`+unmute @user` Unmute\n"
        "`+clear <nombre>` Supprimer messages\n"
        "`+lock` / `+unlock` Verrouiller salon\n"
        "`+slowmode <secondes>` Mode lent"
    ), inline=False)
    
    e.add_field(name="💰 Économie", value=(
        "`+balance [@user]` Voir son argent\n"
        "`+daily` Bonus journalier\n"
        "`+pay @user <montant>` Donner argent\n"
        "`+shop` Boutique\n"
        "`+buy <item>` Acheter un item"
    ), inline=False)
    
    e.add_field(name="🎁 Giveaways", value=(
        "`+gstart <durée> <prix>` Créer giveaway\n"
        "`+gend <message_id>` Terminer giveaway\n"
        "`+greroll <message_id>` Retirer gagnant"
    ), inline=False)
    
    e.add_field(name="🎫 Tickets", value=(
        "`+ticket` Créer ticket\n"
        "`+ticketpanel` Panel tickets\n"
        "`+close` Fermer ticket"
    ), inline=False)
    
    e.add_field(name="🎤 Vocaux", value=(
        "`+createvoc` Créer vocal trigger\n"
        "`+setupvoc #channel` Configurer vocal"
    ), inline=False)
    
    e.add_field(name="🔗 Liens", value=(
        "`+allowlink #channel` Autoriser liens\n"
        "`+disallowlink #channel` Bloquer liens"
    ), inline=False)
    
    e.add_field(name="🤖 Auto-réponses", value=(
        "`+addresponse <trigger> <réponse>` Ajouter\n"
        "`+listresponses` Voir toutes\n"
        "`+delresponse <trigger>` Supprimer"
    ), inline=False)
    
    e.add_field(name="💡 Suggestions", value=(
        "`+suggest <suggestion>` Faire suggestion\n"
        "`+acceptsugg <id>` Accepter\n"
        "`+denysugg <id>` Refuser"
    ), inline=False)
    
    e.add_field(name="🎲 Fun", value=(
        "`+8ball <question>` Boule magique\n"
        "`+coinflip` Pile ou face\n"
        "`+dice` Lancer dé\n"
        "`+love @user1 @user2` % d'amour\n"
        "`+meme` Meme"
    ), inline=False)
    
    e.add_field(name="ℹ️ Utilitaire", value=(
        "`+serverinfo` Infos serveur\n"
        "`+userinfo [@user]` Infos utilisateur\n"
        "`+avatar [@user]` Avatar\n"
        "`+poll <question>` Sondage\n"
        "`+say <message>` Faire parler le bot\n"
        "`+embed <message>` Message en embed\n"
        "`+rules` Afficher les règles"
    ), inline=False)
    
    e.set_footer(text="✨ Bot kawaii créé avec amour 💖", icon_url=ctx.bot.user.avatar.url if ctx.bot.user.avatar else None)
    await ctx.send(embed=e)

# === CONFIG ===
@bot.command(name="config")
@commands.has_permissions(manage_guild=True)
async def config_cmd(ctx):
    conf = data.get("config", {}).get(str(ctx.guild.id), {})
    e = discord.Embed(
        title="⚙️ Configuration",
        description="🌸 Voici la configuration actuelle du serveur",
        color=0xff69b4
    )
    
    config_found = False
    for key in ["logs_channel", "welcome_embed_channel", "welcome_text_channel", 
                "leave_embed_channel", "leave_text_channel", "invitation_channel", 
                "suggestion_channel", "voc_trigger_channel", "auto_role"]:
        val = conf.get(key)
        if val:
            config_found = True
            name = key.replace("_channel", "").replace("_", " ").title()
            emoji = "🎀"
            if "role" in key:
                e.add_field(name=f"{emoji} {name}", value=f"<@&{val}>", inline=False)
            else:
                e.add_field(name=f"{emoji} {name}", value=f"<#{val}>", inline=False)
    
    if not config_found:
        e.description = "✨ Aucune configuration trouvée ! Configure le bot avec les commandes disponibles."
    
    e.set_footer(text="✨ Configuration du serveur 💖")
    await ctx.send(embed=e)

# === CONFIGURATION COMMANDS ===
@bot.command(name="rolejoin")
@commands.has_permissions(manage_roles=True)
async def role_join(ctx, role: discord.Role):
    set_conf(ctx.guild.id, "auto_role", role.id)
    e = discord.Embed(title="✅ Rôle Automatique Configuré", color=0xff69b4)
    e.description = f"✨ Les nouveaux membres recevront automatiquement le rôle {role.mention} ! 💖"
    e.set_footer(text="Rôle automatique configuré avec succès")
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
    e = discord.Embed(title="⚠️ Avertissement", color=0xff69b4)
    e.add_field(name="💫 Membre", value=member.mention, inline=True)
    e.add_field(name="📝 Raison", value=reason, inline=True)
    e.add_field(name="📊 Total", value=f"**{warn_count}** avertissement(s) 🌸", inline=True)
    e.set_footer(text="✨ Sois plus gentil(le) la prochaine fois 💖")
    await ctx.send(embed=e)
    
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
        e.add_field(
            name=f"📋 #{i}",
            value=f"**💭 Raison:** {w['reason']}\n**📅 Date:** {w['date'][:10]}",
            inline=False
        )
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

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "Aucune raison"):
    await member.ban(reason=reason)
    e = discord.Embed(title="🔨 Membre banni", color=0xff1493)
    e.add_field(name="💫 Membre", value=member.mention)
    e.add_field(name="💭 Raison", value=reason)
    e.set_footer(text="✨ Au revoir 👋💔")
    await ctx.send(embed=e)

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def mute(ctx, member: discord.Member, duration: str = "10m"):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if not muted_role:
        muted_role = await ctx.guild.create_role(name="Muted", color=0xff69b4)
        for channel in ctx.guild.channels:
            await channel.set_permissions(muted_role, send_messages=False, speak=False)
    
    await member.add_roles(muted_role)
    
    time_convert = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    duration_seconds = int(duration[:-1]) * time_convert.get(duration[-1], 60)
    
    await ctx.send(f"🔇 {member.mention} a été mute pour **{duration}** ! 🤫💖")
    
    await asyncio.sleep(duration_seconds)
    await member.remove_roles(muted_role)
    await ctx.send(f"🔊 {member.mention} peut parler à nouveau ! 💖")

@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        await ctx.send(f"🔊 {member.mention} peut parler à nouveau ! 💖")
    else:
        await ctx.send(f"🌸 {member.mention} n'est pas mute ! ✨")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🗑️ **{amount}** messages supprimés ! 💖")
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 Salon verrouillé ! 💖")

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 Salon déverrouillé ! 💖")

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    await ctx.send(f"⏱️ Mode lent: **{seconds}**s ! 💖")

# === ECONOMY ===
@bot.command(name="balance", aliases=["bal"])
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    money = data.get("economy", {}).get(gid, {}).get(uid, 0)
    
    e = discord.Embed(title=f"💰 Balance de {member.display_name}", color=0xff69b4)
    e.add_field(name="💎 Argent", value=f"**{money}** 💵 ✨")
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text="✨ Économie 💖")
    await ctx.send(embed=e)

@bot.command(name="daily")
async def daily(ctx):
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    
    data.setdefault("economy", {}).setdefault(gid, {})
    data["economy"][gid][uid] = data["economy"][gid].get(uid, 0) + 100
    save_data(data)
    
    await ctx.send(f"💰 {ctx.author.mention} a reçu **100** 💵 ! Reviens demain ! 🎁💖")

@bot.command(name="pay")
async def pay(ctx, member: discord.Member, amount: int):
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    target_uid = str(member.id)
    
    data.setdefault("economy", {}).setdefault(gid, {})
    
    if data["economy"][gid].get(uid, 0) < amount:
        await ctx.send("❌ Tu n'as pas assez d'argent ! 💔")
        return
    
    data["economy"][gid][uid] = data["economy"][gid].get(uid, 0) - amount
    data["economy"][gid][target_uid] = data["economy"][gid].get(target_uid, 0) + amount
    save_data(data)
    
    await ctx.send(f"💸 {ctx.author.mention} a donné **{amount}** 💵 à {member.mention} ! 💖")

# === GIVEAWAYS ===
@bot.command(name="gstart")
@commands.has_permissions(manage_guild=True)
async def gstart(ctx, duration: str, *, prize: str):
    time_convert = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    duration_seconds = int(duration[:-1]) * time_convert.get(duration[-1], 60)
    
    end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=duration_seconds)
    
    e = discord.Embed(title="🎁 GIVEAWAY 🎁", color=0xff69b4)
    e.description = f"**🎀 Prix:** {prize}\n**⏰ Durée:** {duration}\n**💖 Réagis avec 🎉 pour participer !**"
    e.set_footer(text=f"✨ Se termine le {end_time.strftime('%d/%m/%Y à %H:%M')} 💖")
    
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

@bot.command(name="gend")
@commands.has_permissions(manage_guild=True)
async def gend(ctx, message_id: int):
    msg_id = str(message_id)
    if msg_id not in data.get("giveaways", {}):
        await ctx.send("❌ Giveaway introuvable ! 💔")
        return
    
    gdata = data["giveaways"][msg_id]
    try:
        msg = await ctx.channel.fetch_message(message_id)
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        if reaction:
            users = [user async for user in reaction.users() if not user.bot]
            if users:
                winner = random.choice(users)
                e = discord.Embed(title="🎉 Giveaway Terminé !", color=0xff69b4)
                e.description = f"**🏆 Gagnant:** {winner.mention}\n**🎀 Prix:** {gdata['prize']}\n\n💖 Félicitations !"
                await ctx.send(embed=e)
            else:
                await ctx.send("❌ Aucun participant ! 💔")
        
        del data["giveaways"][msg_id]
        save_data(data)
    except:
        await ctx.send("❌ Erreur lors de la fin du giveaway ! 💔")

@bot.command(name="greroll")
@commands.has_permissions(manage_guild=True)
async def greroll(ctx, message_id: int):
    try:
        msg = await ctx.channel.fetch_message(message_id)
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        if reaction:
            users = [user async for user in reaction.users() if not user.bot]
            if users:
                winner = random.choice(users)
                await ctx.send(f"🎉 Nouveau gagnant : {winner.mention} ! Félicitations ! 💖")
            else:
                await ctx.send("❌ Aucun participant ! 💔")
        else:
            await ctx.send("❌ Aucune réaction trouvée ! 💔")
    except Exception as e:
        await ctx.send(f"❌ Message introuvable ! 💔")

# === AUTO RESPONSES ===
@bot.command(name="addresponse")
@commands.has_permissions(manage_guild=True)
async def add_response(ctx, trigger: str, *, response: str):
    gid = str(ctx.guild.id)
    data.setdefault("auto_responses", {}).setdefault(gid, {})[trigger.lower()] = response
    save_data(data)
    
    e = discord.Embed(title="✅ Auto-réponse Ajoutée", color=0xff69b4)
    e.add_field(name="🎀 Trigger", value=f"```{trigger}```", inline=False)
    e.add_field(name="💬 Réponse", value=f"```{response}```", inline=False)
    e.set_footer(text="✨ Le bot répondra automatiquement 💖")
    await ctx.send(embed=e)

@bot.command(name="listresponses")
async def list_responses(ctx):
    gid = str(ctx.guild.id)
    responses = data.get("auto_responses", {}).get(gid, {})
    
    if not responses:
        await ctx.send("🌸 Aucune auto-réponse configurée ! 💕")
        return
    
    e = discord.Embed(title="🤖 Auto-réponses", color=0xff69b4)
    
    for i, (trigger, response) in enumerate(responses.items(), 1):
        e.add_field(
            name=f"#{i} Trigger: `{trigger}`",
            value=f"**Réponse:** {response}",
            inline=False
        )
    
    e.set_footer(text=f"✨ {len(responses)} réponse(s) 💖")
    await ctx.send(embed=e)

@bot.command(name="delresponse")
@commands.has_permissions(manage_guild=True)
async def del_response(ctx, trigger: str):
    gid = str(ctx.guild.id)
    if gid in data.get("auto_responses", {}) and trigger.lower() in data["auto_responses"][gid]:
        del data["auto_responses"][gid][trigger.lower()]
        save_data(data)
        await ctx.send(f"✅ Auto-réponse pour `{trigger}` supprimée ! 💖")
    else:
        await ctx.send(f"❌ Aucune auto-réponse trouvée pour `{trigger}` ! 💔")

# === SUGGESTIONS ===
@bot.command(name="suggest")
async def suggest(ctx, *, suggestion: str):
    sugg_channel_id = get_conf(ctx.guild.id, "suggestion_channel")
    if not sugg_channel_id:
        await ctx.send("❌ Aucun salon de suggestions configuré ! 💔")
        return
    
    sugg_channel = ctx.guild.get_channel(sugg_channel_id)
    if not sugg_channel:
        await ctx.send("❌ Salon de suggestions introuvable ! 💔")
        return
    
    gid = str(ctx.guild.id)
    data.setdefault("suggestions", {}).setdefault(gid, {})
    sugg_id = len(data["suggestions"][gid]) + 1
    
    e = discord.Embed(title=f"💡 Suggestion #{sugg_id}", description=suggestion, color=0xff69b4)
    e.add_field(name="👤 Suggéré par", value=ctx.author.mention, inline=True)
    e.add_field(name="🆔 ID", value=f"**#{sugg_id}**", inline=True)
    e.set_thumbnail(url=ctx.author.display_avatar.url)
    e.set_footer(text=f"✨ Vote avec 👍 ou 👎 ! 💖")
    
    msg = await sugg_channel.send(embed=e)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    
    data["suggestions"][gid][str(sugg_id)] = {
        "author": str(ctx.author.id),
        "suggestion": suggestion,
        "message_id": msg.id,
        "status": "pending"
    }
    save_data(data)
    
    await ctx.send(f"✅ Ta suggestion a été envoyée dans {sugg_channel.mention} ! (ID: #{sugg_id}) 💖")

@bot.command(name="acceptsugg")
@commands.has_permissions(manage_guild=True)
async def accept_sugg(ctx, sugg_id: int):
    gid = str(ctx.guild.id)
    if str(sugg_id) not in data.get("suggestions", {}).get(gid, {}):
        await ctx.send(f"❌ Suggestion #{sugg_id} introuvable ! 💔")
        return
    
    sugg_data = data["suggestions"][gid][str(sugg_id)]
    sugg_data["status"] = "accepted"
    save_data(data)
    
    sugg_channel_id = get_conf(ctx.guild.id, "suggestion_channel")
    if sugg_channel_id:
        sugg_channel = ctx.guild.get_channel(sugg_channel_id)
        if sugg_channel:
            try:
                msg = await sugg_channel.fetch_message(sugg_data["message_id"])
                e = msg.embeds[0]
                e.color = 0x00ff00
                e.title = f"✅ Suggestion Acceptée #{sugg_id}"
                e.add_field(name="🎉 Statut", value="**ACCEPTÉE !** 🎊", inline=False)
                await msg.edit(embed=e)
            except:
                pass
    
    await ctx.send(f"✅ Suggestion #{sugg_id} acceptée ! 💖")

@bot.command(name="denysugg")
@commands.has_permissions(manage_guild=True)
async def deny_sugg(ctx, sugg_id: int):
    gid = str(ctx.guild.id)
    if str(sugg_id) not in data.get("suggestions", {}).get(gid, {}):
        await ctx.send(f"❌ Suggestion #{sugg_id} introuvable ! 💔")
        return
    
    sugg_data = data["suggestions"][gid][str(sugg_id)]
    sugg_data["status"] = "denied"
    save_data(data)
    
    sugg_channel_id = get_conf(ctx.guild.id, "suggestion_channel")
    if sugg_channel_id:
        sugg_channel = ctx.guild.get_channel(sugg_channel_id)
        if sugg_channel:
            try:
                msg = await sugg_channel.fetch_message(sugg_data["message_id"])
                e = msg.embeds[0]
                e.color = 0xff0000
                e.title = f"❌ Suggestion Refusée #{sugg_id}"
                e.add_field(name="😢 Statut", value="**REFUSÉE** 💔", inline=False)
                await msg.edit(embed=e)
            except:
                pass
    
    await ctx.send(f"❌ Suggestion #{sugg_id} refusée 💔")

# === FUN COMMANDS ===
@bot.command(name="8ball")
async def eight_ball(ctx, *, question: str):
    responses = [
        "Oui absolument ! 💖",
        "C'est certain ! 🌸",
        "Sans aucun doute ! 🎀",
        "Oui définitivement ! 💗",
        "Tu peux compter dessus ! 💕",
        "Peut-être... 🤔",
        "Difficile à dire... 💭",
        "Mieux vaut ne pas te le dire maintenant ! 🙈",
        "Je ne peux pas prédire ça ! 🔮",
        "Repose ta question ! 🌸",
        "Non ! 💔",
        "Mes sources disent non... 😢",
        "Peu probable ! 🌸",
        "N'y compte pas ! 💭",
        "Non définitivement ! 💔"
    ]
    
    e = discord.Embed(title="🔮 Boule Magique", color=0xff69b4)
    e.add_field(name="💭 Question", value=f"```{question}```", inline=False)
    e.add_field(name="🌟 Réponse", value=f"**{random.choice(responses)}**", inline=False)
    e.set_footer(text="✨ La boule magique a parlé ! 💖")
    await ctx.send(embed=e)

@bot.command(name="coinflip")
async def coinflip(ctx):
    result = random.choice(["Pile", "Face"])
    emoji = "🪙" if result == "Pile" else "👑"
    
    e = discord.Embed(title="🪙 Pile ou Face", color=0xff69b4)
    e.description = f"**{emoji} {result} ! {emoji}**"
    e.set_footer(text="✨ Lancer de pièce 💖")
    await ctx.send(embed=e)

@bot.command(name="dice")
async def dice(ctx):
    result = random.randint(1, 6)
    dice_emojis = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    
    e = discord.Embed(title="🎲 Lancer de Dé", color=0xff69b4)
    e.description = f"**{dice_emojis[result-1]} {result} {dice_emojis[result-1]}**"
    e.set_footer(text="✨ Dé lancé ! 💖")
    await ctx.send(embed=e)

@bot.command(name="love")
async def love(ctx, user1: discord.Member, user2: discord.Member = None):
    if user2 is None:
        user2 = user1
        user1 = ctx.author
    
    love_percent = random.randint(0, 100)
    
    if love_percent < 20:
        message = "Aucune compatibilité... 💔"
        color = 0x808080
    elif love_percent < 40:
        message = "Pas vraiment compatibles... 💔"
        color = 0xff6347
    elif love_percent < 60:
        message = "Assez compatibles ! 💕"
        color = 0xffa500
    elif love_percent < 80:
        message = "Très compatibles ! 💖"
        color = 0xff69b4
    else:
        message = "PARFAITEMENT COMPATIBLES ! 💖💕"
        color = 0xff1493
    
    hearts = "💖" * (love_percent // 20)
    bar = "█" * (love_percent // 10) + "░" * (10 - love_percent // 10)
    
    e = discord.Embed(title="💕 Calculateur d'Amour 💕", color=color)
    e.add_field(name="💑 Couple", value=f"{user1.mention} 💕 {user2.mention}", inline=False)
    e.add_field(name="💖 % d'Amour", value=f"**{love_percent}%** {hearts}", inline=False)
    e.add_field(name="📊 Barre", value=f"`{bar}` {love_percent}%", inline=False)
    e.add_field(name="💭 Verdict", value=f"**{message}**", inline=False)
    e.set_footer(text="✨ Calculateur d'amour 💖")
    await ctx.send(embed=e)

@bot.command(name="meme")
async def meme(ctx):
    meme_messages = [
        "Quand tu te réveilles et que c'est déjà l'après-midi 😴",
        "Quand tu vois un chien trop mignon 🐶💖",
        "Moi en train d'étudier VS Moi en train de procrastiner 📚💤",
        "Quand ta pizza arrive enfin 🍕🎉",
        "Moi quand je vois quelque chose de kawaii 😍",
        "POV: Tu essaies d'être productif 💻😴",
        "Quand tu entends ton plat préféré 🍜👂",
        "Moi après 5 minutes d'exercice 💪😵",
        "Quand quelqu'un dit qu'il n'aime pas les animaux 😱💔",
        "Moi en train de faire semblant de comprendre 🤔"
    ]
    
    e = discord.Embed(title="😂 Meme", description=random.choice(meme_messages), color=0xff69b4)
    e.set_footer(text="✨ Meme généré ! 💖")
    await ctx.send(embed=e)

# === UTILITY ===
@bot.command(name="rules")
@commands.has_permissions(manage_guild=True)
async def rules(ctx):
    e = discord.Embed(
        title="📜✨ Règles du Serveur ✨📜",
        description="🌸 Voici les règles à respecter pour garder une bonne ambiance ! 💖",
        color=0xff69b4
    )
    e.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    
    e.add_field(
        name="1️⃣ 🌸 Respect",
        value="Sois respectueux envers tous les membres ! Pas d'insultes, de harcèlement ou de discrimination.",
        inline=False
    )
    
    e.add_field(
        name="2️⃣ 💬 Spam",
        value="Ne spam pas les salons ! Évite les messages répétitifs et les mentions abusives.",
        inline=False
    )
    
    e.add_field(
        name="3️⃣ 🔞 Contenu",
        value="Pas de contenu NSFW, violent ou inapproprié. Garde le serveur family-friendly !",
        inline=False
    )
    
    e.add_field(
        name="4️⃣ 📢 Publicité",
        value="Pas de publicité sans autorisation ! Ne partage pas d'invitations Discord non autorisées.",
        inline=False
    )
    
    e.add_field(
        name="5️⃣ 🎭 Pseudonyme",
        value="Utilise un pseudo approprié et mentionnable. Évite les pseudos offensants.",
        inline=False
    )
    
    e.add_field(
        name="6️⃣ 🎤 Vocal",
        value="Respecte les autres en vocal ! Pas de musique forte ou de bruits parasites.",
        inline=False
    )
    
    e.add_field(
        name="7️⃣ ⚠️ Staff",
        value="Écoute et respecte les décisions du staff. En cas de problème, contacte un modérateur.",
        inline=False
    )
    
    e.add_field(
        name="8️⃣ 💖 Amusement",
        value="Amuse-toi et profite du serveur ! On est là pour passer un bon moment ensemble ! 🌸",
        inline=False
    )
    
    e.set_footer(text="✨ En rejoignant ce serveur, tu acceptes ces règles 💖", icon_url=ctx.bot.user.avatar.url if ctx.bot.user.avatar else None)
    e.set_image(url="https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExc3o4NGljeWVlcXh2Y3FtajF4M2pndTEyeWh1ZXR3YXVhMG9tZjkydCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/Xl0oVz3eb9mfu/giphy.gif")
    
    await ctx.send(embed=e)
