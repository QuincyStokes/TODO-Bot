import discord
from discord import app_commands
from discord.ext import commands
import config
from todo_manager import TodoManager
import asyncio

class TodoBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(command_prefix="!", intents=intents)
        self.todo_manager = TodoManager()
        
    async def setup_hook(self):
        await self.tree.sync()
        print("Bot is ready!")

bot = TodoBot()

# Custom view for interactive todo list items
class TodoItemView(discord.ui.View):
    def __init__(self, todo_list, item_index):
        super().__init__(timeout=300)  # 5 minute timeout
        self.todo_list = todo_list
        self.item_index = item_index
        self.item = todo_list.items[item_index]
        
    @discord.ui.button(label="Toggle", style=discord.ButtonStyle.primary, custom_id="toggle")
    async def toggle_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Toggle the item
        success = bot.todo_manager.toggle_item_in_list(self.todo_list.list_id, self.item.item_id, str(interaction.user.id))
        
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
        # Remove the item
        success = bot.todo_manager.remove_item_from_list(self.todo_list.list_id, self.item.item_id)
        
        if success:
            await interaction.response.edit_message(
                content=f"✅ Removed item {self.item_index + 1} from **{self.todo_list.name}**",
                view=None
            )
        else:
            await interaction.response.send_message("❌ Failed to remove item", ephemeral=True)

# Custom view for interactive todo list with individual item toggles
class InteractiveTodoListView(discord.ui.View):
    def __init__(self, todo_list):
        super().__init__(timeout=300)  # 5 minute timeout
        self.todo_list = todo_list
        self._create_item_buttons()
    
    def _create_item_buttons(self):
        """Create individual toggle buttons for each item"""
        # Clear existing buttons (except Add and Refresh)
        self.clear_items()
        
        # Add Add Item and Refresh buttons first
        self.add_item(AddItemButton(self.todo_list))
        self.add_item(RefreshButton(self.todo_list))
        
        # Add individual toggle buttons for each item
        for i, item in enumerate(self.todo_list.items):
            button = ItemToggleButton(self.todo_list, i, item)
            self.add_item(button)

# Individual toggle button for each item
class ItemToggleButton(discord.ui.Button):
    def __init__(self, todo_list, item_index, item):
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
        # Toggle the item
        success = bot.todo_manager.toggle_item_in_list(self.todo_list.list_id, self.item.item_id, str(interaction.user.id))
        
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

# Add Item button
class AddItemButton(discord.ui.Button):
    def __init__(self, todo_list):
        super().__init__(
            label="➕ Add Item",
            style=discord.ButtonStyle.success,
            custom_id="add_item"
        )
        self.todo_list = todo_list
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddItemModal(self.todo_list))

# Refresh button
class RefreshButton(discord.ui.Button):
    def __init__(self, todo_list):
        super().__init__(
            label="🔄 Refresh",
            style=discord.ButtonStyle.secondary,
            custom_id="refresh"
        )
        self.todo_list = todo_list
    
    async def callback(self, interaction: discord.Interaction):
        embed = create_todo_list_embed(self.todo_list)
        new_view = InteractiveTodoListView(self.todo_list)
        await interaction.response.edit_message(embed=embed, view=new_view)

# Custom view for the main todo list (legacy - keeping for compatibility)
class TodoListView(discord.ui.View):
    def __init__(self, todo_list):
        super().__init__(timeout=300)  # 5 minute timeout
        self.todo_list = todo_list
        
    @discord.ui.button(label="➕ Add Item", style=discord.ButtonStyle.success, custom_id="add_item")
    async def add_item_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Create a modal for adding items
        await interaction.response.send_modal(AddItemModal(self.todo_list))
    
    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary, custom_id="refresh")
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Refresh the list display
        embed = create_todo_list_embed(self.todo_list)
        await interaction.response.edit_message(embed=embed, view=self)

