# Quick Start Guide - Tiger REST API with Auto Token Refresh

## Current Situation

✅ **New Full REST API is Running** on port 9000
❌ **Token has expired** - needs manual regeneration first
✅ **Auto-refresh will keep it alive** after initial setup

---

## Step 1: Regenerate Expired Token (One-Time)

Since your token has expired, you need to regenerate it from Tiger Brokers:

### Option A: Via Tiger OpenAPI Website

1. Go to [Tiger OpenAPI Developer Portal](https://quant.itigerup.com/)
2. Log in with your Tiger account
3. Navigate to "Developer Info" or "Token Management"
4. Click "Generate Token" or "Regenerate Token"
5. Download the new `tiger_openapi_token.properties` file
6. Replace your current token file:
   ```bash
   cp ~/Downloads/tiger_openapi_token.properties ~/tiger_openapi_token.properties
   # OR wherever your config points to
   ```

### Option B: Via Tiger Trade App (if available)

Some Tiger implementations allow token generation via mobile app.

---

## Step 2: Restart the REST API

After getting a new token:

```bash
# Stop current API
pkill -f tiger_rest_api_full.py

# Start new API
cd /home/trader/tiger-mcp
nohup python tiger_rest_api_full.py > rest_api_full.log 2>&1 &

# Verify it's running
curl http://localhost:9000/health
```

---

## Step 3: Test the API

```bash
# Test authentication
curl -H "Authorization: Bearer client_key_001" \
     http://localhost:9000/api/accounts

# Test market data
curl -X POST http://localhost:9000/api/market/quote \
  -H "Authorization: Bearer client_key_001" \
  -H "Content-Type: application/json" \
  -d '{
    "account": "67686635",
    "symbol": "AAPL"
  }'
```

---

## Step 4: Verify Auto-Refresh is Working

Check the logs:

```bash
tail -f rest_api_full.log
```

You should see:
```
✅ Background token refresh scheduler started
⏰ Next token refresh in 12.0h
```

After 1 minute (first refresh):
```
🔄 Starting scheduled token refresh for all accounts...
✅ Token refresh successful for account 67686635, tiger_id: 20154747
✅ Token refresh completed: 3/3 successful
```

---

## Understanding Token Lifecycle

```
Manual Token Generation (15-day validity)
    ↓
Server starts, waits 1 minute
    ↓
First automatic refresh
    ↓
Every 12 hours thereafter
    ↓
Tiger SDK updates tiger_openapi_token.properties
    ↓
Token stays valid indefinitely (as long as server runs)
```

---

## What Changed from Old API?

### Old API (`tiger_rest_api.py`)
- ❌ No token refresh
- ❌ Created new client per request
- ❌ Token expires in 15 days
- ✅ 6 basic endpoints

### New API (`tiger_rest_api_full.py`)
- ✅ Auto token refresh every 12h
- ✅ Background refresh task
- ✅ Token stays valid forever
- ✅ 22 complete endpoints
- ✅ Full documentation

---

## API Endpoints Summary

### Market Data (6)
- `POST /api/market/quote` - Real-time quotes
- `POST /api/market/kline` - Historical bars
- `POST /api/market/batch` - Batch quotes
- `POST /api/market/search` - Symbol search
- `POST /api/market/option-chain` - Options
- `POST /api/market/status` - Market hours

### Company Info (4)
- `POST /api/info/contracts` - Contract details
- `POST /api/info/financials` - Financial data
- `POST /api/info/corporate-actions` - Dividends/splits
- `POST /api/info/earnings` - Earnings calendar

### Trading (6)
- `POST /api/trade/positions` - Get positions
- `POST /api/trade/account-info` - Account balance
- `POST /api/trade/orders` - Order history
- `POST /api/trade/place-order` - Place order
- `POST /api/trade/modify-order` - Modify order
- `POST /api/trade/cancel-order` - Cancel order

### Account (2)
- `GET /api/accounts` - List accounts
- `POST /api/token/refresh` - Manual refresh

---

## Troubleshooting

### "Token expired" error after restart
→ Token file expired, regenerate from Tiger website (Step 1)

### "Auto-refresh not working"
→ Check logs: `tail -f rest_api_full.log`
→ Look for "Background token refresh scheduler started"

### "Permission denied" error
→ Check API key has correct permissions in code
→ Verify account is in allowed_accounts list

### Need to add more accounts?
Edit `tiger_rest_api_full.py`:
```python
ACCOUNT_MAPPING = {
    "your_new_account": {
        "tiger_id": "your_tiger_id",
        "type": "live",
        "license": "TBHK"
    }
}
```

---

## Complete Documentation

See `docs/REST_API_FULL_REFERENCE.md` for:
- Complete endpoint documentation
- Request/response examples
- Error handling
- Configuration options
- Testing guide

---

## Next Steps

1. ✅ Regenerate token from Tiger website
2. ✅ Restart API with new token
3. ✅ Verify auto-refresh is working
4. ✅ Update your client applications to use new endpoints
5. ✅ Monitor logs for the first 24 hours
6. ✅ After 12 hours, verify first scheduled refresh succeeded

**Your token will now stay valid indefinitely! 🎉**
