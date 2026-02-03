
# C O R V E L L I - AI NETWORK ASSISTANT

<div align="center">  
  <p align="center">
    <strong>An intelligent desktop application that translates natural language instructions into precise network commands using artificial intelligence.</strong>
  </p>
  
  <p align="center">
    <strong>MVP Status: Currently generates accurate commands - Command execution functionality in development</strong>
  </p>
</div>

---

## Table of Contents
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Current Capabilities](#current-capabilities)
- [Installation & Setup](#installation--setup)
- [Usage](#usage)
- [Roadmap](#roadmap)
- [Project Structure](#project-structure)
- [Development](#development)

## Features

<div align="center">
  <table>
    <tr>
      <td align="center" width="33%">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; color: white; margin: 10px;">
          <h3>Natural Language Processing</h3>
          <p>Convert plain English network requests into precise Cisco IOS commands using advanced AI models</p>
        </div>
      </td>
      <td align="center" width="33%">
        <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 20px; border-radius: 10px; color: white; margin: 10px;">
          <h3>Desktop Interface</h3>
          <p>Clean Python Tkinter GUI with dark theme and intuitive command input/output interface</p>
        </div>
      </td>
      <td align="center" width="33%">
        <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 20px; border-radius: 10px; color: white; margin: 10px;">
          <h3>Real-time Translation</h3>
          <p>Instant command generation with support for complex networking scenarios and configurations</p>
        </div>
      </td>
    </tr>
    <tr>
      <td align="center" width="33%">
        <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); padding: 20px; border-radius: 10px; color: white; margin: 10px;">
          <h3>Cisco IOS Focus</h3>
          <p>Specialized in Cisco networking commands with plans for multi-vendor support</p>
        </div>
      </td>
      <td align="center" width="33%">
        <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 20px; border-radius: 10px; color: white; margin: 10px;">
          <h3>Educational Tool</h3>
          <p>Perfect for network engineering students and professionals learning Cisco command syntax</p>
        </div>
      </td>
      <td align="center" width="33%">
        <div style="background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); padding: 20px; border-radius: 10px; color: #333; margin: 10px;">
          <h3>Modular Architecture</h3>
          <p>Separated frontend and backend design for easy scaling and customization</p>
        </div>
      </td>
    </tr>
  </table>
</div>

## Technology Stack

<div align="center">
  <table>
    <tr>
      <td align="center">
        <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
      </td>
      <td align="center">
        <img src="https://img.shields.io/badge/Tkinter-FF6B6B?style=for-the-badge&logo=python&logoColor=white" alt="Tkinter">
      </td>
      <td align="center">
        <img src="https://img.shields.io/badge/Node.js-43853D?style=for-the-badge&logo=node.js&logoColor=white" alt="Node.js">
      </td>
      <td align="center">
        <img src="https://img.shields.io/badge/Express.js-404D59?style=for-the-badge&logo=express&logoColor=white" alt="Express">
      </td>
    </tr>
    <tr>
      <td align="center">
        <img src="https://img.shields.io/badge/OpenAI_API-412991?style=for-the-badge&logo=openai&logoColor=white" alt="OpenAI API">
      </td>
      <td align="center">
        <img src="https://img.shields.io/badge/DeepSeek-FF4B4B?style=for-the-badge&logo=ai&logoColor=white" alt="DeepSeek">
      </td>
      <td align="center">
        <img src="https://img.shields.io/badge/OpenRouter-8A2BE2?style=for-the-badge&logo=router&logoColor=white" alt="OpenRouter">
      </td>
      <td align="center">
        <img src="https://img.shields.io/badge/REST_API-FF6F00?style=for-the-badge&logo=api&logoColor=white" alt="REST API">
      </td>
    </tr>
  </table>
</div>

## Current Capabilities

<div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #007bff;">

### What AIConsole Can Do (MVP Status)
- **Natural Language Input**: Accept commands like "show active interfaces" or "configure IP on FastEthernet0/1"
- **Command Generation**: Translate to precise Cisco IOS syntax: `show ip interface brief`, `interface fa0/1`
- **Multi-scenario Support**: Handle various networking tasks including configuration, monitoring, and troubleshooting
- **Real-time Processing**: Instant response with AI-powered command translation
- **Educational Value**: Learn proper Cisco command syntax through natural language interaction

### What's Coming Next
- **SSH Command Execution**: Direct execution of generated commands on real network devices
- **Multi-vendor Support**: Expand beyond Cisco to include MikroTik, Juniper, and other network vendors
- **Command History**: Track and save previously generated commands
- **Learning Mode**: Detailed explanations of generated commands for educational purposes

</div>

## Installation & Setup

### Prerequisites
- Python 3.8 or higher
- Node.js (v16 or higher)
- npm package manager
- OpenRouter API key (for AI model access)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/GodSci3nc3/AIConsole.git
   cd AIConsole
   ```

2. **Set up the backend**
   ```bash
   cd backend
   npm install
   ```

3. **Configure API credentials**
   - Add your OpenRouter API key to the backend configuration
   - Update AI model settings in the backend server

4. **Start the backend server**
   ```bash
   node server.js
   ```

5. **Launch the desktop application**
   ```bash
   cd ../frontend
   python app.py
   ```

## Project Structure

```
AIConsole/
├── frontend/               # Python Tkinter desktop application
│   ├── app.py             # Main GUI application
│   └── assets/            # Images and icons
├── backend/               # Node.js API server
│   ├── server.js          # Express server with AI integration
│   └── package.json       # Node.js dependencies
├── docs/                  # Documentation and examples
└── assets/               # Project resources and screenshots
---
```
<div align="center">
  <strong>Developed by Arturo Rosales V</strong><br>
  <a href="https://github.com/GodSci3nc3">GitHub</a> | 
  <a href="mailto:rosalesvelazquezarturo@email.com">Email</a>
  
  <p>Please reach out through GitHub or email for any questions.</p>
</div>


