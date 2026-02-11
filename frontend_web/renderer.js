// Backend URL
const BACKEND_URL = 'http://localhost:3000';

// State
let connected = false;
let currentHostname = '';
let currentDeviceId = null;
let aiEnabled = false;
let commandCount = 0;

// DOM Elements
const deviceType = document.getElementById('device-type');
const deviceName = document.getElementById('device-name');
const connectionType = document.getElementById('connection-type');
const connectBtn = document.getElementById('connect-btn');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const deviceList = document.getElementById('device-list');
const terminal = document.getElementById('terminal');
const commandInput = document.getElementById('command-input');
const sendBtn = document.getElementById('send-btn');
const aiToggle = document.getElementById('ai-toggle');
const clearBtn = document.getElementById('clear-btn');
const prompt = document.getElementById('prompt');
const connectionStatus = document.getElementById('connection-status');
const commandCounter = document.getElementById('command-counter');

// Event Listeners
connectBtn.addEventListener('click', toggleConnection);
sendBtn.addEventListener('click', sendCommand);
commandInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendCommand();
});
aiToggle.addEventListener('click', toggleAI);
clearBtn.addEventListener('click', closeCurrentDevice);

// Initialize
updatePrompt();
loadDeviceList();

// Functions
function updatePrompt() {
    prompt.textContent = currentHostname ? `${currentHostname}#` : '';
}

function updateStatus(isConnected, text) {
    connected = isConnected;
    statusText.textContent = text;
    connectionStatus.textContent = text;
    
    if (isConnected) {
        statusDot.classList.add('connected');
        connectBtn.textContent = 'Disconnect';
        connectBtn.classList.add('btn-secondary');
        connectBtn.classList.remove('btn-primary');
    } else {
        statusDot.classList.remove('connected');
        connectBtn.textContent = 'Connect';
        connectBtn.classList.remove('btn-secondary');
        connectBtn.classList.add('btn-primary');
    }
}

function addToTerminal(text, type = 'result') {
    const line = document.createElement('div');
    line.className = `terminal-line output-${type}`;
    line.textContent = text;
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
}

function clearTerminal() {
    terminal.innerHTML = '';
}

function toggleAI() {
    aiEnabled = !aiEnabled;
    aiToggle.textContent = aiEnabled ? 'AI: ON' : 'AI: OFF';
    aiToggle.dataset.enabled = aiEnabled;
    
    if (aiEnabled) {
        aiToggle.classList.remove('btn-secondary');
        aiToggle.classList.add('btn-primary');
    } else {
        aiToggle.classList.remove('btn-primary');
        aiToggle.classList.add('btn-secondary');
    }
}

async function toggleConnection() {
    if (connected) {
        await disconnect();
    } else {
        await connect();
    }
}

async function connect() {
    const connType = connectionType.value;
    
    if (connType === 'SSH') {
        await connectSSH();
    } else if (connType === 'Console') {
        await connectSerial();
    } else {
        addToTerminal(`Connection type ${connType} not implemented yet.`, 'error');
    }
}

