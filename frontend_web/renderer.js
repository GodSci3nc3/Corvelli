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
    
    // Filter only real connected devices (exclude default/mock sessions)
    const realDevices = devices.filter(d => 
        d.device_id !== 'default' && 
        (d.connected || d.credentials?.host)
    );
    
    if (realDevices.length === 0) {
        renderEmptyDeviceList();
        return;
    }
    
    realDevices.forEach(device => {
        const item = createDeviceItem(device);
        deviceList.appendChild(item);
    });
}

function renderEmptyDeviceList() {
    loadConfigTemplates();
}

async function loadConfigTemplates() {
    try {
        const response = await fetch(`${BACKEND_URL}/templates`);
        const data = await response.json();
        
        if (data.success && data.templates) {
            renderConfigTemplates(data.templates);
        } else {
            renderNoTemplatesMessage();
        }
    } catch (error) {
        console.error('Error loading templates:', error);
        renderNoTemplatesMessage();
    }
}

function renderConfigTemplates(templates) {
    const settingsSVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 6v6M5.6 5.6l4.2 4.2m4.2 4.2l4.2 4.2M1 12h6m6 0h6M5.6 18.4l4.2-4.2m4.2-4.2l4.2-4.2"/></svg>';
    
    deviceList.innerHTML = `
        <div class="templates-header">
            <h3><span class="template-icon" style="margin-right: 8px;">${settingsSVG}</span>Config Templates</h3>
            <p>Quick network configuration templates</p>
        </div>
    `;
    
    // Templates is an array of objects with {id, name, description, icon, ...}
    templates.forEach(template => {
        const item = createTemplateItem(template.id, template);
        deviceList.appendChild(item);
    });
}
}

function createTemplateItem(key, template) {
    const item = document.createElement('div');
    item.className = 'device-item';
    
    const iconSVG = getTemplateIconSVG(template.icon);
    
    item.innerHTML = `
        <div class="device-item-header">
            <div class="device-item-name">
                <span class="template-icon">${iconSVG}</span>
                <span>${template.name}</span>
            </div>
        </div>
        <div class="device-item-info">${template.description}</div>
        <div class="device-item-last">${template.vendors.join(', ').toUpperCase()}</div>
    `;
    
    item.onclick = () => {
        if (!connected) {
            const warningSVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
            addToTerminal(`<span style="color: #ffa500;">${warningSVG}</span> Connect to a device first to apply templates`, 'warning');
        } else {
            showTemplateDialog(key, template);
        }
    };
    
    return item;
}

function getTemplateIconSVG(iconName) {
    const icons = {
        network: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="2"/><circle cx="12" cy="5" r="2"/><circle cx="19" cy="12" r="2"/><circle cx="5" cy="12" r="2"/><circle cx="12" cy="19" r="2"/><line x1="12" y1="7" x2="12" y2="10"/><line x1="12" y1="14" x2="12" y2="17"/><line x1="14" y1="12" x2="17" y2="12"/><line x1="7" y1="12" x2="10" y2="12"/></svg>',
        link: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
        port: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>',
        lock: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/><circle cx="12" cy="16" r="1"/></svg>',
        gateway: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/></svg>',
        broadcast: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 18a10 10 0 0 1 14 0"/><path d="M8 14a6 6 0 0 1 8 0"/><circle cx="12" cy="11" r="2"/><path d="M12 11V3"/></svg>'
    };
    
    return icons[iconName] || icons.network;
}

function renderNoTemplatesMessage() {
    const settingsSVG = '<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 1v6m0 6v6M5.6 5.6l4.2 4.2m4.2 4.2l4.2 4.2M1 12h6m6 0h6M5.6 18.4l4.2-4.2m4.2-4.2l4.2-4.2"/></svg>';
    
    deviceList.innerHTML = `
        <div class="device-list-empty">
            <div class="device-list-empty-icon">${settingsSVG}</div>
            <div class="device-list-empty-text">No templates available</div>
            <div class="device-list-empty-hint">Connect to a device to get started</div>
        </div>
    `;
}

async function showTemplateDialog(key, template) {
    // TODO: Implement template parameter dialog
    addToTerminal(`Template "${template.name}" selected (dialog coming soon)`, 'info');
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
