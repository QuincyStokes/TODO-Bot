# Discord Todo Bot

A Discord bot that helps manage and create todo lists with collaborative features. Multiple users can create, edit, and check off items from shared todo lists.

## Features

- ✅ **Create todo lists** with custom names
- ✅ **Add items** to specific todo lists
- ✅ **Remove items** from todo lists
- ✅ **Toggle completion** status of items
- ✅ **View all todo lists** and their progress
- ✅ **Show detailed items** in specific lists
- ✅ **Delete todo lists** (only by creator)
- ✅ **Multi-user collaboration** - anyone can edit lists
- ✅ **Persistent storage** using JSON files

## Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `/create` | Create a new todo list | `/create name:Game Polishing` |
| `/add` | Add an item to a todo list | `/add list_name:Game Polishing item:Fix UI bugs` |
| `/remove` | Remove an item from a todo list | `/remove list_name:Game Polishing item_number:1` |
| `/toggle` | Toggle completion status of an item | `/toggle list_name:Game Polishing item_number:1` |
| `/list` | Show all available todo lists | `/list` |
| `/show` | Show items in a specific todo list (public) | `/show list_name:Game Polishing` |
| `/pin` | Pin a todo list to the channel for persistent display | `/pin list_name:Game Polishing` |
| `/delete` | Delete a todo list (creator only) | `/delete list_name:Game Polishing` |

## Interactive Features

### Interactive List View
- Use `/show` to display todo lists with individual toggle buttons for each item
- Each item has its own button showing its number and completion status
- Click any item button to toggle its completion status
- Buttons change color and icon based on completion status
- Perfect for quick item management without typing commands

### Persistent Channel Display
- Use `/pin` to post a todo list to the channel and pin it
- Great for keeping important lists visible in dedicated channels
- Lists remain interactive even when pinned

### Interactive Buttons
- **➕ Add Item**: Opens a modal to add new items
- **🔄 Refresh**: Updates the list display
- **Item Buttons**: Individual buttons for each item (e.g., "1. ⭕", "2. ✅")

## Setup Instructions

### 1. Create a Discord Bot

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name (e.g., "Todo Bot")
3. Go to the "Bot" section in the left sidebar
4. Click "Add Bot"
5. Under "Privileged Gateway Intents", enable:
   - Message Content Intent
   - Server Members Intent
6. Copy the bot token (you'll need this later)

### 2. Invite Bot to Your Server

1. Go to the "OAuth2" → "URL Generator" section
2. Select "bot" under "Scopes"
3. Select these permissions:
   - Send Messages
   - Use Slash Commands
   - Read Message History
   - Embed Links
   - Manage Messages (for pinning functionality)
4. Copy the generated URL and open it in your browser
5. Select your server and authorize the bot

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

1. Create a `.env` file in the project root
2. Add your Discord bot token:

```
DISCORD_TOKEN=your_actual_bot_token_here
```

### 5. Run the Bot

```bash
python bot.py
```

The bot should now be online and ready to use!

## Usage Examples

### Creating a Todo List
```
/create name:Game Polishing
```
✅ Created todo list: **Game Polishing**

### Adding Items
```
/add list_name:Game Polishing item:Fix UI bugs
/add list_name:Game Polishing item:Add sound effects
/add list_name:Game Polishing item:Optimize performance
```
✅ Added item to **Game Polishing**: Fix UI bugs

### Viewing a List (Interactive Display)
```
/show list_name:Game Polishing
```
Shows all items with individual toggle buttons for each item. Click any item button to toggle its completion status.

### Pinning Lists to Channels
```
/pin list_name:Game Polishing
```
Posts the list to the channel and pins it for persistent visibility with interactive buttons.

### Toggling Items
```
/toggle list_name:Game Polishing item_number:1
```
✅ Item 1 marked as completed in **Game Polishing**

### Viewing All Lists
```
/list
```
Shows all available todo lists with completion statistics.

## File Structure

```
TODO-Bot/
├── bot.py              # Main Discord bot with slash commands
├── todo_manager.py     # Core todo list management logic
├── config.py           # Configuration and environment variables
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── env_example.txt    # Example environment variables
└── todo_lists.json    # Data storage (created automatically)
```

## Technical Details

- **Framework**: discord.py with slash commands
- **Storage**: JSON file-based storage for simplicity
- **Permissions**: Anyone can edit lists, only creators can delete
- **Data Persistence**: All data is saved to `todo_lists.json`
- **Error Handling**: Comprehensive error handling with user-friendly messages

## Troubleshooting

### Bot Not Responding
- Check if the bot is online in your server
- Verify the bot token is correct in `.env`
- Ensure the bot has the required permissions

### Commands Not Working
- Make sure the bot has "Use Slash Commands" permission
- Try restarting the bot to sync commands
- Check the console for error messages
- **New commands may take up to 1 hour to appear** - this is a Discord limitation
- Use `/debug` to see all registered commands
- Ensure the bot has proper permissions (Manage Messages for pin command)

### Data Not Saving
- Ensure the bot has write permissions in the directory
- Check if `todo_lists.json` is being created
- Look for error messages in the console

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the MIT License. 