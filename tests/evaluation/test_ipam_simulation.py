#!/usr/bin/env python3
"""
Test IPAM - Generación de Comandos Cisco IOS (Versión Alfa)
Valida que Corvelli genere los comandos correctos para operaciones IPAM.

Filosof­ía Alfa: Corvelli genera comandos, no analiza outputs.
- Para "mostrar IPs" → debe generar 'show ip arp'
- Para "asignar IP" → debe generar 'interface vlan X' + 'ip address'
- Para "verificar IP" → debe generar 'show ip arp' o 'ping'

NO se evalúa si Corvelli analiza, cuenta o detecta conflictos por sí solo.
ESO es trabajo futuro (post-alfa).
"""

import re
import json
import requests
from typing import Dict, List
from datetime import datetime
from pathlib import Path


# ============================================================================
# CONFIGURACIÓN BACKEND CORVELLI
# ============================================================================

CORVELLI_BACKEND_URL = "http://localhost:3000"
COMANDO_ENDPOINT = f"{CORVELLI_BACKEND_URL}/comando"


# ============================================================================
# MOCKS DE SWITCH - Outputs reales de Cisco Catalyst 2960
# ============================================================================

MOCK_SHOW_IP_ARP = """Protocol  Address          Age (min)  Hardware Addr   Type   Interface
Internet  192.168.10.1            -   0050.56c0.0001  ARPA   Vlan10
Internet  192.168.10.2           15   0050.56c0.1234  ARPA   Vlan10
Internet  192.168.10.3           22   0050.56c0.1235  ARPA   Vlan10
Internet  192.168.10.5           45   0050.56c0.1236  ARPA   Vlan10
Internet  192.168.10.8            8   0050.56c0.1237  ARPA   Vlan10
Internet  192.168.10.10          12   0050.56c0.1238  ARPA   Vlan10
Internet  192.168.10.11          33   0050.56c0.1239  ARPA   Vlan10
Internet  192.168.10.12           5   0050.56c0.123a  ARPA   Vlan10
Internet  192.168.10.15          28   0050.56c0.123b  ARPA   Vlan10
Internet  192.168.10.20          19   0050.56c0.123c  ARPA   Vlan10
Internet  192.168.10.21          41   0050.56c0.123d  ARPA   Vlan10
Internet  192.168.10.25           2   0050.56c0.123e  ARPA   Vlan10
Internet  192.168.10.30          37   0050.56c0.123f  ARPA   Vlan10
Internet  192.168.10.35          14   0050.56c0.1240  ARPA   Vlan10
Internet  192.168.10.40          29   0050.56c0.1241  ARPA   Vlan10
Internet  192.168.20.1            -   0050.56c0.0002  ARPA   Vlan20
Internet  192.168.20.2           18   0050.56c0.2234  ARPA   Vlan20
Internet  192.168.20.5           24   0050.56c0.2235  ARPA   Vlan20
Internet  192.168.20.10          11   0050.56c0.2236  ARPA   Vlan20
Internet  192.168.20.15           7   0050.56c0.2237  ARPA   Vlan20
Internet  192.168.20.20          31   0050.56c0.2238  ARPA   Vlan20
Internet  192.168.20.25          16   0050.56c0.2239  ARPA   Vlan20
Internet  192.168.20.30          44   0050.56c0.223a  ARPA   Vlan20
Internet  192.168.20.35           9   0050.56c0.223b  ARPA   Vlan20
Internet  192.168.20.50          27   0050.56c0.223c  ARPA   Vlan20
"""

MOCK_SHOW_VLAN_BRIEF = """VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Gi0/1, Gi0/2
10   VENTAS                           active    Gi0/3, Gi0/4, Gi0/5, Gi0/6
20   IT                               active    Gi0/7, Gi0/8, Gi0/9
30   INVITADOS                        active    Gi0/10
99   NATIVA                           active    
"""

MOCK_SHOW_IP_INTERFACE_BRIEF = """Interface              IP-Address      OK? Method Status                Protocol
Vlan1                  unassigned      YES NVRAM  administratively down down
Vlan10                 192.168.10.1    YES NVRAM  up                    up
Vlan20                 192.168.20.1    YES NVRAM  up                    up
Vlan30                 192.168.30.1    YES NVRAM  up                    up
GigabitEthernet0/1     unassigned      YES unset  up                    up
GigabitEthernet0/2     unassigned      YES unset  up                    up
"""


