import express from 'express';
import OpenAI from 'openai';
import { exec } from 'child_process';
import { promisify } from 'util';
import dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const execAsync = promisify(exec);

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
  apiKey: process.env.OPENROUTER_API_KEY
});

const app = express();
app.use(express.json());

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
  
  // VLAN creation
  if (lower.includes('vlan') && (lower.includes('create') || lower.includes('crear'))) {
    const vlanMatch = lower.match(/(\d+)/);
    const nameMatch = lower.match(/named? ([\w-]+)/);
    if (vlanMatch) {
      let result = prefix.join('\n');
      if (result) result += '\n';
      result += `vlan ${vlanMatch[1]}`;
      if (nameMatch) {
        result += `\nname ${nameMatch[1]}`;
      }
      result += '\nend';
      return result;
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
  
  // Hostname
  if (lower.includes('hostname')) {
    const hostnameMatch = lower.match(/hostname (?:to )?([\w-]+)/);
    if (hostnameMatch) {
      let result = prefix.join('\n');
      if (result) result += '\n';
      result += `hostname ${hostnameMatch[1]}\nend`;
      return result;
    }
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
  
  // Port security
  if (lower.includes('port') && lower.includes('security')) {
    const ifMatch = lower.match(/(?:interface )?(?:gigabitethernet|gi|g)?(?: )?(\d+\/\d+)?/);
    const ifName = ifMatch && ifMatch[1] ? `GigabitEthernet${ifMatch[1]}` : 'GigabitEthernet0/1';
    let result = prefix.join('\n');
    if (result) result += '\n';
    result += `interface ${ifName}\nswitchport mode access\nswitchport port-security\nend`;
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
    
    // Determine if it's a switch based on the prompt
    const isSwitch = switchPrompt && switchPrompt.toLowerCase().includes('switch');
    
    let result = prefix.join('\n');
    if (result) result += '\n';
    
    // Check if user specifically mentioned VLAN
    if (lower.includes('vlan')) {
      const vlanNum = ifMatch ? ifMatch[1] : '1';
      result += `interface vlan ${vlanNum}\nip address 192.168.1.1 255.255.255.0\nno shutdown\nend`;
    }
    // For switches: ALWAYS use VLAN (most switches are Layer 2 only)
    // User can manually use "no switchport" if they have a Layer 3 switch
    else if (isSwitch) {
      // If interface mentioned, inform about VLAN requirement via comment (though we don't show comments)
      // Default to VLAN 1 for management IP
      result += `interface vlan 1\nip address 192.168.1.1 255.255.255.0\nno shutdown\nend`;
    }
    // Router: standard IP configuration
    else {
      const ifName = ifMatch ? `GigabitEthernet${ifMatch[1]}` : 'GigabitEthernet0/1';
      result += `interface ${ifName}\nip address 192.168.1.1 255.255.255.0\nno shutdown\nend`;
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

// Function to call OpenRouter API with fallback models
async function callOpenRouterModel(prompt, switchPrompt = 'Switch>') {
  // List of models to try in order (verified free models)
  const models = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "meta-llama/llama-3.2-1b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "mistralai/mistral-7b-instruct:free"
  ];

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
6. **ANALYZE THE CURRENT PROMPT CAREFULLY**:
   - If prompt ends with ">" (e.g., "Switch>") = USER MODE
     → MUST include "enable" first, then "configure terminal" if config needed
   - If prompt ends with "#" without "(config)" (e.g., "Switch#") = PRIVILEGED MODE
     → Include "configure terminal" if config needed
   - If prompt contains "(config)" (e.g., "Switch(config)#") = CONFIG MODE
     → Ready for config commands, no mode change needed

SWITCH-SPECIFIC RULES:
- **MOST SWITCHES are Layer 2 only and CANNOT use "no switchport"**
- For Switch IP configuration:
  * ALWAYS use "interface vlan 1" for management IP (safest option)
  * Physical interfaces are for switching (VLANs, trunks, access ports)
  * DO NOT use "no switchport" unless explicitly asked
- For Switch physical interfaces: configure switchport settings (mode, vlan, etc.)

ROUTER-SPECIFIC RULES:
- Routers CAN assign IPs directly to physical interfaces
- Use standard "interface GigabitEthernet0/1" then "ip address"

EXAMPLES WITH DIFFERENT MODES:

Example 1 - Switch in Privileged Mode, IP on VLAN (Management):
Current state: Switch#
Input: "configure ip address on interface gigabitethernet 0/1"
Output:
configure terminal
interface vlan 1
ip address 192.168.1.1 255.255.255.0
no shutdown
end

Example 2 - Switch in Privileged Mode, Management IP directly:
Current state: Switch#
Input: "configure management ip address"
Output:
configure terminal
interface vlan 1
ip address 192.168.1.1 255.255.255.0
no shutdown
end

Example 3 - Router in Privileged Mode, IP on interface:
Current state: Router#
Input: "configure ip address on interface gigabitethernet 0/1"
Output:
configure terminal
interface GigabitEthernet0/1
ip address 192.168.1.1 255.255.255.0
no shutdown
end

Example 4 - User Mode with VLAN:
Current state: Switch>
Input: "create vlan 10 named sales"
Output:
enable
configure terminal
vlan 10
name sales
end

Example 5 - Show commands (any mode):
Current state: ${switchPrompt}
Input: "show running configuration"
Output:
show running-config

Remember: 
- ALWAYS check the device type (Switch vs Router)
- For Switches: ALWAYS use "interface vlan 1" for IPs (Layer 2 switches don't support Layer 3)
- For Routers: use physical interfaces for IPs
- ALWAYS check if prompt ends with ">" (user mode) and include "enable" + "configure terminal" when needed!`;

  let lastError = null;

  // Try each model in sequence
  for (let i = 0; i < models.length; i++) {
    const model = models[i];
    try {
      console.log(`Attempting with model ${i + 1}/${models.length}: ${model}`);
      
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
        max_tokens: 300
      });

      const rawResponse = completion.choices[0]?.message?.content || "No response";
      
      // Extract commands from response
      const extractedCommands = extractCommands(rawResponse);

      console.log(`✓ Success with model: ${model}`);
      console.log('Raw response:', rawResponse);
      console.log('Extracted commands:', extractedCommands);

      return extractedCommands;
      
    } catch (error) {
      console.error(`✗ Model ${model} failed:`, error.message);
      lastError = error;
      
      // If it's a rate limit error (429), try next model immediately
      if (error.status === 429) {
        console.log(`Rate limited on ${model}, trying next model...`);
        continue;
      }
      
      // For other errors, also try next model
      console.log(`Error with ${model}, trying next model...`);
      continue;
    }
  }

  // All models failed, try rule-based fallback
  console.error('All OpenRouter models failed. Last error:', lastError?.message);
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
async function executeOnSerial(commands) {
  try {
    console.log('Executing commands on serial device:', commands);
    
    const { stdout, stderr } = await execAsync(`python3 serial_executor.py '${commands}'`);
    
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

app.post('/comando', async (req, res) => {
  const prompt = req.body.mensaje;
  const executeSerial = req.body.execute || false; // Optional parameter to execute on device
  
  console.log('Receiving request:', req.body.mensaje);
  console.log('Execute on serial:', executeSerial);
  
  try {
    console.log('Sending to OpenRouter API...');
    
    // Get current switch prompt state if executing on device
    let switchPrompt = 'Switch>';
    if (executeSerial) {
      console.log('Getting current switch state...');
      switchPrompt = await getCurrentPrompt();
      console.log('Current switch prompt:', switchPrompt);
    }
    
    const generatedCommands = await callOpenRouterModel(prompt, switchPrompt);
    
    console.log('Generated commands:', generatedCommands);
    
    let response = {
      respuesta: generatedCommands,
      generated: true
    };
    
    // If execution is requested, try to execute on serial device
    if (executeSerial) {
      console.log('Attempting serial execution...');
      const executionResult = await executeOnSerial(generatedCommands);
      
      response.execution = executionResult;
      response.executed = executionResult.success;
      
      if (executionResult.success) {
        response.device_responses = executionResult.results;
      } else {
        response.execution_error = executionResult.error;
      }
    }
    
    console.log('Sending to frontend:', response);
    res.json(response);
    
  } catch (error) {
    console.error('ERROR:', error);
    
    // Fallback to error message for demo
    const fallbackResponse = `interface GigabitEthernet0/1
ip address 192.168.1.1 255.255.255.0
no shutdown`;
    
    console.log('Using fallback response for demo');
    res.json({ 
      respuesta: fallbackResponse,
      generated: false,
      error: error.message 
    });
  }
});

// New endpoint for direct serial execution
app.post('/execute', async (req, res) => {
  const commands = req.body.commands;
  
  console.log('Direct execution request:', commands);
  
  try {
    const result = await executeOnSerial(commands);
    res.json(result);
  } catch (error) {
    console.error('Direct execution error:', error);
    res.status(500).json({
      success: false,
      error: error.message
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

app.listen(3000, () => console.log('AIConsole Backend - OpenRouter API + Serial Mode - Port 3000'));
