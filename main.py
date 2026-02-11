import discord
from discord.ext import commands
import os
import asyncio
import aiohttp
from googleapiclient.discovery import build

# =========================
# ENV VARIABLES
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

def get_stream_url(file_id):
    return f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={GOOGLE_API_KEY}"

# =========================
# LOOP PLAYER
# =========================
async def play_loop(vc):
    await bot.wait_until_ready()

    while True:
        for file in get_audio_files():
            print(f"Playing: {file['name']}")
            url = get_stream_url(file["id"])

            source = await discord.FFmpegOpusAudio.from_probe(
                url,
                method="fallback"
            )

            vc.play(source)

            while vc.is_playing():
                await asyncio.sleep(1)

# =========================
# AUTO CONNECT
# =========================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if not channel:
        print("Voice channel tidak ditemukan")
        return

    vc = await channel.connect()
    bot.loop.create_task(play_loop(vc))

bot.run(DISCORD_TOKEN)
