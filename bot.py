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
        # Initialize todo manager with proper storage path
        logger.info(f"Initializing TodoManager with DATA_DIR: {config.DATA_DIR}")
        logger.info(f"Database enabled: {config.USE_DATABASE}")
        logger.info(f"Database path: {config.DATABASE_PATH}")
        
        try:
            self.todo_manager = TodoManager("todo_lists.json")
            logger.info(f"TodoManager initialized successfully. Loaded {len(self.todo_manager.todo_lists)} lists")
        except Exception as e:
            logger.error(f"Failed to initialize TodoManager: {e}")
            # Create a basic todo manager as fallback
            self.todo_manager = TodoManager("todo_lists.json")
            logger.info("Created fallback TodoManager")
        self.last_heartbeat = time.time()
        self.connection_attempts = 0
        self.max_reconnect_attempts = 5
        
    async def setup_hook(self):
        """Setup hook called when bot is ready."""
        try:
            # Sync commands to Discord servers
            logger.info("Syncing commands to Discord servers...")
            await self.tree.sync()
            logger.info("✅ Commands synced successfully!")
            
            # Log all registered commands for debugging
            commands = [cmd.name for cmd in self.tree.get_commands()]
            logger.info(f"Registered commands: {', '.join(commands)}")
            
            logger.info("Bot is ready!")
            self.heartbeat.start()
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")
            # Continue anyway - bot will still work with cached commands
    
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
        try:
            await ctx.send(f"❌ An error occurred: {str(error)}")
        except:
            logger.error("Failed to send error message to user")


bot = TodoBot()


async def safe_interaction_response(interaction: discord.Interaction, content: str, **kwargs):
    """Safely respond to an interaction with error handling."""
    try:
        if interaction.response.is_done():
            await interaction.followup.send(content, **kwargs)
        else:
            await interaction.response.send_message(content, **kwargs)
    except discord.NotFound:
        logger.warning("Interaction not found - it may have expired")
    except discord.Forbidden:
        logger.warning("Bot doesn't have permission to respond to this interaction")
    except discord.HTTPException as e:
        if e.status == 404 and e.code == 10062:
            logger.warning("Unknown interaction - it may have expired or been deleted")
        else:
            logger.error(f"HTTP error responding to interaction: {e}")
    except Exception as e:
        logger.error(f"Failed to respond to interaction: {e}")
        try:
            await interaction.followup.send("❌ An error occurred while processing your request.", ephemeral=True)
        except:
            pass


async def safe_interaction_edit(interaction: discord.Interaction, **kwargs):
    """Safely edit an interaction message with error handling."""
    try:
        await interaction.response.edit_message(**kwargs)
    except discord.NotFound:
        logger.warning("Interaction not found - it may have expired")
    except discord.Forbidden:
        logger.warning("Bot doesn't have permission to edit this interaction")
    except discord.HTTPException as e:
        if e.status == 404 and e.code == 10062:
            logger.warning("Unknown interaction - it may have expired or been deleted")
        else:
            logger.error(f"HTTP error editing interaction: {e}")
    except Exception as e:
        logger.error(f"Failed to edit interaction: {e}")
        try:
            await interaction.followup.send("❌ An error occurred while updating the message.", ephemeral=True)
        except:
            pass


