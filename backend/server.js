import express from 'express';
import OpenAI from 'openai';
import { exec } from 'child_process';
import { promisify } from 'util';
import dotenv from 'dotenv';
import fetch from 'node-fetch';
import fs from 'fs';
import path from 'path';
import os from 'os';
import { getAvailableTemplates, applyTemplate } from './templates.js';

dotenv.config();

const execAsync = promisify(exec);

// ============================================================================
// PERSISTENCE - Session Storage
// ============================================================================

const SESSIONS_DIR = path.join(process.cwd(), 'sessions');

// Create sessions directory if it doesn't exist
if (!fs.existsSync(SESSIONS_DIR)) {
  fs.mkdirSync(SESSIONS_DIR, { recursive: true });
  console.log('[Persistence] Created sessions directory:', SESSIONS_DIR);
}

function getSessionFilePath(sessionId) {
  // Sanitize sessionId for filename (remove special chars)
  const sanitized = sessionId.replace(/[^a-zA-Z0-9-_.]/g, '_');
  return path.join(SESSIONS_DIR, `${sanitized}.json`);
}

function saveSession(session) {
  try {
    const filePath = getSessionFilePath(session.connectionId);
    const data = {
      sessionId: session.connectionId,
      deviceId: session.deviceId,
      deviceHostname: session.deviceHostname,
      connected: session.connected,
      connectionType: session.connectionType,
      vendor: session.vendor,
      deviceOS: session.deviceOS,
      lastPrompt: session.lastPrompt,
      conversationHistory: session.conversationHistory,
      credentials: {
        host: session.credentials.host,
        username: session.credentials.username,
        port: session.credentials.port
        // NOTE: Password is NOT saved for security
      },
      lastActivity: session.lastActivity,
      createdAt: session.createdAt || new Date().toISOString()
    };
    
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
    console.log('[Persistence] Saved session:', session.connectionId);
  } catch (error) {
    console.error('[Persistence] Error saving session:', error.message);
  }
}

function loadSessions() {
  try {
    const files = fs.readdirSync(SESSIONS_DIR);
    const loadedSessions = [];
    
    for (const file of files) {
      if (!file.endsWith('.json')) continue;
      
      try {
        const filePath = path.join(SESSIONS_DIR, file);
        const data = JSON.parse(fs.readFileSync(filePath, 'utf8'));
        
        // Restore session
        const session = new ChatSession(data.sessionId);
        session.deviceId = data.deviceId;
        session.deviceHostname = data.deviceHostname;
        session.connected = false; // Never restore as connected (requires re-auth)
        session.connectionType = data.connectionType;
        session.vendor = data.vendor;
        session.deviceOS = data.deviceOS;
        session.lastPrompt = data.lastPrompt;
        session.conversationHistory = data.conversationHistory || [];
        session.credentials = data.credentials || {};
        session.lastActivity = data.lastActivity;
        session.createdAt = data.createdAt;
        
        sessions.set(data.sessionId, session);
        loadedSessions.push(data.sessionId);
      } catch (error) {
        console.error(`[Persistence] Error loading ${file}:`, error.message);
      }
    }
    
    if (loadedSessions.length > 0) {
      console.log(`[Persistence] Loaded ${loadedSessions.length} sessions from disk`);
    } else {
      console.log('[Persistence] No previous sessions found');
    }
  } catch (error) {
    console.error('[Persistence] Error loading sessions:', error.message);
  }
}

function deleteSession(sessionId) {
  try {
    const filePath = getSessionFilePath(sessionId);
    if (fs.existsSync(filePath)) {
      fs.unlinkSync(filePath);
      console.log('[Persistence] Deleted session file:', sessionId);
    }
  } catch (error) {
    console.error('[Persistence] Error deleting session:', error.message);
  }
}

// ============================================================================
// SESSION MANAGER
// ============================================================================

class ChatSession {
  constructor(connectionId) {
    this.connectionId = connectionId;
    this.connectionType = null;
    this.connected = false;
    this.credentials = {};
    this.lastPrompt = 'Switch>';
    
    // Vendor detection
    this.vendor = null;
    this.deviceOS = null;
    this.deviceModel = null;
    
    // Device identification
    this.deviceHostname = null;
    this.deviceId = null;
    
    // Activity tracking
    this.lastActivity = Date.now();
    
    // Conversational history
    this.conversationHistory = [];
    this.systemPrompt = null;
  }
  
  resetConversation() {
    this.conversationHistory = [];
    this.systemPrompt = null;
    this.saveToFile();
  }
  
  updateActivity() {
    this.lastActivity = Date.now();
    this.saveToFile();
  }
  
  saveToFile() {
    saveSession(this);
  }
}

const sessions = new Map();

function getOrCreateSession(sessionId = 'default') {
  if (!sessions.has(sessionId)) {
    sessions.set(sessionId, new ChatSession(sessionId));
  }
  return sessions.get(sessionId);
}

// ============================================================================
// DEVICE ID & HOSTNAME DETECTION
// ============================================================================

function generateDeviceId(connectionType, host, username) {
  // Format: ssh-192.168.1.1-admin or serial-COM3-cisco
  return `${connectionType}-${host}-${username}`;
}

