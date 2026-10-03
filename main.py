
import os
import json
import random
import re
import asyncio
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands
from discord import app_commands

# ============================================================
# LUNA BOT - SINGLE FILE
# Prefix: l!
# Slash: /help, /hello
# ============================================================

TOKEN = os.getenv("TOKEN", "").strip()
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)

DATA_FILE = "luna_data.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix="l!", intents=intents, help_command=None)

DEFAULT_WELCOME = {
    "enabled": False,
    "channel": 0,
    "role": 0,
    "image": "",
    "color": 0xB8D8FF,
    "title": "🌙 • CHÀO MỪNG THÀNH VIÊN",
    "message": (
        "🌙 Chào mừng {member} đến với **{server}**.\n\n"
        "Giữa vô vàn nơi để dừng chân, thật vui vì hôm nay bạn đã ghé qua đây. ♡\n\n"
        "Hãy cứ thoải mái trò chuyện, tìm người chơi cùng, "
        "bật mic khi muốn, hay đơn giản là ngồi chill một chút dưới ánh trăng.\n\n"
        "✨ Thành viên thứ **{count}** của server."
    )
}

DEFAULT_GUILD = {
    "welcome": DEFAULT_WELCOME,
    "economy": {},
    "warnings": {},
    "shop": {
        "rose": {"name": "🌹 Hoa hồng", "price": 500},
        "choco": {"name": "🍫 Socola", "price": 800},
        "moon": {"name": "🌙 Mảnh trăng", "price": 1500},
    },
    "giveaways": {},
    "modlog": 0
}

data = {}


def load_data():
    global data
    if not os.path.exists(DATA_FILE):
        data = {"guilds": {}}
        save_data()
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"guilds": {}}
        save_data()


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def guild_data(guild_id: int):
    gid = str(guild_id)
    if gid not in data.setdefault("guilds", {}):
        data["guilds"][gid] = json.loads(json.dumps(DEFAULT_GUILD))
        save_data()
    g = data["guilds"][gid]
    g.setdefault("welcome", json.loads(json.dumps(DEFAULT_WELCOME)))
    g.setdefault("economy", {})
    g.setdefault("warnings", {})
    g.setdefault("shop", json.loads(json.dumps(DEFAULT_GUILD["shop"])))
    g.setdefault("giveaways", {})
    g.setdefault("modlog", 0)
    return g


def account(guild_id: int, user_id: int):
    g = guild_data(guild_id)
    uid = str(user_id)
    if uid not in g["economy"]:
        g["economy"][uid] = {
            "coins": 0,
            "daily": 0,
            "work": 0,
            "items": {}
        }
        save_data()
    return g["economy"][uid]


def fmt_coins(n):
    return f"{int(n):,}"


def parse_duration(value: str):
    m = re.fullmatch(r"(\d+)(s|m|h|d|w)", value.lower())
    if not m:
        return None
    number = int(m.group(1))
    return number * {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}[m.group(2)]


def parse_hex(value: str):
    value = value.strip().replace("#", "")
    if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
        return None
    return int(value, 16)


def replace_vars(text, member, guild):
    return (
        text.replace("{member}", member.mention)
        .replace("{name}", member.display_name)
        .replace("{server}", guild.name)
        .replace("{count}", str(guild.member_count or 0))
        .replace("{id}", str(member.id))
    )


def owner_only():
    async def predicate(ctx):
        if ctx.author.id != OWNER_ID:
            raise commands.CheckFailure("Lệnh này chỉ dành cho Owner Bot.")
        return True
    return commands.check(predicate)


async def safe_send(ctx, text, **kwargs):
    try:
        await ctx.send(text, **kwargs)
    except discord.Forbidden:
        pass


# ============================================================
# SỰ KIỆN
# ============================================================

@bot.event
async def on_ready():
    load_data()
    try:
        await bot.tree.sync()
    except Exception as e:
        print("Không thể đồng bộ Slash Commands:", e)

    print("=" * 45)
    print(f"🌙 Luna đã online: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🏠 Server: {len(bot.guilds)}")
    print("⚡ Slash: /help, /hello")
    print("⌨️ Prefix: l!")
    print("=" * 45)


