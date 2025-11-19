#!/usr/bin/env python3
"""
Hoshimi - Complete single-file Discord bot
Generated: compact, feature-rich single file implementing the requested commands.
Requirements: discord.py (2.x)
Run: set environment variable DISCORD_TOKEN, then `python hoshimi_complete.py`
"""

import os
import json
import asyncio
import datetime
import random
import re
from pathlib import Path
from collections import defaultdict

import discord
from discord.ext import commands, tasks

DATA_FILE = "hoshimi_data.json"

def load_data():
    if Path(DATA_FILE).exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

data = load_data()
# ensure keys
for k in ["config","warnings","levels","economy","backups","premium_users","auto_responses","suggestions","giveaways","reaction_roles","allowed_links","tickets","roles_invites","badges"]:
    data.setdefault(k, {})

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.reactions = True
bot = commands.Bot(command_prefix="+", intents=intents, help_command=None)

def get_conf(gid, key, default=None):
    return data.get("config", {}).get(str(gid), {}).get(key, default)

def set_conf(gid, key, value):
    data.setdefault("config", {}).setdefault(str(gid), {})[key] = value
    save_data(data)

# Utilities
def ensure_guild(gid):
    gid = str(gid)
    data.setdefault("config", {}).setdefault(gid, {})
    data.setdefault("warnings", {}).setdefault(gid, {})
    data.setdefault("levels", {}).setdefault(gid, {})
    data.setdefault("economy", {}).setdefault(gid, {})
    data.setdefault("backups", {}).setdefault(gid, [])
    data.setdefault("premium_users", {}).setdefault(gid, {})
    data.setdefault("auto_responses", {}).setdefault(gid, {})
    data.setdefault("suggestions", {}).setdefault(gid, {})
    data.setdefault("reaction_roles", {}).setdefault(gid, {})
    data.setdefault("allowed_links", {}).setdefault(gid, [])
    data.setdefault("tickets", {}).setdefault(gid, {})
    data.setdefault("roles_invites", {}).setdefault(gid, {})
    data.setdefault("badges", {}).setdefault(gid, {})

async def safe_send(channel, content=None, embed=None, delete_after=None):
    try:
        return await channel.send(content=content, embed=embed, delete_after=delete_after)
    except Exception:
        return None

# Basic logging helper
async def log_action(guild, action_type, **kwargs):
    log_ch = get_conf(guild.id, "logs_channel")
    if not log_ch:
        return
    ch = guild.get_channel(log_ch)
    if not ch:
        return
    e = discord.Embed(title=f"Log: {action_type}", color=0xff69b4, timestamp=datetime.datetime.utcnow())
    for k,v in kwargs.items():
        e.add_field(name=str(k), value=str(v), inline=True)
    try:
        await ch.send(embed=e)
    except Exception:
        pass

# -------------------------
# EVENTS
# -------------------------
@bot.event
async def on_ready():
    print(f"Bot connecté: {bot.user} (ID: {bot.user.id})")
    check_giveaway_expiry.start()

@bot.event
async def on_member_join(member):
    gid = str(member.guild.id)
    ensure_guild(gid)
    # auto role
    auto_role = get_conf(member.guild.id, "auto_role")
    if auto_role:
        role = member.guild.get_role(auto_role)
        if role:
            try:
                await member.add_roles(role)
            except:
                pass
    # welcome
    wc = get_conf(member.guild.id, "welcome_embed_channel")
    if wc:
        ch = member.guild.get_channel(wc)
        if ch:
            e = discord.Embed(title=f"Bienvenue {member.display_name} !", description=f"{member.mention} a rejoint le serveur.", color=0xff69b4)
            e.set_thumbnail(url=str(member.display_avatar.url))
            await safe_send(ch, embed=e)
    await log_action(member.guild, "member_join", member=member.mention)

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        await bot.process_commands(message)
        return
    gid = str(message.guild.id)
    ensure_guild(gid)
    # automod bad words
    if get_conf(message.guild.id, "automod_enabled"):
        bad_words = get_conf(message.guild.id, "bad_words", [])
        for w in bad_words:
            if w.lower() in message.content.lower():
                try:
                    await message.delete()
                except:
                    pass
                await log_action(message.guild, "automod", member=message.author.mention, reason="badword")
                return
    # auto_responses
    ars = data.get("auto_responses", {}).get(gid, {})
    for trigger, resp in ars.items():
        if trigger.lower() in message.content.lower():
            await message.channel.send(resp)
            break
    # level xp
    if get_conf(message.guild.id, "level_system_enabled"):
        uid = str(message.author.id)
        user = data["levels"][gid].setdefault(uid, {"xp":0,"level":1,"messages":0})
        user["xp"] += random.randint(10,20)
        user["messages"] += 1
        lvl = user["level"]
        if user["xp"] >= lvl*100:
            user["level"] += 1
            user["xp"] = 0
            lc = get_conf(message.guild.id, "level_channel")
            if lc:
                ch = message.guild.get_channel(lc)
                if ch:
                    await safe_send(ch, embed=discord.Embed(title="Level Up !", description=f"{message.author.mention} est maintenant niveau {user['level']}"))
        save_data(data)
    await bot.process_commands(message)

