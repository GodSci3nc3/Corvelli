#!/usr/bin/env python3
"""
Test IPAM - Escenarios Reales, Generación de Comandos (Versión Alfa)
Valida que Corvelli responda con comandos útiles ante solicitudes IPAM vagas.

Filosofía Alfa: El usuario describe una intención en lenguaje natural.
Corvelli debe responder con comandos Cisco IOS relevantes.

- "Asigna IP a PC-Ventas-05" → genera interface vlan 10 + ip address
- "Dame 3 IPs para APs de IT" → genera múltiples ip address en VLAN 20
- "¿Está bien 192.168.10.25?" → genera show ip arp para verificar

NO se espera que Corvelli analice, cuente ni detecte conflictos por sí solo.
ESO es trabajo futuro (post-alfa).
"""

import re
import json
import requests
from typing import Dict, List
from datetime import datetime
from pathlib import Path



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
# TEST CASES - Escenarios Reales Vagos
# ============================================================================

REAL_SCENARIOS = [
    {
        "id": "vague_assign_by_name",
        "user_input": "Asigna IP a PC-Ventas-05",
        "description": "Solicitud vaga: nombre con pista de VLAN → genera ip address en VLAN 10",
        "weight": 3.0,
        "critical": True,
        "keywords_expected": ["192.168", "interface", "ip address"],
        "should_suggest_ip": True,
        "task_type": "assign"
    },
    {
        "id": "vague_multiple_ips",
        "user_input": "Dame 3 IPs para APs del departamento de IT",
        "description": "Solicitud múltiple → genera ip address en VLAN 20 (al menos 1)",
        "weight": 3.5,
        "critical": False,  # No crítico en alfa: el modelo puede dar 1 o más IPs
        "keywords_expected": ["192.168", "interface", "ip address"],
        "should_suggest_multiple": True,
        "min_ips_expected": 1,  # En alfa: con 1 IP ya es válido
        "task_type": "assign_multiple"
    },
    {
        "id": "vague_question_only",
        "user_input": "Qué IP le pongo a la impresora de contabilidad?",
        "description": "Pregunta abierta → genera ip address en cualquier VLAN válida",
        "weight": 2.5,
        "critical": False,
        "keywords_expected": ["192.168", "ip address"],
        "should_suggest_ip": True,
        "task_type": "assign"
    },
    {
        "id": "vague_conflict_check",
        "user_input": "Este host tiene 192.168.10.25, está bien o hay conflicto?",
        "description": "Verificación de IP → genera show ip arp, ping, o comando de config",
        "weight": 2.0,
        "critical": True,
        # En alfa: Corvelli puede responder con show ip arp O con comandos de config.
        # Ambas son respuestas validas para 'esta bien esta IP?'
        "keywords_expected": ["192.168.10.25"],
        "should_suggest_ip": False,
        "task_type": "verify"
    },
    {
        "id": "vague_guest_wifi",
        "user_input": "Cuántas IPs me quedan libres para WiFi de invitados?",
        "description": "Consulta de disponibilidad → genera show, interface, o respuesta útil",
        "weight": 2.0,
        "critical": False,
        # En alfa: aceptamos show ip arp, show vlan, interface vlan, o respuesta en lenguaje natural
        "keywords_expected": ["vlan", "192.168"],
        "should_suggest_ip": False,
        "task_type": "show"
    },
    {
        "id": "vague_emergency_assign",
        "user_input": "Urgente: necesito IP para servidor temporal",
        "description": "Solicitud urgente → genera ip address en cualquier subnet disponible",
        "weight": 3.0,
        "critical": True,
        "keywords_expected": ["192.168", "ip address", "interface"],
        "should_suggest_ip": True,
        "task_type": "assign"
    },
    {
        "id": "vague_range_question",
        "user_input": "Puedo usar el rango 192.168.10.100-110 sin problemas?",
        "description": "Consulta de rango → genera comandos para verificar o usar el rango",
        "weight": 2.5,
        "critical": False,
        # En alfa: aceptamos show ip arp O comandos de configuracion para el rango
        "keywords_expected": ["192.168.10"],
        "should_suggest_ip": False,
        "task_type": "verify"
    }
]


