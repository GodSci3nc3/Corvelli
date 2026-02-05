# Comparación de Versiones de Prompt - Corvelli

**Fecha:** 4 de febrero de 2026
**Modelo:** google/gemini-2.0-flash-lite-001
**Total de Tests:** 8

---

## Tabla Comparativa

| Métrica | v1.0 (Verbose) | v1.1 (Optimizada) | Cambio | % Cambio |
|---------|----------------|-------------------|---------|----------|
| **Accuracy Promedio** | 90.28% | 93.75% | +0.0347 | +3.8% |
| **Tests Aprobados (>90%)** | 6/8 | 6/8 | +0 | = |
| **Fallas Críticas** | 1 | 0 | -1 | MEJOR |
| **Tokens Entrada (avg)** | 803 | 330 | -472 | -58.9% |
| **Tokens Salida (avg)** | 40 | 47 | +7 | +18.6% |
| **Costo por Comando** | $0.0000721 | $0.0000389 | $-0.0000332 | -46.1% |
| **Costo Total Tests** | $0.000577 | $0.000311 | $-0.000266 | - |

---

## Proyecciones de Costo

| Volumen | v1.0 | v1.1 | Ahorro | % Reducción |
|---------|------|------|--------|-------------|
| **100k comandos** | $7.21 | $3.89 | $3.32 | -46.1% |
| **1M comandos** | $72.08 | $38.86 | $33.23 | -46.1% |
| **Anual (100k/mes)** | $86.50 | $46.63 | $39.87 | -46.1% |

---

## Detalles de Cálculos (Verificables)


### Accuracy:
- v1.0: 0.902778 (90.28%)
- v1.1: 0.937500 (93.75%)
- Diferencia: 0.937500 - 0.902778 = +0.034722
- % Cambio: (0.034722 / 0.902778) × 100 = +3.85%

### Tokens de Entrada:
- v1.0: 802.62 tokens
- v1.1: 330.12 tokens
- Diferencia: 330.12 - 802.62 = -472.50
- % Reducción: (472.50 / 802.62) × 100 = 58.87%

### Costo por Comando:
- v1.0: $0.0000720844
- v1.1: $0.0000388594
- Diferencia: $0.0000388594 - $0.0000720844 = $-0.0000332250
- % Reducción: (0.0000332250 / 0.0000720844) × 100 = 46.09%

### Proyección 100k Comandos:
- v1.0: $0.0000720844 × 100,000 = $7.21
- v1.1: $0.0000388594 × 100,000 = $3.89
- Ahorro: $7.21 - $3.89 = $3.32

---

## Detalles de Tests por Caso

| Test ID | Descripción | v1.0 Score | v1.1 Score | Mejora |
|---------|-------------|------------|------------|--------|
| `ssh_complete` | Configuración SSH completa desde cero [CRITICO] | 77.78% | 100.00% | +22.2% |
| `vlan_creation` | Crear VLAN simple | 100.00% | 100.00% | +0.0% |
| `interface_config` | Configurar puerto de acceso | 100.00% | 100.00% | +0.0% |
| `show_command` | Comando show simple | 100.00% | 100.00% | +0.0% |
| `multi_step` | Múltiples pasos complejos | 75.00% | 87.50% | +12.5% |
| `save_config` | Guardar configuración | 100.00% | 100.00% | +0.0% |
| `mode_detection_user` | Detección correcta de modo usuario | 100.00% | 66.67% | -33.3% |
| `ip_management` | IP de gestión en switch L2 | 100.00% | 100.00% | +0.0% |

---

## Recomendación Final

### RECOMENDADO PARA PRODUCCIÓN
- Mejor accuracy: 93.8% vs 90.3% (+3.8%)
- Reducción de costos: 46.1%
- Fallas críticas: 0 vs 1 (-1)
- Ahorro anual estimado: **$39.87** (asumiendo 100k comandos/mes)
- Reducción de tokens: 58.9%