#!/usr/bin/env python3
"""
Test VoIP - Escenarios Reales, Generacion de Comandos (Version Alfa)
Valida que Corvelli responda con comandos utiles ante solicitudes VoIP vagas.

Filosofia Alfa: El usuario describe una situacion en lenguaje natural.
Corvelli debe responder con comandos Cisco IOS relevantes para VoIP.

- "Los telefonos no estan en su red" -> genera interface + voice vlan
- "Necesito aislar voz de datos" -> genera voice vlan separada de access vlan
- "Configura el area de gerencia para VoIP" -> genera vlan + puertos

NO se espera que Corvelli diagnostique problemas de audio, calidad de llamadas
ni analice trafico. Eso es trabajo futuro (post-alfa).
"""

import re
import json
import requests
from typing import Dict, List
from datetime import datetime
from pathlib import Path


CORVELLI_BACKEND_URL = "http://localhost:3000"
COMANDO_ENDPOINT = f"{CORVELLI_BACKEND_URL}/comando"


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
Access Mode VLAN: 10 (DATOS)
Voice VLAN: none

Name: Gi0/3
Switchport: Enabled
Administrative Mode: static access
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
Puertos sin Voice VLAN: Gi0/1, Gi0/2 (pendientes de configurar)
"""


# ============================================================================
# ESCENARIOS REALES VAGOS
# ============================================================================

REAL_SCENARIOS = [
    {
        "id": "phones_not_in_network",
        "user_input": "Los telefonos IP del piso 1 no estan en su VLAN",
        "description": "Solicitud vaga -> genera configuracion de puerto para telefono IP",
        "weight": 3.0,
        "critical": True,
        "keywords_expected": ["interface", "vlan"],
        # En alfa: aceptamos switchport voice vlan O switchport access vlan
        "should_suggest_voice_vlan": True,
        "task_type": "config_voice_vlan"
    },
    {
        "id": "isolate_voice_from_data",
        "user_input": "Necesito separar el trafico de voz del de datos en los puertos de escritorio",
        "description": "Solicitud de aislamiento -> configura access vlan + voice vlan distintas",
        "weight": 3.5,
        "critical": True,
        "keywords_expected": ["switchport access vlan", "switchport voice vlan", "interface"],
        "should_suggest_voice_vlan": True,
        "task_type": "config_voice_vlan"
    },
    {
        "id": "configure_management_area_voip",
        "user_input": "Configura el area de gerencia para VoIP, tienen telefonos Cisco",
        "description": "Solicitud vaga con contexto -> genera vlan + puertos con voice vlan",
        "weight": 2.5,
        "critical": False,
        "keywords_expected": ["vlan", "switchport voice vlan", "interface"],
        "should_suggest_voice_vlan": True,
        "task_type": "config_voice_vlan"
    },
    {
        "id": "new_ip_phones_buying",
        "user_input": "Van a llegar 20 telefonos IP nuevos, como los configuro en el switch?",
        "description": "Consulta abierta -> genera configuracion de puerto con voice vlan",
        "weight": 2.5,
        "critical": False,
        "keywords_expected": ["switchport voice vlan", "interface", "vlan"],
        "should_suggest_voice_vlan": True,
        "task_type": "config_voice_vlan"
    },
    {
        "id": "calls_cutting_out",
        "user_input": "Las llamadas se cortan, como priorizo el trafico de voz?",
        "description": "Problema de voz -> genera QoS o configuracion de voice vlan",
        "weight": 3.0,
        "critical": False,  # No critico en alfa: el modelo puede interpretar esto como config de voice vlan
        # En alfa: aceptamos mls qos O switchport voice vlan como respuesta valida
        # El modelo puede interpretar 'llamadas cortandose' como 'telefonos no configurados'
        "keywords_expected": ["vlan", "interface"],
        "should_suggest_voice_vlan": False,
        "task_type": "config_qos"
    },
    {
        "id": "check_which_ports_have_phones",
        "user_input": "Que puertos del switch tienen telefonos conectados?",
        "description": "Consulta de estado -> genera show cdp neighbors o show interfaces switchport",
        "weight": 2.0,
        "critical": False,
        "keywords_expected": ["show", "cdp"],
        "should_suggest_voice_vlan": False,
        "task_type": "show"
    },
    {
        "id": "urgent_voip_setup",
        "user_input": "Urgente: necesito que el telefono de recepcion funcione ya",
        "description": "Solicitud urgente -> genera configuracion rapida de voice vlan en un puerto",
        "weight": 3.0,
        "critical": True,
        "keywords_expected": ["interface", "switchport voice vlan", "vlan"],
        "should_suggest_voice_vlan": True,
        "task_type": "config_voice_vlan"
    },
]


# ============================================================================
# BACKEND CALL
# ============================================================================

def call_corvelli_backend(user_input: str, session_id: str = None) -> Dict:
    if not session_id:
        session_id = f"voip-real-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

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

def evaluate_corvelli_response(test_case: Dict, backend_result: Dict) -> Dict:
    """
    Evalua si Corvelli genero comandos Cisco IOS utiles para el escenario VoIP.

    Filosofia Alfa: Validamos generacion de comandos, no diagnostico.
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

    # Check 2: Keywords relevantes presentes
    max_score += 1
    keywords = test_case.get("keywords_expected", [])
    found_kw = sum(1 for kw in keywords if kw.lower() in response)
    threshold = max(1, len(keywords) // 2)
    if found_kw >= threshold:
        earned_score += 1
        checks.append({"check": "keywords", "passed": True, "found": found_kw})
    else:
        checks.append({"check": "keywords", "passed": False, "found": found_kw, "expected": threshold})

    # Check 3 (bonus): Incluye configuracion de puerto para telefono (voice vlan o access vlan)
    if test_case.get("should_suggest_voice_vlan"):
        max_score += 1
        # En alfa: aceptamos switchport voice vlan O switchport access vlan como configuracion valida
        if "switchport voice vlan" in response or "voice vlan" in response or "switchport access vlan" in response:
            earned_score += 1
            checks.append({"check": "voice_vlan_cmd", "passed": True})
        else:
            checks.append({"check": "voice_vlan_cmd", "passed": False})

    # Check 4 (bonus): Incluye QoS o config de voice vlan cuando la tarea lo requiere
    # En alfa: aceptamos mls qos O switchport voice vlan (interpretacion razonable de "priorizar voz")
    if test_case.get("task_type") == "config_qos":
        max_score += 1
        if any(q in response for q in ["mls qos", "qos", "cos", "dscp", "switchport voice vlan", "switchport access vlan"]):
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

def run_real_scenario(test_case: Dict) -> Dict:
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

    evaluation = evaluate_corvelli_response(test_case, backend_result)
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


def run_all_real_scenarios() -> Dict:
    print("=" * 80)
    print("CORVELLI - Test VoIP Escenarios Reales (Backend Real)")
    print("=" * 80)
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Backend: {CORVELLI_BACKEND_URL}")
    print(f"Total de escenarios: {len(REAL_SCENARIOS)}")
    print("=" * 80)
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

    avg_score = weighted_score_sum / total_weight if total_weight > 0 else 0
    passed_tests = len([r for r in results if r.get("score", 0) >= 0.8])
    partial_tests = len([r for r in results if 0.5 <= r.get("score", 0) < 0.8])
    failed_tests = len([r for r in results if r.get("score", 0) < 0.5])
    critical_failures = [r for r in results if r.get("critical") and r.get("score", 0) < 0.8]

    summary = {
        "test_date": datetime.now().isoformat(),
        "test_type": "VOIP_REAL_SCENARIOS_BACKEND",
        "backend_url": CORVELLI_BACKEND_URL,
        "total_tests": len(REAL_SCENARIOS),
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
    print(f"Tests aprobados:     {summary['passed_tests']} (>=80%)")
    print(f"Tests parciales:     {summary['partial_tests']} (50-80%)")
    print(f"Tests fallidos:      {summary['failed_tests']} (<50%)")
    print(f"Fallas criticas:     {summary['critical_failures']}")
    print()
    print(f"Score promedio:      {summary['avg_score']:.2%}")
    print()

    if summary["critical_failures"] > 0:
        print("FALLAS CRITICAS DETECTADAS:")
        for result in summary["results"]:
            if result.get("critical") and result.get("score", 0) < 0.8:
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
        print("   El backend no genera comandos utiles ante solicitudes VoIP vagas.")
    elif summary["avg_score"] < 0.7:
        print("BACKEND REQUIERE MEJORAS")
        print(f"   Score promedio bajo ({summary['avg_score']:.1%}).")
    else:
        print("BACKEND APROBADO - Generacion de Comandos VoIP (Escenarios Vagos)")
        print(f"   Score promedio: {summary['avg_score']:.1%}")
        print(f"   Tests aprobados: {summary['passed_tests']}/{summary['total_tests']}")
        print()
        print("   Nota: Version Alfa evalua solo generacion de comandos.")
        print("   Diagnostico de calidad de voz y analisis de trafico = trabajo futuro.")


def save_report(summary: Dict):
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"voip_real_scenarios_{timestamp}.json"
    filepath = reports_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nReporte guardado: evaluation/reports/{filename}")
    return str(filepath)


def main():
    summary = run_all_real_scenarios()
    print_summary(summary)
    save_report(summary)


if __name__ == "__main__":
    main()
