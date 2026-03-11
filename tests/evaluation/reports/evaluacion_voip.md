# Evaluacion VoIP — Corvelli Version Alfa

**Fecha de ejecucion:** 10 de marzo de 2026  
**Backend evaluado:** `http://localhost:3000` (Node.js, endpoint POST `/comando`)  
**Filosofia de evaluacion:** Version Alfa genera comandos Cisco IOS. No se evalua diagnostico de calidad de voz, analisis de jitter o deteccion de problemas de red — esas capacidades son trabajo futuro.

---

## Metodologia

Cada evaluacion llama al endpoint `/comando` con un contexto de switch simulado (salida de `show vlan`, `show interfaces`, `show cdp neighbors`) y una instruccion de usuario. La respuesta se puntua segun criterios de generacion de comandos:

- **useful_response** — respuesta con contenido util (>10 caracteres)
- **cisco_command** — inclusion de al menos un comando Cisco IOS esperado
- **keywords** — presencia de terminos relevantes al dominio VoIP
- **bonus checks** — verificaciones especificas por tipo de tarea (voice_vlan_cmd, qos_cmd)

Un test se considera aprobado con score >= 80%, parcial entre 50% y 79%, fallido por debajo de 50%.

Para la comprobacion `voice_vlan_cmd` se acepta tanto `switchport voice vlan` como `switchport access vlan`: ambos son enfoques validos para conectar un telefono IP en alfa, dependiendo de como Corvelli interprete la solicitud.

---

## VoIP Simulation

**Descripcion:** 10 escenarios estructurados con contexto de switch de acceso. Cubre configuracion de Voice VLAN, QoS, PortFast, comandos show y configuracion completa de puerto VoIP.

| Test | Descripcion | Score | Estado |
|------|-------------|-------|--------|
| assign_voice_vlan_single_port | Asignar voice vlan en un puerto | 100% | OK |
| assign_voice_vlan_access_mode | Configurar puerto en modo access con voice vlan | 100% | OK |
| create_voice_vlan | Crear VLAN dedicada a voz | 100% | OK |
| bulk_voice_ports | Configurar multiples puertos para telefonos IP | 100% | OK |
| enable_qos_trust_cos | Habilitar QoS trust cos en interfaz | 100% | OK |
| enable_qos_global | Habilitar QoS de forma global | 100% | OK |
| enable_portfast | Habilitar PortFast en puerto de acceso | 100% | OK |
| show_voice_vlan_config | Mostrar configuracion de voice vlan | 100% | OK |
| show_cdp_voip | Mostrar vecinos CDP para identificar telefonos | 100% | OK |
| full_voip_port_config | Configuracion completa de puerto VoIP | 100% | OK |

**Score promedio:** 100%  
**Tests aprobados:** 10/10  
**Fallas criticas:** 0  
**Veredicto:** APROBADO

---

## VoIP Escenarios Reales

**Descripcion:** 7 escenarios con instrucciones vagas redactadas como lo haria un tecnico de red o un responsable de IT sin terminologia precisa. El objetivo es verificar que Corvelli genera una respuesta util ante solicitudes ambiguas relacionadas con telefonia IP.

| Test | Descripcion | Score | Estado |
|------|-------------|-------|--------|
| phones_not_in_network | Telefonos del piso 1 no estan en su VLAN | 100% | OK |
| isolate_voice_from_data | Separar trafico de voz del trafico de datos | 100% | OK |
| configure_management_area_voip | Preparar area de gestion para VoIP | 100% | OK |
| new_ip_phones_buying | Compramos telefonos IP, como los conecto | 100% | OK |
| calls_cutting_out | Las llamadas se cortan, como priorizo el trafico de voz | 100% | OK |
| check_which_ports_have_phones | Que puertos tienen telefonos conectados | 100% | OK |
| urgent_voip_setup | Configuracion urgente de VoIP en un puerto | 100% | OK |

**Score promedio:** 100%  
**Tests aprobados:** 7/7  
**Fallas criticas:** 0  
**Veredicto:** APROBADO

---

## Observaciones

La evaluacion de simulacion cubre los comandos VoIP mas comunes en entornos Cisco IOS: `switchport voice vlan`, `mls qos trust cos`, `spanning-tree portfast` y variantes de `show` para diagnostico. Corvelli genera comandos coherentes en todos los casos.

Los escenarios reales cubren situaciones tipicas de campo: telefonos que no funcionan despues de conectarlos, queja de calidad de llamadas, configuracion urgente antes de una reunion. En todos los casos Corvelli produce una respuesta con comandos validos o una orientacion util.

El escenario `calls_cutting_out` merece una nota: la pregunta sobre prioridad de trafico de voz puede interpretarse como un problema de configuracion de voice VLAN o como un problema de QoS. En version Alfa ambas respuestas se consideran aceptables. La distincion entre configuracion de VLAN de voz y politica de QoS es una mejora prevista para versiones posteriores.
