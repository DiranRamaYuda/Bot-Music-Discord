import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from dotenv import load_dotenv
import urllib.parse, urllib.request, re

def run_bot():
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    intents = discord.Intents.default()
    intents.message_content = True
    client = commands.Bot(command_prefix=".", intents=intents) # lakukan perintah dengan mengetikan ".(bot komen)" untuk menjalan bot

    queues = {}
    voice_clients = {}
    youtube_base_url = 'https://www.youtube.com/'
    youtube_results_url = youtube_base_url + 'results?'
    youtube_watch_url = youtube_base_url + 'watch?v='
    yt_dl_options = {"format": "bestaudio/best"}
    ytdl = yt_dlp.YoutubeDL(yt_dl_options)

    FFMPEG_EXECUTABLE = "C:/ffmpeg/bin/ffmpeg.exe"
    
    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn -filter:a "volume=0.25"',
        'executable': FFMPEG_EXECUTABLE
    }

    @client.event
    async def on_ready():
        print(f'{client.user} Sudah On')

    async def play_next(ctx):
        if queues[ctx.guild.id] != []:
            link = queues[ctx.guild.id].pop(0)
            await gas(ctx, link=link)

    # jalankan bot dengan perindah .gas (nama lagu)
    @client.command(name="gas")
    async def gas(ctx, *, link):
        try:
            if ctx.author.voice is None:
                await ctx.send("Kamu harus berada di voice channel!")
                return

            voice_client = await ctx.author.voice.channel.connect()
            voice_clients[voice_client.guild.id] = voice_client
        except Exception as e:
            print(e)

        try:
            if youtube_base_url not in link:
                query_string = urllib.parse.urlencode({'search_query': link})
                content = urllib.request.urlopen(youtube_results_url + query_string)
                search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
                link = youtube_watch_url + search_results[0]

            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(link, download=False))

            song = data['url']
            title = data.get('title', 'Tidak diketahui')
            duration = data.get('duration', 0)
            thumbnail = data.get('thumbnail')

            minutes, second = divmod(duration, 60)
            duration_formatted = f"{minutes}:{second:02d}"

            embed = discord.Embed (
                title="Playing Song:",
                description=f"[{title}]({link})",
                color=discord.Color.dark_purple()
            )
            embed.set_thumbnail(url=thumbnail)
            embed.add_field(name="Request by:", value=ctx.author.mention, inline=True)
            embed.add_field(name="Duration:", value=duration_formatted, inline=True)

            await ctx.send(embed=embed)

            player = discord.FFmpegOpusAudio(song, **ffmpeg_options)
            voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), client.loop))           
        except Exception as e:
            print(e)

    # membersihkan antrian lagu dengan perintah .bersihkan
    @client.command(name="bersihkan")
    async def bersihkan(ctx):
        if ctx.guild.id in queues:
            queues[ctx.guild.id].clear()
            await ctx.send("Antrian dibersihkan!")
        else:
            await ctx.send("Tidak ada antrian untuk lagu apa pun")

    # pause bot dengan perintah .bentar
    @client.command(name="bentar")
    async def bentar(ctx):
        try:
            voice_clients[ctx.guild.id].pause()
        except Exception as e:
            print(e)

    # melanjutkan bot dengan perintah .lanjut
    @client.command(name="lanjut")
    async def lanjut(ctx):
        try:
            voice_clients[ctx.guild.id].resume()
        except Exception as e:
            print(e)

    # menghentikan bot dengan pertintah .udah
    @client.command(name="udah")
    async def udah(ctx):
        try:
            voice_clients[ctx.guild.id].stop()
            await voice_clients[ctx.guild.id].disconnect()
            del voice_clients[ctx.guild.id]
        except Exception as e:
            print(e)

    # menambahkan antrian lagu dengan perintah .antri (nama lagu)
    @client.command(name="antri")
    async def antri(ctx, *, url):
        if ctx.guild.id not in queues:
            queues[ctx.guild.id] = []

        if youtube_base_url not in url:
            query_string = urllib.parse.urlencode({'search_query': url})
            content = urllib.request.urlopen(youtube_results_url + query_string)
            search_results = re.findall(r'/watch\?v=(.{11})', content.read().decode())
            url = youtube_watch_url + search_results[0]

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

        song = data['url']
        title = data.get('title', 'Tidak diketahui')
        duration = data.get('duration', 0)

        minutes, second = divmod(duration, 60)
        duration_formatted = f"{minutes}:{second:02d}"

        queues[ctx.guild.id].append({"title": title, "duration": duration_formatted, "url": url})
        await ctx.send(f"Ditambahkan ke antrian: **{title}** ({duration_formatted})")

        embed = discord.Embed(
            title="Antrian",
            color=discord.Color.dark_purple()
        )

        for i, song in enumerate(queues[ctx.guild.id], 1):
            embed.add_field(name=f"{i}. {song['song']}", value=f"{song['duration']}", inline=False)

        embed.set_footer(text=f'Request by {ctx.author}')
        await ctx.send(embed=embed)

    client.run(TOKEN)
