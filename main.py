import os
import discord
from discord.ext import commands


# ==========================================
# 🌙 LUNA BOT
# ==========================================

intents = discord.Intents.default()

intents.message_content = True
intents.members = True


bot = commands.Bot(
    command_prefix="l!",
    intents=intents,
    help_command=None
)


# ==========================================
# 📂 LOAD CÁC MODULE
# ==========================================

async def load_extensions():

    extensions = [
        "member",
        "xu",
        "love",
        "admin",
        "help"
    ]

    for extension in extensions:

        try:
            await bot.load_extension(extension)
            print(f"✅ Đã tải: {extension}.py")

        except Exception as e:
            print(f"❌ Lỗi {extension}.py: {e}")


# ==========================================
# 🌙 BOT READY
# ==========================================

@bot.event
async def on_ready():

    print("━━━━━━━━━━━━━━━━━━━━")
    print(f"🌙 Luna đã online: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"📡 Server: {len(bot.guilds)}")
    print("━━━━━━━━━━━━━━━━━━━━")


# ==========================================
# 🚀 START BOT
# ==========================================

async def main():

    await load_extensions()

    await bot.start(
        os.getenv("DISCORD_TOKEN")
    )


if __name__ == "__main__":

    import asyncio

    asyncio.run(main())
