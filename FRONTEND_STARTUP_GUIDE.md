# Frontend Startup Guide

## **How to Start the Music Platform Frontend**

### **Option 1: Use the Batch File (Easiest)**
```bash
cd music-platform
start_frontend.bat
```

### **Option 2: Manual Command**
```bash
cd music-platform/feishin
npm run dev:remote
```

### **Option 3: Direct Vite Command**
```bash
cd music-platform/feishin
npx vite --config remote.vite.config.ts --host 0.0.0.0 --port 5173
```

## **What You'll See**

### **Frontend Features**
- **Unified Responsive UI**: Same experience on Telegram, mobile, and desktop
- **Ethiopian Music Platform**: Professional branding and design
- **Working Payment Methods**: Telebirr H5, M-Pesa, and Legacy Telebirr
- **Real-time Backend Status**: Shows if backend is online/offline
- **Error Handling**: Graceful error pages with troubleshooting

### **Access Points**
- **Main URL**: http://localhost:5173
- **Health Check**: http://localhost:5173/health
- **API Docs**: http://localhost:8000/docs (if backend is running)

## **Prerequisites**

### **1. Backend Should Be Running**
```bash
cd music-platform/backend
start_backend.bat
# OR
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### **2. Node.js Should Be Installed**
```bash
node --version
npm --version
```

### **3. Dependencies Should Be Installed**
```bash
cd music-platform/feishin
npm install
```

## **Troubleshooting**

### **Common Issues**

#### **Port 5173 Already in Use**
```bash
# Kill existing processes
taskkill /F /IM node.exe

# Or use different port
npx vite --config remote.vite.config.ts --port 5174
```

#### **Backend Not Responding**
```bash
# Check backend is running
curl http://localhost:8000/health

# Start backend if needed
cd backend && start_backend.bat
```

#### **Module Not Found**
```bash
# Install dependencies
cd feishin
npm install

# Clear cache
rm -rf node_modules/.vite
npm run dev:remote
```

#### **Proxy Errors**
```bash
# Check Vite proxy configuration
# File: feishin/web.vite.config.ts
# Should include proxies for /api, /health, /payments, /marketplace, /auth
```

## **Expected Output**

When the frontend starts successfully, you should see:

```
  VITE v5.x.x  ready in xxx ms

  Local:   http://localhost:5173/
  Network: http://192.168.x.x:5173/
  press h to show help
```

## **Testing the Frontend**

### **1. Open Browser**
Navigate to http://localhost:5173

### **2. Check Features**
- **Home Page**: Ethiopian music platform dashboard
- **Payments Page**: Click "Manage Payments" to test payment methods
- **Marketplace Page**: Browse music and make purchases
- **Responsive Design**: Resize browser to test mobile/tablet views

### **3. Test Payment Flow**
1. Go to Payments page
2. Select payment provider (Telebirr H5 recommended)
3. Choose payment type (Subscription, Wallet, or Song)
4. See payment processing and confirmation

### **4. Test Backend Integration**
- Check backend status on home page
- Test health endpoint connectivity
- Verify API calls work through proxy

## **Development Tips**

### **Hot Reload**
- Changes to React components automatically refresh
- CSS changes update without full reload
- Backend changes require backend restart

### **Debug Tools**
- **Browser DevTools**: F12 for console and network tabs
- **Vite Dev Server**: Shows compilation errors
- **React DevTools**: Install browser extension for React debugging

### **Mobile Testing**
- Use browser dev tools (F12) to simulate mobile devices
- Test responsive design at different screen sizes
- Verify touch interactions work properly

---

**Frontend is ready to run! Use one of the startup options above to enjoy your unified music platform!**
