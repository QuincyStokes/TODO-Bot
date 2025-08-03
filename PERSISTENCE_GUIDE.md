# 🔄 Data Persistence Guide

This guide explains how to keep your todo list data across Render deployments.

## 🚨 The Problem: Ephemeral Storage

Render's free tier uses **ephemeral storage** - data gets wiped on every deployment. This means:
- ✅ Your bot works perfectly
- ❌ All todo lists disappear when you redeploy
- ❌ No data persistence between updates

## 💡 Solutions

### **Option 1: SQLite Database (Recommended)**

The bot now includes built-in SQLite database support that's more reliable than JSON files.

#### **How it works:**
- Uses SQLite database stored in `/opt/render/project/src/data/todo_bot.db`
- Automatically migrates existing JSON data
- More robust than file-based storage
- Better performance for larger datasets

#### **Setup:**
1. **Enable database mode** (default):
   ```bash
   USE_DATABASE=true
   ```

2. **Deploy to Render** - the bot will automatically:
   - Create the database on first run
   - Migrate any existing JSON data
   - Use database for all future operations

#### **Benefits:**
- ✅ Data persists better than JSON files
- ✅ Automatic migration from old data
- ✅ Better performance
- ✅ More reliable storage

---

### **Option 2: External Cloud Database**

For maximum reliability, use a cloud database service.

#### **A. Supabase (Free Tier)**
1. Create account at [supabase.com](https://supabase.com)
2. Create a new project
3. Get your database URL and API key
4. Add environment variables:
   ```bash
   DATABASE_URL=postgresql://username:password@host:port/database
   SUPABASE_KEY=your_api_key
   ```

#### **B. PlanetScale (Free Tier)**
1. Create account at [planetscale.com](https://planetscale.com)
2. Create a new database
3. Get your connection string
4. Add environment variable:
   ```bash
   DATABASE_URL=mysql://username:password@host:port/database
   ```

#### **C. Railway (Free Tier)**
1. Create account at [railway.app](https://railway.app)
2. Create a PostgreSQL database
3. Get your connection string
4. Add environment variable:
   ```bash
   DATABASE_URL=postgresql://username:password@host:port/database
   ```

---

### **Option 3: Render Persistent Disk (Paid)**

If you upgrade to Render's paid tier, you can use persistent disks:

1. **Upgrade to paid plan** ($7/month)
2. **Add persistent disk** in Render dashboard
3. **Mount disk** to your application
4. **Update DATA_DIR** environment variable:
   ```bash
   DATA_DIR=/opt/render/project/src/data
   ```

---

### **Option 4: Manual Backup/Restore**

For simple cases, manually backup and restore data:

#### **Backup before deployment:**
```bash
# Download your data file from Render
curl -o todo_lists.json https://your-app.onrender.com/data/todo_lists.json
```

#### **Restore after deployment:**
```bash
# Upload your data file to Render
curl -X POST -F "file=@todo_lists.json" https://your-app.onrender.com/upload
```

---

## 🔧 Implementation Details

### **Current Bot Features:**

#### **1. Automatic Database Migration**
- Detects existing JSON data
- Migrates to SQLite database
- Creates backup of old data
- Seamless transition

#### **2. Fallback System**
- Database fails → falls back to JSON
- JSON fails → starts fresh
- No data loss scenarios

#### **3. Environment Variables**
```bash
# Enable/disable database (default: true)
USE_DATABASE=true

# Data directory path
DATA_DIR=/opt/render/project/src/data

# Database file path (auto-generated)
DATABASE_PATH=/opt/render/project/src/data/todo_bot.db
```

#### **4. Backup System**
- Automatic backups before saves
- Migration backups
- Error recovery

---

## 📊 Comparison of Options

| Option | Cost | Reliability | Setup | Maintenance |
|--------|------|-------------|-------|-------------|
| **SQLite Database** | Free | ⭐⭐⭐⭐ | Easy | Low |
| **Supabase** | Free | ⭐⭐⭐⭐⭐ | Medium | Low |
| **PlanetScale** | Free | ⭐⭐⭐⭐⭐ | Medium | Low |
| **Railway** | Free | ⭐⭐⭐⭐⭐ | Medium | Low |
| **Render Disk** | $7/month | ⭐⭐⭐⭐⭐ | Easy | Low |
| **Manual Backup** | Free | ⭐⭐ | Hard | High |

---

## 🚀 Quick Start

### **For Most Users (Recommended):**

1. **Deploy with default settings** - SQLite database is enabled by default
2. **Monitor logs** for migration messages
3. **Test data persistence** by creating lists and redeploying

### **For Advanced Users:**

1. **Choose external database** (Supabase/PlanetScale/Railway)
2. **Set up database** and get connection string
3. **Add environment variables** to Render
4. **Deploy and test**

---

## 🔍 Troubleshooting

### **Data Still Getting Wiped?**

1. **Check environment variables:**
   ```bash
   USE_DATABASE=true
   DATA_DIR=/opt/render/project/src/data
   ```

2. **Check Render logs** for database initialization messages

3. **Verify data directory** exists and is writable

4. **Test with external database** if SQLite isn't working

### **Migration Issues?**

1. **Check backup files** - old data is backed up as `.backup`
2. **Restore from backup** if needed
3. **Check database file** exists in data directory

### **Performance Issues?**

1. **Switch to external database** for better performance
2. **Optimize queries** (already done in current implementation)
3. **Monitor database size** and clean up if needed

---

## 📈 Monitoring

### **Check Data Persistence:**

1. **Create test lists** before deployment
2. **Redeploy** your application
3. **Verify lists still exist** after deployment
4. **Check logs** for database messages

### **Monitor Database Health:**

```bash
# Check database file exists
ls -la /opt/render/project/src/data/todo_bot.db

# Check database size
du -h /opt/render/project/src/data/todo_bot.db

# Check backup files
ls -la /opt/render/project/src/data/*.backup
```

---

## 🎯 Recommendation

**For most users:** Start with the built-in SQLite database (default). It's free, reliable, and handles most use cases.

**For production apps:** Use an external database like Supabase or PlanetScale for maximum reliability.

**For simple testing:** The current implementation should work fine for most scenarios. 