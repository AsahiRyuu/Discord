import discord
from discord.ext import commands
import os
import asyncio
from googleapiclient.discovery import build
import functools

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
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =========================
# GOOGLE DRIVE (SYNC)
# =========================
def fetch_audio_files_sync():
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
# ASYNC WRAPPER (ANTI BLOCK)
# =========================
async def get_audio_files():
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, fetch_audio_files_sync)

# =========================
# PLAYER LOOP
# =========================
async def play_loop(vc):
    await bot.wait_until_ready()
    print("Play loop started")

    while True:
        files = await get_audio_files()
        print("Jumlah lagu:", len(files))

        if not files:
            await asyncio.sleep(10)
            continue

        for file in files:
            print(f"Playing: {file['name']}")

            url = get_stream_url(file["id"])

            source = await discord.FFmpegOpusAudio.from_probe(
                url,
                method="fallback",
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
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

    await asyncio.sleep(5)

    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if not channel:
        print("Voice channel tidak ditemukan")
        return

    if channel.guild.voice_client:
        print("Sudah connect ke voice")
        return

    vc = await channel.connect(
        reconnect=True,
        self_deaf=True
    )

    print("Voice connected, starting play loop")
    asyncio.create_task(play_loop(vc))

# =========================
# RUN
# =========================
bot.run(DISCORD_TOKEN)
