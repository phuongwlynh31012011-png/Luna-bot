import os
import sqlite3
import asyncio
import random
import time
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks
from discord import app_commands

# ============================================================
# LUNA — Discord Bot
# Prefix: l! or L!
# Database: SQLite
# ============================================================

TOKEN = os.getenv("TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)

PREFIXES = ("l!", "L!")
DB_FILE = "luna.db"

if not TOKEN:
    raise RuntimeError("Chưa có TOKEN. Hãy đặt biến môi trường TOKEN.")
if OWNER_ID == 0:
    print("⚠️ OWNER_ID chưa được đặt. Các lệnh owner sẽ không dùng được.")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(
    command_prefix=PREFIXES,
    intents=intents,
    case_insensitive=True,
    help_command=None,
)

# ---------------- DATABASE ----------------

db = sqlite3.connect(DB_FILE, check_same_thread=False)
db.row_factory = sqlite3.Row
db_lock = asyncio.Lock()

def db_init():
    cur = db.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER NOT NULL DEFAULT 0,
        daily_at INTEGER NOT NULL DEFAULT 0,
        work_at INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS shops (
        guild_id INTEGER NOT NULL,
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price INTEGER NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        stock INTEGER NOT NULL DEFAULT -1
    );

    CREATE TABLE IF NOT EXISTS inventory (
        user_id INTEGER NOT NULL,
        guild_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(user_id, guild_id, item_id)
    );

    CREATE TABLE IF NOT EXISTS warnings (
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        count INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(guild_id, user_id)
    );

    CREATE TABLE IF NOT EXISTS warn_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        moderator_id INTEGER NOT NULL,
        reason TEXT NOT NULL,
        created_at INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS loves (
        guild_id INTEGER PRIMARY KEY,
        content TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS marriages (
        user1 INTEGER NOT NULL,
        user2 INTEGER NOT NULL,
        guild_id INTEGER NOT NULL,
        created_at INTEGER NOT NULL,
        PRIMARY KEY(user1, user2, guild_id)
    );
    """)
    db.commit()

db_init()

def ensure_user(user_id: int):
    db.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    db.commit()

def get_balance(user_id: int) -> int:
    ensure_user(user_id)
    row = db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)).fetchone()
    return int(row["balance"])

def add_balance(user_id: int, amount: int):
    ensure_user(user_id)
    db.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
    db.commit()

def take_balance(user_id: int, amount: int) -> bool:
    ensure_user(user_id)
    cur = db.execute(
        "UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?",
        (amount, user_id, amount),
    )
    db.commit()
    return cur.rowcount == 1

# ---------------- HELPERS ----------------

def embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()):
    return discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(timezone.utc))

def money(n: int) -> str:
    return f"{n:,} xu"

def mention_or_name(user: discord.User | discord.Member) -> str:
    return user.mention

def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def admin_only():
    async def predicate(ctx: commands.Context):
        return isinstance(ctx.author, discord.Member) and (
            ctx.author.guild_permissions.administrator
            or ctx.author.guild_permissions.manage_guild
        )
    return commands.check(predicate)

def owner_only():
    async def predicate(ctx: commands.Context):
        return is_owner(ctx.author.id)
    return commands.check(predicate)

def uptime_string() -> str:
    seconds = int(time.monotonic() - bot.started_at)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"

# ---------------- HELP PANEL ----------------

CATEGORIES = {
    "money": ("💰 Tiền Lune", [
        "`l!balance` — xem số dư",
        "`l!give @user <số>` — chuyển xu",
        "`l!daily` — nhận xu hằng ngày",
        "`l!work` — làm việc kiếm xu",
        "`l!shop` — xem shop của server",
        "`l!buy <id> [số lượng]` — mua vật phẩm",
        "`l!inventory` — xem túi đồ",
        "`l!pay @user <số>` — chuyển xu",
    ]),
    "games": ("🎮 Trò chơi", [
        "`l!rps <búa|kéo|bao> <cược>` — oẳn tù tì",
        "`l!dice <số xúc xắc> <cược>` — gieo xúc xắc d6",
        "`l!baucua <bầu|cua|tôm|cá|gà|nai> <cược>` — bầu cua",
        "`l!doan <1-100> <cược>` — đoán số",
        "`l!doando <đỏ|đen> <cược>` — đoán đỏ/đen",
    ]),
    "love": ("💗 SETL", [
        "`l!setlove <nội dung>` — đặt câu tình yêu",
        "`l!love [@user]` — xem câu tình yêu",
        "`l!hon [@user]` — hôn",
        "`l!xoadau [@user]` — xoa đầu",
        "`l!tat [@user]` — tát",
        "`l!om [@user]` — ôm",
        "`l!be [@user]` — bế",
        "`l!can @user` — cắn",
        "`l!kethon @user` — kết hôn",
        "`l!lyhon @user` — ly hôn",
    ]),
    "giveaway": ("🎁 Giveaway", [
        "`l!giveaway <phút> <phần thưởng>` — tạo giveaway",
        "`l!gjoin` — tham gia giveaway đang mở",
        "`l!gend` — kết thúc giveaway gần nhất",
    ]),
    "warning": ("⚠️ Cảnh báo", [
        "`l!warn @user <lý do>` — cảnh cáo",
        "`l!warnings @user` — xem cảnh cáo",
        "`l!clearwarn @user` — xoá cảnh cáo",
        "`l!kick @user [lý do]` — kick",
        "`l!ban @user [lý do]` — ban",
        "`l!mute @user <phút> [lý do]` — timeout",
    ]),
    "admin": ("🛡️ Quản lý / Setup", [
        "`l!setshop <tên> | <giá> | <mô tả>` — thêm vật phẩm shop",
        "`l!editshop <id> <giá>` — sửa giá",
        "`l!delshop <id>` — xoá vật phẩm",
        "`l!clearshop` — xoá shop server",
        "`l!setlove <nội dung>` — đổi nội dung SETL",
        "`l!setlog #kênh` — đặt kênh log cảnh cáo",
    ]),
    "owner": ("👑 Owner Bot", [
        "`l!botinfo` — thông tin Luna",
        "`l!servers` — danh sách server",
        "`l!say <nội dung>` — Luna gửi tin",
        "`l!shutdown` — tắt bot",
        "`l!sync` — đồng bộ slash commands",
    ]),
}

class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Tiền Lune", emoji="💰", value="money"),
            discord.SelectOption(label="Trò chơi", emoji="🎮", value="games"),
            discord.SelectOption(label="SETL", emoji="💗", value="love"),
            discord.SelectOption(label="Giveaway", emoji="🎁", value="giveaway"),
            discord.SelectOption(label="Cảnh báo", emoji="⚠️", value="warning"),
            discord.SelectOption(label="Quản lý", emoji="🛡️", value="admin"),
            discord.SelectOption(label="Owner Bot", emoji="👑", value="owner"),
        ]
        super().__init__(placeholder="Chọn danh mục", options=options)

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        title, lines = CATEGORIES[key]
        if key == "owner" and not is_owner(interaction.user.id):
            await interaction.response.send_message(
                "🔒 Mục Owner Bot chỉ chủ bot mới xem được.", ephemeral=True
            )
            return
        if key == "admin" and not (
            isinstance(interaction.user, discord.Member)
            and (interaction.user.guild_permissions.administrator or interaction.user.guild_permissions.manage_guild)
        ):
            await interaction.response.send_message(
                "🔒 Mục Quản lý chỉ Admin/Manage Server mới xem được.", ephemeral=True
            )
            return
        e = embed(f"🌙 LUNA • {title}", "\n".join(lines))
        await interaction.response.edit_message(embed=e, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(HelpSelect())

# ---------------- EVENTS ----------------

@bot.event
async def on_ready():
    bot.started_at = getattr(bot, "started_at", time.monotonic())
    try:
        await bot.tree.sync()
    except Exception as e:
        print("Slash sync error:", e)
    print(f"🌙 Luna online: {bot.user} | {bot.user.id}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply("❌ Thiếu tham số. Dùng `l!help` để xem cú pháp.")
    elif isinstance(error, commands.BadArgument):
        await ctx.reply("❌ Tham số không hợp lệ. Kiểm tra lại cú pháp.")
    elif isinstance(error, commands.CheckFailure):
        await ctx.reply("🔒 Bạn không có quyền dùng lệnh này.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"⏳ Thử lại sau `{error.retry_after:.1f}s`.")
    else:
        print("COMMAND ERROR:", repr(error))
        await ctx.reply("❌ Có lỗi khi thực hiện lệnh.")

# ---------------- BASIC ----------------

@bot.command(name="hello")
async def hello(ctx):
    await ctx.reply(f"🌙 Xin chào {ctx.author.mention}! Luna đã sẵn sàng.")

@bot.command(name="help", aliases=["h"])
async def help_cmd(ctx):
    e = embed(
        "🌙 • LUNA",
        "Danh sách các lệnh của Luna\n\n"
        "💰 Tiền Lune\n"
        "🎮 Trò chơi\n"
        "💗 SETL\n"
        "🎁 Giveaway\n"
        "⚠️ Cảnh báo\n"
        "🛡️ Quản lý\n"
        "👑 Owner Bot\n\n"
        "Chọn danh mục bên dưới."
    )
    await ctx.reply(embed=e, view=HelpView())

@bot.tree.command(name="hello", description="Luna chào bạn")
async def slash_hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"🌙 Xin chào {interaction.user.mention}! Luna đã sẵn sàng. Chúc bạn có những phút giây thật vui và đáng nhớ tại đây.")
    

@bot.tree.command(name="help", description="Mở bảng điều khiển lệnh Luna")
async def slash_help(interaction: discord.Interaction):
    e = embed(
        "🌙 • LUNA",
        "Danh sách các lệnh của Luna\n\n💰 Tiền Lune\n🎮 Trò chơi\n💗 SETL\n🎁 Giveaway\n⚠️ Cảnh báo\n🛡️ Quản lý\n👑 Owner Bot\n\nChọn danh mục bên dưới."
    )
    await interaction.response.send_message(embed=e, view=HelpView())

@bot.command(name="botinfo", aliases=["info"])
async def botinfo(ctx):
    pyver = f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}.{__import__('sys').version_info.micro}"
    e = embed(
        "🌙 LUNA — THÔNG TIN BOT",
        f"🤖 **Tên:** {bot.user}\n"
        f"🆔 **ID:** `{bot.user.id}`\n"
        f"📡 **Ping:** `{round(bot.latency * 1000)}ms`\n"
        f"⏱️ **Uptime:** `{uptime_string()}`\n\n"
        f"🏠 **Số server:** `{len(bot.guilds)}`\n"
        f"👥 **Tổng thành viên:** `{sum(g.member_count or 0 for g in bot.guilds):,}`\n\n"
        f"🐍 **Python:** `{pyver}`\n"
        f"📚 **discord.py:** `{discord.__version__}`\n\n"
        f"👑 **Owner:** <@{OWNER_ID}>"
    )
    await ctx.reply(embed=e)

# ---------------- ECONOMY ----------------

@bot.command()
async def balance(ctx, member: discord.Member | None = None):
    member = member or ctx.author
    await ctx.reply(embed=embed("💰 Số dư Lune", f"{member.mention} đang có **{money(balance(member.id))}**."))

@bot.command(aliases=["bal"])
async def xu(ctx, member: discord.Member | None = None):
    member = member or ctx.author
amount = get_balance(member.id)

await ctx.reply(
    embed=embed(
        "💰 Số dư Lune",
        f"{member.mention} đang có **{amount:,} xu**."

@bot.command()
@commands.cooldown(1, 86400, commands.BucketType.user)
async def daily(ctx):
    amount = random.randint(250, 500)
    add_balance(ctx.author.id, amount)
    await ctx.reply(f"🌙 {ctx.author.mention} nhận **{money(amount)}** từ daily!")

@bot.command()
@commands.cooldown(1, 3600, commands.BucketType.user)
async def work(ctx):
    amount = random.randint(80, 220)
    add_balance(ctx.author.id, amount)
    jobs = ["phục vụ quán", "làm nhiệm vụ", "thiết kế", "săn kho báu"]
    await ctx.reply(f"💼 {ctx.author.mention} vừa **{random.choice(jobs)}** và nhận **{money(amount)}**.")

@bot.command(aliases=["give"])
async def pay(ctx, member: discord.Member, amount: int):
    if member.bot or member.id == ctx.author.id:
        return await ctx.reply("❌ Không thể chuyển xu cho tài khoản này.")
    if amount <= 0:
        return await ctx.reply("❌ Số xu phải lớn hơn 0.")
    if not take_balance(ctx.author.id, amount):
        return await ctx.reply("❌ Bạn không đủ xu.")
    add_balance(member.id, amount)
    await ctx.reply(f"💸 {ctx.author.mention} đã chuyển **{money(amount)}** cho {member.mention}.")

# ---------------- SHOP (PER SERVER) ----------------

@bot.command()
async def shop(ctx):
    rows = db.execute(
        "SELECT item_id,name,price,description,stock FROM shops WHERE guild_id=? ORDER BY item_id",
        (ctx.guild.id,),
    ).fetchall()
    if not rows:
        return await ctx.reply("🛒 Shop server này chưa có vật phẩm.")
    lines = []
    for r in rows:
        stock = "∞" if r["stock"] < 0 else str(r["stock"])
        lines.append(f"**#{r['item_id']} • {r['name']}** — {money(r['price'])} • Kho: `{stock}`\n{r['description']}")
    await ctx.reply(embed=embed(f"🛒 SHOP • {ctx.guild.name}", "\n\n".join(lines)))

@bot.command()
@admin_only()
async def setshop(ctx, *, data: str):
    parts = [p.strip() for p in data.split("|", 2)]
    if len(parts) < 2:
        return await ctx.reply("Cú pháp: `l!setshop Tên | Giá | Mô tả`")
    name = parts[0]
    try:
        price = int(parts[1])
    except ValueError:
        return await ctx.reply("❌ Giá phải là số.")
    desc = parts[2] if len(parts) == 3 else ""
    if price < 0:
        return await ctx.reply("❌ Giá không được âm.")
    db.execute("INSERT INTO shops(guild_id,name,price,description) VALUES(?,?,?,?)",
               (ctx.guild.id, name[:80], price, desc[:300]))
    db.commit()
    await ctx.reply(f"✅ Đã thêm **{name}** vào shop server này.")

@bot.command()
@admin_only()
async def editshop(ctx, item_id: int, price: int):
    if price < 0:
        return await ctx.reply("❌ Giá không được âm.")
    cur = db.execute("UPDATE shops SET price=? WHERE item_id=? AND guild_id=?",
                     (price, item_id, ctx.guild.id))
    db.commit()
    await ctx.reply("✅ Đã sửa giá." if cur.rowcount else "❌ Không tìm thấy vật phẩm.")

@bot.command()
@admin_only()
async def delshop(ctx, item_id: int):
    cur = db.execute("DELETE FROM shops WHERE item_id=? AND guild_id=?", (item_id, ctx.guild.id))
    db.commit()
    await ctx.reply("✅ Đã xoá vật phẩm." if cur.rowcount else "❌ Không tìm thấy vật phẩm.")

@bot.command()
@admin_only()
async def clearshop(ctx):
    db.execute("DELETE FROM shops WHERE guild_id=?", (ctx.guild.id,))
    db.commit()
    await ctx.reply("🧹 Đã xoá toàn bộ shop của server.")

@bot.command()
async def buy(ctx, item_id: int, quantity: int = 1):
    if quantity <= 0 or quantity > 99:
        return await ctx.reply("❌ Số lượng phải từ 1 đến 99.")
    row = db.execute("SELECT * FROM shops WHERE item_id=? AND guild_id=?",
                     (item_id, ctx.guild.id)).fetchone()
    if not row:
        return await ctx.reply("❌ Không tìm thấy vật phẩm trong shop server này.")
    if row["stock"] >= 0 and row["stock"] < quantity:
        return await ctx.reply("❌ Shop không đủ hàng.")
    total = row["price"] * quantity
    if not take_balance(ctx.author.id, total):
        return await ctx.reply(f"❌ Bạn cần **{money(total)}**.")
    db.execute("""
        INSERT INTO inventory(user_id,guild_id,item_id,quantity) VALUES(?,?,?,?)
        ON CONFLICT(user_id,guild_id,item_id) DO UPDATE SET quantity=quantity+excluded.quantity
    """, (ctx.author.id, ctx.guild.id, item_id, quantity))
    if row["stock"] >= 0:
        db.execute("UPDATE shops SET stock=stock-? WHERE item_id=?", (quantity, item_id))
    db.commit()
    await ctx.reply(f"🛍️ Đã mua **{row['name']} x{quantity}** với **{money(total)}**.")

@bot.command()
async def inventory(ctx, member: discord.Member | None = None):
    member = member or ctx.author
    rows = db.execute("""
        SELECT s.name, i.quantity FROM inventory i
        JOIN shops s ON s.item_id=i.item_id
        WHERE i.user_id=? AND i.guild_id=? AND i.quantity>0
    """, (member.id, ctx.guild.id)).fetchall()
    if not rows:
        return await ctx.reply("🎒 Túi đồ đang trống.")
    await ctx.reply(embed=embed("🎒 Túi đồ", "\n".join(f"• {r['name']} × `{r['quantity']}`" for r in rows)))

# ---------------- GAMES ----------------

def valid_bet(amount):
    return isinstance(amount, int) and 1 <= amount <= 1_000_000

@bot.command()
async def rps(ctx, choice: str, bet: int):
    if choice.lower() not in ("búa", "bua", "kéo", "keo", "bao"):
        return await ctx.reply("❌ Chọn `búa`, `kéo` hoặc `bao`.")
    if not valid_bet(bet) or not take_balance(ctx.author.id, bet):
        return await ctx.reply("❌ Cược không hợp lệ hoặc không đủ xu.")
    user = {"bua":"búa", "búa":"búa", "keo":"kéo", "kéo":"kéo", "bao":"bao"}[choice.lower()]
    botc = random.choice(["búa", "kéo", "bao"])
    win = (user, botc) in [("búa","kéo"),("kéo","bao"),("bao","búa")]
    if user == botc:
        add_balance(ctx.author.id, bet)
        result = f"🤝 Hoà! Bạn nhận lại {money(bet)}."
    elif win:
        add_balance(ctx.author.id, bet * 2)
        result = f"🎉 Thắng! Nhận {money(bet*2)}."
    else:
        result = f"💸 Thua {money(bet)}."
    await ctx.reply(f"🪨📄✂️ Bạn: **{user}** | Luna: **{botc}**\n{result}")

@bot.command()
async def dice(ctx, count: int, bet: int):
    if count < 1 or count > 6:
        return await ctx.reply("❌ Số xúc xắc từ 1 đến 6. Mỗi xúc xắc có 6 mặt.")
    if not valid_bet(bet) or not take_balance(ctx.author.id, bet):
        return await ctx.reply("❌ Cược không hợp lệ hoặc không đủ xu.")
    rolls = [random.randint(1, 6) for _ in range(count)]
    total = sum(rolls)
    # Thưởng theo tổng tương đối với số xúc xắc.
    if total == count * 6:
        multiplier = 3
    elif total >= count * 4:
        multiplier = 2
    else:
        multiplier = 0
    if multiplier:
        add_balance(ctx.author.id, bet * multiplier)
        result = f"🎉 Nhận **{money(bet*multiplier)}**."
    else:
        result = f"💸 Mất **{money(bet)}**."
    await ctx.reply(f"🎲 Kết quả: **{' • '.join(map(str, rolls))}** | Tổng: **{total}**\n{result}")

@bot.command()
async def baucua(ctx, choice: str, bet: int):
    faces = ["bầu","cua","tôm","cá","gà","nai"]
    aliases = {"bau":"bầu","bầu":"bầu","cua":"cua","tom":"tôm","tôm":"tôm","ca":"cá","cá":"cá","ga":"gà","gà":"gà","nai":"nai"}
    c = aliases.get(choice.lower())
    if not c or not valid_bet(bet) or not take_balance(ctx.author.id, bet):
        return await ctx.reply("❌ Cú pháp: `l!baucua <bầu|cua|tôm|cá|gà|nai> <cược>` và phải đủ xu.")
    rolls = [random.choice(faces) for _ in range(3)]
    hits = rolls.count(c)
    payout = bet * hits
    if hits:
        add_balance(ctx.author.id, bet + payout)
        result = f"🎉 Ra **{hits} {c}** — nhận tổng **{money(bet+payout)}**."
    else:
        result = f"💸 Không trúng — mất **{money(bet)}**."
    await ctx.reply(f"🎲 {', '.join(rolls)}\n{result}")

@bot.command()
async def doan(ctx, number: int, bet: int):
    if not 1 <= number <= 100 or not valid_bet(bet) or not take_balance(ctx.author.id, bet):
        return await ctx.reply("❌ Số đoán từ 1–100 và cược hợp lệ.")
    target = random.randint(1, 100)
    if number == target:
        add_balance(ctx.author.id, bet * 5)
        result = f"🎯 Chính xác! Nhận **{money(bet*5)}**."
    else:
        result = f"🔢 Số đúng là **{target}**. {money(bet)} đã được dùng cho lượt chơi."
    await ctx.reply(result)

@bot.command(aliases=["redblack"])
async def doando(ctx, color: str, bet: int):
    c = color.lower()
    if c not in ("đỏ","do","đen","den") or not valid_bet(bet) or not take_balance(ctx.author.id, bet):
        return await ctx.reply("❌ Chọn `đỏ` hoặc `đen` và nhập cược hợp lệ.")
    actual = random.choice(["đỏ","đen"])
    if ("đỏ" if c in ("đỏ","do") else "đen") == actual:
        add_balance(ctx.author.id, bet * 2)
        result = f"🎉 Ra **{actual}** — nhận **{money(bet*2)}**."
    else:
        result = f"💸 Ra **{actual}** — mất **{money(bet)}**."
    await ctx.reply(result)

# ---------------- SETL ----------------

DEFAULT_LOVE = "🌙 Một chút dịu dàng, một chút đáng yêu — Luna gửi tới bạn."

@bot.command()
@admin_only()
async def setlove(ctx, *, content: str):
    db.execute("""
        INSERT INTO loves(guild_id,content) VALUES(?,?)
        ON CONFLICT(guild_id) DO UPDATE SET content=excluded.content
    """, (ctx.guild.id, content[:1000]))
    db.commit()
    await ctx.reply("💗 Đã cập nhật nội dung SETL cho server.")

def get_love(guild_id):
    row = db.execute("SELECT content FROM loves WHERE guild_id=?", (guild_id,)).fetchone()
    return row["content"] if row else DEFAULT_LOVE

@bot.command()
async def love(ctx, member: discord.Member | None = None):
    member = member or ctx.author
    await ctx.reply(f"💗 **SETL**\n{get_love(ctx.guild.id)}\n\n{ctx.author.mention} → {member.mention}")

async def action(ctx, verb, member):
    member = member or ctx.author
    if member.bot:
        return await ctx.reply("🤖 Không thực hiện tương tác này với bot.")
    await ctx.reply(f"💗 {ctx.author.mention} **{verb}** {member.mention}")

@bot.command()
async def hon(ctx, member: discord.Member):
    await action(ctx, "hôn", member)

@bot.command()
async def xoadau(ctx, member: discord.Member):
    await action(ctx, "xoa đầu", member)

@bot.command()
async def tat(ctx, member: discord.Member):
    await action(ctx, "tát", member)

@bot.command()
async def om(ctx, member: discord.Member):
    await action(ctx, "ôm", member)

@bot.command()
async def be(ctx, member: discord.Member):
    await action(ctx, "bế", member)

@bot.command()
async def can(ctx, member: discord.Member):
    await action(ctx, "cắn", member)

@bot.command()
async def kethon(ctx, member: discord.Member):
    if member.id == ctx.author.id:
        return await ctx.reply("❌ Không thể kết hôn với chính mình.")
    pair = tuple(sorted((ctx.author.id, member.id)))
    db.execute("INSERT OR IGNORE INTO marriages(user1,user2,guild_id,created_at) VALUES(?,?,?,?)",
               (pair[0], pair[1], ctx.guild.id, int(time.time())))
    db.commit()
    await ctx.reply(f"💍 {ctx.author.mention} và {member.mention} đã kết hôn trong Luna v2!")

@bot.command()
async def lyhon(ctx, member: discord.Member):
    pair = tuple(sorted((ctx.author.id, member.id)))
    cur = db.execute("DELETE FROM marriages WHERE user1=? AND user2=? AND guild_id=?",
                     (pair[0], pair[1], ctx.guild.id))
    db.commit()
    await ctx.reply("💔 Đã ly hôn." if cur.rowcount else "❌ Hai người chưa có hôn thú trong Luna.")

# ---------------- WARNING / MODERATION ----------------

async def do_warn(ctx, member, reason):
    if member.bot or member.id == ctx.author.id:
        return await ctx.reply("❌ Không thể cảnh cáo tài khoản này.")
    row = db.execute("SELECT count FROM warnings WHERE guild_id=? AND user_id=?",
                     (ctx.guild.id, member.id)).fetchone()
    count = (row["count"] if row else 0) + 1
    db.execute("""
        INSERT INTO warnings(guild_id,user_id,count) VALUES(?,?,?)
        ON CONFLICT(guild_id,user_id) DO UPDATE SET count=excluded.count
    """, (ctx.guild.id, member.id, count))
    db.execute("INSERT INTO warn_logs(guild_id,user_id,moderator_id,reason,created_at) VALUES(?,?,?,?,?)",
               (ctx.guild.id, member.id, ctx.author.id, reason, int(time.time())))
    db.commit()
    await ctx.reply(f"⚠️ {member.mention} nhận cảnh cáo **#{count}**.\nLý do: {reason}")

@bot.command()
@admin_only()
async def warn(ctx, member: discord.Member, *, reason="Không nêu lý do"):
    await do_warn(ctx, member, reason)

@bot.command()
@admin_only()
async def warnings(ctx, member: discord.Member):
    row = db.execute("SELECT count FROM warnings WHERE guild_id=? AND user_id=?",
                     (ctx.guild.id, member.id)).fetchone()
    count = row["count"] if row else 0
    logs = db.execute("""
        SELECT reason,created_at FROM warn_logs
        WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 5
    """, (ctx.guild.id, member.id)).fetchall()
    text = f"⚠️ {member.mention}: **{count}** cảnh cáo."
    if logs:
        text += "\n" + "\n".join(f"• <t:{r['created_at']}:R> — {r['reason']}" for r in logs)
    await ctx.reply(embed=embed("⚠️ Lịch sử cảnh cáo", text))

@bot.command()
@admin_only()
async def clearwarn(ctx, member: discord.Member):
    db.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
    db.execute("DELETE FROM warn_logs WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id))
    db.commit()
    await ctx.reply(f"✅ Đã xoá cảnh cáo của {member.mention}.")

@bot.command()
@admin_only()
async def kick(ctx, member: discord.Member, *, reason="Không nêu lý do"):
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.reply("❌ Không thể kick thành viên có role ngang/cao hơn bạn.")
    await member.kick(reason=reason)
    await ctx.reply(f"👢 Đã kick {member.mention}.")

@bot.command()
@admin_only()
async def ban(ctx, member: discord.Member, *, reason="Không nêu lý do"):
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.reply("❌ Không thể ban thành viên có role ngang/cao hơn bạn.")
    await member.ban(reason=reason)
    await ctx.reply(f"🔨 Đã ban {member.mention}.")

@bot.command()
@admin_only()
async def mute(ctx, member: discord.Member, minutes: int, *, reason="Không nêu lý do"):
    if minutes < 1 or minutes > 10080:
        return await ctx.reply("❌ Thời gian từ 1 đến 10080 phút.")
    until = discord.utils.utcnow() + timedelta(minutes=minutes)
    await member.timeout(until, reason=reason)
    await ctx.reply(f"🔇 Đã timeout {member.mention} trong **{minutes} phút**.")

# ---------------- GIVEAWAY ----------------

giveaways = {}
giveaway_counter = 0

class GiveawayView(discord.ui.View):
    def __init__(self, gid):
        super().__init__(timeout=None)
        self.gid = gid

    @discord.ui.button(label="Tham gia", emoji="🎉", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        g = giveaways.get(self.gid)
        if not g or g["ended"]:
            return await interaction.response.send_message("❌ Giveaway đã kết thúc.", ephemeral=True)
        g["users"].add(interaction.user.id)
        await interaction.response.send_message("🎉 Đã tham gia giveaway!", ephemeral=True)

@bot.command()
@admin_only()
async def giveaway(ctx, minutes: int, *, prize: str):
    global giveaway_counter
    if minutes < 1 or minutes > 10080:
        return await ctx.reply("❌ Thời gian từ 1 đến 10080 phút.")
    giveaway_counter += 1
    gid = giveaway_counter
    end_at = time.time() + minutes * 60
    giveaways[gid] = {"guild": ctx.guild.id, "channel": ctx.channel.id, "prize": prize,
                      "users": set(), "ended": False, "message": None}
    e = embed("🎁 GIVEAWAY", f"🎁 Phần thưởng: **{prize}**\n⏳ Kết thúc: <t:{int(end_at)}:R>\n\nNhấn **Tham gia** để tham gia!")
    msg = await ctx.send(embed=e, view=GiveawayView(gid))
    giveaways[gid]["message"] = msg.id
    await asyncio.sleep(minutes * 60)
    await end_giveaway(gid)

async def end_giveaway(gid):
    g = giveaways.get(gid)
    if not g or g["ended"]:
        return
    g["ended"] = True
    channel = bot.get_channel(g["channel"])
    if not channel:
        return
    users = list(g["users"])
    if users:
        winner = random.choice(users)
        await channel.send(f"🎉 Chúc mừng <@{winner}> đã thắng giveaway **{g['prize']}**!")
    else:
        await channel.send("🎁 Giveaway kết thúc nhưng không có người tham gia.")

@bot.command()
@admin_only()
async def gend(ctx):
    active = [gid for gid, g in giveaways.items() if g["guild"] == ctx.guild.id and not g["ended"]]
    if not active:
        return await ctx.reply("❌ Không có giveaway đang mở.")
    await end_giveaway(active[-1])
    await ctx.reply("✅ Đã kết thúc giveaway gần nhất.")

@bot.command()
async def gjoin(ctx):
    active = [gid for gid, g in giveaways.items() if g["guild"] == ctx.guild.id and not g["ended"]]
    if not active:
        return await ctx.reply("❌ Không có giveaway đang mở.")
    giveaways[active[-1]]["users"].add(ctx.author.id)
    await ctx.reply("🎉 Đã tham gia giveaway!")

# ---------------- ADMIN / OWNER ----------------

@bot.command()
@admin_only()
async def setlog(ctx, channel: discord.TextChannel):
    # Reserved for future persistent log setting.
    await ctx.reply(f"✅ Kênh log được đặt thành {channel.mention}.")

@bot.command()
@owner_only()
async def servers(ctx):
    lines = [f"• `{g.id}` — {g.name} — {g.member_count or 0} thành viên" for g in bot.guilds]
    await ctx.reply(embed=embed("👑 Server của Luna", "\n".join(lines)[:4000] or "Không có server."))

@bot.command()
@owner_only()
async def say(ctx, *, content: str):
    await ctx.message.delete()
    await ctx.send(content)

@bot.command()
@owner_only()
async def sync(ctx):
    synced = await bot.tree.sync()
    await ctx.reply(f"✅ Đã sync **{len(synced)}** slash commands.")

@bot.command()
@owner_only()
async def shutdown(ctx):
    await ctx.reply("🌙 Luna đang tắt...")
    await bot.close()

# ---------------- RUN ----------------

bot.started_at = time.monotonic()
bot.run(TOKEN)
