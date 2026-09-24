import discord, os, unwrap_openai, openai, asyncio, json
from meme_generator import MemeGenerator
from discord.ext import commands
from os.path import join as osjoin
from unwrap_openai import GPT5Deployment, ReasoningEffort 
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional

meme_gen = MemeGenerator()

class Get_Memes(BaseModel):
    """Search Pinecone for Reddit memes related and unrelated to the current conversation"""
    content: str = Field(..., description="The current conversation to match against memes")  

    def execute(self)-> dict[str, Any]:
        print("getting meme")
        return meme_gen.generate_best(self.content)



def execute_tool_call(tool_call, tools: dict[str, type[BaseModel]]):
    import json
    """Execute a tool.
    Args:
        tool_call: The tool call from OpenAI response
        tools: Dict mapping tool names to tool classes

    Return:
        Result of the tool execution    
    """

    tool_name = tool_call.function.name
    if tool_name not in tools:
        return("ERROR: Get_Memes not in tools")
    print("executing...")
    try:
        # Parse arguments and create tool instance
        args = json.loads(tool_call.function.arguments or "{}")
        tool_instance = tools[tool_name](**args)
        return tool_instance.execute() if hasattr(tool_instance, "execute") else {"error": f"{tool_name} missing execute"}
        # Execute the tool if it has an execute method
    except Exception as e:
        return {"error": f"Error executing tool {tool_name}: {str(e)}"}

    
class reply(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name= "Ping!")
    async def Ping(self, ctx:commands.Context):
        await ctx.send("Pong!")

    @commands.Cog.listener()
    async def on_message(self, message):
        # ignore your own messages
        if message.author.id == self.bot.user.id:
            return
        
        content = str(message.content).lower()
        file_path = osjoin(os.getcwd(), "messages.json")

        try:
            # Create new message entry
            new_message = {
                #
                "role": "user",
                "content": f"User {message.author.name}: {content}"
            }
            
            # Load existing messages or create empty list
            messages = []
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    messages = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                messages = []
        except Exception as e:
            print(f"Error loading message: {e}")
        
        #start of ungift command
        if content.startswith('dankrank'):
            #read last 10 messages
            with open(file_path, "r", encoding="utf-8") as f:
                conversation = json.load(f)

            #add instructions
            conversation = [
                {
                "role": "system","content": "You are meme bot."},
                *conversation[-10:]
            ]

            #get and print the ai response
            response = await unwrap_openai.create_openai_completion(conversation,tools=[Get_Memes], tool_choice="required")

            #check if ai wants to use a tool
            tool_calls = response.choices[0].message.tool_calls or []
            if tool_calls:
                print("Attempting to get memes")
                tools = {"Get_Memes": Get_Memes}
                
                for tool_call in tool_calls:
                    #execute Get_Memes
                    result = execute_tool_call(tool_call, tools)      
                    await message.reply(result)                                
            #if it doesn't then print a message
            else:
                await message.reply(response.choices[0].message.content or "Sorry, there was an error...")
        else:
            # Add new message and keep only last 10 
            messages.append(new_message)
            messages = messages[-3:]

        try:
            # Save updated messages
            loop = asyncio.get_running_loop()
            def _save():
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(messages, f, indent=2)
            await loop.run_in_executor(None, _save)
        except Exception as e:
            print(f"Error saving message: {e}")




async def setup(bot:commands.bot):
    await bot.add_cog(reply(bot))