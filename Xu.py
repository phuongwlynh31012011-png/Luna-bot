import sqlite3
import random
import time

import discord
from discord.ext import commands


class Economy(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # =========================
        # 💰 DATABASE
        # =========================

        self.db = sqlite3.connect("lune.db")
        self.cursor = self.db.cursor()

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER NOT NULL DEFAULT 0
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            item_id TEXT,
            amount INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, item_id)
        )
        """)

        self.db.commit()

        # Cooldown
        self.daily_cd = {}
        self.work_cd = {}

        # =========================
        # 🛍️ SHOP
        # =========================

        self.shop = {
            "rose": {
                "name": "🌹 Hoa hồng