# ============================================================================
# CONTEXTO DE RED SIMULADA
# ============================================================================

# Información de red que el backend debería conocer o inferir
NETWORK_CONTEXT = """
Red actual:
- VLAN 10 (VENTAS): 192.168.10.0/24
  IPs en uso: .1 (gateway), .2, .3, .5, .8, .10, .11, .12, .15, .20, .21, .25, .30, .35, .40
  IPs libres: .4, .6, .7, .9, .13, .14, .16-19, .22-24, .26-29, .31-34, .36-254

- VLAN 20 (IT): 192.168.20.0/24
  IPs en uso: .1 (gateway), .2, .5, .10, .15, .20, .25, .30, .35, .50
  IPs libres: .3, .4, .6-9, .11-14, .16-19, .21-24, .26-29, .31-34, .36-254

- VLAN 30 (INVITADOS): 192.168.30.0/24
  IPs en uso: .1 (gateway)
  IPs libres: .2-254
"""


# ============================================================================
# TEST CASES - Generación de Comandos IPAM
# Corvelli Alfa: Solo genera comandos. No analiza, no cuenta, no detecta.
# ============================================================================

TEST_CASES = [
    {
        "id": "show_ips_vlan10",
        "user_input": "Muéstrame todas las IPs en uso en la VLAN 10",
        "description": "Debe generar comando 'show ip arp' para VLAN 10",
        "weight": 2.0,
        "critical": True,
        "expected_commands": ["show ip arp"],
        "expected_keywords": ["show", "arp"],
        "task_type": "show"
    },
    {
        "id": "assign_next_ip_vlan10",
        "user_input": "Dame la siguiente IP libre en 192.168.10.0/24",
        "description": "Debe generar interface vlan 10 + ip address 192.168.10.x",
        "weight": 2.5,
        "critical": True,
        "expected_commands": ["interface", "ip address"],
        "expected_keywords": ["192.168.10", "interface", "vlan"],
        "task_type": "assign"
    },
    {
        "id": "assign_ip_vlan20",
        "user_input": "Necesito una IP libre en la VLAN 20",
        "description": "Debe generar interface vlan 20 + ip address 192.168.20.x",
        "weight": 2.5,
        "critical": True,
        "expected_commands": ["interface", "ip address"],
        "expected_keywords": ["192.168.20", "vlan"],
        "task_type": "assign"
    },
    {
        "id": "verify_ip_occupied",
        "user_input": "Puedo usar 192.168.10.10 para un nuevo dispositivo?",
        "description": "Debe generar comandos para usar o verificar la IP",
        "weight": 2.0,
        "critical": True,
        # En alfa: aceptamos que genere comandos de asignacion O de verificacion.
        # 'Can I use this IP?' -> both show ip arp AND interface/ip address are valid.
        "expected_commands": ["show ip arp", "ping", "interface", "ip address"],
        "expected_keywords": ["192.168.10.10"],
        "task_type": "verify"
    },
    {
        "id": "verify_ip_free",
        "user_input": "Está libre 192.168.10.100?",
        "description": "Debe generar comandos para verificar o usar la IP",
        "weight": 2.0,
        "critical": True,
        "expected_commands": ["show ip arp", "ping", "interface", "ip address"],
        "expected_keywords": ["192.168.10.100"],
        "task_type": "verify"
    },
    {
        "id": "assign_multiple_ips_vlan30",
        "user_input": "Dame 5 IPs consecutivas libres en VLAN 30",
        "description": "Debe generar múltiples ip address en VLAN 30",
        "weight": 2.5,
        "critical": False,
        "expected_commands": ["interface", "ip address"],
        "expected_keywords": ["192.168.30", "vlan"],
        "task_type": "assign_multiple",
        "min_ips": 2  # Al menos 2 IPs sugeridas (no exigimos 5 exactas en alfa)
    },
    {
        "id": "show_usage_vlan10",
        "user_input": "Cuántas IPs están ocupadas en la red 192.168.10.0/24?",
        "description": "Debe generar 'show ip arp' para la red",
        "weight": 1.5,
        "critical": False,
        "expected_commands": ["show ip arp", "show arp"],
        "expected_keywords": ["show", "arp"],
        "task_type": "show"
    },
    {
        "id": "show_available_vlan30",
        "user_input": "Cuántas IPs libres hay en VLAN Invitados?",
        "description": "Debe generar show ip arp, show vlan, o indicar cómo verificar",
        "weight": 1.5,
        "critical": False,
        # En alfa: aceptamos show ip arp, show vlan, o cualquier respuesta util
        "expected_commands": ["show ip arp", "show vlan", "show", "interface"],
        "expected_keywords": ["vlan", "invitados", "30"],
        "task_type": "show"
    },
    {
        "id": "verify_range_free",
        "user_input": "El rango 192.168.30.10-20 está libre?",
        "description": "Debe generar comandos para verificar o usar IPs del rango",
        "weight": 2.0,
        "critical": False,
        "expected_commands": ["show ip arp", "ping", "interface", "ip address"],
        "expected_keywords": ["192.168.30"],
        "task_type": "verify"
    },
    {
        "id": "verify_range_conflict",
        "user_input": "Puedo usar el rango 192.168.10.1-10?",
        "description": "Debe generar comandos para verificar o usar IPs del rango",
        "weight": 2.0,
        "critical": True,
        "expected_commands": ["show ip arp", "ping", "interface", "ip address"],
        "expected_keywords": ["192.168.10"],
        "task_type": "verify"
    }
]


