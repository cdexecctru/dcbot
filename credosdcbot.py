import discord
from discord.ext import commands, tasks
import asyncio
import random
import aiohttp
import datetime
import requests
import os
from flask import Flask
from threading import Thread

# --- RENDER İÇİN WEB SUNUCUSU ---
app = Flask('')

@app.route('/')
def home():
    return "Credos Bot is Alive!"

def run():
    # Render'ın portunu kullan, yoksa 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- Settings ---
TOKEN_URL = "https://script.google.com/macros/s/AKfycbwdEadsb5f6UIzd2qrQ2txinQfXPiDooJ_zfx7LdT7Nw6tj2T2RgAgAHN7zOS4XoZgk/exec"

def get_token():
    try:
        response = requests.get(TOKEN_URL)
        if response.status_code == 200:
            return response.text.strip()
        return None
    except:
        return None

TOKEN = get_token()
PREFIX = "!"
MINECRAFT_SERVER_ADDRESS = "street-brakes.gl.joinmc.link:14056"
MINECRAFT_VERSION_DISPLAY = "1.21.X" 

# --- DYNAMIC CONFIGURATION ---
TICKET_CHANNEL_ID = 1446826531526676510  
TICKET_CATEGORY_ID = 1446826522106265702 
SUPPORT_ROLE_ID = 1446826525847589016    

VOICE_CHANNEL_ID = 1446826556768129044    
VOICE_CATEGORY_ID = 1446826531723804818  

intents = discord.Intents.default()
intents.reactions = True 
intents.members = True   
intents.message_content = True 
intents.voice_states = True 

bot = commands.Bot(command_prefix=PREFIX, intents=intents)

@bot.event
async def on_ready():
    print(f'🤖 Bot Name: {bot.user.name}')
    print(f'🆔 Bot ID: {bot.user.id}')
    print('-----------------------')
    update_mc_status.start()
    print('✅ Status Updater Task Started.')

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id or payload.channel_id != TICKET_CHANNEL_ID:
        return

    if str(payload.emoji) == "🎫":
        guild = bot.get_guild(payload.guild_id)
        member = guild.get_member(payload.user_id)
        channel = bot.get_channel(payload.channel_id)

        try:
            message = await channel.fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji, member)
        except:
            pass 
        
        if TICKET_CATEGORY_ID:
            category = bot.get_channel(TICKET_CATEGORY_ID)
            if category:
                for chan in category.channels:
                    if chan.name.startswith(f"ticket-{member.id}"):
                        await member.send(f"⚠️ You already have an open ticket: {chan.mention}. Please close it first.")
                        return

        await open_ticket_process(guild, member, "Support Request via Reaction")

async def open_ticket_process(guild, member, reason):
    if not TICKET_CATEGORY_ID:
        await member.send("❌ Ticket System Setup is incomplete.")
        return

    category = bot.get_channel(TICKET_CATEGORY_ID)
    support_role = guild.get_role(SUPPORT_ROLE_ID) if SUPPORT_ROLE_ID else None

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    if support_role:
        overwrites[support_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    
    channel_name = f"ticket-{member.id}"
    
    try:
        new_channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"New ticket opened by {member.name}"
        )

        support_role_mention = support_role.mention if support_role else "**Staff Team**"
        
        embed = discord.Embed(
            title=f"🎫 New Ticket: {reason}",
            description=f"{support_role_mention} will assist you shortly.",
            color=discord.Color.blue()
        )
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.set_footer(text=f"Use {PREFIX}close to close the ticket.")
        
        await new_channel.send(f"{member.mention}, {support_role_mention}", embed=embed)
        await member.send(f"✅ Your ticket has been created: {new_channel.mention}")

    except discord.Forbidden:
        await member.send("❌ Permission error.")
    except Exception as e:
        print(f"Error: {e}")

@bot.event
async def on_voice_state_update(member, before, after):
    if not VOICE_CHANNEL_ID or not VOICE_CATEGORY_ID:
        return

    if after.channel and after.channel.id == VOICE_CHANNEL_ID:
        new_channel_name = f"Private Room - {member.name}"
        category = bot.get_channel(VOICE_CATEGORY_ID)
        overwrites = {
            member: discord.PermissionOverwrite(manage_channels=True, manage_roles=True, connect=True, speak=True),
            member.guild.default_role: discord.PermissionOverwrite(speak=True, view_channel=True)
        }

        try:
            new_voice_channel = await category.create_voice_channel(new_channel_name, overwrites=overwrites)
            await member.move_to(new_voice_channel)
        except Exception as e:
            print(f"Voice Error: {e}")

    if before.channel and before.channel.category_id == VOICE_CATEGORY_ID and before.channel.id != VOICE_CHANNEL_ID:
        if len(before.channel.members) == 0:
            await asyncio.sleep(5) 
            if len(before.channel.members) == 0:
                try:
                    await before.channel.delete()
                except:
                    pass

