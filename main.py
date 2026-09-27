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
# 🌙 LUNE ECONOMY
# =========================

import sqlite3
import random
import time

# ID Discord của CHỦ SỞ HỮU BOT
BOT_OWNER_ID = 123456789012345678

db = sqlite3.connect("lune_economy.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 0
)
""")

db.commit()


def get_balance(user_id):
    user_id = str(user_id)

    cursor.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (user_id,)
    )

    result = cursor.fetchone()

    if result is None:
        cursor.execute(
            "INSERT INTO users (user_id, balance) VALUES (?, 0)",
            (user_id,)
        )
        db.commit()
        return 0

    return result[0]


def add_money(user_id, amount):
    user_id = str(user_id)

    get_balance(user_id)

    cursor.execute(
        """
        UPDATE users
        SET balance = balance + ?
        WHERE user_id = ?
        """,
        (amount, user_id)
    )

    db.commit()


# =========================
# 💰 l!balance
# =========================

@bot.command()
async def balance(ctx, member: discord.Member = None):

    member = member or ctx.author
    money = get_balance(member.id)

    await ctx.send(
        f"🌙 **Ví Xu Lune**\n"
        f"👤 {member.mention}\n"
        f"💰 `{money:,} Xu Lune`"
    )


# =========================
# 🎁 l!daily
# =========================

daily_cd = {}

@bot.command()
async def daily(ctx):

    user_id = ctx.author.id
    now = time.time()

    if user_id in daily_cd:

        remaining = 86400 - (
            now - daily_cd[user_id]
        )

        if remaining > 0:

            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)

            await ctx.send(
                f"⏳ Bạn đã nhận Daily rồi!\n"
                f"╰┈➤ Còn `{hours}h {minutes}m`."
            )
            return

    amount = 500

    add_money(user_id, amount)
    daily_cd[user_id] = now

    await ctx.send(
        f"🎁 **Daily thành công!**\n"
        f"╰┈➤ +💰 `{amount:,} Xu Lune`"
    )


# =========================
# 💼 l!work
# =========================

work_cd = {}

@bot.command()
async def work(ctx):

    user_id = ctx.author.id
    now = time.time()

    if user_id in work_cd:

        remaining = 60 - (
            now - work_cd[user_id]
        )

        if remaining > 0:

            await ctx.send(
                f"⏳ Bạn đang nghỉ!\n"
                f"╰┈➤ Thử lại sau `{int(remaining)}s`."
            )
            return

    jobs = [
        "🌙 Trực đêm tại Lune Haven",
        "☕ Làm việc tại quán cà phê",
        "🎮 Chơi game cùng thành viên",
        "🎧 Chạy nhạc cho server",
        "📖 Hỗ trợ thành viên",
        "✨ Làm nhiệm vụ tại Lune Haven"
    ]

    job = random.choice(jobs)
    amount = random.randint(50, 200)

    add_money(user_id, amount)
    work_cd[user_id] = now

    await ctx.send(
        f"{job}\n"
        f"╰┈➤ +💰 `{amount:,} Xu Lune`"
    )


# =========================
# 💸 l!give
# =========================

@bot.command()
async def give(
    ctx,
    member: discord.Member,
    amount: int
):

    if member == ctx.author:
        await ctx.send(
            "❌ Không thể tự chuyển Xu cho mình."
        )
        return

    if amount <= 0:
        await ctx.send(
            "❌ Số Xu phải lớn hơn 0."
        )
        return

    balance = get_balance(ctx.author.id)

    if balance < amount:

        await ctx.send(
            f"❌ Bạn không đủ Xu.\n"
            f"╰┈➤ Số dư: `{balance:,} Xu Lune`"
        )
        return

    add_money(ctx.author.id, -amount)
    add_money(member.id, amount)

    await ctx.send(
        f"💸 **Chuyển Xu thành công!**\n"
        f"╰┈➤ {ctx.author.mention} → {member.mention}\n"
        f"💰 `{amount:,} Xu Lune`"
    )


# =========================
# 🏆 l!rich
# =========================

@bot.command()
async def rich(ctx):

    cursor.execute("""
        SELECT user_id, balance
        FROM users
        ORDER BY balance DESC
        LIMIT 10
    """)

    users = cursor.fetchall()

    if not users:
        await ctx.send(
            "🌙 Chưa có dữ liệu Xu Lune."
        )
        return

    text = ""

    for index, (user_id, money) in enumerate(
        users, start=1
    ):

        user = bot.get_user(int(user_id))

        name = (
            user.display_name
            if user
            else f"User {user_id}"
        )

        text += (
            f"**{index}.** {name}"
            f" — 💰 `{money:,}` Xu\n"
        )

    embed = discord.Embed(
        title="🏆・LUNE RICH",
        description=text
    )

    await ctx.send(embed=embed)


# =========================
# 👑 l!hackxu
# CHỈ OWNER BOT
# =========================

@bot.command()
async def hackxu(
    ctx,
    member: discord.Member,
    amount: int
):

    if ctx.author.id != BOT_OWNER_ID:<@1522168539178598592>

        await ctx.send(
            "❌ Bạn không có quyền sử dụng lệnh này."
        )
        return

    if amount <= 0:

        await ctx.send(
            "❌ Số Xu phải lớn hơn 0."
        )
        return

    add_money(member.id, amount)

    await ctx.send(
        f"👑 **Luna Owner Panel**\n"
        f"💰 Đã thêm `{amount:,} Xu Lune` cho "
        f"{member.mention}."
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