@bot.event
async def on_member_join(member: discord.Member):
    cfg = guild_data(member.guild.id)["welcome"]

    if not cfg.get("enabled") or not cfg.get("channel"):
        return

    channel = member.guild.get_channel(int(cfg["channel"]))
    if channel is None:
        return

    embed = discord.Embed(
        title=replace_vars(cfg.get("title", ""), member, member.guild),
        description=replace_vars(cfg.get("message", ""), member, member.guild),
        color=int(cfg.get("color", 0xB8D8FF))
    )

    if cfg.get("image"):
        embed.set_image(url=cfg["image"])

    embed.set_footer(text=f"{member.guild.name} • Luna")

    role_id = int(cfg.get("role", 0) or 0)
    role = member.guild.get_role(role_id) if role_id else None
    content = (
        f"🎀 {role.mention} — ra chào đón {member.mention} nhé! ♡"
        if role else member.mention
    )

    try:
        await channel.send(content=content, embed=embed)
    except discord.Forbidden:
        print(f"⚠️ Luna thiếu quyền gửi WLC tại {channel}.")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingPermissions):
        await safe_send(ctx, "❌ Bạn không có quyền dùng lệnh này.")
        return
    if isinstance(error, commands.BotMissingPermissions):
        await safe_send(ctx, "❌ Luna thiếu quyền cần thiết.")
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await safe_send(ctx, f"❌ Thiếu thông tin: `{error.param.name}`.")
        return
    if isinstance(error, commands.BadArgument):
        await safe_send(ctx, "❌ Thông tin nhập vào không hợp lệ.")
        return
    if isinstance(error, commands.CheckFailure):
        await safe_send(ctx, f"❌ {error}")
        return
    print("Lỗi lệnh:", repr(error))
    await safe_send(ctx, "❌ Đã xảy ra lỗi khi thực hiện lệnh.")


# ============================================================
# SLASH: /HELLO + /HELP
# ============================================================

@bot.tree.command(name="hello", description="Luna chào bạn")
async def slash_hello(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"🌙 Xin chào {interaction.user.mention}! Luna đang hoạt động ♡"
    )


def make_help_embed():
    embed = discord.Embed(
        title="🌙 • LUNA CONTROL PANEL",
        description="Bot đa năng cho server. Lệnh thường dùng `l!`; Slash giữ `/help` và `/hello`.",
        color=0xB8D8FF
    )
    embed.add_field(
        name="👋 WELCOME",
        value=(
            "`l!setwelcome #kênh @role`\n"
            "`l!welcome on/off/show/test/reset`\n"
            "`l!setwelcomemsg ...`\n"
            "`l!setwelcometitle ...`\n"
            "`l!setwelcomeimage link`\n"
            "`l!setwelcomecolor #mãmàu`"
        ), inline=False
    )
    embed.add_field(
        name="💰 XU LUNE",
        value="`l!balance` • `l!daily` • `l!work` • `l!give` • `l!shop` • `l!buy` • `l!inventory`",
        inline=False
    )
    embed.add_field(
        name="🎁 GIVEAWAY",
        value="`l!giveaway start 1h 1 Phần thưởng`\n`l!giveaway end ID` • `l!giveaway reroll ID`",
        inline=False
    )
    embed.add_field(
        name="⚠️ CẢNH BÁO",
        value="`l!warn @user lý do` • `l!warnings @user` • `l!unwarn @user [số]`\n`l!setmodlog #kênh`",
        inline=False
    )
    embed.add_field(
        name="🛡️ QUẢN LÝ",
        value="`l!clear 10` • `l!lock` • `l!unlock` • `l!kick` • `l!ban`",
        inline=False
    )
    embed.add_field(name="👑 OWNER", value="`l!cheat @user số_xu`", inline=False)
    embed.set_footer(text="Luna • Lune Haven")
    return embed


@bot.tree.command(name="help", description="Mở bảng điều khiển hướng dẫn Luna")
async def slash_help(interaction: discord.Interaction):
    await interaction.response.send_message(embed=make_help_embed())


@bot.command(name="help")
async def prefix_help(ctx):
    await ctx.send(embed=make_help_embed())


# ============================================================
# CƠ BẢN
# ============================================================

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")


@bot.command(name="server")
async def server(ctx):
    g = ctx.guild
    embed = discord.Embed(title=f"🌙 {g.name}", color=0xB8D8FF)
    embed.add_field(name="👥 Thành viên", value=str(g.member_count))
    embed.add_field(name="💬 Kênh", value=str(len(g.channels)))
    embed.add_field(name="👑 Chủ server", value=g.owner.mention if g.owner else "Không rõ")
    await ctx.send(embed=embed)


