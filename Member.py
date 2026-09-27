import discord
from discord.ext import commands


class Member(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    # ==========================================
    # 🏓 l!ping
    # ==========================================

    @commands.command()
    async def ping(self, ctx):

        latency = round(
            self.bot.latency * 1000
        )

        await ctx.send(
            f"🏓 **Pong!** `{latency}ms`"
        )


    # ==========================================
    # 🌙 l!server
    # ==========================================

    @commands.command()
    async def server(self, ctx):

        guild = ctx.guild

        embed = discord.Embed(
            title=f"🌙 {guild.name}",
            description=(
                f"👥 Thành viên: "
                f"`{guild.member_count}`\n"
                f"🆔 Server ID: `{guild.id}`"
            )
        )

        await ctx.send(
            embed=embed
        )


    # ==========================================
    # 🖼️ l!avatar
    # ==========================================

    @commands.command()
    async def avatar(
        self,
        ctx,
        member: discord.Member = None
    ):

        member = member or ctx.author

        embed = discord.Embed(
            title=f"🖼️ Avatar — {member.display_name}"
        )

        embed.set_image(
            url=member.display_avatar.url
        )

        await ctx.send(
            embed=embed
        )


    # ==========================================
    # 👤 l!userinfo
    # ==========================================

    @commands.command()
    async def userinfo(
        self,
        ctx,
        member: discord.Member = None
    ):

        member = member or ctx.author

        embed = discord.Embed(
            title=f"👤 {member.display_name}",
            description=(
                f"**Username:** `{member.name}`\n"
                f"**ID:** `{member.id}`\n"
                f"**Nickname:** "
                f"`{member.nick or 'Không có'}`\n"
                f"**Ngày tham gia:** "
                f"<t:{int