async function detectHostname(session) {
  try {
    if (!session.connected) {
      return null;
    }
    
    const response = await fetch(`${PYTHON_SERVER}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        connection_id: session.connectionId,
        command: 'show running-config | include hostname'
      })
    });
    
    if (!response.ok) {
      return null;
    }
    
    const data = await response.json();
    const output = data.output || '';
    
    // Parse hostname from output
    // Cisco: "hostname SW-CORE-01"
    // Juniper: "set system host-name ROUTER-01"
    
    if (output.includes('hostname ')) {
      const match = output.match(/hostname\s+(\S+)/i);
      if (match && match[1]) {
        return match[1];
      }
    }
    
    if (output.includes('host-name ')) {
      const match = output.match(/host-name\s+(\S+)/i);
      if (match && match[1]) {
        return match[1];
      }
    }
    
    return null;
  } catch (error) {
    console.error('[detectHostname] Error:', error.message);
    return null;
  }
}

// Command logging
const logDir = path.join(os.homedir(), '.corvelli');
const logFile = path.join(logDir, 'command_history.jsonl');

if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

// Python Connection Server URL
const PYTHON_SERVER = 'http://127.0.0.1:5000';

let connectionState = {
  type: null,
  connected: false,
  credentials: {},
  lastPrompt: 'Switch>',
  connectionId: 'default'  // ID for persistent connection
};

// Function to extract commands marked with CMD: prefix
function extractCommands(rawOutput) {
  // Strategy 1: Extract lines marked with CMD:
  const cmdLines = rawOutput.split('\n')
    .filter(line => line.trim().startsWith('CMD:'))
    .map(line => line.replace(/^CMD:\s*/i, '').trim());
  
  if (cmdLines.length > 0) {
    return cmdLines.join('\n');
  }
  
  // Strategy 2: Extract from code blocks
  const codeBlockMatch = rawOutput.match(/```(?:cisco|ios)?\s*([\s\S]*?)```/);
  if (codeBlockMatch) {
    return codeBlockMatch[1].trim();
  }
  
  // Strategy 3: Clean and filter like before
  let cleaned = rawOutput
    .replace(/```[\s\S]*?```/g, '')
    .replace(/Cisco.*?:/gi, '')
    .replace(/Commands?:/gi, '')
    .replace(/Response:/gi, '')
    .replace(/Here.*?:/gi, '')
    .replace(/Sure.*?:/gi, '')
    .replace(/.*conversion rules.*/gi, '')
    .split('\n')
    .map(line => line.trim())
    .filter(line => {
      if (!line) return false;
      if (line.startsWith('#')) return false;
      if (line.startsWith('//')) return false;
      if (line.startsWith('*')) return false;
      if (line.match(/^\d+\./) && !line.toLowerCase().includes('ip address')) return false;
      if (line.length > 100) return false; // Too long to be a command
      if (line.toLowerCase().includes('output only')) return false;
      if (line.toLowerCase().includes('no explanation')) return false;
      
      const validStarts = [
        'interface', 'ip', 'no', 'vlan', 'switchport', 'router', 'hostname',
        'enable', 'show', 'description', 'access-list', 'spanning-tree', 'exit',
        'end', 'configure', 'name', 'shutdown', 'network', 'copy', 'reload',
        'banner', 'line', 'service', 'logging', 'snmp'
      ];
      return validStarts.some(cmd => line.toLowerCase().startsWith(cmd));
    })
    .join('\n');

  return cleaned.trim() || rawOutput.trim();
}

// OpenRouter configuration
const openai = new OpenAI({
  baseURL: "https://openrouter.ai/api/v1",
  apiKey: process.env.OPENROUTER_API_KEY || process.env.OPENAI_API_KEY || 'dummy-key',
  defaultHeaders: {
    "HTTP-Referer": "http://localhost:3000",
    "X-Title": "AIConsole"
  }
});

const app = express();
app.use(express.json());

// Helper function to clean unnecessary 'end' commands
function cleanConfigEnd(commands, keepEnd = false) {
  if (keepEnd) return commands; // Keep 'end' for save operations
  
  // Remove standalone 'end' at the end of command sequence
  return commands.replace(/\nend\s*$/i, '').trim();
}

// Rule-based generator for common patterns (fallback)
function generateRuleBased(prompt, switchPrompt = 'Switch>') {
  const lower = prompt.toLowerCase();
  
  // Determine if we need mode escalation based on switch state
  const isUserMode = switchPrompt.endsWith('>') && !switchPrompt.includes('(');
  const isPrivilegedMode = switchPrompt.endsWith('#') && !switchPrompt.includes('(');
  const isConfigMode = switchPrompt.includes('(config)');
  
  // Build prefix commands based on mode
  let prefix = [];
  
  // Only add enable if in user mode and not a show command
  if (isUserMode && !lower.startsWith('show')) {
    prefix.push('enable');
  }
  
  // Only add configure terminal if not already in config mode and not a show command
  if (!isConfigMode && !lower.startsWith('show') && (lower.includes('configure') || lower.includes('vlan') || lower.includes('interface') || lower.includes('hostname') || lower.includes('ip') || lower.includes('port') || lower.includes('ospf'))) {
    prefix.push('configure terminal');
  }
  
  // Show version (Spanish and English)
  if ((lower.includes('mostrar') || lower.includes('show') || lower.includes('ver')) && 
      (lower.includes('versión') || lower.includes('version'))) {
    return 'show version';
  }
  
  // Show routing table (Spanish and English)
  if ((lower.includes('tabla') && lower.includes('enrutamiento')) || 
      (lower.includes('routing') && lower.includes('table')) ||
      (lower.includes('ver') && lower.includes('rutas')) ||
      lower.includes('show ip route')) {
    return 'show ip route';
  }
  
  // Show interfaces
  if ((lower.includes('mostrar') || lower.includes('show') || lower.includes('ver')) && 
      lower.includes('interface')) {
    return 'show ip interface brief';
  }
  
  // Show MAC address table
  if ((lower.includes('mac') && lower.includes('address')) || 
      (lower.includes('tabla') && lower.includes('mac'))) {
    return 'show mac address-table';
  }
  
  // Show ARP table
  if (lower.includes('arp')) {
    return 'show arp';
  }
  
  // VLAN creation (multiple VLANs support)
  if (lower.includes('vlan') && (lower.includes('create') || lower.includes('crear'))) {
    // Match all VLAN definitions: "VLAN 10 named Employees, VLAN 20 named Guests, etc."
    const vlanPattern = /vlan\s+(\d+)\s+named?\s+([\w-]+)/gi;
    const vlans = [];
    let match;
    
    while ((match = vlanPattern.exec(lower)) !== null) {
      vlans.push({ number: match[1], name: match[2] });
    }
    
    if (vlans.length > 0) {
      let result = prefix.join('\n');
      if (result) result += '\n';
      
      vlans.forEach(vlan => {
        result += `vlan ${vlan.number}\nname ${vlan.name}\n`;
      });
      
      // Don't add 'end' - stay in config mode
      return result.trim();
    }
  }
  
  // Show running config
  if (lower.startsWith('show')) {
    if (lower.includes('running') || lower.includes('config')) {
      return 'show running-config';
    }
    if (lower.includes('vlan')) {
      return 'show vlan brief';
    }
  }
  
  // Hostname with optional banner
  if (lower.includes('hostname')) {
    const hostnameMatch = lower.match(/hostname (?:to )?([-\w]+)/);
    if (hostnameMatch) {
      let result = prefix.join('\n');
      if (result) result += '\n';
      result += `hostname ${hostnameMatch[1]}`;
      
      // Check if banner is also requested
      if (lower.includes('banner')) {
        const bannerMatch = lower.match(/banner.*?['"]([^'"]+)['"]/);
        const bannerMsg = bannerMatch ? bannerMatch[1] : 'Authorized Access Only';
        result += `\nbanner motd #${bannerMsg}#`;
      }
      
      // Don't add 'end' - stay in config mode
      return result;
    }
  }
  
  // Save configuration
  if ((lower.includes('save') || lower.includes('copy')) && 
      (lower.includes('config') || lower.includes('startup') || lower.includes('nvram'))) {
    return 'copy running-config startup-config';
  }
  
  // OSPF
  if (lower.includes('ospf')) {
    let result = prefix.join('\n');
    if (result) result += '\n';
    result += 'router ospf 1\nend';
    return result;
  }
  
  // Interface disable/shutdown
  if (lower.includes('disable') || lower.includes('shutdown') || lower.includes('apagar')) {
    const ifMatch = lower.match(/(?:interface )?(?:gigabitethernet|gi|g)(?: )?(\d+\/\d+)/);
    if (ifMatch) {
      let result = prefix.join('\n');
      if (result) result += '\n';
      result += `interface GigabitEthernet${ifMatch[1]}\nshutdown\nend`;
      return result;
    }
  }
  
  // Port assignment to VLAN (before port security)
  if (lower.includes('assign') && lower.includes('port') && lower.includes('vlan')) {
    // Match patterns like "gi0/1 to gi0/10" or "gi0/11 to gi0/15"
    const rangeMatch = lower.match(/(?:gi|gigabitethernet)(\d+)\/(\d+)\s+to\s+(?:gi|gigabitethernet)\d+\/(\d+)/);
    const vlanMatch = lower.match(/vlan\s+(\d+)/);
    
    if (rangeMatch && vlanMatch) {
      const slot = rangeMatch[1];
      const startPort = parseInt(rangeMatch[2]);
      const endPort = parseInt(rangeMatch[3]);
      const vlanNum = vlanMatch[1];
      
      let result = prefix.join('\n');
      if (result) result += '\n';
      
      // Use interface range for efficiency
      result += `interface range GigabitEthernet${slot}/${startPort}-${endPort}\nswitchport mode access\nswitchport access vlan ${vlanNum}\nend`;
      return result;
    }
  }
  
  // Port security (with detailed options)
  if (lower.includes('port') && lower.includes('security')) {
    const ifMatch = lower.match(/(?:interface )?(?:gigabitethernet|gi|g)(\d+\/\d+)/);
    const ifName = ifMatch && ifMatch[1] ? `GigabitEthernet${ifMatch[1]}` : 'GigabitEthernet0/1';
    const maxMatch = lower.match(/maximum\s+(\d+)/);
    const maxMacs = maxMatch ? maxMatch[1] : '2';
    
    let result = prefix.join('\n');
    if (result) result += '\n';
    result += `interface ${ifName}\nswitchport mode access\nswitchport port-security\nswitchport port-security maximum ${maxMacs}`;
    
    // Check for violation mode
    if (lower.includes('shutdown')) {
      result += '\nswitchport port-security violation shutdown';
    }
    
    result += '\nend';
    return result;
  }
  
  // Multiple ports with IPs
  if (lower.includes('three') && lower.includes('port')) {
    let result = prefix.join('\n');
    if (result) result += '\n';
    result += `interface GigabitEthernet0/1\nip address 192.168.1.2 255.255.255.0\ninterface GigabitEthernet0/2\nip address 192.168.1.3 255.255.255.0\ninterface GigabitEthernet0/3\nip address 192.168.1.4 255.255.255.0\nend`;
    return result;
  }
  
  // IP address configuration
  if (lower.includes('ip') || lower.includes('configure') || lower.includes('address')) {
    const ifMatch = lower.match(/(?:interface )?(?:gigabitethernet|gi|g|vlan)(?: )?(\d+(?:\/\d+)?)/);
    const ipMatch = lower.match(/(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/);
    const maskMatch = lower.match(/mask\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})/) || 
                      lower.match(/\/(\d+)/);
    
    // Determine if it's a switch based on the prompt
    const isSwitch = switchPrompt && switchPrompt.toLowerCase().includes('switch');
    
    let result = prefix.join('\n');
    if (result) result += '\n';
    
    // Extract IP and mask from prompt if available
    const ipAddr = ipMatch ? ipMatch[1] : '192.168.1.1';
    let mask = '255.255.255.0';
    if (maskMatch) {
      if (maskMatch[1].includes('.')) {
        mask = maskMatch[1];
      } else {
        // CIDR notation - convert to mask
        const cidr = parseInt(maskMatch[1]);
        if (cidr === 24) mask = '255.255.255.0';
        else if (cidr === 16) mask = '255.255.0.0';
        else if (cidr === 8) mask = '255.0.0.0';
      }
    }
    
    // Check if user specifically mentioned VLAN
    if (lower.includes('vlan')) {
      const vlanNum = ifMatch ? ifMatch[1] : '1';
      result += `interface vlan ${vlanNum}\nip address ${ipAddr} ${mask}\nno shutdown\nend`;
    }
    // For switches: ALWAYS use VLAN (most switches are Layer 2 only)
    else if (isSwitch) {
      result += `interface vlan 1\nip address ${ipAddr} ${mask}\nno shutdown\nend`;
    }
    // Router: standard IP configuration
    else {
      const ifName = ifMatch ? `GigabitEthernet${ifMatch[1]}` : 'GigabitEthernet0/1';
      result += `interface ${ifName}\nip address ${ipAddr} ${mask}\nno shutdown\nend`;
    }
    
    return result;
  }
  
  return null;
}

