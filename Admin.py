import discord
from discord.ext import commands


class Admin(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    # ==========================================
    # 🧹 l!clear
    # ==========================================

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, amount: int):

        if amount < 1 or amount > 100:
            await ctx.send(
                "❌ Số lượng phải từ `1` đến `100`."
            )
            return

        deleted = await ctx.channel.purge(
            limit=amount + 1
        )

        message = await ctx.send(
            f"🧹 Đã xóa `{len(deleted) - 1}` tin nhắn."
        )

        await message.delete(delay=3)

    # ==========================================
    # 👢 l!kick
    # ==========================================

    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx,
        member: discord.Member,
        *,
        reason: str = "Không có lý do"
    ):

        if member == ctx.author:
            await ctx.send(
                "❌ Bạn không thể kick chính mình."
            )
            return

        try:
            await member.kick(reason=reason)

            await ctx.send(
                f"👢 Đã kick {member.mention}.\n"
                f"📝 Lý do: `{reason}`"
            )

        except discord.Forbidden:
            await ctx.send(
                "❌ Luna không có quyền kick thành viên này."
            )

    # ==========================================
    # 🔨 l!ban
    # ==========================================

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx,
        member: discord.Member,
        *,
        reason: str = "Không có lý do"
    ):

        if member == ctx.author:
            await ctx.send(
                "❌ Bạn không thể ban chính mình."
            )
            return

        try:
            await member.ban(reason=reason)

            await ctx.send(
                f"🔨 Đã ban {member.mention}.\n"
                f"📝 Lý do: `{reason}`"
            )

        except discord.Forbidden:
            await ctx.send(
                "❌ Luna không có quyền ban thành viên này."
            )

    # ==========================================
    # 🔓 l!unban
    # ==========================================

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(
        self,
        ctx,
        user_id: int
    ):

        try:
            user = await self.bot.fetch_user(user_id)

            await ctx.guild.unban(user)

            await ctx.send(
                f"🔓 Đã unban **{user}**."
            )

        except discord.NotFound:
            await ctx.send(
                "❌ Không tìm thấy user hoặc user chưa bị ban."
            )

        except discord.Forbidden:
            await ctx.send(
                "❌ Luna không có quyền unban."
            )

    # ==========================================
    # 🔒 l!lock
    # ==========================================

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx):

        overwrite = ctx.channel.overwrites_for(
            ctx.guild.default_role
        )

        overwrite.send_messages = False

        await ctx.channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite
        )

        await ctx.send(
            "🔒 Đã khóa kênh này."
        )

    # ==========================================
    # 🔓 l!unlock
    # ==========================================

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx):

        overwrite = ctx.channel.overwrites_for(
            ctx.guild.default_role
        )

        overwrite.send_messages = None

        await ctx.channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite
        )

        await ctx.send(
            "🔓 Đã mở khóa kênh này."
        )

    # ==========================================
    # ⚠️ LỖI QUYỀN
    # ==========================================

    @clear.error
    @kick.error
    @ban.error
    @unban.error
    @lock.error
    @unlock.error
    async def admin_error(self, ctx, error):

        if isinstance(
            error,
            commands.MissingPermissions
        ):
           
