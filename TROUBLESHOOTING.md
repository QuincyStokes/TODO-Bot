# Discord Todo Bot Troubleshooting Guide

## 🚨 Common Issues and Solutions

### Issue: Lists disappear after redeploying

**Symptoms:**
- You create a list, redeploy the bot, and `/list` shows no lists
- The bot seems to "forget" all data after restart

**Diagnostic Steps:**

1. **Check Database Status with `/dbinfo`**
   ```
   /dbinfo
   ```
   This will show:
   - Database configuration
   - Whether the database file exists
   - Current data in memory
   - Lists for your guild

2. **Force Reload Data with `/reload`**
   ```
   /reload
   ```
   This forces the bot to reload all data from storage

3. **Force Save Data with `/forcesave`**
   ```
   /forcesave
   ```
   This forces the bot to save all current data to storage

**Common Causes:**

1. **Render Disk Not Mounted Properly**
   - Check if `DATA_DIR` environment variable is set correctly
   - Verify the persistent disk is mounted at `/opt/render/project/src/data`

2. **Database File Permissions**
   - The bot might not have write permissions to the data directory
   - Check if the database file exists and is writable

3. **Database Initialization Issues**
   - Tables might not be created properly
   - The bot might be falling back to JSON storage

**Solutions:**

1. **Check Render Configuration**
   - Ensure your `render.yaml` has the persistent disk configured:
   ```yaml
   disk:
     name: todo-data
     mountPath: /opt/render/project/src/data
     sizeGB: 1
   ```

2. **Verify Environment Variables**
   - `DATA_DIR` should be `/opt/render/project/src/data`
   - `USE_DATABASE` should be `true`

3. **Check Bot Logs**
   - Look for any database initialization errors
   - Check for permission errors

### Issue: "Add Item" button doesn't update the list

**Symptoms:**
- You click "Add Item", fill out the form, but the list doesn't update
- You see error messages about "404 Not Found" or "Unknown Message"

**Solutions:**
1. **Use the `/refresh` command** to create a fresh interactive view
2. **Check if the original message was deleted** - the bot can't edit deleted messages
3. **Try using `/add` command instead** of the UI button

### Issue: Bot shows "Unknown interaction" errors

**Symptoms:**
- Error messages about "404 Not Found (error code: 10062)"
- Bot responses fail with interaction errors

**Solutions:**
1. **Wait a moment and try again** - interactions can expire
2. **Use slash commands directly** instead of UI buttons
3. **Check bot permissions** in your Discord server

## 🔧 Debug Commands

### `/dbinfo` - Database Information
Shows detailed database status including:
- Configuration settings
- Database file existence and size
- Current data in memory
- Lists for your guild

### `/reload` - Force Data Reload
Forces the bot to reload all data from storage. Use this if:
- Lists disappeared after restart
- You suspect data isn't being loaded properly

### `/forcesave` - Force Data Save
Forces the bot to save all current data to storage. Use this if:
- You want to ensure data is persisted
- You suspect data isn't being saved properly

### `/debug` - List All Commands
Shows all registered slash commands for debugging.

## 📊 Database Status Check

Run this diagnostic script on Render to check database status:

```bash
python debug_database.py
```

This will show:
- Environment variables
- Data directory contents
- Database file status
- Table structure
- Current data counts

## 🐛 Common Error Messages

### "404 Not Found (error code: 10008): Unknown Message"
- **Cause**: The original message was deleted or the bot can't find it
- **Solution**: Use `/refresh` to create a new interactive view

### "404 Not Found (error code: 10062): Unknown interaction"
- **Cause**: The interaction expired or was deleted
- **Solution**: Try the command again, interactions have a time limit

### "Database file does not exist"
- **Cause**: First run or database initialization failed
- **Solution**: The bot will create the database automatically on first use

### "Permission denied"
- **Cause**: Bot doesn't have write permissions to data directory
- **Solution**: Check Render disk configuration and permissions

## 🔍 Advanced Debugging

### Check Render Logs
1. Go to your Render dashboard
2. Click on your service
3. Go to the "Logs" tab
4. Look for any error messages related to:
   - Database initialization
   - File permissions
   - Data loading/saving

### Check Database File
If you have SSH access to Render:
```bash
ls -la /opt/render/project/src/data/
sqlite3 /opt/render/project/src/data/todo_bot.db ".tables"
sqlite3 /opt/render/project/src/data/todo_bot.db "SELECT COUNT(*) FROM todo_lists;"
```

### Check JSON Fallback
```bash
cat /opt/render/project/src/data/todo_lists.json
```

## 🚀 Performance Tips

1. **Use `/reload` sparingly** - it reloads all data from storage
2. **Use `/forcesave` when needed** - it saves all data to storage
3. **Monitor database size** - large databases can slow down operations
4. **Check guild isolation** - ensure lists are properly separated by guild

## 📞 Getting Help

If you're still having issues:

1. **Run `/dbinfo`** and share the output
2. **Check Render logs** for any error messages
3. **Try the debug commands** to isolate the issue
4. **Check if the issue is guild-specific** or affects all guilds

## 🔄 Data Recovery

If you've lost data:

1. **Check if JSON fallback exists** - the bot might have saved data there
2. **Use `/reload`** to try loading from storage
3. **Check Render logs** for any data loading errors
4. **Verify disk persistence** - ensure the Render disk is properly configured

Remember: The bot uses both SQLite database and JSON fallback for data persistence. If one fails, the other should still work. 