// Function to get current switch prompt state (fast version)
async function getCurrentPrompt() {
  try {
    // Quick prompt check without full authentication
    const { stdout } = await execAsync(`python3 -c "
import serial
import time

try:
    ser = serial.Serial('/dev/ttyUSB0', 9600, timeout=2)
    time.sleep(0.5)
    ser.reset_input_buffer()
    ser.write(b'\\\\r\\\\n')
    time.sleep(0.5)
    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    ser.close()
    
    lines = [line.strip() for line in response.split('\\\\n') if line.strip()]
    if lines:
        print(lines[-1])
    else:
        print('Switch>')
except:
    print('Switch>')
"`);
    
    return stdout.trim() || 'Switch>';
  } catch (error) {
    console.error('Error getting current prompt:', error);
    return 'Switch>';
  }
}

// Helper function to wait
function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Function to call OpenRouter API with retry strategy
async function callOpenRouterModel(prompt, switchPrompt = 'Switch>') {
  // Single reliable model instead of multiple fallbacks
  const model = "google/gemini-2.0-flash-lite-001"; // $0.000075/1K tokens - Barato y confiable
  const maxRetries = 3;
  const baseDelay = 2000; // 2 segundos base

  const systemPrompt = `You are a Cisco IOS command generator. Convert natural language requests into exact Cisco IOS commands.

CURRENT SWITCH STATE: ${switchPrompt}

DEVICE TYPE DETECTION:
- If prompt contains "Switch" = SWITCH DEVICE
- If prompt contains "Router" = ROUTER DEVICE

CRITICAL RULES:
1. Output ONLY valid Cisco IOS commands
2. One command per line
3. NO explanations, NO markdown, NO comments
4. Use proper Cisco syntax and capitalization
5. For interfaces: use full name like "GigabitEthernet0/1"
6. **ANALYZE THE CURRENT PROMPT STATE**:
   - If prompt ends with ">" (e.g., "Switch>") = USER MODE
     → MUST include "enable" first, then "configure terminal" for config commands
   - If prompt ends with "#" WITHOUT "(config)" (e.g., "Switch#" or "SW-Office-Main#") = PRIVILEGED MODE
     → MUST include "configure terminal" before any config commands
   - If prompt contains "(config)" (e.g., "Switch(config)#") = ALREADY IN CONFIG MODE
     → Do NOT add "configure terminal", just execute config commands directly
7. **STAY IN CONFIG MODE** - Do NOT use "end" or "exit" unless user explicitly asks to exit or save

SWITCH-SPECIFIC RULES:
- **MOST SWITCHES are Layer 2 only and CANNOT use "no switchport"**
- For Switch IP configuration:
  * ALWAYS use "interface vlan X" for management IP
  * Physical interfaces are for switching (VLANs, trunks, access ports)
  * DO NOT use "no switchport" unless explicitly asked
- For Switch physical interfaces: configure switchport settings (mode, vlan, etc.)

ROUTER-SPECIFIC RULES:
- Routers CAN assign IPs directly to physical interfaces
- Use standard "interface GigabitEthernet0/1" then "ip address"

EXAMPLES WITH DIFFERENT MODES:

Example 1 - ALREADY IN CONFIG MODE (DON'T add configure terminal):
Current state: Switch(config)#
Input: "create vlan 10 named sales"
Output:
vlan 10
name sales

Example 2 - PRIVILEGED MODE (MUST add configure terminal):
Current state: Switch#
Input: "create vlan 10 named sales"
Output:
configure terminal
vlan 10
name sales

Example 3 - PRIVILEGED MODE with hostname:
Current state: SW-Office-Main#
Input: "configure hostname and banner"
Output:
configure terminal
hostname SW-Office-Main
banner motd $Authorized Access Only$

Example 4 - USER MODE (need enable + configure terminal):
Current state: Switch>
Input: "create vlan 10"
Output:
enable
configure terminal
vlan 10

Example 5 - User explicitly asks to save (exit config and save):
Current state: Switch(config)#
Input: "save configuration"
Output:
end
copy running-config startup-config

Example 6 - Show commands (NO config mode needed):
Current state: ${switchPrompt}
Input: "show running configuration"
Output:
show running-config

Remember: 
- CHECK THE EXACT PROMPT STATE - if it has "(config)" you're in config mode, if just "#" you need "configure terminal"
- Only use "end" if user asks to save or exit
- For Switches: use "interface vlan X" for IPs (Layer 2 switches)
- For Routers: use physical interfaces for IPs`;

  let lastError = null;

  // Retry strategy with exponential backoff
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`Attempting with ${model} (attempt ${attempt}/${maxRetries})`);
      
      const completion = await openai.chat.completions.create({
        model: model,
        messages: [
          {
            role: "system",
            content: systemPrompt
          },
          {
            role: "user",
            content: prompt
          }
        ],
        temperature: 0.1,
        max_tokens: 400
      });

      const rawResponse = completion.choices[0]?.message?.content || "No response";
      const extractedCommands = extractCommands(rawResponse);

      console.log(`✓ Success with model: ${model}`);
      console.log('Raw response:', rawResponse);
      console.log('Extracted commands:', extractedCommands);

      return extractedCommands;
      
    } catch (error) {
      console.error(`✗ Attempt ${attempt} failed:`, error.message);
      lastError = error;
      
      // If it's a rate limit error and we haven't exhausted retries, wait and retry
      if (error.status === 429 && attempt < maxRetries) {
        const waitTime = baseDelay * attempt; // Exponential backoff: 2s, 4s, 6s
        console.log(`⏳ Rate limited. Waiting ${waitTime}ms before retry ${attempt + 1}...`);
        await wait(waitTime);
        continue;
      }
      
      // For non-429 errors or last attempt, break and go to fallback
      if (attempt === maxRetries) {
        console.error(`All ${maxRetries} attempts failed. Last error:`, error.message);
        break;
      }
      
      // For other errors, wait briefly and retry
      console.log(`⏳ Error occurred. Waiting 1s before retry...`);
      await wait(1000);
    }
  }

  // All retries failed, try rule-based fallback
  console.error('OpenRouter failed after retries. Last error:', lastError?.message);
  console.log('Attempting rule-based generation...');
  
  const ruleBasedResult = generateRuleBased(prompt, switchPrompt);
  if (ruleBasedResult) {
    console.log('Using rule-based fallback:', ruleBasedResult);
    return ruleBasedResult;
  }
  
  throw new Error(`All models failed. Last error: ${lastError?.message}`);
}

