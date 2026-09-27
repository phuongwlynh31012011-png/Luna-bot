import os
import discord
from discord import app_commands
from discord.ext import commands

# =========================
# LUNA BOT
# =========================

intents = discord.Intents.default()

bot = commands.Bot(
    command_prefix="l!",
    intents=intents
)


# =========================
# BOT ONLINE
# =========================

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"🌙 Luna đã online: {bot.user}")


# =========================
# /PING
# =========================

@bot.tree.command(
    name="ping",
    description="Kiểm tra độ trễ của Luna"
)
async def ping(interaction: discord.Interaction):

    latency = round(bot.latency * 1000)

    await interaction.response.send_message(
        f"🌙 **Luna Pong!**\n"
        f"╰┈➤ Ping: `{latency}ms`"
    )


# =========================
# HELP MENU
# =========================

class HelpSelect(discord.ui.Select):

    def __init__(self):

        options = [
            discord.SelectOption(
                label="Lệnh thành viên",
                description="Các lệnh dành cho Member",
                emoji="👤",
                value="member"
            ),

            discord.SelectOption(
                label="Lệnh quản trị",
                description="Các lệnh dành cho Admin",
                emoji="🛡️",
                value="admin"
            ),

            discord.SelectOption(
                label="Thông tin Luna",
                description="Thông tin về bot",
                emoji="🌙",
                value="bot"
            )
        ]

        super().__init__(
            placeholder="☾ Chọn một danh mục...",
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        if self.values[0] == "member":

            embed = discord.Embed(
                title="👤・Lệnh thành viên",
                description=(
                    "`/ping` — Kiểm tra Luna\n"
                    "`/help` — Mở bảng điều khiển\n"
                    "`/avatar` — Xem avatar\n"
                    "`/server` — Thông tin server\n"
                    "`/userinfo` — Thông tin thành viên"
                )
            )

        elif self.values[0] == "admin":

            embed = discord.Embed(
                title="🛡️・Lệnh quản trị",
                description=(
                    "`/clear` — Xóa tin nhắn\n"
                    "`/kick` — Kick thành viên\n"
                    "`/ban` — Ban thành viên\n"
                    "`/mute` — Timeout thành viên\n"
                    "`/unmute` — Gỡ timeout"
                )
            )

        else:

            embed = discord.Embed(
                title="🌙・Luna",
                description=(
                    "**Luna** là bot đồng hành của **Lune Haven**.\n\n"
                    "✦ Quản lý\n"
                    "✦ Tiện ích\n"
                    "✦ Hỗ trợ cộng đồng\n"
                    "✦ Giải trí"
                )
            )

        await interaction.response.edit_message(
            embed=embed,
            view=self.view
        )


class HelpView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=120)

        self.add_item(HelpSelect())


# =========================
# /HELP
# =========================

@bot.tree.command(
    name="help",
    description="Mở bảng điều khiển lệnh của Luna"
)
async def help_command(interaction: discord.Interaction):

    embed = discord.Embed(
        title="🌙・LUNA HELP",
        description=(
            "Chào mừng bạn đến với bảng điều khiển của Luna.\n\n"
            "╰┈➤ Chọn danh mục bên dưới để xem các lệnh."
        )
    )

    await interaction.response.send_message(
        embed=embed,
        view=HelpView()
    )


# =========================
# TOKEN
# =========================

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise ValueError("❌ Chưa tìm thấy DISCORD_TOKEN")

bot.run(TOKEN)