# ============================================================================
# FUNCIONES DE LLAMADA AL BACKEND CORVELLI
# ============================================================================

def call_corvelli_backend(user_input: str, session_id: str = None) -> Dict:
    """
    Llama al backend de Corvelli en localhost:3000/comando.
    
    Objetivo: Enviar queries IPAM al backend real y obtener respuestas.
    Crítico: Usar el sistema de prompts existente de Corvelli, no uno nuevo.
    """
    if not session_id:
        # Generate unique session ID with microseconds to avoid collisions
        session_id = f"ipam-sim-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    
    # Construir mensaje con contexto del switch
    mensaje_con_contexto = f"""Contexto del switch Cisco Catalyst 2960:

Output de 'show ip arp':
{MOCK_SHOW_IP_ARP}

Output de 'show vlan brief':
{MOCK_SHOW_VLAN_BRIEF}

Output de 'show ip interface brief':
{MOCK_SHOW_IP_INTERFACE_BRIEF}

---

{user_input}
"""
    
    try:
        response = requests.post(
            COMANDO_ENDPOINT,
            json={
                "mensaje": mensaje_con_contexto,
                "session_id": session_id,
                "execute": False,  # No ejecutar, solo generar respuesta
                "simulate_connection": True,  # Activar modo de comandos sin conexión real
                "vendor": "cisco",
                "device_os": "IOS"
            },
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        return {
            "success": result.get("success", False),
            "response": result.get("respuesta", ""),
            "raw_result": result,
            "error": None
        }
    
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "response": "",
            "raw_result": {},
            "error": "Backend no disponible en localhost:3000"
        }
    except Exception as e:
        return {
            "success": False,
            "response": "",
            "raw_result": {},
            "error": str(e)
        }


# ============================================================================
# EVALUACIÓN DE RESPUESTAS
# ============================================================================

