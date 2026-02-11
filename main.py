import discord
from discord.ext import commands
import os
import asyncio
import aiohttp

# =========================
# ENV
# =========================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
FOLDER_ID = os.getenv("FOLDER_ID")
VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID"))

# =========================
# BOT
# =========================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# DRIVE API (ASYNC)
# =========================
async def get_audio_files():
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"'{FOLDER_ID}' in parents and mimeType contains 'audio/'",
        "fields": "files(id,name)",
        "key": GOOGLE_API_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            return data.get("files", [])

def file_url(file_id):
    return f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={GOOGLE_API_KEY}"

async def download_file(url, filename):
    path = f"/tmp/{filename}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None

            with open(path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 512):
                    f.write(chunk)

    return path

# =========================
# PLAYER
# =========================
async def play_loop(vc):
    print("▶ play_loop started")

    while True:
        files = await get_audio_files()
        print("🎵 Files:", len(files))

        for f in files:
            print("▶ Playing:", f["name"])
            path = await download_file(file_url(f["id"]), f["name"])
            if not path:
                continue

            vc.play(discord.FFmpegPCMAudio(path))

            while vc.is_playing():
                await asyncio.sleep(1)

            try:
                os.remove(path)
            except:
                pass

# =========================
# BACKGROUND CONNECT TASK
# =========================
async def connect_and_play():
    await bot.wait_until_ready()
    await asyncio.sleep(5)

    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if not channel:
        print("❌ Voice channel tidak ditemukan")
        return

    print("🔊 Connecting to voice (background task)...")
    vc = await channel.connect(reconnect=True, self_deaf=True)

    print("✅ Voice connected")
    asyncio.create_task(play_loop(vc))

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    bot.loop.create_task(connect_and_play())

bot.run(DISCORD_TOKEN)
