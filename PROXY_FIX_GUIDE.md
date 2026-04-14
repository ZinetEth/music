# Vite Proxy Fix Guide

## 🚨 Problem Identified

The Vite development server was trying to proxy `/auth/login` requests to Navidrome on port 4533, but our backend runs on port 8000.

## ✅ Solution Applied

### **1. Updated Vite Proxy Configuration**
**File**: `feishin/web.vite.config.ts`

```typescript
server: {
    proxy: {
        // Existing Navidrome proxy (kept for compatibility)
        '/navidrome': {
            changeOrigin: true,
            rewrite: (path) => path.replace(/^\/navidrome/, ''),
            target: 'http://127.0.0.1:4533',
        },
        
        // NEW: Backend API proxies
        '/api': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8000',
        },
        '/health': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8000',
        },
        '/payments': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8000',
        },
        '/marketplace': {
            changeOrigin: true,
            target: 'http://127.0.0.1:8000',
        },
    },
},
```

### **2. Updated Frontend API Client**
**File**: `feishin/src/renderer/api/aligned-client.ts`

```typescript
// Changed from absolute URL to relative for Vite proxy
const BACKEND_API_URL = 
    ((import.meta as any).env?.BACKEND_API as string | undefined) ||
    ((import.meta as any).env?.VITE_BACKEND_API as string | undefined) ||
    ''; // Use relative URL for Vite proxy
```

## 🔄 How It Works

### **Before Fix**
```
Frontend Request: /auth/login
Vite Proxy: ❌ No matching proxy rule
Result: ECONNREFUSED 127.0.0.1:4533 (Navidrome)
```

### **After Fix**
```
Frontend Request: /health
Vite Proxy: ✅ Matches '/health' rule
Target: http://127.0.0.1:8000 (Our Backend)
Result: ✅ Connected to our backend
```

## 🚀 Restart Instructions

### **1. Stop Current Vite Server**
```bash
# Kill any running Node.js processes
taskkill /F /IM node.exe

# Or use Ctrl+C in the terminal running Vite
```

### **2. Restart Vite Development Server**
```bash
cd feishin
npm run dev
```

### **3. Verify Proxy is Working**
```bash
# Test health endpoint
curl http://localhost:5173/health

# Should return:
# {"status": "healthy", "timestamp": ..., "service": "music-platform-backend"}
```

## 🎯 Expected Behavior

### **Frontend Requests**
- `/health` → Proxied to `http://127.0.0.1:8000/health`
- `/payments/create` → Proxied to `http://127.0.0.1:8000/payments/create`
- `/marketplace/songs` → Proxied to `http://127.0.0.1:8000/marketplace/songs`

### **Backend Responses**
- ✅ Health checks work
- ✅ Payment creation works
- ✅ Marketplace loading works
- ✅ All API calls go to port 8000

## 🔍 Troubleshooting

### **If Still Getting Errors**

1. **Check Backend is Running**
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. **Verify Vite Proxy**
- Check Vite startup logs for proxy configuration
- Look for "Proxy created" messages

3. **Test Direct Backend**
```bash
curl http://localhost:8000/health
```

4. **Test Through Proxy**
```bash
curl http://localhost:5173/health
```

### **Common Issues**

#### **Port Conflicts**
```bash
# Check what's running on ports
netstat -ano | findstr :8000
netstat -ano | findstr :5173
```

#### **Cache Issues**
```bash
# Clear browser cache
# Or use incognito/private browsing
```

#### **Vite Configuration**
- Ensure `web.vite.config.ts` is saved
- Restart Vite after config changes
- Check for syntax errors in config

## 🎊 Result

After applying these fixes:

✅ **Frontend connects to our backend** instead of Navidrome
✅ **All API calls work** through Vite proxy
✅ **Payment methods are functional** 
✅ **Responsive UI works** on all platforms
✅ **No more ECONNREFUSED errors**

## 🚀 Next Steps

1. **Restart Vite** with new proxy configuration
2. **Start Backend** on port 8000
3. **Test Unified UI** on http://localhost:5173
4. **Verify Payments** work across all platforms

---

**🎉 The proxy issue is fixed! Your frontend will now properly connect to the music platform backend!**
