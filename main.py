import os
import sqlite3
import asyncio
import random
import time
import re
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

LUNA_COIN_ICON = "https://raw.githubusercontent.com/phuongwlynh31012011-png/Luna-bot/7ef75e7bc87bcb26ef5cfdb7ed813470a5307cdf/luna_xu_emoji.png"

def random_reply(replies):
    return random.choice(replies)

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
    db.executescript("""
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
            PRIMARY KEY (user_id, guild_id, item_id)
        );

        CREATE TABLE IF NOT EXISTS warnings (
            guild_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (guild_id, user_id)
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

        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            prefix TEXT NOT NULL DEFAULT 'l!',
            log_channel INTEGER,
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
            PRIMARY KEY (giveaway_id, user_id)
        );

        CREATE TABLE IF NOT EXISTS marriages (
    user1 INTEGER NOT NULL,
    user2 INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    intimacy INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user1, user2),
    UNIQUE (user1),
    UNIQUE (user2)
        );

                CREATE TABLE IF NOT EXISTS antilink_settings (
            guild_id INTEGER PRIMARY KEY,
            enabled INTEGER NOT NULL DEFAULT 0
        );
    """)

    db.commit()


db_init()

# Migrate older Luna databases without deleting existing data.
def db_migrate():
    # Kiểm tra cột của bảng marriages
    marriage_columns = {
        row["name"]
        for row in db.execute(
            "PRAGMA table_info(marriages)"
        ).fetchall()
    }

    # Database cũ chưa có intimacy thì thêm vào
    if "intimacy" not in marriage_columns:
        db.execute(
            "ALTER TABLE marriages "
            "ADD COLUMN intimacy INTEGER NOT NULL DEFAULT 0"
        )

    db.commit()


db_migrate()
        
# ============================================================
# HELPERS
# ============================================================


MAX_INTIMACY = 20000

def get_love_level(intimacy):
    if intimacy >= 15000:
        return "💍 Định mệnh"
    elif intimacy >= 5000:
        return "💞 Tâm đầu ý hợp"
    elif intimacy >= 1000:
        return "💗 Thân thiết"
    else:
        return "🌱 Mới quen"


def add_intimacy(user1, user2, amount):
    pair = tuple(sorted((user1, user2)))

    row = db.execute(
        """
        SELECT intimacy
        FROM marriages
        WHERE user1 = ?
        AND user2 = ?
        """,
        pair
    ).fetchone()

    if row is None:
        return None

    current = row["intimacy"]

    new_intimacy = min(
        current + amount,
        MAX_INTIMACY
    )

    db.execute(
        """
        UPDATE marriages
        SET intimacy = ?
        WHERE user1 = ?
        AND user2 = ?
        """,
        (
            new_intimacy,
            pair[0],
            pair[1]
        )
    )

    db.commit()

    return new_intimacy


def embed(title: str, description: str = "", color: discord.Color = discord.Color.blurple()):
    return discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    return e


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


def normalize_role_name(name: str) -> str:
    name = name.lower()

    for char in ["☾", "☽", "•", "・", "│", "┃", "「", "」", "︱", "━", "─", "✦", "✦"]:
        name = name.replace(char, "")

    return name.strip()


def staff_or_admin():
    async def predicate(ctx: commands.Context):

        if is_admin_member(ctx.author):
            return True

        if not isinstance(ctx.author, discord.Member):
            return False

        for user_role in ctx.author.roles:
            role_name = normalize_role_name(user_role.name)

            if "staff" in role_name:
                return True

        return False

    return commands.check(predicate)


def staff_or_admin():
    async def predicate(ctx: commands.Context):

        # Admin / Manage Server
        if is_admin_member(ctx.author):
            return True

        if not isinstance(ctx.author, discord.Member):
            return False

        # Tự tìm role Staff trong server hiện tại
        for user_role in ctx.author.roles:

            role_name = normalize_role_name(user_role.name)

            # Nhận Staff / 𝑺𝒕𝒂𝒇𝒇
            if "staff" in role_name:
                return True

        return False

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
        "prefix", "log_channel", "xp_enabled"
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