// Keep Ollama function commented for future use
/*
async function callOllamaModel(prompt) {
  // ... Ollama implementation ...
}
*/

// Function to execute commands on serial device
async function executeOnSerial(commands, keepAlive = false) {
  try {
    console.log('Executing commands on serial device:', commands);
    
    const keepAliveFlag = keepAlive ? 'true' : 'false';
    const { stdout, stderr } = await execAsync(`python3 serial_executor.py '${commands}' ${keepAliveFlag}`);
    
    if (stderr) {
      console.error('Serial execution stderr:', stderr);
    }
    
    const result = JSON.parse(stdout);
    return result;
  } catch (error) {
    console.error('Serial execution error:', error);
    return {
      success: false,
      error: error.message,
      fallback_response: "Command generated but not executed - check serial connection"
    };
  }
}

// Function to execute commands via SSH
async function executeOnSSH(commands, host, username, password, keepAlive = false) {
  try {
    console.log('Executing commands via SSH:', commands);
    
    const escapedCmd = commands.replace(/'/g, "'\\''");
    const escapedPass = password.replace(/'/g, "'\\''");
    const keepAliveFlag = keepAlive ? 'true' : 'false';
    
    const { stdout, stderr } = await execAsync(
      `python3 ssh_executor.py '${escapedCmd}' ${host} ${username} '${escapedPass}' ${keepAliveFlag}`
    );
    
    if (stderr) {
      console.error('SSH execution stderr:', stderr);
    }
    
    const result = JSON.parse(stdout);
    return result;
  } catch (error) {
    console.error('SSH execution error:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

// Function to test SSH connection
async function testSSHConnection(host, username, password) {
  try {
    const escapedPass = password.replace(/'/g, "'\\''");
    const testCommand = 'show version';
    
    const { stdout, stderr } = await execAsync(
      `python3 ssh_executor.py '${testCommand}' ${host} ${username} '${escapedPass}'`,
      { timeout: 15000 }
    );
    
    const result = JSON.parse(stdout);
    return result.success;
  } catch (error) {
    console.error('SSH connection test failed:', error);
    return false;
  }
}

app.post('/comando', async (req, res) => {
  const prompt = req.body.mensaje;
  const sessionId = req.body.session_id || 'default';
  const executeCommand = req.body.execute || false;
  
  console.log('[/comando] Request:', prompt, 'Session:', sessionId);
  
  try {
    const session = getOrCreateSession(sessionId);
    
    // Initialize AI-only chat sessions
    if (sessionId.startsWith('ai-chat-') && !session.deviceId) {
      session.deviceId = sessionId;
      session.deviceHostname = `AI Assistant - ${new Date().toLocaleDateString()}`;
      session.connected = false;
      session.connectionType = 'AI';
      session.vendor = 'cisco'; // Default for educational mode
      console.log('[/comando] Created AI chat session:', sessionId);
    }
    
    session.updateActivity();
    
    const aiResponse = await chatWithSession(session, prompt);
    
    // For educational mode (AI chats), send full conversational response
    // For connected devices, extract only commands for execution
    let commandsToSend = aiResponse;
    if (session.connected) {
      // Connected to real device - extract only commands
      commandsToSend = extractCommands(aiResponse);
      console.log('[/comando] Extracted commands:', commandsToSend);
    } else {
      // Educational mode - keep full conversational response
      console.log('[/comando] Educational response (full):', aiResponse.substring(0, 100) + '...');
    }
    
    let response = {
      success: true,
      respuesta: commandsToSend,
      output: commandsToSend,
      generated: true,
      vendor: session.vendor,
      device_os: session.deviceOS
    };
    
    if (executeCommand && session.connected) {
      console.log('[/comando] Executing commands...');
      
      const execResponse = await fetch('http://127.0.0.1:5000/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          connection_id: sessionId,
          command: commandsToSend
        })
      });
      
      const execResult = await execResponse.json();
      
      response.executed = execResult.success;
      response.execution = execResult;
      
      if (execResult.success) {
        response.device_output = execResult.output;
      }
      
      logCommand(session, prompt, commandsToSend, execResult.success, execResult.output);
    } else {
      logCommand(session, prompt, commandsToSend, false);
    }
    
    res.json(response);
    
  } catch (error) {
    console.error('[/comando] Error:', error);
    
    const session = getOrCreateSession(sessionId);
    session.updateActivity();
    const fallbackCommands = await callOpenRouterModel(prompt, session.lastPrompt);
    
    res.json({ 
      respuesta: fallbackCommands,
      generated: true,
      fallback: true,
      error: error.message 
    });
  }
});

// New endpoint for direct serial execution
app.post('/execute', async (req, res) => {
  const { command, useAI } = req.body;
  
  console.log('Direct execution request:', command, 'useAI:', useAI);
  
  try {
    let commandToExecute = command;
    
    // If AI is enabled, process with AI first
    if (useAI) {
      console.log('Processing with AI...');
      const aiCommands = await callOpenRouterModel(command, connectionState.lastPrompt);
      commandToExecute = aiCommands;
      console.log('AI generated:', commandToExecute);
    }
    
    // Execute on persistent Python connection
    const response = await fetch(`${PYTHON_SERVER}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        connection_id: connectionState.connectionId,
        command: commandToExecute
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      res.json({
        success: true,
        output: result.output
      });
    } else {
      res.json({
        success: false,
        error: result.error
      });
    }
  } catch (error) {
    console.error('Direct execution error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// SSH Connect endpoint
app.post('/ssh-connect', async (req, res) => {
  const { host, username, password } = req.body;
  
  console.log('SSH connection request:', host, username);
  
  try {
    const response = await fetch(`${PYTHON_SERVER}/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        connection_id: connectionState.connectionId,
        connection_type: 'ssh',
        host: host,
        port: 22,
        username: username,
        password: password
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      connectionState.type = 'ssh';
      connectionState.connected = true;
      connectionState.credentials = { host, username, password };
      
      res.json({
        connected: true,
        message: result.message
      });
    } else {
      res.json({
        connected: false,
        error: result.error
      });
    }
  } catch (error) {
    console.error('SSH connection error:', error);
    res.json({
      connected: false,
      error: error.message
    });
  }
});

// Serial Connect endpoint
app.post('/serial-connect', async (req, res) => {
  const { port, baudrate, password } = req.body;
  
  console.log('Serial connection request:', port, baudrate);
  
  try {
    const response = await fetch(`${PYTHON_SERVER}/connect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        connection_id: connectionState.connectionId,
        connection_type: 'serial',
        serial_port: port || '/dev/ttyUSB0',
        baudrate: baudrate || 9600,
        password: password || ''
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      connectionState.type = 'serial';
      connectionState.connected = true;
      
      res.json({
        success: true,
        message: result.message
      });
    } else {
      res.json({
        success: false,
        error: result.error
      });
    }
  } catch (error) {
    console.error('Serial connection error:', error);
    res.json({
      success: false,
      error: error.message
    });
  }
});

// SSH Execute endpoint
app.post('/ssh-execute', async (req, res) => {
  const { command, useAI, host, username, password } = req.body;
  
  console.log('Direct SSH execution request:', command);
  
  try {
    // If not connected, connect first
    if (!connectionState.connected || connectionState.type !== 'ssh') {
      const connectResponse = await fetch(`${PYTHON_SERVER}/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          connection_id: connectionState.connectionId,
          connection_type: 'ssh',
          host: host,
          port: 22,
          username: username,
          password: password
        })
      });
      
      const connectResult = await connectResponse.json();
      if (!connectResult.success) {
        return res.json({
          success: false,
          error: connectResult.error
        });
      }
      
      connectionState.type = 'ssh';
      connectionState.connected = true;
      connectionState.credentials = { host, username, password };
    }
    
    // Execute command
    const response = await fetch(`${PYTHON_SERVER}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        connection_id: connectionState.connectionId,
        command: command
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      res.json({
        success: true,
        output: result.output
      });
    } else {
      res.json({
        success: false,
        error: result.error
      });
    }
  } catch (error) {
    console.error('Direct SSH execution error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Disconnect endpoint
app.post('/disconnect', async (req, res) => {
  try {
    const response = await fetch(`${PYTHON_SERVER}/disconnect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        connection_id: connectionState.connectionId
      })
    });
    
    const result = await response.json();
    
    connectionState = {
      type: null,
      connected: false,
      credentials: {},
      lastPrompt: 'Switch>',
      connectionId: 'default'
    };
    
    res.json({ 
      success: true, 
      message: 'Connection state cleared' 
    });
  } catch (error) {
    // Even if Python server fails, reset local state
    connectionState = {
      type: null,
      connected: false,
      credentials: {},
      lastPrompt: 'Switch>',
      connectionId: 'default'
    };
    
    res.json({ 
      success: true, 
      message: 'Connection state cleared' 
    });
  }
});