async function connectSSH() {
    // Show credentials dialog
    const credentials = await showSSHDialog();
    if (!credentials) return;
    
    try {
        addToTerminal('Connecting via SSH...', 'command');
        
        const response = await fetch(`${BACKEND_URL}/ssh-execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                host: credentials.host,
                username: credentials.username,
                password: credentials.password,
                command: 'show version | include Software',
                useAI: false
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentHostname = deviceName.value || 'Switch';
            updatePrompt();
            updateStatus(true, 'Connected via SSH');
            addToTerminal('Connected successfully', 'success');
            addToTerminal(data.output, 'result');
        } else {
            addToTerminal(`Connection failed: ${data.error}`, 'error');
        }
    } catch (error) {
        addToTerminal(`Error: ${error.message}`, 'error');
    }
}

async function connectSerial() {
    try {
        addToTerminal('Connecting via Serial...', 'command');
        
        // First, establish connection to Python server
        const connectResponse = await fetch(`${BACKEND_URL}/serial-connect`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                port: '/dev/ttyUSB0',
                baudrate: 9600,
                password: ''
            })
        });
        
        const connectData = await connectResponse.json();
        
        if (!connectData.success) {
            addToTerminal(`Connection failed: ${connectData.error}`, 'error');
            return;
        }
        
        // Now execute test command
        const response = await fetch(`${BACKEND_URL}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                command: 'show version | include Software',
                useAI: false
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentHostname = deviceName.value || 'Switch';
            updatePrompt();
            updateStatus(true, 'Connected via Serial');
            addToTerminal('Connected successfully', 'success');
            if (data.output && typeof data.output === 'string') {
                addToTerminal(data.output, 'result');
            }
        } else {
            addToTerminal(`Execution failed: ${data.error}`, 'error');
        }
    } catch (error) {
        addToTerminal(`Error: ${error.message}`, 'error');
    }
}