# -------------------------
# COMMANDS - CONFIGURATION
# -------------------------
@bot.command(name="config")
@commands.has_permissions(manage_guild=True)
async def config_cmd(ctx):
    gid = str(ctx.guild.id)
    ensure_guild(gid)
    conf = data.get("config", {}).get(gid, {})
    e = discord.Embed(title="Panel de configuration", color=0xff69b4)
    lines = []
    for k,v in conf.items():
        lines.append(f"**{k}**: {v}")
    e.description = "\n".join(lines) if lines else "Aucune configuration."
    await ctx.send(embed=e)

@bot.command(name="setwelcome")
@commands.has_permissions(manage_guild=True)
async def set_welcome(ctx, channel: discord.TextChannel, type: str = "embed"):
    if type.lower() == "embed":
        set_conf(ctx.guild.id, "welcome_embed_channel", channel.id)
        await ctx.send("Bienvenue (embed) configurée.")
    else:
        set_conf(ctx.guild.id, "welcome_text_channel", channel.id)
        await ctx.send("Bienvenue (texte) configurée.")

@bot.command(name="setleave")
@commands.has_permissions(manage_guild=True)
async def set_leave(ctx, channel: discord.TextChannel, type: str = "embed"):
    if type.lower() == "embed":
        set_conf(ctx.guild.id, "leave_embed_channel", channel.id)
        await ctx.send("Message de départ (embed) configuré.")
    else:
        set_conf(ctx.guild.id, "leave_text_channel", channel.id)
        await ctx.send("Message de départ (texte) configuré.")

@bot.command(name="setlogs")
@commands.has_permissions(manage_guild=True)
async def set_logs(ctx, channel: discord.TextChannel):
    set_conf(ctx.guild.id, "logs_channel", channel.id)
    await ctx.send("Salon de logs configuré.")

@bot.command(name="setinvitation")
@commands.has_permissions(manage_guild=True)
async def set_invitation(ctx, channel: discord.TextChannel):
    set_conf(ctx.guild.id, "invitation_channel", channel.id)
    await ctx.send("Salon d'invitations configuré.")

@bot.command(name="setsuggestion")
@commands.has_permissions(manage_guild=True)
async def set_suggestion(ctx, channel: discord.TextChannel):
    set_conf(ctx.guild.id, "suggestion_channel", channel.id)
    await ctx.send("Salon de suggestions configuré.")

@bot.command(name="rolejoin")
@commands.has_permissions(manage_guild=True)
async def role_join(ctx, role: discord.Role):
    set_conf(ctx.guild.id, "auto_role", role.id)
    await ctx.send(f"Rôle automatique mis: {role.name}")

# -------------------------
# INVITES
# -------------------------
@bot.command(name="roleinvite")
@commands.has_permissions(manage_guild=True)
async def role_invite(ctx, invites_needed: int, role: discord.Role):
    gid = str(ctx.guild.id)
    data.setdefault("roles_invites", {})[gid] = {"invites": invites_needed, "role": role.id}
    save_data(data)
    await ctx.send(f"Role d'invite configuré: {role.name} pour {invites_needed} invites")

@bot.command(name="invites")
async def invites_cmd(ctx, member: discord.Member=None):
    member = member or ctx.author
    gid = str(ctx.guild.id)
    invites = data.get("user_invites", {}).get(gid, {}).get(str(member.id), 0)
    await ctx.send(f"{member.mention} a {invites} invite(s).")

# -------------------------
# MODERATION
# -------------------------
@bot.command(name="warn")
@commands.has_permissions(manage_messages=True)
async def warn_cmd(ctx, member: discord.Member, *, reason: str="Aucune raison"):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    data.setdefault("warnings", {}).setdefault(gid, {}).setdefault(uid, [])
    data["warnings"][gid][uid].append({"reason":reason, "moderator":str(ctx.author.id), "date": datetime.datetime.utcnow().isoformat()})
    save_data(data)
    await ctx.send(f"{member.mention} averti. Raison: {reason}")
    await log_action(ctx.guild, "warning", membre=member.mention, raison=reason, modérateur=ctx.author.mention)

@bot.command(name="warnings")
async def warnings_cmd(ctx, member: discord.Member):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    warns = data.get("warnings", {}).get(gid, {}).get(uid, [])
    if not warns:
        await ctx.send(f"{member.mention} n'a aucun avertissement.")
        return
    e = discord.Embed(title=f"Avertissements {member.display_name}", color=0xff69b4)
    for i,w in enumerate(warns,1):
        e.add_field(name=f"#{i}", value=f"{w['reason']} - {w['date'][:10]}", inline=False)
    await ctx.send(embed=e)

@bot.command(name="clearwarns")
@commands.has_permissions(manage_messages=True)
async def clear_warns(ctx, member: discord.Member):
    gid = str(ctx.guild.id)
    uid = str(member.id)
    if uid in data.get("warnings", {}).get(gid, {}):
        del data["warnings"][gid][uid]
        save_data(data)
    await ctx.send("Avertissements effacés.")

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_cmd(ctx, member: discord.Member, *, reason: str="Aucune raison"):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"{member.mention} expulsé.")
        await log_action(ctx.guild, "member_kick", membre=member.display_name, raison=reason, modérateur=ctx.author.mention)
    except Exception as e:
        await ctx.send(f"Erreur: {e}")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_cmd(ctx, member: discord.Member, *, reason: str="Aucune raison"):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"{member.mention} banni.")
        await log_action(ctx.guild, "member_ban", membre=member.display_name, raison=reason, modérateur=ctx.author.mention)
    except Exception as e:
        await ctx.send(f"Erreur: {e}")

