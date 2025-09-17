import asyncio
import base64
import os
from queue import Empty
from uuid import uuid4

import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv

from twitter_extractor import TwitterScraper

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
CHANNEL_ID_IMAGES = int(os.getenv("CHANNEL_ID_IMAGES", 0))
CHANNEL_ID_NOTES = int(os.getenv("CHANNEL_ID_NOTES", 0))
CHANNEL_ID_QUERY = int(os.getenv("CHANNEL_ID_QUERY", 0))
CHANNEL_ID_LOGS = int(os.getenv("CHANNEL_ID_LOGS", 0))
API_URL = os.getenv("API_URL", "http://localhost:5000/")
# === CONFIGURATION ===
CHANNEL_ID_TO_WATCH = [CHANNEL_ID_NOTES, CHANNEL_ID_IMAGES, CHANNEL_ID_QUERY]


# === BOT SETUP ===
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)
intents = discord.Intents.all()

class MyBot(commands.Bot):
	async def setup_hook(self):
		# C'est ici qu'on démarre les tâches de fond
		self.loop.create_task(result_dispatcher())

bot = MyBot(command_prefix="!", intents=intents)

# === Twitter Scraper ===
scraper = TwitterScraper()
scraper.start()


# === API CALL FUNCTION ===

async def result_dispatcher():
	await bot.wait_until_ready()
	print("[OK] Result dispatcher started.")

	while not bot.is_closed():
		try:
			result = scraper.result_queue.get(timeout=5)
			print(f"[OK] New result: {result}")

			if result['status'] == 'failure':
				print(f"[ERROR] Failed {result['tweet_url']} after {result['retries']} retries.")
				continue
			else:
				print(f"[OK] Successfully processed tweet {result['tweet_url']}.")
				images = result.get('images', [])
				b64_imgs = result.get('base64_images', [])
				filenames = result.get('filenames', [])
				for image, base64_image, filename in zip(images, b64_imgs, filenames, strict=False):
					await add_data(filename, image, base64_image, db_name="image_embeddings")
					#await reload_data("image_embeddings")

			# Exemple ultra-simple : broadcast sur tous les channels
			for guild in bot.guilds:
				for channel in guild.text_channels:
					if channel.id == CHANNEL_ID_LOGS:
						try:
							await channel.send(
								f"Résultat pour: {result['status'].upper()} - {result['message']}")
						except Exception as e:
							print(f"[ERROR] Could not send message in {channel}: {e}")

		except Empty:
			await asyncio.sleep(30)
	scraper.stop()



async def reload_data(db_name):
	"""
	Recharge les données de la DB spécifiée.
	Exemple: POST /reload/notes
	"""
	API_URL_ENDPOINT = f"{API_URL}reload/{db_name}"

	async with aiohttp.ClientSession() as session:
		async with session.post(API_URL_ENDPOINT) as resp:
			if resp.status != 200:
				print(f"Erreur API {resp.status}")
			else:
				print(f"[OK] Données rechargées pour {db_name}")


async def add_data(author, content, timestamp, db_name="notes"):
	# On détermine quelle bdd utiliser
	# Si y'a un tweet, on get une image donc on utilise la bdd "images"
	API_ENDPOINT = f"{API_URL}add_data/{db_name}"

	if db_name == "image_embeddings":
		print(f"[INFO] Adding image data to {db_name} database")
		print(f"[INFO] Image content: {content[:50]}...")  # Log first 50 chars for brevity
		print(f"[INFO] Author: {author}, Timestamp: {timestamp[:50]}")
		payload = {
			"filepath": content,
			"base64": timestamp,
			"file_name": author
		}
	else:
		payload = {
			"content": content,
			"author": author,
			"timestamp": str(timestamp)
		}

	async with aiohttp.ClientSession() as session:
		async with session.post(API_ENDPOINT, json=payload) as resp:
			if resp.status != 200:
				print(f"Erreur API {resp.status}, message = {resp.reason}")
			else:
				print("[OK] Message envoyé à l'API")

# === EVENT HANDLER ===
@bot.event
async def on_message(message):
	if message.author.bot:
		return

	if message.channel.id not in CHANNEL_ID_TO_WATCH and not message.content.startswith("!"):
		return

	is_tweet = "twitter.com" in message.content or "x.com" in message.content
	if message.channel.id == CHANNEL_ID_IMAGES and is_tweet:
		scraper.add_url(message.content)
		await message.add_reaction("✅")
	elif message.channel.id == CHANNEL_ID_NOTES:
		# Log local
		content = message.content.strip().replace("'", " ").replace('"', " ")
		# Appel à l'API
		await add_data(
			author=str(message.author),
			content=content,
			timestamp=message.created_at
		)
	elif message.channel.id == CHANNEL_ID_QUERY:
		# Log local
		content = message.content.strip().replace("'", " ").replace('"', " ")
		payload = {
			"question": content
		}

		async with aiohttp.ClientSession() as session:
			async with session.post(API_URL + "query", json=payload) as resp:
				if resp.status != 200:
					print(f"Erreur API {resp.status}, message = {resp.reason}")
					await message.channel.send(f"❌ Erreur lors de la requête : {resp.reason}")
				else:
					print("[OK] Message envoyé à l'API")
					response = await resp.json()
					image = response.get("image")
					if image:
						files = []
						files_path = []
						for img_path in image:
							# On sauvegarde l'image dans le dossier local
							uuid_name = uuid4()
							img_path2 = os.path.join("./data/", f"{uuid_name}.jpg")
							files_path.append(img_path2)
							with open(img_path2, "wb+") as img_file:
								img_file.write(base64.b64decode(img_path))
							files.append(discord.File(img_path2))

						await message.channel.send(content="[RESP] Images trouvées", files=files)
						for img_path in files_path:
							os.remove(img_path)
					else:
						await message.channel.send(f"""[INFO] Résultat: {response['result']}""")
	await bot.process_commands(message)


@bot.command(name="reload")
async def reload(ctx, db_name: str):
	"""
	Commande pour recharger les données d'une base de données.
	Usage: !reload <db_name>
	"""
	if ctx.channel.id != CHANNEL_ID_LOGS:
		await ctx.send("[ERROR] Cette commande ne peut être utilisée que dans le channel de logs.")
		return

	await reload_data(db_name)
	await ctx.send(f"[OK] Données rechargées pour {db_name}.")


@bot.command(name="batch")
async def batch(ctx):
	"""
	Commande pour traiter les tweets en batch.
	Usage: !batch
	"""
	if ctx.channel.id != CHANNEL_ID_LOGS:
		await ctx.send("[ERROR] Cette commande ne peut être utilisée que dans le channel de logs.")
		return

	await ctx.send("[RELOAD] Traitement des tweets en cours...")
	for guild in bot.guilds:
		for channel in guild.text_channels:
			if client.user in channel.members or channel.permissions_for(guild.me).read_messages:
				if channel.id not in CHANNEL_ID_TO_WATCH:
					continue
				async for message in channel.history(limit=None, oldest_first=True):
					if message.author.bot:
						continue
					if "twitter.com" in message.content or "x.com" in message.content:
						scraper.add_url(message.content)
					else:
						# Log local
						print(f"[LOG] {message.author} a écrit : {message.content}")

						# Appel à l'API
						await add_data(
							author=str(message.author),
							content=message.content,
							timestamp=message.created_at
						)

	await ctx.send("[OK] Traitement des tweets terminé.")

# === LANCEMENT DU BOT ===

if __name__ == "__main__":
	# Lancer le bot Discord
	bot.run(TOKEN)
