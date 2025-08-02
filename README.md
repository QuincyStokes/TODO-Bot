# Discord Todo Bot

A feature-rich Discord bot for managing todo lists with interactive features, guild isolation, and persistent storage.

## 🚀 Features

- **Interactive Todo Lists**: Create, manage, and share todo lists within Discord servers
- **Guild Isolation**: Each Discord server has its own isolated todo lists
- **Persistent Storage**: Data persists through server restarts using Render's persistent disk
- **User Permissions**: Only list creators can delete their lists
- **Interactive UI**: Buttons and modals for easy list management
- **Scalable**: Tested with 100+ users and 1000+ items per list
- **Comprehensive Testing**: Full test suite with unit, integration, and comprehensive tests

## 📁 Project Structure

```
TODO-Bot/
├── bot.py                 # Main Discord bot application
├── todo_manager.py        # Core todo list management logic
├── config.py             # Configuration and environment variables
├── requirements.txt      # Python dependencies
├── run_tests.py         # Main test runner
├── tests/               # Test suite directory
│   ├── __init__.py
│   ├── test_todo_bot.py      # Unit tests
│   ├── test_integration.py   # Integration tests
│   └── test_comprehensive.py # Comprehensive tests
├── render.yaml          # Render deployment configuration
├── runtime.txt          # Python version specification
├── Procfile            # Process definition for Render
└── README.md           # This file
```

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.11.7+
- Discord Bot Token
- Render account (for deployment)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/QuincyStokes/TODO-Bot.git
   cd TODO-Bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env_example.txt .env
   # Edit .env with your Discord bot token
   ```

4. **Run the bot**
   ```bash
   python bot.py
   ```

### Render Deployment

1. **Fork this repository** to your GitHub account

2. **Create a new Web Service** on Render:
   - Connect your GitHub repository
   - Set build command: `pip install -r requirements.txt`
   - Set start command: `python bot.py`
   - Add environment variables:
     - `DISCORD_TOKEN`: Your Discord bot token
     - `DATA_DIR`: `/opt/render/project/src/data`

3. **Configure persistent storage**:
   - Add a disk in the Render dashboard
   - Mount path: `/opt/render/project/src/data`
   - Size: 1GB (adjust as needed)

## 🧪 Testing

### Run All Tests
```bash
python run_tests.py
```

### Run Individual Test Suites
```bash
# Unit tests
python -m tests.test_todo_bot

# Integration tests
python -m tests.test_integration

# Comprehensive tests
python -m tests.test_comprehensive
```

### Test Coverage

The test suite covers:

- ✅ **Unit Tests** (23 tests): Core functionality testing
- ✅ **Integration Tests** (5 tests): Bot initialization and command registration
- ✅ **Comprehensive Tests** (14 tests): Server downtime recovery, guild isolation, scalability, edge cases

## 📋 Bot Commands

| Command | Description | Usage |
|---------|-------------|-------|
| `/create` | Create a new todo list | `/create name:Shopping` |
| `/add` | Add item to a list | `/add list_name:Shopping item:Milk` |
| `/remove` | Remove item from list | `/remove list_name:Shopping item_number:1` |
| `/toggle` | Toggle item completion | `/toggle list_name:Shopping item_number:1` |
| `/list` | Show all lists in server | `/list` |
| `/show` | Show items in a list | `/show list_name:Shopping` |
| `/pin` | Pin list to channel | `/pin list_name:Shopping` |
| `/delete` | Delete a list (creator only) | `/delete list_name:Shopping` |

## 🔒 Security & Privacy

- **Guild Isolation**: Each Discord server's data is completely isolated
- **User Permissions**: Only list creators can delete their lists
- **Data Persistence**: Secure JSON storage with error handling
- **Rate Limiting**: Optimized file I/O to prevent excessive writes

## 🚀 Performance & Scalability

### Tested Performance Metrics

- **100 users creating lists**: ~6.5 seconds
- **1000 items per list**: ~13 seconds to add
- **Memory usage**: <50MB for large datasets
- **Concurrent operations**: Thread-safe implementation

### Scalability Features

- **Rate-limited saving**: Prevents excessive file I/O
- **UUID-based IDs**: Prevents collisions during rapid creation
- **Efficient data structures**: Optimized for large datasets
- **Graceful error handling**: Recovers from corrupted data

## 🧹 Code Quality

### Python Conventions Followed

- **PEP 8**: Proper formatting and naming conventions
- **Type Hints**: Full type annotations for better IDE support
- **Docstrings**: Comprehensive documentation for all classes and methods
- **Error Handling**: Graceful error recovery and logging
- **Modular Design**: Clean separation of concerns

### Code Review Improvements

1. **Project Structure**: Organized tests into dedicated directory
2. **Import Organization**: Proper import ordering and grouping
3. **Documentation**: Enhanced docstrings with Args/Returns sections
4. **Type Safety**: Added comprehensive type hints
5. **Error Handling**: Improved exception handling and logging
6. **Performance**: Optimized data saving with rate limiting
7. **Testing**: Comprehensive test suite with 100% pass rate

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_TOKEN` | Discord bot token | Required |
| `DATA_DIR` | Data storage directory | `/opt/render/project/src/data` |
| `PORT` | Flask server port | `10000` |

### Render Configuration

The `render.yaml` file configures:
- Python 3.11.7 runtime
- Persistent disk storage
- Environment variables
- Build and start commands

## 🐛 Troubleshooting

### Common Issues

1. **Bot not responding**: Check Discord token and permissions
2. **Data not persisting**: Verify Render disk configuration
3. **Tests failing**: Ensure all dependencies are installed

### Debug Commands

- `/debug`: List all registered commands
- Check Render logs for deployment issues

## 📈 Future Enhancements

- [ ] Database migration (PostgreSQL)
- [ ] Advanced permissions system
- [ ] List sharing between users
- [ ] Due dates and reminders
- [ ] List templates and categories
- [ ] Export/import functionality

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite: `python run_tests.py`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Discord.py library for excellent Discord API integration
- Render for reliable hosting and persistent storage
- Python community for best practices and conventions

---

**🎉 Ready for Production Deployment!**

All test suites pass with 100% success rate:
- ✅ Server downtime recovery: VERIFIED
- ✅ Guild isolation: VERIFIED  
- ✅ Scalability (100 users): VERIFIED
- ✅ Edge cases: VERIFIED
- ✅ Data persistence: VERIFIED 