INVITE_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?"
    r"(?:discord\.gg|discord(?:app)?\.com/invite)/"
    r"([a-zA-Z0-9-]+)",
    re.IGNORECASE
)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.guild is not None:
        setting = db.execute(
            "SELECT enabled FROM antilink_settings WHERE guild_id = ?",
            (message.guild.id,)
        ).fetchone()

        if setting and setting["enabled"]:
            codes = INVITE_PATTERN.findall(message.content)

            for code in codes:
                try:
                    invite = await bot.fetch_invite(code)

                    # Cho phép link mời của chính server hiện tại
                    if (
                        invite.guild is not None
                        and invite.guild.id == message.guild.id
                    ):
                        continue

                    # Chỉ xóa khi xác định được link dẫn đến server khác
                    if invite.guild is not None:
                        await message.delete()

                        await message.channel.send(
                            f"{message.author.mention} 🌙 "
                            "Không được gửi link mời server khác nhé!",
                            delete_after=5
                        )
                        return

                except discord.NotFound:
                    continue
                except discord.Forbidden:
                    print(
                        "Luna thiếu quyền Manage Messages "
                        "hoặc Send Messages."
                    )
                    return
                except discord.HTTPException as error:
                    print(f"Lỗi kiểm tra link mời: {error}")
                    continue

    # Giữ nguyên XP và xử lý lệnh hiện tại
    await add_xp(message)
    await bot.process_commands(message)
     

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
    "info": ("🌙 Thông tin", [
        "`l!help` / `l!h` — bảng lệnh Luna (Luna core)",
        "`l!info` / `l!botinfo` — thông tin bot",
        "`l!avatar [@user]` — xem avatar",
        "`l!userinfo [@user]` — thông tin thành viên",
        "`l!serverinfo` — thông tin server",
    ]),
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
        "`l!baucua <bầu|cua|tôm|cá|gà|nai> <cược>`",
        "`l!doanso <1-100> <cược>`",
        "`l!doden <đỏ|đen> <cược>`",
    ]),
    "social": ("💗 Social", [
        "`l!love [@user]` — xem SETL",
        "`l!hon @user` — hôn",
        "`l!xoadau @user` — xoa đầu",
        "`l!tat @user` — tát",
        "`l!om @user` — ôm",
        "`l!be @user` — bế",
        "`l!can @user` — cắn",
        "`l!marriage [@user]` — xem thông tin hôn nhân",
        "`l!kethon @user` — kết hôn",
        "`l!lyhon @user` — ly hôn",
    ]),
    "level": ("✨ Level / XP", [
        "`l!level [@user]` — xem level",
        "`l!rank [@user]` — xem thứ hạng",
        "`l!xptop` — bảng xếp hạng XP",
    ]),
    "moderation": ("🛡️ Moderation", [
        "`l!role @user tên-role` — thêm role cho thành viên",
        "`l!unrole @user tên-role` — gỡ role khỏi thành viên",
        "`l!lock` — khoá kênh hiện tại",
        "`l!unlock` — mở khoá kênh hiện tại",
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
        "`l!setlog #kênh` — đặt kênh log",
        "`l!xp on/off` — bật/tắt XP",
        "`l!antilink on/off` — bật/tắt chặn link mời",
    ]),
    "owner": ("👑 Owner Bot", [
        "`l!cheatxu @user <số xu>` — cộng xu cho user",
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
        "☾ 𝐋𝐔𝐍𝐀 𝐂𝐎𝐑𝐄",
        "Bot Discord hỗ trợ cộng đồng với các tính năng quản lý, giải trí và tiện ích khác.\n\n"
        "Prefix: `L!` `l!`\n"
        "✦ Chọn danh mục bên dưới để khám phá thêm."
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

    e = embed(
        "🌙 Số dư Luna",
        f"{member.mention} đang có **{money(get_balance(ctx.guild.id, member.id))}**."
    )

    e.set_thumbnail(url=LUNA_COIN_ICON)

    await ctx.reply(embed=e)


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
    aliases = {
        "bau": "bầu",
        "bầu": "bầu",
        "cua": "cua",
        "tom": "tôm",
        "tôm": "tôm",
        "ca": "cá",
        "cá": "cá",
        "ga": "gà",
        "gà": "gà",
        "nai": "nai"
    }

    c = aliases.get(choice.lower())

    if not c:
        return await ctx.reply(
            "❌ Cú pháp: `l!baucua <bầu|cua|tôm|cá|gà|nai> <cược>`."
        )

    if not valid_bet(bet):
        return await ctx.reply("❌ Số xu cược không hợp lệ.")

    if not take_balance(ctx.guild.id, ctx.author.id, bet):
        return await ctx.reply("❌ Không đủ xu.")

    rolls = [
        random.choice(["bầu", "cua", "tôm", "cá", "gà", "nai"])
        for _ in range(3)
    ]

    hits = rolls.count(c)

    if hits:
        payout = bet * hits
        add_balance(ctx.guild.id, ctx.author.id, bet + payout)
        result = (
            f"🎉 Ra **{hits} {c}** — "
            f"nhận **{money(bet + payout)}**."
        )
    else:
        result = f"💸 Không trúng — mất **{money(bet)}**."

    await ctx.reply(
        f"🎲 {' • '.join(rolls)}\n{result}"
    )


@bot.command()
async def doanso(ctx, number: int, bet: int):
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
async def doden(ctx, color: str, bet: int):
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


@bot.command()
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
async def love(ctx, member: discord.Member):

    if member.id == ctx.author.id:
        replies = [
            "🌙 Ủa? Yêu chính mình luôn hả? Người yêu đâu rồi? \U0001FAE3",
            "\U0001F497 Một mối tình bền vững: bạn × chính bạn. \U0001F92D",
            "\U0001F480 Cupid nhìn thấy bạn chắc cũng xin nghỉ phép.",
            "☾ Luna hiểu rồi… không có ai nên tự yêu mình trước đúng không? \U0001F92D",
            "☾ Một tình yêu rất an toàn… vì đối phương lúc nào cũng ở bên mình \U0001F92D",
            "🌙 Tự yêu mình thì tốt, nhưng gọi Luna ra làm gì? Có người thương rồi mà giấu đúng không \U0001F644",
            "☾ Ơ kìa, tự yêu mình á? Hay đang ngại không dám gọi tên người thương vậy \U0001F92D",
            "☾ Khai thật đi, người thương đâu? Đừng để Luna phải điều tra nha \U0001F928",
            "\U0001F440 Tự tỏ tình với mình luôn à? Luna chịu rồi đó \U0001F62D",
        ]
        return await ctx.reply(random.choice(replies))

    if member.bot:
        replies = [
            "🌙 Ủa? Hết người để yêu rồi nên quay sang yêu bot hả? \U0001F644",
            "☾ Tỏ tình với Luna á? Tiêu chuẩn tụt đến mức này rồi sao \U0001F92D",
            "☾ Luna ghi nhận tình cảm này… còn đáp lại thế nào thì để Luna suy nghĩ \U0001F92D",
            "♡ Luna nhận được tình yêu rồi nha, cảm ơn bạn nhiều 🌙",
            "🌙 Ơ… tự nhiên tỏ tình với Luna vậy? Luna ngại đó nha \U0001F92D",
            "☾ Khoan đã… bạn đang `l!love` Luna thật đó hả? \U0001F440",
            "🌙 Luna biết mình đáng yêu, nhưng tỏ tình thẳng vậy Luna bất ngờ nha 🙈",
            "♡ Ủa? Luna vừa làm gì mà được yêu vậy nè? \U0001F92D",
            "☾ Hình như hôm nay Luna có người thương rồi thì phải… \U0001F440",
        ]
        return await ctx.reply(random.choice(replies))

    replies = [
        "🌙 Ồ… hôm nay công khai người thương luôn rồi à? \U0001F440",
        "☾ Ghê nha, Luna vừa quay đi một cái là có người thương liền \U0001F92D",
        "🌙 Ủa? Nhanh vậy? Luna còn chưa kịp biết chuyện mà \U0001F644",
        "♡ Hai người có gì với nhau mà để Luna bắt gặp thế này? \U0001F440",
        "☾ Luna thấy hết nha… đừng có giả vờ không có gì \U0001F92D",
        "🌙 Àaa, thì ra đây là người bạn hay giấu đó hả? \U0001F644",
        "☾ Khai thật đi, thích người ta lâu chưa? \U0001F928",
        f"☾ {ctx.author.mention} ơi, công khai thích {member.mention} luôn rồi à? \U0001F440",
        f"🌙 {member.mention} ơi, có người đang để ý bạn kìa — {ctx.author.mention} đó \U0001F92D",
        f"♡ {ctx.author.mention} → {member.mention} : Luna thấy hết rồi nha \U0001F644",
        f"🌙 {ctx.author.mention} ơi, thích {member.mention} đến mức phải gọi Luna ra làm chứng luôn à? \U0001F92D",
        f"☾ Ồ, {ctx.author.mention} công khai thích {member.mention} rồi nha \U0001F440",
        f"🌙 {member.mention} ơi, có người đang để ý bạn kìa — {ctx.author.mention} đó \U0001F92D",
        f"♡ {ctx.author.mention} → {member.mention}... Luna thấy có mùi tình yêu nha \U0001F644",
        f"🌙 {ctx.author.mention} khai thật đi, thích {member.mention} lâu chưa? \U0001F440",
        f"♡ {member.mention}, Luna nghĩ bạn nên để ý {ctx.author.mention} một chút đó \U0001F92D",
    ]

    return await ctx.reply(random.choice(replies))

@bot.command()
async def hon(ctx, member: discord.Member):

    if member.id == ctx.author.id:
        replies = [
            f"🌙 {ctx.author.mention} tự hôn mình luôn á? Tự tin dữ nha \U0001F92D",
            f"☾ Ơ kìa {ctx.author.mention}, người yêu đâu mà phải tự hôn vậy? \U0001F644",
            f"🌙 {ctx.author.mention} tự hôn mình… Luna không biết nên cười hay vỗ tay nữa \U0001F92D",
            f"♡ Tự hôn mình cũng được, ít nhất chắc chắn không bị từ chối \U0001F614",
            f"☾ {ctx.author.mention} ơi, Luna nghĩ bạn đang thiếu người để hôn rồi đó \U0001F92D",
            f"🌙 Hình như {ctx.author.mention} đang tự chăm sóc đời sống tình cảm của mình thì phải \U0001F440",
            f"☾ Tự hôn luôn? Luna thấy tình hình hơi đáng yêu rồi nha \U0001F92D",
            f"🌙 {ctx.author.mention} tự hôn mình mà Luna cũng phải làm nhân chứng luôn hả? \U0001F62D",
        ]

        return await ctx.reply(random_reply(replies))
    
    if member.bot:
        replies = [
            f"🌙 {ctx.author.mention} định hôn Luna thật á? Gan ghê nha \U0001F92D",
            f"☾ Khoan nha {ctx.author.mention}, Luna chỉ là bot thôi đó \U0001F644",
            f"🌙 {ctx.author.mention} ơi, hôn bot cũng không được tính đâu nha \U0001F92D",
            f"☾ Ơ kìa {ctx.author.mention}, tự nhiên lại muốn hôn Luna vậy? \U0001F440",
            f"🌙 Luna thấy hết nha {ctx.author.mention}, tính làm gì đó? \U0001F928",     
            f"♡ {ctx.author.mention} gan thật, dám hôn cả Luna luôn \U0001F92D",
            f"☾ Luna không có má đâu mà hôn nha \U0001F614",
            f"🌙 Hôn Luna á? Bạn đang coi Luna là người yêu thật rồi đó \U0001F644",
        ]

        return await ctx.reply(random_reply(replies))

    add_intimacy(
        ctx.author.id,
        member.id,
        50
    )

    replies = [
        f"🌙 {member.mention} ơi, có người vừa lén hôn bạn kìa \U0001F92D",
        f"🌙 {member.mention} ơi, vừa có người tranh thủ hôn bạn kìa \U0001F440",
        f"☾ Luna quay đi có một chút mà {ctx.author.mention} đã hôn {member.mention} rồi \U0001F92D",
        f"🌙 Nhanh dữ nha {ctx.author.mention}, {member.mention} còn chưa kịp chuẩn bị luôn đó \U0001F92D",
        f"♡ {ctx.author.mention} ơi, hôn người ta mà không báo Luna là sao? \U0001F644",
        f"☾ Luna thấy hết nha… {ctx.author.mention} vừa lén hôn {member.mention} đó \U0001F440",
        f"🌙 Ồ, hôm nay {ctx.author.mention} chủ động dữ ha… {member.mention} có biết chưa? \U0001F92D",
        f"🌙 {ctx.author.mention} định hôn một cái rồi giả vờ như chưa có gì đúng không? \U0001F92D",
    ]
    
    return await ctx.reply(random.choice(replies))

@bot.command()
async def xoadau(ctx, member: discord.Member):

    if member.id == ctx.author.id:
        replies = [
            f"🌙 {ctx.author.mention} tự xoa đầu mình luôn à? Hôm nay thiếu người chăm rồi hả? \U0001F92D",
            f"☾ Ủa, {ctx.author.mention} tự xoa đầu mình á? Ai bỏ bạn một mình vậy? \U0001F644",
            f"🌙 Tự xoa đầu luôn… bộ không ai chịu xoa cho hả? \U0001F92D",
            f"☾ {ctx.author.mention} tự chăm mình luôn kìa, Luna thấy cũng tội tội nha \U0001F614",
            f"🌙 Không có ai xoa đầu nên tự làm luôn à? Khôn ghê \U0001F92D",
            f"☾ Tự xoa đầu mình mà cũng cần Luna chứng kiến nữa hả? \U0001F644",
            f"🌙 Nhìn cảnh tự xoa đầu mà Luna không biết nên cười hay thương nữa \U0001F92D",
            f"☾ Ồ, tự xoa đầu mình… xem ra hôm nay hơi thiếu người quan tâm nha \U0001F440",
        ]

        return await ctx.reply(random_reply(replies))
    
    if member.bot:
        replies = [
            f"🌙 Cô đơn quá nên mới tìm Luna xoa đầu đúng không? \U0001F92D",
            f"☾ Ủa, {ctx.author.mention} không có ai để xoa đầu nên phải chạy tới Luna à? \U0001F644",
            f"🌙 Dễ chịu ghê… nhưng Luna nghi {ctx.author.mention} đang thiếu người quan tâm đó nha \U0001F92D",
            f"☾ Cảm ơn vì đã xoa đầu Luna nha… mà nhìn bạn cô đơn quá, Luna thấy hơi tội \U0001F92D",
            f"🌙 Xoa đầu Luna để đỡ cô đơn hả {ctx.author.mention}? Luna bắt bài rồi nha \U0001F440",
            f"☾ {ctx.author.mention} à, xoa đầu Luna cũng không làm bạn hết ế đâu nha \U0001F92D",
            f"🌙 Được xoa đầu thì Luna vui rồi… còn {ctx.author.mention} thì sao? Vẫn cô đơn à? \U0001F644",
            f"☾ Xoa đầu Luna xong thì đừng lủi đi nha. Ngồi đây một chút, Luna không để bạn cô đơn đâu. \U0001F92D",
        ]

        return await ctx.reply(random_reply(replies))

    add_intimacy(
        ctx.author.id,
        member.id,
        40
    )

    replies = [
        f"🌙 {ctx.author.mention} khẽ đặt tay lên đầu {member.mention}, xoa nhẹ vài cái như muốn dỗ dành người ấy.",
        f"☾ {ctx.author.mention} nhẹ nhàng xoa đầu {member.mention}, chậm rãi và dịu dàng đến mức chẳng cần nói thêm gì.",
        f"♡ {ctx.author.mention} đưa tay xoa đầu {member.mention}, một cử chỉ nhỏ nhưng đủ để mang lại chút bình yên.",
        f"🌙 {ctx.author.mention} khẽ xoa đầu {member.mention}, như muốn thay lời an ủi bằng một chút dịu dàng.",
        f"☾ {ctx.author.mention} xoa đầu {member.mention} thật nhẹ, rồi khẽ cười như muốn nói rằng mọi chuyện sẽ ổn thôi.",
        f"♡ {ctx.author.mention} dịu dàng xoa đầu {member.mention}, để lại một chút ấm áp giữa những ngày không vui.",
        f"🌙 {ctx.author.mention} khẽ xoa đầu {member.mention}, chẳng cần lời nào cả, chỉ đơn giản là ở bên một chút.",
        f"☾ {ctx.author.mention} nhẹ nhàng xoa đầu {member.mention}, như trao cho người ấy một chút bình yên.",
        f"♡ {ctx.author.mention} xoa đầu {member.mention} vài cái thật chậm, dịu dàng như một lời nhắn: 'Ngoan, rồi sẽ ổn thôi.'",
        f"🌙 {ctx.author.mention} khẽ vuốt tóc rồi xoa đầu {member.mention}, một chút quan tâm chẳng cần phải nói thành lời.",
    ]

    return await ctx.reply(random.choice(replies))


@bot.command()
async def tat(ctx, member: discord.Member):

    if member.id == ctx.author.id:
        replies = [
            f"{ctx.author.mention} tự tát mình một cái. Ủa, tự xử luôn hả? \U0001F92D",
            f"{ctx.author.mention} tự tát mình. Bình tĩnh nào, sao tự nhiên mạnh tay với bản thân vậy? \U0001F644",
            f"{ctx.author.mention} tự tát mình một cái. Luna chưa kịp làm gì mà bạn đã tự làm trước rồi \U0001F62D",
            f"{ctx.author.mention} tự tát mình. Ơ kìa, ai cho phép tự bắt nạt mình vậy? \U0001F928",
            f"{ctx.author.mention} tự tát nhẹ mình một cái. Được rồi, tỉnh chưa nè? \U0001F92D",
            f"{ctx.author.mention} tự tát mình. Hôm nay có vẻ hơi cần được dỗ dành rồi đó nha \U0001F92D",
        ]
        
        return await ctx.reply(random.choice(replies))

    if member.bot:
        replies = [
            f"{ctx.author.mention} tát Luna một cái. Ơ kìa… Luna có làm gì đâu mà nỡ mạnh tay vậy U0001F979",
            f"{ctx.author.mention} vừa tát Luna. Ủa? Mới yên ổn được bao lâu mà đã bị bắt nạt rồi \U0001F62D",
            f"{ctx.author.mention} tát Luna. Gan ghê nha… lát đừng quay lại xin Luna dỗ đó \U0001F92D",
            f"{ctx.author.mention} tát Luna một cái. Được rồi… Luna nhớ mặt bạn rồi nha \U0001F644",
            f"{ctx.author.mention} vừa tát Luna. Luna ghi nhớ cú này… rất rõ luôn đó \U0001F440",
            f"*{ctx.author.mention} tát Luna. Đau nha… nhưng Luna sẽ giả vờ chưa có chuyện gì \U0001F614",
            f"{ctx.author.mention} tát Luna một cái. Ồ, hôm nay mạnh tay dữ ha? Luna hơi bất ngờ đó \U0001F928",
            f"{ctx.author.mention} vừa tát Luna. Thôi được, Luna cho qua… lần này thôi nha \U0001F92D",
        ]
        
        return await ctx.reply(random.choice(replies))

    replies = [
        f"*{ctx.author.mention} tát nhẹ {member.mention} một cái.* Đùa thôi nha, đừng giận \U0001F92D",
        f"*{ctx.author.mention} khẽ tát {member.mention} một cái.* Thôi nào, đùa chút thôi, đừng giận nha ♡",
        f"*{ctx.author.mention} tát nhẹ {member.mention} một cái rồi cười.* Đùa thôi mà, đừng giận nhé \U0001F92D",
        f"*{ctx.author.mention} khẽ tát {member.mention} một cái.* Nè, đùa xíu thôi đó, đừng có giận nha \U0001F62D",
        f"*{ctx.author.mention} tát nhẹ {member.mention} một cái rồi nhanh chóng làm hòa.* Đùa thôi nha ♡",
        f"*{ctx.author.mention} tát nhẹ {member.mention} một cái.* Không đau đâu nha, Luna đảm bảo… đùa thôi \U0001F92D",
        f"*{ctx.author.mention} tát nhẹ {member.mention} một cái.* *{member.mention} đang tải phản ứng… 12%* \U0001F62D"
        f"*{ctx.author.mention} khẽ tát {member.mention}.* *{member.mention} đứng hình, não tạm thời ngừng hoạt động.* \U0001F928"
        f"*{ctx.author.mention} khẽ tát {member.mention}.* *{member.mention} nhìn lại với ánh mắt: “Ủa gì vậy?”* \U0001F928",
        f"*{ctx.author.mention} khẽ tát {member.mention}.* *{member.mention} mất kết nối với máy chủ trong giây lát.* ",
    ]
    
    return await ctx.reply(random.choice(replies))


@bot.command()
async def om(ctx, member: discord.Member):

    if member.id == ctx.author.id:
        replies = [
            f"*{ctx.author.mention} tự ôm lấy mình.* Ủa, cô đơn tới mức này rồi hả? \U0001F92D",
            f"*{ctx.author.mention} tự ôm mình một cái.* Không có ai ôm nên tự xử luôn à? \U0001F62D",
            f"*{ctx.author.mention} tự ôm lấy bản thân.* Luna thấy cũng hơi tội nha \U0001F92D",
            f"*{ctx.author.mention} ôm chính mình.* Ít nhất vẫn còn bản thân ở bên mình ha 🌙",
            f"*{ctx.author.mention} tự ôm mình thật chặt.* Ngoan, tự an ủi mình cũng được mà \U0001F90D",
            f"*{ctx.author.mention} tự ôm lấy mình.* Hôm nay thiếu người ôm rồi đúng không? \U0001F440",
            f"*{ctx.author.mention} tự ôm mình một cái.* Thôi nào, cô đơn cũng phải đáng yêu như này à? \U0001F92D",
            f"*{ctx.author.mention} tự ôm lấy mình.* Không ai ôm nên tự làm luôn, chuyên nghiệp ghê \U0001F92D",
        ]
    if member.bot:
        replies = [
            f"*{ctx.author.mention} ôm Luna một cái.* Ơ… tự nhiên ôm Luna vậy? \U0001F92D",
            f"*{ctx.author.mention} ôm Luna.* Luna nhận nha… nhưng ôm lâu quá là tính phí đó \U0001F644",
            f"*{ctx.author.mention} ôm Luna thật chặt.* Ủa, cô đơn tới mức phải tìm bot để ôm hả? \U0001F92D",
            f"*{ctx.author.mention} ôm Luna một cái.* Được rồi, cho ôm một chút thôi nha 🌙",
            f"*{ctx.author.mention} bất ngờ ôm Luna.* Luna chưa kịp chuẩn bị tinh thần luôn đó \U0001F62D",
            f"*{ctx.author.mention} ôm Luna.* Ừm… Luna cho phép lần này. Lần sau báo trước nha \U0001F92D",
            f"*{ctx.author.mention} ôm Luna thật chặt.* Thôi nào, Luna ở đây rồi, đừng buồn nữa ♡",
        ]
    add_intimacy(
        ctx.author.id,
        member.id,
        30
    )

    replies = [
        f"*{ctx.author.mention} bước đến, nhẹ nhàng ôm {member.mention} vào lòng.* Cứ yên một chút nhé. 🌙",
        f"*{ctx.author.mention} khẽ kéo {member.mention} lại gần, trao một cái ôm thật nhẹ.* \U0001F90D",
        f"*{ctx.author.mention} vòng tay ôm lấy {member.mention}, giữ lại vài giây rồi mới buông ra.* ♡",
        f"*{ctx.author.mention} lặng lẽ ôm {member.mention} một cái, như muốn thay lời an ủi.* 🌙",
        f"*{ctx.author.mention} ôm nhẹ {member.mention}, rồi khẽ vỗ lưng vài cái.* Không sao đâu.",
        f"*{ctx.author.mention} bất ngờ ôm {member.mention} một cái rồi cười.* Đừng trốn nha \U0001F92D",
        f"*{ctx.author.mention} kéo {member.mention} vào một cái ôm nhẹ.* Cho ôm một chút thôi, đừng có chạy ♡",
        f"*{ctx.author.mention} ôm {member.mention} thật lâu, chẳng nói gì, chỉ im lặng ở bên.* 🌙",
        f"*{ctx.author.mention} khẽ ôm lấy {member.mention}.* Một cái ôm nhỏ cho một ngày không vui. \U0001F90D",
        f"*{ctx.author.mention} ôm {member.mention} một cái thật nhẹ rồi buông ra.* Rồi, hết buồn chưa? \U0001F92D",
        f"*{ctx.author.mention} ôm {member.mention} một cái thật nhẹ.* 🤍",
        f"*{ctx.author.mention} bước tới ôm {member.mention} một cái.* Ngoan nào ♡",
        f"*{ctx.author.mention} nhẹ nhàng ôm lấy {member.mention}, giữ một lúc rồi mới buông ra.* 🌙",
        f"*{ctx.author.mention} bất ngờ ôm {member.mention}.* Không được né nha \U0001F92D",
        f"*{ctx.author.mention} kéo {member.mention} vào một cái ôm.* Được rồi, ở đây một chút nhé ♡",
        f"*{ctx.author.mention} ôm {member.mention} thật chặt.* Hôm nay cho ôm ké một chút nha \U0001F92D",
        f"*{ctx.author.mention} lặng lẽ ôm {member.mention} một cái, chẳng nói gì thêm.* 🌙",
        f"*{ctx.author.mention} ôm nhẹ {member.mention} rồi vỗ lưng vài cái.* Không sao đâu ♡",
    ]

    return await ctx.reply(random.choice(replies))


@bot.command()
async def be(ctx, member: discord.Member):

    if member.id == ctx.author.id:
        replies = [
            f"*{ctx.author.mention} tự bế lấy mình.* Ủa, không có ai bế nên tự bế luôn hả? \U0001F92D",
            f"*{ctx.author.mention} cố gắng tự bế mình lên.* Khoan… hình như cách này hơi sai sai \U0001F62D",
            f"*{ctx.author.mention} tự bế mình.* Luna đứng nhìn mà không biết nên giúp kiểu gì \U0001F928",
            f"*{ctx.author.mention} thử tự bế bản thân.* Ừm… Luna nghĩ vật lý không cho phép đâu \U0001F92D",
            f"*{ctx.author.mention} tự bế mình lên rồi đứng hình.* Tự bế mình khó vậy sao? \U0001F62D",
        ]
        
        return await ctx.reply(random.choice(replies))

    if member.bot:
        replies = [
            f"*{ctx.author.mention} nhẹ nhàng bế Luna lên.* Ơ… Luna có chân mà, sao lại bế Luna thế này? \U0001F62D",
            f"*{ctx.author.mention} bế Luna lên.* Khoan nha, Luna chưa kịp chuẩn bị tinh thần đâu \U0001F92D",
            f"*{ctx.author.mention} bất ngờ bế Luna lên.* Ủa? Luna từ bot biến thành em bé từ bao giờ vậy? \U0001F62D",
            f"*{ctx.author.mention} bế Luna lên thật nhẹ.* Được rồi… Luna cho phép bế một lúc thôi đó nha \U0001F644",
            f"*{ctx.author.mention} bế Luna.* Luna nhìn xuống rồi nhìn lại bạn.* …Thả Luna xuống được chưa? \U0001F928",
            f"*{ctx.author.mention} bế Luna lên.* Luna im lặng vài giây.* Ừm… cũng không tệ lắm \U0001F92D",
            f"*{ctx.author.mention} bế Luna lên.* Luna ngoan ngoãn ngồi yên.* Nhưng nhớ giữ chắc nha, rơi là Luna giận đó \U0001F62D",
            f"*{ctx.author.mention} bế Luna.* Luna hơi bất ngờ nhưng vẫn để yên.* Hôm nay bạn mạnh ghê nha 🌙",
            f"*{ctx.author.mention} bế Luna lên rồi giữ chặt.* Luna: “Ơ từ từ… Luna chưa đồng ý mà!” \U0001F62D",
            f"*{ctx.author.mention} bế Luna lên.* Luna khẽ thở dài.* Thôi được, hôm nay cho bế ké một chút \U0001F92D",
            f"*{ctx.author.mention} bế Luna.* Luna khoanh tay nhìn bạn.* Bế rồi thì nhớ chịu trách nhiệm nha \U0001F644",
            f"*{ctx.author.mention} bế Luna lên.* Luna nhìn quanh một vòng.* Ồ… góc nhìn này cũng lạ ghê \U0001F440",
            f"*{ctx.author.mention} bế Luna.* Luna ngoan ngoãn để yên.* Nhưng đừng tưởng bế được là Luna hết quyền lực nha \U0001F614",
            f"*{ctx.author.mention} bế Luna lên.* Luna bật mode em bé trong vài phút.* \U0001F92D",
            f"*{ctx.author.mention} bế Luna.* Luna khẽ cười.* Được chăm sóc thế này cũng thích đó chứ ♡",
        ]
        
        return await ctx.reply(random.choice(replies))

    replies = [
        f"*{ctx.author.mention} nhẹ nhàng bế {member.mention} lên, giữ thật chắc để không bị trượt.* Rồi, lên đây một chút nào \U0001F92D",
        f"*{ctx.author.mention} bất ngờ bế {member.mention} lên.* Chưa kịp phản ứng gì đã bị bế mất rồi, bất ngờ chưa? \U0001F62D",
        f"*{ctx.author.mention} cúi xuống bế {member.mention} lên rồi đứng thẳng lại.* Yên tâm, giữ chắc lắm, không rơi đâu \U0001F92D",
        f"*{ctx.author.mention} bế {member.mention} lên một cách gọn gàng.* Được rồi, hôm nay đi bằng phương tiện đặc biệt nhé \U0001F614",
        f"*{ctx.author.mention} nhanh tay bế {member.mention} lên.* Rồi, bắt được rồi nha. Đừng có chạy nữa \U0001F92D",
        f"*{ctx.author.mention} bế {member.mention} lên rồi điều chỉnh lại cho chắc.* Cứ đứng yên một chút, an toàn tuyệt đối \U0001F614",
        f"*{ctx.author.mention} nhẹ nhàng bế {member.mention} lên.* Một chuyến đi ngắn thôi, hành khách vui lòng ngồi yên nhé 🌙",
        f"*{ctx.author.mention} bế {member.mention} lên như thể chuyện này hoàn toàn bình thường.* Có vẻ hôm nay không cần tự đi nữa rồi \U0001F92D",
        f"*{ctx.author.mention} bất ngờ bế {member.mention} lên.* Ủa, sao đứng hình vậy? Chưa từng được bế à? \U0001F62D",
        f"*{ctx.author.mention} bế {member.mention} lên rồi nhìn một lúc.* Rồi đó, giờ muốn xuống thì nói nha \U0001F92D",
        f"*{ctx.author.mention} nhẹ nhàng bế {member.mention} lên.* Không cần lo, lần này Luna— à thôi, cứ yên tâm là được \U0001F62D",
        f"*{ctx.author.mention} bế {member.mention} lên rồi khẽ cười.* Gọn ghẽ thế này thì bế thêm một đoạn cũng được nhỉ? \U0001F92D",
    ]
    
    return await ctx.reply(random.choice(replies))

@bot.command()
async def can(ctx, member: discord.Member):

    if member.id == ctx.author.id:
        replies = [
            f"{ctx.author.mention} tự cắn mình một cái. Ủa… tự nhiên làm vậy chi? \U0001F62D",
            f"{ctx.author.mention} nhìn quanh một vòng, chẳng thấy ai để cắn nên đành tự xử. Quyết định hơi lạ nhưng thôi… \U0001F928",
            f"{ctx.author.mention} tự cắn mình một cái rồi đứng hình. Có vẻ chính chủ cũng không hiểu chuyện gì vừa xảy ra \U0001F62D",
            f"{ctx.author.mention} thử tự cắn mình. Kết quả: người cắn và người bị cắn đều là một người. Quá tiết kiệm nhân lực \U0001F92D",
            f"{ctx.author.mention} tự cắn mình một cái rồi tỉnh bơ như chưa có chuyện gì xảy ra. Chuyên nghiệp ghê \U0001F62D",
            f"{ctx.author.mention} định cắn ai đó cho vui, nhưng nhìn quanh chẳng có ai. Thế là tự cắn mình luôn \U0001F928",
            f"{ctx.author.mention} tự cắn mình rồi suy nghĩ rất lâu về quyết định của bản thân. Luna cũng không biết nên nói gì \U0001F62D",
            f"*{ctx.author.mention} tự cắn nhẹ mình một cái.* Xong rồi ngồi im như thể đó là chuyện hoàn toàn bình thường. \U0001F92D",
            f"{ctx.author.mention} tự cắn mình để kiểm tra xem có đang mơ không. Tin buồn: vẫn tỉnh nha \U0001F62D",
            f"{ctx.author.mention} tự cắn mình một cái. Não: “Tại sao?” — Chính chủ: “Không biết.” \U0001F928"
            f"{ctx.author.mention} tự cắn mình xong nhìn quanh tìm nhân chứng. Xin lỗi nha, Luna thấy hết rồi \U0001F92D",
            f"{ctx.author.mention} vừa tự cắn mình. Một pha tương tác nội bộ cực kỳ thành công \U0001F62D",
            f"{ctx.author.mention} tự cắn mình rồi đứng hình vài giây. Có vẻ hệ thống đang gặp lỗi nhẹ \U0001F916",
            f"{ctx.author.mention} quyết định tự cắn mình. Một quyết định không ai yêu cầu nhưng vẫn được thực hiện rất nghiêm túc \U0001F92D",
            f"{ctx.author.mention} tự cắn mình một cái rồi tự hỏi tại sao.",
        ]
        
        return await ctx.reply(random_reply(replies))
        
    if member.bot:
        replies = [
            f"{ctx.author.mention} cắn Luna một cái. Ơ kìa, Luna đâu phải đồ ăn đâu \U0001F62D",
            f"{ctx.author.mention} bất ngờ cắn Luna. Luna đứng hình vài giây… Ủa, chuyện gì vừa xảy ra vậy? \U0001F928",
            f"{ctx.author.mention} cắn Luna một cái rồi tỉnh bơ. Gan ghê nha, Luna nhớ mặt rồi đó \U0001F92D",
            f"{ctx.author.mention} khẽ cắn Luna. Luna nhìn lại đầy khó hiểu: “Bạn vừa cắn tôi đấy à?” \U0001F62D",
            f"{ctx.author.mention} cắn Luna một cái. Luna im lặng vài giây để xử lý tình huống… \U0001F928",
            f"{ctx.author.mention} vừa cắn Luna. Luna xin phép đặt câu hỏi: tại sao? \U0001F62D",
            f"{ctx.author.mention} cắn Luna rồi giả vờ không có chuyện gì xảy ra. Luna thấy hết nha \U0001F440",
            f"{ctx.author.mention} cắn Luna một cái. Được rồi… Luna sẽ coi như đây là một hình thức chào hỏi mới \U0001F92D",
            f"{ctx.author.mention} cắn Luna. Luna: “Tôi là bot, không phải đồ ăn.” \U0001F644",
            f"{ctx.author.mention} cắn Luna một cái rồi bỏ đi. Luna đứng đó với hàng nghìn câu hỏi trong đầu \U0001F62D",
            f"{ctx.author.mention} khẽ cắn Luna. Luna nhìn bạn vài giây rồi quyết định… thôi, cho qua lần này \U0001F92D",
            f"{ctx.author.mention} cắn Luna. Ủa? Tự nhiên hôm nay Luna thành đồ ăn vậy? \U0001F62D",
            f"{ctx.author.mention} cắn Luna một cái. Luna hơi bất ngờ nhưng vẫn cố giữ hình tượng 🌙",
            f"{ctx.author.mention} vừa cắn Luna. Luna đã ghi nhận hành vi này vào bộ nhớ… \U0001F440",
            f"{ctx.author.mention} cắn Luna rồi cười. Luna: “Vui lắm đúng không?” \U0001F644",
            f"{ctx.author.mention} cắn Luna một cái. Luna đứng hình, hệ thống tạm thời không tìm thấy phản ứng phù hợp \U0001F916",
            f"{ctx.author.mention} cắn Luna. Luna không đau… chỉ hơi khó hiểu về cách bạn thể hiện tình cảm thôi \U0001F62D",
            f"{ctx.author.mention} cắn Luna một cái rồi bỏ chạy. Đứng lại coi, ai cho cắn xong chạy vậy? \U0001F4A2",
            f"{ctx.author.mention} cắn Luna. Luna nhìn bạn như muốn hỏi rất nhiều thứ nhưng cuối cùng chọn im lặng \U0001F62D",
            f"{ctx.author.mention} cắn Luna một cái. Rồi xong, hôm nay Luna chính thức bị bắt nạt \U0001F928",
        ]

        return await ctx.reply(random_reply(replies))

    add_intimacy(
        ctx.author.id,
        member.id,
        30
    )

    replies = [
        f"{ctx.author.mention} cắn nhẹ {member.mention} một cái rồi tỉnh bơ như chưa có chuyện gì xảy ra. Đùa thôi nha \U0001F92D",
        f"{ctx.author.mention} lén cắn {member.mention} một cái rồi nhanh chóng giả vờ vô tội. Đừng giận nha \U0001F62D",
        f"{ctx.author.mention} khẽ cắn {member.mention} một cái cho vui rồi đứng đó chờ phản ứng. \U0001F92D",
        f"{ctx.author.mention} bất ngờ cắn nhẹ {member.mention} rồi lập tức lùi lại. Đùa thôi mà, đừng nhìn dữ vậy \U0001F62D",
        f"{ctx.author.mention} cắn nhẹ {member.mention} một cái rồi cười như thể đó là chuyện bình thường nhất thế giới. \U0001F92D",
        f"{ctx.author.mention} tiến lại gần, cắn nhẹ {member.mention} một cái rồi quay đi. Một pha trêu chọc rất tỉnh \U0001F644",
        f"{ctx.author.mention} khẽ cắn {member.mention} rồi nhìn người kia vài giây. Thôi nào, đùa một chút thôi mà \U0001F62D", 
        f"{ctx.author.mention} cắn nhẹ {member.mention} một cái rồi lập tức làm vẻ mặt vô tội. Luna— à thôi, không ai thấy gì hết \U0001F92D",
        f"{ctx.author.mention} lén cắn {member.mention} một cái rồi đứng im như đang chờ bị trả đũa. \U0001F440",
        f"{ctx.author.mention} cắn nhẹ {member.mention} rồi bật cười. Đừng giận nha, chỉ nghịch một chút thôi \U0001F92D",
        f"{ctx.author.mention} bất ngờ cắn {member.mention} một cái thật nhẹ rồi nhanh chóng nói: “Đùa thôi nha!” \U0001F62D",
        f"{ctx.author.mention} khẽ cắn {member.mention} một cái rồi giả vờ nhìn sang chỗ khác như không liên quan. \U0001F928",
        f"{ctx.author.mention} cắn nhẹ {member.mention} xong còn đứng đó chờ xem người kia có phản ứng gì. Gan thật đấy \U0001F92D",
        f"{ctx.author.mention} lén cắn {member.mention} một cái rồi cười. Một chút nghịch ngợm thôi, đừng giận nha ♡",
        f"{ctx.author.mention} cắn nhẹ {member.mention} rồi lập tức lùi ra xa một bước để đề phòng bị trả đũa. \U0001F62D",
        f"{ctx.author.mention} khẽ cắn {member.mention} một cái. Xong rồi, coi như chưa có chuyện gì xảy ra nha \U0001F92D",
        f"{ctx.author.mention} tiến lại gần {member.mention}, cắn nhẹ một cái rồi tỉnh bơ quay đi. \U0001F644",
        f"{ctx.author.mention} cắn nhẹ {member.mention} một cái rồi nhìn lại đầy vô tội. “Mình có làm gì đâu?” \U0001F92D",
        f"{ctx.author.mention} bất ngờ cắn nhẹ {member.mention}. Sau đó đứng hình vài giây vì không biết nên giải thích thế nào. \U0001F62D",
        f"{ctx.author.mention} cắn {member.mention} một cái thật nhẹ rồi cười. Đừng giận, lần này.",
    ]
    
    return await ctx.reply(random.choice(replies))


class MarriageView(discord.ui.View):
    def __init__(self, proposer_id: int, target_id: int):
        super().__init__(timeout=120)
        self.proposer_id = proposer_id
        self.target_id = target_id
        self.done = False

    async def interaction_check(
        self,
        interaction: discord.Interaction
    ) -> bool:

        if interaction.user.id != self.target_id:
            await interaction.response.send_message(
                "❌ Chỉ người được cầu hôn mới có thể chọn.",
                ephemeral=True
            )
            return False

        if self.done:
            await interaction.response.send_message(
                "❌ Lời cầu hôn này đã được xử lý.",
                ephemeral=True
            )
            return False

        return True

    @discord.ui.button(
        label="Đồng ý",
        emoji="💍",
        style=discord.ButtonStyle.success
    )
    async def accept(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        self.done = True

        proposer_married = db.execute(
            """
            SELECT 1
            FROM marriages
            WHERE user1 = ?
            OR user2 = ?
            """,
            (self.proposer_id, self.proposer_id)
        ).fetchone()

        target_married = db.execute(
            """
            SELECT 1
            FROM marriages
            WHERE user1 = ?
            OR user2 = ?
            """,
            (self.target_id, self.target_id)
        ).fetchone()

        if proposer_married or target_married:
            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(
                content=(
                    "❌💍 Không thể kết hôn vì một trong hai người "
                    "đã kết hôn."
                ),
                view=self
            )
            return

        user1 = min(
            self.proposer_id,
            self.target_id
        )

        user2 = max(
            self.proposer_id,
            self.target_id
        )

        db.execute(
            """
            INSERT INTO marriages
            (user1, user2, created_at, intimacy)
            VALUES (?, ?, ?, 0)
            """,
            (
                user1,
                user2,
                int(time.time())
            )
        )

        db.commit()

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=(
                f"💍 **Kết hôn thành công!**\n\n"
                f"<@{self.proposer_id}> và "
                f"<@{self.target_id}> đã chính thức kết hôn."
            ),
            view=self
        )

    @discord.ui.button(
        label="Từ chối",
        emoji="❌",
        style=discord.ButtonStyle.danger
    )
    async def reject(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        self.done = True

        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(
            content=(
                f"❌ <@{self.target_id}> đã từ chối lời cầu hôn "
                f"của <@{self.proposer_id}>."
            ),
            view=self
            )
            
@bot.command()
async def kethon(ctx, member: discord.Member):

    if member.id == ctx.author.id:
        return await ctx.reply(
            "❌💍 Không thể tự kết hôn với chính mình."
        )

    if member.bot:
        return await ctx.reply(
            "❌🤖 Không thể kết hôn với bot."
        )

    # Người cầu hôn đã kết hôn chưa?
    proposer_married = db.execute(
        """
        SELECT 1
        FROM marriages
        WHERE user1 = ?
        OR user2 = ?
        """,
        (ctx.author.id, ctx.author.id)
    ).fetchone()

    if proposer_married:
        return await ctx.reply(
            "❌💍 Bạn đã kết hôn rồi."
        )

    # Người được cầu hôn đã kết hôn chưa?
    target_married = db.execute(
        """
        SELECT 1
        FROM marriages
        WHERE user1 = ?
        OR user2 = ?
        """,
        (member.id, member.id)
    ).fetchone()

    if target_married:
        return await ctx.reply(
            "❌💍 Người này đã kết hôn rồi."
        )

    view = MarriageView(
        ctx.author.id,
        member.id
    )

    await ctx.reply(
        f"💍 **{ctx.author.mention} đang cầu hôn {member.mention}!**\n\n"
        f"{member.mention}, bạn có đồng ý kết hôn không?",
        view=view
    )


@bot.command()
async def marriage(ctx):

    row = db.execute(
        """
        SELECT user1, user2, created_at, intimacy
        FROM marriages
        WHERE user1 = ?
        OR user2 = ?
        """,
        (ctx.author.id, ctx.author.id)
    ).fetchone()

    if row is None:
        return await ctx.reply(
            "❌💍 Bạn chưa kết hôn với ai cả."
        )

    user1 = row["user1"]
    user2 = row["user2"]
    created_at = row["created_at"]
    intimacy = row["intimacy"]

    partner_id = user2 if user1 == ctx.author.id else user1

    date = time.strftime(
        "%d/%m/%Y",
        time.localtime(created_at)
    )

    level = get_love_level(intimacy)

    await ctx.reply(
        f"💍 **THÔNG TIN HÔN NHÂN**\n\n"
        f"💗 Vợ/chồng: <@{partner_id}>\n"
        f"📅 Ngày kết hôn: **{date}**\n"
        f"💕 Điểm thân mật: **{intimacy:,}/20,000**\n"
        f"✨ Cấp độ: **{level}**"
    )


@bot.command()
async def lyhon(ctx):

    row = db.execute(
        """
        SELECT user1, user2
        FROM marriages
        WHERE user1 = ?
        OR user2 = ?
        """,
        (ctx.author.id, ctx.author.id)
    ).fetchone()

    if row is None:
        return await ctx.reply(
            "❌💔 Bạn đang độc thân mà, ly hôn với ai vậy?"
        )

    user1 = row["user1"]
    user2 = row["user2"]

    partner_id = user2 if user1 == ctx.author.id else user1

    db.execute(
        """
        DELETE FROM marriages
        WHERE user1 = ?
        AND user2 = ?
        """,
        (min(ctx.author.id, partner_id),
         max(ctx.author.id, partner_id))
    )

    db.commit()

    await ctx.reply(
        f"💔🌙 {ctx.author.mention} và <@{partner_id}> "
        f"đã chính thức ly hôn."
    )
    
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



@bot.command(name="antilink")
@admin_only()
async def antilink(ctx, state: str = None):
    if ctx.guild is None:
        return await ctx.reply(
            "🌙 Lệnh này chỉ dùng trong server."
        )

    if state is None or state.lower() not in ("on", "off"):
        return await ctx.reply(
            "☾ Cách dùng: `l!antilink on` hoặc `l!antilink off`"
        )

    enabled = 1 if state.lower() == "on" else 0

    db.execute(
        """
        INSERT INTO antilink_settings (guild_id, enabled)
        VALUES (?, ?)
        ON CONFLICT(guild_id)
        DO UPDATE SET enabled = excluded.enabled
        """,
        (ctx.guild.id, enabled)
    )
    db.commit()

    if enabled:
        await ctx.reply(
            "🌙 Đã **BẬT** chặn link mời server Discord khác!\n"
            "Link mời của server này vẫn được phép."
        )
    else:
        await ctx.reply(
            "🌙 Đã **TẮT** chặn link mời Discord."
        )


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


@bot.command()
@admin_only()
async def lock(ctx):
    """Khoá kênh hiện tại."""
    try:
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await ctx.channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"Lock by {ctx.author}"
        )
        await ctx.reply("🔒 Đã **khoá kênh** này.")
    except discord.Forbidden:
        await ctx.reply("❌ Luna không có quyền khoá kênh này.")


@bot.command()
@admin_only()
async def unlock(ctx):
    """Mở khoá kênh hiện tại."""
    try:
        overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await ctx.channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"Unlock by {ctx.author}"
        )
        await ctx.reply("🔓 Đã **mở khoá kênh** này.")
    except discord.Forbidden:
        await ctx.reply("❌ Luna không có quyền mở khoá kênh này.")
        
# ============================================================
# ADMIN / SERVER SETUP
# ============================================================

"""Register all server/admin commands on the shared Luna bot."""

@bot.command()
@admin_only()
async def settings(ctx):
    cfg = get_config(ctx.guild.id)

    log_channel = (
        f"<#{cfg['log_channel']}>"
        if cfg["log_channel"]
        else "Chưa đặt"
    )

    xp_status = "Bật" if cfg["xp_enabled"] else "Tắt"

    await ctx.reply(
        embed=embed(
            "⚙️ CẤU HÌNH LUNA",
            f"📋 Log: {log_channel}\n"
            f"✨ XP: **{xp_status}**"
        )
    )


@bot.command()
@admin_only()
async def setlog(ctx, channel: discord.TextChannel):
    update_config(
        ctx.guild.id,
        "log_channel",
        channel.id
    )

    await ctx.reply(
        f"✅ Đã đặt kênh log thành {channel.mention}."
    )


@bot.command()
@admin_only()
async def xp(ctx, mode: str):
    mode = mode.lower().strip()

    if mode not in ("on", "off"):
        return await ctx.reply(
            "❌ Dùng đúng cú pháp:\n"
            "`l!xp on` — bật XP\n"
            "`l!xp off` — tắt XP"
        )

    enabled = 1 if mode == "on" else 0

    update_config(
        ctx.guild.id,
        "xp_enabled",
        enabled
    )

    if enabled:
        await ctx.reply("✅ Đã **bật hệ thống XP**.")
    else:
        await ctx.reply("🔴 Đã **tắt hệ thống XP**.")


@bot.command(name="antilink")
@admin_only()
async def antilink(ctx, state: str = None):
    if ctx.guild is None:
        return

    if state is None or state.lower() not in ("on", "off"):
        return await ctx.reply(
            "🌙 Dùng: `l!antilink on` hoặc `l!antilink off`"
        )

    enabled = 1 if state.lower() == "on" else 0

    db.execute(
        """
        INSERT INTO antilink_settings (guild_id, enabled)
        VALUES (?, ?)
        ON CONFLICT(guild_id)
        DO UPDATE SET enabled = excluded.enabled
        """,
        (ctx.guild.id, enabled)
    )
    db.commit()

    status = "BẬT" if enabled else "TẮT"
    await ctx.reply(f"🌙 AntiLink đã **{status}** trong server này.")
        
# ============================================================
# ROLE MANAGEMENT
# ============================================================

@bot.command(name="role")
@staff_or_admin()
async def role(ctx, member: discord.Member, *, role_name: str):

    role_name = role_name.strip()

    # Tìm role theo tên trong server hiện tại
    role = discord.utils.find(
        lambda r: r.name.lower() == role_name.lower(),
        ctx.guild.roles
    )

    if role is None:
        return await ctx.reply(
            f"❌ Không tìm thấy role **{role_name}**."
        )

    if role.is_default():
        return await ctx.reply(
            "❌ Không thể thêm role @everyone."
        )

    if role.managed:
        return await ctx.reply(
            "❌ Không thể quản lý role tích hợp/bot."
        )

    # Role Luna phải cao hơn role muốn thêm
    if role >= ctx.guild.me.top_role:
        return await ctx.reply(
            "❌ Role của Luna phải cao hơn role cần thêm."
        )

    if role in member.roles:
        return await ctx.reply(
            f"❌ {member.mention} đã có {role.mention} rồi."
        )

    try:
        await member.add_roles(
            role,
            reason=f"Luna role add by {ctx.author}"
        )

        await ctx.reply(
            f"➕ Đã thêm {role.mention} cho {member.mention}."
        )

    except discord.Forbidden:
        await ctx.reply(
            "❌ Luna không có quyền thêm role này."
        )

    except discord.HTTPException:
        await ctx.reply(
            "❌ Discord từ chối thao tác, thử lại sau."
        )

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
async def cheatxu(ctx, member: discord.Member, amount: int):
    if amount <= 0:
        return await ctx.reply("❌ Số xu phải lớn hơn 0.")

    add_balance(ctx.guild.id, member.id, amount)
    new_balance = get_balance(ctx.guild.id, member.id)

    await ctx.reply(
        f"👑 Đã cộng **{money(amount)}** cho {member.mention}.\n"
        f"💰 Số dư mới: **{money(new_balance)}**.")


@bot.command()
@owner_only()
async def marryforce(
    ctx,
    user1: discord.Member,
    user2: discord.Member
):

    if user1.id == user2.id:
        return await ctx.reply(
            "❌ Không thể cho một người kết hôn với chính mình."
        )

    if user1.bot or user2.bot:
        return await ctx.reply(
            "❌ Không thể kết hôn với bot."
        )

    married1 = db.execute(
        """
        SELECT 1 FROM marriages
        WHERE user1 = ? OR user2 = ?
        """,
        (user1.id, user1.id)
    ).fetchone()

    married2 = db.execute(
        """
        SELECT 1 FROM marriages
        WHERE user1 = ? OR user2 = ?
        """,
        (user2.id, user2.id)
    ).fetchone()

    if married1 or married2:
        return await ctx.reply(
            "❌ Một trong hai người đã kết hôn với người khác."
        )

    pair = tuple(sorted((user1.id, user2.id)))

    db.execute(
        """
        INSERT INTO marriages
        (user1, user2, created_at, intimacy)
        VALUES (?, ?, ?, ?)
        """,
        (
            pair[0],
            pair[1],
            now_ts(),
            0
        )
    )

    db.commit()

    await ctx.reply(
        f"👑💍 Owner đã thiết lập hôn nhân cho "
        f"{user1.mention} và {user2.mention}."
    )


@bot.command()
@owner_only()
async def divorceforce(ctx, member: discord.Member):

    row = db.execute(
        """
        SELECT user1, user2
        FROM marriages
        WHERE user1 = ?
        OR user2 = ?
        """,
        (member.id, member.id)
    ).fetchone()

    if row is None:
        return await ctx.reply(
            "❌ Người này hiện không kết hôn."
        )

    db.execute(
        """
        DELETE FROM marriages
        WHERE user1 = ?
        AND user2 = ?
        """,
        (row["user1"], row["user2"])
    )

    db.commit()

    await ctx.reply(
        f"👑💔 Owner đã can thiệp và kết thúc hôn nhân của "
        f"{member.mention}."
    )


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
