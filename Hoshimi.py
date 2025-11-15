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

# === KAWAII DATA ===
KAWAII_COLORS = [0xff69b4, 0xff1493, 0xffc0cb, 0xffb6c1, 0xff69b4]
KAWAII_EMOJIS = ["💖", "✨", "🌸", "🎀", "💕", "🌺", "⭐", "💗", "🦄", "🌈", "🧁", "🍰", "🎉", "💫", "🌟", "🍓", "🌷", "🦋", "🎨", "🎪"]

def random_kawaii_color():
    return random.choice(KAWAII_COLORS)

def random_kawaii_emojis(count=3):
    return " ".join(random.sample(KAWAII_EMOJIS, min(count, len(KAWAII_EMOJIS))))

# === Bot Init ===
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="+", intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"✨💖🌸 Bot ultra kawaii connecté: {bot.user} 🌸💖✨")
    await bot.change_presence(activity=discord.Game(name="✨💖 hoshimi ultra kawaii | +help 💖✨"))
    check_giveaways.start()
    
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            data["invites"][str(guild.id)] = {inv.code: inv.uses for inv in invites}
            save_data(data)
        except:
            pass

# === KAWAII EVENTS ===
@bot.event
async def on_member_join(member):
    # Welcome embed
    wc = get_conf(member.guild.id, "welcome_embed_channel")
    if wc:
        ch = member.guild.get_channel(wc)
        if ch:
            e = discord.Embed(
                title=f"💖✨🌸 BIENVENUE {member.display_name.upper()} ! 🌸✨💖",
                description=f"🎀 Ohayō {member.mention} ! Tu es la **{member.guild.member_count}ème** personne ultra kawaii ! 💕\n\n🌟 Nous sommes tellement heureux de t'accueillir dans notre famille mignonne ! ✨\n\n🌈 Amuse-toi bien et sois toujours aussi adorable ! (◕‿◕)♡",
                color=random_kawaii_color()
            )
            e.set_thumbnail(url=member.display_avatar.url)
            e.set_image(url="https://i.imgur.com/KOaXSQZ.gif")
            e.add_field(name="💫 Membre Kawaii", value=member.mention, inline=True)
            e.add_field(name="🎉 Membres Total", value=f"**{member.guild.member_count}** personnes mignonnes ! 💖", inline=True)
            e.set_footer(text=f"✨💖 {member.guild.name} t'aime déjà ! 💖✨", icon_url=member.guild.icon.url if member.guild.icon else None)
            await ch.send(f"🎊💕✨ {member.mention} ✨💕🎊", embed=e)
    
    # Welcome text
    wt = get_conf(member.guild.id, "welcome_text_channel")
    if wt:
        ch = member.guild.get_channel(wt)
        if ch:
            messages = [
                f"💖✨ NYA NYA ! Bienvenue {member.mention} ! Tu es trop kawaii pour ce serveur ! 🌸💕",
                f"🎀💫 YATTA ! {member.mention} est arrivé(e) ! On va s'amuser comme des fous ! (◕‿◕)♡ 🌟",
                f"🌈💖 SUGOI ! {member.mention} a rejoint la famille kawaii ! Prépare-toi à une overdose de mignonnerie ! ✨🎉",
                f"🌸💕 Ohayō {member.mention} ! Bienvenue dans le serveur le plus adorable de l'univers ! 🦄✨"
            ]
            await ch.send(random.choice(messages))

@bot.event
async def on_member_remove(member):
    # Leave embed
    lc = get_conf(member.guild.id, "leave_embed_channel")
    if lc:
        ch = member.guild.get_channel(lc)
        if ch:
            e = discord.Embed(
                title=f"💔✨ AU REVOIR {member.display_name.upper()}... ✨💔",
                description=f"🌸 {member.mention} nous a quitté... Notre serveur est moins kawaii maintenant... (｡•́︿•̀｡) 💔\n\n🌟 On espère te revoir bientôt, personne adorable ! ✨",
                color=0x9370db
            )
            e.set_thumbnail(url=member.display_avatar.url)
            e.add_field(name="👋 Membre Parti", value=member.mention, inline=True)
            e.add_field(name="😢 Membres Restants", value=f"**{member.guild.member_count}** 💔", inline=True)
            e.set_footer(text=f"✨ Tu vas nous manquer ! 💔", icon_url=member.guild.icon.url if member.guild.icon else None)
            await ch.send(embed=e)

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return
    
    gid = str(message.guild.id)
    
    # KAWAII AUTO REACTIONS (15% de chance)
    if random.randint(1, 100) <= 15:
        await message.add_reaction(random.choice(KAWAII_EMOJIS))
    
    # Link filter
    allowed_channels = data.get("allowed_links", {}).get(gid, [])
    if message.channel.id not in allowed_channels:
        url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        if re.search(url_pattern, message.content):
            await message.delete()
            await message.channel.send(f"❌🌸✨ {message.author.mention}, les liens sont interdits ici ! Sois kawaii ! ✨🌸❌", delete_after=5)
            return
    
    # Auto responses
    auto_resp = data.get("auto_responses", {}).get(gid, {})
    for trigger, response in auto_resp.items():
        if trigger.lower() in message.content.lower():
            await message.channel.send(f"✨💖 {response} 💖✨")
            break
    
    await bot.process_commands(message)

# === HELP ===
@bot.command(name="help")
async def help_cmd(ctx):
    e = discord.Embed(
        title="🌸✨💖 COMMANDES ULTRA KAWAII 💖✨🌸",
        description="🎀 Voici toutes les commandes mignonnes du bot le plus adorable ! (◕‿◕)♡ 🌟",
        color=random_kawaii_color()
    )
    e.set_thumbnail(url="https://i.imgur.com/9xPqm8L.gif")
    
    e.add_field(name=f"{random_kawaii_emojis(2)} ⚙️ Configuration Ultra Mignonne ⚙️", value=(
        "`+config` 📋✨ Configuration actuelle kawaii\n"
        "`+setwelcome #channel <embed/text>` 🎀💕 Bienvenue ultra mimi\n"
        "`+setleave #channel <embed/text>` 👋💔 Au revoir tristoune\n"
        "`+setlogs #channel` 📝🌸 Logs super kawaii\n"
        "`+setinvitation #channel` 💌✨ Logs invitations mignonnes\n"
        "`+setsuggestion #channel` 💡💖 Salon suggestions adorables"
    ), inline=False)
    
    e.add_field(name=f"{random_kawaii_emojis(2)} 👥 Invitations Mignonnes", value=(
        "`+roleinvite <nb> @role` 🎀💫 Rôle par invitations kawaii\n"
        "`+invites [@user]` 💌🌟 Voir invitations adorables"
    ), inline=False)
    
    e.add_field(name=f"{random_kawaii_emojis(2)} 🛡️ Modération Kawaii", value=(
        "`+warn @user <raison>` ⚠️💕 Avertir gentiment\n"
        "`+warnings @user` 📋🌸 Voir avertissements\n"
        "`+clearwarns @user` ✨💖 Effacer avertissements\n"
        "`+kick @user <raison>` 👢🌟 Expulser avec amour\n"
        "`+ban @user <raison>` 🔨💔 Bannir tristement\n"
        "`+mute @user <durée>` 🔇🎀 Mute mignon\n"
        "`+unmute @user` 🔊💕 Unmute joyeux\n"
        "`+clear <nombre>` 🗑️✨ Supprimer messages\n"
        "`+lock` / `+unlock` 🔒🌸 Verrouiller salon\n"
        "`+slowmode <secondes>` ⏱️💖 Mode lent kawaii"
    ), inline=False)
    
    e.add_field(name=f"{random_kawaii_emojis(2)} 💰 Économie Ultra Kawaii", value=(
        "`+balance [@user]` 💎✨ Voir son argent mignon\n"
        "`+daily` 🎁💖 Bonus journalier adorable\n"
        "`+pay @user <montant>` 💸🌟 Donner argent kawaii\n"
        "`+shop` 🏪💕 Boutique ultra cute\n"
        "`+buy <item>` 🛍️🌸 Acheter item mignon"
    ), inline=False)
    
    e.add_field(name=f"{random_kawaii_emojis(2)} 🎁 Giveaways Adorables", value=(
        "`+gstart <durée> <prix>` 🎉💖 Créer giveaway kawaii\n"
        "`+gend <message_id>` 🏁✨ Terminer giveaway\n"
        "`+greroll <message_id>` 🔄🌸 Retirer gagnant"
    ), inline=False)
    
    e.add_field(name=f"{random_kawaii_emojis(2)} 🎭 Rôles Réactions Kawaii", value=(
        "`+reactionrole` 🌈💕 Créer menu rôles mignon\n"
        "`+addrr <msg_id> <emoji> @role` ➕✨ Ajouter rôle kawaii"
    ), inline=False)
    
    e.add_field(name=f"{random_kawaii_emojis(2)} 🎫 Tickets Ultra Mignons", value=(
        "`+ticket` 🎟️💖 Créer ticket kawaii\n"
        "`+ticketpanel` 🎪✨ Panel tickets adorable\n"
        "`+close` 🚪🌸 Fermer ticket"
    ), inline=False)
    
    e.add_field(name=f"{random_kawaii_emojis(2)} 🎤 Vocaux Adorables", value=(
        "`+createvoc` 🎵💕 Créer vocal trigger mignon\n"
        "`+setupvoc #channel` ⚙️✨ Configurer vocal kawaii"
    ), inline=False)
    
    e.add_field(name=f"{random_kawaii_emojis(2)} 🔗 Liens Kawaii", value=(
        "`+allowlink #channel` ✅💖 Autoriser liens\n"
        "`+disallowlink #channel` ❌🌸 Bloquer liens"
    ), inline=False)
    
    e.add_field(name=f"{random_kawaii_emojis(2)} 🤖 Auto-réponses Ultra Mignonnes", value=(
        "`+addresponse <trigger> <réponse>` ➕💕 Ajouter réponse kawaii\n"
        "`+listresponses` 📋✨ Voir toutes les réponses\n"
        "`+delresponse <trigger>` 🗑️🌸 Supprimer réponse"
    ), inline=False)
    
    e.add_field(name=f"{random_kawaii_emojis(2)} 💡 Suggestions Adorables", value=(
        "`+suggest <suggestion>` 💭💖 Faire suggestion mignonne\n"
        "`+acceptsugg <id>` ✅✨ Accepter suggestion\n"
        "`+denysugg <id>` ❌🌸 Refuser suggestion"
    ), inline=False)
    
    e.add_field(name=f"{random_kawaii_emojis(2)} 🎲 Fun Ultra Kawaii", value=(
        "`+8ball <question>` 🔮💕 Boule magique adorable\n"
        "`+coinflip` 🪙✨ Pile ou face kawaii\n"
        "`+dice` 🎲🌸 Lancer dé mignon\n"
        "`+love @user1 @user2` 💕💖 % d'amour kawaii\n"
        "`+meme` 😂🌟 Meme ultra cute"
    ), inline=False)
    
    e.add_field(name=f"{random_kawaii_emojis(2)} ℹ️ Utilitaire Kawaii", value=(
        "`+serverinfo` 🏰💖 Infos serveur adorable\n"
        "`+userinfo [@user]` 👤✨ Infos utilisateur mignon\n"
        "`+avatar [@user]` 🖼️🌸 Avatar kawaii\n"
        "`+poll <question>` 📊💕 Sondage ultra cute"
    ), inline=False)
    
    e.set_footer(text="✨💖🌸 Bot ultra kawaii créé avec BEAUCOUP d'amour ! (◕‿◕)♡ 🌸💖✨", icon_url=ctx.bot.user.avatar.url if ctx.bot.user.avatar else None)
    await ctx.send(f"🎀✨💖 Voici toutes mes commandes mignonnes {ctx.author.mention} ! 💖✨🎀", embed=e)

