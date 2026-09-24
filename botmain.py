import discord, os
from discord.ext import commands
from os.path import join as osjoin

intents = discord.Intents.default()
intents.message_content = True #needed to read messages


token_path = os.path.join('token.txt')
with open(token_path) as file:
    token = file.read()

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents= intents, case_insensitive= True)
    
    async def on_ready(self):
        print(f"✅ Logged in as {bot.user}")
    
    #function implement
    async def setup_hook(self):
        await self.load_extension('reply_tools')

#async def hello(ctx):
#    await ctx.send("Hello world!")


bot= Bot()
bot.run(token)