# ============================================================
# WELCOME
# ============================================================

@bot.group(name="welcome", invoke_without_command=True)
@commands.has_guild_permissions(manage_guild=True)
async def welcome(ctx):
    await welcome_show(ctx)


@welcome.command(name="on")
@commands.has_guild_permissions(manage_guild=True)
async def welcome_on(ctx):
    guild_data(ctx.guild.id)["welcome"]["enabled"] = True
    save_data()
    await ctx.send("🟢 Đã bật Welcome.")


@welcome.command(name="off")
@commands.has_guild_permissions(manage_guild=True)
async def welcome_off(ctx):
    guild_data(ctx.guild.id)["welcome"]["enabled"] = False
    save_data()
    await ctx.send("🔴 Đã tắt Welcome.")


@welcome.command(name="show")
@commands.has_guild_permissions(manage_guild=True)
async def welcome_show(ctx):
    cfg = guild_data(ctx.guild.id)["welcome"]
    channel = ctx.guild.get_channel(int(cfg.get("channel", 0) or 0))
    role = ctx.guild.get_role(int(cfg.get("role", 0) or 0))

    embed = discord.Embed(title="🌙 • WELCOME", color=int(cfg.get("color", 0xB8D8FF)))
    embed.add_field(name="Trạng thái", value="🟢 Bật" if cfg.get("enabled") else "🔴 Tắt", inline=False)
    embed.add_field(name="📢 Kênh", value=channel.mention if channel else "Chưa cài", inline=False)
    embed.add_field(name="🎀 Role", value=role.mention if role else "Chưa cài", inline=False)
    embed.add_field(name="🖼️ Ảnh", value="Đã cài" if cfg.get("image") else "Chưa cài", inline=False)
    embed.add_field(name="📝 Tiêu đề", value=cfg.get("title", "Chưa cài")[:1024], inline=False)
    await ctx.send(embed=embed)


@welcome.command(name="test")
@commands.has_guild_permissions(manage_guild=True)
async def welcome_test(ctx):
    cfg = guild_data(ctx.guild.id)["welcome"]
    if not cfg.get("channel"):
        await ctx.send("❌ Chưa cài kênh Welcome.")
        return

    channel = ctx.guild.get_channel(int(cfg["channel"]))
    if channel is None:
        await ctx.send("❌ Không tìm thấy kênh Welcome.")
        return

    member = ctx.author
    embed = discord.Embed(
        title=replace_vars(cfg.get("title", ""), member, ctx.guild),
        description=replace_vars(cfg.get("message", ""), member, ctx.guild),
        color=int(cfg.get("color", 0xB8D8FF))
    )
    if cfg.get("image"):
        embed.set_image(url=cfg["image"])

    role = ctx.guild.get_role(int(cfg.get("role", 0) or 0))
    content = f"🎀 {role.mention} — ra chào đón {member.mention} nhé! ♡" if role else member.mention

    try:
        await channel.send(content=content, embed=embed)
        await ctx.send("✅ Đã gửi thử Welcome.")
    except discord.Forbidden:
        await ctx.send("❌ Luna không có quyền gửi vào kênh Welcome.")


@welcome.command(name="reset")
@commands.has_guild_permissions(manage_guild=True)
async def welcome_reset(ctx):
    guild_data(ctx.guild.id)["welcome"] = json.loads(json.dumps(DEFAULT_WELCOME))
    save_data()
    await ctx.send("♻️ Đã reset Welcome.")


@bot.command(name="setwelcome")
@commands.has_guild_permissions(manage_guild=True)
async def setwelcome(ctx, channel: discord.TextChannel, role: discord.Role = None):
    cfg = guild_data(ctx.guild.id)["welcome"]
    cfg["channel"] = channel.id
    if role:
        cfg["role"] = role.id
    cfg["enabled"] = True
    save_data()
    await ctx.send(
        f"✅ Đã cài Welcome tại {channel.mention}"
        + (f" và role {role.mention}." if role else ".")
    )


@bot.command(name="setwelcomemsg", aliases=["welcomemsg"])
@commands.has_guild_permissions(manage_guild=True)
async def setwelcomemsg(ctx, *, message: str):
    guild_data(ctx.guild.id)["welcome"]["message"] = message
    save_data()
    await ctx.send("✅ Đã đổi nội dung Welcome.\nBiến: `{member}` `{name}` `{server}` `{count}` `{id}`")