# === CONFIG ===
@bot.command(name="config")
@commands.has_permissions(manage_guild=True)
async def config_cmd(ctx):
    conf = data.get("config", {}).get(str(ctx.guild.id), {})
    e = discord.Embed(
        title="⚙️✨💖 CONFIGURATION ULTRA KAWAII 💖✨⚙️",
        description="🌸 Voici toute la configuration mignonne de ton serveur adorable ! (◕‿◕)♡ 🌟",
        color=random_kawaii_color()
    )
    
    config_found = False
    for key in ["logs_channel", "welcome_embed_channel", "welcome_text_channel", 
                "leave_embed_channel", "leave_text_channel", "invitation_channel", 
                "suggestion_channel", "voc_trigger_channel", "auto_role"]:
        val = conf.get(key)
        if val:
            config_found = True
            name = key.replace("_channel", "").replace("_", " ").title()
            emoji = random.choice(KAWAII_EMOJIS)
            if "role" in key:
                e.add_field(name=f"{emoji} 🎀 {name} Kawaii", value=f"<@&{val}> ✨", inline=False)
            else:
                e.add_field(name=f"{emoji} 💫 {name} Mignon", value=f"<#{val}> 💖", inline=False)
    
    if not config_found:
        e.description = "🌸✨ Aucune configuration trouvée ! Configure-moi pour que je sois encore plus kawaii ! 💖🎀"
    
    e.set_footer(text="✨💕 Configuration ultra mignonne ! Nya~ 🌸💖")
    await ctx.send(embed=e)

# === CONFIGURATION COMMANDS ===
@bot.command(name="setwelcome")
@commands.has_permissions(manage_guild=True)
async def set_welcome(ctx, channel: discord.TextChannel, type: str = "embed"):
    if type.lower() == "embed":
        set_conf(ctx.guild.id, "welcome_embed_channel", channel.id)
        e = discord.Embed(title="✅🎀💖 Bienvenue Configurée ! 💖🎀✅", color=random_kawaii_color())
        e.description = f"🌸✨ La bienvenue kawaii (embed ultra mignon) a été configurée dans {channel.mention} ! (◕‿◕)♡ 💕"
        await ctx.send(embed=e)
    elif type.lower() == "text":
        set_conf(ctx.guild.id, "welcome_text_channel", channel.id)
        e = discord.Embed(title="✅🎀💖 Bienvenue Configurée ! 💖🎀✅", color=random_kawaii_color())
        e.description = f"🌸✨ La bienvenue kawaii (texte adorable) a été configurée dans {channel.mention} ! Yatta ! 💕"
        await ctx.send(embed=e)

@bot.command(name="setleave")
@commands.has_permissions(manage_guild=True)
async def set_leave(ctx, channel: discord.TextChannel, type: str = "embed"):
    if type.lower() == "embed":
        set_conf(ctx.guild.id, "leave_embed_channel", channel.id)
        e = discord.Embed(title="✅👋💔 Au Revoir Configuré ! 💔👋✅", color=random_kawaii_color())
        e.description = f"🌸✨ Les messages d'au revoir kawaii (embed tristoune) sont maintenant dans {channel.mention} ! (｡•́︿•̀｡) 💕"
        await ctx.send(embed=e)
    elif type.lower() == "text":
        set_conf(ctx.guild.id, "leave_text_channel", channel.id)
        e = discord.Embed(title="✅👋💔 Au Revoir Configuré ! 💔👋✅", color=random_kawaii_color())
        e.description = f"🌸✨ Les messages d'au revoir kawaii (texte triste) sont maintenant dans {channel.mention} ! 💕"
        await ctx.send(embed=e)

@bot.command(name="setlogs")
@commands.has_permissions(manage_guild=True)
async def set_logs(ctx, channel: discord.TextChannel):
    set_conf(ctx.guild.id, "logs_channel", channel.id)
    e = discord.Embed(title="✅📝✨ Logs Configurés ! ✨📝✅", color=random_kawaii_color())
    e.description = f"🌸💖 Les logs ultra kawaii sont maintenant dans {channel.mention} ! Je vais tout surveiller avec amour ! (◕‿◕)♡ 💕"
    await ctx.send(embed=e)

@bot.command(name="setinvitation")
@commands.has_permissions(manage_guild=True)
async def set_invitation(ctx, channel: discord.TextChannel):
    set_conf(ctx.guild.id, "invitation_channel", channel.id)
    e = discord.Embed(title="✅💌✨ Invitations Configurées ! ✨💌✅", color=random_kawaii_color())
    e.description = f"🌸💖 Les invitations mignonnes seront trackées dans {channel.mention} ! Sugoi ! 💕✨"
    await ctx.send(embed=e)

@bot.command(name="setsuggestion")
@commands.has_permissions(manage_guild=True)
async def set_suggestion(ctx, channel: discord.TextChannel):
    set_conf(ctx.guild.id, "suggestion_channel", channel.id)
    e = discord.Embed(title="✅💡✨ Suggestions Configurées ! ✨💡✅", color=random_kawaii_color())
    e.description = f"🌸💖 Les suggestions adorables iront dans {channel.mention} ! Yatta ! 💕🌟"
    await ctx.send(embed=e)

# === MODERATION ===
@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member, *, reason: str = "Aucune raison fournie... mais sois plus gentil(le) quand même ! 💕"):
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
    e = discord.Embed(title="⚠️✨💖 AVERTISSEMENT KAWAII 💖✨⚠️", color=random_kawaii_color())
    e.description = f"🌸 {member.mention} a reçu un avertissement mignon mais sérieux ! (｡•́︿•̀｡) 💔"
    e.add_field(name="💫🎀 Membre Averti", value=member.mention, inline=True)
    e.add_field(name="📝💕 Raison Kawaii", value=f"```{reason}```", inline=False)
    e.add_field(name="📊✨ Total d'Avertissements", value=f"**{warn_count}** avertissement(s) mignon(s) ! 🌸", inline=True)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text="✨💖 Sois plus gentil(le) la prochaine fois ! On t'aime quand même ! (◕‿◕)♡ 🌸💕")
    await ctx.send(embed=e)
    
    try:
        dm_embed = discord.Embed(
            title=f"⚠️💕 Avertissement Kawaii de {ctx.guild.name} 💕⚠️",
            description=f"🌸 Tu as reçu un avertissement mignon sur **{ctx.guild.name}** ! (｡•́︿•̀｡) 💔",
            color=random_kawaii_color()
        )
        dm_embed.add_field(name="💭✨ Raison", value=f"```{reason}```", inline=False)
        dm_embed.add_field(name="📊💖 Tu as maintenant", value=f"**{warn_count}** avertissement(s) ! 🌸", inline=False)
        dm_embed.set_footer(text="✨💕 Sois plus gentil(le) et tout ira bien ! On croit en toi ! (◕‿◕)♡ 🌸💖")
        await member.send(embed=dm_embed)
    except:
        pass

