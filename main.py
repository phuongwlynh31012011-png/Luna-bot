import os
import sqlite3
import asyncio
import random
import time
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

# ============================================================
# LUNA — Discord Bot
# Prefix: l! / L!
# Slash: /hello /help only
# Database: SQLite
# Designed for multiple servers
# ============================================================

TOKEN = os.getenv("TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
PREFIXES = ("l!", "L!")
DB_FILE = os.getenv("LUNA_DB", "luna.db")

if not TOKEN:
    raise RuntimeError("Chưa có TOKEN. Hãy đặt biến môi trường TOKEN.")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
guilds_intent = True
intents.guilds = guilds_intent

bot = commands.Bot(
    command_prefix=PREFIXES,
    intents=intents,
    case_insensitive=True,
    help_command=None,
)

# ============================================================
# DATABASE
# ============================================================

db = sqlite3.connect(DB_FILE, check_same_thread=False)
db.row_factory = sqlite3.Row
db.execute("PRAGMA journal_mode=WAL")
db.execute("PRAGMA foreign_keys=ON")


def db_init():
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            balance INTEGER NOT NULL DEFAULT 0,
            daily_at INTEGER NOT NULL DEFAULT 0,
            work_at INTEGER NOT NULL DEFAULT 0,
            xp INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
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

        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            prefix TEXT NOT NULL DEFAULT 'l!',
            welcome_channel INTEGER,
            goodbye_channel INTEGER,
            log_channel INTEGER,
            autorole_id INTEGER,
            welcome_text TEXT NOT NULL DEFAULT 'Giữa vô vàn nơi để dừng chân, thật vui vì hôm nay bạn đã ghé qua đây. ♡\n\nHãy cứ thoải mái trò chuyện, tìm người chơi cùng, bật mic khi muốn, hay đơn giản là ngồi chill một chút dưới ánh trăng. ☾\n\nMong rằng từ một người xa lạ, bạn sẽ tìm thấy những người khiến mỗi lần online đều trở nên đáng mong chờ. ✦',
            goodbye_text TEXT NOT NULL DEFAULT '🌙 **{member_name}** đã rời khỏi **{server}**.\n\nCảm ơn bạn vì khoảng thời gian đã ở cùng mọi người. Hẹn gặp lại một ngày nào đó. ♡',
            welcome_title TEXT NOT NULL DEFAULT '🌙 Chào mừng bạn đến với {server}.',
            goodbye_title TEXT NOT NULL DEFAULT '🌙 Hẹn gặp lại {member_name}.',
            welcome_image TEXT NOT NULL DEFAULT '',
            goodbye_image TEXT NOT NULL DEFAULT '',
            welcome_color INTEGER NOT NULL DEFAULT 0xB8D8FF,
            goodbye_color INTEGER NOT NULL DEFAULT 0xB8D8FF,
            welcome_role INTEGER,
            goodbye_role INTEGER,
            welcome_enabled INTEGER NOT NULL DEFAULT 1,
            goodbye_enabled INTEGER NOT NULL DEFAULT 1,
            autorole_enabled INTEGER NOT NULL DEFAULT 0,
            xp_enabled INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS giveaways (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            message_id INTEGER,
            prize TEXT NOT NULL,
            end_at INTEGER NOT NULL,
            ended INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS giveaway_entries (
            giveaway_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY(giveaway_id, user_id)
        );
        """
    )
    db.commit()


db_init()

# Migrate older Luna databases without deleting existing data.
def db_migrate():
    columns = {row["name"] for row in db.execute("PRAGMA table_info(guild_config)").fetchall()}
    additions = {
        "welcome_title": "TEXT NOT NULL DEFAULT '🌙 Chào mừng bạn đến với {server}.'",
        "goodbye_title": "TEXT NOT NULL DEFAULT '🌙 Hẹn gặp lại {member_name}.'",
        "welcome_image": "TEXT NOT NULL DEFAULT ''",
        "goodbye_image": "TEXT NOT NULL DEFAULT ''",
        "welcome_color": "INTEGER NOT NULL DEFAULT 0xB8D8FF",
        "goodbye_color": "INTEGER NOT NULL DEFAULT 0xB8D8FF",
        "welcome_role": "INTEGER",
        "goodbye_role": "INTEGER",
    }
    for name, definition in additions.items():
        if name not in columns:
            db.execute(f"ALTER TABLE guild_config ADD COLUMN {name} {definition}")
    db.commit()

db_migrate()

# ============================================================
# HELPERS
# ============================================================


def embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()):
    return discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )


def money(amount: int) -> str:
    return f"{amount:,} xu"


def now_ts() -> int:
    return int(time.time())


def is_owner(user_id: int) -> bool:
    return OWNER_ID != 0 and user_id == OWNER_ID


def is_admin_member(member) -> bool:
    return isinstance(member, discord.Member) and (
        member.guild_permissions.administrator
        or member.guild_permissions.manage_guild
    )


def admin_only():
    async def predicate(ctx: commands.Context):
        return is_admin_member(ctx.author)
    return commands.check(predicate)


def owner_only():
    async def predicate(ctx: commands.Context):
        return is_owner(ctx.author.id)
    return commands.check(predicate)


def ensure_user(guild_id: int, user_id: int):
    db.execute(
        "INSERT OR IGNORE INTO users(guild_id,user_id) VALUES(?,?)",
        (guild_id, user_id),
    )
    db.commit()


def get_balance(guild_id: int, user_id: int) -> int:
    ensure_user(guild_id, user_id)
    row = db.execute(
        "SELECT balance FROM users WHERE guild_id=? AND user_id=?",
        (guild_id, user_id),
    ).fetchone()
    return int(row["balance"])


def add_balance(guild_id: int, user_id: int, amount: int):
    ensure_user(guild_id, user_id)
    db.execute(
        "UPDATE users SET balance=balance+? WHERE guild_id=? AND user_id=?",
        (amount, guild_id, user_id),
    )
    db.commit()


def take_balance(guild_id: int, user_id: int, amount: int) -> bool:
    ensure_user(guild_id, user_id)
    cur = db.execute(
        "UPDATE users SET balance=balance-? WHERE guild_id=? AND user_id=? AND balance>=?",
        (amount, guild_id, user_id, amount),
    )
    db.commit()
    return cur.rowcount == 1


def get_config(guild_id: int):
    row = db.execute("SELECT * FROM guild_config WHERE guild_id=?", (guild_id,)).fetchone()
    if row:
        return row
    db.execute("INSERT INTO guild_config(guild_id) VALUES(?)", (guild_id,))
    db.commit()
    return db.execute("SELECT * FROM guild_config WHERE guild_id=?", (guild_id,)).fetchone()


def update_config(guild_id: int, field: str, value):
    allowed = {
        "prefix", "welcome_channel", "goodbye_channel", "log_channel",
        "autorole_id", "welcome_text", "goodbye_text",
        "welcome_title", "goodbye_title", "welcome_image", "goodbye_image",
        "welcome_color", "goodbye_color", "welcome_role", "goodbye_role",
        "welcome_enabled", "goodbye_enabled", "autorole_enabled", "xp_enabled"
    }
    if field not in allowed:
        raise ValueError("Invalid config field")
    db.execute(f"UPDATE guild_config SET {field}=? WHERE guild_id=?", (value, guild_id))
    db.commit()


def format_message(template: str, member: discord.Member):
    # Unknown placeholders are left untouched instead of crashing the event.
    values = {
        "member": member.mention,
        "member_name": member.display_name,
        "username": member.name,
        "server": member.guild.name,
        "count": str(member.guild.member_count or 0),
        "id": str(member.id),
    }
    try:
        return template.format_map(_SafeFormatDict(values))
    except Exception:
        return template


class _SafeFormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def uptime_string():
    seconds = int(time.monotonic() - bot.started_at)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{days}d {hours}h {minutes}m {seconds}s"


async def send_log(guild: discord.Guild, title: str, description: str):
    cfg = get_config(guild.id)
    channel_id = cfg["log_channel"]
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        try:
            await channel.send(embed=embed(title, description, discord.Color.orange()))
        except discord.HTTPException:
            pass


async def add_xp(message: discord.Message):
    if not message.guild or message.author.bot:
        return
    cfg = get_config(message.guild.id)
    if not cfg["xp_enabled"]:
        return
    ensure_user(message.guild.id, message.author.id)
    row = db.execute(
        "SELECT xp,level FROM users WHERE guild_id=? AND user_id=?",
        (message.guild.id, message.author.id),
    ).fetchone()
    gained = random.randint(5, 12)
    xp = row["xp"] + gained
    level = row["level"]
    needed = 100 + level * 50
    leveled = False
    while xp >= needed:
        xp -= needed
        level += 1
        needed = 100 + level * 50
        leveled = True
    db.execute(
        "UPDATE users SET xp=?,level=? WHERE guild_id=? AND user_id=?",
        (xp, level, message.guild.id, message.author.id),
    )
    db.commit()
    if leveled:
        await message.channel.send(
            f"✨ Chúc mừng {message.author.mention} lên **Level {level}**!"
        )

# ============================================================
# EVENTS
# ============================================================

@bot.event
async def on_ready():
    bot.started_at = getattr(bot, "started_at", time.monotonic())
    try:
        await bot.tree.sync()
    except Exception as exc:
        print("Slash sync error:", repr(exc))
    print(f"🌙 Luna online: {bot.user} | {bot.user.id} | {len(bot.guilds)} servers")
    if not getattr(bot, "giveaway_task", None) or bot.giveaway_task.done():
        bot.giveaway_task = bot.loop.create_task(giveaway_watcher())
    # Khôi phục button cho các giveaway còn đang hoạt động sau restart.
    active = db.execute("SELECT id,message_id FROM giveaways WHERE ended=0 AND message_id IS NOT NULL").fetchall()
    for row in active:
        try:
            bot.add_view(GiveawayView(row["id"]), message_id=row["message_id"])
        except Exception:
            pass


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await add_xp(message)
    await bot.process_commands(message)


@bot.event
async def on_member_join(member: discord.Member):
    cfg = get_config(member.guild.id)

    # Autorole is independent from Welcome.
    if cfg["autorole_enabled"] and cfg["autorole_id"]:
        role = member.guild.get_role(cfg["autorole_id"])
        if role:
            try:
                await member.add_roles(role, reason="Luna autorole")
            except discord.HTTPException:
                pass

    if not cfg["welcome_enabled"] or not cfg["welcome_channel"]:
        return

    channel = member.guild.get_channel(cfg["welcome_channel"])
    if not channel:
        return

    title = format_message(cfg["welcome_title"], member)
    description = format_message(cfg["welcome_text"], member)
    e = embed(title, description, discord.Color(int(cfg["welcome_color"])))
    if cfg["welcome_image"]:
        e.set_image(url=cfg["welcome_image"])
    e.set_footer(text=f"{member.guild.name} • Luna")

    role_id = cfg["welcome_role"]
    role = member.guild.get_role(role_id) if role_id else None
    content = f"🪽 {member.mention} đã ghé qua {member.guild.name} rồi nè! ♡"
    if role:
        content += f"\n🎀 {role.mention} — ra chào đón thành viên mới nhé! ♡"

    try:
        await channel.send(content=content, embed=e)
    except discord.HTTPException as exc:
        print("Welcome send error:", repr(exc))


@bot.event
async def on_member_remove(member: discord.Member):
    cfg = get_config(member.guild.id)
    if not cfg["goodbye_enabled"] or not cfg["goodbye_channel"]:
        return

    channel = member.guild.get_channel(cfg["goodbye_channel"])
    if not channel:
        return

    title = format_message(cfg["goodbye_title"], member)
    description = format_message(cfg["goodbye_text"], member)
    e = embed(title, description, discord.Color(int(cfg["goodbye_color"])))
    if cfg["goodbye_image"]:
        e.set_image(url=cfg["goodbye_image"])
    e.set_footer(text=f"{member.guild.name} • Luna")

    role_id = cfg["goodbye_role"]
    role = member.guild.get_role(role_id) if role_id else None
    content = f"🌙 Tạm biệt {member.mention} — hẹn gặp lại! ♡"
    if role:
        content += f"\n🎀 {role.mention}"

    try:
        await channel.send(content=content, embed=e)
    except discord.HTTPException as exc:
        print("Goodbye send error:", repr(exc))


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        return await ctx.reply("🔒 Bạn không có quyền dùng lệnh này.")
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.reply("❌ Thiếu tham số. Dùng `l!help` để xem cú pháp.")
    if isinstance(error, commands.BadArgument):
        return await ctx.reply("❌ Tham số không hợp lệ. Kiểm tra lại cú pháp.")
    if isinstance(error, commands.CheckFailure):
        return await ctx.reply("🔒 Bạn không có quyền dùng lệnh này.")
    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.reply(f"⏳ Thử lại sau `{error.retry_after:.1f}s`.")
    print("COMMAND ERROR:", repr(error))
    try:
        await ctx.reply("❌ Có lỗi khi thực hiện lệnh.")
    except discord.HTTPException:
        pass

# ============================================================
# HELP
# ============================================================

CATEGORIES = {
    "money": ("💰 Tiền Lune", [
        "`l!balance [@user]` — xem số dư",
        "`l!give @user <số>` — chuyển xu",
        "`l!daily` — nhận xu hằng ngày",
        "`l!work` — làm việc kiếm xu",
        "`l!shop` — xem shop",
        "`l!setshop Tên | Giá | Mô tả` — thêm shop",
        "`l!buy <id> [số lượng]` — mua",
        "`l!inventory [@user]` — xem túi đồ",
        "`l!leaderboard` — bảng xếp hạng xu",
    ]),
    "games": ("🎮 Trò chơi", [
        "`l!rps <búa|kéo|bao> <cược>`",
        "`l!dice <1-6> <cược>`",
        "`l!baucua <mặt> <cược>`",
        "`l!doan <1-100> <cược>`",
        "`l!doando <đỏ|đen> <cược>`",
    ]),
    "social": ("💗 Social", [
        "`l!love [@user]` — xem SETL",
        "`l!hon @user` — hôn",
        "`l!xoadau @user` — xoa đầu",
        "`l!tat @user` — tát",
        "`l!om @user` — ôm",
        "`l!be @user` — bế",
        "`l!can @user` — cắn",
        "`l!kethon @user` — kết hôn",
        "`l!lyhon @user` — ly hôn",
    ]),
    "level": ("✨ Level / XP", [
        "`l!level [@user]` — xem level",
        "`l!rank [@user]` — xem thứ hạng",
        "`l!xptop` — bảng xếp hạng XP",
    ]),
    "moderation": ("🛡️ Moderation", [
        "`l!warn @user <lý do>`",
        "`l!warnings @user`",
        "`l!clearwarn @user`",
        "`l!kick @user [lý do]`",
        "`l!ban @user [lý do]`",
        "`l!unban <user_id>`",
        "`l!mute @user <phút> [lý do]`",
        "`l!unmute @user`",
        "`l!clear <số>`",
    ]),
    "server": ("⚙️ Server Setup", [
        "`l!settings` — xem cấu hình",
        "`l!setwelcome #kênh [@role]`",
        "`l!setgoodbye #kênh [@role]`",
        "`l!setlog #kênh`",
        "`l!setautorole @role`",
        "`l!welcome on/off`",
        "`l!goodbye on/off`",
        "`l!autorole on/off`",
        "`l!xp on/off`",
        "`l!setwelcometext <nội dung>`",
        "`l!setwelcometitle <tiêu đề>`",
        "`l!setwelcomeimage <link/ảnh>`",
        "`l!setwelcomecolor #mãmàu`",
        "`l!setwelcomerole @role`",
        "`l!setgoodbyetext <nội dung>`",
        "`l!setbyetitle <tiêu đề>`",
        "`l!setbyeimage <link/ảnh>`",
        "`l!setbyecolor #mãmàu`",
        "`l!setbyerole @role`",
        "`l!testwelcome` • `l!testbye`",
    ]),
    "owner": ("👑 Owner Bot", [
        "`l!botinfo` — thông tin Luna",
        "`l!servers` — danh sách server",
        "`l!say <nội dung>`",
        "`l!sync` — sync slash",
        "`l!shutdown` — tắt bot",
    ]),
}


class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Tiền Lune", emoji="💰", value="money"),
            discord.SelectOption(label="Trò chơi", emoji="🎮", value="games"),
            discord.SelectOption(label="Social", emoji="💗", value="social"),
            discord.SelectOption(label="Level / XP", emoji="✨", value="level"),
            discord.SelectOption(label="Moderation", emoji="🛡️", value="moderation"),
            discord.SelectOption(label="Server Setup", emoji="⚙️", value="server"),
            discord.SelectOption(label="Owner Bot", emoji="👑", value="owner"),
        ]
        super().__init__(placeholder="Chọn danh mục", options=options)

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        if key == "owner" and not is_owner(interaction.user.id):
            return await interaction.response.send_message(
                "🔒 Mục Owner Bot chỉ chủ bot mới xem được.", ephemeral=True
            )
        if key == "server" and not is_admin_member(interaction.user):
            return await interaction.response.send_message(
                "🔒 Mục Server Setup chỉ Admin/Manage Server mới xem được.", ephemeral=True
            )
        title, lines = CATEGORIES[key]
        await interaction.response.edit_message(
            embed=embed(f"🌙 LUNA • {title}", "\n".join(lines)),
            view=self.view,
        )


class HelpView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(HelpSelect())


async def send_help(target):
    e = embed(
        "🌙 • LUNA",
        "Luna hỗ trợ quản lý server, economy, game, level và các tiện ích.\n\n"
        "💡 Chọn danh mục bên dưới để xem lệnh.\n"
        "Prefix: `l!`"
    )
    if isinstance(target, commands.Context):
        await target.reply(embed=e, view=HelpView())
    else:
        await target.response.send_message(embed=e, view=HelpView())


# Slash-only basic commands: /hello and /help
@bot.tree.command(name="hello", description="Luna chào bạn")
async def slash_hello(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🌙 Xin chào {interaction.user.mention}! Luna đã sẵn sàng."
    )


@bot.tree.command(name="help", description="Mở bảng lệnh Luna")
async def slash_help(interaction: discord.Interaction):
    await send_help(interaction)


# ============================================================
# BASIC / INFO
# ============================================================

@bot.command(name="help", aliases=["h"])
async def help_cmd(ctx):
    await send_help(ctx)


@bot.command(name="botinfo", aliases=["info"])
async def botinfo(ctx):
    pyver = f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}.{__import__('sys').version_info.micro}"
    await ctx.reply(embed=embed(
        "🌙 LUNA — THÔNG TIN BOT",
        f"🤖 **Tên:** {bot.user}\n"
        f"🆔 **ID:** `{bot.user.id}`\n"
        f"📡 **Ping:** `{round(bot.latency * 1000)}ms`\n"
        f"⏱️ **Uptime:** `{uptime_string()}`\n\n"
        f"🏠 **Server:** `{len(bot.guilds)}`\n"
        f"👥 **Thành viên:** `{sum(g.member_count or 0 for g in bot.guilds):,}`\n\n"
        f"🐍 **Python:** `{pyver}`\n"
        f"📚 **discord.py:** `{discord.__version__}`\n"
        f"👑 **Owner:** <@{OWNER_ID}>"
    ))


@bot.command()
async def avatar(ctx, member: discord.Member | None = None):
    member = member or ctx.author
    e = embed(f"🖼️ Avatar • {member.display_name}")
    e.set_image(url=member.display_avatar.url)
    await ctx.reply(embed=e)


@bot.command()
async def userinfo(ctx, member: discord.Member | None = None):
    member = member or ctx.author
    await ctx.reply(embed=embed(
        f"👤 {member.display_name}",
        f"ID: `{member.id}`\n"
        f"Username: `{member.name}`\n"
        f"Tham gia Discord: {discord.utils.format_dt(member.created_at, 'F')}\n"
        f"Vào server: {discord.utils.format_dt(member.joined_at, 'F') if member.joined_at else 'Không rõ'}\n"
        f"Role cao nhất: {member.top_role.mention}"
    ))


@bot.command()
async def serverinfo(ctx):
    g = ctx.guild
    await ctx.reply(embed=embed(
        f"🏠 {g.name}",
        f"ID: `{g.id}`\n"
        f"Owner: <@{g.owner_id}>\n"
        f"Thành viên: `{g.member_count or 0}`\n"
        f"Kênh: `{len(g.channels)}`\n"
        f"Role: `{len(g.roles)}`\n"
        f"Tạo ngày: {discord.utils.format_dt(g.created_at, 'F')}"
    ))

# ============================================================
# ECONOMY
# ============================================================

@bot.command()
async def balance(ctx, member: discord.Member | None = None):
    member = member or ctx.author
    await ctx.reply(embed=embed(
        "💰 Số dư Lune",
        f"{member.mention} đang có **{money(get_balance(ctx.guild.id, member.id))}**."
    ))


@bot.command(aliases=["bal", "xu"])
async def balance2(ctx, member: discord.Member | None = None):
    await balance(ctx, member)


@bot.command()
async def daily(ctx):
    ensure_user(ctx.guild.id, ctx.author.id)
    row = db.execute(
        "SELECT daily_at FROM users WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, ctx.author.id)
    ).fetchone()
    remaining = 86400 - (now_ts() - row["daily_at"])
    if remaining > 0:
        return await ctx.reply(f"⏳ Daily còn **{remaining // 3600}h {(remaining % 3600) // 60}m**.")
    amount = random.randint(250, 500)
    db.execute(
        "UPDATE users SET balance=balance+?, daily_at=? WHERE guild_id=? AND user_id=?",
        (amount, now_ts(), ctx.guild.id, ctx.author.id)
    )
    db.commit()
    await ctx.reply(f"🌙 {ctx.author.mention} nhận **{money(amount)}** từ daily!")


@bot.command()
async def work(ctx):
    ensure_user(ctx.guild.id, ctx.author.id)
    row = db.execute(
        "SELECT work_at FROM users WHERE guild_id=? AND user_id=?",
        (ctx.guild.id, ctx.author.id)
    ).fetchone()
    remaining = 3600 - (now_ts() - row["work_at"])
    if remaining > 0:
        return await ctx.reply(f"⏳ Work còn **{remaining // 60}m {remaining % 60}s**.")
    amount = random.randint(80, 220)
    jobs = ["phục vụ quán", "làm nhiệm vụ", "thiết kế", "săn kho báu"]
    db.execute(
        "UPDATE users SET balance=balance+?, work_at=? WHERE guild_id=? AND user_id=?",
        (amount, now_ts(), ctx.guild.id, ctx.author.id)
    )
    db.commit()
    await ctx.reply(f"💼 {ctx.author.mention} vừa **{random.choice(jobs)}** và nhận **{money(amount)}**.")


@bot.command(aliases=["give"])
async def pay(ctx, member: discord.Member, amount: int):
    if member.bot or member.id == ctx.author.id or amount <= 0:
        return await ctx.reply("❌ Người nhận hoặc số xu không hợp lệ.")
    if not take_balance(ctx.guild.id, ctx.author.id, amount):
        return await ctx.reply("❌ Bạn không đủ xu.")
    add_balance(ctx.guild.id, member.id, amount)
    await ctx.reply(f"💸 {ctx.author.mention} đã chuyển **{money(amount)}** cho {member.mention}.")


@bot.command()
async def leaderboard(ctx):
    rows = db.execute(
        "SELECT user_id,balance FROM users WHERE guild_id=? ORDER BY balance DESC LIMIT 10",
        (ctx.guild.id,)
    ).fetchall()
    if not rows:
        return await ctx.reply("📊 Chưa có dữ liệu.")
    lines = [f"**{i}.** <@{r['user_id']}> — {money(r['balance'])}" for i, r in enumerate(rows, 1)]
    await ctx.reply(embed=embed("🏆 TOP XU", "\n".join(lines)))

# ============================================================
# SHOP
# ============================================================

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
    parts = [p.strip() for p in data.split("|", 3)]
    if len(parts) < 2:
        return await ctx.reply("Cú pháp: `l!setshop Tên | Giá | Mô tả | Kho` — Kho bỏ trống để vô hạn.")
    try:
        price = int(parts[1])
        stock = int(parts[3]) if len(parts) >= 4 and parts[3] else -1
    except ValueError:
        return await ctx.reply("❌ Giá/kho phải là số.")
    if price < 0 or stock < -1:
        return await ctx.reply("❌ Giá không âm, kho dùng `-1` để vô hạn.")
    name = parts[0][:80]
    desc = parts[2][:300] if len(parts) >= 3 else ""
    db.execute(
        "INSERT INTO shops(guild_id,name,price,description,stock) VALUES(?,?,?,?,?)",
        (ctx.guild.id, name, price, desc, stock)
    )
    db.commit()
    await ctx.reply(f"✅ Đã thêm **{name}** vào shop.")


@bot.command()
@admin_only()
async def editshop(ctx, item_id: int, price: int):
    if price < 0:
        return await ctx.reply("❌ Giá không được âm.")
    cur = db.execute("UPDATE shops SET price=? WHERE item_id=? AND guild_id=?", (price, item_id, ctx.guild.id))
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
    if quantity < 1 or quantity > 99:
        return await ctx.reply("❌ Số lượng từ 1 đến 99.")
    row = db.execute("SELECT * FROM shops WHERE item_id=? AND guild_id=?", (item_id, ctx.guild.id)).fetchone()
    if not row:
        return await ctx.reply("❌ Không tìm thấy vật phẩm.")
    if row["stock"] >= 0 and row["stock"] < quantity:
        return await ctx.reply("❌ Shop không đủ hàng.")
    total = row["price"] * quantity
    if not take_balance(ctx.guild.id, ctx.author.id, total):
        return await ctx.reply(f"❌ Bạn cần **{money(total)}**.")
    db.execute(
        "INSERT INTO inventory(user_id,guild_id,item_id,quantity) VALUES(?,?,?,?) "
        "ON CONFLICT(user_id,guild_id,item_id) DO UPDATE SET quantity=quantity+excluded.quantity",
        (ctx.author.id, ctx.guild.id, item_id, quantity)
    )
    if row["stock"] >= 0:
        db.execute("UPDATE shops SET stock=stock-? WHERE item_id=?", (quantity, item_id))
    db.commit()
    await ctx.reply(f"🛍️ Đã mua **{row['name']} x{quantity}** với **{money(total)}**.")


@bot.command()
async def inventory(ctx, member: discord.Member | None = None):
    member = member or ctx.author
    rows = db.execute(
        "SELECT s.name,i.quantity FROM inventory i JOIN shops s ON s.item_id=i.item_id "
        "WHERE i.user_id=? AND i.guild_id=? AND i.quantity>0",
        (member.id, ctx.guild.id)
    ).fetchall()
    if not rows:
        return await ctx.reply("🎒 Túi đồ đang trống.")
    await ctx.reply(embed=embed("🎒 Túi đồ", "\n".join(f"• {r['name']} × `{r['quantity']}`" for r in rows)))

# ============================================================
# GAMES
# ============================================================


def valid_bet(amount):
    return isinstance(amount, int) and 1 <= amount <= 1_000_000


@bot.command()
async def rps(ctx, choice: str, bet: int):
    aliases = {"bua":"búa", "búa":"búa", "keo":"kéo", "kéo":"kéo", "bao":"bao"}
    user = aliases.get(choice.lower())
    if not user or not valid_bet(bet):
        return await ctx.reply("❌ Chọn `búa`, `kéo`, `bao` và cược hợp lệ.")
    if not take_balance(ctx.guild.id, ctx.author.id, bet):
        return await ctx.reply("❌ Không đủ xu.")
    botc = random.choice(["búa", "kéo", "bao"])
    win = (user, botc) in [("búa","kéo"),("kéo","bao"),("bao","búa")]
    if user == botc:
        add_balance(ctx.guild.id, ctx.author.id, bet)
        result = f"🤝 Hoà! Nhận lại {money(bet)}."
    elif win:
        add_balance(ctx.guild.id, ctx.author.id, bet * 2)
        result = f"🎉 Thắng! Nhận {money(bet*2)}."
    else:
        result = f"💸 Thua {money(bet)}."
    await ctx.reply(f"🪨📄✂️ Bạn: **{user}** | Luna: **{botc}**\n{result}")


@bot.command()
async def dice(ctx, count: int, bet: int):
    if not 1 <= count <= 6 or not valid_bet(bet):
        return await ctx.reply("❌ Số xúc xắc 1–6 và cược hợp lệ.")
    if not take_balance(ctx.guild.id, ctx.author.id, bet):
        return await ctx.reply("❌ Không đủ xu.")
    rolls = [random.randint(1, 6) for _ in range(count)]
    total = sum(rolls)
    multiplier = 3 if total == count * 6 else 2 if total >= count * 4 else 0
    if multiplier:
        add_balance(ctx.guild.id, ctx.author.id, bet * multiplier)
        result = f"🎉 Nhận **{money(bet*multiplier)}**."
    else:
        result = f"💸 Mất **{money(bet)}**."
    await ctx.reply(f"🎲 Kết quả: **{' • '.join(map(str, rolls))}** | Tổng: **{total}**\n{result}")


@bot.command()
async def baucua(ctx, choice: str, bet: int):
    aliases = {"bau":"bầu","bầu":"bầu","cua":"cua","tom":"tôm","tôm":"tôm","ca":"cá","cá":"cá","ga":"gà","gà":"gà","nai":"nai"}
    c = aliases.get(choice.lower())
    if not c or not valid_bet(bet) or not take_balance(ctx.guild.id, ctx.author.id, bet):
        return await ctx.reply("❌ Cú pháp: `l!baucua <bầu|cua|tôm|cá|gà|nai> <cược>`.")
    rolls = [random.choice(["bầu","cua","tôm","cá","gà","nai"]) for _ in range(3)]
    hits = rolls.count(c)
    if hits:
        payout = bet * hits
        add_balance(ctx.guild.id, ctx.author.id, bet + payout)
        result = f"🎉 Ra **{hits} {c}** — nhận **{money(bet+payout)}**."
    else:
        result = f"💸 Không trúng — mất **{money(bet)}**."
    await ctx.reply(f"🎲 {', '.join(rolls)}\n{result}")


@bot.command()
async def doan(ctx, number: int, bet: int):
    if not 1 <= number <= 100 or not valid_bet(bet):
        return await ctx.reply("❌ Số đoán từ 1–100 và cược hợp lệ.")
    if not take_balance(ctx.guild.id, ctx.author.id, bet):
        return await ctx.reply("❌ Không đủ xu.")
    target = random.randint(1, 100)
    if number == target:
        add_balance(ctx.guild.id, ctx.author.id, bet * 5)
        await ctx.reply(f"🎯 Chính xác! Nhận **{money(bet*5)}**.")
    else:
        await ctx.reply(f"🔢 Số đúng là **{target}**. {money(bet)} đã dùng cho lượt chơi.")


@bot.command(aliases=["redblack"])
async def doando(ctx, color: str, bet: int):
    c = color.lower()
    if c not in ("đỏ","do","đen","den") or not valid_bet(bet):
        return await ctx.reply("❌ Chọn `đỏ` hoặc `đen` và cược hợp lệ.")
    if not take_balance(ctx.guild.id, ctx.author.id, bet):
        return await ctx.reply("❌ Không đủ xu.")
    actual = random.choice(["đỏ","đen"])
    chosen = "đỏ" if c in ("đỏ","do") else "đen"
    if chosen == actual:
        add_balance(ctx.guild.id, ctx.author.id, bet * 2)
        result = f"🎉 Ra **{actual}** — nhận **{money(bet*2)}**."
    else:
        result = f"💸 Ra **{actual}** — mất **{money(bet)}**."
    await ctx.reply(result)

# ============================================================
# LEVEL / XP
# ============================================================

@bot.command(aliases=["lv"])
async def level(ctx, member: discord.Member | None = None):
    member = member or ctx.author
    ensure_user(ctx.guild.id, member.id)
    row = db.execute("SELECT xp,level FROM users WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id)).fetchone()
    needed = 100 + row["level"] * 50
    await ctx.reply(embed=embed("✨ LEVEL", f"{member.mention}\nLevel: **{row['level']}**\nXP: **{row['xp']} / {needed}**"))


@bot.command(aliases=["rank"])
async def rank(ctx, member: discord.Member | None = None):
    member = member or ctx.author
    ensure_user(ctx.guild.id, member.id)
    row = db.execute("SELECT level,xp FROM users WHERE guild_id=? AND user_id=?", (ctx.guild.id, member.id)).fetchone()
    higher = db.execute("SELECT COUNT(*) AS c FROM users WHERE guild_id=? AND level>?", (ctx.guild.id, row["level"])).fetchone()["c"]
    await ctx.reply(f"🏅 {member.mention} đang ở khoảng **#{higher + 1}** với Level **{row['level']}**.")

@bot.command()
async def xptop(ctx):
    rows = db.execute("SELECT user_id,level,xp FROM users WHERE guild_id=? ORDER BY level DESC,xp DESC LIMIT 10", (ctx.guild.id,)).fetchall()
    if not rows:
        return await ctx.reply("📊 Chưa có dữ liệu XP.")
    lines = [f"**{i}.** <@{r['user_id']}> — Lv.{r['level']} • {r['xp']} XP" for i,r in enumerate(rows,1)]
    await ctx.reply(embed=embed("🏆 TOP XP", "\n".join(lines)))

# ============================================================
# SETL / SOCIAL
# ============================================================

DEFAULT_LOVE = "🌙 Một chút dịu dàng, một chút đáng yêu — Luna gửi tới bạn."


@bot.command()
@admin_only()
async def setlove(ctx, *, content: str):
    db.execute("INSERT INTO loves(guild_id,content) VALUES(?,?) ON CONFLICT(guild_id) DO UPDATE SET content=excluded.content", (ctx.guild.id, content[:1000]))
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
    if member.bot:
        return await ctx.reply("🤖 Không thực hiện tương tác này với bot.")
    await ctx.reply(f"💗 {ctx.author.mention} **{verb}** {member.mention}")


for _name, _verb in [("hon","hôn"),("xoadau","xoa đầu"),("tat","tát"),("om","ôm"),("be","bế"),("can","cắn")]:
    async def _action_command(ctx, member: discord.Member, _v=_verb):
        await action(ctx, _v, member)
    _action_command.__name__ = _name
    bot.command(name=_name)(_action_command)


@bot.command()
async def kethon(ctx, member: discord.Member):
    if member.id == ctx.author.id or member.bot:
        return await ctx.reply("❌ Không thể kết hôn với tài khoản này.")
    pair = tuple(sorted((ctx.author.id, member.id)))
    db.execute("INSERT OR IGNORE INTO marriages(user1,user2,guild_id,created_at) VALUES(?,?,?,?)", (pair[0],pair[1],ctx.guild.id,now_ts()))
    db.commit()
    await ctx.reply(f"💍 {ctx.author.mention} và {member.mention} đã đăng ký kết hôn trong Luna.")


@bot.command()
async def lyhon(ctx, member: discord.Member):
    pair = tuple(sorted((ctx.author.id, member.id)))
    cur = db.execute("DELETE FROM marriages WHERE user1=? AND user2=? AND guild_id=?", (pair[0],pair[1],ctx.guild.id))
    db.commit()
    await ctx.reply("💔 Đã ly hôn." if cur.rowcount else "❌ Hai người chưa có hôn thú trong Luna.")

# ============================================================
# MODERATION
# ============================================================

async def do_warn(ctx, member, reason):
    if member.bot or member.id == ctx.author.id:
        return await ctx.reply("❌ Không thể cảnh cáo tài khoản này.")
    row = db.execute("SELECT count FROM warnings WHERE guild_id=? AND user_id=?", (ctx.guild.id,member.id)).fetchone()
    count = (row["count"] if row else 0) + 1
    db.execute("INSERT INTO warnings(guild_id,user_id,count) VALUES(?,?,?) ON CONFLICT(guild_id,user_id) DO UPDATE SET count=excluded.count", (ctx.guild.id,member.id,count))
    db.execute("INSERT INTO warn_logs(guild_id,user_id,moderator_id,reason,created_at) VALUES(?,?,?,?,?)", (ctx.guild.id,member.id,ctx.author.id,reason,now_ts()))
    db.commit()
    await ctx.reply(f"⚠️ {member.mention} nhận cảnh cáo **#{count}**.\nLý do: {reason}")
    await send_log(ctx.guild,"⚠️ WARN",f"{member.mention} bị warn bởi {ctx.author.mention}\nLý do: {reason}")


@bot.command()
@admin_only()
async def warn(ctx, member: discord.Member, *, reason="Không nêu lý do"):
    await do_warn(ctx, member, reason)


@bot.command()
@admin_only()
async def warnings(ctx, member: discord.Member):
    row = db.execute("SELECT count FROM warnings WHERE guild_id=? AND user_id=?", (ctx.guild.id,member.id)).fetchone()
    count = row["count"] if row else 0
    logs = db.execute("SELECT reason,created_at FROM warn_logs WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 5", (ctx.guild.id,member.id)).fetchall()
    text = f"{member.mention}: **{count}** cảnh cáo."
    if logs:
        text += "\n" + "\n".join(f"• <t:{r['created_at']}:R> — {r['reason']}" for r in logs)
    await ctx.reply(embed=embed("⚠️ Lịch sử cảnh cáo",text))


@bot.command()
@admin_only()
async def clearwarn(ctx, member: discord.Member):
    db.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (ctx.guild.id,member.id))
    db.execute("DELETE FROM warn_logs WHERE guild_id=? AND user_id=?", (ctx.guild.id,member.id))
    db.commit()
    await ctx.reply(f"✅ Đã xoá cảnh cáo của {member.mention}.")


@bot.command()
@admin_only()
async def kick(ctx, member: discord.Member, *, reason="Không nêu lý do"):
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.reply("❌ Không thể kick role ngang/cao hơn bạn.")
    await member.kick(reason=reason)
    await ctx.reply(f"👢 Đã kick {member.mention}.")
    await send_log(ctx.guild,"👢 KICK",f"{member} bị kick bởi {ctx.author.mention}\nLý do: {reason}")


@bot.command()
@admin_only()
async def ban(ctx, member: discord.Member, *, reason="Không nêu lý do"):
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.reply("❌ Không thể ban role ngang/cao hơn bạn.")
    await member.ban(reason=reason)
    await ctx.reply(f"🔨 Đã ban {member.mention}.")
    await send_log(ctx.guild,"🔨 BAN",f"{member} bị ban bởi {ctx.author.mention}\nLý do: {reason}")


@bot.command()
@admin_only()
async def unban(ctx, user_id: int):
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.reply(f"✅ Đã unban **{user}**.")
    except (discord.NotFound, discord.HTTPException):
        await ctx.reply("❌ Không tìm thấy user trong danh sách ban hoặc Discord từ chối thao tác.")


@bot.command()
@admin_only()
async def mute(ctx, member: discord.Member, minutes: int, *, reason="Không nêu lý do"):
    if not 1 <= minutes <= 10080:
        return await ctx.reply("❌ Thời gian từ 1 đến 10080 phút.")
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.reply("❌ Không thể timeout role ngang/cao hơn bạn.")
    await member.timeout(discord.utils.utcnow() + timedelta(minutes=minutes), reason=reason)
    await ctx.reply(f"🔇 Đã timeout {member.mention} trong **{minutes} phút**.")
    await send_log(ctx.guild,"🔇 TIMEOUT",f"{member.mention} — {minutes} phút\nLý do: {reason}")

@bot.command()
@admin_only()
async def unmute(ctx, member: discord.Member):
    await member.timeout(None, reason=f"Unmute by {ctx.author}")
    await ctx.reply(f"🔊 Đã gỡ timeout cho {member.mention}.")


@bot.command()
@admin_only()
async def clear(ctx, amount: int):
    if not 1 <= amount <= 100:
        return await ctx.reply("❌ Số lượng từ 1 đến 100.")
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Đã xoá **{len(deleted)-1}** tin nhắn.")
    await asyncio.sleep(3)
    try:
        await msg.delete()
    except discord.HTTPException:
        pass

# ============================================================
# ADMIN / WELCOME / GOODBYE
# ============================================================

"""Register all server/admin commands on the shared Luna bot."""

@bot.command()
@admin_only()
async def settings(ctx):
    cfg = get_config(ctx.guild.id)
    def ch(cid):
        return f"<#{cid}>" if cid else "Chưa đặt"
    def role(rid):
        return f"<@&{rid}>" if rid else "Chưa đặt"
    await ctx.reply(embed=embed("⚙️ Cấu hình Luna",
        f"👋 Welcome: {'Bật' if cfg['welcome_enabled'] else 'Tắt'} • {ch(cfg['welcome_channel'])}\n"
        f"🚪 Goodbye: {'Bật' if cfg['goodbye_enabled'] else 'Tắt'} • {ch(cfg['goodbye_channel'])}\n"
        f"🎀 Welcome role: {role(cfg['welcome_role'])}\n"
        f"🎀 Goodbye role: {role(cfg['goodbye_role'])}\n"
        f"🖼️ Welcome ảnh: {'Đã cài' if cfg['welcome_image'] else 'Chưa cài'}\n"
        f"🖼️ Goodbye ảnh: {'Đã cài' if cfg['goodbye_image'] else 'Chưa cài'}\n"
        f"📋 Log: {ch(cfg['log_channel'])}\n"
        f"🎭 Autorole: {'Bật' if cfg['autorole_enabled'] else 'Tắt'} • {role(cfg['autorole_id'])}\n"
        f"✨ XP: {'Bật' if cfg['xp_enabled'] else 'Tắt'}"
    ))

@bot.command()
@admin_only()
async def setwelcome(ctx, channel: discord.TextChannel, role: discord.Role | None = None):
    update_config(ctx.guild.id, "welcome_channel", channel.id)
    if role:
        update_config(ctx.guild.id, "welcome_role", role.id)
    await ctx.reply(f"✅ Welcome: {channel.mention}" + (f" • Role: {role.mention}" if role else ""))

@bot.command()
@admin_only()
async def setgoodbye(ctx, channel: discord.TextChannel, role: discord.Role | None = None):
    update_config(ctx.guild.id, "goodbye_channel", channel.id)
    if role:
        update_config(ctx.guild.id, "goodbye_role", role.id)
    await ctx.reply(f"✅ Goodbye: {channel.mention}" + (f" • Role: {role.mention}" if role else ""))

@bot.command()
@admin_only()
async def setlog(ctx, channel: discord.TextChannel):
    update_config(ctx.guild.id, "log_channel", channel.id)
    await ctx.reply(f"✅ Log channel: {channel.mention}")

@bot.command()
@admin_only()
async def setautorole(ctx, role: discord.Role):
    update_config(ctx.guild.id, "autorole_id", role.id)
    await ctx.reply(f"✅ Autorole đã đặt thành {role.mention}.")

async def toggle_setting(ctx, field, value, label):
    update_config(ctx.guild.id, field, 1 if value == "on" else 0)
    await ctx.reply(f"✅ {label}: **{'BẬT' if value == 'on' else 'TẮT'}**")

@bot.command()
@admin_only()
async def welcome(ctx, value: str):
    value = value.lower()
    if value not in ("on", "off"):
        return await ctx.reply("Dùng `l!welcome on` hoặc `l!welcome off`.")
    await toggle_setting(ctx, "welcome_enabled", value, "Welcome")

@bot.command()
@admin_only()
async def goodbye(ctx, value: str):
    value = value.lower()
    if value not in ("on", "off"):
        return await ctx.reply("Dùng `l!goodbye on` hoặc `l!goodbye off`.")
    await toggle_setting(ctx, "goodbye_enabled", value, "Goodbye")

@bot.command()
@admin_only()
async def autorole(ctx, value: str):
    value = value.lower()
    if value not in ("on", "off"):
        return await ctx.reply("Dùng `l!autorole on` hoặc `l!autorole off`.")
    await toggle_setting(ctx, "autorole_enabled", value, "Autorole")

@bot.command()
@admin_only()
async def xp(ctx, value: str):
    value = value.lower()
    if value not in ("on", "off"):
        return await ctx.reply("Dùng `l!xp on` hoặc `l!xp off`.")
    await toggle_setting(ctx, "xp_enabled", value, "XP")

@bot.command()
@admin_only()
async def setwelcometext(ctx, *, content: str):
    update_config(ctx.guild.id, "welcome_text", content[:4000])
    await ctx.reply("✅ Đã cập nhật nội dung Welcome.")

@bot.command(aliases=["setwelcomemsg"])
@admin_only()
async def setwelcomemessage(ctx, *, content: str):
    update_config(ctx.guild.id, "welcome_text", content[:4000])
    await ctx.reply("✅ Đã cập nhật nội dung Welcome.")

@bot.command()
@admin_only()
async def setwelcometitle(ctx, *, title: str):
    update_config(ctx.guild.id, "welcome_title", title[:256])
    await ctx.reply("✅ Đã cập nhật tiêu đề Welcome.")

@bot.command()
@admin_only()
async def setwelcomeimage(ctx, url: str | None = None):
    if not url and ctx.message.attachments:
        url = ctx.message.attachments[0].url
    if url and not url.startswith(("http://", "https://")):
        return await ctx.reply("❌ Link ảnh phải bắt đầu bằng `https://` hoặc `http://`.")
    update_config(ctx.guild.id, "welcome_image", url or "")
    await ctx.reply("🖼️ Đã cập nhật ảnh Welcome." if url else "🖼️ Đã xoá ảnh Welcome.")

@bot.command()
@admin_only()
async def setwelcomecolor(ctx, color: str):
    raw = color.strip().replace("#", "")
    if len(raw) != 6:
        return await ctx.reply("❌ Màu phải dạng `#B8D8FF`.")
    try:
        value = int(raw, 16)
    except ValueError:
        return await ctx.reply("❌ Mã màu không hợp lệ.")
    update_config(ctx.guild.id, "welcome_color", value)
    await ctx.reply("🎨 Đã đổi màu Welcome.")

@bot.command()
@admin_only()
async def setwelcomerole(ctx, role: discord.Role | None = None):
    update_config(ctx.guild.id, "welcome_role", role.id if role else None)
    await ctx.reply(f"🎀 Welcome role: {role.mention}" if role else "🎀 Đã xoá Welcome role.")

@bot.command()
@admin_only()
async def setgoodbyetext(ctx, *, content: str):
    update_config(ctx.guild.id, "goodbye_text", content[:4000])
    await ctx.reply("✅ Đã cập nhật nội dung Goodbye.")

@bot.command(aliases=["setbyemsg"])
@admin_only()
async def setbyemessage(ctx, *, content: str):
    update_config(ctx.guild.id, "goodbye_text", content[:4000])
    await ctx.reply("✅ Đã cập nhật nội dung Goodbye.")

@bot.command()
@admin_only()
async def setbyetitle(ctx, *, title: str):
    update_config(ctx.guild.id, "goodbye_title", title[:256])
    await ctx.reply("✅ Đã cập nhật tiêu đề Goodbye.")

@bot.command()
@admin_only()
async def setbyeimage(ctx, url: str | None = None):
    if not url and ctx.message.attachments:
        url = ctx.message.attachments[0].url
    if url and not url.startswith(("http://", "https://")):
        return await ctx.reply("❌ Link ảnh phải bắt đầu bằng `https://` hoặc `http://`.")
    update_config(ctx.guild.id, "goodbye_image", url or "")
    await ctx.reply("🖼️ Đã cập nhật ảnh Goodbye." if url else "🖼️ Đã xoá ảnh Goodbye.")

@bot.command()
@admin_only()
async def setbyecolor(ctx, color: str):
    raw = color.strip().replace("#", "")
    if len(raw) != 6:
        return await ctx.reply("❌ Màu phải dạng `#B8D8FF`.")
    try:
        value = int(raw, 16)
    except ValueError:
        return await ctx.reply("❌ Mã màu không hợp lệ.")
    update_config(ctx.guild.id, "goodbye_color", value)
    await ctx.reply("🎨 Đã đổi màu Goodbye.")

@bot.command()
@admin_only()
async def setbyerole(ctx, role: discord.Role | None = None):
    update_config(ctx.guild.id, "goodbye_role", role.id if role else None)
    await ctx.reply(f"🎀 Goodbye role: {role.mention}" if role else "🎀 Đã xoá Goodbye role.")

@bot.command()
@admin_only()
async def testwelcome(ctx):
    cfg = get_config(ctx.guild.id)
    member = ctx.author
    e = embed(format_message(cfg["welcome_title"], member), format_message(cfg["welcome_text"], member), discord.Color(int(cfg["welcome_color"])))
    if cfg["welcome_image"]:
        e.set_image(url=cfg["welcome_image"])
    role = ctx.guild.get_role(cfg["welcome_role"]) if cfg["welcome_role"] else None
    content = f"🪽 {member.mention} đã ghé qua {ctx.guild.name} rồi nè! ♡"
    if role:
        content += f"\n🎀 {role.mention} — ra chào đón thành viên mới nhé! ♡"
    await ctx.reply(content=content, embed=e)

@bot.command()
@admin_only()
async def testbye(ctx):
    cfg = get_config(ctx.guild.id)
    member = ctx.author
    e = embed(format_message(cfg["goodbye_title"], member), format_message(cfg["goodbye_text"], member), discord.Color(int(cfg["goodbye_color"])))
    if cfg["goodbye_image"]:
        e.set_image(url=cfg["goodbye_image"])
    role = ctx.guild.get_role(cfg["goodbye_role"]) if cfg["goodbye_role"] else None
    content = f"🌙 Tạm biệt {member.mention} — hẹn gặp lại! ♡"
    if role:
        content += f"\n🎀 {role.mention}"
    await ctx.reply(content=content, embed=e)

# ============================================================
# GIVEAWAY — PERSISTENT ACROSS RESTARTS
# ============================================================

class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id: int):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="Tham gia", emoji="🎉", style=discord.ButtonStyle.success, custom_id="luna:giveaway_join")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        row = db.execute("SELECT * FROM giveaways WHERE id=? AND ended=0", (self.giveaway_id,)).fetchone()
        if not row or row["end_at"] <= now_ts():
            return await interaction.response.send_message("❌ Giveaway đã kết thúc.", ephemeral=True)
        db.execute("INSERT OR IGNORE INTO giveaway_entries(giveaway_id,user_id) VALUES(?,?)", (self.giveaway_id,interaction.user.id))
        db.commit()
        await interaction.response.send_message("🎉 Đã tham gia giveaway!", ephemeral=True)


async def end_giveaway(gid: int):
    row = db.execute("SELECT * FROM giveaways WHERE id=? AND ended=0", (gid,)).fetchone()
    if not row:
        return False
    db.execute("UPDATE giveaways SET ended=1 WHERE id=?", (gid,))
    db.commit()
    channel = bot.get_channel(row["channel_id"])
    if not channel:
        return False
    entries = db.execute("SELECT user_id FROM giveaway_entries WHERE giveaway_id=?", (gid,)).fetchall()
    users = [r["user_id"] for r in entries]
    if not users:
        await channel.send(f"🎁 Giveaway **{row['prize']}** kết thúc nhưng không có người tham gia.")
        return True
    winner = random.choice(users)
    await channel.send(f"🎉 Chúc mừng <@{winner}> đã thắng giveaway **{row['prize']}**!")
    return True


async def giveaway_watcher():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            rows = db.execute("SELECT id FROM giveaways WHERE ended=0 AND end_at<=?", (now_ts(),)).fetchall()
            for row in rows:
                await end_giveaway(row["id"])
        except Exception as exc:
            print("Giveaway watcher error:", repr(exc))
        await asyncio.sleep(10)


@bot.command()
@admin_only()
async def giveaway(ctx, minutes: int, *, prize: str):
    if not 1 <= minutes <= 10080:
        return await ctx.reply("❌ Thời gian từ 1 đến 10080 phút.")
    end_at = now_ts() + minutes * 60
    cur = db.execute(
        "INSERT INTO giveaways(guild_id,channel_id,prize,end_at) VALUES(?,?,?,?)",
        (ctx.guild.id,ctx.channel.id,prize[:300],end_at)
    )
    gid = cur.lastrowid
    db.commit()
    msg = await ctx.send(embed=embed("🎁 GIVEAWAY", f"🎁 Phần thưởng: **{prize}**\n⏳ Kết thúc: <t:{end_at}:R>\n\nNhấn **Tham gia** để tham gia!"), view=GiveawayView(gid))
    db.execute("UPDATE giveaways SET message_id=? WHERE id=?", (msg.id,gid))
    db.commit()


@bot.command()
async def gjoin(ctx):
    row = db.execute("SELECT id FROM giveaways WHERE guild_id=? AND ended=0 ORDER BY id DESC LIMIT 1", (ctx.guild.id,)).fetchone()
    if not row:
        return await ctx.reply("❌ Không có giveaway đang mở.")
    db.execute("INSERT OR IGNORE INTO giveaway_entries(giveaway_id,user_id) VALUES(?,?)", (row["id"],ctx.author.id))
    db.commit()
    await ctx.reply("🎉 Đã tham gia giveaway!")


@bot.command()
@admin_only()
async def gend(ctx):
    row = db.execute("SELECT id FROM giveaways WHERE guild_id=? AND ended=0 ORDER BY id DESC LIMIT 1", (ctx.guild.id,)).fetchone()
    if not row:
        return await ctx.reply("❌ Không có giveaway đang mở.")
    await end_giveaway(row["id"])
    await ctx.reply("✅ Đã kết thúc giveaway gần nhất.")

# ============================================================
# OWNER
# ============================================================

@bot.command()
@owner_only()
async def servers(ctx):
    lines = [f"• `{g.id}` — {g.name} — {g.member_count or 0} TV" for g in bot.guilds]
    await ctx.reply(embed=embed("👑 Server của Luna", "\n".join(lines)[:4000] or "Không có server."))


@bot.command()
@owner_only()
async def say(ctx, *, content: str):
    try:
        await ctx.message.delete()
    except discord.HTTPException:
        pass
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


# ============================================================
# RUN
# ============================================================

bot.started_at = time.monotonic()
bot.giveaway_task = None

if __name__ == "__main__":
    bot.run(TOKEN)