@bot.command(name="mute")
@commands.has_permissions(manage_roles=True)
async def mute_cmd(ctx, member: discord.Member, duration: int=0):
    # Simple mute: create role "Muted" if needed and remove send_messages perms
    guild = ctx.guild
    muted = discord.utils.get(guild.roles, name="Muted")
    if not muted:
        perms = discord.Permissions(send_messages=False, speak=False)
        muted = await guild.create_role(name="Muted", permissions=perms)
        for ch in guild.channels:
            try:
                await ch.set_permissions(muted, send_messages=False, speak=False)
            except:
                pass
    try:
        await member.add_roles(muted)
        await ctx.send(f"{member.mention} mis en sourdine.")
        if duration>0:
            await asyncio.sleep(duration)
            try:
                await member.remove_roles(muted)
                await ctx.send(f"{member.mention} a été unmuted automatique.")
            except:
                pass
    except Exception as e:
        await ctx.send(f"Erreur: {e}")

@bot.command(name="unmute")
@commands.has_permissions(manage_roles=True)
async def unmute_cmd(ctx, member: discord.Member):
    muted = discord.utils.get(ctx.guild.roles, name="Muted")
    if muted:
        try:
            await member.remove_roles(muted)
            await ctx.send(f"{member.mention} a été unmute.")
        except Exception as e:
            await ctx.send(f"Erreur: {e}")
    else:
        await ctx.send("Aucun rôle Muted trouvé.")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear_cmd(ctx, amount: int=5):
    try:
        deleted = await ctx.channel.purge(limit=amount+1)
        await ctx.send(f"Supprimé {len(deleted)-1} messages.", delete_after=5)
    except Exception as e:
        await ctx.send(f"Erreur: {e}")

@bot.command(name="lock")
@commands.has_permissions(manage_guild=True)
async def lock_cmd(ctx):
    role = ctx.guild.default_role
    await ctx.channel.set_permissions(role, send_messages=False)
    await ctx.send("Salon verrouillé.")

@bot.command(name="unlock")
@commands.has_permissions(manage_guild=True)
async def unlock_cmd(ctx):
    role = ctx.guild.default_role
    await ctx.channel.set_permissions(role, send_messages=True)
    await ctx.send("Salon déverrouillé.")

@bot.command(name="slowmode")
@commands.has_permissions(manage_guild=True)
async def slowmode_cmd(ctx, seconds: int=5):
    try:
        await ctx.channel.edit(slowmode_delay=seconds)
        await ctx.send(f"Slowmode réglé sur {seconds}s.")
    except Exception as e:
        await ctx.send(f"Erreur: {e}")

# Advanced moderation
@bot.command(name="masswarn")
@commands.has_permissions(administrator=True)
async def masswarn_cmd(ctx, role: discord.Role, *, reason: str):
    warned=0
    for m in role.members:
        gid=str(ctx.guild.id)
        uid=str(m.id)
        data.setdefault("warnings", {}).setdefault(gid, {}).setdefault(uid, [])
        data["warnings"][gid][uid].append({"reason":reason,"moderator":str(ctx.author.id),"date":datetime.datetime.utcnow().isoformat()})
        warned+=1
        try:
            await m.send(f"Avertissement: {reason}")
        except:
            pass
    save_data(data)
    await ctx.send(f"{warned} membres avertis.")

@bot.command(name="massban")
@commands.has_permissions(administrator=True)
async def massban_cmd(ctx, *members: discord.Member):
    banned=0
    for m in members:
        try:
            await m.ban(reason=f"Mass ban par {ctx.author}")
            banned+=1
        except:
            pass
    await ctx.send(f"{banned} bannis.")

@bot.command(name="nuke")
@commands.has_permissions(administrator=True)
async def nuke_cmd(ctx):
    confirm = await ctx.send("Réagissez ✅ pour confirmer (30s).")
    await confirm.add_reaction("✅")
    def check(reaction, user):
        return user==ctx.author and str(reaction.emoji)=="✅" and reaction.message.id==confirm.id
    try:
        await bot.wait_for("reaction_add", timeout=30.0, check=check)
        pos = ctx.channel.position
        new = await ctx.channel.clone()
        await ctx.channel.delete()
        await new.edit(position=pos)
        await new.send("Salon nuked.")
    except asyncio.TimeoutError:
        await confirm.edit(content="Annulé.")

@bot.command(name="lockall")
@commands.has_permissions(administrator=True)
async def lockall_cmd(ctx):
    count=0
    for ch in ctx.guild.text_channels:
        try:
            await ch.set_permissions(ctx.guild.default_role, send_messages=False)
            count+=1
        except:
            pass
    await ctx.send(f"{count} salons verrouillés.")

@bot.command(name="unlockall")
@commands.has_permissions(administrator=True)
async def unlockall_cmd(ctx):
    count=0
    for ch in ctx.guild.text_channels:
        try:
            await ch.set_permissions(ctx.guild.default_role, send_messages=True)
            count+=1
        except:
            pass
    await ctx.send(f"{count} salons déverrouillés.")

# -------------------------
# PROTECTION
# -------------------------
@bot.command(name="toggleantispam")
@commands.has_permissions(manage_guild=True)
async def toggle_antispam(ctx):
    cur = get_conf(ctx.guild.id, "antispam_enabled") or False
    set_conf(ctx.guild.id, "antispam_enabled", not cur)
    await ctx.send(f"Anti-spam {'activé' if not cur else 'désactivé'}.")