@bot.command(name="setwelcometitle")
@commands.has_guild_permissions(manage_guild=True)
async def setwelcometitle(ctx, *, title: str):
    guild_data(ctx.guild.id)["welcome"]["title"] = title
    save_data()
    await ctx.send("✅ Đã đổi tiêu đề Welcome.")


@bot.command(name="setwelcomeimage")
@commands.has_guild_permissions(manage_guild=True)
async def setwelcomeimage(ctx, url: str = None):
    if not url and ctx.message.attachments:
        url = ctx.message.attachments[0].url
    if not url:
        await ctx.send("❌ Gửi link ảnh hoặc đính kèm ảnh cùng lệnh.")
        return
    guild_data(ctx.guild.id)["welcome"]["image"] = url
    save_data()
    await ctx.send("🖼️ Đã đổi ảnh Welcome.")


@bot.command(name="setwelcomecolor")
@commands.has_guild_permissions(manage_guild=True)
async def setwelcomecolor(ctx, color: str):
    value = parse_hex(color)
    if value is None:
        await ctx.send("❌ Màu phải dạng `#B8D8FF`.")
        return
    guild_data(ctx.guild.id)["welcome"]["color"] = value
    save_data()
    await ctx.send("🎨 Đã đổi màu Welcome.")


# ============================================================
# XU LUNE
# ============================================================

@bot.command(name="balance", aliases=["bal", "xu"])
async def balance(ctx, member: discord.Member = None):
    member = member or ctx.author
    acc = account(ctx.guild.id, member.id)
    await ctx.send(f"🌙 {member.mention} có **{fmt_coins(acc['coins'])} xu Lune**.")


@bot.command(name="daily")
async def daily(ctx):
    acc = account(ctx.guild.id, ctx.author.id)
    now = int(datetime.now(timezone.utc).timestamp())
    remaining = int(acc.get("daily", 0)) + 86400 - now

    if remaining > 0:
        await ctx.send(f"⏳ Daily còn **{remaining // 3600} giờ {(remaining % 3600) // 60} phút**.")
        return

    amount = random.randint(300, 600)
    acc["coins"] += amount
    acc["daily"] = now
    save_data()
    await ctx.send(f"🌙 Daily: **+{fmt_coins(amount)} xu Lune**!")


@bot.command(name="work")
async def work(ctx):
    acc = account(ctx.guild.id, ctx.author.id)
    now = int(datetime.now(timezone.utc).timestamp())
    remaining = int(acc.get("work", 0)) + 3600 - now

    if remaining > 0:
        await ctx.send(f"⏳ Work còn **{remaining // 60} phút**.")
        return

    amount = random.randint(50, 100)
    acc["coins"] += amount
    acc["work"] = now
    save_data()
    await ctx.send(f"💼 Work: **+{fmt_coins(amount)} xu Lune**!")


@bot.command(name="give")
async def give(ctx, member: discord.Member, amount: int):
    if member.bot or member.id == ctx.author.id or amount <= 0:
        await ctx.send("❌ Thông tin chuyển xu không hợp lệ.")
        return

    sender = account(ctx.guild.id, ctx.author.id)
    receiver = account(ctx.guild.id, member.id)
    if sender["coins"] < amount:
        await ctx.send("❌ Bạn không đủ xu.")
        return

    sender["coins"] -= amount
    receiver["coins"] += amount
    save_data()
    await ctx.send(f"💸 Đã chuyển **{fmt_coins(amount)} xu** cho {member.mention}.")


@bot.command(name="shop")
async def shop(ctx):
    shop_data = guild_data(ctx.guild.id)["shop"]
    embed = discord.Embed(title="🌙 • SHOP LUNE", description="Mua bằng xu Lune.", color=0xB8D8FF)
    for key, item in shop_data.items():
        embed.add_field(name=f"{item['name']} — `{key}`", value=f"💰 {fmt_coins(item['price'])} xu", inline=False)
    embed.set_footer(text="Dùng: l!buy tên_vật_phẩm [số_lượng]")
    await ctx.send(embed=embed)