@bot.command(name="warnings")
async def warnings(ctx, member: discord.Member):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    warns = data.get("warnings", {}).get(gid, {}).get(uid, [])
    
    if not warns:
        e = discord.Embed(
            title=f"🎉✨💖 AUCUN AVERTISSEMENT ! 💖✨🎉",
            description=f"🌸 {member.mention} n'a AUCUN avertissement ! Quelle personne ultra kawaii et adorable ! (◕‿◕)♡ 💕✨",
            color=random_kawaii_color()
        )
        e.set_thumbnail(url=member.display_avatar.url)
        e.set_footer(text="✨💖 Continue comme ça, tu es parfait(e) ! 🌸💕")
        await ctx.send(embed=e)
        return
    
    e = discord.Embed(
        title=f"⚠️🌸💕 AVERTISSEMENTS DE {member.display_name.upper()} 💕🌸⚠️",
        description=f"📋✨ Voici tous les avertissements kawaii de {member.mention} ! (｡•́︿•̀｡) 💔",
        color=random_kawaii_color()
    )
    e.set_thumbnail(url=member.display_avatar.url)
    
    for i, w in enumerate(warns, 1):
        emoji = random.choice(KAWAII_EMOJIS)
        e.add_field(
            name=f"{emoji} 📋 Avertissement #{i}",
            value=f"**💭 Raison Kawaii:** {w['reason']}\n**📅 Date Mignonne:** {w['date'][:10]} ✨",
            inline=False
        )
    
    e.add_field(name="💫📊 Total", value=f"**{len(warns)}** avertissement(s) au total ! 🌸", inline=False)
    e.set_footer(text="✨💕 Essaye d'être plus gentil(le) la prochaine fois ! On t'aime ! (◕‿◕)♡ 🌸💖")
    await ctx.send(embed=e)

@bot.command(name="clearwarns")
@commands.has_permissions(manage_messages=True)
async def clear_warns(ctx, member: discord.Member):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    if gid in data.get("warnings", {}) and uid in data["warnings"][gid]:
        warn_count = len(data["warnings"][gid][uid])
        del data["warnings"][gid][uid]
        save_data(data)
        
        e = discord.Embed(
            title="🎉✨💖 AVERTISSEMENTS EFFACÉS ! 💖✨🎉",
            description=f"🌸 Tous les **{warn_count}** avertissement(s) de {member.mention} ont été effacés ! Nouveau départ ultra kawaii ! (◕‿◕)♡ 💕✨",
            color=random_kawaii_color()
        )
        e.set_thumbnail(url=member.display_avatar.url)
        e.set_footer(text="✨💖 Tout le monde mérite une seconde chance kawaii ! 🌸💕")
        await ctx.send(embed=e)
    else:
        e = discord.Embed(
            title="🌸✨💖 AUCUN AVERTISSEMENT ! 💖✨🌸",
            description=f"🎉 {member.mention} n'a aucun avertissement à effacer ! Quelle personne adorable et parfaite ! (◕‿◕)♡ 💕",
            color=random_kawaii_color()
        )
        e.set_thumbnail(url=member.display_avatar.url)
        e.set_footer(text="✨💖 Trop mignon(ne) pour avoir des warnings ! 🌸💕")
        await ctx.send(embed=e)

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "Aucune raison... mais bye bye quand même ! 💔"):
    await member.kick(reason=reason)
    e = discord.Embed(
        title="👢✨💔 MEMBRE EXPULSÉ KAWAII 💔✨👢",
        description=f"🌸 {member.mention} a été expulsé du serveur... C'est trop triste ! (｡•́︿•̀｡) 💔",
        color=0xff69b4
    )
    e.add_field(name="💫🎀 Membre Expulsé", value=f"**{member.display_name}**\n{member.mention}", inline=True)
    e.add_field(name="💭💕 Raison Kawaii", value=f"```{reason}```", inline=False)
    e.add_field(name="👋✨ Message", value="Bye bye ! Peut-être qu'on se reverra un jour ! 🌸💕", inline=False)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text="✨💔 Au revoir personne mignonne mais pas assez gentille ! 👋💖")
    await ctx.send(embed=e)

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "Aucune raison... mais tu ne reviendras pas ! 💔"):
    await member.ban(reason=reason)
    e = discord.Embed(
        title="🔨✨💔 MEMBRE BANNI KAWAII 💔✨🔨",
        description=f"🌸 {member.mention} a été banni du serveur pour toujours... Notre cœur est brisé ! (｡•́︿•̀｡) 💔💔💔",
        color=0xff1493
    )
    e.add_field(name="💫🎀 Membre Banni", value=f"**{member.display_name}**\n{member.mention}", inline=True)
    e.add_field(name="💭💕 Raison du Ban", value=f"```{reason}```", inline=False)
    e.add_field(name="👋✨ Message Final", value="Au revoir pour toujours ! Tu vas nous manquer... ou pas ! 🌸💔", inline=False)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text="✨💔 Adieu pour l'éternité ! (｡•́︿•̀｡) 👋💔")
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
    
    e = discord.Embed(
        title="🔇✨💕 MUTE KAWAII ACTIVÉ ! 💕✨🔇",
        description=f"🌸 {member.mention} a été mute ultra kawaii pour **{duration}** ! Chut chut petit(e) mignon(ne) ! 🤫💖",
        color=random_kawaii_color()
    )
    e.add_field(name="💫🎀 Membre Mute", value=member.mention, inline=True)
    e.add_field(name="⏰💕 Durée Mignonne", value=f"**{duration}** ✨", inline=True)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text="✨💖 Silence kawaii ! Réfléchis bien ! (◕‿◕) 🌸💕")
    await ctx.send(embed=e)
    
    await asyncio.sleep(duration_seconds)
    await member.remove_roles(muted_role)
    
    unmute_e = discord.Embed(
        title="🔊✨🎉 UNMUTE AUTOMATIQUE KAWAII ! 🎉✨🔊",
        description=f"🌸💖 {member.mention} peut parler à nouveau ! Bienvenue back personne adorable ! (◕‿◕)♡ 💕✨",
        color=random_kawaii_color()
    )
    unmute_e.set_thumbnail(url=member.display_avatar.url)
    unmute_e.set_footer(text="✨💖 Sois plus gentil(le) maintenant ! On t'aime ! 🌸💕")
    await ctx.send(unmute_e)

@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute(ctx, member: discord.Member):
    muted_role = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted_role in member.roles:
        await member.remove_roles(muted_role)
        e = discord.Embed(
            title="🔊✨🎉 UNMUTE KAWAII ! 🎉✨🔊",
            description=f"🌸💖 {member.mention} peut parler à nouveau ! Yaaaay ! Bienvenue back ! (◕‿◕)♡ 💕✨🎊",
            color=random_kawaii_color()
        )
        e.set_thumbnail(url=member.display_avatar.url)
        e.set_footer(text="✨💖 On est trop content(e) de te revoir parler ! 🌸💕")
        await ctx.send(embed=e)
    else:
        e = discord.Embed(
            title="🌸✨💖 PAS MUTE ! 💖✨🌸",
            description=f"🎉 {member.mention} n'est pas mute du tout ! Tout va bien dans le meilleur des mondes kawaii ! (◕‿◕)♡ 💕",
            color=random_kawaii_color()
        )
        e.set_footer(text="✨💖 Aucun problème à signaler ! 🌸💕")
        await ctx.send(embed=e)

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)
    e = discord.Embed(
        title="🗑️✨💖 NETTOYAGE KAWAII ! 💖✨🗑️",
        description=f"🌸 **{amount}** messages ont été supprimés ! Tout est propre et mignon maintenant ! ✨💕",
        color=random_kawaii_color()
    )
    e.set_footer(text="✨💖 Salon ultra clean ! (◕‿◕)♡ 🌸💕")
    msg = await ctx.send(embed=e)
    await asyncio.sleep(3)
    await msg.delete()

@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    e = discord.Embed(
        title="🔒✨💖 SALON VERROUILLÉ KAWAII ! 💖✨🔒",
        description=f"🌸 Ce salon adorable est maintenant verrouillé ! Personne ne peut parler ! 🤫💕",
        color=random_kawaii_color()
    )
    e.set_footer(text="✨💖 Silence mignon activé ! (◕‿◕) 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    e = discord.Embed(
        title="🔓✨🎉 SALON DÉVERROUILLÉ KAWAII ! 🎉✨🔓",
        description=f"🌸 Ce salon adorable est maintenant déverrouillé ! Tout le monde peut parler à nouveau ! Yaaaay ! 💕✨",
        color=random_kawaii_color()
    )
    e.set_footer(text="✨💖 Liberté de parole kawaii restaurée ! (◕‿◕)♡ 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="slowmode")
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, seconds: int):
    await ctx.channel.edit(slowmode_delay=seconds)
    e = discord.Embed(
        title="⏱️✨💖 MODE LENT KAWAII ! 💖✨⏱️",
        description=f"🌸 Le mode lent ultra mignon a été activé ! **{seconds}** secondes entre chaque message adorable ! 💕",
        color=random_kawaii_color()
    )
    e.add_field(name="⏰💫 Délai Kawaii", value=f"**{seconds}** secondes ✨", inline=True)
    e.set_footer(text="✨💖 Prenez votre temps, soyez mignons ! (◕‿◕) 🌸💕")
    await ctx.send(embed=e)