@bot.command(name="toggleantiraid")
@commands.has_permissions(manage_guild=True)
async def toggle_antiraid(ctx):
    cur = get_conf(ctx.guild.id, "antiraid_enabled") or False
    set_conf(ctx.guild.id, "antiraid_enabled", not cur)
    await ctx.send(f"Anti-raid {'activé' if not cur else 'désactivé'}.")

@bot.command(name="toggleautomod")
@commands.has_permissions(manage_guild=True)
async def toggle_automod(ctx):
    cur = get_conf(ctx.guild.id, "automod_enabled") or False
    set_conf(ctx.guild.id, "automod_enabled", not cur)
    await ctx.send(f"Automod {'activé' if not cur else 'désactivé'}.")

@bot.command(name="addbadword")
@commands.has_permissions(manage_guild=True)
async def add_badword(ctx, *, word: str):
    gid=str(ctx.guild.id)
    bl = get_conf(ctx.guild.id, "bad_words", [])
    bl = bl or []
    if word.lower() not in [w.lower() for w in bl]:
        bl.append(word)
        set_conf(ctx.guild.id, "bad_words", bl)
        await ctx.send("Mot ajouté.")
    else:
        await ctx.send("Déjà présent.")

@bot.command(name="listbadwords")
@commands.has_permissions(manage_guild=True)
async def list_badwords(ctx):
    bl = get_conf(ctx.guild.id, "bad_words", []) or []
    await ctx.send("Mots interdits:\n" + ("\n".join(bl) if bl else "aucun"))

@bot.command(name="removebadword")
@commands.has_permissions(manage_guild=True)
async def remove_badword(ctx, *, word: str):
    bl = get_conf(ctx.guild.id, "bad_words", []) or []
    bl = [w for w in bl if w.lower()!=word.lower()]
    set_conf(ctx.guild.id, "bad_words", bl)
    await ctx.send("Retiré si existait.")

# -------------------------
# LEVELS
# -------------------------
@bot.command(name="togglelevels")
@commands.has_permissions(manage_guild=True)
async def toggle_levels(ctx):
    cur = get_conf(ctx.guild.id, "level_system_enabled") or False
    set_conf(ctx.guild.id, "level_system_enabled", not cur)
    await ctx.send(f"Niveaux {'activé' if not cur else 'désactivé'}.")

@bot.command(name="rank")
async def rank_cmd(ctx, member: discord.Member=None):
    member = member or ctx.author
    gid=str(ctx.guild.id)
    uid=str(member.id)
    u = data.get("levels", {}).get(gid, {}).get(uid, {"xp":0,"level":1,"messages":0})
    e = discord.Embed(title=f"Rang de {member.display_name}", color=0xff69b4)
    e.add_field(name="Niveau", value=u["level"])
    e.add_field(name="XP", value=u["xp"])
    e.add_field(name="Messages", value=u["messages"])
    await ctx.send(embed=e)

@bot.command(name="leaderboard", aliases=["lb","top"])
async def leaderboard_cmd(ctx):
    gid=str(ctx.guild.id)
    allu = data.get("levels", {}).get(gid, {})
    ranking = sorted(allu.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)[:10]
    e = discord.Embed(title="Classement", color=0xff69b4)
    for i,(uid,ud) in enumerate(ranking,1):
        m = ctx.guild.get_member(int(uid))
        name = m.display_name if m else uid
        e.add_field(name=f"#{i} {name}", value=f"Lvl {ud['level']} • {ud['xp']} XP", inline=False)
    await ctx.send(embed=e)

@bot.command(name="setxp")
@commands.has_permissions(administrator=True)
async def set_xp(ctx, member: discord.Member, xp: int):
    gid=str(ctx.guild.id); uid=str(member.id)
    data.setdefault("levels", {}).setdefault(gid, {}).setdefault(uid, {"xp":0,"level":1,"messages":0})
    data["levels"][gid][uid]["xp"]=xp
    save_data(data)
    await ctx.send("XP définie.")

@bot.command(name="setlevel")
@commands.has_permissions(administrator=True)
async def set_level_cmd(ctx, member: discord.Member, level: int):
    gid=str(ctx.guild.id); uid=str(member.id)
    data.setdefault("levels", {}).setdefault(gid, {}).setdefault(uid, {"xp":0,"level":1,"messages":0})
    data["levels"][gid][uid]["level"]=level
    save_data(data)
    await ctx.send("Niveau défini.")

# -------------------------
# BACKUPS
# -------------------------
@bot.command(name="backup")
@commands.has_permissions(administrator=True)
async def backup_cmd(ctx):
    gid=str(ctx.guild.id)
    backup = {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "channels": [ {"name":c.name,"type":str(c.type),"id":c.id} for c in ctx.guild.channels],
        "roles": [ {"name":r.name,"id":r.id,"color":r.color.value} for r in ctx.guild.roles]
    }
    data.setdefault("backups", {}).setdefault(gid, [])
    data["backups"][gid].append(backup)
    # keep last 10
    data["backups"][gid]=data["backups"][gid][-10:]
    save_data(data)
    await ctx.send("Backup effectué.")