# Modal for adding items
class AddItemModal(discord.ui.Modal, title="Add Todo Item"):
    def __init__(self, todo_list):
        super().__init__()
        self.todo_list = todo_list
        
    item_content = discord.ui.TextInput(
        label="Item Description",
        placeholder="Enter the todo item...",
        required=True,
        max_length=200
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        content = self.item_content.value
        new_item = bot.todo_manager.add_item_to_list(self.todo_list.list_id, content, str(interaction.user.id))
        
        if new_item:
            await interaction.response.send_message(f"✅ Added item to **{self.todo_list.name}**: {content}", ephemeral=True)
            # Update the original message with the new list
            embed = create_todo_list_embed(self.todo_list)
            view = InteractiveTodoListView(self.todo_list)
            await interaction.message.edit(embed=embed, view=view)
        else:
            await interaction.response.send_message("❌ Failed to add item", ephemeral=True)

def create_todo_list_embed(todo_list):
    """Create an embed for displaying a todo list"""
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

@bot.tree.command(name="create", description="Create a new todo list")
@app_commands.describe(name="Name of the todo list")
async def create_list(interaction: discord.Interaction, name: str):
    """Create a new todo list"""
    try:
        # Check if list already exists
        existing_list = bot.todo_manager.get_list_by_name(name)
        if existing_list:
            await interaction.response.send_message(f"❌ A todo list named '{name}' already exists!", ephemeral=True)
            return
        
        # Create new list
        todo_list = bot.todo_manager.create_list(name, str(interaction.user.id))
        await interaction.response.send_message(f"✅ Created todo list: **{name}**", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error creating todo list: {str(e)}", ephemeral=True)

@bot.tree.command(name="add", description="Add an item to a todo list")
@app_commands.describe(list_name="Name of the todo list", item="The todo item to add")
async def add_item(interaction: discord.Interaction, list_name: str, item: str):
    """Add an item to a specific todo list"""
    try:
        # Find the list
        todo_list = bot.todo_manager.get_list_by_name(list_name)
        if not todo_list:
            await interaction.response.send_message(f"❌ Todo list '{list_name}' not found!", ephemeral=True)
            return
        
        # Add item
        new_item = bot.todo_manager.add_item_to_list(todo_list.list_id, item, str(interaction.user.id))
        await interaction.response.send_message(f"✅ Added item to **{list_name}**: {item}", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error adding item: {str(e)}", ephemeral=True)

@bot.tree.command(name="remove", description="Remove an item from a todo list")
@app_commands.describe(list_name="Name of the todo list", item_number="Number of the item to remove (1, 2, 3, etc.)")
async def remove_item(interaction: discord.Interaction, list_name: str, item_number: int):
    """Remove an item from a specific todo list"""
    try:
        # Find the list
        todo_list = bot.todo_manager.get_list_by_name(list_name)
        if not todo_list:
            await interaction.response.send_message(f"❌ Todo list '{list_name}' not found!", ephemeral=True)
            return
        
        # Check if item number is valid
        if item_number < 1 or item_number > len(todo_list.items):
            await interaction.response.send_message(f"❌ Invalid item number. The list has {len(todo_list.items)} items.", ephemeral=True)
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
    """Toggle completion status of an item"""
    try:
        # Find the list
        todo_list = bot.todo_manager.get_list_by_name(list_name)
        if not todo_list:
            await interaction.response.send_message(f"❌ Todo list '{list_name}' not found!", ephemeral=True)
            return
        
        # Check if item number is valid
        if item_number < 1 or item_number > len(todo_list.items):
            await interaction.response.send_message(f"❌ Invalid item number. The list has {len(todo_list.items)} items.", ephemeral=True)
            return
        
        # Toggle item
        item_to_toggle = todo_list.items[item_number - 1]
        success = bot.todo_manager.toggle_item_in_list(todo_list.list_id, item_to_toggle.item_id, str(interaction.user.id))
        
        if success:
            status = "completed" if item_to_toggle.completed else "uncompleted"
            await interaction.response.send_message(f"✅ Item {item_number} marked as {status} in **{list_name}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Failed to toggle item", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error toggling item: {str(e)}", ephemeral=True)

@bot.tree.command(name="list", description="Show all todo lists")
async def list_lists(interaction: discord.Interaction):
    """Show all available todo lists"""
    try:
        todo_lists = bot.todo_manager.get_all_lists()
        
        if not todo_lists:
            await interaction.response.send_message("📝 No todo lists found. Create one with `/create`!", ephemeral=True)
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
    """Show items in a specific todo list with interactive buttons"""
    try:
        # Find the list
        todo_list = bot.todo_manager.get_list_by_name(list_name)
        if not todo_list:
            await interaction.response.send_message(f"❌ Todo list '{list_name}' not found!", ephemeral=True)
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
    """Pin a todo list to the channel for persistent display"""
    try:
        # Find the list
        todo_list = bot.todo_manager.get_list_by_name(list_name)
        if not todo_list:
            await interaction.response.send_message(f"❌ Todo list '{list_name}' not found!", ephemeral=True)
            return
        
        # Create embed and view
        embed = create_todo_list_embed(todo_list)
        view = InteractiveTodoListView(todo_list)
        
        # Send as a pinned message (public)
        message = await interaction.channel.send(embed=embed, view=view)
        
        # Pin the message if possible
        try:
            await message.pin()
            await interaction.response.send_message(f"✅ Pinned todo list **{list_name}** to the channel!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"✅ Posted todo list **{list_name}** to the channel! (Note: Bot doesn't have permission to pin messages)", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error pinning todo list: {str(e)}", ephemeral=True)

@bot.tree.command(name="debug", description="List all registered commands (debug)")
async def debug_commands(interaction: discord.Interaction):
    """List all registered commands for debugging"""
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
    """Delete a todo list"""
    try:
        # Find the list
        todo_list = bot.todo_manager.get_list_by_name(list_name)
        if not todo_list:
            await interaction.response.send_message(f"❌ Todo list '{list_name}' not found!", ephemeral=True)
            return
        
        # Check if user is the creator
        if todo_list.created_by != str(interaction.user.id):
            await interaction.response.send_message("❌ You can only delete todo lists that you created!", ephemeral=True)
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
    print(f"Logged in as {bot.user}")
    print(f"Bot is in {len(bot.guilds)} guild(s)")

if __name__ == "__main__":
    if not config.DISCORD_TOKEN:
        print("❌ Error: DISCORD_TOKEN not found in environment variables!")
        print("Please create a .env file with your Discord bot token.")
        exit(1)
    
    bot.run(config.DISCORD_TOKEN) 