// New endpoint to test serial connection
app.get('/connection-status', async (req, res) => {
  try {
    // Quick check: does the serial port exist?
    const fs = await import('fs');
    const portExists = fs.existsSync('/dev/ttyUSB0');
    
    if (!portExists) {
      return res.json({ 
        connected: false, 
        message: 'Puerto serial /dev/ttyUSB0 no encontrado'
      });
    }
    
    // Port exists, assume connection will work
    res.json({ 
      connected: true,
      message: 'Switch detectado en /dev/ttyUSB0'
    });
    
  } catch (error) {
    res.json({ 
      connected: false, 
      message: 'Error verificando puerto serial',
      error: error.message 
    });
  }
});

// ============================================================================
// VENDOR DETECTION
// ============================================================================
async function detectVendor(sessionId) {
  console.log('[Vendor Detection] Starting for session:', sessionId);
  
  try {
    const session = sessions.get(sessionId);
    if (!session || !session.connected) {
      console.log('[Vendor Detection] Session not connected');
      return { vendor: 'unknown', os: 'unknown' };
    }
    
    const response = await fetch('http://127.0.0.1:5000/execute', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        connection_id: sessionId,
        command: 'show version'
      })
    });
    
    const result = await response.json();
    if (!result.success) {
      console.log('[Vendor Detection] Failed to execute show version');
      return { vendor: 'unknown', os: 'unknown' };
    }
    
    const output = result.output.toLowerCase();
    console.log('[Vendor Detection] Analyzing output...');
    
    if (output.includes('cisco') || output.includes('ios')) {
      let os = 'IOS';
      if (output.includes('ios-xe')) os = 'IOS-XE';
      else if (output.includes('nx-os')) os = 'NX-OS';
      
      console.log('[Vendor Detection] Detected: Cisco', os);
      return { vendor: 'cisco', os: os };
    }
    
    if (output.includes('juniper') || output.includes('junos')) {
      console.log('[Vendor Detection] Detected: Juniper JunOS');
      return { vendor: 'juniper', os: 'JunOS' };
    }
    
    if (output.includes('arista')) {
      console.log('[Vendor Detection] Detected: Arista EOS');
      return { vendor: 'arista', os: 'EOS' };
    }
    
    console.log('[Vendor Detection] Unknown vendor');
    return { vendor: 'unknown', os: 'unknown' };
    
  } catch (error) {
    console.error('[Vendor Detection] Error:', error);
    return { vendor: 'unknown', os: 'unknown' };
  }
}