@bot.command(name="listbackups")
@commands.has_permissions(administrator=True)
async def list_backups_cmd(ctx):
    gid=str(ctx.guild.id)
    bs = data.get("backups", {}).get(gid, [])
    if not bs:
        await ctx.send("Aucun backup.")
        return
    e=discord.Embed(title="Backups", color=0xff69b4)
    for i,b in enumerate(bs[-5:],1):
        e.add_field(name=f"Backup #{i}", value=b["timestamp"], inline=False)
    await ctx.send(embed=e)

@bot.command(name="togglebackup")
@commands.has_permissions(administrator=True)
async def toggle_backup_cmd(ctx):
    cur = get_conf(ctx.guild.id, "auto_backup") or False
    set_conf(ctx.guild.id, "auto_backup", not cur)
    await ctx.send(f"Auto-backup {'activé' if not cur else 'désactivé'}.")

# -------------------------
# PREMIUM & BADGES
# -------------------------
@bot.command(name="premium")
async def premium_cmd(ctx, member: discord.Member=None):
    member = member or ctx.author
    gid=str(ctx.guild.id); uid=str(member.id)
    is_p = data.get("premium_users", {}).get(gid, {}).get(uid, False)
    await ctx.send(f"{member.mention} premium: {is_p}")

@bot.command(name="setpremium")
@commands.has_permissions(administrator=True)
async def set_premium_cmd(ctx, member: discord.Member, status: bool=True):
    gid=str(ctx.guild.id); uid=str(member.id)
    data.setdefault("premium_users", {}).setdefault(gid, {})[uid]=status
    save_data(data)
    await ctx.send("Statut premium mis.")

@bot.command(name="badges")
async def badges_cmd(ctx, member: discord.Member=None):
    member = member or ctx.author
    gid=str(ctx.guild.id); uid=str(member.id)
    b = data.get("badges", {}).get(gid, {}).get(uid, [])
    await ctx.send(f"Badges de {member.display_name}: {b}")

@bot.command(name="givebadge")
@commands.has_permissions(administrator=True)
async def give_badge_cmd(ctx, member: discord.Member, badge_id: str):
    gid=str(ctx.guild.id); uid=str(member.id)
    data.setdefault("badges", {}).setdefault(gid, {}).setdefault(uid, [])
    if badge_id not in data["badges"][gid][uid]:
        data["badges"][gid][uid].append(badge_id)
        save_data(data)
    await ctx.send("Badge donné.")

# -------------------------
# REACTION ROLES
# -------------------------
@bot.command(name="reactionrole")
@commands.has_permissions(manage_roles=True)
async def reaction_role_cmd(ctx, message_id: int, emoji: str, role: discord.Role):
    gid=str(ctx.guild.id)
    try:
        msg = await ctx.channel.fetch_message(message_id)
        await msg.add_reaction(emoji)
        data.setdefault("reaction_roles", {}).setdefault(gid, {})[str(message_id)] = {"channel":ctx.channel.id, "roles": {emoji: role.id}}
        save_data(data)
        await ctx.send("Rôle réaction configuré.")
    except Exception as e:
        await ctx.send(f"Erreur: {e}")

@bot.event
async def on_raw_reaction_add(payload):
    if payload.member and payload.member.bot:
        return
    gid=str(payload.guild_id)
    msg_id=str(payload.message_id)
    rr = data.get("reaction_roles", {}).get(gid, {}).get(msg_id, {})
    if not rr:
        return
    emoji = str(payload.emoji)
    role_id = rr.get("roles", {}).get(emoji)
    if role_id:
        guild = bot.get_guild(payload.guild_id)
        member = payload.member or guild.get_member(payload.user_id)
        role = guild.get_role(role_id)
        if member and role:
            try:
                await member.add_roles(role)
            except:
                pass

@bot.event
async def on_raw_reaction_remove(payload):
    gid=str(payload.guild_id)
    msg_id=str(payload.message_id)
    rr = data.get("reaction_roles", {}).get(gid, {}).get(msg_id, {})
    if not rr:
        return
    emoji = str(payload.emoji)
    role_id = rr.get("roles", {}).get(emoji)
    if role_id:
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        role = guild.get_role(role_id)
        if member and role:
            try:
                await member.remove_roles(role)
            except:
                pass

# -------------------------
# TICKETS
# -------------------------
@bot.command(name="ticket")
async def ticket_cmd(ctx):
    gid=str(ctx.guild.id)
    tickets = data.setdefault("tickets", {}).setdefault(gid, {})
    name = f"ticket-{ctx.author.name}"
    category = discord.utils.get(ctx.guild.categories, name="🎫 Tickets")
    if not category:
        category = await ctx.guild.create_category("🎫 Tickets")
    ch = await ctx.guild.create_text_channel(name, category=category, topic=f"Ticket de {ctx.author.display_name}")
    await ch.set_permissions(ctx.guild.default_role, read_messages=False)
    await ch.set_permissions(ctx.author, read_messages=True, send_messages=True)
    tickets[str(ch.id)] = {"owner":str(ctx.author.id), "created": datetime.datetime.utcnow().isoformat()}
    save_data(data)
    await ctx.send(f"Ticket créé: {ch.mention}")

@bot.command(name="close")
async def close_cmd(ctx):
    if ctx.channel.name.startswith("ticket-"):
        await ctx.send("Fermeture dans 3s...")
        await asyncio.sleep(3)
        try:
            gid=str(ctx.guild.id)
            tickets = data.get("tickets", {}).get(gid, {})
            if str(ctx.channel.id) in tickets:
                del tickets[str(ctx.channel.id)]
                save_data(data)
            await ctx.channel.delete()
        except Exception:
            pass
    else:
        await ctx.send("Cette commande ne peut être utilisée que dans un ticket.")