async function disconnect() {
    try {
        await fetch(`${BACKEND_URL}/disconnect`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        currentHostname = '';
        updatePrompt();
        updateStatus(false, 'Disconnected');
        addToTerminal('Connection closed.', 'success');
    } catch (error) {
        addToTerminal(`Error disconnecting: ${error.message}`, 'error');
    }
}

async function sendCommand() {
    const command = commandInput.value.trim();
    if (!command) return;
    
    commandInput.value = '';
    addToTerminal(`${currentHostname || ''}# ${command}`, 'command');
    
    try {
        const connType = connectionType.value;
        const endpoint = connType === 'SSH' ? '/ssh-execute' : '/execute';
        
        const response = await fetch(`${BACKEND_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                command: command,
                useAI: aiEnabled
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Typewriter effect
            await typewriterEffect(data.output);
            commandCount++;
            commandCounter.textContent = `Commands: ${commandCount}`;
        } else {
            addToTerminal(`Error: ${data.error}`, 'error');
        }
    } catch (error) {
        addToTerminal(`Error: ${error.message}`, 'error');
    }
}

async function typewriterEffect(text) {
    const lines = text.split('\n');
    for (const line of lines) {
        const elem = document.createElement('div');
        elem.className = 'terminal-line output-result';
        terminal.appendChild(elem);
        
        for (let i = 0; i < line.length; i++) {
            elem.textContent += line[i];
            terminal.scrollTop = terminal.scrollHeight;
            await sleep(5);
        }
        elem.textContent += '\n';
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function showSSHDialog() {
    return new Promise((resolve) => {
        // Create modal
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        `;
        
        const dialog = document.createElement('div');
        dialog.style.cssText = `
            background: var(--dark-bg);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            width: 400px;
            color: var(--light-text);
        `;
        
        dialog.innerHTML = `
            <h2 style="margin-bottom: 20px; font-size: 16px;">SSH Credentials</h2>
            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px; font-size: 11px;">Host/IP:</label>
                <input type="text" id="ssh-host" value="192.168.1.10" style="width: 100%; padding: 8px; background: var(--terminal-bg); border: 1px solid var(--border); color: var(--light-text); border-radius: 4px; font-family: inherit;">
            </div>
            <div style="margin-bottom: 15px;">
                <label style="display: block; margin-bottom: 5px; font-size: 11px;">Username:</label>
                <input type="text" id="ssh-username" value="admin" style="width: 100%; padding: 8px; background: var(--terminal-bg); border: 1px solid var(--border); color: var(--light-text); border-radius: 4px; font-family: inherit;">
            </div>
            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 5px; font-size: 11px;">Password:</label>
                <input type="password" id="ssh-password" value="admin123" style="width: 100%; padding: 8px; background: var(--terminal-bg); border: 1px solid var(--border); color: var(--light-text); border-radius: 4px; font-family: inherit;">
            </div>
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button id="ssh-cancel" class="btn btn-secondary">Cancel</button>
                <button id="ssh-connect" class="btn btn-primary">Connect</button>
            </div>
        `;
        
        modal.appendChild(dialog);
        document.body.appendChild(modal);
        
        const hostInput = dialog.querySelector('#ssh-host');
        const userInput = dialog.querySelector('#ssh-username');
        const passInput = dialog.querySelector('#ssh-password');
        
        dialog.querySelector('#ssh-connect').onclick = () => {
            const creds = {
                host: hostInput.value.trim(),
                username: userInput.value.trim(),
                password: passInput.value
            };
            document.body.removeChild(modal);
            resolve(creds);
        };
        
        dialog.querySelector('#ssh-cancel').onclick = () => {
            document.body.removeChild(modal);
            resolve(null);
        };
        
        hostInput.focus();
    });
}

// ============================================================
// DEVICE LIST MANAGEMENT
// ============================================================

async function loadDeviceList() {
    try {
        const response = await fetch(`${BACKEND_URL}/devices`);
        const data = await response.json();
        
        if (data.success && data.devices) {
            renderDeviceList(data.devices);
        } else {
            renderEmptyDeviceList();
        }
    } catch (error) {
        console.error('Error loading devices:', error);
        renderEmptyDeviceList();
    }
}

function renderDeviceList(devices) {
    deviceList.innerHTML = '';
    
    if (devices.length === 0) {
        renderEmptyDeviceList();
        return;
    }
    
    devices.forEach(device => {
        const item = createDeviceItem(device);
        deviceList.appendChild(item);
    });
}

function renderEmptyDeviceList() {
    deviceList.innerHTML = `
        <div class="device-list-empty">
            <div class="device-list-empty-icon">+</div>
            <div class="device-list-empty-text">No devices connected</div>
            <div class="device-list-empty-hint">Click "Connect" to add a device</div>
        </div>
    `;
}

function createDeviceItem(device) {
    const item = document.createElement('div');
    item.className = 'device-item';
    
    const hostname = device.device_hostname || 'Unknown';
    const vendor = device.vendor || 'Unknown';
    const deviceOS = device.device_os || '';
    const connected = device.connected;
    const address = device.credentials?.host || 'N/A';
    const username = device.credentials?.username || '';
    const messageCount = device.message_count || 0;
    
    item.innerHTML = `
        <div class="device-item-header">
            <div class="device-item-name">
                <div class="device-item-status ${connected ? 'connected' : ''}"></div>
                <span>${hostname}</span>
            </div>
            <div class="device-item-vendor">${vendor.toUpperCase()}${deviceOS ? ' ' + deviceOS : ''}</div>
        </div>
        <div class="device-item-info">${address}${username ? ' • ' + username : ''}</div>
        <div class="device-item-last">${connected ? messageCount + ' commands' : 'Disconnected'}</div>
    `;
    
    item.onclick = () => openDevice(device);
    
    return item;
}

function openDevice(device) {
    currentDeviceId = device.device_id;
    currentHostname = device.device_hostname || device.credentials?.host || 'Device';
    connected = device.connected;
    
    // Update UI
    deviceName.value = currentHostname;
    updatePrompt();
    updateStatus(connected, connected ? 'Connected' : 'Disconnected');
    
    // Switch views
    deviceList.classList.add('hidden');
    terminal.classList.remove('hidden');
    
    // Clear terminal for this device
    terminal.innerHTML = '';
    addToTerminal(`Connected to ${currentHostname}`, 'success');
}

function closeCurrentDevice() {
    // Switch back to device list
    terminal.classList.add('hidden');
    deviceList.classList.remove('hidden');
    
    currentDeviceId = null;
    currentHostname = '';
    connected = false;
    
    updatePrompt();
    updateStatus(false, 'Disconnected');
    
    // Reload device list
    loadDeviceList();
}
