import os
import random
import sqlite3
import asyncio
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from discord import app_commands


# =========================================================
# CẤU HÌNH
# =========================================================

TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))

PREFIXES = ("l!", "L!")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=PREFIXES,
    intents=intents,
    help_command=None
)


# =========================================================
# DATABASE
# =========================================================

db = sqlite3.connect("luna.db")
db.row_factory = sqlite3.Row
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    xu INTEGER DEFAULT 0,
    daily_at TEXT DEFAULT '',
    work_at TEXT DEFAULT ''
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    user_id INTEGER,
    moderator_id INTEGER,
    reason TEXT,
    created_at TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS marriages (
    user1 INTEGER PRIMARY KEY,
    user2 INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS loves (
    user_id INTEGER PRIMARY KEY,
    text TEXT
)
""")

db.commit()


# =========================================================
# HÀM DATABASE
# =========================================================

def ensure_user(user_id: int):
    cur.execute(
        "INSERT OR IGNORE INTO users(user_id, xu) VALUES(?, 0)",
        (user_id,)
    )
    db.commit()


def get_xu(user_id: int):
    ensure_user(user_id)
    row = cur.execute(
        "SELECT xu FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()
    return row["xu"]


def add_xu(user_id: int, amount: int):
    ensure_user(user_id)
    cur.execute(
        "UPDATE users SET xu = xu + ? WHERE user_id=?",
        (amount, user_id)
    )
    db.commit()


def set_xu(user_id: int, amount: int):
    ensure_user(user_id)
    cur.execute(
        "UPDATE users SET xu=? WHERE user_id=?",
        (max(0, amount), user_id)
    )
    db.commit()


def get_cooldown(user_id: int, typ: str):
    ensure_user(user_id)
    row = cur.execute(
        f"SELECT {typ}_at FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    value = row[f"{typ}_at"]

    if not value:
        return None

    try:
        return datetime.fromisoformat(value)
    except:
        return None


def set_cooldown(user_id: int, typ: str):
    cur.execute(
        f"UPDATE users SET {typ}_at=? WHERE user_id=?",
        (datetime.now().isoformat(), user_id)
    )
    db.commit()


# =========================================================
# EMBED
# =========================================================

def luna_embed(title, description="", color=0xB77CFF):
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now()
    )
    embed.set_footer(text="🌙 Luna")
    return embed


# =========================================================
# KIỂM TRA OWNER
# =========================================================

def owner_only():
    async def predicate(ctx):
        if ctx.author.id != OWNER_ID:
            await ctx.send(
                "❌ Lệnh này chỉ dành cho **Owner Bot**.",
                delete_after=5
            )
            return False
        return True

    return commands.check(predicate)


# =========================================================
# KIỂM TRA ADMIN
# =========================================================

def admin_only():
    async def predicate(ctx):
        if not ctx.author.guild_permissions.administrator:
            await ctx.send(
                "❌ Lệnh này chỉ dành cho **Admin**.",
                delete_after=5
            )
            return False
        return True

    return commands.check(predicate)


# =========================================================
# HELP MENU
# =========================================================

class HelpSelect(discord.ui.Select):
    def __init__(self, owner_id):
        self.owner_id = owner_id

        options = [
            discord.SelectOption(
                label="Tiền Lune",
                value="money",
                emoji="💰"
            ),
            discord.SelectOption(
                label="Trò chơi",
                value="games",
                emoji="🎮"
            ),
            discord.SelectOption(
                label="SETL",
                value="setl",
                emoji="💗"
            ),
            discord.SelectOption(
                label="Giveaway",
                value="giveaway",
                emoji="🎁"
            ),
            discord.SelectOption(
                label="Cảnh báo",
                value="warn",
                emoji="⚠️"
            ),
            discord.SelectOption(
                label="Quản lý",
                value="admin",
                emoji="🛡️"
            ),
            discord.SelectOption(
                label="Owner Bot",
                value="owner",
                emoji="👑"
            )
        ]

        super().__init__(
            placeholder="Chọn danh mục",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Đây không phải bảng điều khiển của bạn.",
                ephemeral=True
            )
            return

        value = self.values[0]

        if value == "money":
            text = """
**💰 TIỀN LUNE**

`l!balance`
→ Xem số Xu Lune.

`l!daily`
→ Nhận **300–600 Xu**, cooldown 24 giờ.

`l!work`
→ Làm việc nhận **50–100 Xu**, cooldown 1 giờ.

`l!give @user số_xu`
→ Chuyển Xu cho thành viên.

`l!leaderboard`
→ Xem bảng xếp hạng Xu.
"""

        elif value == "games":
            text = """
**🎮 TRÒ CHƠI**

`l!coinflip số_xu`
→ Tung đồng xu.

`l!dice số_xu`
→ Chơi xúc xắc.

`l!slots số_xu`
→ Máy slot.

`l!rps số_xu`
→ Kéo búa bao.

`l!guess số_xu`
→ Đoán số.
"""

        elif value == "setl":
            text = """
**💗 SETL**

`l!hon @user`
→ Hôn.

`l!xoadau @user`
→ Xoa đầu.

`l!tat @user`
→ Tát.

`l!om @user`
→ Ôm.

`l!be @user`
→ Bế.

`l!can @user`
→ Cắn.
"""

        elif value == "giveaway":
            text = """
**🎁 GIVEAWAY**

`l!giveaway số_phút phần_thưởng`
→ Tạo giveaway.

Ví dụ:

`l!giveaway 10 500`

→ Giveaway 10 phút, phần thưởng 500 Xu.
"""

        elif value == "warn":
            if not interaction.user.guild_permissions.administrator:
                text = "❌ Bạn cần quyền **Administrator** để xem nhóm này."
            else:
                text = """
**⚠️ CẢNH BÁO — ADMIN**

`l!warn @user lý_do`
→ Cảnh báo thành viên.

`l!warnings @user`
→ Xem cảnh báo.

`l!unwarn @user`
→ Xóa cảnh báo gần nhất.

`l!clearwarn @user`
→ Xóa toàn bộ cảnh báo.
"""

        elif value == "admin":
            if not interaction.user.guild_permissions.administrator:
                text = "❌ Bạn cần quyền **Administrator** để xem nhóm này."
            else:
                text = """
**🛡️ QUẢN LÝ — ADMIN**

`l!kick @user lý_do`
→ Kick thành viên.

`l!ban @user lý_do`
→ Ban thành viên.

`l!unban ID`
→ Gỡ ban.

`l!clear số_lượng`
→ Xóa tin nhắn.

`l!lock`
→ Khóa kênh.

`l!unlock`
→ Mở khóa kênh.
"""

        else:
            if interaction.user.id != OWNER_ID:
                text = "❌ Nhóm này chỉ dành cho **Owner Bot**."
            else:
                text = """
**👑 OWNER BOT**

`l!cheat @user số_xu`
→ Cộng Xu cho thành viên.

`l!setxu @user số_xu`
→ Đặt số Xu.

`l!giveall số_xu`
→ Cộng Xu cho tất cả thành viên.

`l!shutdown`
→ Tắt bot.

`l!reload`
→ Reload bot.
"""

        embed = luna_embed("🌙・BẢNG ĐIỀU KHIỂN LUNA", text)
        await interaction.response.edit_message(
            embed=embed,
            view=self.view
        )


class HelpView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=180)
        self.add_item(HelpSelect(owner_id))


async def send_help(target):
    embed = luna_embed(
        "🌙・LUNA",
        """
**Danh sách các lệnh của Luna**

💰 Tiền Lune  
🎮 Trò chơi  
💗 SETL  
🎁 Giveaway  
⚠️ Cảnh báo  
🛡️ Quản lý  
👑 Owner Bot

**Tiền tố:** `l!` hoặc `L!`

Chọn một danh mục bên dưới để xem lệnh.
"""
    )

    view = HelpView(target.author.id)

    await target.send(
        embed=embed,
        view=view
    )


# =========================================================
# PREFIX HELP
# =========================================================

@bot.command(name="help")
async def help_prefix(ctx):
    await send_help(ctx)


# =========================================================
# SLASH HELP
# =========================================================

@bot.tree.command(name="help", description="Mở bảng điều khiển lệnh Luna")
async def help_slash(interaction: discord.Interaction):

    embed = luna_embed(
        "🌙・LUNA",
        """
**Danh sách các lệnh của Luna**

💰 Tiền Lune
🎮 Trò chơi
💗 SETL
🎁 Giveaway
⚠️ Cảnh báo
🛡️ Quản lý
👑 Owner Bot

Chọn danh mục bên dưới.
"""
    )

    await interaction.response.send_message(
        embed=embed,
        view=HelpView(interaction.user.id)
    )


# =========================================================
# HELLO
# =========================================================

@bot.command(name="hello")
async def hello_prefix(ctx):
    await ctx.send(f"🌙 Xin chào {ctx.author.mention}! Luna đã sẵn sàng.")


@bot.tree.command(name="hello", description="Luna chào bạn")
async def hello_slash(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🌙 Xin chào {interaction.user.mention}! Luna đã sẵn sàng."
    )


# =========================================================
# BALANCE
# =========================================================

@bot.command(name="balance", aliases=["bal", "xu"])
async def balance(ctx, member: discord.Member = None):

    member = member or ctx.author
    amount = get_xu(member.id)

    embed = luna_embed(
        "💰・XU LUNE",
        f"**{member.display_name}** đang có\n\n"
        f"🌙 **{amount:,} Xu Lune**"
    )

    await ctx.send(embed=embed)


# =========================================================
# DAILY
# =========================================================

@bot.command(name="daily")
async def daily(ctx):

    old = get_cooldown(ctx.author.id, "daily")

    if old:
        next_time = old + timedelta(hours=24)
        if datetime.now() < next_time:
            remaining = next_time - datetime.now()
            hours = int(remaining.total_seconds() // 3600)
            minutes = int(
                remaining.total_seconds() % 3600 // 60
            )

            await ctx.send(
                f"⏳ Bạn đã nhận daily rồi.\n"
                f"Thử lại sau **{hours} giờ {minutes} phút**."
            )
            return

    amount = random.randint(300, 600)

    add_xu(ctx.author.id, amount)
    set_cooldown(ctx.author.id, "daily")

    await ctx.send(
        f"🎁 {ctx.author.mention} nhận được "
        f"**{amount:,} Xu Lune** từ daily!"
    )


# =========================================================
# WORK
# =========================================================

@bot.command(name="work")
async def work(ctx):

    old = get_cooldown(ctx.author.id, "work")

    if old:
        next_time = old + timedelta(hours=1)

        if datetime.now() < next_time:
            remaining = next_time - datetime.now()

            minutes = int(
                remaining.total_seconds() // 60
            )

            await ctx.send(
                f"⏳ Bạn đang nghỉ sau ca làm.\n"
                f"Thử lại sau **{minutes} phút**."
            )
            return

    amount = random.randint(50, 100)

    add_xu(ctx.author.id, amount)
    set_cooldown(ctx.author.id, "work")

    jobs = [
        "phục vụ quán cà phê",
        "làm freelancer",
        "chăm sóc vườn",
        "đi giao hàng",
        "làm việc tại cửa hàng"
    ]

    job = random.choice(jobs)

    await ctx.send(
        f"💼 {ctx.author.mention} vừa **{job}** "
        f"và nhận **{amount:,} Xu Lune**!"
    )


# =========================================================
# GIVE
# =========================================================

@bot.command(name="give")
async def give(ctx, member: discord.Member, amount: int):

    if member.id == ctx.author.id:
        await ctx.send("❌ Không thể tự chuyển Xu cho chính mình.")
        return

    if amount <= 0:
        await ctx.send("❌ Số Xu phải lớn hơn 0.")
        return

    balance = get_xu(ctx.author.id)

    if balance < amount:
        await ctx.send("❌ Bạn không đủ Xu Lune.")
        return

    add_xu(ctx.author.id, -amount)
    add_xu(member.id, amount)

    await ctx.send(
        f"💸 {ctx.author.mention} đã chuyển "
        f"**{amount:,} Xu Lune** cho {member.mention}."
    )


# =========================================================
# LEADERBOARD
# =========================================================

@bot.command(name="leaderboard", aliases=["top"])
async def leaderboard(ctx):

    rows = cur.execute("""
        SELECT user_id, xu
        FROM users
        ORDER BY xu DESC
        LIMIT 10
    """).fetchall()

    if not rows:
        await ctx.send("Chưa có dữ liệu.")
        return

    text = ""

    for i, row in enumerate(rows, 1):
        member = ctx.guild.get_member(row["user_id"])

        if member:
            name = member.display_name
        else:
            name = f"User {row['user_id']}"

        text += (
            f"**{i}.** {name} — "
            f"🌙 `{row['xu']:,}`\n"
        )

    embed = luna_embed(
        "🏆・TOP XU LUNE",
        text
    )

    await ctx.send(embed=embed)


# =========================================================
# GAME: COINFLIP
# =========================================================

@bot.command(name="coinflip", aliases=["cf"])
async def coinflip(ctx, amount: int):

    if amount <= 0:
        await ctx.send("❌ Số Xu không hợp lệ.")
        return

    if get_xu(ctx.author.id) < amount:
        await ctx.send("❌ Bạn không đủ Xu.")
        return

    result = random.choice(["🪙 Mặt ngửa", "🪙 Mặt sấp"])

    win = random.choice([True, False])

    if win:
        add_xu(ctx.author.id, amount)
        msg = f"🎉 Bạn thắng và nhận **{amount:,} Xu**!\n{result}"
    else:
        add_xu(ctx.author.id, -amount)
        msg = f"💸 Bạn thua **{amount:,} Xu**.\n{result}"

    await ctx.send(msg)


# =========================================================
# GAME: DICE
# =========================================================

@bot.command(name="dice")
async def dice(ctx, amount: int):

    if amount <= 0:
        await ctx.send("❌ Số Xu không hợp lệ.")
        return

    if get_xu(ctx.author.id) < amount:
        await ctx.send("❌ Bạn không đủ Xu.")
        return

    player = random.randint(1, 6)
    luna = random.randint(1, 6)

    if player > luna:
        add_xu(ctx.author.id, amount)
        result = f"🎉 Bạn thắng **+{amount:,} Xu**!"
    elif player < luna:
        add_xu(ctx.author.id, -amount)
        result = f"💸 Bạn thua **-{amount:,} Xu**!"
    else:
        result = "🤝 Hòa! Không mất Xu."

    await ctx.send(
        f"🎲 Bạn: **{player}**\n"
        f"🌙 Luna: **{luna}**\n\n"
        f"{result}"
    )


# =========================================================
# GAME: SLOTS
# =========================================================

@bot.command(name="slots")
async def slots(ctx, amount: int):

    if amount <= 0:
        await ctx.send("❌ Số Xu không hợp lệ.")
        return

    if get_xu(ctx.author.id) < amount:
        await ctx.send("❌ Bạn không đủ Xu.")
        return

    icons = ["🍒", "🍋", "🍉", "⭐", "💎"]
    result = [random.choice(icons) for _ in range(3)]

    if result[0] == result[1] == result[2]:
        reward = amount * 3
        add_xu(ctx.author.id, reward)

        msg = f"🎉 JACKPOT! **+{reward:,} Xu**"
    elif len(set(result)) == 2:
        reward = amount
        add_xu(ctx.author.id, reward)

        msg = f"✨ Bạn thắng **+{reward:,} Xu**"
    else:
        add_xu(ctx.author.id, -amount)

        msg = f"💸 Bạn mất **{amount:,} Xu**"

    await ctx.send(
        f"🎰・` {' | '.join(result)} `\n\n{msg}"
    )


# =========================================================
# GAME: RPS
# =========================================================

@bot.command(name="rps")
async def rps(ctx, amount: int):

    if amount <= 0:
        await ctx.send("❌ Số Xu không hợp lệ.")
        return

    if get_xu(ctx.author.id) < amount:
        await ctx.send("❌ Bạn không đủ Xu.")
        return

    choices = ["kéo", "búa", "bao"]
    bot_choice = random.choice(choices)

    player = random.choice(choices)

    if player == bot_choice:
        result = "🤝 Hòa!"
    elif (
        (player == "kéo" and bot_choice == "bao") or
        (player == "búa" and bot_choice == "kéo") or
        (player == "bao" and bot_choice == "búa")
    ):
        add_xu(ctx.author.id, amount)
        result = f"🎉 Thắng **+{amount:,} Xu**!"
    else:
        add_xu(ctx.author.id, -amount)
        result = f"💸 Thua **-{amount:,} Xu**!"

    await ctx.send(
        f"✊ Bạn: **{player}**\n"
        f"🌙 Luna: **{bot_choice}**\n\n"
        f"{result}"
    )


# =========================================================
# GAME: GUESS
# =========================================================

@bot.command(name="guess")
async def guess(ctx, amount: int):

    if amount <= 0:
        await ctx.send("❌ Số Xu không hợp lệ.")
        return

    if get_xu(ctx.author.id) < amount:
        await ctx.send("❌ Bạn không đủ Xu.")
        return

    number = random.randint(1, 5)
    guess_number = random.randint(1, 5)

    if number == guess_number:
        reward = amount * 2
        add_xu(ctx.author.id, reward)

        result = f"🎉 Đoán đúng! **+{reward:,} Xu**"
    else:
        add_xu(ctx.author.id, -amount)

        result = f"💸 Đoán sai! **-{amount:,} Xu**"

    await ctx.send(
        f"🔢 Số của Luna: **{number}**\n"
        f"🎯 Bạn đoán: **{guess_number}**\n\n"
        f"{result}"
    )


# =========================================================
# SETL
# =========================================================

async def action(ctx, member, action_name, emoji):

    if member.id == ctx.author.id:
        await ctx.send("❌ Không thể dùng lệnh này với chính mình.")
        return

    await ctx.send(
        f"{emoji} {ctx.author.mention} **{action_name}** "
        f"{member.mention}!"
    )


@bot.command(name="hon")
async def hon(ctx, member: discord.Member):
    await action(ctx, member, "hôn", "💋")


@bot.command(name="xoadau")
async def xoadau(ctx, member: discord.Member):
    await action(ctx, member, "xoa đầu", "🌸")


@bot.command(name="tat")
async def tat(ctx, member: discord.Member):
    await action(ctx, member, "tát", "👋")


@bot.command(name="om")
async def om(ctx, member: discord.Member):
    await action(ctx, member, "ôm", "🫂")


@bot.command(name="be")
async def be(ctx, member: discord.Member):
    await action(ctx, member, "bế", "🫶")


@bot.command(name="can")
async def can(ctx, member: discord.Member):
    await action(ctx, member, "cắn nhẹ", "🦷")


# =========================================================
# LOVE
# =========================================================

@bot.command(name="setlove")
async def setlove(ctx, *, text: str):

    cur.execute(
        "INSERT OR REPLACE INTO loves(user_id, text) VALUES(?, ?)",
        (ctx.author.id, text)
    )
    db.commit()

    await ctx.send(
        f"💗 Đã đặt trạng thái tình yêu của "
        f"{ctx.author.mention} thành:\n> {text}"
    )


@bot.command(name="love")
async def love(ctx, member: discord.Member = None):

    member = member or ctx.author

    row = cur.execute(
        "SELECT text FROM loves WHERE user_id=?",
        (member.id,)
    ).fetchone()

    if not row:
        await ctx.send(
            f"💗 {member.mention} chưa đặt trạng thái tình yêu."
        )
        return

    await ctx.send(
        f"💗 Trạng thái tình yêu của {member.mention}:\n"
        f"> {row['text']}"
    )


@bot.command(name="kethon")
async def kethon(ctx, member: discord.Member):

    if member.id == ctx.author.id:
        await ctx.send("❌ Không thể kết hôn với chính mình.")
        return

    cur.execute(
        "INSERT OR REPLACE INTO marriages(user1, user2) VALUES(?, ?)",
        (ctx.author.id, member.id)
    )

    db.commit()

    await ctx.send(
        f"💍 {ctx.author.mention} và {member.mention} "
        f"đã kết hôn!"
    )


@bot.command(name="cr")
async def cr(ctx, member: discord.Member = None):

    if member is None:
        await ctx.send("💗 Hãy tag người bạn crush.")
        return

    percent = random.randint(1, 100)

    await ctx.send(
        f"💗 Độ hợp nhau giữa "
        f"{ctx.author.mention} và {member.mention}: "
        f"**{percent}%**"
    )


@bot.command(name="lyhon")
async def lyhon(ctx):

    row = cur.execute(
        "SELECT user2 FROM marriages WHERE user1=?",
        (ctx.author.id,)
    ).fetchone()

    if not row:
        row = cur.execute(
            "SELECT user1 FROM marriages WHERE user2=?",
            (ctx.author.id,)
        ).fetchone()

    if not row:
        await ctx.send("❌ Bạn chưa kết hôn.")
        return

    cur.execute(
        "DELETE FROM marriages WHERE user1=? OR user2=?",
        (ctx.author.id, ctx.author.id)
    )
    db.commit()

    await ctx.send(
        f"💔 {ctx.author.mention} đã kết thúc cuộc hôn nhân."
    )


# =========================================================
# WARN
# =========================================================

@bot.command(name="warn")
@admin_only()
async def warn(ctx, member: discord.Member, *, reason="Không có lý do"):

    cur.execute("""
        INSERT INTO warnings(
            guild_id,
            user_id,
            moderator_id,
            reason,
            created_at
        )
        VALUES(?, ?, ?, ?, ?)
    """, (
        ctx.guild.id,
        member.id,
        ctx.author.id,
        reason,
        datetime.now().isoformat()
    ))

    db.commit()

    count = cur.execute("""
        SELECT COUNT(*)
        FROM warnings
        WHERE guild_id=? AND user_id=?
    """, (
        ctx.guild.id,
        member.id
    )).fetchone()[0]

    await ctx.send(
        f"⚠️ {member.mention} đã nhận **cảnh báo #{count}**.\n"
        f"📝 Lý do: {reason}"
    )


@bot.command(name="warnings")
@admin_only()
async def warnings(ctx, member: discord.Member):

    rows = cur.execute("""
        SELECT reason, moderator_id, created_at
        FROM warnings
        WHERE guild_id=? AND user_id=?
        ORDER BY id DESC
    """, (
        ctx.guild.id,
        member.id
    )).fetchall()

    if not rows:
        await ctx.send(
            f"✅ {member.mention} không có cảnh báo."
        )
        return

    text = ""

    for i, row in enumerate(rows, 1):
        text += (
            f"**#{i}** — {row['reason']}\n"
        )

    await ctx.send(
        embed=luna_embed(
            f"⚠️ CẢNH BÁO — {member.display_name}",
            text
        )
    )


@bot.command(name="unwarn")
@admin_only()
async def unwarn(ctx, member: discord.Member):

    row = cur.execute("""
        SELECT id
        FROM warnings
        WHERE guild_id=? AND user_id=?
        ORDER BY id DESC
        LIMIT 1
    """, (
        ctx.guild.id,
        member.id
    )).fetchone()

    if not row:
        await ctx.send("❌ Thành viên này không có cảnh báo.")
        return

    cur.execute(
        "DELETE FROM warnings WHERE id=?",
        (row["id"],)
    )
    db.commit()

    await ctx.send(
        f"✅ Đã xóa cảnh báo gần nhất của {member.mention}."
    )


@bot.command(name="clearwarn")
@admin_only()
async def clearwarn(ctx, member: discord.Member):

    cur.execute("""
        DELETE FROM warnings
        WHERE guild_id=? AND user_id=?
    """, (
        ctx.guild.id,
        member.id
    ))

    db.commit()

    await ctx.send(
        f"✅ Đã xóa toàn bộ cảnh báo của {member.mention}."
    )


# =========================================================
# ADMIN: KICK
# =========================================================

@bot.command(name="kick")
@admin_only()
async def kick(ctx, member: discord.Member, *, reason="Không có lý do"):

    try:
        await member.kick(reason=reason)

        await ctx.send(
            f"👢 Đã kick {member.mention}.\n"
            f"📝 Lý do: {reason}"
        )
    except discord.Forbidden:
        await ctx.send("❌ Luna không đủ quyền kick thành viên này.")


# =========================================================
# ADMIN: BAN
# =========================================================

@bot.command(name="ban")
@admin_only()
async def ban(ctx, member: discord.Member, *, reason="Không có lý do"):

    try:
        await member.ban(reason=reason)

        await ctx.send(
            f"🔨 Đã ban {member.mention}.\n"
            f"📝 Lý do: {reason}"
        )
    except discord.Forbidden:
        await ctx.send("❌ Luna không đủ quyền ban thành viên này.")


# =========================================================
# ADMIN: UNBAN
# =========================================================

@bot.command(name="unban")
@admin_only()
async def unban(ctx, user_id: int):

    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)

        await ctx.send(
            f"✅ Đã unban **{user}**."
        )

    except discord.NotFound:
        await ctx.send("❌ Không tìm thấy user hoặc user chưa bị ban.")

    except discord.Forbidden:
        await ctx.send("❌ Luna không có quyền unban.")


# =========================================================
# ADMIN: CLEAR
# =========================================================

@bot.command(name="clear")
@admin_only()
async def clear(ctx, amount: int):

    if amount < 1 or amount > 100:
        await ctx.send("❌ Nhập số từ 1 đến 100.")
        return

    deleted = await ctx.channel.purge(limit=amount + 1)

    msg = await ctx.send(
        f"🧹 Đã xóa **{len(deleted) - 1}** tin nhắn."
    )

    await asyncio.sleep(3)

    try:
        await msg.delete()
    except:
        pass


# =========================================================
# ADMIN: LOCK
# =========================================================

@bot.command(name="lock")
@admin_only()
async def lock(ctx):

    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False

    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        overwrite=overwrite
    )

    await ctx.send("🔒 Đã khóa kênh.")


# =========================================================
# ADMIN: UNLOCK
# =========================================================

@bot.command(name="unlock")
@admin_only()
async def unlock(ctx):

    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = None

    await ctx.channel.set_permissions(
        ctx.guild.default_role,
        overwrite=overwrite
    )

    await ctx.send("🔓 Đã mở khóa kênh.")


# =========================================================
# OWNER: CHEAT
# =========================================================

@bot.command(name="cheat")
@owner_only()
async def cheat(ctx, member: discord.Member, amount: int):

    if amount == 0:
        await ctx.send("❌ Số Xu không hợp lệ.")
        return

    add_xu(member.id, amount)

    await ctx.send(
        f"👑 Owner đã thay đổi Xu của {member.mention} "
        f"**{amount:+,} Xu**."
    )


# =========================================================
# OWNER: SET XU
# =========================================================

@bot.command(name="setxu")
@owner_only()
async def setxu(ctx, member: discord.Member, amount: int):

    if amount < 0:
        await ctx.send("❌ Số Xu không thể âm.")
        return

    set_xu(member.id, amount)

    await ctx.send(
        f"👑 Đã đặt số Xu của {member.mention} thành "
        f"**{amount:,} Xu**."
    )


# =========================================================
# OWNER: GIVE ALL
# =========================================================

@bot.command(name="giveall")
@owner_only()
async def giveall(ctx, amount: int):

    if amount <= 0:
        await ctx.send("❌ Số Xu không hợp lệ.")
        return

    count = 0

    for member in ctx.guild.members:

        if member.bot:
            continue

        add_xu(member.id, amount)
        count += 1

    await ctx.send(
        f"👑 Đã cộng **{amount:,} Xu** cho "
        f"**{count} thành viên**."
    )


# =========================================================
# OWNER: SHUTDOWN
# =========================================================

@bot.command(name="shutdown")
@owner_only()
async def shutdown(ctx):

    await ctx.send("🌙 Luna đang tắt...")

    await bot.close()


# =========================================================
# OWNER: RELOAD
# =========================================================

@bot.command(name="reload")
@owner_only()
async def reload_bot(ctx):

    await ctx.send(
        "🔄 Luna đã nhận lệnh reload.\n"
        "Nếu chạy trên Railway, hãy Restart Deployment để khởi động lại."
    )


# =========================================================
# GIVEAWAY
# =========================================================

class GiveawayView(discord.ui.View):

    def __init__(self, prize, author_id):
        super().__init__(timeout=None)

        self.prize = prize
        self.author_id = author_id
        self.users = set()

    @discord.ui.button(
        label="Tham gia",
        emoji="🎉",
        style=discord.ButtonStyle.primary
    )
    async def join(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        if interaction.user.id in self.users:
            self.users.remove(interaction.user.id)

            await interaction.response.send_message(
                "Bạn đã rời giveaway.",
                ephemeral=True
            )

        else:
            self.users.add(interaction.user.id)

            await interaction.response.send_message(
                "🎉 Đã tham gia giveaway!",
                ephemeral=True
            )


@bot.command(name="giveaway")
@admin_only()
async def giveaway(ctx, minutes: int, *, prize: str):

    if minutes < 1:
        await ctx.send("❌ Thời gian phải lớn hơn 0.")
        return

    end_time = datetime.now() + timedelta(minutes=minutes)

    embed = luna_embed(
        "🎁・GIVEAWAY",
        f"""
🎁 **Phần thưởng:** {prize}

👑 Người tạo: {ctx.author.mention}

⏰ Kết thúc: <t:{int(end_time.timestamp())}:R>

Nhấn nút **🎉 Tham gia** bên dưới để tham gia.
"""
    )

    view = GiveawayView(prize, ctx.author.id)

    message = await ctx.send(
        embed=embed,
        view=view
    )

    await asyncio.sleep(minutes * 60)

    if not view.users:
        await ctx.send(
            "🎁 Giveaway kết thúc nhưng không có người tham gia."
        )
        return

    winner_id = random.choice(list(view.users))

    winner = ctx.guild.get_member(winner_id)

    await ctx.send(
        f"🎉 Chúc mừng {winner.mention}!\n"
        f"Bạn đã thắng giveaway **{prize}**!"
    )


# =========================================================
# ERROR HANDLER
# =========================================================

@bot.event
async def on_command_error(ctx, error):

    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingPermissions):
        await ctx.send(
            "❌ Bạn không có quyền dùng lệnh này.",
            delete_after=5
        )
        return

    if isinstance(error, commands.CheckFailure):
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "❌ Thiếu thông tin.\n"
            "Dùng `l!help` để xem cách sử dụng."
        )
        return

    if isinstance(error, commands.MemberNotFound):
        await ctx.send(
            "❌ Không tìm thấy thành viên đó."
        )
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send(
            "❌ Sai định dạng lệnh."
        )
        return

    print("COMMAND ERROR:", repr(error))


# =========================================================
# BOT READY
# =========================================================

@bot.event
async def on_ready():

    try:
        synced = await bot.tree.sync()
        print(f"Đã sync {len(synced)} slash commands.")
    except Exception as e:
        print("Lỗi sync slash:", e)

    print("=" * 40)
    print(f"🌙 Luna đã online: {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print(f"👑 Owner ID: {OWNER_ID}")
    print("=" * 40)


# =========================================================
# CHẠY BOT
# =========================================================

if not TOKEN:
    raise RuntimeError(
        "Chưa có TOKEN. Hãy thêm biến môi trường TOKEN trên Railway."
    )

if OWNER_ID == 0:
    print(
        "⚠️ Chưa đặt OWNER_ID. "
        "Các lệnh Owner sẽ không sử dụng được."
    )

bot.run(TOKEN)