@bot.command(name="buy")
async def buy(ctx, item_name: str, amount: int = 1):
    shop_data = guild_data(ctx.guild.id)["shop"]
    key = item_name.lower()
    if key not in shop_data:
        await ctx.send("❌ Không có vật phẩm này. Dùng `l!shop`.")
        return
    if amount <= 0 or amount > 100:
        await ctx.send("❌ Số lượng không hợp lệ.")
        return

    item = shop_data[key]
    total = item["price"] * amount
    acc = account(ctx.guild.id, ctx.author.id)
    if acc["coins"] < total:
        await ctx.send(f"❌ Cần **{fmt_coins(total)} xu**, bạn chỉ có **{fmt_coins(acc['coins'])} xu**.")
        return

    acc["coins"] -= total
    acc["items"][key] = acc["items"].get(key, 0) + amount
    save_data()
    await ctx.send(f"🛍️ Đã mua **{item['name']} x{amount}**.")


@bot.command(name="inventory", aliases=["inv"])
async def inventory(ctx, member: discord.Member = None):
    member = member or ctx.author
    acc = account(ctx.guild.id, member.id)
    if not acc["items"]:
        await ctx.send(f"🎒 {member.mention} chưa có vật phẩm.")
        return

    shop_data = guild_data(ctx.guild.id)["shop"]
    lines = [
        f"{shop_data.get(k, {}).get('name', k)}: **{v}**"
        for k, v in acc["items"].items()
    ]
    await ctx.send(f"🎒 **Kho của {member.display_name}**\n" + "\n".join(lines))


# ============================================================
# OWNER CHEAT
# ============================================================

@bot.command(name="cheat")
@owner_only()
async def cheat(ctx, member: discord.Member, amount: int):
    if amount == 0:
        await ctx.send("❌ Số xu phải khác 0.")
        return
    acc = account(ctx.guild.id, member.id)
    acc["coins"] += amount
    save_data()
    action = "thêm" if amount > 0 else "trừ"
    await ctx.send(f"👑 Đã **{action} {fmt_coins(abs(amount))} xu** cho {member.mention}.")


# ============================================================
# GIVEAWAY
# ============================================================

def giveaway_embed(info, ended=False):
    title = "🎉 GIVEAWAY ĐÃ KẾT THÚC" if ended else "🎉 GIVEAWAY"
    embed = discord.Embed(
        title=title,
        description=(
            f"🎁 **Phần thưởng:** {info['prize']}\n"
            f"👥 **Số người thắng:** {info['winners']}\n"
            f"⏰ **Kết thúc:** <t:{info['end']}:R>\n\n"
            "React **🎉** để tham gia!"
        ),
        color=0x888888 if ended else 0xB8D8FF
    )
    return embed


@bot.group(name="giveaway", aliases=["ga"], invoke_without_command=True)
async def giveaway(ctx):
    await ctx.send(
        "🎉 `l!giveaway start 1h 1 Phần thưởng`\n"
        "`l!giveaway end ID`\n"
        "`l!giveaway reroll ID`"
    )


@giveaway.command(name="start")
@commands.has_guild_permissions(manage_guild=True)
async def giveaway_start(ctx, duration: str, winners: int, *, prize: str):
    seconds = parse_duration(duration)
    if seconds is None or seconds < 10:
        await ctx.send("❌ Thời gian ví dụ: `10m`, `1h`, `1d`.")
        return
    if not 1 <= winners <= 50:
        await ctx.send("❌ Số người thắng từ 1 đến 50.")
        return

    end = int(datetime.now(timezone.utc).timestamp()) + seconds
    info = {
        "channel_id": ctx.channel.id,
        "message_id": 0,
        "prize": prize,
        "winners": winners,
        "end": end,
        "ended": False
    }

    msg = await ctx.send(embed=giveaway_embed(info))
    await msg.add_reaction("🎉")
    info["message_id"] = msg.id
    guild_data(ctx.guild.id)["giveaways"][str(msg.id)] = info
    save_data()

    await ctx.send(f"✅ Đã tạo Giveaway `#{msg.id}`.")
    await asyncio.sleep(seconds)
    await finish_giveaway(ctx.guild.id, msg.id)


