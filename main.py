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

http_session: aiohttp.ClientSession | None = None


# =========================
# GOOGLE DRIVE
# =========================
async def get_audio_files():
    print("🔍 Fetching audio files from Drive...")

    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"'{FOLDER_ID}' in parents and mimeType contains 'audio/'",
        "fields": "files(id,name)",
        "pageSize": 100,
        "key": GOOGLE_API_KEY,
    }

    async with http_session.get(url, params=params) as resp:
        if resp.status != 200:
            print("❌ Drive API error:", resp.status)
            print(await resp.text())
            return []

        data = await resp.json()
        files = data.get("files", [])
        print(f"🎵 Found {len(files)} audio files")
        return files


def file_url(file_id):
    return f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={GOOGLE_API_KEY}"


# =========================
# PLAYER LOOP (STREAMING)
# =========================
async def play_loop(vc: discord.VoiceClient):
    print("▶ play_loop started")
    await asyncio.sleep(3)

    while True:
        if not vc.is_connected():
            print("⚠️ Voice disconnected")
            return

        files = await get_audio_files()

        if not files:
            print("⚠️ No files found, retry in 10s")
            await asyncio.sleep(10)
            continue

        for f in files:
            if not vc.is_connected():
                return

            stream_url = file_url(f["id"])
            print("▶ Streaming:", f["name"])

            done = asyncio.Event()

            def after_play(error):
                if error:
                    print("❌ Playback error:", error)
                done.set()

            source = discord.FFmpegOpusAudio(
                stream_url,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn"
            )

            vc.play(source, after=after_play)
            await done.wait()


# =========================
# CONNECT VOICE
# =========================
async def connect_and_play():
    await bot.wait_until_ready()
    await asyncio.sleep(3)

    channel = bot.get_channel(VOICE_CHANNEL_ID)
    if not channel:
        print("❌ Voice channel tidak ditemukan")
        return

    print("🔊 Connecting to voice...")

    vc = None
    try:
        vc = await channel.connect(reconnect=True, self_deaf=True)
    except discord.ClientException:
        vc = discord.utils.get(bot.voice_clients, guild=channel.guild)

    if not vc:
        print("❌ Gagal connect voice")
        return

    print("✅ Voice connected")

    # PENTING: jangan await
    asyncio.create_task(play_loop(vc))



# =========================
# READY
# =========================
@bot.event
async def on_ready():
    global http_session
    print(f"✅ Logged in as {bot.user}")

    timeout = aiohttp.ClientTimeout(total=60)
    http_session = aiohttp.ClientSession(timeout=timeout)

    asyncio.create_task(connect_and_play())


# =========================
# RUN
# =========================
bot.run(DISCORD_TOKEN)

