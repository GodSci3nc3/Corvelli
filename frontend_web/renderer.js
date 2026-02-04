// Backend URL
const BACKEND_URL = 'http://localhost:3000';

// State
let connected = false;
let currentHostname = '';
let aiEnabled = false;
let commandCount = 0;

// DOM Elements
const deviceType = document.getElementById('device-type');
const deviceName = document.getElementById('device-name');
const connectionType = document.getElementById('connection-type');
const connectBtn = document.getElementById('connect-btn');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
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
clearBtn.addEventListener('click', clearTerminal);

// Initialize
updatePrompt();

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
            addToTerminal(data.output, 'result');
        } else {
            addToTerminal(`Connection failed: ${data.error}`, 'error');
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
