# How to Run Tiger REST API

## Quick Start (Choose One Method)

---

## Method 1: Foreground (Development) 🔧

**Best for**: Testing, development, seeing logs live

```bash
cd /home/trader/tiger-mcp
python tiger_rest_api_full.py
```

**Pros:**
- ✅ See logs in real-time
- ✅ Easy to stop (Ctrl+C)

**Cons:**
- ❌ Stops when you close terminal
- ❌ Stops when SSH disconnects

---

## Method 2: Background (Recommended) ⭐

**Best for**: Production, keeping it running 24/7

```bash
cd /home/trader/tiger-mcp
nohup python tiger_rest_api_full.py > rest_api_full.log 2>&1 &
```

**Pros:**
- ✅ Runs in background
- ✅ Continues after terminal closes
- ✅ Simple to use

**Cons:**
- ❌ Doesn't auto-restart on crash
- ❌ Doesn't start on system reboot

### Managing Background Process

**Check if running:**
```bash
ps aux | grep tiger_rest_api_full | grep -v grep
# Or
curl http://localhost:9000/health
```

**View logs:**
```bash
tail -f rest_api_full.log
# Or last 50 lines
tail -50 rest_api_full.log
```

**Stop it:**
```bash
pkill -f tiger_rest_api_full.py
```

**Restart it:**
```bash
pkill -f tiger_rest_api_full.py
cd /home/trader/tiger-mcp
nohup python tiger_rest_api_full.py > rest_api_full.log 2>&1 &
```

---

## Method 3: Screen Session 🖥️

**Best for**: Long-running process you want to check on

```bash
# Start in screen
cd /home/trader/tiger-mcp
screen -S tiger-api
python tiger_rest_api_full.py

# Detach: Press Ctrl+A then D
```

**Reattach to see logs:**
```bash
screen -r tiger-api
```

**List all screens:**
```bash
screen -ls
```

**Kill screen:**
```bash
screen -X -S tiger-api quit
```

---

## Method 4: Systemd Service (Production) 🏢

**Best for**: Production deployment, auto-start on boot

### Setup (One-time)

```bash
# Copy service file
sudo cp /home/trader/tiger-mcp/tiger-api.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable tiger-api
```

### Usage

**Start:**
```bash
sudo systemctl start tiger-api
```

**Stop:**
```bash
sudo systemctl stop tiger-api
```

**Restart:**
```bash
sudo systemctl restart tiger-api
```

**Check status:**
```bash
sudo systemctl status tiger-api
```

**View logs:**
```bash
sudo journalctl -u tiger-api -f
# Or
tail -f /home/trader/tiger-mcp/rest_api_full.log
```

**Pros:**
- ✅ Auto-restarts on crash
- ✅ Starts on system boot
- ✅ Proper service management
- ✅ System-level integration

**Cons:**
- ❌ Requires sudo/root access
- ❌ Slightly more complex setup

---

## Quick Commands Reference

| Task | Command |
|------|---------|
| **Start (background)** | `cd /home/trader/tiger-mcp && nohup python tiger_rest_api_full.py > rest_api_full.log 2>&1 &` |
| **Check if running** | `curl http://localhost:9000/health` |
| **View logs** | `tail -f /home/trader/tiger-mcp/rest_api_full.log` |
| **Stop** | `pkill -f tiger_rest_api_full.py` |
| **Get PID** | `ps aux \| grep tiger_rest_api_full \| grep -v grep` |
| **Test endpoint** | `curl http://localhost:9000/health` |

---

## Verify It's Running

### Method 1: Check Process
```bash
ps aux | grep tiger_rest_api_full | grep -v grep
```

**Expected output:**
```
trader   123456  0.5  0.8  616852 143972 ?  SNl  00:08  0:02 python tiger_rest_api_full.py
```

### Method 2: Check Port
```bash
lsof -i :9000
```

**Expected output:**
```
COMMAND   PID   USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
python  123456 trader    6u  IPv4  12345      0t0  TCP *:9000 (LISTEN)
```

### Method 3: Health Check
```bash
curl http://localhost:9000/health
```

**Expected output:**
```json
{
  "status": "healthy",
  "service": "Tiger MCP REST API - Full Edition",
  "version": "2.0.0"
}
```

---

## Troubleshooting

### Port Already in Use
```bash
# Find what's using port 9000
lsof -i :9000

# Kill it
kill -9 <PID>
```

### Can't Find Python
```bash
# Check Python location
which python3

# Use full path
/usr/bin/python3 tiger_rest_api_full.py
```

### Permission Denied
```bash
# Make sure you're in the right directory
cd /home/trader/tiger-mcp

# Check file exists
ls -la tiger_rest_api_full.py
```

### Token Expired Error
```bash
# Check token file
cat tiger_openapi_token.properties

# If expired, regenerate from Tiger website
# Then restart API
```

---

## My Recommendation

For **your use case** (keeping it running 24/7), use **Method 2 (Background)**:

```bash
cd /home/trader/tiger-mcp
nohup python tiger_rest_api_full.py > rest_api_full.log 2>&1 &
echo "API started! Check status:"
sleep 2
curl http://localhost:9000/health
```

Then check it's working:
```bash
tail -f rest_api_full.log
```

You should see:
```
🚀 Tiger MCP REST API Server starting...
✅ Background token refresh scheduler started
INFO: Uvicorn running on http://0.0.0.0:9000
```

---

## Access Your API

Once running, you can access:

- **Health Check**: http://localhost:9000/health
- **Interactive Docs**: http://localhost:9000/docs
- **API Base**: http://localhost:9000

**From other machines** (if firewall allows):
- http://YOUR_SERVER_IP:9000

---

**Questions? Check the logs!**
```bash
tail -50 rest_api_full.log
```
