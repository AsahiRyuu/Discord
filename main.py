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
# GLOBAL HTTP SESSION
# =========================
http_session: aiohttp.ClientSession | None = None

# =========================
# GOOGLE DRIVE (FIXED)
# =========================
async def get_audio_files():
    print("🔍 Fetching audio files from Drive...")

    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        # FIX QUERY
        "q": (
            f"'{FOLDER_ID}' in parents and "
            "(mimeType='audio/mpeg' or mimeType='audio/mp3' or mimeType contains 'audio/')"
        ),
        "fields": "files(id,name,mimeType)",
        "pageSize": 100,
        "key": GOOGLE_API_KEY,
    }

    async with http_session.get(url, params=params) as resp:
        if resp.status != 200:
            print("❌ Drive API error:", resp.status)
            text = await resp.text()
            print(text)
            return []

        data = await resp.json()
        files = data.get("files", [])

        print(f"🎵 Drive returned {len(files)} files")
        return files

def file_url(file_id):
    return f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={GOOGLE_API_KEY}"

# =========================
# DOWNLOAD
# =========================
async def download_file(url, filename):
    path = f"/tmp/{filename}"

    async with http_session.get(url) as resp:
        if resp.status != 200:
            print("❌ Download gagal:", resp.status)
            return None

        with open(path, "wb") as f:
            async for chunk in resp.content.iter_chunked(1024 * 512):
                f.write(chunk)

    return path

# =========================
# PLAYER LOOP
# =========================
async def play_loop(vc: discord.VoiceClient):
    print("▶ play_loop started")
    await asyncio.sleep(3)

    while True:
        if not vc.is_connected():
            print("⚠️ Voice disconnect, stop loop")
            return

        files = await get_audio_files()
        print("🎵 Files:", len(files))

        if not files:
            await asyncio.sleep(10)
            continue

        for f in files:
            if not vc.is_connected():
                return

            print("▶ Playing:", f["name"])

            path = await download_file(file_url(f["id"]), f["name"])
            if not path:
                continue

            source = discord.FFmpegPCMAudio(path)
            vc.play(source)

            while vc.is_playing():
                await asyncio.sleep(1)

            try:
                os.remove(path)
            except:
                pass

# =========================
# CONNECT VOICE
# =========================
async def connect_and_play():
    await bot.wait_until_ready()
    await asyncio.sleep(5)

    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if not channel:
        print("❌ Voice channel tidak ditemukan")
        return

    print("🔊 Connecting to voice...")
    vc = await channel.connect(reconnect=True, self_deaf=True)

    print("✅ Voice connected")
    asyncio.create_task(play_loop(vc))

# =========================
# READY
# =========================
@bot.event
async def on_ready():
    global http_session
    print(f"✅ Logged in as {bot.user}")

    timeout = aiohttp.ClientTimeout(total=180)
    http_session = aiohttp.ClientSession(timeout=timeout)

    bot.loop.create_task(connect_and_play())

# =========================
# RUN
# =========================
bot.run(DISCORD_TOKEN)