async def finish_giveaway(guild_id, message_id):
    g = guild_data(guild_id)
    raw = g["giveaways"].get(str(message_id))
    if not raw or raw.get("ended"):
        return

    channel = bot.get_channel(int(raw["channel_id"]))
    if channel is None:
        raw["ended"] = True
        save_data()
        return

    try:
        msg = await channel.fetch_message(message_id)
    except (discord.NotFound, discord.Forbidden):
        raw["ended"] = True
        save_data()
        return

    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    users = []
    if reaction:
        try:
            async for user in reaction.users():
                if not user.bot:
                    users.append(user)
        except discord.HTTPException:
            pass

    random.shuffle(users)
    winners = users[:int(raw["winners"])]
    raw["ended"] = True
    save_data()

    ended_embed = giveaway_embed(raw, ended=True)

    if winners:
        mentions = ", ".join(u.mention for u in winners)
        ended_embed.add_field(name="🏆 Người thắng", value=mentions, inline=False)
        await channel.send(f"🎉 Chúc mừng {mentions}! Bạn đã thắng **{raw['prize']}**!")
    else:
        ended_embed.add_field(name="🏆 Người thắng", value="Không có người tham gia hợp lệ.", inline=False)
        await channel.send("🎉 Giveaway kết thúc nhưng chưa có người thắng.")

    try:
        await msg.edit(embed=ended_embed)
    except discord.HTTPException:
        pass


@giveaway.command(name="end")
@commands.has_guild_permissions(manage_guild=True)
async def giveaway_end(ctx, message_id: int):
    if str(message_id) not in guild_data(ctx.guild.id)["giveaways"]:
        await ctx.send("❌ Không tìm thấy Giveaway.")
        return
    await finish_giveaway(ctx.guild.id, message_id)
    await ctx.send("✅ Đã kết thúc Giveaway.")


@giveaway.command(name="reroll")
@commands.has_guild_permissions(manage_guild=True)
async def giveaway_reroll(ctx, message_id: int):
    raw = guild_data(ctx.guild.id)["giveaways"].get(str(message_id))
    if not raw:
        await ctx.send("❌ Không tìm thấy Giveaway.")
        return

    channel = bot.get_channel(int(raw["channel_id"]))
    if channel is None:
        await ctx.send("❌ Không tìm thấy kênh Giveaway.")
        return

    try:
        msg = await channel.fetch_message(message_id)
    except discord.HTTPException:
        await ctx.send("❌ Không lấy được Giveaway.")
        return

    reaction = discord.utils.get(msg.reactions, emoji="🎉")
    users = []
    if reaction:
        async for user in reaction.users():
            if not user.bot:
                users.append(user)

    if not users:
        await ctx.send("❌ Không có người tham gia.")
        return

    winner = random.choice(users)
    await ctx.send(f"🔄 Reroll! Người thắng mới: {winner.mention} — **{raw['prize']}**.")


# ============================================================
# CẢNH BÁO
# ============================================================

WARN_STEPS = {
    3: ("timeout", 5 * 60),
    4: ("timeout", 15 * 60),
    5: ("timeout", 60 * 60),
    6: ("timeout", 24 * 60 * 60),
    7: ("kick", 0),
    8: ("ban", 0),
}


async def send_modlog(guild, text):
    channel_id = int(guild_data(guild.id).get("modlog", 0) or 0)
    if not channel_id:
        return
    channel = guild.get_channel(channel_id)
    if channel:
        try:
            await channel.send(text)
        except discord.HTTPException:
            pass


@bot.command(name="setmodlog")
@commands.has_guild_permissions(manage_guild=True)
async def setmodlog(ctx, channel: discord.TextChannel):
    guild_data(ctx.guild.id)["modlog"] = channel.id
    save_data()
    await ctx.send(f"📋 Đã đặt kênh log: {channel.mention}")


