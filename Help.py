import discord
from discord import app_commands
from discord.ext import commands


class Help(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # ==========================================
    # 🌙 /help
    # ==========================================

    @app_commands.command(
        name="help",
        description="Xem các lệnh của Luna"
    )
    async def help_command(
        self,
        interaction: discord.Interaction
    ):

        embed = discord.Embed(
            title="🌙・LUNA HELP",
            description=(
                "**👤 MEMBER**\n"
                "`l!ping` — Kiểm tra Luna\n"
                "`l!server` — Thông tin server\n"
                "`l!avatar @user` — Xem avatar\n"
                "`l!userinfo @user` — Thông tin thành viên\n"
                "`l!botinfo` — Thông tin Luna\n\n"

                "**💰 XU LUNE**\n"
                "`l!balance` — Xem số dư\n"
                "`l!daily` — Nhận Xu mỗi ngày\n"
                "`l!work` — Kiếm Xu\n"
                "`l!give @user <số tiền>` — Chuyển Xu\n"
                "`l!rich` — BXH Xu\n"
                "`l!shop` — Xem shop\n"
                "`l!buy <món>` — Mua đồ\n"
                "`l!inventory` — Xem túi đồ\n\n"

                "**💕 LOVE**\n"
                "`l!love @user` — Xem % tình yêu\n"
                "`l!crush @user` — Đặt crush\n"
                "`l!couple` — Xem người yêu\n"
                "`l!marry @user` — Kết hôn\n"
                "`l!divorce` — Ly hôn\n"
                "`l!loveboard` — BXH tình yêu\n\n"

                "**🛡️ ADMIN**\n"
                "`l!clear <số lượng>` — Xóa tin nhắn\n"
                "`l!kick @user` — Kick\n"
                "`l!ban @user` — Ban\n"
                "`l!unban <ID>` — Unban\n"
                "`l!lock` — Khóa kênh\n"
                "`l!unlock` — Mở khóa kênh"
            ),
            color=discord.Color.dark_purple()
        )

        embed.set_footer(
            text="🌙 Luna • Lune Haven"
        )

        await interaction.response.send_message(
            embed=embed
        )

    # ==========================================
    # 👋 /hello
    # ==========================================

    @app_commands.command(
        name="hello",
        description="Luna chào bạn"
    )
    async def hello_command(
        self,
        interaction: discord.Interaction
    ):

        await interaction.response.send_message(
            f"🌙 Xin chào {interaction.user.mention}!\n"
            "╰┈➤ Chào mừng bạn đến với **Lune Haven** ♡"
        )


# ==========================================
# 📂 LOAD EXTENSION
# ==========================================

async def setup(bot):
    await bot.add_cog(Help(bot))
