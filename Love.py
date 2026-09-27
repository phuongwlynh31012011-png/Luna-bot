import random
import sqlite3

import discord
from discord.ext import commands


class Love(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        self.db = sqlite3.connect("lune.db")
        self.cursor = self.db.cursor()

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS love_data (
            user_id INTEGER PRIMARY KEY,
            crush_id INTEGER
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS couples (
            user1 INTEGER PRIMARY KEY,
            user2 INTEGER UNIQUE
        )
        """)

        self.db.commit()


    # ==========================================
    # 💕 l!love @user
    # ==========================================

    @commands.command()
    async def love(
        self,
        ctx,
        member: discord.Member
    ):

        if member == ctx.author:

            await ctx.send(
                "💕 Không thể xem tình yêu với chính mình."
            )

            return

        # Tạo % ổn định theo 2 ID
        ids = sorted([
            ctx.author.id,
            member.id
        ])

        random.seed(
            ids[0] * 100000 + ids[1]
        )

        percent = random.randint(1, 100)

        random.seed()

        if percent >= 90:
            status = "💍 Định mệnh!"
        elif percent >= 70:
            status = "💕 Rất hợp nhau!"
        elif percent >= 50:
            status = "💗 Có khả năng đó!"
        elif percent >= 30:
            status = "🌸 Khá hợp!"
        else:
            status = "🌙 Cần thêm thời gian..."

        embed = discord.Embed(
            title="💕・LUNE LOVE",
            description=(
                f"👤 {ctx.author.mention}\n"
                f"💗 {member.mention}\n\n"
                f"💞 Độ tình yêu: **{percent}%**\n"
                f"✨ {status}"
            )
        )

        await ctx.send(embed=embed)


    # ==========================================
    # 💘 l!crush @user
    # ==========================================

    @commands.command()
    async def crush(
        self,
        ctx,
        member: discord.Member
    ):

        if member == ctx.author:

            await ctx.send(
                "❌ Bạn không thể đặt chính mình làm crush."
            )

            return

        self.cursor.execute(
            """
            INSERT INTO love_data (user_id, crush_id)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET crush_id = excluded.crush_id
            """,
            (
                ctx.author.id,
                member.id
            )
        )

        self.db.commit()

        await ctx.send(
            f"💘 {ctx.author.mention} đã đặt "
            f"{member.mention} làm **crush**!"
        )


    # ==========================================
    # 💕 l!couple
    # ==========================================

    @commands.command()
    async def couple(self, ctx):

        self.cursor.execute(
            """
            SELECT user2
            FROM couples
            WHERE user1 = ?
            """,
            (ctx.author.id,)
        )

        result = self.cursor.fetchone()

        if result is None:

            self.cursor.execute(
                """
                SELECT user1
                FROM couples
                WHERE user2 = ?
                """,
                (ctx.author.id,)
            )

            result = self.cursor.fetchone()

            if result is None:

                await ctx.send(
                    "🌙 Bạn hiện chưa có người yêu."
                )

                return

            partner_id = result[0]

        else:

            partner_id = result[0]

        partner = self.bot.get_user(partner_id)

        if partner is None:

            await ctx.send(
                "💕 Không tìm thấy thông tin người yêu."
            )

            return

        await ctx.send(
            f"💑 **Cặp đôi của bạn**\n"
            f"💕 {ctx.author.mention} × "
            f"{partner.mention}"
        )


    # ==========================================
    # 💍 l!marry @user
    # ==========================================

    @commands.command()
    async def marry(
        self,
        ctx,
        member: discord.Member
    ):

        if member == ctx.author:

            await ctx.send(
                "💍 Không thể kết hôn với chính mình."
            )

            return

        # Kiểm tra người gửi đã có người yêu
        self.cursor.execute(
            """
            SELECT user1, user2
            FROM couples
            WHERE user1 = ? OR user2 = ?
            """,
            (
                ctx.author.id,
                ctx.author.id
            )
        )

        if self.cursor.fetchone():

            await ctx.send(
                "💕 Bạn đã có người yêu rồi."
            )

            return

        # Kiểm tra người được cầu hôn
        self.cursor.execute(
            """
            SELECT user1, user2
            FROM couples
            WHERE user1 = ? OR user2 = ?
            """,
            (
                member.id,
                member.id
            )
        )

        if self.cursor.fetchone():

            await ctx.send(
                f"💕 {member.mention} đã có người yêu."
            )

            return

        # Tạo cặp đôi
        self.cursor.execute(
            """
            INSERT INTO couples (user1, user2)
            VALUES (?, ?)
            """,
            (
                ctx.author.id,
                member.id
            )
        )

        self.db.commit()

        await ctx.send(
            f"💍 **Chúc mừng!**\n"
            f"💕 {ctx.author.mention} × "
            f"{member.mention}\n"
            f"✨ Hai bạn đã trở thành một cặp!"
        )


    # ==========================================
    # 💔 l!divorce
    # ==========================================

    @commands.command()
    async def divorce(self, ctx):

        self.cursor.execute(
            """
            SELECT user1, user2
            FROM couples
            WHERE user1 = ? OR user2 = ?
            """,
            (
                ctx.author.id,
                ctx.author.id
            )
        )

        result = self.cursor.fetchone()

        if result is None:

            await ctx.send(
                "🌙 Bạn hiện không có người yêu."
            )

            return

        user1, user2 = result

        self.cursor.execute(
            """
            DELETE FROM couples
            WHERE user1 = ? AND user2 = ?
            """,
            (
                user1,
                user2
            )
        )

        self.db.commit()

        await ctx.send(
            "💔 Hai bạn đã chia tay."
        )


    # ==========================================
    # 🏆 l!loveboard
    # ==========================================

    @commands.command()
    async def loveboard(self, ctx):

        self.cursor.execute(
            """
            SELECT user1, user2
            FROM couples
            LIMIT 10
            """
        )

        couples = self.cursor.fetchall()

        if not couples:

            await ctx.send(
                "💕 Chưa có cặp đôi nào."
            )

            return

        text = ""

        for index, (user1, user2) in enumerate(
            couples,
            start=1
        ):

            member1 = self.bot.get_user(user1)
            member2 = self.bot.get_user(user2)

            name1 = (
                member1.display_name
                if member1
                else "Unknown"
            )

            name2 = (
                member2.display_name
                if member2
                else "Unknown"
            )

            text += (
                f"**{index}.** 💕 "
                f"{name1} × {name2}\n"
            )

        embed = discord.Embed(
            title="💕・LUNE LOVEBOARD",
            description=text
        )

        await ctx.send(
            embed=embed
        )


# ==========================================
# 📂 LOAD EXTENSION
# ==========================================

async def setup(bot):

    await bot.add_cog(
        Love(bot)
      )
