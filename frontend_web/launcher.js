const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const { app, dialog } = require('electron');

const isDev = !process.env.PORTABLE_EXECUTABLE_DIR && !process.resourcesPath;
const isPackaged = process.env.PORTABLE_EXECUTABLE_DIR || process.resourcesPath;

let backendPath;
if (isDev) {
  backendPath = path.join(__dirname, '..', 'backend');
} else {
  backendPath = path.join(process.resourcesPath, 'backend');
}

const setupFlagPath = path.join(app.getPath('userData'), '.corvelli-setup-done');

console.log('[Launcher] Starting Corvelli...');
console.log('[Launcher] Backend path:', backendPath);

let nodeProcess = null;
let pythonProcess = null;

function checkCommand(cmd) {
  try {
    execSync(`${cmd} --version`, { stdio: 'pipe' });
    return true;
  } catch {
    return false;
  }
}

async function verifyAndSetupDependencies() {
  const hasPython = checkCommand(process.platform === 'win32' ? 'python' : 'python3');
  const hasNode = checkCommand('node');
  
  if (!hasPython || !hasNode) {
    const missing = [];
    if (!hasPython) missing.push('Python 3.8+');
    if (!hasNode) missing.push('Node.js 18+');
    
    const result = await dialog.showMessageBox({
      type: 'error',
      title: 'Missing Requirements',
      message: `Corvelli requires ${missing.join(' and ')} to run.`,
      detail: 'Click OK to open download pages.',
      buttons: ['OK', 'Cancel']
    });
    
    if (result.response === 0) {
      if (!hasPython) require('electron').shell.openExternal('https://www.python.org/downloads/');
      if (!hasNode) require('electron').shell.openExternal('https://nodejs.org/');
    }
    
    app.quit();
    return false;
  }
  
  if (fs.existsSync(setupFlagPath)) {
    return true;
  }
  
  const setupResult = await dialog.showMessageBox({
    type: 'info',
    title: 'First Run Setup',
    message: 'Installing backend dependencies...',
    detail: 'This only happens once. Takes ~30 seconds.',
    buttons: ['Continue']
  });
  
  try {
    console.log('[Launcher] Installing Python packages...');
    const pipCmd = process.platform === 'win32' ? 'pip' : 'pip3';
    execSync(`${pipCmd} install fastapi uvicorn pydantic paramiko pyserial python-dotenv requests`, {
      cwd: backendPath,
      stdio: 'inherit'
    });
    
    console.log('[Launcher] Installing Node packages...');
    execSync('npm install', {
      cwd: backendPath,
      stdio: 'inherit'
    });
    
    fs.writeFileSync(setupFlagPath, new Date().toISOString());
    
    await dialog.showMessageBox({
      type: 'info',
      title: 'Setup Complete',
      message: 'Corvelli is ready to use!',
      buttons: ['OK']
    });
    
    return true;
    
  } catch (error) {
    console.error('[Launcher] Setup failed:', error);
    await dialog.showMessageBox({
      type: 'error',
      title: 'Setup Failed',
      message: 'Failed to install dependencies',
      detail: error.message,
      buttons: ['OK']
    });
    app.quit();
    return false;
  }
}

function waitForPort(port, maxAttempts = 30) {
  return new Promise((resolve, reject) => {
    const net = require('net');
    let attempts = 0;
    
    const checkPort = () => {
      attempts++;
      const socket = new net.Socket();
      
      socket.setTimeout(1000);
      socket.on('connect', () => {
        socket.destroy();
        console.log(`[Launcher] Port ${port} is ready`);
        resolve();
      });
      
      socket.on('timeout', () => {
        socket.destroy();
        if (attempts < maxAttempts) {
          setTimeout(checkPort, 1000);
        } else {
          reject(new Error(`Port ${port} not ready after ${maxAttempts} attempts`));
        }
      });
      
      socket.on('error', () => {
        if (attempts < maxAttempts) {
          setTimeout(checkPort, 1000);
        } else {
          reject(new Error(`Port ${port} not ready after ${maxAttempts} attempts`));
        }
      });
      
      socket.connect(port, '127.0.0.1');
    };
    
    checkPort();
  });
}

async function startPythonServer() {
  return new Promise((resolve, reject) => {
    console.log('[Launcher] Starting Python connection server...');
    
    const pythonExe = process.platform === 'win32' ? 'python.exe' : 'python3';
    const scriptPath = path.join(backendPath, 'connection_server.py');
    
    if (!fs.existsSync(scriptPath)) {
      console.error('[Launcher] Python script not found:', scriptPath);
      return reject(new Error('Python script not found'));
    }
    
    pythonProcess = spawn(pythonExe, [scriptPath], {
      cwd: backendPath,
      env: { ...process.env, PYTHONUNBUFFERED: '1' }
    });
    
    pythonProcess.stdout.on('data', (data) => {
      console.log('[Python]', data.toString().trim());
    });
    
    pythonProcess.stderr.on('data', (data) => {
      console.error('[Python Error]', data.toString().trim());
    });
    
    pythonProcess.on('error', (error) => {
      console.error('[Launcher] Failed to start Python:', error);
      reject(error);
    });
    
    setTimeout(() => {
      waitForPort(5000)
        .then(() => resolve())
        .catch(reject);
    }, 2000);
  });
}

async function startNodeServer() {
  return new Promise((resolve, reject) => {
    console.log('[Launcher] Starting Node.js API server...');
    
    const nodeExe = process.platform === 'win32' ? 'node.exe' : 'node';
    const scriptPath = path.join(backendPath, 'server.js');
    
    if (!fs.existsSync(scriptPath)) {
      console.error('[Launcher] Node script not found:', scriptPath);
      return reject(new Error('Node script not found'));
    }
    
    nodeProcess = spawn(nodeExe, [scriptPath], {
      cwd: backendPath,
      env: { ...process.env }
    });
    
    nodeProcess.stdout.on('data', (data) => {
      console.log('[Node]', data.toString().trim());
    });
    
    nodeProcess.stderr.on('data', (data) => {
      console.error('[Node Error]', data.toString().trim());
    });
    
    nodeProcess.on('error', (error) => {
      console.error('[Launcher] Failed to start Node:', error);
      reject(error);
    });
    
    setTimeout(() => {
      waitForPort(3000)
        .then(() => resolve())
        .catch(reject);
    }, 2000);
  });
}

async function startServers() {
  const ready = await verifyAndSetupDependencies();
  if (!ready) return;
  
  try {
    await startPythonServer();
    console.log('[Launcher] Python server started successfully');
    
    await startNodeServer();
    console.log('[Launcher] Node.js server started successfully');
    
    console.log('[Launcher] All backend services ready!');
    
    require('./main.js');
    
  } catch (error) {
    console.error('[Launcher] Failed to start servers:', error);
    
    dialog.showMessageBox({
      type: 'error',
      title: 'Error starting Corvelli',
      message: 'Failed to start backend servers',
      detail: error.message,
      buttons: ['OK']
    });
    
    app.quit();
  }
}

process.on('exit', () => {
  console.log('[Launcher] Shutting down backend services...');
  if (pythonProcess) pythonProcess.kill();
  if (nodeProcess) nodeProcess.kill();
});

process.on('SIGINT', () => process.exit(0));
process.on('SIGTERM', () => process.exit(0));

if (require.main === module) {
  app.whenReady().then(startServers);
}

module.exports = { startServers };