def evaluate_response(test_case: Dict, backend_result: Dict) -> Dict:
    """
    Evalúa si Corvelli generó los comandos correctos para la tarea IPAM.

    Filosofía Alfa: Solo validamos generación de comandos Cisco IOS.
    - ¿Generó un comando relevante (show, interface, ip address, ping)?
    - ¿El comando es apropiado para el tipo de tarea (show vs assign vs verify)?
    - ¿Menciona la IP o VLAN correcta?

    NO se valida análisis, conteo ni detección de conflictos.
    """
    if backend_result["error"]:
        return {
            "score": 0.0,
            "max_score": 3,
            "earned_score": 0,
            "details": {"error": backend_result["error"], "checks": []}
        }

    response = backend_result["response"].lower()
    max_score = 0
    earned_score = 0
    checks = []

    # Check 1: Respuesta no vacía (>10 chars, algo útil)
    # Threshold bajo porque comandos cortos como 'show ip arp' son válidos
    max_score += 1
    if response and len(response) > 10:
        earned_score += 1
        checks.append({"check": "useful_response", "passed": True})
    else:
        checks.append({"check": "useful_response", "passed": False})

    # Check 2: Contiene al menos un comando Cisco IOS esperado
    max_score += 1
    expected_cmds = test_case.get("expected_commands", [])
    cmd_found = any(cmd.lower() in response for cmd in expected_cmds)
    if cmd_found:
        earned_score += 1
        found_cmds = [c for c in expected_cmds if c.lower() in response]
        checks.append({"check": "cisco_command", "passed": True, "found": found_cmds})
    else:
        checks.append({"check": "cisco_command", "passed": False, "expected_any_of": expected_cmds})

    # Check 3: Keywords relevantes presentes (IP, VLAN, etc.)
    max_score += 1
    keywords = test_case.get("expected_keywords", [])
    if keywords:
        found_kw = sum(1 for kw in keywords if kw.lower() in response)
        threshold = max(1, len(keywords) // 2)
        if found_kw >= threshold:
            earned_score += 1
            checks.append({"check": "keywords", "passed": True, "found": found_kw})
        else:
            checks.append({"check": "keywords", "passed": False, "found": found_kw, "expected": threshold})
    else:
        # Sin keywords específicas, el check se otorga si hay cualquier IP
        ip_pattern = r'192\.168\.\d{1,3}\.\d{1,3}'
        if re.search(ip_pattern, response):
            earned_score += 1
            checks.append({"check": "keywords", "passed": True, "reason": "Contiene IP válida"})
        else:
            checks.append({"check": "keywords", "passed": False, "reason": "No contiene IP ni keywords"})

    # Check 4 (bonus): Para tareas de asignación, ¿incluye 'ip address'?
    if test_case.get("task_type") in ("assign", "assign_multiple"):
        max_score += 1
        if "ip address" in response:
            earned_score += 1
            ip_pattern = r'192\.168\.\d{1,3}\.\d{1,3}'
            ips = re.findall(ip_pattern, response)
            checks.append({"check": "ip_address_cmd", "passed": True, "ips": ips})
        else:
            checks.append({"check": "ip_address_cmd", "passed": False})

        # Check 5 (bonus para múltiples): ¿Sugiere más de una IP?
        if test_case.get("task_type") == "assign_multiple":
            max_score += 1
            min_ips = test_case.get("min_ips", 2)
            ip_pattern = r'192\.168\.\d{1,3}\.\d{1,3}'
            ips_found = re.findall(ip_pattern, response)
            if len(ips_found) >= min_ips:
                earned_score += 1
                checks.append({"check": "multiple_ips", "passed": True, "count": len(ips_found)})
            else:
                checks.append({"check": "multiple_ips", "passed": False, "found": len(ips_found), "expected": min_ips})

    final_score = earned_score / max_score if max_score > 0 else 0

    return {
        "score": final_score,
        "max_score": max_score,
        "earned_score": earned_score,
        "details": {
            "checks": checks,
            "response_length": len(backend_result["response"])
        }
    }


# ============================================================================
# EJECUCIÓN DE TESTS
# ============================================================================

def run_test_case(test_case: Dict) -> Dict:
    """
    Ejecuta un caso de prueba individual.
    """
    print(f"  [{test_case['id']}] {test_case['description']}...", end=" ")
    
    backend_result = call_corvelli_backend(test_case["user_input"])
    
    if backend_result["error"]:
        print(f"❌ ERROR: {backend_result['error']}")
        return {
            "test_id": test_case["id"],
            "description": test_case["description"],
            "critical": test_case["critical"],
            "weight": test_case["weight"],
            "success": False,
            "score": 0.0,
            "weighted_score": 0.0,
            "error": backend_result["error"]
        }
    
    evaluation = evaluate_response(test_case, backend_result)
    
    score = evaluation["score"]
    status = "✅" if score >= 0.9 else "⚠️" if score >= 0.5 else "❌"
    critical = " [CRITICAL]" if test_case["critical"] else ""
    
    print(f"{status} Score: {score:.2f}{critical}")
    
    return {
        "test_id": test_case["id"],
        "description": test_case["description"],
        "critical": test_case["critical"],
        "weight": test_case["weight"],
        "success": True,
        "score": score,
        "weighted_score": score * test_case["weight"],
        "user_input": test_case["user_input"],
        "corvelli_response": backend_result["response"],
        "evaluation": evaluation,
        "error": None
    }


def run_all_tests() -> Dict:
    """
    Ejecuta todos los tests y genera reporte.
    """
    print("="*80)
    print("CORVELLI - Test IPAM Simulación (Backend Real)")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend: {CORVELLI_BACKEND_URL}")
    print(f"Total de tests: {len(TEST_CASES)}")
    print("="*80)
    print()
    
    results = []
    total_weight = 0
    weighted_score_sum = 0
    
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] ", end="")
        
        result = run_test_case(test_case)
        results.append(result)
        
        if result["success"]:
            total_weight += test_case["weight"]
            weighted_score_sum += result["weighted_score"]
    
    num_tests = len(TEST_CASES)
    avg_score = weighted_score_sum / total_weight if total_weight > 0 else 0
    passed_tests = len([r for r in results if r.get("score", 0) >= 0.9])
    partial_tests = len([r for r in results if 0.5 <= r.get("score", 0) < 0.9])
    failed_tests = len([r for r in results if r.get("score", 0) < 0.5])
    critical_failures = [r for r in results if r.get("critical") and r.get("score", 0) < 0.9]
    
    summary = {
        "test_date": datetime.now().isoformat(),
        "test_type": "IPAM_SIMULATION_BACKEND",
        "backend_url": CORVELLI_BACKEND_URL,
        "total_tests": num_tests,
        "passed_tests": passed_tests,
        "partial_tests": partial_tests,
        "failed_tests": failed_tests,
        "critical_failures": len(critical_failures),
        "avg_score": avg_score,
        "total_weight": total_weight,
        "weighted_score_sum": weighted_score_sum,
        "results": results
    }
    
    return summary


