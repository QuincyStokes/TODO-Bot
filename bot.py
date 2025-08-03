#!/usr/bin/env python3
"""
Discord Todo Bot

A Discord bot for managing todo lists with interactive features.
Supports creating, managing, and sharing todo lists within Discord servers.
"""

# Import audioop patch first to prevent import errors
import patch_audioop

import asyncio
import logging
import os
import threading
import time
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks
from flask import Flask

import config
from todo_manager import TodoManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app for health check
app = Flask(__name__)


@app.route('/')
def health_check():
    """Health check endpoint for Render deployment."""
    return "Discord Bot is running! 🚀"


@app.route('/health')
def health():
    """Detailed health check endpoint."""
    return {"status": "healthy", "bot": "running", "timestamp": time.time()}


def run_flask():
    """Run Flask server in a separate thread for Render port binding."""
    try:
        port = int(os.environ.get('PORT', 10000))
        logger.info(f"Starting Flask server on port {port}")
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Flask server error: {e}")


class TodoBot(commands.Bot):
    """Main Discord bot class for todo list management."""
    
    def __init__(self):
        """Initialize the bot with proper intents and todo manager."""
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(command_prefix="!", intents=intents)
        self.todo_manager = TodoManager()
        self.last_heartbeat = time.time()
        self.connection_attempts = 0
        self.max_reconnect_attempts = 5
        
    async def setup_hook(self):
        """Setup hook called when bot is ready."""
        try:
            await self.tree.sync()
            logger.info("Bot is ready!")
            self.heartbeat.start()
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")
    
    @tasks.loop(minutes=1)
    async def heartbeat(self):
        """Send periodic heartbeat to keep connection alive."""
        try:
            if self.is_ready():
                self.last_heartbeat = time.time()
                logger.debug("Heartbeat sent")
            else:
                logger.warning("Bot not ready during heartbeat")
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
    
    @heartbeat.before_loop
    async def before_heartbeat(self):
        """Wait until bot is ready before starting heartbeat."""
        await self.wait_until_ready()
    
    async def on_disconnect(self):
        """Handle bot disconnection."""
        logger.warning("Bot disconnected from Discord")
        self.heartbeat.cancel()
    
    async def on_connect(self):
        """Handle bot connection."""
        logger.info("Bot connected to Discord")
        self.connection_attempts = 0
    
    async def on_resumed(self):
        """Handle bot resumption."""
        logger.info("Bot resumed connection to Discord")
    
    async def on_error(self, event_method: str, *args, **kwargs):
        """Handle bot errors."""
        logger.error(f"Error in {event_method}: {args} {kwargs}")
    
    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return
        logger.error(f"Command error: {error}")
        await ctx.send(f"❌ An error occurred: {str(error)}")


bot = TodoBot()


class TodoItemView(discord.ui.View):
    """Interactive view for individual todo items."""
    
    def __init__(self, todo_list, item_index):
        """Initialize the view with a specific todo item."""
        super().__init__(timeout=300)  # 5 minute timeout
        self.todo_list = todo_list
        self.item_index = item_index
        self.item = todo_list.items[item_index]
        
    @discord.ui.button(label="Toggle", style=discord.ButtonStyle.primary, custom_id="toggle")
    async def toggle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle the completion status of an item."""
        success = bot.todo_manager.toggle_item_in_list(
            self.todo_list.list_id, 
            self.item.item_id, 
            str(interaction.user.id)
        )
        
        if success:
            # Update the item reference
            self.item = self.todo_list.items[self.item_index]
            
            # Update button label
            toggle_label = "✅ Mark Complete" if not self.item.completed else "⭕ Mark Incomplete"
            button.label = toggle_label
            
            status = "completed" if self.item.completed else "uncompleted"
            await interaction.response.edit_message(
                content=f"✅ Item {self.item_index + 1} marked as {status} in **{self.todo_list.name}**",
                view=self
            )
        else:
            await interaction.response.send_message("❌ Failed to toggle item", ephemeral=True)
    
    @discord.ui.button(label="🗑️ Remove", style=discord.ButtonStyle.danger, custom_id="remove")
    async def remove_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove an item from the todo list."""
        success = bot.todo_manager.remove_item_from_list(self.todo_list.list_id, self.item.item_id)
        
        if success:
            await interaction.response.edit_message(
                content=f"✅ Removed item {self.item_index + 1} from **{self.todo_list.name}**",
                view=None
            )
        else:
            await interaction.response.send_message("❌ Failed to remove item", ephemeral=True)


