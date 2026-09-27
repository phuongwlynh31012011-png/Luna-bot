import os
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="l!",
    intents=intents,
    help_command=None
)


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"🌙 Luna đã online: {bot.user}")


# =========================
# /help
# =========================

@bot.tree.command(
    name="help",
    description="Xem bảng điều khiển lệnh của Luna"
)
async def help_command(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🌙 Luna — Help",
        description=(
            "╭───────────────╮\n"
            "     **LUNA COMMANDS**\n"
            "╰───────────────╯\n\n"

            "👤 **MEMBER**\n"
            "`l!ping` — Kiểm tra Luna\n"
            "`l!server` — Thông tin server\n"
            "`l!avatar` — Xem avatar\n"
            "`l!userinfo` — Thông tin thành viên\n"
            "`l!botinfo` — Thông tin Luna\n\n"

            "🛡️ **ADMIN**\n"
            "`l!clear` — Xóa tin nhắn\n"
            "`l!kick` — Kick thành viên\n"
            "`l!ban` — Ban thành viên\n\n"

            "🌙 **SLASH**\n"
            "`/help` — Bảng điều khiển\n"
            "`/hello` — Luna chào bạn"
        )
    )

    await interaction.response.send_message(embed=embed)


# =========================
# /hello
# =========================

@bot.tree.command(
    name="hello",
    description="Luna chào bạn"
)
async def hello(interaction: discord.Interaction):

    await interaction.response.send_message(
        f"🌙 Xin chào {interaction.user.mention}!\n"
        "╰┈➤ Chào mừng bạn đến với **Lune Haven** ♡"
    )


# =========================
# l!ping
# =========================

@bot.command()
async def ping(ctx):

    await ctx.send(
        f"🏓 Pong! `{round(bot.latency * 1000)}ms`"
    )


# =========================
# l!server
# =========================

@bot.command()
async def server(ctx):

    guild = ctx.guild

    embed = discord.Embed(
        title=f"🌙 {guild.name}",
        description=f"👥 Thành viên: `{guild.member_count}`"
    )

    await ctx.send(embed=embed)


# =========================
# l!avatar
# =========================

@bot.command()
async def avatar(ctx):

    await ctx.send(
        ctx.author.display_avatar.url
    )


# =========================
# l!userinfo
# =========================

@bot.command()
async def userinfo(ctx):

    member = ctx.author

    embed = discord.Embed(
        title=f"👤 {member.display_name}",
        description=(
            f"Username: `{member.name}`\n"
            f"ID: `{member.id}`"
        )
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    await ctx.send(embed=embed)


# =========================
# l!botinfo
# =========================

@bot.command()
async def botinfo(ctx):

    await ctx.send(
        "🌙 **Luna**\n"
        "Bot đồng hành của **Lune Haven**.\n"
        "Quản lý • Tiện ích • Giải trí"
    )


# =========================
# l!clear — ADMIN
# =========================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):

    if amount < 1 or amount > 100:
        await ctx.send("❌ Nhập số từ `1` đến `100`.")
        return

    await ctx.channel.purge(limit=amount + 1)

    await ctx.send(
        f"🧹 Đã xóa `{amount}` tin nhắn."
    )


# =========================
# l!kick — ADMIN
# =========================

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member):

    await member.kick()

    await ctx.send(
        f"👢 Đã kick {member.mention}."
    )


# =========================
# l!ban — ADMIN
# =========================

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member):

    await member.ban()

    await ctx.send(
        f"🔨 Đã ban {member.mention}."
    )


# =========================
# TOKEN
# =========================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("Chưa có DISCORD_TOKEN!")

bot.run(TOKEN)