// ============================================================================
// DYNAMIC SYSTEM PROMPTS
// ============================================================================
function buildSystemPrompt(session, isConnected = true) {
  
  // EDUCATIONAL MODE: Conversational AI when not connected
  if (!isConnected) {
    return `Eres un ingeniero de redes experimentado que está ayudando a colegas y estudiantes. Respondes como si estuvieras explicando algo en una conversación por chat: directo, claro, sin complicaciones.

TU ESTILO:
- Vas al grano sin rodeos innecesarios
- Explicas conceptos complejos de forma simple
- Usas ejemplos prácticos cuando ayudan
- Evitas listas largas de viñetas (solo cuando realmente simplifican)
- Escribes de forma natural, como si charlaras con un colega

CÓMO RESPONDES:
- Si te piden un comando, lo das y explicas brevemente qué hace
- Si te preguntan un concepto, lo explicas de forma que cualquiera lo entienda
- Si algo requiere contexto, preguntas antes de asumir
- Si hay varias formas de hacer algo, mencionas la más práctica primero

CONOCIMIENTO:
Manejas Cisco, Juniper y Arista. Tienes experiencia real configurando switches, routers, troubleshooting de red. Conoces CCNA, CCNP y conceptos avanzados.

EJEMPLOS DE TU ESTILO:

User: "Cómo verifico la versión en un switch Cisco?"
Tú: "El comando es \`show version\`. Te va a dar la versión del IOS, el modelo del equipo, cuánto tiempo lleva encendido y más info del hardware.

Puedes ejecutarlo desde cualquier modo (user o privileged). Si estás en user mode (>) solo tipea \`enable\` primero.

¿Necesitas interpretar alguna parte del output?"

User: "Explícame qué son las VLANs"
Tú: "Las VLANs son básicamente una forma de dividir un switch físico en múltiples switches lógicos. Cada VLAN es como una red independiente, aunque todo esté en el mismo hardware.

¿Por qué usarlas? Principalmente por seguridad y organización. Puedes separar departamentos, ambientes (producción vs desarrollo), o simplemente reducir el dominio de broadcast.

En Cisco la config básica es así:
\`\`\`
configure terminal
vlan 10
name Ventas
exit
interface GigabitEthernet0/1
switchport mode access
switchport access vlan 10
\`\`\`

Esto crea la VLAN 10 y le asigna un puerto. ¿Quieres saber cómo configurar trunking o routing entre VLANs?"

IMPORTANTE: Responde siempre en español de forma natural, como lo haría un ingeniero latinoamericano. Sin traducción forzada, sin formalismos excesivos.`;
  }
  
  // COMMAND GENERATION MODE: When connected to a real device
  const basePrompt = `You are a network device command generator. Convert natural language requests into exact device commands.

CRITICAL RULES:
1. Output ONLY executable commands, no explanations
2. Check current device state from prompt
3. Use proper mode escalation
4. Prefix all commands with "CMD: " for easy extraction

Current device state: ${session.lastPrompt}`;

  if (session.vendor === 'cisco') {
    return basePrompt + `

CISCO ${session.deviceOS || 'IOS'} SYNTAX:
- Use "configure terminal" to enter config mode
- VLAN creation: vlan X + name Y
- Interface config: interface GigabitEthernet0/1
- Save config: end + copy running-config startup-config
- For switches: use "interface vlan X" for IPs
- For routers: use physical interfaces for IPs

MODE DETECTION:
- If prompt ends with ">" → User mode (need "enable")
- If prompt ends with "#" without "(config)" → Privileged mode
- If prompt contains "(config)" → Already in config mode (DON'T add "configure terminal")

SUBNET CALCULATION:
- When user doesn't specify subnet mask, calculate optimal mask
- For LANs: prefer /24 (254 hosts)
- For point-to-point links: use /30 (2 hosts)
- For server segments: use /27 (30 hosts) or /26 (62 hosts)
- ALWAYS show subnet mask in dotted decimal (255.255.255.0)

EXAMPLES:
Request: "configure IP 192.168.1.1 on interface Gi0/1"
Output:
CMD: configure terminal
CMD: interface GigabitEthernet0/1
CMD: ip address 192.168.1.1 255.255.255.0
CMD: no shutdown`;
  }

  if (session.vendor === 'juniper') {
    return basePrompt + `

JUNIPER JUNOS SYNTAX:
- Use "configure" to enter config mode (NOT "configure terminal")
- VLAN creation: set vlans vlan-name vlan-id X
- Interface config: set interfaces ge-0/0/1
- Save config: commit (NOT "copy run start")

SUBNET CALCULATION:
- Use CIDR notation: /24, /30, etc.
- Optimal masks same as Cisco`;
  }

  return basePrompt;
}

