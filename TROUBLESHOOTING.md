# Discord Bot Troubleshooting Guide

This guide helps diagnose and fix common issues with the Discord Todo Bot on Render.

## Common Issues and Solutions

### 1. Bot Goes Offline After Deployment

**Symptoms:**
- Bot appears online initially but goes offline after a few minutes
- Bot doesn't respond to commands
- Health check endpoint returns errors

**Causes:**
- Missing error handling and reconnection logic
- No heartbeat mechanism
- Flask server crashes
- Discord connection issues

**Solutions:**
- ✅ **Fixed**: Added comprehensive error handling and reconnection logic
- ✅ **Fixed**: Implemented heartbeat mechanism
- ✅ **Fixed**: Added proper logging for debugging
- ✅ **Fixed**: Made Flask thread daemon to prevent crashes

### 2. Bot Not Starting

**Symptoms:**
- Bot never appears online
- Render shows deployment success but bot is offline
- No logs in Render dashboard

**Causes:**
- Invalid Discord token
- Missing environment variables
- Data directory permissions
- Import errors

**Solutions:**
- Check Discord token in Render environment variables
- Verify all required environment variables are set
- Check data directory permissions
- Review startup logs in Render dashboard

### 3. Bot Responds Intermittently

**Symptoms:**
- Bot sometimes responds, sometimes doesn't
- Commands work occasionally
- Slash commands not syncing

**Causes:**
- Rate limiting
- Connection instability
- Command sync issues

**Solutions:**
- ✅ **Fixed**: Added rate limit handling
- ✅ **Fixed**: Improved connection stability
- ✅ **Fixed**: Enhanced command syncing

## Debugging Steps

### 1. Check Render Logs
```bash
# View recent logs in Render dashboard
# Look for error messages and connection issues
```

### 2. Test Health Endpoint
```bash
# Test if the bot is responding to health checks
curl https://your-app-name.onrender.com/health
```

### 3. Check Bot Status
```bash
# Test basic connectivity
curl https://your-app-name.onrender.com/
```

### 4. Monitor Logs
The bot now creates detailed logs:
- `bot.log` - Main bot logs
- `startup.log` - Startup process logs

### 5. Environment Variables
Ensure these are set in Render:
- `DISCORD_TOKEN` - Your Discord bot token
- `DATA_DIR` - Data storage directory (auto-set)

## Render-Specific Issues

### 1. Cold Starts
Render services can have cold starts. The bot now handles this with:
- Automatic reconnection logic
- Heartbeat mechanism
- Proper error handling

### 2. Memory Limits
If you hit memory limits:
- Check for memory leaks in your code
- Monitor resource usage in Render dashboard
- Consider upgrading your Render plan

### 3. Timeout Issues
Render has request timeouts. The bot now:
- Uses daemon threads for Flask
- Implements proper error handling
- Has health check endpoints

## Monitoring Your Bot

### 1. Health Check Endpoints
- `/` - Basic status
- `/health` - Detailed health information

### 2. Log Files
- Check `bot.log` for Discord connection issues
- Check `startup.log` for startup problems
- Monitor Render dashboard logs

### 3. Discord Status
- Check if bot appears online in Discord
- Test slash commands
- Verify bot permissions

## Quick Fixes

### If Bot Won't Start:
1. Check Discord token in Render environment variables
2. Verify bot has proper permissions in Discord
3. Check Render logs for error messages

### If Bot Goes Offline:
1. Check Render logs for connection errors
2. Verify Discord token is still valid
3. Test health endpoint
4. Restart the service in Render

### If Commands Don't Work:
1. Check if slash commands are synced
2. Verify bot permissions in Discord server
3. Test basic commands like `/debug`

## Prevention

The updated bot now includes:
- ✅ Automatic reconnection on disconnection
- ✅ Heartbeat mechanism to keep connection alive
- ✅ Comprehensive error handling
- ✅ Detailed logging for debugging
- ✅ Rate limit handling
- ✅ Health check endpoints

These improvements should prevent most common issues that cause bots to go offline on Render. 