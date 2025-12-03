#!/bin/bash
# Script para ejecutar el test automáticamente

cd /home/arthur/Escritorio/AIConsole/tests/switch_project

# Enviar ENTERs automáticamente al script
(
  sleep 1; echo ""   # Primer ENTER para comenzar
  sleep 45; echo "y" # Step 1
  sleep 45; echo "y" # Step 2
  sleep 45; echo "y" # Step 3
  sleep 45; echo "y" # Step 4
  sleep 45; echo "y" # Step 5
  sleep 45; echo "y" # Step 6
  sleep 45; echo "y" # Step 7
) | python3 configure_switch.py