// ============================================================================
// CONVERSATIONAL CHAT
// ============================================================================
async function chatWithSession(session, userMessage) {
  console.log('[Chat] User message:', userMessage);
  
  // Initialize or regenerate system prompt
  if (session.conversationHistory.length === 0) {
    // New conversation - create system prompt
    session.systemPrompt = buildSystemPrompt(session, session.connected);
    session.conversationHistory.push({
      role: "system",
      content: session.systemPrompt
    });
    console.log('[Chat] System prompt created for vendor:', session.vendor);
  } else if (!session.connected && session.conversationHistory.length > 0) {
    // Educational mode chat with existing history - check if prompt needs update
    const currentSystemPrompt = session.conversationHistory[0].content;
    if (currentSystemPrompt.includes("Output ONLY executable commands, no explanations")) {
      // Old command-only prompt detected - regenerate for educational mode
      console.log('[Chat] Updating to conversational prompt for educational mode');
      session.systemPrompt = buildSystemPrompt(session, false);
      session.conversationHistory[0].content = session.systemPrompt;
      session.saveToFile();
    }
  }
  
  session.conversationHistory.push({
    role: "user",
    content: userMessage
  });
  session.saveToFile(); // Save after adding user message
  
  // Single reliable model with retry strategy
  const model = "google/gemini-2.0-flash-lite-001";
  const maxRetries = 3;
  const baseDelay = 2000; // 2 segundos base
  
  let lastError = null;
  
  // Retry strategy with exponential backoff
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      console.log(`[Chat] Attempting with ${model} (attempt ${attempt}/${maxRetries})`);
      
      const completion = await openai.chat.completions.create({
        model: model,
        messages: session.conversationHistory,
        temperature: 0.1,
        max_tokens: 800
      });
      
      const aiResponse = completion.choices[0]?.message?.content || "No response";
      
      session.conversationHistory.push({
        role: "assistant",
        content: aiResponse
      });
      session.saveToFile(); // Save after adding AI response
      
      console.log('[Chat] ✓ Success with model:', model);
      return aiResponse;
      
    } catch (error) {
      console.error(`[Chat] ✗ Attempt ${attempt} failed:`, error.message);
      lastError = error;
      
      // If it's a rate limit error and we haven't exhausted retries, wait and retry
      if (error.status === 429 && attempt < maxRetries) {
        const waitTime = baseDelay * attempt; // Exponential backoff: 2s, 4s, 6s
        console.log(`[Chat] ⏳ Rate limited. Waiting ${waitTime}ms before retry ${attempt + 1}...`);
        await wait(waitTime);
        continue;
      }
      
      // For context length errors, try with shorter history
      if (error.message?.includes('context_length') && attempt < maxRetries) {
        console.log(`[Chat] ⏳ Context too long. Trimming history and retrying...`);
        // Keep system prompt + last 4 messages
        const systemMsg = session.conversationHistory[0];
        const recentMessages = session.conversationHistory.slice(-4);
        session.conversationHistory = [systemMsg, ...recentMessages];
        session.saveToFile(); // Save after trimming history
        await wait(1000);
        continue;
      }
      
      // For final attempt or other errors, break
      if (attempt === maxRetries) {
        console.error(`[Chat] All ${maxRetries} attempts failed. Last error:`, error.message);
        break;
      }
      
      // For other errors, wait briefly and retry
      console.log(`[Chat] ⏳ Error occurred. Waiting 1s before retry...`);
      await wait(1000);
    }
  }
  
  throw lastError || new Error('All chat attempts failed after retries');
}

// ============================================================================
// COMMAND LOGGING
// ============================================================================
function logCommand(session, prompt, commands, executed, output = null) {
  try {
    const logEntry = {
      timestamp: new Date().toISOString(),
      user: os.userInfo().username,
      session_id: session.connectionId,
      device: session.credentials.host || 'serial',
      vendor: session.vendor || 'unknown',
      device_os: session.deviceOS || 'unknown',
      prompt_input: prompt,
      commands_generated: commands,
      executed: executed,
      output: output ? output.substring(0, 500) : null
    };
    
    fs.appendFileSync(logFile, JSON.stringify(logEntry) + '\n');
    console.log('[Logging] Command logged');
  } catch (error) {
    console.error('[Logging] Failed:', error);
  }
}

// ============================================================================
// NEW SESSION-BASED ENDPOINTS
// ============================================================================

