"""
Script Inicializador Rápido do Subsistema Gramado (Smart Pitch).
Abre automaticamente em janelas separadas de terminal todos os componentes:
  - 3 Réplicas do Controlador de Processo (IDs 1, 2 e 3)
  - 1 Middleware de Objetos Distribuídos
  - 1 Módulo de Atuadores MQTT
  - 1 Módulo de Sensores MQTT
  - 1 Painel Cliente Interativo

Pré-requisito: Broker MQTT Mosquitto rodando (docker compose up -d).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

DIRETORIO_GRAMADO = Path(__file__).resolve().parent

# Garante o interpretador correto caso o Windows tenha aliases da WindowsStore
if "WindowsApps" in sys.executable:
    PYTHON_EXEC = r"C:\Users\bryan\AppData\Local\Programs\Python\Python315\python.exe"
    if not Path(PYTHON_EXEC).exists():
        PYTHON_EXEC = "py"
else:
    PYTHON_EXEC = sys.executable



def abrir_processo(titulo: str, comando_args: list[str]) -> None:
    """Abre um novo terminal visível para acompanhar os logs de cada componente."""
    if os.name == "nt":
        # Windows: abre uma nova janela do cmd mantendo-a aberta (/k) caso pare
        cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in comando_args)
        subprocess.Popen(
            f'start "{titulo}" cmd /k {cmd_str}',
            cwd=str(DIRETORIO_GRAMADO),
            shell=True,
        )
    else:
        # Linux / macOS: inicia em background no grupo atual
        subprocess.Popen(comando_args, cwd=str(DIRETORIO_GRAMADO))


def main() -> None:
    print("=" * 65)
    print(" INICIANDO TODOS OS COMPONENTES DO SMART PITCH (GRAMADO)")
    print("=" * 65)

    processos = [
        ("Controlador 1", [PYTHON_EXEC, "controlador.py", "1"]),
        ("Controlador 2", [PYTHON_EXEC, "controlador.py", "2"]),
        ("Controlador 3", [PYTHON_EXEC, "controlador.py", "3"]),
        ("Middleware SD", [PYTHON_EXEC, "middleware.py"]),
        ("Atuadores MQTT", [PYTHON_EXEC, "atuadores.py"]),
        ("Sensores MQTT", [PYTHON_EXEC, "sensores.py"]),
    ]

    for titulo, args in processos:
        print(f" -> Iniciando {titulo}...")
        abrir_processo(titulo, args)
        time.sleep(0.8)

    print(" -> Abrindo Painel do Cliente...")
    time.sleep(1.0)
    abrir_processo("Cliente Smart Pitch", [PYTHON_EXEC, "cliente.py"])

    print("\nTodos os processos foram iniciados em suas respectivas janelas!")


if __name__ == "__main__":
    main()

