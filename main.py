from dotenv import load_dotenv
load_dotenv()

import discord
import feedparser
import os
import yaml
import asyncio
import re

# ---------------- Discord setup ----------------
intents = discord.Intents.default()
client = discord.Client(intents=intents)

# ---------------- Environment variables ----------------
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_CHANNEL_IDS_RAW = os.getenv("DISCORD_CHANNEL_IDS")
RSS_FEED_URLS_RAW = os.getenv("RSS_FEED_URLS")

if not DISCORD_BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN is missing")

if not DISCORD_CHANNEL_IDS_RAW:
    raise ValueError("DISCORD_CHANNEL_IDS is missing")

if not RSS_FEED_URLS_RAW:
    raise ValueError("RSS_FEED_URLS is missing")

DISCORD_CHANNEL_IDS = [int(cid.strip()) for cid in DISCORD_CHANNEL_IDS_RAW.split(",")]
RSS_FEED_URLS = [url.strip() for url in RSS_FEED_URLS_RAW.split(",")]

EMOJI = "📰"
SENT_FILE = "sent_articles.yaml"

# ---------------- Helper functions ----------------
def load_sent_articles():
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r") as f:
            data = yaml.safe_load(f)
            return data if data else {}
    return {}

def save_sent_articles(data):
    with open(SENT_FILE, "w") as f:
        yaml.dump(data, f)

def clean_html(html):
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"<.*?>", "", text)
    return text.strip()

def extract_images(html):
    return re.findall(r'src="(https?://[^"]+)"', html)

# ---------------- RSS handling ----------------
async def fetch_feed(channel):
    sent_articles = load_sent_articles()

    if channel.id not in sent_articles:
        sent_articles[channel.id] = []

    for rss_url in RSS_FEED_URLS:
        feed = feedparser.parse(
            rss_url,
            request_headers={
                "User-Agent": "Mozilla/5.0 (compatible; DiscordRSSBot/1.0)"
            }
        )

        if feed.bozo:
            print(f"RSS error: {feed.bozo_exception}")
            continue

        if not feed.entries:
            continue

        entry = feed.entries[0]

        if entry.link in sent_articles[channel.id]:
            continue

        sent_articles[channel.id].append(entry.link)

        title = entry.title
        description = entry.description if hasattr(entry, "description") else ""
        text = clean_html(description)
        images = extract_images(description)

        # Send main content (clean text)
        message = f"{EMOJI} **{title}**"
        if text:
            message += f"\n{text}"

        await channel.send(message)

        # Send first image separately so Discord embeds it
        if images:
            await channel.send(images[0])

        # Optional: send source link cleanly

        print(f"Posted: {title}")

    save_sent_articles(sent_articles)

# ---------------- Discord events ----------------
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    while True:
        for channel_id in DISCORD_CHANNEL_IDS:
            channel = client.get_channel(channel_id)
            if channel:
                await fetch_feed(channel)
        await asyncio.sleep(600)  # 10  minutes

# ---------------- Start bot ----------------
print("Starting bot...")
client.run(DISCORD_BOT_TOKEN)