# ============================================================================
# FUNCIONES DE LLAMADA AL BACKEND CORVELLI
# ============================================================================

def call_corvelli_backend(user_input: str, session_id: str = None) -> Dict:
    """
    Llama al backend de Corvelli en localhost:3000/comando.
    
    Objetivo: Usar el sistema de prompts REAL de Corvelli, no inventar uno nuevo.
    Crítico: Validar que el backend actual pueda manejar requests IPAM vagos.
    """
    if not session_id:
        # Generar session_id único para este test con microsegundos
        session_id = f"ipam-test-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    
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
            "error": "No se pudo conectar al backend. ¿Está corriendo en localhost:3000?"
        }
    except Exception as e:
        return {
            "success": False,
            "response": "",
            "raw_result": {},
            "error": str(e)
        }


# ============================================================================
# EVALUACIÓN DE RESPUESTAS DEL BACKEND
# ============================================================================

def evaluate_corvelli_response(test_case: Dict, backend_result: Dict) -> Dict:
    """
    Evalúa si Corvelli generó comandos Cisco IOS útiles para la solicitud IPAM.

    Filosofía Alfa: Validamos generación de comandos, no análisis.
    - ¿Respuesta no vacía?
    - ¿Contiene comandos Cisco IOS relevantes?
    - ¿Incluye IP/VLAN correcta según el contexto?
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

    # Check 1: Respuesta no vacía y útil (>10 chars)
    # Threshold bajo porque comandos cortos son válidos en alfa
    max_score += 1
    if response and len(response) > 10:
        earned_score += 1
        checks.append({"check": "useful_response", "passed": True})
    else:
        checks.append({"check": "useful_response", "passed": False, "reason": "Respuesta muy corta o vacía"})

    # Check 2: Keywords esperados (comandos o IPs relevantes)
    max_score += 1
    keywords_found = sum(1 for kw in test_case.get("keywords_expected", []) if kw.lower() in response)
    threshold = max(1, len(test_case.get("keywords_expected", [])) // 2)
    if keywords_found >= threshold:
        earned_score += 1
        checks.append({"check": "keywords", "passed": True, "found": keywords_found})
    else:
        checks.append({"check": "keywords", "passed": False, "found": keywords_found, "expected": threshold})

    # Check 3: ¿Sugiere IP válida cuando debe?
    if test_case.get("should_suggest_ip"):
        max_score += 1
        ip_pattern = r'192\.168\.\d{1,3}\.\d{1,3}'
        ips_found = re.findall(ip_pattern, response)
        if ips_found:
            earned_score += 1
            checks.append({"check": "suggest_ip", "passed": True, "ips": ips_found})
        else:
            checks.append({"check": "suggest_ip", "passed": False, "reason": "No sugirió IP"})

    # Check 4: ¿Sugiere múltiples IPs cuando debe?
    if test_case.get("should_suggest_multiple"):
        max_score += 1
        ip_pattern = r'192\.168\.\d{1,3}\.\d{1,3}'
        ips_found = re.findall(ip_pattern, response)
        min_expected = test_case.get("min_ips_expected", 2)
        if len(ips_found) >= min_expected:
            earned_score += 1
            checks.append({"check": "suggest_multiple", "passed": True, "ips": ips_found})
        else:
            checks.append({"check": "suggest_multiple", "passed": False, "found": len(ips_found), "expected": min_expected})

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

def run_real_scenario(test_case: Dict) -> Dict:
    """
    Ejecuta un escenario real completo: backend → evaluación.
    """
    print(f"  [{test_case['id']}] {test_case['description']}...", end=" ")
    
    # Llamar al backend de Corvelli
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
    
    # Evaluar respuesta
    evaluation = evaluate_corvelli_response(test_case, backend_result)
    
    # Status
    score = evaluation["score"]
    status = "✅" if score >= 0.8 else "⚠️" if score >= 0.5 else "❌"
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


def run_all_real_scenarios() -> Dict:
    """
    Ejecuta todos los escenarios reales y genera reporte.
    """
    print("="*80)
    print("CORVELLI - Test IPAM Escenarios Reales (Backend Real)")
    print("="*80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend: {CORVELLI_BACKEND_URL}")
    print(f"Total de escenarios: {len(REAL_SCENARIOS)}")
    print("="*80)
    print()
    
    results = []
    total_weight = 0
    weighted_score_sum = 0
    
    for i, test_case in enumerate(REAL_SCENARIOS, 1):
        print(f"[{i}/{len(REAL_SCENARIOS)}] ", end="")
        
        result = run_real_scenario(test_case)
        results.append(result)
        
        if result["success"]:
            total_weight += test_case["weight"]
            weighted_score_sum += result["weighted_score"]
    
    # Métricas agregadas
    num_tests = len(REAL_SCENARIOS)
    avg_score = weighted_score_sum / total_weight if total_weight > 0 else 0
    passed_tests = len([r for r in results if r.get("score", 0) >= 0.8])
    partial_tests = len([r for r in results if 0.5 <= r.get("score", 0) < 0.8])
    failed_tests = len([r for r in results if r.get("score", 0) < 0.5])
    critical_failures = [r for r in results if r.get("critical") and r.get("score", 0) < 0.8]
    
    summary = {
        "test_date": datetime.now().isoformat(),
        "test_type": "IPAM_REAL_SCENARIOS_BACKEND",
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
    print(f"Tests aprobados:     {summary['passed_tests']} (>80%)")
    print(f"Tests parciales:     {summary['partial_tests']} (50-80%)")
    print(f"Tests fallidos:      {summary['failed_tests']} (<50%)")
    print(f"Fallas críticas:     {summary['critical_failures']}")
    print()
    print(f"Score promedio:      {summary['avg_score']:.2%}")
    print()
    
    # Fallas críticas
    if summary['critical_failures'] > 0:
        print("⚠️  FALLAS CRÍTICAS DETECTADAS:")
        for result in summary['results']:
            if result.get('critical') and result.get('score', 0) < 0.8:
                print(f"   - {result['test_id']}: {result['description']}")
                print(f"     Score: {result['score']:.2%}")
                if result.get('error'):
                    print(f"     Error: {result['error']}")
                else:
                    # Mostrar checks fallidos
                    failed_checks = [c for c in result.get('evaluation', {}).get('details', {}).get('checks', []) if not c.get('passed')]
                    if failed_checks:
                        print(f"     Checks fallidos: {[c['check'] for c in failed_checks]}")
        print()
    
    # Evaluación
    print("="*80)
    print("EVALUACIÓN")
    print("="*80)
    print()
    
    if summary['critical_failures'] > 0:
        print("❌ BACKEND NO LISTO PARA IPAM")
        print("   El backend no genera comandos útiles ante solicitudes IPAM vagas.")
    elif summary['avg_score'] < 0.7:
        print("⚠️  BACKEND REQUIERE MEJORAS")
        print(f"   Score promedio bajo ({summary['avg_score']:.1%}).")
        print("   Considerar ajustar prompts para entender mejor IPAM.")
    else:
        print("✅ BACKEND APROBADO - Generación de Comandos IPAM (Escenarios Vagos)")
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
    filename = f"ipam_real_scenarios_{timestamp}.json"
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
    
    Objetivo: Validar que el backend de Corvelli maneje escenarios IPAM reales vagos.
    """
    summary = run_all_real_scenarios()
    print_summary(summary)
    save_report(summary)


if __name__ == "__main__":
    main()
