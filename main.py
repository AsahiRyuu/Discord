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
# DRIVE API (ASYNC)
# =========================
async def get_audio_files():
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"'{FOLDER_ID}' in parents and mimeType contains 'audio/'",
        "fields": "files(id,name)",
        "key": GOOGLE_API_KEY
    }

    async with http_session.get(url, params=params) as resp:
        if resp.status != 200:
            print("❌ Drive API error:", resp.status)
            return []

        data = await resp.json()
        return data.get("files", [])

def file_url(file_id):
    return f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={GOOGLE_API_KEY}"

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
# PLAYER LOOP (STABIL)
# =========================
async def play_loop(vc: discord.VoiceClient):
    print("▶ play_loop started")
    await asyncio.sleep(3)  # beri waktu voice stabil

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
# BACKGROUND CONNECT
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

    timeout = aiohttp.ClientTimeout(total=120)
    http_session = aiohttp.ClientSession(timeout=timeout)

    bot.loop.create_task(connect_and_play())

# =========================
# SHUTDOWN CLEAN
# =========================
@bot.event
async def on_close():
    if http_session:
        await http_session.close()

bot.run(DISCORD_TOKEN)