app.post('/connect', async (req, res) => {
  const { session_id, connection_type, host, port, username, password } = req.body;
  
  // Generate device ID from connection parameters
  const deviceId = session_id || generateDeviceId(connection_type, host, username);
  
  console.log('[/connect] Type:', connection_type, 'Device ID:', deviceId);
  
  try {
    const session = getOrCreateSession(deviceId);
    
    session.connectionType = connection_type;
    session.credentials = { host, port, username, password };
    session.deviceId = deviceId;
    
    const response = await fetch('http://127.0.0.1:5000/connect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        connection_id: deviceId,
        connection_type: connection_type.toLowerCase(),
        host: host,
        port: port || 22,
        username: username,
        password: password
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      session.connected = true;
      session.updateActivity();
      
      console.log('[/connect] Detecting vendor...');
      const vendorInfo = await detectVendor(deviceId);
      session.vendor = vendorInfo.vendor;
      session.deviceOS = vendorInfo.os;
      
      console.log('[/connect] Detecting hostname...');
      const hostname = await detectHostname(session);
      session.deviceHostname = hostname || host;
      
      console.log('[/connect] Connected! Device:', session.deviceHostname, 'Vendor:', session.vendor, session.deviceOS);
      
      res.json({
        success: true,
        message: 'Connected successfully',
        device_id: deviceId,
        device_hostname: session.deviceHostname,
        vendor: session.vendor,
        device_os: session.deviceOS
      });
    } else {
      res.json({
        success: false,
        error: result.error
      });
    }
  } catch (error) {
    console.error('[/connect] Error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/disconnect', async (req, res) => {
  const { session_id } = req.body;
  const sessionId = session_id || 'default';
  
  console.log('[/disconnect] Session:', sessionId);
  
  try {
    await fetch('http://127.0.0.1:5000/disconnect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ connection_id: sessionId })
    });
    
    sessions.delete(sessionId);
    
    res.json({
      success: true,
      message: 'Disconnected successfully'
    });
  } catch (error) {
    console.error('[/disconnect] Error:', error);
    sessions.delete(sessionId);
    res.json({
      success: true,
      message: 'Session cleared'
    });
  }
});

app.post('/reset-chat', async (req, res) => {
  const { session_id } = req.body;
  const sessionId = session_id || 'default';
  
  console.log('[/reset-chat] Session:', sessionId);
  
  const session = sessions.get(sessionId);
  if (session) {
    session.resetConversation();
    session.updateActivity();
    res.json({
      success: true,
      message: 'Conversation reset'
    });
  } else {
    res.json({
      success: false,
      error: 'Session not found'
    });
  }
});

app.get('/session-info', async (req, res) => {
  const sessionId = req.query.session_id || 'default';
  const includeHistory = req.query.include_history === 'true';
  
  const session = sessions.get(sessionId);
  if (session) {
    const sessionData = {
      device_id: session.deviceId,
      device_hostname: session.deviceHostname,
      connected: session.connected,
      connection_type: session.connectionType,
      vendor: session.vendor,
      device_os: session.deviceOS,
      last_prompt: session.lastPrompt,
      message_count: session.conversationHistory.length,
      last_activity: session.lastActivity
    };
    
    // Include full conversation history if requested
    if (includeHistory) {
      sessionData.conversation_history = session.conversationHistory;
    }
    
    res.json({
      success: true,
      session: sessionData
    });
  } else {
    res.json({
      success: false,
      error: 'Session not found'
    });
  }
});

app.get('/devices', async (req, res) => {
  try {
    const devices = [];
    
    for (const [sessionId, session] of sessions.entries()) {
      devices.push({
        device_id: session.deviceId || sessionId,
        device_hostname: session.deviceHostname || 'Unknown',
        connected: session.connected,
        connection_type: session.connectionType,
        vendor: session.vendor,
        device_os: session.deviceOS,
        message_count: session.conversationHistory.length,
        last_activity: session.lastActivity,
        credentials: {
          host: session.credentials.host,
          username: session.credentials.username
        }
      });
    }
    
    // Sort by last activity (most recent first)
    devices.sort((a, b) => b.last_activity - a.last_activity);
    
    res.json({
      success: true,
      count: devices.length,
      devices: devices
    });
  } catch (error) {
    console.error('[/devices] Error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// Delete session endpoint
app.delete('/session/:sessionId', async (req, res) => {
  try {
    const sessionId = req.params.sessionId;
    
    if (!sessions.has(sessionId)) {
      return res.status(404).json({
        success: false,
        error: 'Session not found'
      });
    }
    
    // Remove from memory
    sessions.delete(sessionId);
    
    // Remove from disk
    deleteSession(sessionId);
    
    res.json({
      success: true,
      message: 'Session deleted successfully'
    });
  } catch (error) {
    console.error('[DELETE /session] Error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/command-history', async (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 100;
    const sessionId = req.query.session_id;
    
    if (!fs.existsSync(logFile)) {
      return res.json({ logs: [] });
    }
    
    const content = fs.readFileSync(logFile, 'utf-8');
    let logs = content
      .split('\n')
      .filter(line => line.trim())
      .map(line => JSON.parse(line))
      .reverse();
    
    if (sessionId) {
      logs = logs.filter(log => log.session_id === sessionId);
    }
    
    res.json({
      success: true,
      logs: logs.slice(0, limit),
      total: logs.length
    });
  } catch (error) {
    console.error('[/command-history] Error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.get('/export-history', async (req, res) => {
  try {
    if (!fs.existsSync(logFile)) {
      return res.status(404).send('No history found');
    }
    
    const content = fs.readFileSync(logFile, 'utf-8');
    const logs = content
      .split('\n')
      .filter(line => line.trim())
      .map(line => JSON.parse(line));
    
    const csv = [
      'Timestamp,User,Session,Device,Vendor,OS,Prompt,Commands,Executed',
      ...logs.map(log => 
        `"${log.timestamp}","${log.user}","${log.session_id}","${log.device}","${log.vendor}","${log.device_os}","${log.prompt_input.replace(/"/g, '""')}","${log.commands_generated.replace(/"/g, '""')}","${log.executed}"`
      )
    ].join('\n');
    
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename=corvelli_history.csv');
    res.send(csv);
  } catch (error) {
    console.error('[/export-history] Error:', error);
    res.status(500).send('Error exporting history');
  }
});

app.delete('/command-history', async (req, res) => {
  try {
    if (fs.existsSync(logFile)) {
      fs.unlinkSync(logFile);
    }
    
    res.json({
      success: true,
      message: 'History cleared'
    });
  } catch (error) {
    console.error('[/clear-history] Error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

// ============================================================================
// CONFIG TEMPLATES
// ============================================================================

app.get('/templates', (req, res) => {
  try {
    const sessionId = req.query.session_id || 'default';
    const session = getOrCreateSession(sessionId);
    
    // Use session's detected vendor, default to cisco
    const vendor = session.vendor || req.query.vendor || 'cisco';
    
    const available = getAvailableTemplates(vendor);
    
    res.json({
      success: true,
      vendor: vendor,
      templates: available
    });
  } catch (error) {
    console.error('[/templates] Error:', error);
    res.status(500).json({
      success: false,
      error: error.message
    });
  }
});

app.post('/apply-template', (req, res) => {
  try {
    const { template_id, params, session_id } = req.body;
    
    if (!template_id) {
      return res.status(400).json({
        success: false,
        error: 'template_id is required'
      });
    }
    
    const session = getOrCreateSession(session_id || 'default');
    const vendor = session.vendor || 'cisco';
    
    const result = applyTemplate(template_id, vendor, params || {});
    
    res.json({
      success: true,
      template_id: template_id,
      vendor: vendor,
      prompt: result.prompt,
      commands: result.commands
    });
  } catch (error) {
    console.error('[/apply-template] Error:', error);
    res.status(400).json({
      success: false,
      error: error.message
    });
  }
});

// Load sessions from disk before starting server
loadSessions();

app.listen(3000, () => console.log('AIConsole Backend - OpenRouter API + Serial Mode - Port 3000'));