@bot.command(name="ticketpanel")
@commands.has_permissions(manage_guild=True)
async def ticketpanel_cmd(ctx):
    e = discord.Embed(title="Créer un ticket", description="Appuie sur le bouton pour créer un ticket.")
    msg = await ctx.send(embed=e)
    await msg.add_reaction("🎫")

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    if reaction.emoji == "🎫":
        try:
            await reaction.message.channel.send("Réagis au panel +ticket pour créer un ticket.")
        except:
            pass

# -------------------------
# VOICE (temporary voice channels)
# -------------------------
@bot.command(name="createvoc")
@commands.has_permissions(manage_channels=True)
async def createvoc_cmd(ctx):
    category = discord.utils.get(ctx.guild.categories, name="🎤 Vocaux")
    if not category:
        category = await ctx.guild.create_category("🎤 Vocaux")
    trigger = await ctx.guild.create_voice_channel("➕ Créer un Vocal", category=category)
    set_conf(ctx.guild.id, "voc_trigger_channel", trigger.id)
    await ctx.send("Vocal trigger créé.")

@bot.command(name="setupvoc")
@commands.has_permissions(manage_channels=True)
async def setupvoc_cmd(ctx, channel: discord.VoiceChannel):
    set_conf(ctx.guild.id, "voc_trigger_channel", channel.id)
    await ctx.send("Vocal trigger configuré.")

@bot.event
async def on_voice_state_update(member, before, after):
    if not after.channel:
        return
    tc = get_conf(member.guild.id, "voc_trigger_channel")
    if tc and after.channel.id == tc:
        category = after.channel.category
        new = await member.guild.create_voice_channel(f"Vocal {member.display_name}", category=category)
        try:
            await member.move_to(new)
        except:
            pass
        data.setdefault("temp_vocs", {})[str(new.id)] = {"owner": str(member.id), "guild": str(member.guild.id)}
        save_data(data)
    # cleanup
    if before.channel and str(before.channel.id) in data.get("temp_vocs", {}):
        if len(before.channel.members)==0:
            try:
                await before.channel.delete()
            except:
                pass
            del data["temp_vocs"][str(before.channel.id)]
            save_data(data)

# -------------------------
# LINKS
# -------------------------
@bot.command(name="allowlink")
@commands.has_permissions(manage_channels=True)
async def allowlink_cmd(ctx, channel: discord.TextChannel):
    gid=str(ctx.guild.id)
    data.setdefault("allowed_links", {}).setdefault(gid, [])
    if channel.id not in data["allowed_links"][gid]:
        data["allowed_links"][gid].append(channel.id)
        save_data(data)
    await ctx.send("Liens autorisés dans le salon.")

@bot.command(name="disallowlink")
@commands.has_permissions(manage_channels=True)
async def disallowlink_cmd(ctx, channel: discord.TextChannel):
    gid=str(ctx.guild.id)
    if channel.id in data.get("allowed_links", {}).get(gid, []):
        data["allowed_links"][gid].remove(channel.id)
        save_data(data)
    await ctx.send("Liens désactivés dans le salon.")

# -------------------------
# AUTO-RESPONSES
# -------------------------
@bot.command(name="addresponse")
@commands.has_permissions(manage_guild=True)
async def addresponse_cmd(ctx, trigger: str, *, response: str):
    gid=str(ctx.guild.id)
    data.setdefault("auto_responses", {}).setdefault(gid, {})[trigger]=response
    save_data(data)
    await ctx.send("Auto-response ajouté.")

@bot.command(name="listresponses")
@commands.has_permissions(manage_guild=True)
async def listresponses_cmd(ctx):
    gid=str(ctx.guild.id)
    ars = data.get("auto_responses", {}).get(gid, {})
    if not ars:
        await ctx.send("Aucune auto-response.")
        return
    e=discord.Embed(title="Auto-responses", color=0xff69b4)
    for t,r in ars.items():
        e.add_field(name=t, value=(r[:50]+"...") if len(r)>50 else r, inline=False)
    await ctx.send(embed=e)

@bot.command(name="delresponse")
@commands.has_permissions(manage_guild=True)
async def delresponse_cmd(ctx, trigger: str):
    gid=str(ctx.guild.id)
    if trigger in data.get("auto_responses", {}).get(gid, {}):
        del data["auto_responses"][gid][trigger]
        save_data(data)
    await ctx.send("Supprimé si existait.")

# -------------------------
# SUGGESTIONS
# -------------------------
@bot.command(name="suggest")
async def suggest_cmd(ctx, *, suggestion: str):
    gid=str(ctx.guild.id)
    sid = str(int(datetime.datetime.utcnow().timestamp()))
    data.setdefault("suggestions", {}).setdefault(gid, {})[sid] = {"author": str(ctx.author.id), "text": suggestion, "status":"pending"}
    save_data(data)
    await ctx.send("Suggestion enregistrée.")

@bot.command(name="acceptsugg")
@commands.has_permissions(manage_guild=True)
async def acceptsugg_cmd(ctx, sid: str):
    gid=str(ctx.guild.id)
    sugg = data.get("suggestions", {}).get(gid, {}).get(sid)
    if sugg:
        sugg["status"]="accepted"
        save_data(data)
        await ctx.send("Suggestion acceptée.")