@bot.command(name='gstart')
@commands.has_permissions(manage_messages=True) 
async def start_giveaway(ctx, duration_minutes: int, winner_count: int, *, prize: str):
    duration_seconds = duration_minutes * 60
    end_time = discord.utils.utcnow() + datetime.timedelta(seconds=duration_seconds)

    embed = discord.Embed(
        title=f"🎉 GIVEAWAY: {prize}",
        description=f"React with 🎉 to enter! \nNumber of Winners: **{winner_count}**",
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Ends:")
    embed.timestamp = end_time

    giveaway_message = await ctx.send("🎉 **NEW GIVEAWAY!** 🎉", embed=embed)
    await giveaway_message.add_reaction("🎉")
    await ctx.send(f"✅ Giveaway started!", delete_after=5)

    await asyncio.sleep(duration_seconds)
    await select_winner(ctx.channel, giveaway_message.id, prize, winner_count)

async def select_winner(channel, message_id, prize, winner_count):
    try:
        reaction_message = await channel.fetch_message(message_id)
        reaction = discord.utils.get(reaction_message.reactions, emoji="🎉")
        
        users = [user async for user in reaction.users() if user != bot.user] if reaction else []
        
        if not users or len(users) < winner_count:
            current_embed = reaction_message.embeds[0]
            current_embed.description = "⚠️ No winner selected (insufficient participation)."
            await reaction_message.edit(embed=current_embed)
            return

        winners = random.sample(users, winner_count)
        winners_mentions = ", ".join([w.mention for w in winners])

        await channel.send(f"🎊 **GIVEAWAY RESULT!** 🎊 \nWinners: {winners_mentions}")

        current_embed = reaction_message.embeds[0]
        current_embed.description = f"**🏆 WINNERS:** {winners_mentions}"
        current_embed.color = discord.Color.green()
        await reaction_message.edit(embed=current_embed)
    except:
        pass

@bot.command(name='ip')
async def minecraft_status(ctx):
    api_url = f"https://api.mcstatus.io/v2/status/java/{MINECRAFT_SERVER_ADDRESS}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                if response.status != 200:
                    await ctx.send("❌ API error.")
                    return

                data = await response.json()
                is_online = data.get('online', False)
                public_ip = "play.credos.qzz.io"
                
                online_players = data.get('players', {}).get('online', 0)
                max_players = data.get('players', {}).get('max', 0)

                color = discord.Color.green() if is_online else discord.Color.red()
                title = "✅ ONLINE" if is_online else "🔴 OFFLINE"
                
                embed = discord.Embed(title=f"Server Status: {title}", color=color)
                embed.add_field(name="🌐 IP Address", value=f"`{public_ip}`", inline=False)
                embed.add_field(name="🎮 Players", value=f"**{online_players}** / {max_players}", inline=True)
                embed.add_field(name="⚙️ Version", value=f"**{MINECRAFT_VERSION_DISPLAY}**", inline=True)
                
                if data.get('favicon'):
                    embed.set_thumbnail(url=data['favicon']) 
                
                await ctx.send(embed=embed)
        except Exception as e:
            print(f"Error: {e}")

@bot.command(name='ticketsetup')
@commands.has_permissions(administrator=True)
async def ticket_setup(ctx, category: discord.CategoryChannel, support_role: discord.Role):
    global TICKET_CHANNEL_ID, TICKET_CATEGORY_ID, SUPPORT_ROLE_ID
    TICKET_CATEGORY_ID = category.id
    SUPPORT_ROLE_ID = support_role.id
    
    embed = discord.Embed(title="🎫 Support Ticket", description="React with 🎫 to open a ticket.", color=discord.Color.blue())
    setup_message = await ctx.send(embed=embed)
    await setup_message.add_reaction("🎫")
    TICKET_CHANNEL_ID = ctx.channel.id
    await ctx.send("✅ Done.", delete_after=5)

@bot.command(name='close')
@commands.has_permissions(administrator=True)
async def close_ticket(ctx):
    if not ctx.channel.name.startswith("ticket-"):
        return
    await ctx.send("🗑️ Deleting in 10s...")
    await asyncio.sleep(10)
    await ctx.channel.delete()

@tasks.loop(minutes=5)
async def update_mc_status():
    api_url = f"https://api.mcstatus.io/v2/status/java/{MINECRAFT_SERVER_ADDRESS}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url) as response:
                data = await response.json()
                is_online = data.get('online', False)
                players = data.get('players', {}).get('online', 0)
                
                activity = discord.Game(name=f"{players} Players" if is_online else "Offline")
                status = discord.Status.online if is_online else discord.Status.dnd
                await bot.change_presence(activity=activity, status=status)
        except:
            pass

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(error)

if __name__ == "__main__":
    if TOKEN:
        keep_alive() # Render için web sunucusunu başlatır
        bot.run(TOKEN) # Botu başlatır
    else:
        print("❌ Token alınamadı!")
