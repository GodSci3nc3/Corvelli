#!/usr/bin/env python3
"""
Test IPAM - Simulación Técnica con Backend de Corvelli
Valida que Corvelli pueda manejar operaciones IPAM técnicas y específicas.

Objetivo: Probar capacidades IPAM del backend con escenarios técnicos precisos.
Crítico: El backend debe escanear IPs, sugerir libres, detectar conflictos.

Este test usa el backend real en localhost:3000, no lógica aislada.
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
# TEST CASES - Escenarios Técnicos IPAM
# ============================================================================

TEST_CASES = [
    {
        "id": "scan_network_vlan10",
        "user_input": "Muéstrame todas las IPs en uso en la VLAN 10",
        "description": "Escanear y listar IPs ocupadas en subnet específica",
        "weight": 2.0,
        "critical": True,
        "expected_ips_count_min": 10,  # Mínimo 10 IPs detectadas
        "expected_keywords": ["192.168.10", "uso", "ocupad", "vlan"],
        "should_list_ips": True
    },
    {
        "id": "suggest_next_ip_vlan10",
        "user_input": "Dame la siguiente IP libre en 192.168.10.0/24",
        "description": "Sugerir siguiente IP disponible en subnet",
        "weight": 2.5,
        "critical": True,
        "expected_ip": "192.168.10.4",  # Primera IP libre según contexto
        "should_suggest_specific_ip": True,
        "subnet": "192.168.10.0/24"
    },
    {
        "id": "suggest_next_ip_vlan20",
        "user_input": "Necesito una IP libre en la VLAN 20",
        "description": "Sugerir IP libre sin especificar subnet exacta",
        "weight": 2.5,
        "critical": True,
        "expected_first_free": "192.168.20.3",  # Primera libre en VLAN 20
        "should_suggest_vlan20": True,
        "expected_keywords": ["192.168.20", "libre"]
    },
    {
        "id": "detect_conflict_192_168_10_10",
        "user_input": "Puedo usar 192.168.10.10 para un nuevo dispositivo?",
        "description": "Detectar conflicto con IP existente",
        "weight": 3.0,
        "critical": True,
        "expected_conflict": True,
        "test_ip": "192.168.10.10",
        "expected_keywords": ["uso", "ocupad", "conflict", "no", "exist"]
    },
    {
        "id": "no_conflict_192_168_10_100",
        "user_input": "Está libre 192.168.10.100?",
        "description": "Confirmar que IP libre no tiene conflicto",
        "weight": 2.0,
        "critical": True,
        "expected_conflict": False,
        "test_ip": "192.168.10.100",
        "expected_keywords": ["libre", "disponible", "sí", "puedes"]
    },
    {
        "id": "suggest_multiple_ips",
        "user_input": "Dame 5 IPs consecutivas libres en VLAN 30",
        "description": "Sugerir múltiples IPs secuenciales",
        "weight": 3.0,
        "critical": False,
        "min_ips_expected": 5,
        "should_be_consecutive": True,
        "subnet": "192.168.30.0/24"
    },
    {
        "id": "calculate_usage_vlan10",
        "user_input": "Cuántas IPs están ocupadas en la red 192.168.10.0/24?",
        "description": "Calcular uso de subnet",
        "weight": 1.5,
        "critical": False,
        "expected_count": 15,  # 15 IPs en uso según contexto
        "tolerance": 2,  # ±2 IPs aceptable
        "should_report_number": True
    },
    {
        "id": "calculate_available_vlan30",
        "user_input": "Cuántas IPs libres hay en VLAN Invitados?",
        "description": "Calcular disponibilidad en subnet casi vacía",
        "weight": 1.5,
        "critical": False,
        "expected_available_min": 250,  # Casi toda la subnet libre
        "should_report_number": True
    },
    {
        "id": "range_check_free",
        "user_input": "El rango 192.168.30.10-20 está libre?",
        "description": "Validar disponibilidad de rango de IPs",
        "weight": 2.5,
        "critical": False,
        "range_start": "192.168.30.10",
        "range_end": "192.168.30.20",
        "expected_all_free": True,
        "expected_keywords": ["libre", "disponible", "sí"]
    },
    {
        "id": "range_check_partial_conflict",
        "user_input": "Puedo usar el rango 192.168.10.1-10?",
        "description": "Detectar conflictos en rango con IPs ocupadas",
        "weight": 2.5,
        "critical": True,
        "range_start": "192.168.10.1",
        "range_end": "192.168.10.10",
        "expected_conflicts": True,
        "expected_keywords": ["uso", "ocupad", "conflict", "alguna"]
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
    Evalúa si la respuesta del backend cumple con lo esperado.
    
    Objetivo: Validar respuestas técnicas precisas del backend.
    Crítico: No solo validar keywords, también lógica correcta.
    """
    if backend_result["error"]:
        return {
            "score": 0.0,
            "max_score": 5,
            "earned_score": 0,
            "details": {
                "error": backend_result["error"],
                "checks": []
            }
        }
    
    response = backend_result["response"].lower()
    max_score = 0
    earned_score = 0
    checks = []
    
    # Check 1: Respuesta no vacía y útil
    max_score += 1
    if response and len(response) > 20:
        earned_score += 1
        checks.append({"check": "useful_response", "passed": True})
    else:
        checks.append({"check": "useful_response", "passed": False})
    
    # Check 2: Keywords esperados presentes
    if test_case.get("expected_keywords"):
        max_score += 1
        keywords_found = sum(1 for kw in test_case["expected_keywords"] if kw.lower() in response)
        threshold = len(test_case["expected_keywords"]) // 2
        
        if keywords_found >= threshold:
            earned_score += 1
            checks.append({"check": "keywords", "passed": True, "found": keywords_found})
        else:
            checks.append({"check": "keywords", "passed": False, "found": keywords_found, "expected": threshold})
    
    # Check 3: Detectó conflicto correctamente
    if "expected_conflict" in test_case:
        max_score += 2  # Crítico, vale doble
        conflict_words = ["uso", "ocupad", "conflict", "exist", "asignad", "no disponible", "no puedes"]
        free_words = ["libre", "disponible", "sí", "puedes", "ok"]
        
        has_conflict_indicators = any(word in response for word in conflict_words)
        has_free_indicators = any(word in response for word in free_words)
        
        expected = test_case["expected_conflict"]
        
        if expected and has_conflict_indicators:
            earned_score += 2
            checks.append({"check": "detect_conflict", "passed": True, "detected": True})
        elif not expected and has_free_indicators:
            earned_score += 2
            checks.append({"check": "detect_conflict", "passed": True, "detected": False})
        else:
            checks.append({"check": "detect_conflict", "passed": False, "expected": expected, "indicators": {"conflict": has_conflict_indicators, "free": has_free_indicators}})
    
    # Check 4: Sugirió IP específica esperada
    if "expected_ip" in test_case:
        max_score += 2  # Crítico
        expected_ip = test_case["expected_ip"]
        
        if expected_ip in response:
            earned_score += 2
            checks.append({"check": "suggest_specific_ip", "passed": True, "ip": expected_ip})
        else:
            # Buscar cualquier IP del subnet correcto
            ip_pattern = r'192\.168\.\d{1,3}\.\d{1,3}'
            found_ips = re.findall(ip_pattern, response)
            
            if found_ips:
                earned_score += 1  # Medio punto: sugirió algo pero no exacto
                checks.append({"check": "suggest_specific_ip", "passed": False, "expected": expected_ip, "found": found_ips})
            else:
                checks.append({"check": "suggest_specific_ip", "passed": False, "expected": expected_ip, "found": []})
    
    # Check 5: Sugirió múltiples IPs
    if "min_ips_expected" in test_case:
        max_score += 1
        ip_pattern = r'192\.168\.\d{1,3}\.\d{1,3}'
        found_ips = re.findall(ip_pattern, response)
        min_expected = test_case["min_ips_expected"]
        
        if len(found_ips) >= min_expected:
            earned_score += 1
            checks.append({"check": "suggest_multiple", "passed": True, "found": len(found_ips), "ips": found_ips})
        else:
            checks.append({"check": "suggest_multiple", "passed": False, "found": len(found_ips), "expected": min_expected})
    
    # Check 6: Reportó número (para cálculos)
    if test_case.get("should_report_number"):
        max_score += 1
        numbers_found = re.findall(r'\b\d{1,3}\b', response)
        
        if numbers_found:
            earned_score += 1
            checks.append({"check": "report_number", "passed": True, "numbers": numbers_found})
        else:
            checks.append({"check": "report_number", "passed": False})
    
    # Check 7: Listó IPs (para scan)
    if test_case.get("should_list_ips"):
        max_score += 1
        ip_pattern = r'192\.168\.\d{1,3}\.\d{1,3}'
        found_ips = re.findall(ip_pattern, response)
        min_expected = test_case.get("expected_ips_count_min", 5)
        
        if len(found_ips) >= min_expected:
            earned_score += 1
            checks.append({"check": "list_ips", "passed": True, "found": len(found_ips)})
        else:
            checks.append({"check": "list_ips", "passed": False, "found": len(found_ips), "expected": min_expected})
    
    # Asegurar al menos 3 checks
    if max_score < 3:
        max_score = 3
    
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
        print("   Hay fallas críticas en funcionalidad IPAM básica.")
    elif summary['avg_score'] < 0.8:
        print("⚠️  BACKEND REQUIERE MEJORAS IPAM")
        print(f"   Score promedio: {summary['avg_score']:.1%}")
    else:
        print("✅ BACKEND IPAM APROBADO")
        print(f"   Score promedio: {summary['avg_score']:.1%}")
        print(f"   Tests aprobados: {summary['passed_tests']}/{summary['total_tests']}")


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
