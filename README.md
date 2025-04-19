
# 🧠 Consola Inteligente para Redes

**Consola Inteligente para Redes** es una herramienta que transforma instrucciones en lenguaje natural en comandos reales para dispositivos de red, utilizando inteligencia artificial. Su interfaz de escritorio permite a cualquier usuario escribir lo que desea hacer —como "ver interfaces activas"— y recibir al instante el comando exacto a ejecutar, todo sin necesidad de conocimientos avanzados en redes.

Este proyecto tiene como objetivo acelerar la administración de redes, servir como asistente de estudio para estudiantes de cisco, e incluso convertirse en una herramienta confiable para automatizar tareas técnicas en infraestructura.

## ✨ Características principales

- 🧠 Traducción automática de lenguaje natural a comandos Cisco.
- 🖥️ Interfaz de escritorio simple con Python + Tkinter.
- 🔌 Backend basado en Node.js con conexión a modelos LLM (IA) como DeepSeek vía OpenRouter.
- 🔒 Separación entre frontend (visual) y backend (IA), ideal para escalar y personalizar.
- 🚀 Rápido, intuitivo, listo para probar en segundos.

## 🚧 ¿Qué puedes hacer con esto?

- Preguntar cosas como:
  - "ver interfaces activas"
  - "configurar IP en fa0/1"
  - "mostrar configuración actual"
- Y obtener:
  - `show ip interface brief`
  - `interface FastEthernet0/1
ip address 192.168.1.1 255.255.255.0`
  - `show running-config`

## 📦 Tecnologías utilizadas

- **Frontend**: Python 3 + Tkinter
- **Backend**: Node.js + Express
- **IA**: OpenRouter (modelo DeepSeek)
- **Formato**: API tipo OpenAI

## ⚙️ Instalación rápida

1. Clona este repositorio.
2. Instala las dependencias del backend:
   ```bash
   cd backend
   npm install
   ```
3. Ejecuta el servidor backend:
   ```bash
   node server.js
   ```
4. Abre el frontend:
   ```bash
   cd ../frontend
   python app.py
   ```

## 🛠️ Próximas funciones

- Ejecución SSH real de los comandos generados.
- Soporte para múltiples vendors (MikroTik, Juniper, etc.).
- Modo aprendizaje y explicación de comandos.
- Historial de comandos generados.
- Compatibilidad web con Electron.js

---

## 🤝 Créditos

Proyecto desarrollado por Arturo Rosales V.  
Estudiante de Ingeniería en Tecnologías de la Información  
Universidad Politécnica de Victoria  
El mejor programador que el mundo haya visto 🌟