class InteractiveTodoListView(discord.ui.View):
    """Interactive view for todo lists with individual item toggles."""
    
    def __init__(self, todo_list):
        """Initialize the view with a todo list."""
        super().__init__(timeout=300)  # 5 minute timeout
        self.todo_list = todo_list
        self._create_item_buttons()
    
    def _create_item_buttons(self):
        """Create individual toggle buttons for each item."""
        # Clear existing buttons (except Add and Refresh)
        self.clear_items()
        
        # Add Add Item and Refresh buttons first
        self.add_item(AddItemButton(self.todo_list))
        self.add_item(RefreshButton(self.todo_list))
        
        # Add individual toggle buttons for each item
        for i, item in enumerate(self.todo_list.items):
            button = ItemToggleButton(self.todo_list, i, item)
            self.add_item(button)


class ItemToggleButton(discord.ui.Button):
    """Individual toggle button for each todo item."""
    
    def __init__(self, todo_list, item_index, item):
        """Initialize the button with item state."""
        # Set button label based on current state
        label = f"{item_index + 1}. {'✅' if item.completed else '⭕'}"
        style = discord.ButtonStyle.success if item.completed else discord.ButtonStyle.secondary
        
        super().__init__(
            label=label,
            style=style,
            custom_id=f"toggle_item_{item_index}"
        )
        self.todo_list = todo_list
        self.item_index = item_index
        self.item = item
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click to toggle item completion."""
        success = bot.todo_manager.toggle_item_in_list(
            self.todo_list.list_id, 
            self.item.item_id, 
            str(interaction.user.id)
        )
        
        if success:
            # Update the item reference
            self.item = self.todo_list.items[self.item_index]
            
            # Update button label and style
            self.label = f"{self.item_index + 1}. {'✅' if self.item.completed else '⭕'}"
            self.style = discord.ButtonStyle.success if self.item.completed else discord.ButtonStyle.secondary
            
            # Update the entire view
            new_view = InteractiveTodoListView(self.todo_list)
            embed = create_todo_list_embed(self.todo_list)
            
            await interaction.response.edit_message(embed=embed, view=new_view)
        else:
            await interaction.response.send_message("❌ Failed to toggle item", ephemeral=True)


class AddItemButton(discord.ui.Button):
    """Button to add new items to a todo list."""
    
    def __init__(self, todo_list):
        """Initialize the add item button."""
        super().__init__(
            label="➕ Add Item",
            style=discord.ButtonStyle.success,
            custom_id="add_item"
        )
        self.todo_list = todo_list
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click to show add item modal."""
        await interaction.response.send_modal(AddItemModal(self.todo_list))


class RefreshButton(discord.ui.Button):
    """Button to refresh the todo list display."""
    
    def __init__(self, todo_list):
        """Initialize the refresh button."""
        super().__init__(
            label="🔄 Refresh",
            style=discord.ButtonStyle.secondary,
            custom_id="refresh"
        )
        self.todo_list = todo_list
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click to refresh the display."""
        embed = create_todo_list_embed(self.todo_list)
        new_view = InteractiveTodoListView(self.todo_list)
        await interaction.response.edit_message(embed=embed, view=new_view)


class TodoListView(discord.ui.View):
    """Legacy view for todo lists (kept for compatibility)."""
    
    def __init__(self, todo_list):
        """Initialize the legacy view."""
        super().__init__(timeout=300)  # 5 minute timeout
        self.todo_list = todo_list
        
    @discord.ui.button(label="➕ Add Item", style=discord.ButtonStyle.success, custom_id="add_item")
    async def add_item_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle add item button click."""
        await interaction.response.send_modal(AddItemModal(self.todo_list))
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary, custom_id="refresh")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle refresh button click."""
        embed = create_todo_list_embed(self.todo_list)
        await interaction.response.edit_message(embed=embed, view=self)


class AddItemModal(discord.ui.Modal, title="Add Todo Item"):
    """Modal for adding new items to a todo list."""
    
    def __init__(self, todo_list):
        """Initialize the modal with a todo list."""
        super().__init__()
        self.todo_list = todo_list
        
    item_content = discord.ui.TextInput(
        label="Item Description",
        placeholder="Enter the todo item...",
        required=True,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission to add the item."""
        content = self.item_content.value
        new_item = bot.todo_manager.add_item_to_list(
            self.todo_list.list_id, 
            content, 
            str(interaction.user.id)
        )
        
        if new_item:
            await interaction.response.send_message(
                f"✅ Added item to **{self.todo_list.name}**: {content}", 
                ephemeral=True
            )
            # Update the original message with the new list
            embed = create_todo_list_embed(self.todo_list)
            view = InteractiveTodoListView(self.todo_list)
            await interaction.message.edit(embed=embed, view=view)
        else:
            await interaction.response.send_message("❌ Failed to add item", ephemeral=True)