# === ECONOMY ===
@bot.command(name="balance", aliases=["bal"])
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    money = data.get("economy", {}).get(gid, {}).get(uid, 0)
    
    e = discord.Embed(
        title=f"💰✨💖 BALANCE KAWAII DE {member.display_name.upper()} 💖✨💰",
        description=f"🌸 Voici tout l'argent mignon de cette personne adorable ! (◕‿◕)♡ 💕",
        color=random_kawaii_color()
    )
    e.add_field(name="💎✨ Argent Ultra Mignon", value=f"# {random_kawaii_emojis(2)} **{money}** 💵 ✨", inline=False)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text="✨💖 Économie ultra kawaii ! Continue de gagner de l'argent mignon ! 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="daily")
async def daily(ctx):
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    
    data.setdefault("economy", {}).setdefault(gid, {})
    data["economy"][gid][uid] = data["economy"][gid].get(uid, 0) + 100
    save_data(data)
    
    e = discord.Embed(
        title="💰✨🎁 BONUS QUOTIDIEN KAWAII ! 🎁✨💰",
        description=f"🌸 {ctx.author.mention} a reçu son bonus quotidien ultra mignon ! (◕‿◕)♡ 💕",
        color=random_kawaii_color()
    )
    e.add_field(name="💎🎀 Tu as reçu", value=f"# {random_kawaii_emojis(3)} **+100** 💵 ✨", inline=False)
    e.add_field(name="🌟💖 Reviens demain", value="Pour encore plus d'argent kawaii ! 🎁✨", inline=False)
    e.set_thumbnail(url=ctx.author.display_avatar.url)
    e.set_footer(text="✨💖 Bonus quotidien adorable ! À demain ! 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="pay")
async def pay(ctx, member: discord.Member, amount: int):
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    target_uid = str(member.id)
    
    data.setdefault("economy", {}).setdefault(gid, {})
    
    if data["economy"][gid].get(uid, 0) < amount:
        e = discord.Embed(
            title="❌💔🌸 PAS ASSEZ D'ARGENT KAWAII ! 🌸💔❌",
            description=f"😢 {ctx.author.mention}, tu n'as pas assez d'argent mignon pour donner **{amount}** 💵 ! (｡•́︿•̀｡) 💔",
            color=0xff1493
        )
        e.set_footer(text="✨💔 Gagne plus d'argent kawaii d'abord ! 🌸💕")
        await ctx.send(embed=e)
        return
    
    data["economy"][gid][uid] = data["economy"][gid].get(uid, 0) - amount
    data["economy"][gid][target_uid] = data["economy"][gid].get(target_uid, 0) + amount
    save_data(data)
    
    e = discord.Embed(
        title="💸✨🎁 PAIEMENT KAWAII EFFECTUÉ ! 🎁✨💸",
        description=f"🌸 {ctx.author.mention} a donné de l'argent ultra mignon à {member.mention} ! Quelle générosité adorable ! (◕‿◕)♡ 💕✨",
        color=random_kawaii_color()
    )
    e.add_field(name="💰🎀 Montant Kawaii", value=f"# {random_kawaii_emojis(2)} **{amount}** 💵 ✨", inline=False)
    e.add_field(name="💖✨ De", value=ctx.author.mention, inline=True)
    e.add_field(name="🎁✨ À", value=member.mention, inline=True)
    e.set_footer(text="✨💖 Transaction ultra mignonne réussie ! 🌸💕")
    await ctx.send(embed=e)

# === GIVEAWAYS ===
@bot.command(name="gstart")
@commands.has_permissions(manage_guild=True)
async def gstart(ctx, duration: str, *, prize: str):
    time_convert = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    duration_seconds = int(duration[:-1]) * time_convert.get(duration[-1], 60)
    
    end_time = datetime.datetime.utcnow() + datetime.timedelta(seconds=duration_seconds)
    
    e = discord.Embed(
        title="🎁✨💖 GIVEAWAY ULTRA KAWAII ! 💖✨🎁",
        description=f"# {random_kawaii_emojis(5)}\n\n🌸 **UN GIVEAWAY ADORABLE A COMMENCÉ !** 🌸",
        color=random_kawaii_color()
    )
    e.add_field(name="🎀💕 Prix Ultra Mignon", value=f"# **{prize}** ✨", inline=False)
    e.add_field(name="⏰🌟 Durée Kawaii", value=f"**{duration}** ⏱️", inline=True)
    e.add_field(name="💖✨ Comment Participer", value="**Réagis avec 🎉 pour participer au giveaway le plus mignon de l'univers ! (◕‿◕)♡**", inline=False)
    e.set_footer(text=f"✨💖 Se termine le {end_time.strftime('%d/%m/%Y à %H:%M')} ! Bonne chance kawaii ! 🌸💕")
    e.set_image(url="https://i.imgur.com/KOaXSQZ.gif")
    
    msg = await ctx.send(f"🎊✨💖 @everyone UN GIVEAWAY ULTRA KAWAII ! 💖✨🎊", embed=e)
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
                            e = discord.Embed(
                                title="🎉✨💖 GIVEAWAY KAWAII TERMINÉ ! 💖✨🎉",
                                description=f"# {random_kawaii_emojis(5)}\n\n🌸 **LE GIVEAWAY ULTRA MIGNON EST TERMINÉ !** 🌸",
                                color=random_kawaii_color()
                            )
                            e.add_field(name="🏆👑 GAGNANT KAWAII", value=f"# {winner.mention} 🎊✨", inline=False)
                            e.add_field(name="🎀💕 Prix Adorable", value=f"**{gdata['prize']}** 💖", inline=False)
                            e.add_field(name="🌟💫 Message", value="**FÉLICITATIONS ! Tu es la personne la plus chanceuse et la plus kawaii de l'univers ! (◕‿◕)♡** 💕✨🎉", inline=False)
                            e.set_thumbnail(url=winner.display_avatar.url)
                            e.set_footer(text="✨💖 Giveaway ultra kawaii terminé avec succès ! 🌸💕")
                            await channel.send(f"🎊✨💖 {winner.mention} 💖✨🎊", embed=e)
                        else:
                            e = discord.Embed(
                                title="❌💔🌸 AUCUN PARTICIPANT KAWAII ! 🌸💔❌",
                                description=f"😢 Aucune personne adorable n'a participé au giveaway... C'est trop triste ! (｡•́︿•̀｡) 💔",
                                color=0xff1493
                            )
                            e.set_footer(text="✨💔 Dommage... Plus de chance la prochaine fois ! 🌸💕")
                            await channel.send(embed=e)
                except:
                    pass
        
        del data["giveaways"][msg_id]
        save_data(data)

# === REACTION ROLES ===
@bot.command(name="reactionrole")
@commands.has_permissions(manage_roles=True)
async def reaction_role(ctx):
    e = discord.Embed(
        title="🎭✨💖 CHOISIS TES RÔLES KAWAII ! 💖✨🎭",
        description=f"# {random_kawaii_emojis(5)}\n\n🌸 **Réagis avec les emojis adorables pour obtenir des rôles ultra mignons !** (◕‿◕)♡ 💕\n\n✨ Les rôles seront ajoutés par un admin kawaii ! 💖",
        color=random_kawaii_color()
    )
    e.set_footer(text="✨💖 Système de rôles réactions ultra kawaii ! 🌸💕")
    msg = await ctx.send(embed=e)
    
    gid = str(ctx.guild.id)
    data.setdefault("reaction_roles", {})[str(msg.id)] = {"guild": gid, "roles": {}}
    save_data(data)
    
    success_e = discord.Embed(
        title="✅🎉💖 MENU CRÉÉ AVEC SUCCÈS ! 💖🎉✅",
        description=f"🌸 Le menu kawaii a été créé ! Utilise cette commande adorable pour ajouter des rôles :\n\n```+addrr {msg.id} <emoji> @role```\n\n✨ Exemple ultra mignon :\n```+addrr {msg.id} 💖 @Membre Kawaii```",
        color=random_kawaii_color()
    )
    success_e.set_footer(text="✨💖 Menu de rôles ultra kawaii prêt ! 🌸💕")
    await ctx.send(embed=success_e)

@bot.command(name="addrr")
@commands.has_permissions(manage_roles=True)
async def add_rr(ctx, message_id: str, emoji: str, role: discord.Role):
    if message_id not in data.get("reaction_roles", {}):
        e = discord.Embed(
            title="❌💔🌸 MESSAGE INTROUVABLE ! 🌸💔❌",
            description=f"😢 Le message n'a pas été trouvé ! Vérifie l'ID adorable ! (｡•́︿•̀｡) 💔",
            color=0xff1493
        )
        e.set_footer(text="✨💔 Utilise le bon ID kawaii ! 🌸💕")
        await ctx.send(embed=e)
        return
    
    data["reaction_roles"][message_id]["roles"][emoji] = role.id
    save_data(data)
    
    try:
        msg = await ctx.channel.fetch_message(int(message_id))
        await msg.add_reaction(emoji)
        
        e = discord.Embed(
            title="✅🎉💖 RÔLE AJOUTÉ AVEC SUCCÈS ! 💖🎉✅",
            description=f"🌸 Le rôle ultra kawaii a été ajouté au menu adorable ! (◕‿◕)♡ 💕",
            color=random_kawaii_color()
        )
        e.add_field(name="💫🎀 Emoji Kawaii", value=emoji, inline=True)
        e.add_field(name="👑✨ Rôle Mignon", value=role.mention, inline=True)
        e.set_footer(text="✨💖 Rôle réaction ultra kawaii configuré ! 🌸💕")
        await ctx.send(embed=e)
    except Exception as ex:
        await ctx.send(f"❌💔 Erreur kawaii : {ex} 💔✨")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    
    msg_id = str(payload.message_id)
    if msg_id in data.get("reaction_roles", {}):
        guild = bot.get_guild(payload.guild_id)
        if guild:
            role_id = data["reaction_roles"][msg_id]["roles"].get(str(payload.emoji))
            if role_id:
                role = guild.get_role(role_id)
                member = guild.get_member(payload.user_id)
                if role and member:
                    await member.add_roles(role)

@bot.event
async def on_raw_reaction_remove(payload):
    msg_id = str(payload.message_id)
    if msg_id in data.get("reaction_roles", {}):
        guild = bot.get_guild(payload.guild_id)
        if guild:
            role_id = data["reaction_roles"][msg_id]["roles"].get(str(payload.emoji))
            if role_id:
                role = guild.get_role(role_id)
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
    
    e = discord.Embed(
        title="✅🤖💖 AUTO-RÉPONSE KAWAII AJOUTÉE ! 💖🤖✅",
        description=f"🌸 Une nouvelle réponse automatique ultra mignonne a été ajoutée ! (◕‿◕)♡ 💕",
        color=random_kawaii_color()
    )
    e.add_field(name="🎀✨ Trigger Kawaii", value=f"```{trigger}```", inline=False)
    e.add_field(name="💬💕 Réponse Adorable", value=f"```{response}```", inline=False)
    e.set_footer(text="✨💖 Le bot répondra automatiquement maintenant ! 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="listresponses")
async def list_responses(ctx):
    gid = str(ctx.guild.id)
    responses = data.get("auto_responses", {}).get(gid, {})
    
    if not responses:
        e = discord.Embed(
            title="🌸✨💖 AUCUNE AUTO-RÉPONSE ! 💖✨🌸",
            description=f"😢 Aucune réponse automatique kawaii configurée ! Ajoute-en avec `+addresponse` ! 💕",
            color=random_kawaii_color()
        )
        e.set_footer(text="✨💖 Configure des réponses adorables ! 🌸💕")
        await ctx.send(embed=e)
        return
    
    e = discord.Embed(
        title="🤖✨💖 AUTO-RÉPONSES KAWAII 💖✨🤖",
        description=f"🌸 Voici toutes les réponses automatiques ultra mignonnes ! (◕‿◕)♡ 💕",
        color=random_kawaii_color()
    )
    
    for i, (trigger, response) in enumerate(responses.items(), 1):
        emoji = random.choice(KAWAII_EMOJIS)
        e.add_field(
            name=f"{emoji} #{i} Trigger: `{trigger}`",
            value=f"**Réponse:** {response} ✨",
            inline=False
        )
    
    e.set_footer(text=f"✨💖 {len(responses)} réponse(s) automatique(s) kawaii ! 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="delresponse")
@commands.has_permissions(manage_guild=True)
async def del_response(ctx, trigger: str):
    gid = str(ctx.guild.id)
    if gid in data.get("auto_responses", {}) and trigger.lower() in data["auto_responses"][gid]:
        del data["auto_responses"][gid][trigger.lower()]
        save_data(data)
        
        e = discord.Embed(
            title="✅🗑️💖 AUTO-RÉPONSE SUPPRIMÉE ! 💖🗑️✅",
            description=f"🌸 La réponse automatique pour `{trigger}` a été supprimée ! (｡•́︿•̀｡) 💔",
            color=random_kawaii_color()
        )
        e.set_footer(text="✨💖 Auto-réponse kawaii supprimée avec succès ! 🌸💕")
        await ctx.send(embed=e)
    else:
        e = discord.Embed(
            title="❌💔🌸 TRIGGER INTROUVABLE ! 🌸💔❌",
            description=f"😢 Aucune auto-réponse trouvée pour `{trigger}` ! Vérifie le trigger kawaii ! 💔",
            color=0xff1493
        )
        e.set_footer(text="✨💔 Utilise +listresponses pour voir les triggers ! 🌸💕")
        await ctx.send(embed=e)

# === SUGGESTIONS ===
@bot.command(name="suggest")
async def suggest(ctx, *, suggestion: str):
    sugg_channel_id = get_conf(ctx.guild.id, "suggestion_channel")
    if not sugg_channel_id:
        await ctx.send("❌💔 Aucun salon de suggestions kawaii configuré ! Configure-le avec `+setsuggestion #channel` ! 💔✨")
        return
    
    sugg_channel = ctx.guild.get_channel(sugg_channel_id)
    if not sugg_channel:
        await ctx.send("❌💔 Salon de suggestions introuvable ! 💔✨")
        return
    
    gid = str(ctx.guild.id)
    data.setdefault("suggestions", {}).setdefault(gid, {})
    sugg_id = len(data["suggestions"][gid]) + 1
    
    e = discord.Embed(
        title=f"💡✨💖 SUGGESTION KAWAII #{sugg_id} 💖✨💡",
        description=f"# {random_kawaii_emojis(3)}\n\n{suggestion}",
        color=random_kawaii_color()
    )
    e.add_field(name="👤💕 Suggéré par", value=ctx.author.mention, inline=True)
    e.add_field(name="🆔🌟 ID Kawaii", value=f"**#{sugg_id}**", inline=True)
    e.set_thumbnail(url=ctx.author.display_avatar.url)
    e.set_footer(text=f"✨💖 Vote avec 👍 ou 👎 ! Suggestion ultra mignonne ! 🌸💕")
    
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
    
    success_e = discord.Embed(
        title="✅💡💖 SUGGESTION ENVOYÉE ! 💖💡✅",
        description=f"🌸 Ta suggestion ultra kawaii a été envoyée dans {sugg_channel.mention} ! (◕‿◕)♡ 💕",
        color=random_kawaii_color()
    )
    success_e.add_field(name="🆔✨ ID", value=f"**#{sugg_id}**", inline=True)
    success_e.set_footer(text="✨💖 Merci pour ta suggestion adorable ! 🌸💕")
    await ctx.send(success_e)

@bot.command(name="acceptsugg")
@commands.has_permissions(manage_guild=True)
async def accept_sugg(ctx, sugg_id: int):
    gid = str(ctx.guild.id)
    if str(sugg_id) not in data.get("suggestions", {}).get(gid, {}):
        await ctx.send(f"❌💔 Suggestion #{sugg_id} introuvable ! 💔✨")
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
                e.title = f"✅💚💖 SUGGESTION ACCEPTÉE #{sugg_id} 💖💚✅"
                e.add_field(name="🎉✨ Statut Kawaii", value="**ACCEPTÉE ! YATTA !** 🎊💕", inline=False)
                await msg.edit(embed=e)
            except:
                pass
    
    e = discord.Embed(
        title="✅🎉💖 SUGGESTION ACCEPTÉE ! 💖🎉✅",
        description=f"🌸 La suggestion #{sugg_id} a été acceptée ! Quelle idée adorable ! (◕‿◕)♡ 💕",
        color=0x00ff00
    )
    e.set_footer(text="✨💖 Excellente suggestion kawaii ! 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="denysugg")
@commands.has_permissions(manage_guild=True)
async def deny_sugg(ctx, sugg_id: int):
    gid = str(ctx.guild.id)
    if str(sugg_id) not in data.get("suggestions", {}).get(gid, {}):
        await ctx.send(f"❌💔 Suggestion #{sugg_id} introuvable ! 💔✨")
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
                e.title = f"❌💔 SUGGESTION REFUSÉE #{sugg_id} 💔❌"
                e.add_field(name="😢✨ Statut Kawaii", value="**REFUSÉE... Dommage !** 💔", inline=False)
                await msg.edit(embed=e)
            except:
                pass
    
    e = discord.Embed(
        title="❌💔🌸 SUGGESTION REFUSÉE 🌸💔❌",
        description=f"😢 La suggestion #{sugg_id} a été refusée... C'est triste ! (｡•́︿•̀｡) 💔",
        color=0xff0000
    )
    e.set_footer(text="✨💔 Peut-être la prochaine fois ! 🌸💕")
    await ctx.send(embed=e)

# === FUN COMMANDS ===
@bot.command(name="8ball")
async def eight_ball(ctx, *, question: str):
    responses = [
        "Oui absolument ! 💖✨",
        "C'est certain kawaii ! 🌸💕",
        "Sans aucun doute adorable ! 🎀✨",
        "Oui définitivement mignon ! 💗🌟",
        "Tu peux compter dessus ! 💕✨",
        "Peut-être oui peut-être non... 🤔💖",
        "Difficile à dire... 💭✨",
        "Mieux vaut ne pas te le dire maintenant ! 🙈💕",
        "Je ne peux pas prédire ça maintenant ! 🔮✨",
        "Repose ta question kawaii ! 🌸💖",
        "Non absolument pas ! 💔✨",
        "Mes sources disent non... 😢💕",
        "Peu probable mon mignon ! 🌸💔",
        "N'y compte pas trop ! 💭✨",
        "Non définitivement ! 💔🌟"
    ]
    
    e = discord.Embed(
        title="🔮✨💖 BOULE MAGIQUE KAWAII 💖✨🔮",
        color=random_kawaii_color()
    )
    e.add_field(name="💭💕 Ta Question Adorable", value=f"```{question}```", inline=False)
    e.add_field(name="🌟✨ Réponse Ultra Mignonne", value=f"# {random.choice(responses)}", inline=False)
    e.set_footer(text="✨💖 La boule magique kawaii a parlé ! (◕‿◕)♡ 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="coinflip")
async def coinflip(ctx):
    result = random.choice(["Pile", "Face"])
    emoji = "🪙" if result == "Pile" else "👑"
    
    e = discord.Embed(
        title="🪙✨💖 PILE OU FACE KAWAII 💖✨🪙",
        description=f"# {emoji} **{result.upper()} !** {emoji}",
        color=random_kawaii_color()
    )
    e.set_footer(text="✨💖 Lancer de pièce ultra mignon ! (◕‿◕)♡ 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="dice")
async def dice(ctx):
    result = random.randint(1, 6)
    dice_emojis = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
    
    e = discord.Embed(
        title="🎲✨💖 LANCER DE DÉ KAWAII 💖✨🎲",
        description=f"# {dice_emojis[result-1]} **{result}** {dice_emojis[result-1]}",
        color=random_kawaii_color()
    )
    e.set_footer(text="✨💖 Dé ultra mignon lancé ! (◕‿◕)♡ 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="love")
async def love(ctx, user1: discord.Member, user2: discord.Member = None):
    if user2 is None:
        user2 = user1
        user1 = ctx.author
    
    love_percent = random.randint(0, 100)
    
    if love_percent < 20:
        message = "Aucune compatibilité... C'est trop triste ! 💔😢"
        color = 0x808080
    elif love_percent < 40:
        message = "Pas vraiment compatibles... Dommage ! 💔✨"
        color = 0xff6347
    elif love_percent < 60:
        message = "Assez compatibles ! Pas mal du tout ! 💕✨"
        color = 0xffa500
    elif love_percent < 80:
        message = "Très compatibles ! C'est adorable ! 💖✨"
        color = 0xff69b4
    else:
        message = "PARFAITEMENT COMPATIBLES ! COUPLE ULTRA KAWAII ! 💖💕✨"
        color = 0xff1493
    
    hearts = "💖" * (love_percent // 20)
    bar = "█" * (love_percent // 10) + "░" * (10 - love_percent // 10)
    
    e = discord.Embed(
        title="💕✨💖 CALCULATEUR D'AMOUR KAWAII 💖✨💕",
        description=f"# {random_kawaii_emojis(3)}",
        color=color
    )
    e.add_field(name="💑 Couple Adorable", value=f"{user1.mention} 💕 {user2.mention}", inline=False)
    e.add_field(name="💖 % d'Amour Kawaii", value=f"# **{love_percent}%** {hearts}", inline=False)
    e.add_field(name="📊 Barre d'Amour", value=f"`{bar}` {love_percent}%", inline=False)
    e.add_field(name="💭 Verdict Mignon", value=f"**{message}**", inline=False)
    e.set_footer(text="✨💖 Calculateur d'amour ultra kawaii ! (◕‿◕)♡ 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="meme")
async def meme(ctx):
    meme_messages = [
        "Quand tu te réveilles et que c'est déjà l'après-midi 😴✨",
        "Quand tu vois un chien trop mignon dans la rue 🐶💖",
        "Moi en train d'étudier VS Moi en train de procrastiner 📚💤",
        "Quand ta pizza arrive enfin 🍕🎉",
        "Moi quand je vois quelque chose de kawaii 😍✨",
        "POV: Tu essaies d'être productif 💻😴",
        "Quand tu entends ton plat préféré 🍜👂",
        "Moi après 5 minutes d'exercice 💪😵",
        "Quand quelqu'un dit qu'il n'aime pas les animaux mignons 😱💔",
        "Moi en train de faire semblant de comprendre 🤔✨"
    ]
    
    e = discord.Embed(
        title="😂✨💖 MEME ULTRA KAWAII 💖✨😂",
        description=f"# {random.choice(meme_messages)}\n\n{random_kawaii_emojis(5)}",
        color=random_kawaii_color()
    )
    e.set_footer(text="✨💖 Meme adorable généré ! (◕‿◕)♡ 🌸💕")
    await ctx.send(embed=e)

# === UTILITY ===
@bot.command(name="serverinfo")
async def serverinfo(ctx):
    guild = ctx.guild
    
    e = discord.Embed(
        title=f"🏰✨💖 INFOS SERVEUR KAWAII 💖✨🏰",
        description=f"# {random_kawaii_emojis(5)}\n\n🌸 Voici toutes les infos adorables du serveur ! (◕‿◕)♡ 💕",
        color=random_kawaii_color()
    )
    
    if guild.icon:
        e.set_thumbnail(url=guild.icon.url)
    
    e.add_field(name="💫🎀 Nom Kawaii", value=f"**{guild.name}**", inline=True)
    e.add_field(name="🆔✨ ID Mignon", value=f"`{guild.id}`", inline=True)
    e.add_field(name="👑💕 Propriétaire", value=guild.owner.mention if guild.owner else "Inconnu", inline=True)
    e.add_field(name="👥🌟 Membres Adorables", value=f"**{guild.member_count}** 💖", inline=True)
    e.add_field(name="💬✨ Salons", value=f"**{len(guild.channels)}** 🌸", inline=True)
    e.add_field(name="🎭💕 Rôles", value=f"**{len(guild.roles)}** 🎀", inline=True)
    e.add_field(name="📅💖 Créé le", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
    e.add_field(name="🌟✨ Niveau de Boost", value=f"**Niveau {guild.premium_tier}** 💫", inline=True)
    
    e.set_footer(text="✨💖 Serveur ultra kawaii ! (◕‿◕)♡ 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="userinfo")
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    
    e = discord.Embed(
        title=f"👤✨💖 INFOS KAWAII DE {member.display_name.upper()} 💖✨👤",
        description=f"# {random_kawaii_emojis(5)}\n\n🌸 Voici toutes les infos adorables de cette personne mignonne ! (◕‿◕)♡ 💕",
        color=random_kawaii_color()
    )
    
    e.set_thumbnail(url=member.display_avatar.url)
    
    e.add_field(name="💫🎀 Nom d'utilisateur", value=f"**{member.name}**", inline=True)
    e.add_field(name="🆔✨ ID Mignon", value=f"`{member.id}`", inline=True)
    e.add_field(name="💬💕 Surnom Kawaii", value=member.display_name, inline=True)
    e.add_field(name="📅💖 Compte créé le", value=member.created_at.strftime("%d/%m/%Y"), inline=True)
    e.add_field(name="🎉🌟 A rejoint le", value=member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "Inconnu", inline=True)
    e.add_field(name="🎭✨ Rôles", value=f"**{len(member.roles)-1}** rôles adorables 💖", inline=True)
    
    if member.premium_since:
        e.add_field(name="💎🌸 Boost depuis", value=member.premium_since.strftime("%d/%m/%Y"), inline=True)
    
    e.set_footer(text="✨💖 Utilisateur ultra kawaii ! (◕‿◕)♡ 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="avatar")
async def avatar(ctx, member: discord.Member = None):
    member = member or ctx.author
    
    e = discord.Embed(
        title=f"🖼️✨💖 AVATAR KAWAII DE {member.display_name.upper()} 💖✨🖼️",
        description=f"# {random_kawaii_emojis(5)}\n\n🌸 Voici l'avatar ultra mignon de {member.mention} ! (◕‿◕)♡ 💕",
        color=random_kawaii_color()
    )
    e.set_image(url=member.display_avatar.url)
    e.add_field(name="🔗💫 Lien Direct", value=f"[Clique ici pour télécharger !]({member.display_avatar.url}) ✨", inline=False)
    e.set_footer(text="✨💖 Avatar adorable ! (◕‿◕)♡ 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="poll")
async def poll(ctx, *, question: str):
    e = discord.Embed(
        title="📊✨💖 SONDAGE ULTRA KAWAII 💖✨📊",
        description=f"# {random_kawaii_emojis(5)}\n\n**{question}**",
        color=random_kawaii_color()
    )
    e.add_field(name="💕✨ Comment voter", value="Réagis avec 👍 pour OUI ou 👎 pour NON ! 🌸", inline=False)
    e.set_footer(text=f"✨💖 Sondage créé par {ctx.author.display_name} ! (◕‿◕)♡ 🌸💕", icon_url=ctx.author.display_avatar.url)
    
    msg = await ctx.send(embed=e)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

# === INVITATIONS TRACKING ===
@bot.event
async def on_invite_create(invite):
    data.setdefault("invites", {})[str(invite.guild.id)] = {}
    invites = await invite.guild.invites()
    for inv in invites:
        data["invites"][str(invite.guild.id)][inv.code] = inv.uses
    save_data(data)

@bot.command(name="roleinvite")
@commands.has_permissions(manage_roles=True)
async def role_invite(ctx, invites_needed: int, role: discord.Role):
    gid = str(ctx.guild.id)
    data.setdefault("roles_invites", {})[gid] = {
        "invites": invites_needed,
        "role": role.id
    }
    save_data(data)
    
    e = discord.Embed(
        title="✅🎀💖 RÔLE D'INVITATION CONFIGURÉ ! 💖🎀✅",
        description=f"🌸 Les membres adorables qui invitent **{invites_needed}** personnes recevront le rôle {role.mention} ! (◕‿◕)♡ 💕",
        color=random_kawaii_color()
    )
    e.add_field(name="💫✨ Invitations Requises", value=f"**{invites_needed}** 🌟", inline=True)
    e.add_field(name="👑💕 Rôle Kawaii", value=role.mention, inline=True)
    e.set_footer(text="✨💖 Système d'invitations ultra kawaii configuré ! 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="invites")
async def invites(ctx, member: discord.Member = None):
    member = member or ctx.author
    gid = str(ctx.guild.id)
    uid = str(member.id)
    
    invite_count = data.get("user_invites", {}).get(gid, {}).get(uid, 0)
    
    e = discord.Embed(
        title=f"💌✨💖 INVITATIONS DE {member.display_name.upper()} 💖✨💌",
        description=f"# {random_kawaii_emojis(5)}",
        color=random_kawaii_color()
    )
    e.set_thumbnail(url=member.display_avatar.url)
    e.add_field(name="🎀💕 Invitations Totales", value=f"# **{invite_count}** invitations kawaii ! 🌟", inline=False)
    
    # Check role reward
    role_config = data.get("roles_invites", {}).get(gid, {})
    if role_config:
        required = role_config.get("invites", 0)
        if invite_count >= required:
            e.add_field(name="👑✨ Statut", value=f"**TU AS LE RÔLE ! YATTA !** 🎉💖", inline=False)
        else:
            remaining = required - invite_count
            e.add_field(name="📊💫 Progression", value=f"Plus que **{remaining}** invitation(s) pour le rôle kawaii ! 💕", inline=False)
    
    e.set_footer(text="✨💖 Continue d'inviter des personnes adorables ! (◕‿◕)♡ 🌸💕")
    await ctx.send(embed=e)

# === LINKS MANAGEMENT ===
@bot.command(name="allowlink")
@commands.has_permissions(manage_channels=True)
async def allow_link(ctx, channel: discord.TextChannel):
    gid = str(ctx.guild.id)
    data.setdefault("allowed_links", {}).setdefault(gid, [])
    if channel.id not in data["allowed_links"][gid]:
        data["allowed_links"][gid].append(channel.id)
        save_data(data)
    
    e = discord.Embed(
        title="✅🔗💖 LIENS AUTORISÉS KAWAII ! 💖🔗✅",
        description=f"🌸 Les liens adorables sont maintenant autorisés dans {channel.mention} ! (◕‿◕)♡ 💕",
        color=random_kawaii_color()
    )
    e.set_footer(text="✨💖 Partagez des liens mignons ! 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="disallowlink")
@commands.has_permissions(manage_channels=True)
async def disallow_link(ctx, channel: discord.TextChannel):
    gid = str(ctx.guild.id)
    if gid in data.get("allowed_links", {}) and channel.id in data["allowed_links"][gid]:
        data["allowed_links"][gid].remove(channel.id)
        save_data(data)
    
    e = discord.Embed(
        title="✅🚫💖 LIENS BLOQUÉS KAWAII ! 💖🚫✅",
        description=f"🌸 Les liens sont maintenant bloqués dans {channel.mention} ! Protection mignonne activée ! (◕‿◕)♡ 💕",
        color=random_kawaii_color()
    )
    e.set_footer(text="✨💖 Salon protégé des liens ! 🌸💕")
    await ctx.send(embed=e)

# === TICKETS ===
@bot.command(name="ticket")
async def ticket(ctx):
    category = discord.utils.get(ctx.guild.categories, name="🎫 Tickets Kawaii")
    if not category:
        category = await ctx.guild.create_category("🎫 Tickets Kawaii")
    
    ticket_channel = await ctx.guild.create_text_channel(
        name=f"ticket-{ctx.author.name}",
        category=category,
        topic=f"Ticket kawaii de {ctx.author.display_name} 💖✨"
    )
    
    await ticket_channel.set_permissions(ctx.guild.default_role, read_messages=False)
    await ticket_channel.set_permissions(ctx.author, read_messages=True, send_messages=True)
    
    e = discord.Embed(
        title="🎫✨💖 TICKET KAWAII CRÉÉ ! 💖✨🎫",
        description=f"# {random_kawaii_emojis(5)}\n\n🌸 Bienvenue dans ton ticket ultra mignon {ctx.author.mention} ! (◕‿◕)♡ 💕\n\n💬 Un staff adorable va venir t'aider très bientôt !\n🚪 Utilise `+close` pour fermer ce ticket kawaii !",
        color=random_kawaii_color()
    )
    e.set_thumbnail(url=ctx.author.display_avatar.url)
    e.set_footer(text="✨💖 Ticket ultra kawaii ! Nous sommes là pour t'aider ! 🌸💕")
    
    await ticket_channel.send(f"🎀💕 {ctx.author.mention} 💕🎀", embed=e)
    
    confirm_e = discord.Embed(
        title="✅🎫💖 TICKET CRÉÉ ! 💖🎫✅",
        description=f"🌸 Ton ticket kawaii a été créé ! Va dans {ticket_channel.mention} ! (◕‿◕)♡ 💕",
        color=random_kawaii_color()
    )
    await ctx.send(embed=confirm_e)

@bot.command(name="close")
async def close_ticket(ctx):
    if "ticket-" in ctx.channel.name:
        e = discord.Embed(
            title="🚪✨💖 FERMETURE DU TICKET KAWAII 💖✨🚪",
            description=f"🌸 Ce ticket adorable va se fermer dans **5 secondes** ! (｡•́︿•̀｡) 💔\n\n✨ Merci d'avoir utilisé notre support ultra kawaii ! 💕",
            color=random_kawaii_color()
        )
        e.set_footer(text="✨💖 À bientôt ! Bye bye ticket mignon ! 👋🌸💕")
        await ctx.send(embed=e)
        await asyncio.sleep(5)
        await ctx.channel.delete()
    else:
        await ctx.send("❌💔 Cette commande ne fonctionne que dans les tickets kawaii ! 💔✨")

@bot.command(name="ticketpanel")
@commands.has_permissions(manage_guild=True)
async def ticket_panel(ctx):
    e = discord.Embed(
        title="🎫✨💖 PANEL DE TICKETS ULTRA KAWAII 💖✨🎫",
        description=f"# {random_kawaii_emojis(5)}\n\n🌸 **Besoin d'aide adorable ?** 🌸\n\n💬 Clique sur le bouton mignon ci-dessous pour créer un ticket kawaii ! (◕‿◕)♡ 💕\n\n✨ Notre équipe de staff ultra mignonne est là pour t'aider ! 💖",
        color=random_kawaii_color()
    )
    e.add_field(name="🎀💕 Pourquoi créer un ticket ?", value=(
        "• Questions adorables 💭\n"
        "• Problèmes techniques 🔧\n"
        "• Signalements mignons 📢\n"
        "• Support général kawaii 💖\n"
        "• Suggestions ultra cute 💡"
    ), inline=False)
    e.set_footer(text="✨💖 Support ultra kawaii disponible 24/7 ! 🌸💕")
    e.set_image(url="https://i.imgur.com/KOaXSQZ.gif")
    
    class TicketButton(Button):
        def __init__(self):
            super().__init__(label="🎫 Créer un Ticket Kawaii 💖", style=discord.ButtonStyle.primary, emoji="🎀")
        
        async def callback(self, interaction: discord.Interaction):
            category = discord.utils.get(interaction.guild.categories, name="🎫 Tickets Kawaii")
            if not category:
                category = await interaction.guild.create_category("🎫 Tickets Kawaii")
            
            ticket_channel = await interaction.guild.create_text_channel(
                name=f"ticket-{interaction.user.name}",
                category=category,
                topic=f"Ticket kawaii de {interaction.user.display_name} 💖✨"
            )
            
            await ticket_channel.set_permissions(interaction.guild.default_role, read_messages=False)
            await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            
            ticket_e = discord.Embed(
                title="🎫✨💖 TICKET KAWAII CRÉÉ ! 💖✨🎫",
                description=f"# {random_kawaii_emojis(5)}\n\n🌸 Bienvenue dans ton ticket ultra mignon {interaction.user.mention} ! (◕‿◕)♡ 💕\n\n💬 Un staff adorable va venir t'aider très bientôt !\n🚪 Utilise `+close` pour fermer ce ticket kawaii !",
                color=random_kawaii_color()
            )
            ticket_e.set_thumbnail(url=interaction.user.display_avatar.url)
            ticket_e.set_footer(text="✨💖 Ticket ultra kawaii ! Nous sommes là pour t'aider ! 🌸💕")
            
            await ticket_channel.send(f"🎀💕 {interaction.user.mention} 💕🎀", embed=ticket_e)
            await interaction.response.send_message(f"✅🎫💖 Ton ticket kawaii a été créé ! Va dans {ticket_channel.mention} ! 💖🎫✅", ephemeral=True)
    
    view = View(timeout=None)
    view.add_item(TicketButton())
    
    await ctx.send(embed=e, view=view)

# === VOCAUX TEMPORAIRES ===
@bot.command(name="setupvoc")
@commands.has_permissions(manage_channels=True)
async def setup_voc(ctx, channel: discord.VoiceChannel):
    set_conf(ctx.guild.id, "voc_trigger_channel", channel.id)
    
    e = discord.Embed(
        title="✅🎤💖 VOCAUX TEMPORAIRES CONFIGURÉS ! 💖🎤✅",
        description=f"🌸 Le salon {channel.mention} est maintenant le trigger kawaii pour créer des vocaux temporaires adorables ! (◕‿◕)♡ 💕\n\n✨ Rejoins-le pour créer ton propre vocal ultra mignon ! 💖",
        color=random_kawaii_color()
    )
    e.set_footer(text="✨💖 Vocaux temporaires kawaii configurés ! 🌸💕")
    await ctx.send(embed=e)

@bot.event
async def on_voice_state_update(member, before, after):
    gid = str(member.guild.id)
    trigger_channel_id = get_conf(member.guild.id, "voc_trigger_channel")
    
    # Création de vocal temporaire
    if after.channel and after.channel.id == trigger_channel_id:
        category = after.channel.category
        new_channel = await member.guild.create_voice_channel(
            name=f"🌸 Vocal de {member.display_name} 💖",
            category=category
        )
        await member.move_to(new_channel)
        
        data.setdefault("temp_vocs", {})[str(new_channel.id)] = {
            "owner": str(member.id),
            "guild": gid
        }
        save_data(data)
    
    # Suppression de vocal temporaire
    if before.channel and str(before.channel.id) in data.get("temp_vocs", {}):
        if len(before.channel.members) == 0:
            await before.channel.delete()
            del data["temp_vocs"][str(before.channel.id)]
            save_data(data)

@bot.command(name="createvoc")
@commands.has_permissions(manage_channels=True)
async def create_voc(ctx):
    category = discord.utils.get(ctx.guild.categories, name="🎤 Vocaux Kawaii")
    if not category:
        category = await ctx.guild.create_category("🎤 Vocaux Kawaii")
    
    trigger_channel = await ctx.guild.create_voice_channel(
        name="➕ Créer un Vocal Kawaii 💖",
        category=category
    )
    
    set_conf(ctx.guild.id, "voc_trigger_channel", trigger_channel.id)
    
    e = discord.Embed(
        title="✅🎤💖 VOCAL TRIGGER CRÉÉ ! 💖🎤✅",
        description=f"🌸 Le salon vocal trigger ultra kawaii a été créé ! (◕‿◕)♡ 💕\n\n✨ Rejoins {trigger_channel.mention} pour créer automatiquement ton propre vocal temporaire adorable ! 💖\n\n🎀 Le vocal sera supprimé automatiquement quand tout le monde part ! 💕",
        color=random_kawaii_color()
    )
    e.set_footer(text="✨💖 Système de vocaux temporaires ultra kawaii activé ! 🌸💕")
    await ctx.send(embed=e)

# === ERROR HANDLER ===
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        e = discord.Embed(
            title="❌💔🌸 PERMISSIONS MANQUANTES ! 🌸💔❌",
            description=f"😢 {ctx.author.mention}, tu n'as pas les permissions kawaii pour utiliser cette commande adorable ! (｡•́︿•̀｡) 💔",
            color=0xff1493
        )
        e.set_footer(text="✨💔 Demande à un admin mignon ! 🌸💕")
        await ctx.send(embed=e)
    
    elif isinstance(error, commands.MissingRequiredArgument):
        e = discord.Embed(
            title="❌💭🌸 ARGUMENT MANQUANT KAWAII ! 🌸💭❌",
            description=f"😢 {ctx.author.mention}, il manque des arguments adorables à ta commande ! (｡•́︿•̀｡) 💔\n\n✨ Utilise `+help` pour voir comment utiliser cette commande mignonne ! 💖",
            color=0xff1493
        )
        e.set_footer(text="✨💔 Vérifie la syntaxe kawaii ! 🌸💕")
        await ctx.send(embed=e)
    
    elif isinstance(error, commands.CommandNotFound):
        e = discord.Embed(
            title="❌🔍🌸 COMMANDE INTROUVABLE ! 🌸🔍❌",
            description=f"😢 {ctx.author.mention}, cette commande kawaii n'existe pas ! (｡•́︿•̀｡) 💔\n\n✨ Utilise `+help` pour voir toutes les commandes adorables disponibles ! 💖",
            color=0xff1493
        )
        e.set_footer(text="✨💔 Vérifie l'orthographe mignonne ! 🌸💕")
        await ctx.send(embed=e)
    
    else:
        e = discord.Embed(
            title="❌💥🌸 ERREUR KAWAII ! 🌸💥❌",
            description=f"😢 Une erreur ultra mignonne est survenue ! (｡•́︿•̀｡) 💔\n\n```{str(error)}```",
            color=0xff1493
        )
        e.set_footer(text="✨💔 Contacte un développeur kawaii ! 🌸💕")
        await ctx.send(embed=e)

# === SHOP (BONUS) ===
@bot.command(name="shop")
async def shop(ctx):
    items = {
        "🎀": {"name": "Badge Kawaii", "price": 500, "description": "Un badge ultra mignon !"},
        "🌸": {"name": "Fleur Adorable", "price": 300, "description": "Une fleur magnifique !"},
        "💖": {"name": "Coeur Mignon", "price": 1000, "description": "Un coeur plein d'amour !"},
        "⭐": {"name": "Étoile Brillante", "price": 750, "description": "Une étoile kawaii !"},
        "🦄": {"name": "Licorne Magique", "price": 2000, "description": "Une licorne ultra rare !"}
    }
    
    e = discord.Embed(
        title="🏪✨💖 BOUTIQUE ULTRA KAWAII 💖✨🏪",
        description=f"# {random_kawaii_emojis(5)}\n\n🌸 Bienvenue dans la boutique la plus adorable de l'univers ! (◕‿◕)♡ 💕\n\n✨ Utilise `+buy <item>` pour acheter un item mignon ! 💖",
        color=random_kawaii_color()
    )
    
    for emoji, item in items.items():
        e.add_field(
            name=f"{emoji} **{item['name']}**",
            value=f"💰 **{item['price']}** 💵\n💭 {item['description']} ✨",
            inline=False
        )
    
    e.set_footer(text="✨💖 Achète des items ultra mignons ! 🌸💕")
    await ctx.send(embed=e)

@bot.command(name="buy")
async def buy(ctx, item: str):
    items = {
        "badge": {"emoji": "🎀", "name": "Badge Kawaii", "price": 500},
        "fleur": {"emoji": "🌸", "name": "Fleur Adorable", "price": 300},
        "coeur": {"emoji": "💖", "name": "Coeur Mignon", "price": 1000},
        "étoile": {"emoji": "⭐", "name": "Étoile Brillante", "price": 750},
        "licorne": {"emoji": "🦄", "name": "Licorne Magique", "price": 2000}
    }
    
    item = item.lower()
    if item not in items:
        await ctx.send(f"❌💔 Cet item kawaii n'existe pas ! Utilise `+shop` pour voir les items adorables ! 💔✨")
        return
    
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    
    data.setdefault("economy", {}).setdefault(gid, {})
    user_money = data["economy"][gid].get(uid, 0)
    
    item_data = items[item]
    if user_money < item_data["price"]:
        e = discord.Embed(
            title="❌💔🌸 PAS ASSEZ D'ARGENT KAWAII ! 🌸💔❌",
            description=f"😢 {ctx.author.mention}, tu n'as que **{user_money}** 💵 mais cet item adorable coûte **{item_data['price']}** 💵 ! (｡•́︿•̀｡) 💔",
            color=0xff1493
        )
        e.set_footer(text="✨💔 Gagne plus d'argent kawaii ! 🌸💕")
        await ctx.send(embed=e)
        return
    
    data["economy"][gid][uid] = user_money - item_data["price"]
    save_data(data)
    
    e = discord.Embed(
        title="✅🛍️💖 ACHAT KAWAII RÉUSSI ! 💖🛍️✅",
        description=f"# {item_data['emoji']} {item_data['emoji']} {item_data['emoji']}\n\n🌸 {ctx.author.mention} a acheté **{item_data['name']}** ! Trop mignon ! (◕‿◕)♡ 💕",
        color=random_kawaii_color()
    )
    e.add_field(name="💰 Prix Payé", value=f"**{item_data['price']}** 💵 ✨", inline=True)
    e.add_field(name="💎 Argent Restant", value=f"**{data['economy'][gid][uid]}** 💵 💖", inline=True)
    e.set_thumbnail(url=ctx.author.display_avatar.url)
    e.set_footer(text="✨💖 Merci pour ton achat kawaii ! 🌸💕")
    await ctx.send(embed=e)

# === RUN BOT ===
if __name__ == "__main__":
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        print("❌💔 Token Discord manquant ! Configure DISCORD_TOKEN dans les variables d'environnement ! 💔✨")
    else:
        print("🌸✨💖 Démarrage du bot ultra kawaii... 💖✨🌸")
        bot.run(TOKEN)
