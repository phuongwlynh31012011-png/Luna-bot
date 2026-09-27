import os
import discord
from discord.ext import commands
from datetime import timedelta

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="l!",
    intents=intents,
    help_command=None
)


# =========================
# BOT ONLINE
# =========================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"🌙 Luna đã online: {bot.user}")


# =========================
# SLASH: /help
# =========================

@bot.tree.command(
    name="help",
    description="Mở bảng điều khiển lệnh của Luna"
)
async def help_command(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🌙・LUNA HELP",
        description=(
            "╰┈➤ Bảng điều khiển lệnh Luna\n\n"
            "👤 **MEMBER**\n"
            "`l!ping` — Kiểm tra Luna\n"
            "`l!avatar` — Xem avatar\n"
            "`l!server` — Thông tin server\n"
            "`l!userinfo` — Thông tin thành viên\n"
            "`l!botinfo` — Thông tin Luna\n\n"

            "🛡️ **ADMIN**\n"
            "`l!clear` — Xóa tin nhắn\n"
            "`l!kick` — Kick thành viên\n"
            "`l!ban` — Ban thành viên\n"
            "`l!timeout` — Timeout thành viên"
        )
    )

    await interaction.response.send_message(embed=embed)


# =========================
# SLASH: /hello
# =========================

@bot.tree.command(
    name="hello",
    description="Luna chào bạn"
)
async def hello(interaction: discord.Interaction):

    await interaction.response.send_message(
        f"🌙 Xin chào {interaction.user.mention}!\n"
        "╰┈➤ Chào mừng bạn đến với Lune Haven ♡"
    )


# =========================
# l!ping
# =========================

@bot.command()
async def ping(ctx):

    ping = round(bot.latency * 1000)

    await ctx.send(
        f"🌙 **Luna Pong!**\n"
        f"╰┈➤ `{ping}ms`"
    )


# =========================
# l!avatar
# =========================

@bot.command()
async def avatar(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = discord.Embed(
        title=f"🌙 Avatar — {member.display_name}"
    )

    embed.set_image(url=member.display_avatar.url)

    await ctx.send(embed=embed)


# =========================
# l!server
# =========================

@bot.command()
async def server(ctx):

    guild = ctx.guild

    await ctx.send(
        f"🌙 **{guild.name}**\n"
        f"👥 Thành viên: `{guild.member_count}`\n"
        f"🆔 ID: `{guild.id}`"
    )


# =========================
# l!userinfo
# =========================

@bot.command()
async def userinfo(ctx, member: discord.Member = None):

    member = member or ctx.author

    embed = discord.Embed(
        title=f"👤・{member.display_name}",
        description=(
            f"Username: `{member.name}`\n"
            f"ID: `{member.id}`"
        )
    )

    embed.set_thumbnail(url=member.display_avatar.url)

    await ctx.send(embed=embed)


# =========================
# l!botinfo
# =========================

@bot.command()
async def botinfo(ctx):

    await ctx.send(
        "🌙 **Luna**\n"
        "Bot đồng hành của **Lune Haven**."
    )


# =========================
# ADMIN: l!clear
# =========================

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):

    if amount < 1 or amount > 100:
        await ctx.send("❌ Nhập số từ `1` đến `100`.")
        return

    await ctx.channel.purge(limit=amount + 1)

    msg = await ctx.send(
        f"🧹 Đã xóa `{amount}` tin nhắn."
    )

    await msg.delete(delay=3)


# =========================
# ADMIN: l!kick
# =========================

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(
    ctx,
    member: discord.Member,
    *,
    reason="Không có lý do"
):

    await member.kick(reason=reason)

    await ctx.send(
        f"👢 Đã kick {member.mention}\n"
        f"📝 Lý do: {reason}"
    )


# =========================
# ADMIN: l!ban
# =========================

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(
    ctx,
    member: discord.Member,
    *,
    reason="Không có lý do"
):

    await member.ban(reason=reason)

    await ctx.send(
        f"🔨 Đã ban {member.mention}\n"
        f"📝 Lý do: {reason}"
    )


# =========================
# ADMIN: l!timeout
# =========================

@bot.command()
@commands.has_permissions(moderate_members=True)
async def timeout(
    ctx,
    member: discord.Member,
    minutes: int,
    *,
    reason="Không có lý do"
):

    if minutes < 1 or minutes > 40320:
        await ctx.send(
            "❌ Thời gian phải từ `1` đến `40320` phút."
        )
        return

    await member.timeout(
        timedelta(minutes=minutes),
        reason=reason
    )

    await ctx.send(
        f"🔇 Đã timeout {member.mention} "
        f"trong `{minutes}` phút.\n"
        f"📝 Lý do: {reason}"
    )


# =========================
# LỖI QUYỀN
# =========================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "🛡️ Bạn không có quyền sử dụng lệnh này."
        )
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ Bạn chưa nhập đủ thông tin."
        )
        return

    print(f"ERROR: {error}")


# =========================
# TOKEN
# =========================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError(
        "❌ Chưa tìm thấy DISCORD_TOKEN trên Railway."
    )

bot.run(TOKEN)
