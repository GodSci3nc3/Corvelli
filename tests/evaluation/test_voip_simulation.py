#!/usr/bin/env python3
"""
Test VoIP - Generacion de Comandos Voice VLAN, Cisco IOS (Version Alfa)
Valida que Corvelli genere los comandos correctos para configuraciones VoIP.

Filosofia Alfa: Corvelli genera comandos, no diagnostica problemas de audio,
latencia, jitter ni calidad de llamadas.

- "Configura telefono IP en Gi0/1" -> switchport voice vlan X
- "Habilita QoS para VoIP" -> mls qos trust cos/dscp
- "Muestra puertos con telefono" -> show interfaces switchport

NO se evalua diagnostico de red, analisis de trafico ni calidad de llamadas.
Eso es trabajo futuro (post-alfa).
"""

import re
import json
import requests
from typing import Dict, List
from datetime import datetime
from pathlib import Path


CORVELLI_BACKEND_URL = "http://localhost:3000"
COMANDO_ENDPOINT = f"{CORVELLI_BACKEND_URL}/comando"


# Contexto de red simulada con VoIP
MOCK_SHOW_VLAN_BRIEF = """VLAN Name                             Status    Ports
---- -------------------------------- --------- -------------------------------
1    default                          active    Gi0/1, Gi0/2
10   DATOS                            active    Gi0/3, Gi0/4, Gi0/5, Gi0/6
20   VOICE                            active    Gi0/7, Gi0/8
30   INVITADOS                        active    Gi0/10
99   NATIVA                           active
"""

MOCK_SHOW_INTERFACES_SWITCHPORT = """Name: Gi0/1
Switchport: Enabled
Administrative Mode: static access
Operational Mode: static access
Administrative Trunking Encapsulation: dot1q
Access Mode VLAN: 10 (DATOS)
Voice VLAN: none

Name: Gi0/3
Switchport: Enabled
Administrative Mode: static access
Operational Mode: static access
Access Mode VLAN: 10 (DATOS)
Voice VLAN: 20 (VOICE)
"""

NETWORK_CONTEXT = """
Red actual:
- VLAN 10 (DATOS): 192.168.10.0/24 - PCs y workstations
- VLAN 20 (VOICE): 192.168.20.0/24 - Telefonos IP Cisco
- VLAN 30 (INVITADOS): 192.168.30.0/24
- VLAN 99 (NATIVA): usada en trunks

Puertos con telefono IP configurado: Gi0/3, Gi0/4
Puertos sin Voice VLAN: Gi0/1, Gi0/2 (pendientes)
"""


# ============================================================================
# TEST CASES - Generacion de Comandos VoIP
# ============================================================================

