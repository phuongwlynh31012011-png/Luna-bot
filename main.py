import discord
from discord.ext import commands
import os, json, random, time

# =========================================================
# 🌙 LUNA BOT
# =========================================================

TOKEN = os.getenv("TOKEN")

# 👑 ID OWNER BOT 
OWNER_ID = 1522168539178598592

PREFIX = "l!"
DATA_FILE = "data.json"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None
)


# =========================================================
# 💾 DATA
# =========================================================

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "balances": {},
            "cooldowns": {},
            "welcome": {}
        }

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault("balances", {})
        data.setdefault("cooldowns", {})
        data.setdefault("welcome", {})
        return data

    except:
        return {
            "balances": {},
            "cooldowns": {},
            "welcome": {}
        }


data = load_data()


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# =========================================================
# 💰 XU LUNE
# =========================================================

def balance(user_id):
    return int(
        data["balances"].get(
            str(user_id),
            0
        )
    )


def add_xu(user_id, amount):
    uid = str(user_id)
    data["balances"][uid] = balance(user_id) + amount
    save_data()


def remove_xu(user_id, amount):
    if balance(user_id) < amount:
        return False

    data["balances"][str(user_id)] = (
        balance(user_id) - amount
    )
    save_data()
    return True


# =========================================================
# ⏳ COOLDOWN
# =========================================================

def get_cd(user_id, name):
    return float(
        data["cooldowns"]
        .get(str(user_id), {})
        .get(name, 0)
    )


def set_cd(user_id, name):
    uid = str(user_id)

    if uid not in data["cooldowns"]:
        data["cooldowns"][uid] = {}

    data["cooldowns"][uid][name] = time.time()
    save_data()


def cd_left(user_id, name, seconds):
    last = get_cd(user_id, name)
    return max(
        0,
        seconds - (time.time() - last)
    )


# =========================================================
# 👋 WELCOME RIÊNG TỪNG SERVER
# =========================================================

def default_welcome():
    return {
        "enabled": False,
        "channel": None,
        "role": None,
        "image": None,
        "color": 0xBDEFFF,
        "message": (
            "🌙 **Chào mừng {user} đến với {server}!** ♡\n\n"
            "Chúc bạn có những phút giây thật vui vẻ tại đây."
        )
    }


def get_welcome(guild_id):
    gid = str(guild_id)

    if gid not in data["welcome"]:
        data["welcome"][gid] = default_welcome()
        save_data()

    return data["welcome"][gid]


# =========================================================
# 🌙 BOT ONLINE
# =========================================================

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()

        print("================================")
        print(f"🌙 Luna: {bot.user}")
        print(f"🆔 ID: {bot.user.id}")
        print(f"🏠 Server: {len(bot.guilds)}")
        print(f"⚡ Slash: {len(synced)}")
        print("================================")

    except Exception as e:
        print(f"❌ Lỗi sync: {e}")


# =========================================================
# 👋 MEMBER JOIN
# =========================================================

@bot.event
async def on_member_join(member):

    config = get_welcome(
        member.guild.id
    )

    if not config["enabled"]:
        return

    if not config["channel"]:
        return

    channel = member.guild.get_channel(
        config["channel"]
    )

    if not channel:
        return

    text = config["message"]

    text = text.replace(
        "{user}",
        member.mention
    )

    text = text.replace(
        "{name}",
        member.display_name
    )

    text = text.replace(
        "{server}",
        member.guild.name
    )

    text = text.replace(
        "{members}",
        str(member.guild.member_count)
    )

    embed = discord.Embed(
        description=text,
        color=config["color"]
    )

    if config["image"]:
        embed.set_image(
            url=config["image"]
        )

    content = None

    if config["role"]:
        role = member.guild.get_role(
            config["role"]
        )

        if role:
            content = (
                f"🎀 {role.mention} "
                f"ra chào thành viên mới nhé! ♡"
            )

    await channel.send(
        content=content,
        embed=embed
    )


# =========================================================
# 🌙 /HELLO
# =========================================================

@bot.tree.command(
    name="hello",
    description="Helo bbi"
)
async def hello(interaction):

    await interaction.response.send_message(
        f"🌙 Xin chào {interaction.user.mention}!\n"
        "╰┈➤ Luna rất vui được gặp bạn ♡"
    )


# =========================================================
# 📖 /HELP
# =========================================================