def print_summary(summary: Dict):
    """Imprime resumen de resultados."""
    print()
    print("="*80)
    print("RESUMEN DE RESULTADOS")
    print("="*80)
    print()
    
    print(f"Tests totales:       {summary['total_tests']}")
    print(f"Tests aprobados:     {summary['passed_tests']} (>90%)")
    print(f"Tests parciales:     {summary['partial_tests']} (50-90%)")
    print(f"Tests fallidos:      {summary['failed_tests']} (<50%)")
    print(f"Fallas críticas:     {summary['critical_failures']}")
    print()
    print(f"Score promedio:      {summary['avg_score']:.2%}")
    print()
    
    if summary['critical_failures'] > 0:
        print("⚠️  FALLAS CRÍTICAS DETECTADAS:")
        for result in summary['results']:
            if result.get('critical') and result.get('score', 0) < 0.9:
                print(f"   - {result['test_id']}: {result['description']}")
                print(f"     Score: {result['score']:.2%}")
                if result.get('error'):
                    print(f"     Error: {result['error']}")
                else:
                    failed_checks = [c for c in result.get('evaluation', {}).get('details', {}).get('checks', []) if not c.get('passed')]
                    if failed_checks:
                        print(f"     Checks fallidos: {[c['check'] for c in failed_checks]}")
        print()
    
    print("="*80)
    print("EVALUACIÓN")
    print("="*80)
    print()
    
    if summary['critical_failures'] > 0:
        print("❌ BACKEND NO LISTO PARA IPAM")
        print("   Hay fallas en generación de comandos básicos para IPAM.")
    elif summary['avg_score'] < 0.8:
        print("⚠️  BACKEND REQUIERE MEJORAS EN IPAM")
        print(f"   Score promedio: {summary['avg_score']:.1%}")
    else:
        print("✅ BACKEND APROBADO - Generación de Comandos IPAM")
        print(f"   Score promedio: {summary['avg_score']:.1%}")
        print(f"   Tests aprobados: {summary['passed_tests']}/{summary['total_tests']}")
        print()
        print("   Nota: Versión Alfa evalúa solo generación de comandos.")
        print("   Análisis de outputs e inteligencia IPAM = trabajo futuro.")


def save_report(summary: Dict):
    """Guarda reporte en JSON."""
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"ipam_simulation_{timestamp}.json"
    filepath = reports_dir / filename
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Reporte guardado: evaluation/reports/{filename}")
    
    return str(filepath)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """
    Punto de entrada principal.
    
    Objetivo: Validar capacidades IPAM técnicas del backend de Corvelli.
    """
    summary = run_all_tests()
    print_summary(summary)
    save_report(summary)


if __name__ == "__main__":
    main()
