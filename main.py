import discord
from discord.ext import commands
import os
import asyncio
import aiohttp
import shutil
from googleapiclient.discovery import build

# =========================
# DETECT FFMPEG
# =========================
FFMPEG_PATH = shutil.which("ffmpeg")
print("FFMPEG PATH:", FFMPEG_PATH)

if not FFMPEG_PATH:
    raise RuntimeError("FFmpeg tidak ditemukan di environment")

# =========================
# ENV VARIABLES (Railway)
# =========================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
FOLDER_ID = os.getenv("FOLDER_ID")
VOICE_CHANNEL_ID = int(os.getenv("VOICE_CHANNEL_ID"))

# =========================
# DISCORD SETUP
# =========================
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# GOOGLE DRIVE
# =========================
def get_audio_files():
    service = build("drive", "v3", developerKey=GOOGLE_API_KEY)

    query = f"'{FOLDER_ID}' in parents and mimeType contains 'audio/'"

    results = service.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()

    return results.get("files", [])

def get_download_url(file_id):
    return f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={GOOGLE_API_KEY}"

# =========================
# DOWNLOAD FILE TEMP
# =========================
async def download_file(url, filename):
    path = f"/tmp/{filename}"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                with open(path, "wb") as f:
                    f.write(await resp.read())
                return path
    return None

# =========================
# LOOP PLAYER
# =========================
async def play_loop(vc):
    await bot.wait_until_ready()

    while True:
        files = get_audio_files()

        if not files:
            print("Folder kosong.")
            await asyncio.sleep(15)
            continue

        for file in files:
            print(f"Playing: {file['name']}")
            url = get_download_url(file["id"])

            filepath = await download_file(url, file["name"])
            if not filepath:
                continue

            source = discord.FFmpegPCMAudio(
                filepath,
                executable=FFMPEG_PATH
            )

            vc.play(source)

            while vc.is_playing():
                await asyncio.sleep(1)

            try:
                os.remove(filepath)
            except:
                pass

# =========================
# AUTO CONNECT
# =========================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if not channel:
        print("Voice channel tidak ditemukan.")
        return

    vc = await channel.connect()
    bot.loop.create_task(play_loop(vc))

# =========================
# RUN
# =========================
bot.run(DISCORD_TOKEN)
