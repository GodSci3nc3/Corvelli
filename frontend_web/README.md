# Corvelli Web Frontend

## How to run

### Prerequisites
1. Backend must be running on port 3000
   ```bash
   cd backend
   node server.js
   ```

### Run Electron App
```bash
cd frontend_web
npm start
```

### Development mode (with DevTools)
```bash
npm run dev
```

## Features
- Modern Electron interface
- Same functionality as Tkinter version
- SSH and Serial connections
- AI-powered command assistance
- Typewriter effect for output
- Clean, professional design

## Architecture
- `main.js`: Electron main process
- `renderer.js`: Frontend logic
- `index.html`: UI structure
- `styles.css`: Modern styling
- `preload.js`: Security layer

## Backend Connection
Connects to Node.js backend at http://localhost:3000
All endpoints remain the same:
- POST /execute (Serial)
- POST /ssh-execute (SSH)
- POST /disconnect
