import discord
from discord.ext import commands
import os
import asyncio
import aiohttp
from googleapiclient.discovery import build

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
# GOOGLE DRIVE (SYNC)
# =========================
def fetch_files_sync():
    service = build("drive", "v3", developerKey=GOOGLE_API_KEY)
    query = f"'{FOLDER_ID}' in parents and mimeType contains 'audio/'"
    res = service.files().list(
        q=query,
        fields="files(id,name)"
    ).execute()
    return res.get("files", [])

def file_url(file_id):
    return f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={GOOGLE_API_KEY}"

# =========================
# ASYNC WRAPPER (ANTI BLOCK)
# =========================
async def get_files():
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, fetch_files_sync)

async def download_file(url, filename):
    path = f"/tmp/{filename}"

    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            with open(path, "wb") as f:
                async for chunk in resp.content.iter_chunked(1024 * 512):
                    f.write(chunk)
    return path

# =========================
# PLAYER LOOP (SAFE)
# =========================
async def play_loop(vc):
    print("▶ play_loop started")
    await asyncio.sleep(2)  # <<< PENTING: kasih napas ke event loop

    while True:
        files = await get_files()
        print("🎵 Jumlah lagu:", len(files))

        if not files:
            await asyncio.sleep(10)
            continue

        for f in files:
            print("▶ Playing:", f["name"])

            url = file_url(f["id"])
            path = await download_file(url, f["name"])
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
# READY
# =========================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    await asyncio.sleep(5)  # stabilkan gateway

    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if not channel:
        print("❌ Channel tidak ditemukan")
        return

    if channel.guild.voice_client:
        print("ℹ️ Sudah connect voice")
        return

    vc = await channel.connect(reconnect=True, self_deaf=True)
    print("🔊 Voice connected")

    # PENTING: create task terpisah
    asyncio.create_task(play_loop(vc))

bot.run(DISCORD_TOKEN)