@bot.command(name="warn")
@commands.has_guild_permissions(moderate_members=True)
async def warn(ctx, member: discord.Member, *, reason: str = "Không ghi lý do"):
    if member.bot or member.id == ctx.author.id:
        await ctx.send("❌ Không thể cảnh báo đối tượng này.")
        return

    g = guild_data(ctx.guild.id)
    uid = str(member.id)
    g["warnings"].setdefault(uid, [])
    g["warnings"][uid].append({
        "reason": reason,
        "by": ctx.author.id,
        "time": int(datetime.now(timezone.utc).timestamp())
    })
    count = len(g["warnings"][uid])
    save_data()

    embed = discord.Embed(title="⚠️ CẢNH BÁO THÀNH VIÊN", color=0xF2C94C)
    embed.description = (
        f"👤 Thành viên: {member.mention}\n"
        f"🔢 Số cảnh báo: **{count}**\n"
        f"📝 Lý do: {reason}\n"
        f"👮 Người cảnh báo: {ctx.author.mention}"
    )
    await ctx.send(embed=embed)
    await send_modlog(ctx.guild, f"⚠️ {member} nhận cảnh báo #{count}: {reason}")

    action = WARN_STEPS.get(count)
    if not action:
        return

    kind, duration = action
    try:
        if kind == "timeout":
            until = discord.utils.utcnow() + timedelta(seconds=duration)
            await member.timeout(until, reason=f"Đủ {count} cảnh báo: {reason}")
            await ctx.send(f"⏱️ {member.mention} đạt {count} cảnh báo → timeout {duration // 60} phút.")
        elif kind == "kick":
            await member.kick(reason=f"Đủ {count} cảnh báo.")
            await ctx.send(f"👢 {member.mention} đã bị kick do đủ {count} cảnh báo.")
        elif kind == "ban":
            await member.ban(reason=f"Đủ {count} cảnh báo.")
            await ctx.send(f"🔨 {member.mention} đã bị ban do đủ {count} cảnh báo.")
    except discord.Forbidden:
        await ctx.send("❌ Luna không đủ quyền để xử lý tự động.")


@bot.command(name="warnings", aliases=["warns"])
async def warnings(ctx, member: discord.Member = None):
    member = member or ctx.author
    records = guild_data(ctx.guild.id)["warnings"].get(str(member.id), [])
    if not records:
        await ctx.send(f"🛡️ {member.mention} không có cảnh báo.")
        return

    lines = [f"**#{i}** — {item.get('reason', 'Không rõ')}" for i, item in enumerate(records[-20:], 1)]
    embed = discord.Embed(
        title=f"⚠️ Cảnh báo của {member.display_name}",
        description="\n".join(lines),
        color=0xF2C94C
    )
    await ctx.send(embed=embed)


@bot.command(name="unwarn")
@commands.has_guild_permissions(moderate_members=True)
async def unwarn(ctx, member: discord.Member, index: int = None):
    records = guild_data(ctx.guild.id)["warnings"].get(str(member.id), [])
    if not records:
        await ctx.send("❌ Không có cảnh báo.")
        return

    if index is None:
        records.pop()
    elif 1 <= index <= len(records):
        records.pop(index - 1)
    else:
        await ctx.send("❌ Số cảnh báo không hợp lệ.")
        return

    save_data()
    await ctx.send(f"✅ Đã gỡ cảnh báo của {member.mention}.")


# ============================================================
# QUẢN LÝ
# ============================================================

@bot.command(name="clear", aliases=["purge"])
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int):
    if not 1 <= amount <= 100:
        await ctx.send("❌ Số lượng từ 1 đến 100.")
        return
    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Đã xóa **{len(deleted) - 1}** tin nhắn.")
    await asyncio.sleep(3)
    try:
        await msg.delete()
    except discord.HTTPException:
        pass


@bot.command(name="lock")
@commands.has_permissions(manage_channels=True)
async def lock(ctx):
    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = False
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send("🔒 Đã khóa kênh.")


@bot.command(name="unlock")
@commands.has_permissions(manage_channels=True)
async def unlock(ctx):
    overwrite = ctx.channel.overwrites_for(ctx.guild.default_role)
    overwrite.send_messages = None
    await ctx.channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
    await ctx.send("🔓 Đã mở khóa kênh.")


@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason: str = "Không ghi lý do"):
    if member == ctx.guild.owner:
        await ctx.send("❌ Không thể kick chủ server.")
        return
    await member.kick(reason=reason)
    await ctx.send(f"👢 Đã kick {member.mention}.\n📝 {reason}")


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "Không ghi lý do"):
    if member == ctx.guild.owner:
        await ctx.send("❌ Không thể ban chủ server.")
        return
    await member.ban(reason=reason)
    await ctx.send(f"🔨 Đã ban {member.mention}.\n📝 {reason}")


# ============================================================
# CHẠY BOT
# ============================================================

if __name__ == "__main__":
    load_data()

    if not TOKEN:
        raise RuntimeError("Chưa có TOKEN. Hãy thêm biến TOKEN trên Railway.")

    if OWNER_ID == 0:
        print("⚠️ OWNER_ID chưa được cài. l!cheat sẽ không dùng được.")

    bot.run(TOKEN)
        
