import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import json
import threading
import time
import random
from PIL import Image, ImageTk
import os

# Colores y estilos
DARK_BG = "#1E1E2E"
LIGHT_TEXT = "#CDD6F4"
ACCENT_COLOR = "#89B4FA"
SUCCESS_COLOR = "#A6E3A1"
ERROR_COLOR = "#F38BA8"
COMMAND_COLOR = "#FAB387"
OUTPUT_COLOR = "#89DCEB"
BORDER_COLOR = "#313244"
TERMINAL_BG = "#11111B"
HIGHLIGHT_COLOR = "#F5C2E7"

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background=DARK_BG, foreground=LIGHT_TEXT,
                         relief=tk.SOLID, borderwidth=1,
                         font=("Segoe UI", 9, "normal"))
        label.pack(padx=4, pady=4)

    def hide_tip(self, event=None):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

class NetworkConsole:
    def __init__(self, root):
        self.root = root
        self.root.title("IA en Consola - Asistente de Redes")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        self.root.configure(bg=DARK_BG)
        
        # Variables de estado
        self.connected = False
        self.device_name = "Router1"
        self.device_type = "Router"
        self.connection_type = "SSH"
        self.history = []
        self.history_index = 0
        self.ai_mode = False  # Modo AI desactivado por defecto (modo Putty)
        
        # Cargar iconos
        self.icons = self.load_icons()
        
        # Crear la interfaz
        self.create_menu()
        self.create_main_layout()
                
        # Configuración inicial y mensajes de bienvenida
        self.display_welcome_message()
        
        # Vincular las teclas
        self.bind_keys()
        
        # Simular estado inicial
        self.simulate_connected_state()
    
    def load_icons(self):
        icons = {}
        
        # Si no existen los iconos, los creamos como estáticos en variables
        # Normalmente cargaríamos desde archivos, pero para este ejemplo los definimos directamente
        
        # Simulación de carga de iconos
        try:
            # Crear un directorio temporal si no existe
            os.makedirs("temp_icons", exist_ok=True)
            
            # En un caso real, cargaríamos iconos desde archivos
            return icons
        except Exception as e:
            print(f"Error al cargar iconos: {e}")
            return {}
    
    def create_menu(self):
        menubar = tk.Menu(self.root, bg=DARK_BG, fg=LIGHT_TEXT, activebackground=ACCENT_COLOR)
        self.root.config(menu=menubar)
        
        # Menú Archivo
        file_menu = tk.Menu(menubar, tearoff=0, bg=DARK_BG, fg=LIGHT_TEXT, activebackground=ACCENT_COLOR)
        file_menu.add_command(label="Nuevo Dispositivo", command=self.new_device)
        file_menu.add_command(label="Conectar", command=self.toggle_connection)
        file_menu.add_separator()
        file_menu.add_command(label="Guardar sesión", command=self.save_session)
        file_menu.add_command(label="Cargar sesión", command=self.load_session)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.root.quit)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        
        # Menú Editar
        edit_menu = tk.Menu(menubar, tearoff=0, bg=DARK_BG, fg=LIGHT_TEXT, activebackground=ACCENT_COLOR)
        edit_menu.add_command(label="Limpiar terminal", command=self.clear_terminal)
        edit_menu.add_command(label="Preferencias", command=self.show_preferences)
        menubar.add_cascade(label="Editar", menu=edit_menu)
        
        # Menú Ayuda
        help_menu = tk.Menu(menubar, tearoff=0, bg=DARK_BG, fg=LIGHT_TEXT, activebackground=ACCENT_COLOR)
        help_menu.add_command(label="Comandos comunes", command=self.show_common_commands)
        help_menu.add_command(label="Acerca de", command=self.show_about)
        menubar.add_cascade(label="Ayuda", menu=help_menu)
    
    def create_main_layout(self):
        # Crear frames
        self.top_frame = tk.Frame(self.root, bg=DARK_BG)
        self.top_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.mid_frame = tk.Frame(self.root, bg=DARK_BG)
        self.mid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.bottom_frame = tk.Frame(self.root, bg=DARK_BG)
        self.bottom_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Barra de información del dispositivo
        self.create_device_info_bar()
        
        # Terminal
        self.create_terminal()
        
        # Entrada de comandos
        self.create_command_input()
        
        # Barra de estado
        self.create_status_bar()
    
    def create_device_info_bar(self):
        info_frame = tk.Frame(self.top_frame, bg=DARK_BG)
        info_frame.pack(fill=tk.X)
        
        # Tipo de dispositivo
        self.device_type_var = tk.StringVar(value="Router")
        device_type_label = tk.Label(info_frame, text="Tipo:", bg=DARK_BG, fg=LIGHT_TEXT)
        device_type_label.pack(side=tk.LEFT, padx=(0, 5))
        device_type_combo = ttk.Combobox(info_frame, textvariable=self.device_type_var, 
                                          values=["Router", "Switch", "Firewall"], width=10, state="readonly")
        device_type_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        # Nombre del dispositivo
        self.device_name_var = tk.StringVar(value="Router1")
        device_name_label = tk.Label(info_frame, text="Nombre:", bg=DARK_BG, fg=LIGHT_TEXT)
        device_name_label.pack(side=tk.LEFT, padx=(10, 5))
        device_name_entry = tk.Entry(info_frame, textvariable=self.device_name_var, width=15)
        device_name_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Tipo de conexión
        self.connection_type_var = tk.StringVar(value="SSH")
        connection_type_label = tk.Label(info_frame, text="Conexión:", bg=DARK_BG, fg=LIGHT_TEXT)
        connection_type_label.pack(side=tk.LEFT, padx=(10, 5))
        connection_type_combo = ttk.Combobox(info_frame, textvariable=self.connection_type_var, 
                                              values=["SSH", "Telnet", "Console"], width=10, state="readonly")
        connection_type_combo.pack(side=tk.LEFT, padx=(0, 10))
        
        # Botón de conexión
        self.connect_button = tk.Button(info_frame, text="Conectar", command=self.toggle_connection, 
                                         bg=ACCENT_COLOR, fg=DARK_BG, activebackground=SUCCESS_COLOR)
        self.connect_button.pack(side=tk.RIGHT, padx=5)
        
        # Indicador de estado
        self.status_indicator = tk.Canvas(info_frame, width=15, height=15, bg=DARK_BG, highlightthickness=0)
        self.status_indicator.pack(side=tk.RIGHT, padx=5)
        self.status_indicator.create_oval(2, 2, 13, 13, fill=ERROR_COLOR, outline="")
    
    def create_terminal(self):
        terminal_frame = tk.Frame(self.mid_frame, bg=DARK_BG, bd=1, relief=tk.SUNKEN)
        terminal_frame.pack(fill=tk.BOTH, expand=True)
        
        # Estilo para el terminal
        style = ttk.Style()
        style.configure("Terminal.TFrame", background=TERMINAL_BG)
        
        # Terminal en frame con estilo
        terminal_inner_frame = ttk.Frame(terminal_frame, style="Terminal.TFrame")
        terminal_inner_frame.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        
        # Widget de texto para el terminal
        self.terminal = scrolledtext.ScrolledText(
            terminal_inner_frame,
            bg=TERMINAL_BG,
            fg=LIGHT_TEXT,
            insertbackground=LIGHT_TEXT,
            selectbackground=ACCENT_COLOR,
            selectforeground=DARK_BG,
            font=("Courier New", 11),
            wrap=tk.WORD,
            bd=0
        )
        self.terminal.pack(fill=tk.BOTH, expand=True)
        self.terminal.config(state=tk.DISABLED)
        
        # Configuración de etiquetas de color con tamaños aumentados
        self.terminal.tag_configure("command", foreground=COMMAND_COLOR, font=("Courier New", 11, "bold"))
        self.terminal.tag_configure("output", foreground=OUTPUT_COLOR, font=("Courier New", 10))
        self.terminal.tag_configure("error", foreground=ERROR_COLOR, font=("Courier New", 11, "bold"))
        self.terminal.tag_configure("success", foreground=SUCCESS_COLOR, font=("Courier New", 11, "bold"))
        self.terminal.tag_configure("system", foreground=ACCENT_COLOR, font=("Courier New", 10))
        self.terminal.tag_configure("highlight", foreground=HIGHLIGHT_COLOR, font=("Courier New", 11, "bold"))
    
    def create_command_input(self):
        input_frame = tk.Frame(self.bottom_frame, bg=DARK_BG)
        input_frame.pack(fill=tk.X, pady=5)
        
        # Etiqueta para mostrar el prompt
        self.prompt_label = tk.Label(input_frame, text=f"{self.device_name}# ", 
                                      bg=DARK_BG, fg=ACCENT_COLOR, font=("Courier New", 10))
        self.prompt_label.pack(side=tk.LEFT)
        
        # Entrada de comandos
        self.command_entry = tk.Entry(
            input_frame,
            bg=TERMINAL_BG,
            fg=LIGHT_TEXT,
            insertbackground=LIGHT_TEXT,
            font=("Courier New", 10),
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
            highlightcolor=ACCENT_COLOR
        )
        self.command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.command_entry.focus()
        
        # Botón para activar/desactivar modo AI
        self.ai_toggle_button = tk.Button(
            input_frame,
            text="🤖 AI: OFF",
            command=self.toggle_ai_mode,
            bg=BORDER_COLOR,
            fg=LIGHT_TEXT,
            activebackground=ACCENT_COLOR,
            bd=0,
            padx=15,
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT
        )
        self.ai_toggle_button.pack(side=tk.RIGHT, padx=5)
        
        # Botón de envío
        self.send_button = tk.Button(
            input_frame,
            text="Enviar",
            command=self.send_command,
            bg=ACCENT_COLOR,
            fg=DARK_BG,
            activebackground=SUCCESS_COLOR,
            bd=0,
            padx=10,
            font=("Segoe UI", 9)
        )
        self.send_button.pack(side=tk.RIGHT)
        
        # Tooltip para el comando
        self.update_command_tooltip()
    
    def create_status_bar(self):
        status_frame = tk.Frame(self.root, bg=BORDER_COLOR, height=22)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Estado de la conexión
        self.status_label = tk.Label(status_frame, text="Desconectado", bg=BORDER_COLOR, fg=LIGHT_TEXT, anchor=tk.W, padx=10)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Contador de comandos
        self.command_count = tk.Label(status_frame, text="Comandos: 0", bg=BORDER_COLOR, fg=LIGHT_TEXT, anchor=tk.E, padx=10)
        self.command_count.pack(side=tk.RIGHT)
    
    def display_welcome_message(self):
        welcome_message = """
========================================================================
              AIConsole - Control Inteligente de Switches
========================================================================
"""
        self.update_terminal(welcome_message, "system")
    
    def bind_keys(self):
        # Tecla Enter para enviar comando
        self.command_entry.bind("<Return>", lambda event: self.send_command())
        
        # Teclas de flecha para historial
        self.command_entry.bind("<Up>", lambda event: self.navigate_history(-1))
        self.command_entry.bind("<Down>", lambda event: self.navigate_history(1))
        
        # Ctrl+L para limpiar la pantalla
        self.root.bind("<Control-l>", lambda event: self.clear_terminal())
    
    def toggle_ai_mode(self):
        """Activar/desactivar modo AI"""
        self.ai_mode = not self.ai_mode
        
        if self.ai_mode:
            self.ai_toggle_button.config(
                text="🤖 AI: ON",
                bg=SUCCESS_COLOR,
                fg=DARK_BG
            )
        else:
            self.ai_toggle_button.config(
                text="🤖 AI: OFF",
                bg=BORDER_COLOR,
                fg=LIGHT_TEXT
            )
        
        self.update_command_tooltip()
    
    def update_command_tooltip(self):
        """Actualizar tooltip según el modo activo"""
        if self.ai_mode:
            tooltip_text = "Modo AI: Ingresa comandos en lenguaje natural (español o inglés)"
        else:
            tooltip_text = "Modo Putty: Ingresa comandos Cisco directos (ej: show version)"
        
        # Remover tooltip anterior si existe
        if hasattr(self, 'command_tooltip'):
            self.command_tooltip.widget.unbind("<Enter>")
            self.command_tooltip.widget.unbind("<Leave>")
        
        # Crear nuevo tooltip
        self.command_tooltip = ToolTip(self.command_entry, tooltip_text)
    
    def update_terminal(self, text, tag=None):
        self.terminal.config(state=tk.NORMAL)
        if tag:
            self.terminal.insert(tk.END, text + "\n", tag)
        else:
            self.terminal.insert(tk.END, text + "\n")
        self.terminal.see(tk.END)
        self.terminal.config(state=tk.DISABLED)
    
    def send_command(self):
        command = self.command_entry.get().strip()
        if not command:
            return
        
        # Guardar en historial
        self.history.append(command)
        self.history_index = len(self.history)
        
        # Mostrar el comando en el terminal
        self.update_terminal(f"{self.device_name}# {command}", "command")
        
        # Limpiar entrada
        self.command_entry.delete(0, tk.END)
        
        # Actualizar contador de comandos
        self.command_count.config(text=f"Comandos: {len(self.history)}")
        
        # Verificar conexión
        if not self.connected:
            self.update_terminal("Error: No hay conexión con el dispositivo. Por favor, conéctese primero.", "error")
            return
        
        # Mostrar animación de "pensando"
        self.show_thinking_animation()
        
        # Enviar comando al backend
        threading.Thread(target=self.process_command, args=(command,)).start()
    
    def process_command(self, command):
        try:
            # Determinar el endpoint según el modo
            if self.ai_mode:
                # Modo AI: usar endpoint con IA
                response = requests.post('http://localhost:3000/comando', json={
                    "mensaje": command, 
                    "execute": True
                }, timeout=60)  # Increased timeout for AI processing
            else:
                # Modo Putty: enviar comando directo sin IA
                response = requests.post('http://localhost:3000/execute', json={
                    "commands": command
                }, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                
                # Detener animación de pensamiento
                self.root.after_cancel(self.thinking_animation_id)
                self.terminal.config(state=tk.NORMAL)
                self.terminal.delete("thinking_line.first", "thinking_line.last")
                self.terminal.config(state=tk.DISABLED)
                
                # Modo AI: mostrar comandos generados
                if self.ai_mode:
                    generated_commands = result.get('respuesta', 'No commands generated')
                    
                    # Verificar si hubo error de rate limit en el resultado
                    if result.get('error') and 'rate' in str(result.get('error')).lower():
                        self.update_terminal("", "error")
                        self.update_terminal("=" * 60, "error")
                        self.update_terminal("⚠️  ERROR: LÍMITE DE VELOCIDAD ALCANZADO", "error")
                        self.update_terminal("=" * 60, "error")
                        self.update_terminal("El servicio de IA está temporalmente limitado.", "system")
                        self.update_terminal("", "system")
                        self.update_terminal("Opciones:", "system")
                        self.update_terminal("1. Espera 1 minuto e intenta de nuevo", "system")
                        self.update_terminal("2. Cambia a modo Putty (🤖 AI: OFF)", "system")
                        self.update_terminal("3. Usa comandos Cisco directos", "system")
                        self.update_terminal("", "system")
                        return
                    
                    self.update_terminal("", "system")
                    self.update_terminal("=" * 60, "system")
                    self.update_terminal("COMANDOS GENERADOS:", "highlight")
                    self.update_terminal("=" * 60, "system")
                    self.update_terminal(generated_commands, "command")
                    self.update_terminal("", "system")
                
                # Show execution results if available
                if result.get('executed', False) or result.get('success', False):
                    self.update_terminal("=" * 60, "success")
                    self.update_terminal("RESULTADOS DE EJECUCIÓN:", "success")
                    self.update_terminal("=" * 60, "success")
                    
                    # Para modo AI
                    if 'device_responses' in result:
                        device_responses = result.get('device_responses', [])
                        
                        for i, cmd_result in enumerate(device_responses, 1):
                            cmd = cmd_result.get('command', '')
                            response_text = cmd_result.get('response', '')
                            
                            self.update_terminal(f"\n[{i}] Comando ejecutado:", "system")
                            self.update_terminal(f"    {cmd}", "command")
                            
                            if response_text:
                                self.update_terminal(f"Respuesta del switch:", "system")
                                for line in response_text.split('\\n'):
                                    if line.strip():
                                        self.update_terminal(f"    {line}", "output")
                    
                    # Para modo Putty directo
                    elif 'results' in result:
                        results = result.get('results', [])
                        for i, cmd_result in enumerate(results, 1):
                            cmd = cmd_result.get('command', '')
                            response_text = cmd_result.get('response', '')
                            
                            if cmd:
                                self.update_terminal(f"\n[{i}] {cmd}", "command")
                            if response_text:
                                for line in response_text.split('\\n'):
                                    if line.strip():
                                        self.update_terminal(f"    {line}", "output")
                    
                    self.update_terminal("=" * 60, "success")
                    
                else:
                    # Error en la ejecución
                    error = result.get('error', 'Unknown error')
                    self.update_terminal("", "error")
                    self.update_terminal("=" * 60, "error")
                    self.update_terminal("ERROR EN LA EJECUCIÓN", "error")
                    self.update_terminal("=" * 60, "error")
                    self.update_terminal(error, "error")
                    self.update_terminal("", "system")
                    
                    if self.ai_mode:
                        self.update_terminal("Los comandos fueron generados pero no se ejecutaron.", "system")
                    else:
                        self.update_terminal("El comando no pudo ser ejecutado en el switch.", "system")
                
            elif response.status_code == 429:
                # Rate limit específico del servidor
                self.handle_rate_limit_error()
            else:
                self.update_terminal(f"Error: Server response ({response.status_code})", "error")
                
        except requests.RequestException as e:
            error_msg = str(e)
            
            # Detener animación de pensamiento si hay error
            try:
                self.root.after_cancel(self.thinking_animation_id)
                self.terminal.config(state=tk.NORMAL)
                self.terminal.delete("thinking_line.first", "thinking_line.last")
                self.terminal.config(state=tk.DISABLED)
            except:
                pass
            
            # Verificar si es error de rate limit
            if '429' in error_msg or 'rate' in error_msg.lower():
                self.handle_rate_limit_error()
            else:
                self.update_terminal(f"Connection error: {error_msg}", "error")
    
    def handle_rate_limit_error(self):
        """Manejar error de rate limit de forma informativa"""
        self.update_terminal("", "error")
        self.update_terminal("=" * 60, "error")
        self.update_terminal("⚠️  LÍMITE DE VELOCIDAD ALCANZADO", "error")
        self.update_terminal("=" * 60, "error")
        self.update_terminal("", "system")
        self.update_terminal("El servicio de IA está temporalmente limitado.", "system")
        self.update_terminal("Esto sucede cuando se hacen muchas peticiones seguidas.", "system")
        self.update_terminal("", "system")
        self.update_terminal("SOLUCIONES:", "highlight")
        self.update_terminal("", "system")
        self.update_terminal("1️⃣  Espera 60 segundos e intenta de nuevo", "system")
        self.update_terminal("", "system")
        self.update_terminal("2️⃣  Cambia a MODO PUTTY (🤖 AI: OFF)", "success")
        self.update_terminal("    - Envía comandos Cisco directos", "system")
        self.update_terminal("    - Sin límites de velocidad", "system")
        self.update_terminal("    - Ejemplo: show version", "system")
        self.update_terminal("", "system")
        self.update_terminal("3️⃣  Usa comandos básicos mientras esperas", "system")
        self.update_terminal("", "system")
        self.update_terminal("=" * 60, "error")
        self.update_terminal("", "system")
    
    def format_and_display_result(self, result):
        self.terminal.config(state=tk.NORMAL)
        
        # Formatear el resultado como salida de comando Cisco
        lines = result.strip().split('\n')
        for line in lines:
            # Detectar si es un comando o resultado
            if line.strip().startswith(self.device_name) or "config" in line:
                self.terminal.insert(tk.END, line + "\n", "command")
            else:
                self.terminal.insert(tk.END, line + "\n", "output")
        
        self.terminal.see(tk.END)
        self.terminal.config(state=tk.DISABLED)
    
    def show_thinking_animation(self):
        self.terminal.config(state=tk.NORMAL)
        self.terminal.insert(tk.END, "Procesando comando ", "system")
        self.terminal.mark_set("thinking_line.first", "end-1c linestart")
        self.terminal.mark_gravity("thinking_line.first", "left")
        self.terminal.insert(tk.END, ".", "system")
        self.terminal.mark_set("thinking_line.last", "end-1c")
        self.terminal.mark_gravity("thinking_line.last", "right")
        self.terminal.config(state=tk.DISABLED)
        self.thinking_dots = 1
        self.thinking_animation_id = self.root.after(300, self.update_thinking_animation)
    
    def update_thinking_animation(self):
        self.terminal.config(state=tk.NORMAL)
        current_text = self.terminal.get("thinking_line.first", "thinking_line.last")
        
        # Limpiar puntos actuales
        self.terminal.delete("thinking_line.first", "thinking_line.last")
        
        # Añadir nuevos puntos
        self.thinking_dots = (self.thinking_dots % 3) + 1
        dots = "." * self.thinking_dots
        self.terminal.insert("thinking_line.first", dots, "system")
        
        self.terminal.config(state=tk.DISABLED)
        self.terminal.see(tk.END)
        
        # Programar la siguiente actualización
        self.thinking_animation_id = self.root.after(300, self.update_thinking_animation)
    
    def navigate_history(self, direction):
        if not self.history:
            return
        
        # Actualizar índice
        new_index = self.history_index + direction
        if 0 <= new_index < len(self.history):
            self.history_index = new_index
            # Actualizar entrada con el comando del historial
            self.command_entry.delete(0, tk.END)
            self.command_entry.insert(0, self.history[self.history_index])
    
    def clear_terminal(self):
        self.terminal.config(state=tk.NORMAL)
        self.terminal.delete(1.0, tk.END)
        self.terminal.config(state=tk.DISABLED)
        self.display_welcome_message()
    
    def toggle_connection(self):
        if self.connected:
            # Desconectar
            self.connected = False
            self.connect_button.config(text="Conectar", bg=ACCENT_COLOR)
            self.status_indicator.itemconfig(1, fill=ERROR_COLOR)
            self.status_label.config(text="Desconectado")
            self.update_terminal(f"Conexion cerrada.", "error")
        else:
            # Intentar conexion REAL
            self.update_terminal(f"Verificando conexion serial USB...", "system")
            self.root.update()
            
            try:
                response = requests.get('http://localhost:3000/connection-status', timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('connected'):
                        # Conexion exitosa
                        self.connected = True
                        self.connect_button.config(text="Desconectar", bg=SUCCESS_COLOR)
                        self.status_indicator.itemconfig(1, fill=SUCCESS_COLOR)
                        self.status_label.config(text="Conectado via USB Serial (/dev/ttyUSB0)")
                        
                        self.update_terminal("", "system")
                        self.update_terminal("=" * 60, "success")
                        self.update_terminal("CONEXION ESTABLECIDA CON SWITCH", "success")
                        self.update_terminal("=" * 60, "success")
                        self.update_terminal(f"Puerto: /dev/ttyUSB0", "system")
                        self.update_terminal(f"Baudrate: 9600", "system")
                        self.update_terminal(f"Estado: Autenticado", "success")
                        self.update_terminal("=" * 60, "success")
                        self.update_terminal("", "system")
                    else:
                        # Conexion fallida
                        self.connected = False
                        self.update_terminal("", "system")
                        self.update_terminal("ERROR: No se pudo conectar al switch", "error")
                        self.update_terminal(result.get('message', 'Unknown error'), "error")
                        self.update_terminal("", "system")
                        self.update_terminal("Verifica:", "system")
                        self.update_terminal("1. Switch encendido", "system")
                        self.update_terminal("2. Cable USB conectado", "system")
                        self.update_terminal("3. Puerto correcto (/dev/ttyUSB0)", "system")
                else:
                    self.update_terminal(f"Error del servidor: {response.status_code}", "error")
                    
            except requests.RequestException as e:
                self.update_terminal(f"Error de conexion con backend: {str(e)}", "error")
    
    def simulate_device_welcome(self):
        device_welcome = f"""
{self.device_name}#
*                                                                    *
*                      Cisco Internetwork Operating System           *
*                             Software (IOS)                         *
*         Copyright (c) 1986-2025 by cisco Systems, Inc.             *
*                Compiled Wed 12-Feb-25 12:05 by prod_rel_team       *
*                                                                    *
* Version 17.9.1, RELEASE SOFTWARE (fc2)                             *
* Technical Support: http://www.cisco.com/techsupport                *
*                                                                    *
*                                                                    *
{self.device_name}#
"""
        self.update_terminal(device_welcome, "system")
    
    def simulate_connected_state(self):
        # Start with disconnected state - user must manually connect
        pass
    
    def new_device(self):
        # En una implementación real, mostraríamos un diálogo para configurar un nuevo dispositivo
        messagebox.showinfo("Nuevo Dispositivo", "Funcionalidad para agregar nuevos dispositivos en desarrollo.")
    
    def save_session(self):
        # Simulación de guardado de sesión
        messagebox.showinfo("Guardar Sesión", "Sesión guardada correctamente.")
    
    def load_session(self):
        # Simulación de carga de sesión
        messagebox.showinfo("Cargar Sesión", "Funcionalidad para cargar sesiones en desarrollo.")
    
    def show_preferences(self):
        # En una implementación real, mostraríamos un diálogo de preferencias
        messagebox.showinfo("Preferencias", "Funcionalidad de preferencias en desarrollo.")
    
    def show_common_commands(self):
        commands = """Comandos comunes para dispositivos Cisco:

1. Ver configuración:
   - show running-config
   - show startup-config

2. Configuración de interfaces:
   - interface GigabitEthernet0/1
   - ip address 192.168.1.1 255.255.255.0
   - no shutdown

3. Configuración de VLAN:
   - vlan 10
   - name Finance
   - interface GigabitEthernet0/1
   - switchport mode access
   - switchport access vlan 10

4. Configuración de routing:
   - ip route 0.0.0.0 0.0.0.0 192.168.1.254
   - router ospf 1
   - network 192.168.1.0 0.0.0.255 area 0

5. Guardar configuración:
   - copy running-config startup-config
"""
        # Crear una ventana pop-up
        help_window = tk.Toplevel(self.root)
        help_window.title("Comandos Comunes")
        help_window.geometry("600x400")
        help_window.configure(bg=DARK_BG)
        
        # Texto con los comandos
        text = scrolledtext.ScrolledText(
            help_window,
            bg=TERMINAL_BG,
            fg=LIGHT_TEXT,
            font=("Courier New", 10),
            wrap=tk.WORD,
            padx=10,
            pady=10
        )
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text.insert(tk.END, commands)
        text.config(state=tk.DISABLED)
    
    def show_about(self):
        about_text = """
IA en Consola - Asistente Inteligente para Redes

Versión: 1.0.0
Desarrollado por: Arturo Rosales V.

Esta herramienta permite interactuar con dispositivos de red Cisco
utilizando lenguaje natural. La IA interpreta tus instrucciones
y genera los comandos Cisco correspondientes.

© 2025 
"""
        messagebox.showinfo("Acerca de", about_text)


# Iniciar la aplicación
if __name__ == "__main__":
    root = tk.Tk()
    app = NetworkConsole(root)
    
    # Configurar el tema para ttk
    style = ttk.Style()
    style.theme_use('clam')  # Usar un tema base que podamos personalizar
    
    # Personalizar los comboboxes
    style.configure("TCombobox", 
                   fieldbackground=TERMINAL_BG,
                   background=DARK_BG,
                   foreground=LIGHT_TEXT,
                   arrowcolor=ACCENT_COLOR)
    style.map("TCombobox",
              fieldbackground=[("readonly", TERMINAL_BG)],
              selectbackground=[("readonly", ACCENT_COLOR)],
              selectforeground=[("readonly", DARK_BG)])
    
    # Iniciar el loop principal
    root.mainloop()