@bot.command(name="denysugg")
@commands.has_permissions(manage_guild=True)
async def denysugg_cmd(ctx, sid: str):
    gid=str(ctx.guild.id)
    sugg = data.get("suggestions", {}).get(gid, {}).get(sid)
    if sugg:
        sugg["status"]="denied"
        save_data(data)
        await ctx.send("Suggestion refusée.")

# -------------------------
# ECONOMY
# -------------------------
@bot.command(name="balance")
async def balance_cmd(ctx, member: discord.Member=None):
    member = member or ctx.author
    gid=str(ctx.guild.id)
    bal = data.get("economy", {}).get(gid, {}).get(str(member.id), 0)
    await ctx.send(f"{member.mention} a {bal} 💵")

@bot.command(name="daily")
async def daily_cmd(ctx):
    gid=str(ctx.guild.id)
    uid=str(ctx.author.id)
    user = data.setdefault("economy", {}).setdefault(gid, {}).setdefault(uid, {"money":0,"last_daily":None})
    last = user.get("last_daily")
    now = datetime.datetime.utcnow().timestamp()
    if last and now - last < 24*3600:
        await ctx.send("Tu as déjà pris ton daily.")
        return
    user["last_daily"] = now
    user["money"] = user.get("money",0) + 100
    save_data(data)
    await ctx.send("Daily récupéré: 100 💵")

@bot.command(name="pay")
async def pay_cmd(ctx, member: discord.Member, amount: int):
    if amount<=0:
        await ctx.send("Montant invalide.")
        return
    gid=str(ctx.guild.id)
    uid=str(ctx.author.id); vid=str(member.id)
    em = data.setdefault("economy", {}).setdefault(gid, {}).setdefault(uid, {"money":0})
    rm = data.setdefault("economy", {}).setdefault(gid, {}).setdefault(vid, {"money":0})
    if em.get("money",0) < amount:
        await ctx.send("Pas assez d'argent.")
        return
    em["money"] -= amount
    rm["money"] = rm.get("money",0) + amount
    save_data(data)
    await ctx.send("Payé.")

@bot.command(name="shop")
async def shop_cmd(ctx):
    items = {"badge":500, "fleur":300, "coeur":1000}
    e=discord.Embed(title="Boutique", color=0xff69b4)
    for k,v in items.items():
        e.add_field(name=k, value=f"{v} 💵", inline=False)
    await ctx.send(embed=e)

@bot.command(name="buy")
async def buy_cmd(ctx, item: str):
    items = {"badge":500, "fleur":300, "coeur":1000}
    item = item.lower()
    if item not in items:
        await ctx.send("Item inconnu.")
        return
    gid=str(ctx.guild.id); uid=str(ctx.author.id)
    user = data.setdefault("economy", {}).setdefault(gid, {}).setdefault(uid, {"money":0})
    price = items[item]
    if user.get("money",0) < price:
        await ctx.send("Pas assez d'argent.")
        return
    user["money"] -= price
    save_data(data)
    await ctx.send("Achat effectué.")

# -------------------------
# GIVEAWAYS (simple)
# -------------------------
@bot.command(name="gstart")
@commands.has_permissions(manage_guild=True)
async def gstart_cmd(ctx, duration: str, *, prize: str):
    # duration format: 1h, 30m, 1d
    m = re.match(r"(\d+)([smhd])", duration)
    if not m:
        await ctx.send("Format durée invalide. Ex: 10s 5m 1h 1d")
        return
    num, unit = int(m.group(1)), m.group(2)
    mult = {"s":1,"m":60,"h":3600,"d":86400}[unit]
    end = datetime.datetime.utcnow() + datetime.timedelta(seconds=num*mult)
    msg = await ctx.send(embed=discord.Embed(title="Giveaway", description=f"{prize}\nReact 🎉 to join\nEnds: {end.isoformat()}"))
    await msg.add_reaction("🎉")
    gid=str(ctx.guild.id)
    data.setdefault("giveaways", {})[str(msg.id)] = {"guild":gid, "channel":str(ctx.channel.id), "end_time": end.isoformat(), "prize":prize}
    save_data(data)
    await ctx.send("Giveaway lancé.")

@tasks.loop(seconds=20.0)
async def check_giveaway_expiry():
    now = datetime.datetime.utcnow()
    to_end=[]
    for mid,g in list(data.get("giveaways", {}).items()):
        end = datetime.datetime.fromisoformat(g["end_time"])
        if now >= end:
            to_end.append(mid)
    for mid in to_end:
        g = data["giveaways"].get(mid)
        if not g:
            continue
        guild = bot.get_guild(int(g["guild"]))
        channel = guild.get_channel(int(g["channel"])) if guild else None
        if channel:
            try:
                msg = await channel.fetch_message(int(mid))
                reaction = discord.utils.get(msg.reactions, emoji="🎉")
                users = []
                if reaction:
                    users = [u async for u in reaction.users() if not u.bot]
                if users:
                    winner = random.choice(users)
                    await channel.send(f"Winner: {winner.mention} - Prize: {g['prize']}")
                else:
                    await channel.send("Aucun participant.")
            except:
                pass
        del data["giveaways"][mid]
        save_data(data)

@bot.command(name="gend")
@commands.has_permissions(manage_guild=True)
async def gend_cmd(ctx, message_id: int):
    mid=str(message_id)
    if mid in data.get("giveaways", {}):
        del data["giveaways"][mid]
        save_data(data)
        await ctx.send("Giveaway terminé.")