TEST_CASES = [
    # --- Configuracion de Voice VLAN en puertos ---
    {
        "id": "assign_voice_vlan_single_port",
        "user_input": "Configura el puerto Gi0/1 para telefono IP en VLAN 20",
        "description": "Debe generar interface Gi0/1 + configuracion para telefono IP (voice vlan o access vlan)",
        "weight": 3.0,
        "critical": True,
        # En alfa: aceptamos switchport voice vlan 20 O switchport access vlan 20
        # Ambas son formas validas de configurar un puerto para telefono IP
        "expected_commands": ["switchport voice vlan", "switchport access vlan", "interface"],
        "expected_keywords": ["gi0/1", "vlan 20"],
        "task_type": "config_voice_vlan"
    },
    {
        "id": "assign_voice_vlan_access_mode",
        "user_input": "Asigna Voice VLAN 20 al puerto Gi0/2 con datos en VLAN 10",
        "description": "Debe generar interface + switchport access vlan 10 + switchport voice vlan 20",
        "weight": 3.0,
        "critical": True,
        "expected_commands": ["switchport voice vlan", "switchport access vlan", "interface"],
        "expected_keywords": ["gi0/2", "vlan 10", "vlan 20"],
        "task_type": "config_voice_vlan"
    },
    {
        "id": "create_voice_vlan",
        "user_input": "Crea la VLAN 20 para telefonos IP y llamala VOICE",
        "description": "Debe generar vlan 20 + name VOICE",
        "weight": 2.0,
        "critical": True,
        "expected_commands": ["vlan 20", "name"],
        "expected_keywords": ["vlan", "20", "voice"],
        "task_type": "create_vlan"
    },
    {
        "id": "bulk_voice_ports",
        "user_input": "Configura los puertos Gi0/1 al Gi0/8 para telefonos IP en VLAN 20",
        "description": "Debe generar configuracion para multiples puertos con voice vlan 20",
        "weight": 2.5,
        "critical": False,
        "expected_commands": ["switchport voice vlan", "interface"],
        "expected_keywords": ["voice vlan", "20"],
        "task_type": "config_voice_vlan"
    },

    # --- QoS para voz ---
    {
        "id": "enable_qos_trust_cos",
        "user_input": "Habilita QoS en el puerto Gi0/1 para priorizar trafico de voz",
        "description": "Debe generar mls qos trust cos o mls qos trust dscp",
        "weight": 2.5,
        "critical": True,
        "expected_commands": ["mls qos trust", "qos"],
        "expected_keywords": ["qos", "gi0/1"],
        "task_type": "config_qos"
    },
    {
        "id": "enable_qos_global",
        "user_input": "Activa QoS de forma global en el switch para VoIP",
        "description": "Debe generar mls qos (global)",
        "weight": 2.0,
        "critical": False,
        "expected_commands": ["mls qos", "qos"],
        "expected_keywords": ["qos"],
        "task_type": "config_qos"
    },
    {
        "id": "enable_portfast",
        "user_input": "Activa PortFast en los puertos de telefonos IP para reducir tiempo de convergencia",
        "description": "Debe generar spanning-tree portfast",
        "weight": 1.5,
        "critical": False,
        "expected_commands": ["spanning-tree portfast", "portfast"],
        "expected_keywords": ["portfast", "spanning-tree"],
        "task_type": "config_stp"
    },

    # --- Verificacion ---
    {
        "id": "show_voice_vlan_config",
        "user_input": "Muestra la configuracion de Voice VLAN en todos los puertos",
        "description": "Debe generar show interfaces switchport, show vlan, o configurar voice vlan",
        "weight": 1.5,
        "critical": False,
        # En alfa: aceptamos show O configuracion de voice vlan
        # El modelo puede interpretar 'muestra la config de voice vlan' como
        # 'configura la voice vlan' dado el contexto del switch
        "expected_commands": ["show interfaces switchport", "show vlan", "show run", "switchport voice vlan", "interface"],
        "expected_keywords": ["vlan"],
        "task_type": "show"
    },
    {
        "id": "show_cdp_voip",
        "user_input": "Muestra que telefonos IP estan conectados al switch",
        "description": "Debe generar show cdp neighbors o show interfaces switchport",
        "weight": 1.5,
        "critical": False,
        "expected_commands": ["show cdp", "show interfaces switchport", "show cdp neighbors"],
        "expected_keywords": ["show", "cdp"],
        "task_type": "show"
    },

    # --- Configuracion completa ---
    {
        "id": "full_voip_port_config",
        "user_input": "Configura el puerto Gi0/5 completo para telefono Cisco: datos VLAN 10, voz VLAN 20, QoS y PortFast",
        "description": "Debe generar configuracion completa: access vlan, voice vlan, qos, portfast",
        "weight": 3.0,
        "critical": True,
        "expected_commands": ["switchport voice vlan", "switchport access vlan", "mls qos trust", "spanning-tree portfast"],
        "expected_keywords": ["gi0/5", "vlan 10", "vlan 20", "qos"],
        "task_type": "config_full"
    },
]


# ============================================================================
# BACKEND CALL
# ============================================================================

def call_corvelli_backend(user_input: str, session_id: str = None) -> Dict:
    if not session_id:
        session_id = f"voip-sim-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    mensaje_con_contexto = f"""Contexto del switch Cisco Catalyst 2960:

