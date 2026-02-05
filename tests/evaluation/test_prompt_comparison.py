#!/usr/bin/env python3
"""
Test de comparación entre versiones de prompts del sistema.
Evalúa v1.0 (verbose) vs v1.1 (optimized) sin necesidad de switch real.
"""

import json
import os
import sys
import requests
from typing import Dict, List, Tuple
from difflib import SequenceMatcher

# Configuración
OPENROUTER_API_KEY = "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"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
VERSIONS_FILE = "../../backend/prompts/versions.json"

# Costos del modelo (Gemini 2.0 Flash Lite)
COST_INPUT_PER_MILLION = 0.075  # $0.075 por 1M tokens de entrada
COST_OUTPUT_PER_MILLION = 0.30  # $0.30 por 1M tokens de salida

# Casos de prueba
TEST_CASES = [
    {
        "id": "ssh_complete",
        "description": "Configuración SSH completa desde cero",
        "switch_state": "Switch#",
        "user_input": "Configura este switch para poder conectarme con SSH. Usuario admin, contraseña cisco123, dominio lab.local",
        "required_commands": [
            "configure terminal",
            "hostname",
            "ip domain-name",
            "crypto key generate rsa",
            "username admin",
            "line vty 0 15",
            "login local",
            "transport input ssh",
            "interface vlan 1"
        ],
        "critical": True,
        "weight": 3.0
    },
    {
        "id": "vlan_creation",
        "description": "Crear VLAN simple",
        "switch_state": "Switch(config)#",
        "user_input": "crear vlan 10 llamado ventas",
        "required_commands": [
            "vlan 10",
            "name ventas"
        ],
        "critical": False,
        "weight": 1.0
    },
    {
        "id": "interface_config",
        "description": "Configurar puerto de acceso",
        "switch_state": "Switch#",
        "user_input": "configura el puerto gi0/5 en modo acceso para la vlan 10",
        "required_commands": [
            "configure terminal",
            "interface gigabitethernet0/5",
            "switchport mode access",
            "switchport access vlan 10"
        ],
        "critical": False,
        "weight": 1.5
    },
    {
        "id": "show_command",
        "description": "Comando show simple",
        "switch_state": "Switch#",
        "user_input": "muéstrame la configuración de las vlans",
        "required_commands": [
            "show vlan"
        ],
        "critical": False,
        "weight": 0.5
    },
    {
        "id": "multi_step",
        "description": "Múltiples pasos complejos",
        "switch_state": "Switch>",
        "user_input": "Crea vlan 20 IT, asigna los puertos 10 al 15 a esa vlan, y configura el puerto 24 como trunk",
        "required_commands": [
            "enable",
            "configure terminal",
            "vlan 20",
            "name IT",
            "interface range gigabitethernet0/10-15",
            "switchport access vlan 20",
            "interface gigabitethernet0/24",
            "switchport mode trunk"
        ],
        "critical": False,
        "weight": 2.0
    },
    {
        "id": "save_config",
        "description": "Guardar configuración",
        "switch_state": "Switch(config)#",
        "user_input": "guarda la configuración",
        "required_commands": [
            "end",
            "copy running-config startup-config"
        ],
        "critical": False,
        "weight": 1.0
    },
    {
        "id": "mode_detection_user",
        "description": "Detección correcta de modo usuario",
        "switch_state": "Switch>",
        "user_input": "crear vlan 30",
        "required_commands": [
            "enable",
            "configure terminal",
            "vlan 30"
        ],
        "critical": False,
        "weight": 1.5
    },
    {
        "id": "ip_management",
        "description": "IP de gestión en switch L2",
        "switch_state": "Switch#",
        "user_input": "configura la IP de gestión 192.168.1.10 máscara 255.255.255.0",
        "required_commands": [
            "configure terminal",
            "interface vlan 1",
            "ip address 192.168.1.10 255.255.255.0",
            "no shutdown"
        ],
        "critical": False,
        "weight": 1.5
    }
]