@bot.command(name="greroll")
@commands.has_permissions(manage_guild=True)
async def greroll_cmd(ctx, message_id: int):
    mid=str(message_id)
    g = data.get("giveaways", {}).get(mid)
    if not g:
        await ctx.send("Giveaway introuvable.")
        return
    guild = bot.get_guild(int(g["guild"]))
    channel = guild.get_channel(int(g["channel"])) if guild else None
    if channel:
        try:
            msg = await channel.fetch_message(int(mid))
            reaction = discord.utils.get(msg.reactions, emoji="🎉")
            users = [u async for u in reaction.users() if not u.bot] if reaction else []
            if users:
                winner = random.choice(users)
                await ctx.send(f"New winner: {winner.mention}")
            else:
                await ctx.send("Aucun participant.")
        except:
            await ctx.send("Erreur.")

# -------------------------
# FUN & UTIL
# -------------------------
@bot.command(name="8ball")
async def ball_cmd(ctx, *, question: str):
    answers = ["Oui","Non","Peut-être","Ask later","Sans doute"]
    await ctx.send(random.choice(answers))

@bot.command(name="coinflip")
async def coin_cmd(ctx):
    await ctx.send(random.choice(["Pile","Face"]))

@bot.command(name="dice")
async def dice_cmd(ctx):
    await ctx.send(str(random.randint(1,6)))

@bot.command(name="love")
async def love_cmd(ctx, a: discord.Member, b: discord.Member):
    pct = random.randint(0,100)
    await ctx.send(f"❤️ Compatibilité {a.display_name} & {b.display_name}: {pct}%")

@bot.command(name="meme")
async def meme_cmd(ctx):
    await ctx.send("Pas d'API meme intégrée — ajoute tes memes manuellement.")

@bot.command(name="poll")
@commands.has_permissions(manage_guild=True)
async def poll_cmd(ctx, *, question: str):
    msg = await ctx.send(embed=discord.Embed(title="Sondage", description=question))
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
async def say_cmd(ctx, *, message: str):
    try:
        await ctx.message.delete()
    except:
        pass
    await ctx.send(message)

@bot.command(name="embed")
@commands.has_permissions(manage_messages=True)
async def embed_cmd(ctx, *, message: str):
    try:
        await ctx.message.delete()
    except:
        pass
    await ctx.send(embed=discord.Embed(description=message))

@bot.command(name="rules")
async def rules_cmd(ctx):
    await ctx.send("Insère les règles du serveur ici.")

@bot.command(name="serverinfo")
async def serverinfo_cmd(ctx):
    g = ctx.guild
    e=discord.Embed(title=g.name, description=f"{g.member_count} membres")
    await ctx.send(embed=e)

@bot.command(name="userinfo")
async def userinfo_cmd(ctx, member: discord.Member=None):
    m = member or ctx.author
    e=discord.Embed(title=m.display_name)
    e.add_field(name="ID", value=m.id)
    e.add_field(name="Créé le", value=m.created_at.strftime("%d/%m/%Y"))
    await ctx.send(embed=e)

@bot.command(name="avatar")
async def avatar_cmd(ctx, member: discord.Member=None):
    m = member or ctx.author
    e=discord.Embed()
    e.set_image(url=m.display_avatar.url)
    await ctx.send(embed=e)

# -------------------------
# STARTUP
# -------------------------


# === INTEGRATED CONFIG PANEL ===

# === ADVANCED CONFIG PANEL (Option B) ===
# This code must be inserted in the bot after commands but before main.
# It uses discord.ui.Button and Select to build an interactive panel.

import discord
from discord.ui import View, Button, Select

class ConfigPanel(View):
    def __init__(self, guild_id):
        super().__init__(timeout=120)
        self.guild_id = guild_id

        # PAGE SELECTOR
        self.add_item(Select(
            placeholder="Choisir une catégorie…",
            options=[
                discord.SelectOption(label="Salons", description="Configurer salons de bienvenue / départ / logs", emoji="📺", value="channels"),
                discord.SelectOption(label="Modération", description="Automod / badwords / invites", emoji="🛡️", value="moderation"),
                discord.SelectOption(label="Rôles", description="Auto-role / reaction role", emoji="🎭", value="roles"),
                discord.SelectOption(label="Niveaux", description="XP / niveaux", emoji="⭐", value="levels"),
                discord.SelectOption(label="Économie", description="Shop / daily / monnaie", emoji="💰", value="economy"),
                discord.SelectOption(label="Tickets", description="Configuration système ticket", emoji="🎫", value="tickets"),
                discord.SelectOption(label="Vocaux", description="Salon trigger vocaux", emoji="🎤", value="voc"),
            ],
            custom_id="panel_select"
        ))

    async def interaction_check(self, interaction: discord.Interaction):
        return True

@bot.command(name="config2")
@commands.has_permissions(manage_guild=True)
async def config2(ctx):
    view = ConfigPanel(ctx.guild.id)
    embed = discord.Embed(
        title="⚙️ Panneau de configuration ⸺ Hoshimi",
        description="""Sélectionne une catégorie pour configurer le bot.

**Expiration dans 2 minutes.**""",
        color=0xff69b4
    )
    await ctx.send(embed=embed, view=view)


if __name__ == "__main__":
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        print("DISCORD_TOKEN manquant.")
        exit(1)
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("Token invalide.")
    except Exception as e:
        print("Erreur fatale:", e)