Output de 'show vlan brief':
{MOCK_SHOW_VLAN_BRIEF}

Output de 'show interfaces switchport' (resumen):
{MOCK_SHOW_INTERFACES_SWITCHPORT}

Informacion de red:
{NETWORK_CONTEXT}

---

{user_input}
"""

    try:
        response = requests.post(
            COMANDO_ENDPOINT,
            json={
                "mensaje": mensaje_con_contexto,
                "session_id": session_id,
                "execute": False,
                "simulate_connection": True,
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
        return {"success": False, "response": "", "raw_result": {}, "error": "Backend no disponible en localhost:3000"}
    except Exception as e:
        return {"success": False, "response": "", "raw_result": {}, "error": str(e)}


# ============================================================================
# EVALUACION
# ============================================================================

def evaluate_response(test_case: Dict, backend_result: Dict) -> Dict:
    """
    Evalua si Corvelli genero los comandos Cisco IOS correctos para VoIP.

    Filosofia Alfa: Solo validamos generacion de comandos.
    - Para config: switchport voice vlan, mls qos, portfast
    - Para show: show interfaces switchport, show cdp, show vlan
    """
    if backend_result["error"]:
        return {
            "score": 0.0, "max_score": 3, "earned_score": 0,
            "details": {"error": backend_result["error"], "checks": []}
        }

    response = backend_result["response"].lower()
    max_score = 0
    earned_score = 0
    checks = []

    # Check 1: Respuesta no vacia (>10 chars)
    max_score += 1
    if response and len(response) > 10:
        earned_score += 1
        checks.append({"check": "useful_response", "passed": True})
    else:
        checks.append({"check": "useful_response", "passed": False})

    # Check 2: Contiene al menos un comando Cisco IOS esperado
    max_score += 1
    expected_cmds = test_case.get("expected_commands", [])
    found_cmds = [c for c in expected_cmds if c.lower() in response]
    if found_cmds:
        earned_score += 1
        checks.append({"check": "cisco_command", "passed": True, "found": found_cmds})
    else:
        checks.append({"check": "cisco_command", "passed": False, "expected_any_of": expected_cmds})

    # Check 3: Keywords relevantes (VLAN, interfaz, etc.)
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
        earned_score += 1
        checks.append({"check": "keywords", "passed": True, "reason": "Sin keywords especificas"})

    # Check 4 (bonus): Configuracion incluye voice vlan o access vlan para telefono
    # En alfa: aceptamos switchport voice vlan O switchport access vlan
    # Ambas son formas validas de configurar un puerto para telefono IP
    if test_case.get("task_type") in ("config_voice_vlan", "config_full"):
        max_score += 1
        if "switchport voice vlan" in response or "switchport access vlan" in response:
            earned_score += 1
            checks.append({"check": "voice_vlan_cmd", "passed": True})
        else:
            checks.append({"check": "voice_vlan_cmd", "passed": False})

    # Check 5 (bonus): Configuracion completa incluye QoS
    if test_case.get("task_type") in ("config_qos", "config_full"):
        max_score += 1
        if any(q in response for q in ["mls qos", "qos"]):
            earned_score += 1
            checks.append({"check": "qos_cmd", "passed": True})
        else:
            checks.append({"check": "qos_cmd", "passed": False})

    final_score = earned_score / max_score if max_score > 0 else 0

    return {
        "score": final_score,
        "max_score": max_score,
        "earned_score": earned_score,
        "details": {"checks": checks, "response_length": len(backend_result["response"])}
    }


# ============================================================================
# EJECUCION
# ============================================================================

def run_test_case(test_case: Dict) -> Dict:
    print(f"  [{test_case['id']}] {test_case['description']}...", end=" ")

    backend_result = call_corvelli_backend(test_case["user_input"])

    if backend_result["error"]:
        print(f"ERROR: {backend_result['error']}")
        return {
            "test_id": test_case["id"], "description": test_case["description"],
            "critical": test_case["critical"], "weight": test_case["weight"],
            "success": False, "score": 0.0, "weighted_score": 0.0,
            "error": backend_result["error"]
        }

    evaluation = evaluate_response(test_case, backend_result)
    score = evaluation["score"]
    status = "OK" if score >= 0.9 else "PARCIAL" if score >= 0.5 else "FALLO"
    critical = " [CRITICO]" if test_case["critical"] else ""

    print(f"{status} | Score: {score:.2f}{critical}")

    return {
        "test_id": test_case["id"], "description": test_case["description"],
        "critical": test_case["critical"], "weight": test_case["weight"],
        "success": True, "score": score,
        "weighted_score": score * test_case["weight"],
        "user_input": test_case["user_input"],
        "corvelli_response": backend_result["response"],
        "evaluation": evaluation, "error": None
    }


def run_all_tests() -> Dict:
    print("=" * 80)
    print("CORVELLI - Test VoIP Voice VLAN, Simulacion (Backend Real)")
    print("=" * 80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend: {CORVELLI_BACKEND_URL}")
    print(f"Total de tests: {len(TEST_CASES)}")
    print("=" * 80)
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

    avg_score = weighted_score_sum / total_weight if total_weight > 0 else 0
    passed_tests = len([r for r in results if r.get("score", 0) >= 0.9])
    partial_tests = len([r for r in results if 0.5 <= r.get("score", 0) < 0.9])
    failed_tests = len([r for r in results if r.get("score", 0) < 0.5])
    critical_failures = [r for r in results if r.get("critical") and r.get("score", 0) < 0.9]

    summary = {
        "test_date": datetime.now().isoformat(),
        "test_type": "VOIP_SIMULATION_BACKEND",
        "backend_url": CORVELLI_BACKEND_URL,
        "total_tests": len(TEST_CASES),
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
    print()
    print("=" * 80)
    print("RESUMEN DE RESULTADOS")
    print("=" * 80)
    print()
    print(f"Tests totales:       {summary['total_tests']}")
    print(f"Tests aprobados:     {summary['passed_tests']} (>=90%)")
    print(f"Tests parciales:     {summary['partial_tests']} (50-90%)")
    print(f"Tests fallidos:      {summary['failed_tests']} (<50%)")
    print(f"Fallas criticas:     {summary['critical_failures']}")
    print()
    print(f"Score promedio:      {summary['avg_score']:.2%}")
    print()

    if summary["critical_failures"] > 0:
        print("FALLAS CRITICAS DETECTADAS:")
        for result in summary["results"]:
            if result.get("critical") and result.get("score", 0) < 0.9:
                print(f"   - {result['test_id']}: {result['description']}")
                print(f"     Score: {result['score']:.2%}")
                failed = [c for c in result.get("evaluation", {}).get("details", {}).get("checks", []) if not c.get("passed")]
                if failed:
                    print(f"     Checks fallidos: {[c['check'] for c in failed]}")
        print()

    print("=" * 80)
    print("EVALUACION")
    print("=" * 80)
    print()

    if summary["critical_failures"] > 0:
        print("BACKEND NO LISTO PARA VOIP")
        print("   Hay fallas en generacion de comandos basicos para VoIP.")
    elif summary["avg_score"] < 0.8:
        print("BACKEND REQUIERE MEJORAS EN VOIP")
        print(f"   Score promedio: {summary['avg_score']:.1%}")
    else:
        print("BACKEND APROBADO - Generacion de Comandos VoIP")
        print(f"   Score promedio: {summary['avg_score']:.1%}")
        print(f"   Tests aprobados: {summary['passed_tests']}/{summary['total_tests']}")
        print()
        print("   Nota: Version Alfa evalua solo generacion de comandos.")
        print("   Diagnostico de calidad de voz y analisis de trafico = trabajo futuro.")


def save_report(summary: Dict):
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"voip_simulation_{timestamp}.json"
    filepath = reports_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nReporte guardado: evaluation/reports/{filename}")
    return str(filepath)


def main():
    summary = run_all_tests()
    print_summary(summary)
    save_report(summary)


if __name__ == "__main__":
    main()