class TodoItemView(discord.ui.View):
    """Interactive view for individual todo items."""
    
    def __init__(self, todo_list, item_index):
        """Initialize the view with a specific todo item."""
        super().__init__(timeout=300)  # 5 minute timeout
        self.todo_list = todo_list
        self.item_index = item_index
        self.item = todo_list.items[item_index]
    
    async def on_timeout(self):
        """Handle view timeout by updating the message."""
        try:
            embed = discord.Embed(
                title="⏰ View Expired",
                description=f"The interactive view for **{self.todo_list.name}** has timed out after 5 minutes.",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="How to continue:",
                value=f"• Use `/show {self.todo_list.name}` to get a fresh interactive view\n"
                      "• Use commands like `/add`, `/toggle`, `/remove` for direct actions",
                inline=False
            )
            embed.set_footer(text="Interactive views expire after 5 minutes for security reasons")
            
            # Try to edit the message, fallback to followup if needed
            try:
                await self.message.edit(embed=embed, view=None)
            except:
                # If we can't edit, try to send a followup
                try:
                    await self.message.reply(embed=embed)
                except:
                    pass
        except Exception as e:
            logger.error(f"Error in TodoItemView timeout: {e}")
        
    @discord.ui.button(label="Toggle", style=discord.ButtonStyle.primary, custom_id="toggle")
    async def toggle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Toggle the completion status of an item."""
        try:
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
                await safe_interaction_edit(
                    interaction,
                    content=f"✅ Item {self.item_index + 1} marked as {status} in **{self.todo_list.name}**",
                    view=self
                )
            else:
                await safe_interaction_response(interaction, "❌ Failed to toggle item", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in toggle button: {e}")
            await safe_interaction_response(interaction, "❌ An error occurred while toggling the item", ephemeral=True)
    
    @discord.ui.button(label="🗑️ Remove", style=discord.ButtonStyle.danger, custom_id="remove")
    async def remove_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Remove an item from the todo list."""
        try:
            success = bot.todo_manager.remove_item_from_list(self.todo_list.list_id, self.item.item_id)
            
            if success:
                await safe_interaction_edit(
                    interaction,
                    content=f"✅ Removed item {self.item_index + 1} from **{self.todo_list.name}**",
                    view=None
                )
            else:
                await safe_interaction_response(interaction, "❌ Failed to remove item", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in remove button: {e}")
            await safe_interaction_response(interaction, "❌ An error occurred while removing the item", ephemeral=True)


class InteractiveTodoListView(discord.ui.View):
    """Interactive view for todo lists with individual item toggles."""
    
    def __init__(self, todo_list):
        """Initialize the view with a todo list."""
        super().__init__(timeout=300)  # 5 minute timeout
        self.todo_list = todo_list
        self._create_item_buttons()
    
    async def on_timeout(self):
        """Handle view timeout by updating the message."""
        try:
            embed = discord.Embed(
                title="🚨 **INTERACTIVE VIEW EXPIRED** 🚨",
                description=f"**⚠️ WARNING: This interactive view for '{self.todo_list.name}' is no longer functional!**\n\n"
                           f"**The buttons below are now disabled and will not respond to clicks.**\n"
                           f"*This happened automatically after 5 minutes for security reasons.*",
                color=discord.Color.red()
            )
            embed.add_field(
                name="🔄 **To Continue Using This List:**",
                value=f"**• Use `/show {self.todo_list.name}` to get a fresh interactive view**\n"
                      f"**• Use `/add`, `/toggle`, `/remove` commands for direct actions**\n"
                      f"**• Use `/refresh {self.todo_list.name}` for a quick refresh**",
                inline=False
            )
            embed.add_field(
                name="📊 **Current List Status:**",
                value=f"**Total Items:** {len(self.todo_list.items)}\n"
                      f"**Completed:** {sum(1 for item in self.todo_list.items if item.completed)}\n"
                      f"**Pending:** {sum(1 for item in self.todo_list.items if not item.completed)}",
                inline=False
            )
            embed.set_footer(text="🕐 Interactive views automatically expire after 5 minutes | Use /show to get a fresh view")
            
            # Try to edit the message, fallback to followup if needed
            try:
                await self.message.edit(embed=embed, view=None)
            except:
                # If we can't edit, try to send a followup
                try:
                    await self.message.reply(embed=embed)
                except:
                    pass
        except Exception as e:
            logger.error(f"Error in InteractiveTodoListView timeout: {e}")
    
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
        try:
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
                
                await safe_interaction_edit(interaction, embed=embed, view=new_view)
            else:
                await safe_interaction_response(interaction, "❌ Failed to toggle item", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in item toggle button: {e}")
            await safe_interaction_response(interaction, "❌ An error occurred while toggling the item", ephemeral=True)


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
        try:
            logger.info(f"AddItemButton clicked for list: {self.todo_list.name}")
            await interaction.response.send_modal(AddItemModal(self.todo_list))
        except Exception as e:
            logger.error(f"Error in add item button: {e}")
            await safe_interaction_response(interaction, "❌ An error occurred while opening the add item modal", ephemeral=True)


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
        try:
            embed = create_todo_list_embed(self.todo_list)
            new_view = InteractiveTodoListView(self.todo_list)
            await safe_interaction_edit(interaction, embed=embed, view=new_view)
        except Exception as e:
            logger.error(f"Error in refresh button: {e}")
            await safe_interaction_response(interaction, "❌ An error occurred while refreshing the list", ephemeral=True)


class TodoListView(discord.ui.View):
    """Legacy view for todo lists (kept for compatibility)."""
    
    def __init__(self, todo_list):
        """Initialize the legacy view."""
        super().__init__(timeout=300)  # 5 minute timeout
        self.todo_list = todo_list
    
    async def on_timeout(self):
        """Handle view timeout by updating the message."""
        try:
            embed = discord.Embed(
                title="🚨 **INTERACTIVE VIEW EXPIRED** 🚨",
                description=f"**⚠️ WARNING: This interactive view for '{self.todo_list.name}' is no longer functional!**\n\n"
                           f"**The buttons below are now disabled and will not respond to clicks.**\n"
                           f"*This happened automatically after 5 minutes for security reasons.*",
                color=discord.Color.red()
            )
            embed.add_field(
                name="🔄 **To Continue Using This List:**",
                value=f"**• Use `/show {self.todo_list.name}` to get a fresh interactive view**\n"
                      f"**• Use `/add`, `/toggle`, `/remove` commands for direct actions**\n"
                      f"**• Use `/refresh {self.todo_list.name}` for a quick refresh**",
                inline=False
            )
            embed.add_field(
                name="📊 **Current List Status:**",
                value=f"**Total Items:** {len(self.todo_list.items)}\n"
                      f"**Completed:** {sum(1 for item in self.todo_list.items if item.completed)}\n"
                      f"**Pending:** {sum(1 for item in self.todo_list.items if not item.completed)}",
                inline=False
            )
            embed.set_footer(text="🕐 Interactive views automatically expire after 5 minutes | Use /show to get a fresh view")
            
            # Try to edit the message, fallback to followup if needed
            try:
                await self.message.edit(embed=embed, view=None)
            except:
                # If we can't edit, try to send a followup
                try:
                    await self.message.reply(embed=embed)
                except:
                    pass
        except Exception as e:
            logger.error(f"Error in TodoListView timeout: {e}")
        
    @discord.ui.button(label="➕ Add Item", style=discord.ButtonStyle.success, custom_id="add_item")
    async def add_item_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle add item button click."""
        try:
            await interaction.response.send_modal(AddItemModal(self.todo_list))
        except Exception as e:
            logger.error(f"Error in legacy add item button: {e}")
            await safe_interaction_response(interaction, "❌ An error occurred while opening the add item modal", ephemeral=True)
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary, custom_id="refresh")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle refresh button click."""
        try:
            embed = create_todo_list_embed(self.todo_list)
            await safe_interaction_edit(interaction, embed=embed, view=self)
        except Exception as e:
            logger.error(f"Error in legacy refresh button: {e}")
            await safe_interaction_response(interaction, "❌ An error occurred while refreshing the list", ephemeral=True)


class AddItemModal(discord.ui.Modal, title="Add Todo Item"):
    """Modal for adding new items to a todo list."""
    
    def __init__(self, todo_list):
        """Initialize the modal with a todo list."""
        super().__init__()
        self.todo_list = todo_list
        logger.info(f"AddItemModal initialized for list: {todo_list.name} (ID: {todo_list.list_id})")
        
    item_content = discord.ui.TextInput(
        label="Item Description",
        placeholder="Enter the todo item...",
        required=True,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission to add the item."""
        try:
            content = self.item_content.value
            logger.info(f"Adding item '{content}' to list '{self.todo_list.name}' (ID: {self.todo_list.list_id})")
            
            new_item = bot.todo_manager.add_item_to_list(
                self.todo_list.list_id, 
                content, 
                str(interaction.user.id)
            )
            
            if new_item:
                logger.info(f"Successfully added item to list. New item ID: {new_item.item_id}")
                
                # Send success confirmation first
                await safe_interaction_response(interaction, "✅ Item added successfully!", ephemeral=True)
                
                # Try to update the original message, but don't fail if it doesn't work
                try:
                    # Refresh the todo list from the manager to get the latest data
                    updated_list = bot.todo_manager.get_list(self.todo_list.list_id)
                    if updated_list:
                        embed = create_todo_list_embed(updated_list)
                        view = InteractiveTodoListView(updated_list)
                        await interaction.message.edit(embed=embed, view=view)
                        logger.info("Successfully updated original message with new item")
                    else:
                        logger.warning("Could not find updated list in manager")
                except discord.NotFound:
                    logger.warning("Original message not found - it may have been deleted")
                    # Send a followup message to let user know the item was added but view couldn't be updated
                    try:
                        await interaction.followup.send("✅ Item added! (Original message couldn't be updated - use `/show` to see the updated list)", ephemeral=True)
                    except:
                        pass
                except discord.Forbidden:
                    logger.warning("Bot doesn't have permission to edit the original message")
                    # Send a followup message to let user know the item was added but view couldn't be updated
                    try:
                        await interaction.followup.send("✅ Item added! (Original message couldn't be updated - use `/show` to see the updated list)", ephemeral=True)
                    except:
                        pass
                except Exception as edit_error:
                    logger.warning(f"Could not update original message: {edit_error}")
                    # Send a followup message to let user know the item was added but view couldn't be updated
                    try:
                        await interaction.followup.send("✅ Item added! (Original message couldn't be updated - use `/show` to see the updated list)", ephemeral=True)
                    except:
                        pass
            else:
                logger.error("Failed to add item - add_item_to_list returned None")
                await safe_interaction_response(interaction, "❌ Failed to add item", ephemeral=True)
        except Exception as e:
            logger.error(f"Error in add item modal: {e}")
            await safe_interaction_response(interaction, "❌ An error occurred while adding the item", ephemeral=True)


def create_todo_list_embed(todo_list) -> discord.Embed:
    """Create an embed for displaying a todo list.
    
    Args:
        todo_list: The TodoList object to display
        
    Returns:
        discord.Embed: Formatted embed for the todo list
    """
    embed = discord.Embed(
        title=f"📋 {todo_list.name}",
        color=discord.Color.blue()
    )
    
    if not todo_list.items:
        embed.add_field(name="Items", value="No items yet. Add some with the ➕ button!", inline=False)
    else:
        items_text = ""
        for i, item in enumerate(todo_list.items, 1):
            status = "✅" if item.completed else "⭕"
            items_text += f"{i}. {status} {item.content}\n"
        embed.add_field(name="Items", value=items_text, inline=False)
    
    return embed


# Command handlers with enhanced error handling
@bot.tree.command(name="create", description="Create a new todo list")
@app_commands.describe(name="Name of the todo list")
async def create_list(interaction: discord.Interaction, name: str):
    """Create a new todo list."""
    try:
        guild_id = str(interaction.guild_id)
        
        # Check if list already exists
        if bot.todo_manager.list_exists(name, guild_id):
            # Get the new name that will be used
            existing_lists = bot.todo_manager.get_lists_by_name(name, guild_id)
            new_name = f"{name} (1)"
            i = 2
            while bot.todo_manager.list_exists(new_name, guild_id):
                new_name = f"{name} ({i})"
                i += 1
            
            # Create the list with the new name
            todo_list = bot.todo_manager.create_list(name, str(interaction.user.id), guild_id)
            
            await safe_interaction_response(
                interaction, 
                f"✅ Created todo list: **{todo_list.name}**\n"
                f"ℹ️ A list named '{name}' already exists, so this one was renamed automatically.", 
                ephemeral=True
            )
        else:
            # Create the list with the original name
            todo_list = bot.todo_manager.create_list(name, str(interaction.user.id), guild_id)
            
            await safe_interaction_response(
                interaction, 
                f"✅ Created todo list: **{name}**", 
                ephemeral=True
            )
            
    except Exception as e:
        logger.error(f"Error creating todo list: {e}")
        await safe_interaction_response(interaction, f"❌ Error creating todo list: {str(e)}", ephemeral=True)


@bot.tree.command(name="add", description="Add items to a todo list (separate multiple items with commas)")
@app_commands.describe(list_name="Name of the todo list", items="The todo items to add (separate multiple items with commas)")
async def add_item(interaction: discord.Interaction, list_name: str, items: str):
    """Add one or more items to a specific todo list."""
    try:
        guild_id = str(interaction.guild_id)
        
        # Find the list in this guild
        todo_list = bot.todo_manager.get_list_by_name(list_name, guild_id)
        if not todo_list:
            await safe_interaction_response(
                interaction,
                f"❌ Todo list '{list_name}' not found in this server!", 
                ephemeral=True
            )
            return
        
        # Split items by comma and clean them up
        item_list = [item.strip() for item in items.split(',') if item.strip()]
        
        if not item_list:
            await safe_interaction_response(
                interaction,
                "❌ No valid items provided. Please enter at least one item.", 
                ephemeral=True
            )
            return
        
        # Add all items
        successful_items = []
        failed_items = []
        
        for item in item_list:
            new_item = bot.todo_manager.add_item_to_list(todo_list.list_id, item, str(interaction.user.id))
            if new_item:
                successful_items.append(item)
            else:
                failed_items.append(item)
        
        # Create response message
        if successful_items and not failed_items:
            if len(successful_items) == 1:
                await safe_interaction_response(interaction, f"✅ Added 1 item to **{list_name}**", ephemeral=True)
            else:
                await safe_interaction_response(interaction, f"✅ Added {len(successful_items)} items to **{list_name}**", ephemeral=True)
        elif successful_items and failed_items:
            await safe_interaction_response(
                interaction, 
                f"⚠️ Added {len(successful_items)} items to **{list_name}**, but failed to add {len(failed_items)} items", 
                ephemeral=True
            )
        else:
            await safe_interaction_response(interaction, "❌ Failed to add any items", ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error adding items: {e}")
        await safe_interaction_response(interaction, f"❌ Error adding items: {str(e)}", ephemeral=True)


@bot.tree.command(name="remove", description="Remove an item from a todo list")
@app_commands.describe(list_name="Name of the todo list", item_number="Number of the item to remove (1, 2, 3, etc.)")
async def remove_item(interaction: discord.Interaction, list_name: str, item_number: int):
    """Remove an item from a specific todo list."""
    try:
        guild_id = str(interaction.guild_id)
        
        # Find the list in this guild
        todo_list = bot.todo_manager.get_list_by_name(list_name, guild_id)
        if not todo_list:
            await safe_interaction_response(
                interaction,
                f"❌ Todo list '{list_name}' not found in this server!", 
                ephemeral=True
            )
            return
        
        # Check if item number is valid
        if item_number < 1 or item_number > len(todo_list.items):
            await safe_interaction_response(
                interaction,
                f"❌ Invalid item number. The list has {len(todo_list.items)} items.", 
                ephemeral=True
            )
            return
        
        # Remove item
        item_to_remove = todo_list.items[item_number - 1]
        success = bot.todo_manager.remove_item_from_list(todo_list.list_id, item_to_remove.item_id)
        
        if success:
            await safe_interaction_response(
                interaction,
                f"✅ Removed item {item_number} from **{list_name}**", 
                ephemeral=True
            )
        else:
            await safe_interaction_response(interaction, "❌ Failed to remove item", ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error removing item: {e}")
        await safe_interaction_response(interaction, f"❌ Error removing item: {str(e)}", ephemeral=True)


@bot.tree.command(name="toggle", description="Toggle completion status of an item")
@app_commands.describe(list_name="Name of the todo list", item_number="Number of the item to toggle (1, 2, 3, etc.)")
async def toggle_item(interaction: discord.Interaction, list_name: str, item_number: int):
    """Toggle completion status of an item."""
    try:
        guild_id = str(interaction.guild_id)
        
        # Find the list in this guild
        todo_list = bot.todo_manager.get_list_by_name(list_name, guild_id)
        if not todo_list:
            await safe_interaction_response(
                interaction,
                f"❌ Todo list '{list_name}' not found in this server!", 
                ephemeral=True
            )
            return
        
        # Check if item number is valid
        if item_number < 1 or item_number > len(todo_list.items):
            await safe_interaction_response(
                interaction,
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
            await safe_interaction_response(
                interaction,
                f"✅ Item {item_number} marked as {status} in **{list_name}**", 
                ephemeral=True
            )
        else:
            await safe_interaction_response(interaction, "❌ Failed to toggle item", ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error toggling item: {e}")
        await safe_interaction_response(interaction, f"❌ Error toggling item: {str(e)}", ephemeral=True)


@bot.tree.command(name="list", description="Show all todo lists")
async def list_lists(interaction: discord.Interaction):
    """Show all available todo lists in this server."""
    try:
        guild_id = str(interaction.guild_id)
        todo_lists = bot.todo_manager.get_all_lists(guild_id)
        
        if not todo_lists:
            embed = discord.Embed(
                title="📋 No Todo Lists Found",
                description="No todo lists found in this server.",
                color=discord.Color.orange()
            )
            
            embed.add_field(
                name="What to do next:",
                value="• Use `/create <name>` to create a new todo list\n"
                      "• Use `/dbinfo` to check database status\n"
                      "• Use `/reload` (admin only) to reload data from storage",
                inline=False
            )
            
            await safe_interaction_response(interaction, "", embed=embed, ephemeral=True)
            return
        
        # Group lists by base name to show duplicates
        list_groups = {}
        for todo_list in todo_lists:
            base_name = todo_list.name.split(" (")[0]  # Remove numbering like " (1)", " (2)"
            if base_name not in list_groups:
                list_groups[base_name] = []
            list_groups[base_name].append(todo_list)
        
        embed = discord.Embed(
            title="📋 Todo Lists",
            description=f"Found {len(todo_lists)} todo list(s) in this server:",
            color=discord.Color.green()
        )
        
        for base_name, lists in list_groups.items():
            if len(lists) == 1:
                # Single list - show normally
                todo_list = lists[0]
                item_count = len(todo_list.items)
                completed_count = sum(1 for item in todo_list.items if item.completed)
                embed.add_field(
                    name=todo_list.name,
                    value=f"Items: {item_count} | Completed: {completed_count} | Created by <@{todo_list.created_by}>",
                    inline=False
                )
            else:
                # Multiple lists with similar names - show as group
                embed.add_field(
                    name=f"📁 {base_name} ({len(lists)} lists)",
                    value="Multiple lists with similar names:",
                    inline=False
                )
                
                for i, todo_list in enumerate(lists, 1):
                    item_count = len(todo_list.items)
                    completed_count = sum(1 for item in todo_list.items if item.completed)
                    embed.add_field(
                        name=f"  {todo_list.name}",
                        value=f"Items: {item_count} | Completed: {completed_count} | Created by <@{todo_list.created_by}>",
                        inline=False
                    )
        
        await safe_interaction_response(interaction, "", embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error listing todo lists: {e}")
        await safe_interaction_response(interaction, f"❌ Error listing todo lists: {str(e)}", ephemeral=True)


@bot.tree.command(name="show", description="Show items in a specific todo list with interactive buttons")
@app_commands.describe(list_name="Name of the todo list to show")
async def show_list(interaction: discord.Interaction, list_name: str):
    """Show items in a specific todo list with interactive buttons."""
    try:
        guild_id = str(interaction.guild_id)
        logger.info(f"Looking for list '{list_name}' in guild {guild_id}")
        
        # Get all lists for this guild for debugging
        all_lists = bot.todo_manager.get_all_lists(guild_id)
        logger.info(f"Found {len(all_lists)} lists in guild {guild_id}: {[l.name for l in all_lists]}")
        
        todo_list = bot.todo_manager.get_list_by_name(list_name, guild_id)
        
        if not todo_list:
            # Provide more helpful error message
            if all_lists:
                list_names = [l.name for l in all_lists]
                await safe_interaction_response(
                    interaction,
                    f"❌ Todo list '{list_name}' not found in this server!\n\n"
                    f"Available lists: {', '.join(list_names)}", 
                    ephemeral=True
                )
            else:
                await safe_interaction_response(
                    interaction,
                    f"❌ Todo list '{list_name}' not found in this server!\n\n"
                    f"No lists found. Create one with `/create {list_name}`", 
                    ephemeral=True
                )
            return
        
        logger.info(f"Found list '{todo_list.name}' with {len(todo_list.items)} items")
        embed = create_todo_list_embed(todo_list)
        view = InteractiveTodoListView(todo_list)
        await safe_interaction_response(interaction, "", embed=embed, view=view)
        
    except Exception as e:
        logger.error(f"Error showing todo list: {e}")
        await safe_interaction_response(interaction, f"❌ Error showing todo list: {str(e)}", ephemeral=True)





@bot.tree.command(name="debug", description="List all registered commands (debug)")
async def debug_commands(interaction: discord.Interaction):
    """List all registered commands for debugging."""
    try:
        commands = [cmd.name for cmd in bot.tree.get_commands()]
        embed = discord.Embed(
            title="🔧 Debug: Registered Commands",
            description="Available slash commands:",
            color=discord.Color.blue()
        )
        
        for cmd in commands:
            embed.add_field(name=f"/{cmd}", value="✅ Registered", inline=False)
        
        await safe_interaction_response(interaction, "", embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in debug command: {e}")
        await safe_interaction_response(interaction, f"❌ Error in debug command: {str(e)}", ephemeral=True)


@bot.tree.command(name="sync", description="Force sync commands to Discord servers (admin only)")
async def sync_commands(interaction: discord.Interaction):
    """Force sync commands to Discord servers (admin only)."""
    try:
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await safe_interaction_response(
                interaction,
                "❌ This command requires administrator permissions!", 
                ephemeral=True
            )
            return
        
        # Show syncing message
        await safe_interaction_response(
            interaction,
            "🔄 Syncing commands to Discord servers... This may take a few moments.", 
            ephemeral=True
        )
        
        # Sync commands
        await bot.tree.sync()
        
        # Get updated command list
        commands = [cmd.name for cmd in bot.tree.get_commands()]
        
        embed = discord.Embed(
            title="✅ Commands Synced Successfully!",
            description="All commands have been updated on Discord servers.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📋 Registered Commands",
            value=", ".join([f"`/{cmd}`" for cmd in commands]),
            inline=False
        )
        
        embed.add_field(
            name="⏰ Next Steps",
            value="• Commands should be available immediately\n"
                  "• If you still see 'outdated' messages, wait 2-3 minutes\n"
                  "• Try using the commands again",
            inline=False
        )
        
        embed.set_footer(text="Note: Discord caches commands for a few minutes")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error syncing commands: {e}")
        await safe_interaction_response(
            interaction, 
            f"❌ Error syncing commands: {str(e)}", 
            ephemeral=True
        )




@bot.tree.command(name="delete", description="Delete a todo list")
@app_commands.describe(list_name="Name of the todo list to delete")
async def delete_list(interaction: discord.Interaction, list_name: str):
    """Delete a todo list."""
    try:
        guild_id = str(interaction.guild_id)
        todo_list = bot.todo_manager.get_list_by_name(list_name, guild_id)
        
        if not todo_list:
            await safe_interaction_response(
                interaction,
                f"❌ Todo list '{list_name}' not found in this server!", 
                ephemeral=True
            )
            return
        
        success = bot.todo_manager.delete_list(todo_list.list_id)
        
        if success:
            await safe_interaction_response(
                interaction,
                f"✅ Deleted todo list: **{list_name}**", 
                ephemeral=True
            )
        else:
            await safe_interaction_response(interaction, "❌ Failed to delete todo list", ephemeral=True)
            
    except Exception as e:
        logger.error(f"Error deleting todo list: {e}")
        await safe_interaction_response(interaction, f"❌ Error deleting todo list: {str(e)}", ephemeral=True)


@bot.tree.command(name="help", description="Show help information and commands")
async def help_command(interaction: discord.Interaction):
    """Show help information and available commands."""
    try:
        embed = discord.Embed(
            title="📋 Todo Bot Help",
            description="A Discord bot for managing todo lists with interactive features.",
            color=discord.Color.blue()
        )
        
        # Basic commands
        embed.add_field(
            name="📝 List Management",
            value="• `/create [name]` - Create a new todo list\n"
                  "• `/list` - Show all todo lists in this server\n"
                  "• `/show [name]` - Display a todo list with interactive buttons\n"
                  "• `/info [name]` - Get detailed information about a list\n"
                  "• `/delete [name]` - Delete a todo list",
            inline=False
        )
        
        # Item management
        embed.add_field(
             name="✅ Item Management",
             value="• `/add [items] to [list]` - Add items to a list (separate multiple items with commas)\n"
                   "• `/remove [number] from [list]` - Remove an item by number\n"
                   "• `/toggle [number] in [list]` - Toggle item completion",
             inline=False
         )
        
        # Interactive features
        embed.add_field(
            name="🔄 Interactive Features",
            value="• Interactive views have buttons for quick actions\n"
                  "• Views expire after 5 minutes for security\n"
                  "• Use `/show [name]` to refresh expired views",
            inline=False
        )
        
        # Tips and features
        embed.add_field(
            name="💡 Tips & Features",
            value="• **Duplicate names?** Lists are automatically renamed (e.g., 'Shopping (1)', 'Shopping (2)')\n"
                  "• **Multiple lists?** Use `/list` to see all lists grouped by name\n"
                  "• **Need details?** Use `/info [name]` for comprehensive list information\n"
                  "• **Quick actions?** Use interactive buttons for faster workflow",
            inline=False
        )
        
        # Troubleshooting
        embed.add_field(
             name="🔧 Troubleshooting",
             value="• **View expired?** Use `/show [name]` to refresh\n"
                   "• **Commands outdated?** Use `/sync` (admin only) to force update\n"
                   "• **Bot offline?** Check if Render server is running\n"
                   "• **Commands not working?** Use `/debug` to check status\n"
                   "• **Need help?** Contact the bot administrator",
             inline=False
         )
        
        embed.set_footer(text="Tip: Use commands for quick actions, interactive views for detailed work")
        
        await safe_interaction_response(interaction, "", embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await safe_interaction_response(interaction, f"❌ Error showing help: {str(e)}", ephemeral=True)


@bot.tree.command(name="info", description="Get detailed information about a todo list")
@app_commands.describe(list_name="Name of the todo list to get info about")
async def list_info(interaction: discord.Interaction, list_name: str):
    """Get detailed information about a specific todo list."""
    try:
        guild_id = str(interaction.guild_id)
        todo_list = bot.todo_manager.get_list_by_name(list_name, guild_id)
        
        if not todo_list:
            await safe_interaction_response(
                interaction,
                f"❌ Todo list '{list_name}' not found in this server!", 
                ephemeral=True
            )
            return
        
        # Create detailed embed
        embed = discord.Embed(
            title=f"📋 {todo_list.name} - Detailed Information",
            description=f"Created by <@{todo_list.created_by}>",
            color=discord.Color.blue()
        )
        
        # Basic info
        embed.add_field(
            name="📊 List Statistics",
            value=f"• **Total Items:** {len(todo_list.items)}\n"
                  f"• **Completed:** {sum(1 for item in todo_list.items if item.completed)}\n"
                  f"• **Pending:** {sum(1 for item in todo_list.items if not item.completed)}\n"
                  f"• **Completion Rate:** {round((sum(1 for item in todo_list.items if item.completed) / len(todo_list.items) * 100) if todo_list.items else 0, 1)}%",
            inline=False
        )
        
        # Technical details
        # Handle timestamp conversion safely
        try:
            if isinstance(todo_list.created_at, str):
                # Parse ISO string to datetime
                from datetime import datetime
                created_dt = datetime.fromisoformat(todo_list.created_at.replace('Z', '+00:00'))
                created_timestamp = int(created_dt.timestamp())
            else:
                created_timestamp = int(todo_list.created_at.timestamp())
            created_at_display = f"<t:{created_timestamp}:F>"
        except Exception as e:
            logger.warning(f"Could not parse created_at timestamp: {e}")
            created_at_display = todo_list.created_at
        
        embed.add_field(
            name="🔧 Technical Details",
            value=f"• **List ID:** `{todo_list.list_id}`\n"
                  f"• **Guild ID:** `{todo_list.guild_id}`\n"
                  f"• **Created By:** <@{todo_list.created_by}>\n"
                  f"• **Created At:** {created_at_display}",
            inline=False
        )
        
        # Items breakdown
        if todo_list.items:
            completed_items = [item for item in todo_list.items if item.completed]
            pending_items = [item for item in todo_list.items if not item.completed]
            
            if completed_items:
                completed_text = "\n".join([f"✅ {item.content}" for item in completed_items])
                embed.add_field(
                    name=f"✅ Completed Items ({len(completed_items)})",
                    value=completed_text[:1024] + ("..." if len(completed_text) > 1024 else ""),
                    inline=False
                )
            
            if pending_items:
                pending_text = "\n".join([f"⭕ {item.content}" for item in pending_items])
                embed.add_field(
                    name=f"⭕ Pending Items ({len(pending_items)})",
                    value=pending_text[:1024] + ("..." if len(pending_text) > 1024 else ""),
                    inline=False
                )
        else:
            embed.add_field(
                name="📝 Items",
                value="No items in this list yet.",
                inline=False
            )
        
        embed.set_footer(text=f"List ID: {todo_list.list_id} | Use /show {list_name} for interactive view")
        
        await safe_interaction_response(interaction, "", embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error getting list info: {e}")
        await safe_interaction_response(interaction, f"❌ Error getting list info: {str(e)}", ephemeral=True)


@bot.tree.command(name="refresh", description="Create a fresh interactive view for a todo list")
@app_commands.describe(list_name="Name of the todo list to refresh")
async def refresh_list(interaction: discord.Interaction, list_name: str):
    """Create a fresh interactive view for a todo list."""
    try:
        guild_id = str(interaction.guild_id)
        todo_list = bot.todo_manager.get_list_by_name(list_name, guild_id)
        
        if not todo_list:
            await safe_interaction_response(
                interaction,
                f"❌ Todo list '{list_name}' not found in this server!", 
                ephemeral=True
            )
            return
        
        embed = create_todo_list_embed(todo_list)
        view = InteractiveTodoListView(todo_list)
        
        await safe_interaction_response(interaction, 
            f"🔄 Created fresh interactive view for **{list_name}**!", 
            ephemeral=True
        )
        
        # Send the refreshed view to the channel
        await interaction.channel.send(embed=embed, view=view)
        
    except Exception as e:
        logger.error(f"Error refreshing todo list: {e}")
        await safe_interaction_response(interaction, f"❌ Error refreshing list: {str(e)}", ephemeral=True)








@bot.event
async def on_ready():
    """Called when the bot is ready."""
    logger.info(f"Logged in as {bot.user}")
    print(f"✅ Bot is online as {bot.user}")
    
    # Log guild information
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