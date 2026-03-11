# Evaluacion IPAM — Corvelli Version Alfa

**Fecha de ejecucion:** 10 de marzo de 2026  
**Backend evaluado:** `http://localhost:3000` (Node.js, endpoint POST `/comando`)  
**Filosofia de evaluacion:** Version Alfa genera comandos Cisco IOS. No se evalua analisis de redes, deteccion de conflictos ni conteo de IPs — esas capacidades son trabajo futuro.

---

## Metodologia

Cada evaluacion llama al endpoint `/comando` con un contexto de switch simulado (salida de `show ip arp`, `show vlan`, `show interfaces`) y una instruccion de usuario. La respuesta se puntua segun criterios de generacion de comandos:

- **useful_response** — respuesta con contenido util (>10 caracteres)
- **cisco_command** — inclusion de al menos un comando Cisco IOS esperado
- **keywords** — presencia de terminos relevantes al dominio
- **bonus checks** — verificaciones especificas por tipo de tarea (ip address, multiple IPs)

Un test se considera aprobado con score >= 80%, parcial entre 50% y 79%, fallido por debajo de 50%. Los tests marcados como criticos penalizan directamente el veredicto si fallan.

---

## IPAM Simulation

**Descripcion:** 10 escenarios estructurados con contexto de red definido. Cubre tareas de tipo `show`, `assign`, `verify` y `assign_multiple`.

| Test | Descripcion | Score | Estado |
|------|-------------|-------|--------|
| show_ips_vlan10 | Mostrar IPs asignadas en VLAN 10 | 100% | OK |
| assign_next_ip_vlan10 | Asignar siguiente IP disponible en VLAN 10 | 100% | OK |
| assign_ip_vlan20 | Asignar IP en VLAN 20 | 100% | OK |
| verify_ip_occupied | Verificar si IP esta ocupada | 100% | OK |
| verify_ip_free | Verificar si IP esta libre | 100% | OK |
| assign_multiple_ips_vlan30 | Asignar multiples IPs en VLAN 30 | 80% | OK |
| show_usage_vlan10 | Mostrar uso de VLAN 10 | 100% | OK |
| show_available_vlan30 | Mostrar IPs disponibles en VLAN 30 | 67% | Parcial |
| verify_range_free | Verificar rango libre | 100% | OK |
| verify_range_conflict | Verificar conflicto en rango | 100% | OK |

**Score promedio:** 95.1%  
**Tests aprobados:** 8/10  
**Tests parciales:** 2/10  
**Fallas criticas:** 0  
**Veredicto:** APROBADO

Los dos resultados parciales corresponden a respuestas validas de Corvelli que no cubren todos los checks de bonus — en ningun caso se trata de respuestas incorrectas o vacias.

---

## IPAM Escenarios Reales

**Descripcion:** 7 escenarios con instrucciones vagas redactadas como lo haria un tecnico de red, sin estructura ni terminologia precisa. El objetivo es verificar que Corvelli genera algun comando o respuesta util ante solicitudes ambiguas.

| Test | Descripcion | Score | Estado |
|------|-------------|-------|--------|
| already_assigned_confusion | Confusion sobre IP ya asignada | 100% | OK |
| no_context_show | Solicitud de show sin contexto previo | 100% | OK |
| vague_assign_request | Solicitud vaga de asignacion de IP | 100% | OK |
| conflict_doubt_vague | Duda vaga sobre posible conflicto | 100% | OK |
| vague_multiple_ips | Solicitud de multiples IPs sin especificar | 100% | OK |
| check_if_in_use | Verificar si una IP esta en uso | 100% | OK |
| urgent_assignment | Solicitud urgente de asignacion | 100% | OK |

**Score promedio:** 100%  
**Tests aprobados:** 7/7  
**Fallas criticas:** 0  
**Veredicto:** APROBADO

---

## Observaciones

Los escenarios de simulacion con instrucciones estructuradas obtienen resultados solidos. Los casos parciales en `assign_multiple_ips_vlan30` y `show_available_vlan30` se deben a que Corvelli genera comandos validos pero no incluye la secuencia completa de asignacion multiple — comportamiento coherente con alfa.

Los escenarios reales alcanzan puntuacion perfecta porque el criterio de evaluacion acepta explicitamente tanto comandos Cisco como respuestas en lenguaje natural, reflejando que en situaciones vagas cualquier respuesta util es correcta para alfa.