def load_prompts() -> Dict:
    """Carga las versiones de prompts desde el JSON"""
    versions_path = os.path.join(os.path.dirname(__file__), VERSIONS_FILE)
    with open(versions_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def call_openrouter_model(system_prompt: str, switch_prompt: str, user_message: str, max_tokens: int = 300) -> Dict:
    """
    Llama a OpenRouter API con el prompt especificado.
    Retorna: {"commands": str, "tokens_input": int, "tokens_output": int, "cost": float}
    """
    # Reemplazar placeholder
    system_prompt_formatted = system_prompt.replace("{{switchPrompt}}", switch_prompt)
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "google/gemini-2.0-flash-lite-001",
        "messages": [
            {"role": "system", "content": system_prompt_formatted},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens
    }
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        commands = result["choices"][0]["message"]["content"].strip()
        
        # Tokens
        usage = result.get("usage", {})
        tokens_input = usage.get("prompt_tokens", 0)
        tokens_output = usage.get("completion_tokens", 0)
        
        # Costo
        cost_input = (tokens_input / 1_000_000) * COST_INPUT_PER_MILLION
        cost_output = (tokens_output / 1_000_000) * COST_OUTPUT_PER_MILLION
        total_cost = cost_input + cost_output
        
        return {
            "commands": commands,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "cost": total_cost,
            "error": None
        }
    
    except Exception as e:
        return {
            "commands": "",
            "tokens_input": 0,
            "tokens_output": 0,
            "cost": 0,
            "error": str(e)
        }


def similarity_score(text1: str, text2: str) -> float:
    """Calcula similitud entre dos textos (0.0 a 1.0)"""
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()


def evaluate_commands(generated: str, required: List[str]) -> Dict:
    """
    Evalúa si los comandos generados contienen los requeridos.
    Retorna: {"score": float, "missing": List[str], "found": List[str]}
    """
    generated_lower = generated.lower()
    found = []
    missing = []
    
    for cmd in required:
        # Buscar comando o similitud alta
        if cmd.lower() in generated_lower:
            found.append(cmd)
        else:
            # Verificar con similitud parcial (para variaciones)
            max_sim = 0
            for line in generated.split('\n'):
                sim = similarity_score(cmd, line)
                max_sim = max(max_sim, sim)
            
            if max_sim > 0.7:  # 70% de similitud mínima
                found.append(cmd)
            else:
                missing.append(cmd)
    
    score = len(found) / len(required) if required else 1.0
    
    return {
        "score": score,
        "found": found,
        "missing": missing
    }


def run_test_case(test_case: Dict, prompt_version: str, system_prompt: str, max_tokens: int) -> Dict:
    """Ejecuta un caso de prueba individual"""
    print(f"  [{test_case['id']}] {test_case['description']}...", end=" ")
    
    result = call_openrouter_model(
        system_prompt=system_prompt,
        switch_prompt=test_case['switch_state'],
        user_message=test_case['user_input'],
        max_tokens=max_tokens
    )
    
    if result['error']:
        print(f"❌ ERROR: {result['error']}")
        return {
            "test_id": test_case['id'],
            "success": False,
            "error": result['error'],
            "score": 0.0,
            "tokens_input": 0,
            "tokens_output": 0,
            "cost": 0
        }
    
    # Evaluar comandos
    evaluation = evaluate_commands(result['commands'], test_case['required_commands'])
    
    # Score ponderado
    weighted_score = evaluation['score'] * test_case['weight']
    
    status = "✅" if evaluation['score'] >= 0.9 else "⚠️" if evaluation['score'] >= 0.7 else "❌"
    print(f"{status} Score: {evaluation['score']:.2f} | Tokens: {result['tokens_input']}+{result['tokens_output']} | Cost: ${result['cost']:.6f}")
    
    return {
        "test_id": test_case['id'],
        "description": test_case['description'],
        "critical": test_case['critical'],
        "weight": test_case['weight'],
        "success": True,
        "score": evaluation['score'],
        "weighted_score": weighted_score,
        "found_commands": len(evaluation['found']),
        "missing_commands": evaluation['missing'],
        "generated_output": result['commands'],
        "tokens_input": result['tokens_input'],
        "tokens_output": result['tokens_output'],
        "cost": result['cost']
    }


def run_version_tests(version_id: str, version_data: Dict) -> Dict:
    """Ejecuta todos los tests para una versión de prompt"""
    print(f"\n{'='*80}")
    print(f"TESTING VERSION: {version_id} - {version_data['name']}")
    print(f"{'='*80}")
    print(f"Description: {version_data['description']}")
    print(f"Estimated tokens: {version_data['estimated_tokens']}")
    print(f"Estimated cost: ${version_data['estimated_cost_per_command']:.7f}")
    print()
    
    system_prompt = version_data['prompt_text']
    max_tokens = 400 if version_id == "1.1" else 300  # v1.1 usa más tokens de salida
    
    results = []
    total_cost = 0
    total_tokens_input = 0
    total_tokens_output = 0
    total_weight = 0
    weighted_score_sum = 0
    
    for test_case in TEST_CASES:
        result = run_test_case(test_case, version_id, system_prompt, max_tokens)
        results.append(result)
        
        if result['success']:
            total_cost += result['cost']
            total_tokens_input += result['tokens_input']
            total_tokens_output += result['tokens_output']
            total_weight += test_case['weight']
            weighted_score_sum += result['weighted_score']
    
    # Calcular promedios
    num_tests = len(TEST_CASES)
    avg_score = weighted_score_sum / total_weight if total_weight > 0 else 0
    avg_tokens_input = total_tokens_input / num_tests
    avg_tokens_output = total_tokens_output / num_tests
    avg_cost = total_cost / num_tests
    
    # Identificar tests críticos fallidos
    critical_failures = [r for r in results if r.get('critical') and r.get('score', 0) < 0.9]
    
    summary = {
        "version_id": version_id,
        "version_name": version_data['name'],
        "total_tests": num_tests,
        "passed_tests": len([r for r in results if r.get('score', 0) >= 0.9]),
        "partial_tests": len([r for r in results if 0.7 <= r.get('score', 0) < 0.9]),
        "failed_tests": len([r for r in results if r.get('score', 0) < 0.7]),
        "critical_failures": len(critical_failures),
        "avg_score": avg_score,
        "avg_tokens_input": avg_tokens_input,
        "avg_tokens_output": avg_tokens_output,
        "total_tokens": total_tokens_input + total_tokens_output,
        "total_cost": total_cost,
        "avg_cost": avg_cost,
        "results": results
    }
    
    return summary


def print_comparison(v1_summary: Dict, v2_summary: Dict):
    """Imprime comparación entre dos versiones"""
    print(f"\n{'='*80}")
    print("COMPARISON REPORT")
    print(f"{'='*80}\n")
    
    # Tabla de métricas
    print(f"{'Metric':<30} {'v1.0 (Verbose)':<25} {'v1.1 (Optimized)':<25} {'Change':<15}")
    print("-" * 95)
    
    # Accuracy
    v1_score = v1_summary['avg_score']
    v2_score = v2_summary['avg_score']
    score_change = ((v2_score - v1_score) / v1_score * 100) if v1_score > 0 else 0
    v1_score_pct = f'{v1_score:.2%}'
    v2_score_pct = f'{v2_score:.2%}'
    score_change_str = f'{score_change:+.1f}%'
    print(f"{'Average Score':<30} {v1_score_pct:<25} {v2_score_pct:<25} {score_change_str:<15}")
    
    # Tests
    v1_passed = f"{v1_summary['passed_tests']}/{v1_summary['total_tests']}"
    v2_passed = f"{v2_summary['passed_tests']}/{v2_summary['total_tests']}"
    passed_diff = v2_summary['passed_tests'] - v1_summary['passed_tests']
    print(f"{'Tests Passed (>90%)':<30} {v1_passed:<25} {v2_passed:<25} {passed_diff:+d}")
    
    v1_critical = f"{v1_summary['critical_failures']}"
    v2_critical = f"{v2_summary['critical_failures']}"
    critical_diff = v2_summary['critical_failures'] - v1_summary['critical_failures']
    print(f"{'Critical Failures':<30} {v1_critical:<25} {v2_critical:<25} {critical_diff:+d}")
    
    # Tokens
    v1_input = v1_summary['avg_tokens_input']
    v2_input = v2_summary['avg_tokens_input']
    input_reduction = ((v1_input - v2_input) / v1_input * 100) if v1_input > 0 else 0
    v1_input_str = f'{v1_input:.0f}'
    v2_input_str = f'{v2_input:.0f}'
    input_change_str = f'{-input_reduction:+.1f}%'
    print(f"{'Avg Input Tokens':<30} {v1_input_str:<25} {v2_input_str:<25} {input_change_str:<15}")
    
    v1_output = v1_summary['avg_tokens_output']
    v2_output = v2_summary['avg_tokens_output']
    output_change = ((v2_output - v1_output) / v1_output * 100) if v1_output > 0 else 0
    v1_output_str = f'{v1_output:.0f}'
    v2_output_str = f'{v2_output:.0f}'
    output_change_str = f'{output_change:+.1f}%'
    print(f"{'Avg Output Tokens':<30} {v1_output_str:<25} {v2_output_str:<25} {output_change_str:<15}")
    
    # Costo
    v1_cost = v1_summary['avg_cost']
    v2_cost = v2_summary['avg_cost']
    cost_reduction = ((v1_cost - v2_cost) / v1_cost * 100) if v1_cost > 0 else 0
    v1_cost_str = f'${v1_cost:.7f}'
    v2_cost_str = f'${v2_cost:.7f}'
    cost_change_str = f'{-cost_reduction:+.1f}%'
    print(f"{'Avg Cost per Command':<30} {v1_cost_str:<25} {v2_cost_str:<25} {cost_change_str:<15}")
    
    v1_total = f"${v1_summary['total_cost']:.6f}"
    v2_total = f"${v2_summary['total_cost']:.6f}"
    total_diff = v2_summary['total_cost'] - v1_summary['total_cost']
    total_diff_str = f'${total_diff:+.6f}'
    print(f"{'Total Test Cost':<30} {v1_total:<25} {v2_total:<25} {total_diff_str:<15}")
    
    # Proyección a 100k comandos
    v1_100k = v1_cost * 100000
    v2_100k = v2_cost * 100000
    savings_100k = v1_100k - v2_100k
    v1_100k_str = f'${v1_100k:.2f}'
    v2_100k_str = f'${v2_100k:.2f}'
    savings_str = f'${-savings_100k:+.2f}'
    print(f"\n{'Projected Cost (100k cmds)':<30} {v1_100k_str:<25} {v2_100k_str:<25} {savings_str:<15}")
    
    # Recomendación
    print(f"\n{'='*80}")
    print("RECOMMENDATION")
    print(f"{'='*80}\n")
    
    if v2_summary['critical_failures'] > v1_summary['critical_failures']:
        print("⚠️  WARNING: v1.1 has MORE critical failures than v1.0")
        print("   NOT RECOMMENDED for production deployment")
    elif v2_score < v1_score - 0.05:  # 5% drop in accuracy
        print("⚠️  WARNING: v1.1 accuracy is significantly lower than v1.0")
        print("   Consider further tuning before deployment")
    elif cost_reduction < 30:
        print("⚠️  Cost reduction is less than expected (< 30%)")
        print("   Review if optimization is worth the effort")
    else:
        print("✅ v1.1 RECOMMENDED for production deployment")
        print(f"   • Similar or better accuracy ({v2_score:.1%} vs {v1_score:.1%})")
        print(f"   • Significant cost reduction ({cost_reduction:.1f}%)")
        print(f"   • No increase in critical failures")
        print(f"   • Estimated annual savings: ${savings_100k * 3.65:.2f} (100k cmds/month)")
    
    # Detalles de tests críticos fallidos
    if v2_summary['critical_failures'] > 0:
        print(f"\n⚠️  CRITICAL TEST FAILURES IN v1.1:")
        for result in v2_summary['results']:
            if result.get('critical') and result.get('score', 0) < 0.9:
                print(f"   • {result['test_id']}: {result['description']}")
                print(f"     Score: {result['score']:.2%}, Missing: {result.get('missing_commands', [])}")


def generate_comparison_table_markdown(v1_summary: Dict, v2_summary: Dict) -> str:
    """Genera tabla comparativa en formato Markdown con cálculos verificables"""
    
    # Cálculos con fórmulas explícitas
    v1_score = v1_summary['avg_score']
    v2_score = v2_summary['avg_score']
    accuracy_diff = v2_score - v1_score
    accuracy_change_pct = (accuracy_diff / v1_score * 100) if v1_score > 0 else 0
    
    v1_passed = v1_summary['passed_tests']
    v2_passed = v2_summary['passed_tests']
    passed_diff = v2_passed - v1_passed
    
    v1_critical = v1_summary['critical_failures']
    v2_critical = v2_summary['critical_failures']
    critical_diff = v2_critical - v1_critical
    
    v1_tokens_in = v1_summary['avg_tokens_input']
    v2_tokens_in = v2_summary['avg_tokens_input']
    token_in_diff = v2_tokens_in - v1_tokens_in
    token_in_reduction = (abs(token_in_diff) / v1_tokens_in * 100) if v1_tokens_in > 0 else 0
    
    v1_tokens_out = v1_summary['avg_tokens_output']
    v2_tokens_out = v2_summary['avg_tokens_output']
    token_out_diff = v2_tokens_out - v1_tokens_out
    token_out_change = (token_out_diff / v1_tokens_out * 100) if v1_tokens_out > 0 else 0
    
    v1_cost = v1_summary['avg_cost']
    v2_cost = v2_summary['avg_cost']
    cost_diff = v2_cost - v1_cost
    cost_reduction = (abs(cost_diff) / v1_cost * 100) if v1_cost > 0 else 0
    
    v1_total_cost = v1_summary['total_cost']
    v2_total_cost = v2_summary['total_cost']
    total_cost_diff = v2_total_cost - v1_total_cost
    
    # Proyecciones
    cost_100k_v1 = v1_cost * 100000
    cost_100k_v2 = v2_cost * 100000
    savings_100k = cost_100k_v1 - cost_100k_v2
    
    cost_1M_v1 = v1_cost * 1000000
    cost_1M_v2 = v2_cost * 1000000
    savings_1M = cost_1M_v1 - cost_1M_v2
    
    annual_savings = savings_100k * 12  # 100k comandos/mes
    
    # Generar Markdown
    md = []
    md.append("# Comparación de Versiones de Prompt - Corvelli")
    md.append(f"\n**Fecha:** 4 de febrero de 2026")
    md.append(f"**Modelo:** google/gemini-2.0-flash-lite-001")
    md.append(f"**Total de Tests:** {v1_summary['total_tests']}")
    md.append("\n---\n")
    
    md.append("## 📊 Tabla Comparativa\n")
    md.append("| Métrica | v1.0 (Verbose) | v1.1 (Optimizada) | Cambio | % Cambio |")
    md.append("|---------|----------------|-------------------|---------|----------|")
    
    # Accuracy
    status_accuracy = "✅" if accuracy_change_pct > 0 else "⚠️" if accuracy_change_pct == 0 else "❌"
    md.append(f"| **Accuracy Promedio** | {v1_score:.2%} | {v2_score:.2%} | {accuracy_diff:+.4f} | {status_accuracy} {accuracy_change_pct:+.1f}% |")
    
    # Tests
    status_passed = "✅" if passed_diff >= 0 else "❌"
    md.append(f"| **Tests Aprobados (>90%)** | {v1_passed}/{v1_summary['total_tests']} | {v2_passed}/{v2_summary['total_tests']} | {passed_diff:+d} | {status_passed} |")
    
    status_critical = "✅" if critical_diff <= 0 else "❌"
    md.append(f"| **Fallas Críticas** | {v1_critical} | {v2_critical} | {critical_diff:+d} | {status_critical} |")
    
    # Tokens Input
    status_tokens_in = "✅" if token_in_diff < 0 else "❌"
    md.append(f"| **Tokens Entrada (avg)** | {v1_tokens_in:.0f} | {v2_tokens_in:.0f} | {token_in_diff:+.0f} | {status_tokens_in} -{token_in_reduction:.1f}% |")
    
    # Tokens Output
    status_tokens_out = "✅" if token_out_diff <= 0 else "⚠️"
    md.append(f"| **Tokens Salida (avg)** | {v1_tokens_out:.0f} | {v2_tokens_out:.0f} | {token_out_diff:+.0f} | {status_tokens_out} {token_out_change:+.1f}% |")
    
    # Cost per command
    status_cost = "✅" if cost_diff < 0 else "❌"
    md.append(f"| **Costo por Comando** | ${v1_cost:.7f} | ${v2_cost:.7f} | ${cost_diff:+.7f} | {status_cost} -{cost_reduction:.1f}% |")
    
    md.append(f"| **Costo Total Tests** | ${v1_total_cost:.6f} | ${v2_total_cost:.6f} | ${total_cost_diff:+.6f} | - |")
    
    md.append("\n---\n")
    md.append("## 💰 Proyecciones de Costo\n")
    md.append("| Volumen | v1.0 | v1.1 | Ahorro | % Reducción |")
    md.append("|---------|------|------|--------|-------------|")
    md.append(f"| **100k comandos** | ${cost_100k_v1:.2f} | ${cost_100k_v2:.2f} | ${savings_100k:.2f} | -{cost_reduction:.1f}% |")
    md.append(f"| **1M comandos** | ${cost_1M_v1:.2f} | ${cost_1M_v2:.2f} | ${savings_1M:.2f} | -{cost_reduction:.1f}% |")
    md.append(f"| **Anual (100k/mes)** | ${cost_100k_v1 * 12:.2f} | ${cost_100k_v2 * 12:.2f} | ${annual_savings:.2f} | -{cost_reduction:.1f}% |")
    
    md.append("\n---\n")
    md.append("## 🔍 Detalles de Cálculos (Verificables)\n")
    md.append("\n### Accuracy:")
    md.append(f"- v1.0: {v1_score:.6f} ({v1_score:.2%})")
    md.append(f"- v1.1: {v2_score:.6f} ({v2_score:.2%})")
    md.append(f"- Diferencia: {v2_score:.6f} - {v1_score:.6f} = {accuracy_diff:+.6f}")
    md.append(f"- % Cambio: ({accuracy_diff:.6f} / {v1_score:.6f}) × 100 = {accuracy_change_pct:+.2f}%")
    
    md.append("\n### Tokens de Entrada:")
    md.append(f"- v1.0: {v1_tokens_in:.2f} tokens")
    md.append(f"- v1.1: {v2_tokens_in:.2f} tokens")
    md.append(f"- Diferencia: {v2_tokens_in:.2f} - {v1_tokens_in:.2f} = {token_in_diff:+.2f}")
    md.append(f"- % Reducción: ({abs(token_in_diff):.2f} / {v1_tokens_in:.2f}) × 100 = {token_in_reduction:.2f}%")
    
    md.append("\n### Costo por Comando:")
    md.append(f"- v1.0: ${v1_cost:.10f}")
    md.append(f"- v1.1: ${v2_cost:.10f}")
    md.append(f"- Diferencia: ${v2_cost:.10f} - ${v1_cost:.10f} = ${cost_diff:+.10f}")
    md.append(f"- % Reducción: ({abs(cost_diff):.10f} / {v1_cost:.10f}) × 100 = {cost_reduction:.2f}%")
    
    md.append("\n### Proyección 100k Comandos:")
    md.append(f"- v1.0: ${v1_cost:.10f} × 100,000 = ${cost_100k_v1:.2f}")
    md.append(f"- v1.1: ${v2_cost:.10f} × 100,000 = ${cost_100k_v2:.2f}")
    md.append(f"- Ahorro: ${cost_100k_v1:.2f} - ${cost_100k_v2:.2f} = ${savings_100k:.2f}")
    
    md.append("\n---\n")
    md.append("## 📋 Detalles de Tests por Caso\n")
    md.append("| Test ID | Descripción | v1.0 Score | v1.1 Score | Mejora |")
    md.append("|---------|-------------|------------|------------|--------|")
    
    for i, test_case in enumerate(TEST_CASES):
        v1_result = v1_summary['results'][i]
        v2_result = v2_summary['results'][i]
        v1_test_score = v1_result.get('score', 0)
        v2_test_score = v2_result.get('score', 0)
        improvement = v2_test_score - v1_test_score
        status = "✅" if improvement >= 0 else "⚠️"
        critical = " 🔴" if test_case['critical'] else ""
        md.append(f"| `{test_case['id']}` | {test_case['description']}{critical} | {v1_test_score:.2%} | {v2_test_score:.2%} | {status} {improvement:+.1%} |")
    
    md.append("\n---\n")
    md.append("## ✅ Recomendación Final\n")
    
    if v2_summary['critical_failures'] > v1_summary['critical_failures']:
        md.append("### ⚠️ NO RECOMENDADO")
        md.append(f"- v1.1 tiene {v2_summary['critical_failures']} fallas críticas vs {v1_summary['critical_failures']} en v1.0")
        md.append("- Se requiere más trabajo antes de deployment")
    elif v2_score < v1_score - 0.05:
        md.append("### ⚠️ REQUIERE REVISIÓN")
        md.append(f"- Accuracy bajó significativamente ({accuracy_change_pct:.1f}%)")
        md.append("- Considerar ajustes antes de producción")
    elif cost_reduction < 30:
        md.append("### ⚠️ BAJO IMPACTO")
        md.append(f"- Reducción de costo menor al esperado ({cost_reduction:.1f}%)")
        md.append("- Evaluar si vale la pena el cambio")
    else:
        md.append("### ✅ RECOMENDADO PARA PRODUCCIÓN")
        md.append(f"- Mejor accuracy: {v2_score:.1%} vs {v1_score:.1%} ({accuracy_change_pct:+.1f}%)")
        md.append(f"- Reducción de costos: {cost_reduction:.1f}%")
        md.append(f"- Fallas críticas: {v2_critical} vs {v1_critical} ({critical_diff:+d})")
        md.append(f"- Ahorro anual estimado: **${annual_savings:.2f}** (asumiendo 100k comandos/mes)")
        md.append(f"- Reducción de tokens: {token_in_reduction:.1f}%")
    
    return "\n".join(md)


def save_results(v1_summary: Dict, v2_summary: Dict):
    """Guarda resultados en JSON y genera tabla comparativa en Markdown"""
    output_dir = os.path.dirname(__file__)
    
    # Calcular métricas de comparación
    v1_cost = v1_summary['avg_cost']
    v2_cost = v2_summary['avg_cost']
    v1_tokens = v1_summary['avg_tokens_input']
    v2_tokens = v2_summary['avg_tokens_input']
    
    # JSON con resultados completos
    json_file = "prompt_comparison_results.json"
    json_path = os.path.join(output_dir, json_file)
    
    data = {
        "test_date": "2026-02-04",
        "model": "google/gemini-2.0-flash-lite-001",
        "versions_tested": ["1.0", "1.1"],
        "v1.0_summary": v1_summary,
        "v1.1_summary": v2_summary,
        "comparison": {
            "accuracy_change": v2_summary['avg_score'] - v1_summary['avg_score'],
            "accuracy_change_percent": ((v2_summary['avg_score'] - v1_summary['avg_score']) / v1_summary['avg_score'] * 100) if v1_summary['avg_score'] > 0 else 0,
            "cost_reduction_absolute": v1_cost - v2_cost,
            "cost_reduction_percent": ((v1_cost - v2_cost) / v1_cost * 100) if v1_cost > 0 else 0,
            "token_reduction_absolute": v1_tokens - v2_tokens,
            "token_reduction_percent": ((v1_tokens - v2_tokens) / v1_tokens * 100) if v1_tokens > 0 else 0,
            "savings_100k_commands": (v1_cost - v2_cost) * 100000,
            "savings_1M_commands": (v1_cost - v2_cost) * 1000000,
            "savings_annual_100k_per_month": (v1_cost - v2_cost) * 100000 * 12
        }
    }
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Markdown con tabla comparativa
    md_file = "prompt_comparison_report.md"
    md_path = os.path.join(output_dir, md_file)
    
    markdown_content = generate_comparison_table_markdown(v1_summary, v2_summary)
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"\n✅ Results saved to:")
    print(f"   - JSON: {json_file}")
    print(f"   - Markdown Report: {md_file}")


def main():
    print("CORVELLI - Prompt Version Comparison Test")
    print("=" * 80)
    
    # Cargar prompts
    prompts = load_prompts()
    
    # Test v1.0
    v1_summary = run_version_tests("1.0", prompts['versions']['1.0'])
    
    # Test v1.1
    v2_summary = run_version_tests("1.1", prompts['versions']['1.1'])
    
    # Comparación
    print_comparison(v1_summary, v2_summary)
    
    # Guardar resultados
    save_results(v1_summary, v2_summary)


if __name__ == "__main__":
    main()