def create_todo_list_embed(todo_list) -> discord.Embed:
    """Create an embed for displaying a todo list.
    
    Args:
        todo_list: The TodoList object to display
        
    Returns:
        discord.Embed: Formatted embed for the todo list
    """
    embed = discord.Embed(
        title=f"📋 {todo_list.name}",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    
    if not todo_list.items:
        embed.description = "This list is empty. Click 'Add Item' to get started!"
        return embed
    
    # Calculate completion stats
    completed_count = sum(1 for item in todo_list.items if item.completed)
    total_count = len(todo_list.items)
    completion_percentage = (completed_count / total_count) * 100 if total_count > 0 else 0
    
    embed.description = f"**Progress:** {completed_count}/{total_count} completed ({completion_percentage:.1f}%)"
    
    # Add items to embed
    for i, item in enumerate(todo_list.items, 1):
        status = "✅" if item.completed else "⭕"
        
        embed.add_field(
            name=f"{i}. {status} {item.content}",
            value="",  # Empty value for cleaner look
            inline=False
        )
    
    return embed


# Bot Commands
@bot.tree.command(name="create", description="Create a new todo list")
@app_commands.describe(name="Name of the todo list")
async def create_list(interaction: discord.Interaction, name: str):
    """Create a new todo list in the current server."""
    try:
        guild_id = str(interaction.guild_id)
        
        # Check if list already exists in this guild
        existing_list = bot.todo_manager.get_list_by_name(name, guild_id)
        if existing_list:
            await interaction.response.send_message(
                f"❌ A todo list named '{name}' already exists in this server!", 
                ephemeral=True
            )
            return
        
        # Create new list
        todo_list = bot.todo_manager.create_list(name, str(interaction.user.id), guild_id)
        await interaction.response.send_message(f"✅ Created todo list: **{name}**", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error creating todo list: {str(e)}", ephemeral=True)


@bot.tree.command(name="add", description="Add an item to a todo list")
@app_commands.describe(list_name="Name of the todo list", item="The todo item to add")
async def add_item(interaction: discord.Interaction, list_name: str, item: str):
    """Add an item to a specific todo list."""
    try:
        guild_id = str(interaction.guild_id)
        
        # Find the list in this guild
        todo_list = bot.todo_manager.get_list_by_name(list_name, guild_id)
        if not todo_list:
            await interaction.response.send_message(
                f"❌ Todo list '{list_name}' not found in this server!", 
                ephemeral=True
            )
            return
        
        # Add item
        new_item = bot.todo_manager.add_item_to_list(todo_list.list_id, item, str(interaction.user.id))
        await interaction.response.send_message(f"✅ Added item to **{list_name}**: {item}", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error adding item: {str(e)}", ephemeral=True)


@bot.tree.command(name="remove", description="Remove an item from a todo list")
@app_commands.describe(list_name="Name of the todo list", item_number="Number of the item to remove (1, 2, 3, etc.)")
async def remove_item(interaction: discord.Interaction, list_name: str, item_number: int):
    """Remove an item from a specific todo list."""
    try:
        guild_id = str(interaction.guild_id)
        
        # Find the list in this guild
        todo_list = bot.todo_manager.get_list_by_name(list_name, guild_id)
        if not todo_list:
            await interaction.response.send_message(
                f"❌ Todo list '{list_name}' not found in this server!", 
                ephemeral=True
            )
            return
        
        # Check if item number is valid
        if item_number < 1 or item_number > len(todo_list.items):
            await interaction.response.send_message(
                f"❌ Invalid item number. The list has {len(todo_list.items)} items.", 
                ephemeral=True
            )
            return
        
        # Remove item
        item_to_remove = todo_list.items[item_number - 1]
        success = bot.todo_manager.remove_item_from_list(todo_list.list_id, item_to_remove.item_id)
        
        if success:
            await interaction.response.send_message(f"✅ Removed item {item_number} from **{list_name}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to remove item", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error removing item: {str(e)}", ephemeral=True)


@bot.tree.command(name="toggle", description="Toggle completion status of an item")
@app_commands.describe(list_name="Name of the todo list", item_number="Number of the item to toggle (1, 2, 3, etc.)")
async def toggle_item(interaction: discord.Interaction, list_name: str, item_number: int):
    """Toggle completion status of an item."""
    try:
        guild_id = str(interaction.guild_id)
        
        # Find the list in this guild
        todo_list = bot.todo_manager.get_list_by_name(list_name, guild_id)
        if not todo_list:
            await interaction.response.send_message(
                f"❌ Todo list '{list_name}' not found in this server!", 
                ephemeral=True
            )
            return
        
        # Check if item number is valid
        if item_number < 1 or item_number > len(todo_list.items):
            await interaction.response.send_message(
                f"❌ Invalid item number. The list has {len(todo_list.items)} items.", 
                ephemeral=True
            )
            return
        
        # Toggle item
        item_to_toggle = todo_list.items[item_number - 1]
        success = bot.todo_manager.toggle_item_in_list(
            todo_list.list_id, 
            item_to_toggle.item_id, 
            str(interaction.user.id)
        )
        
        if success:
            status = "completed" if item_to_toggle.completed else "uncompleted"
            await interaction.response.send_message(
                f"✅ Item {item_number} marked as {status} in **{list_name}**", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Failed to toggle item", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error toggling item: {str(e)}", ephemeral=True)


@bot.tree.command(name="list", description="Show all todo lists")
async def list_lists(interaction: discord.Interaction):
    """Show all available todo lists in this server."""
    try:
        guild_id = str(interaction.guild_id)
        todo_lists = bot.todo_manager.get_all_lists(guild_id)
        
        if not todo_lists:
            await interaction.response.send_message(
                "📝 No todo lists found in this server. Create one with `/create`!", 
                ephemeral=True
            )
            return
        
        embed = discord.Embed(title="📋 Todo Lists", color=discord.Color.blue())
        
        for todo_list in todo_lists:
            completed_count = sum(1 for item in todo_list.items if item.completed)
            total_count = len(todo_list.items)
            
            status = f"{completed_count}/{total_count} completed"
            if total_count == 0:
                status = "Empty"
            
            embed.add_field(
                name=f"📝 {todo_list.name}",
                value=f"Items: {status}\nCreated by: <@{todo_list.created_by}>",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error listing todo lists: {str(e)}", ephemeral=True)


@bot.tree.command(name="show", description="Show items in a specific todo list")
@app_commands.describe(list_name="Name of the todo list to show")
async def show_list(interaction: discord.Interaction, list_name: str):
    """Show items in a specific todo list with interactive buttons."""
    try:
        guild_id = str(interaction.guild_id)
        
        # Find the list in this guild
        todo_list = bot.todo_manager.get_list_by_name(list_name, guild_id)
        if not todo_list:
            await interaction.response.send_message(
                f"❌ Todo list '{list_name}' not found in this server!", 
                ephemeral=True
            )
            return
        
        # Create embed and view
        embed = create_todo_list_embed(todo_list)
        view = InteractiveTodoListView(todo_list)
        
        # Send publicly (not ephemeral)
        await interaction.response.send_message(embed=embed, view=view)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error showing todo list: {str(e)}", ephemeral=True)


@bot.tree.command(name="pin", description="Pin a todo list to the channel for persistent display")
@app_commands.describe(list_name="Name of the todo list to pin")
async def pin_list(interaction: discord.Interaction, list_name: str):
    """Pin a todo list to the channel for persistent display."""
    try:
        guild_id = str(interaction.guild_id)
        
        # Find the list in this guild
        todo_list = bot.todo_manager.get_list_by_name(list_name, guild_id)
        if not todo_list:
            await interaction.response.send_message(
                f"❌ Todo list '{list_name}' not found in this server!", 
                ephemeral=True
            )
            return
        
        # Create embed and view
        embed = create_todo_list_embed(todo_list)
        view = InteractiveTodoListView(todo_list)
        
        # Send as a pinned message (public)
        message = await interaction.channel.send(embed=embed, view=view)
        
        # Pin the message if possible
        try:
            await message.pin()
            await interaction.response.send_message(
                f"✅ Pinned todo list **{list_name}** to the channel!", 
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                f"✅ Posted todo list **{list_name}** to the channel! "
                "(Note: Bot doesn't have permission to pin messages)", 
                ephemeral=True
            )
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error pinning todo list: {str(e)}", ephemeral=True)


@bot.tree.command(name="debug", description="List all registered commands (debug)")
async def debug_commands(interaction: discord.Interaction):
    """List all registered commands for debugging."""
    try:
        embed = discord.Embed(title="🔧 Registered Commands", color=discord.Color.blue())
        
        for cmd in bot.tree.get_commands():
            embed.add_field(
                name=f"/{cmd.name}",
                value=f"Description: {cmd.description}\nParameters: {len(cmd.parameters)}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error listing commands: {str(e)}", ephemeral=True)


@bot.tree.command(name="delete", description="Delete a todo list")
@app_commands.describe(list_name="Name of the todo list to delete")
async def delete_list(interaction: discord.Interaction, list_name: str):
    """Delete a todo list (only creator can delete)."""
    try:
        guild_id = str(interaction.guild_id)
        
        # Find the list in this guild
        todo_list = bot.todo_manager.get_list_by_name(list_name, guild_id)
        if not todo_list:
            await interaction.response.send_message(
                f"❌ Todo list '{list_name}' not found in this server!", 
                ephemeral=True
            )
            return
        
        # Check if user is the creator
        if todo_list.created_by != str(interaction.user.id):
            await interaction.response.send_message(
                "❌ You can only delete todo lists that you created!", 
                ephemeral=True
            )
            return
        
        # Delete list
        success = bot.todo_manager.delete_list(todo_list.list_id)
        
        if success:
            await interaction.response.send_message(f"✅ Deleted todo list: **{list_name}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to delete todo list", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error deleting todo list: {str(e)}", ephemeral=True)


@bot.event
async def on_ready():
    """Event handler for when bot is ready."""
    logger.info(f"Logged in as {bot.user}")
    logger.info(f"Bot is in {len(bot.guilds)} guild(s)")
    print(f"✅ Bot is online! Logged in as {bot.user}")
    print(f"📊 Bot is in {len(bot.guilds)} guild(s)")
    
    # Log guild information for debugging
    for guild in bot.guilds:
        logger.info(f"Connected to guild: {guild.name} (ID: {guild.id})")


def main():
    """Main function to start the bot."""
    if not config.DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not found in environment variables!")
        print("❌ Error: DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your Discord bot token.")
        exit(1)
    
    # Start Flask server in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask server thread started")

    # Run bot with error handling and reconnection
    while True:
        try:
            logger.info("Starting Discord bot...")
            bot.run(config.DISCORD_TOKEN, log_handler=None)
        except discord.LoginFailure:
            logger.error("Invalid Discord token!")
            break
        except discord.HTTPException as e:
            logger.error(f"HTTP error: {e}")
            if e.status == 429:  # Rate limited
                logger.info("Rate limited, waiting 60 seconds...")
                time.sleep(60)
            else:
                logger.info("Waiting 30 seconds before reconnecting...")
                time.sleep(30)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            logger.info("Waiting 30 seconds before reconnecting...")
            time.sleep(30)


if __name__ == "__main__":
    main() 