@bot.tree.command(
    name="help",
    description="Mở bảng hướng dẫn Luna"
)
async def help_command(interaction):

    embed = discord.Embed(
        title="🌙・𝐋𝐔𝐍𝐀 𝐂𝐎𝐍𝐓𝐑𝐎𝐋",
        description=(
            "Bảng hướng dẫn Luna ♡\n\n"
            "Prefix: `l!`\n"
            "Slash: `/hello` • `/help`"
        ),
        color=0xBDEFFF
    )

    embed.add_field(
        name="👤・THÀNH VIÊN",
        value=(
            "`l!ping`\n"
            "`l!avatar [@user]`\n"
            "`l!userinfo [@user]`\n"
            "`l!server`"
        ),
        inline=False
    )

    embed.add_field(
        name="💰・XU LUNE",
        value=(
            "`l!balance`\n"
            "`l!daily` — 24h / 300–600 xu\n"
            "`l!work` — 1h / 50–100 xu\n"
            "`l!give @user số_xu`\n"
            "`l!shop`\n"
            "`l!buy item`"
        ),
        inline=False
    )

    embed.add_field(
        name="💗・TÌNH YÊU",
        value=(
            "`l!love @user`\n"
            "`l!couple`"
        ),
        inline=False
    )

    embed.add_field(
        name="👋・WELCOME",
        value=(
            "`l!welcome`\n"
            "`l!welcome on/off`\n"
            "`l!welcome channel #kênh`\n"
            "`l!welcome role @role`\n"
            "`l!welcome image link`\n"
            "`l!welcome color mã_màu`\n"
            "`l!welcome text nội_dung`\n"
            "`l!welcome show`\n"
            "`l!welcome reset`"
        ),
        inline=False
    )

    embed.add_field(
        name="🛠️・QUẢN LÝ",
        value=(
            "`l!clear số_lượng`\n"
            "`l!say nội_dung`"
        ),
        inline=False
    )

    embed.add_field(
        name="👑・OWNER",
        value="`l!cheatxu @user số_xu`",
        inline=False
    )

    embed.set_footer(
        text="Luna • Xu Lune 🌙"
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# =========================================================
# 🏓 PING
# =========================================================

@bot.command()
async def ping(ctx):
    ms = round(bot.latency * 1000)
    await ctx.send(
        f"🌙 Pong! `{ms}ms`"
    )


# =========================================================
# 🖼️ AVATAR
# =========================================================

@bot.command()
async def avatar(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    embed = discord.Embed(
        title=f"🌙 Avatar • {member.display_name}",
        color=0xBDEFFF
    )

    embed.set_image(
        url=member.display_avatar.url
    )

    await ctx.send(embed=embed)


# =========================================================
# 👤 USERINFO
# =========================================================

@bot.command()
async def userinfo(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    embed = discord.Embed(
        title=f"👤・{member.display_name}",
        color=0xBDEFFF
    )

    embed.set_thumbnail(
        url=member.display_avatar.url
    )

    embed.add_field(
        name="Tên",
        value=member.name,
        inline=True
    )

    embed.add_field(
        name="ID",
        value=str(member.id),
        inline=True
    )

    embed.add_field(
        name="Xu Lune",
        value=f"{balance(member.id):,}",
        inline=True
    )

    await ctx.send(embed=embed)


# =========================================================
# 🏠 SERVER
# =========================================================

@bot.command()
async def server(ctx):

    guild = ctx.guild

    embed = discord.Embed(
        title=f"🌙・{guild.name}",
        color=0xBDEFFF
    )

    embed.add_field(
        name="👥 Thành viên",
        value=str(guild.member_count),
        inline=True
    )

    embed.add_field(
        name="💬 Kênh",
        value=str(len(guild.channels)),
        inline=True
    )

    await ctx.send(embed=embed)


# =========================================================
# 💰 BALANCE
# =========================================================

@bot.command()
async def balance(
    ctx,
    member: discord.Member = None
):

    member = member or ctx.author

    await ctx.send(
        f"🌙 {member.mention} có "
        f"**{balance(member.id):,} xu Lune**."
    )


# =========================================================
# 🎁 DAILY
# 24 GIỜ — 300 ĐẾN 600
# =========================================================

@bot.command()
async def daily(ctx):

    user_id = ctx.author.id

    remaining = cd_left(
        user_id,
        "daily",
        86400
    )

    if remaining > 0:

        hours = int(
            remaining // 3600
        )

        minutes = int(
            (remaining % 3600) // 60
        )

        await ctx.send(
            f"⏳ {ctx.author.mention}, "
            f"bạn đã nhận daily rồi!\n"
            f"🌙 Nhận lại sau "
            f"**{hours} giờ {minutes} phút**."
        )

        return

    amount = random.randint(
        300,
        600
    )

    add_xu(
        user_id,
        amount
    )

    set_cd(
        user_id,
        "daily"
    )

    await ctx.send(
        f"🎁 {ctx.author.mention} nhận được "
        f"**{amount:,} xu Lune**!\n"
        f"⏰ Daily tiếp theo sau **24 giờ**."
    )


# =========================================================
# 💼 WORK
# 1 GIỜ — 50 ĐẾN 100
# =========================================================

@bot.command()
async def work(ctx):

    user_id = ctx.author.id

    remaining = cd_left(
        user_id,
        "work",
        3600
    )

    if remaining > 0:

        minutes = int(
            remaining // 60
        )

        seconds = int(
            remaining % 60
        )

        await ctx.send(
            f"⏳ {ctx.author.mention}, "
            f"bạn vừa làm việc xong!\n"
            f"💼 Làm lại sau "
            f"**{minutes} phút {seconds} giây**."
        )

        return

    amount = random.randint(
        50,
        100
    )

    jobs = [
        "phục vụ quán cà phê",
        "thiết kế ảnh",
        "chăm sóc thú cưng",
        "viết nội dung",
        "làm việc tại cửa hàng"
    ]

    job = random.choice(jobs)

    add_xu(
        user_id,
        amount
    )

    set_cd(
        user_id,
        "work"
    )

    await ctx.send(
        f"💼 {ctx.author.mention} đã {job} "
        f"và nhận **{amount:,} xu Lune**!\n"
        f"⏰ Có thể `l!work` lại sau **1 giờ**."
    )


# =========================================================
# 💸 GIVE
# =========================================================

@bot.command()
async def give(
    ctx,
    member: discord.Member,
    amount: int
):

    if member.bot:
        await ctx.send(
            "❌ Không thể gửi xu cho bot."
        )
        return

    if member.id == ctx.author.id:
        await ctx.send(
            "❌ Không thể tự gửi xu cho mình."
        )
        return

    if amount <= 0:
        await ctx.send(
            "❌ Số xu phải lớn hơn 0."
        )
        return

    if not remove_xu(
        ctx.author.id,
        amount
    ):
        await ctx.send(
            "❌ Bạn không đủ xu Lune."
        )
        return

    add_xu(
        member.id,
        amount
    )

    await ctx.send(
        f"💸 {ctx.author.mention} đã gửi "
        f"**{amount:,} xu Lune** cho "
        f"{member.mention}."
    )


# =========================================================
# 🛒 SHOP
# =========================================================

SHOP = {
    "gift": {
        "name": "🎁 Gift",
        "price": 500
    },
    "role": {
        "name": "💜 Custom Role",
        "price": 1000
    },
    "vip": {
        "name": "💎 VIP",
        "price": 5000
    }
}


@bot.command()
async def shop(ctx):

    embed = discord.Embed(
        title="🌙・𝐋𝐔𝐍𝐀 𝐒𝐇𝐎𝐏",
        description=(
            "Dùng `l!buy mã_item` để mua."
        ),
        color=0xBDEFFF
    )

    for item_id, item in SHOP.items():

        embed.add_field(
            name=item["name"],
            value=(
                f"Mã: `{item_id}`\n"
                f"💰 **{item['price']:,} xu Lune**"
            ),
            inline=False
        )

    await ctx.send(embed=embed)


# =========================================================
# 🛍️ BUY
# =========================================================

@bot.command()
async def buy(
    ctx,
    item: str
):

    item = item.lower()

    if item not in SHOP:
        await ctx.send(
            "❌ Item không tồn tại.\n"
            "Dùng `l!shop` để xem."
        )
        return

    price = SHOP[item]["price"]

    if not remove_xu(
        ctx.author.id,
        price
    ):
        await ctx.send(
            f"❌ Bạn không đủ xu Lune.\n"
            f"Giá: **{price:,} xu**"
        )
        return

    await ctx.send(
        f"🛒 {ctx.author.mention} đã mua "
        f"**{SHOP[item]['name']}**!"
    )


# =========================================================
# 💗 LOVE
# =========================================================

@bot.command()
async def love(
    ctx,
    member: discord.Member
):

    if member.id == ctx.author.id:
        await ctx.send(
            "💗 Tự yêu bản thân: **100%** ✨"
        )
        return

    percent = random.randint(
        1,
        100
    )

    await ctx.send(
        f"💗 **Luna Love**\n\n"
        f"☾ {ctx.author.mention} × {member.mention}\n"
        f"💞 Độ hợp: **{percent}%**"
    )


# =========================================================
# 💕 COUPLE
# =========================================================

@bot.command()
async def couple(ctx):

    members = [
        m for m in ctx.guild.members
        if not m.bot
    ]

    if len(members) < 2:
        await ctx.send(
            "❌ Không đủ thành viên."
        )
        return

    first, second = random.sample(
        members,
        2
    )

    percent = random.randint(
        50,
        100
    )

    await ctx.send(
        f"💗 **Luna ghép đôi**\n\n"
        f"☾ {first.mention} × {second.mention}\n"
        f"💞 Độ hợp: **{percent}%**"
    )


# =========================================================
# 👑 CHEAT XU
# CHỈ OWNER BOT
# =========================================================

@bot.command()
async def cheatxu(
    ctx,
    member: discord.Member,
    amount: int
):

    if ctx.author.id != OWNER_ID:
        await ctx.send(
            "❌ Chỉ Owner Bot mới dùng được."
        )
        return

    if amount <= 0:
        await ctx.send(
            "❌ Số xu phải lớn hơn 0."
        )
        return

    add_xu(
        member.id,
        amount
    )

    await ctx.send(
        f"👑 Đã cộng **{amount:,} xu Lune** "
        f"cho {member.mention}."
    )


# =========================================================
# 🧹 CLEAR
# =========================================================

@bot.command()
@commands.has_permissions(
    manage_messages=True
)
async def clear(
    ctx,
    amount: int
):

    if amount <= 0:
        await ctx.send(
            "❌ Số lượng không hợp lệ."
        )
        return

    deleted = await ctx.channel.purge(
        limit=amount + 1
    )

    msg = await ctx.send(
        f"🧹 Đã xóa "
        f"**{len(deleted) - 1}** tin nhắn."
    )

    await msg.delete(
        delay=3
    )


# =========================================================
# 🗣️ SAY
# =========================================================

@bot.command()
@commands.has_permissions(
    manage_messages=True
)
async def say(
    ctx,
    *,
    message
):

    await ctx.message.delete()
    await ctx.send(message)


# =========================================================
# 👋 WELCOME
# =========================================================

@bot.group(
    name="welcome",
    invoke_without_command=True
)
@commands.has_permissions(
    manage_guild=True
)
async def welcome(ctx):

    config = get_welcome(
        ctx.guild.id
    )

    status = (
        "🟢 Bật"
        if config["enabled"]
        else "🔴 Tắt"
    )

    channel = (
        f"<#{config['channel']}>"
        if config["channel"]
        else "Chưa cài"
    )

    role = (
        f"<@&{config['role']}>"
        if config["role"]
        else "Chưa cài"
    )

    embed = discord.Embed(
        title="🌙・𝐖𝐄𝐋𝐂𝐎𝐌𝐄",
        description=(
            f"**Trạng thái:** {status}\n"
            f"📢 **Kênh:** {channel}\n"
            f"🎀 **Role:** {role}\n"
            f"🖼️ **Ảnh:** "
            f"{'Đã cài' if config['image'] else 'Chưa cài'}\n\n"
            "**Cài đặt:**\n"
            "`l!welcome on`\n"
            "`l!welcome off`\n"
            "`l!welcome channel #kênh`\n"
            "`l!welcome role @role`\n"
            "`l!welcome image link`\n"
            "`l!welcome color mã_màu`\n"
            "`l!welcome text nội_dung`\n"
            "`l!welcome show`\n"
            "`l!welcome reset`"
        ),
        color=config["color"]
    )

    await ctx.send(embed=embed)


# =========================================================
# 🟢 WELCOME ON
# =========================================================

@welcome.command(name="on")
@commands.has_permissions(manage_guild=True)
async def welcome_on(ctx):

    config = get_welcome(ctx.guild.id)
    config["enabled"] = True
    save_data()

    await ctx.send(
        "🟢 Đã bật chào member."
    )


# =========================================================
# 🔴 WELCOME OFF
# =========================================================

@welcome.command(name="off")
@commands.has_permissions(manage_guild=True)
async def welcome_off(ctx):

    config = get_welcome(ctx.guild.id)
    config["enabled"] = False
    save_data()

    await ctx.send(
        "🔴 Đã tắt chào member."
    )


# =========================================================
# 📢 KÊNH WELCOME
# =========================================================

@welcome.command(name="channel")
@commands.has_permissions(manage_guild=True)
async def welcome_channel(
    ctx,
    channel: discord.TextChannel
):

    config = get_welcome(ctx.guild.id)
    config["channel"] = channel.id
    save_data()

    await ctx.send(
        f"📢 Kênh welcome: {channel.mention}"
    )


# =========================================================
# 🎀 ROLE WELCOME
# =========================================================

@welcome.command(name="role")
@commands.has_permissions(manage_guild=True)
async def welcome_role(
    ctx,
    role: discord.Role
):

    config = get_welcome(ctx.guild.id)
    config["role"] = role.id
    save_data()

    await ctx.send(
        f"🎀 Role welcome: {role.mention}"
    )


# =========================================================
# 🖼️ ẢNH WELCOME
# =========================================================

@welcome.command(name="image")
@commands.has_permissions(manage_guild=True)
async def welcome_image(
    ctx,
    *,
    url
):

    config = get_welcome(ctx.guild.id)
    config["image"] = url.strip()
    save_data()

    await ctx.send(
        "🖼️ Đã cập nhật ảnh Welcome."
    )


# =========================================================
# 🎨 MÀU WELCOME
# =========================================================

@welcome.command(name="color")
@commands.has_permissions(manage_guild=True)
async def welcome_color(
    ctx,
    color: str
):

    color = color.replace(
        "#",
        ""
    )

    try:
        value = int(color, 16)

    except ValueError:
        await ctx.send(
            "❌ Mã màu không hợp lệ.\n"
            "Ví dụ: `l!welcome color BDEFFF`"
        )
        return

    config = get_welcome(ctx.guild.id)
    config["color"] = value
    save_data()

    await ctx.send(
        f"🎨 Đã đổi màu thành "
        f"`#{color.upper()}`."
    )


# =========================================================
# 📝 NỘI DUNG WELCOME
# =========================================================

@welcome.command(name="text")
@commands.has_permissions(manage_guild=True)
async def welcome_text(
    ctx,
    *,
    message
):

    config = get_welcome(ctx.guild.id)
    config["message"] = message
    save_data()

    await ctx.send(
        "📝 Đã cập nhật lời chào."
    )


# =========================================================
# 👀 XEM WELCOME
# =========================================================

@welcome.command(name="show")
@commands.has_permissions(manage_guild=True)
async def welcome_show(ctx):

    config = get_welcome(ctx.guild.id)

    embed = discord.Embed(
        title="🌙・𝐖𝐄𝐋𝐂𝐎𝐌𝐄",
        description=config["message"],
        color=config["color"]
    )

    embed.add_field(
        name="Trạng thái",
        value=(
            "🟢 Bật"
            if config["enabled"]
            else "🔴 Tắt"
        ),
        inline=False
    )

    embed.add_field(
        name="📢 Kênh",
        value=(
            f"<#{config['channel']}>"
            if config["channel"]
            else "Chưa cài"
        ),
        inline=False
    )

    embed.add_field(
        name="🎀 Role",
        value=(
            f"<@&{config['role']}>"
            if config["role"]
            else "Chưa cài"
        ),
        inline=False
    )

    if config["image"]:
        embed.set_image(
            url=config["image"]
        )

    await ctx.send(embed=embed)


# =========================================================
# ♻️ RESET WELCOME
# =========================================================

@welcome.command(name="reset")
@commands.has_permissions(manage_guild=True)
async def welcome_reset(ctx):

    data["welcome"][
        str(ctx.guild.id)
    ] = default_welcome()

    save_data()

    await ctx.send(
        "♻️ Đã reset Welcome của server."
    )


# =========================================================
# ❌ XỬ LÝ LỖI
# =========================================================

@bot.event
async def on_command_error(
    ctx,
    error
):

    if isinstance(
        error,
        commands.CommandNotFound
    ):
        return

    if isinstance(
        error,
        commands.MissingPermissions
    ):
        await ctx.send(
            "❌ Bạn không có quyền dùng lệnh này."
        )
        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):
        await ctx.send(
            "❌ Bạn nhập thiếu thông tin."
        )
        return

    if isinstance(
        error,
        commands.BadArgument
    ):
        await ctx.send(
            "❌ Thông tin nhập vào không hợp lệ."
        )
        return

    print(
        f"❌ Lỗi: {error}"
    )


# =========================================================
# 🚀 START
# =========================================================

if not TOKEN:
    print("❌ Chưa tìm thấy TOKEN.")
else:
    bot.run(TOKEN)
