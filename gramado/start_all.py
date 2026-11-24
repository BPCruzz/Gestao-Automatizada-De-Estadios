"""
Script Inicializador do Subsistema Gramado (Smart Pitch).
Modo padrão (unificado em 1 terminal):
  - Sobe os 3 Controladores, Atuadores, Sensores e o Painel Web em background.
  - Abre o Painel Web estilo terminal (http://127.0.0.1:8080).
  - Permite derrubar/religar qualquer Controlador (1, 2 ou 3) no próprio terminal
    para demonstrar tolerância a quedas sem precisar de 7 janelas abertas.

Uso alternativo (janelas separadas):
  python gramado/start_all.py --janelas

Pré-requisito: Broker MQTT Mosquitto e 3 bancos PostgreSQL rodando (docker compose up -d).
"""

import os
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

DIRETORIO_GRAMADO = Path(__file__).resolve().parent

# Garante o interpretador correto caso o Windows tenha aliases da WindowsStore
if "WindowsApps" in sys.executable:
    PYTHON_EXEC = r"C:\Users\bryan\AppData\Local\Programs\Python\Python315\python.exe"
    if not Path(PYTHON_EXEC).exists():
        PYTHON_EXEC = "python"
else:
    PYTHON_EXEC = sys.executable


def iniciar_background(comando_args: list[str]) -> subprocess.Popen:
    """Inicia um componente silenciosamente no mesmo console."""
    return subprocess.Popen(
        comando_args,
        cwd=str(DIRETORIO_GRAMADO),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def encerrar_processo(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


def abrir_em_janela(titulo: str, comando_args: list[str]) -> None:
    """Abre um novo terminal visível para acompanhar os logs de cada componente."""
    if os.name == "nt":
        cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in comando_args)
        subprocess.Popen(
            f'start "{titulo}" cmd /k {cmd_str}',
            cwd=str(DIRETORIO_GRAMADO),
            shell=True,
        )
    else:
        subprocess.Popen(comando_args, cwd=str(DIRETORIO_GRAMADO))


def iniciar_modo_janelas() -> None:
    print("=" * 65)
    print(" INICIANDO COMPONENTES DO SMART PITCH EM JANELAS SEPARADAS")
    print("=" * 65)

    processos = [
        ("Controlador 1", [PYTHON_EXEC, "controlador.py", "1"]),
        ("Controlador 2", [PYTHON_EXEC, "controlador.py", "2"]),
        ("Controlador 3", [PYTHON_EXEC, "controlador.py", "3"]),
        ("Atuadores MQTT", [PYTHON_EXEC, "atuadores.py"]),
        ("Sensores MQTT", [PYTHON_EXEC, "sensores.py"]),
    ]

    for titulo, args in processos:
        print(f" -> Iniciando {titulo}...")
        abrir_em_janela(titulo, args)
        time.sleep(0.8)

    print(" -> Abrindo Painel Web...")
    time.sleep(1.0)
    abrir_em_janela("Painel Smart Pitch", [PYTHON_EXEC, "painel_web.py"])
    print("\nTodos os processos foram iniciados!")


def iniciar_modo_unificado() -> None:
    print("=" * 65)
    print("   SMART PITCH — GERENCIADOR CENTRALIZADO (1 TERMINAL)")
    print("=" * 65)

    controladores: dict[int, subprocess.Popen | None] = {}
    for cid in (1, 2, 3):
        print(f" -> Subindo Controlador {cid}...")
        controladores[cid] = iniciar_background([PYTHON_EXEC, "controlador.py", str(cid)])
        time.sleep(0.4)

    print(" -> Subindo Atuadores MQTT e Sensores MQTT...")
    atuadores = iniciar_background([PYTHON_EXEC, "atuadores.py"])
    sensores = iniciar_background([PYTHON_EXEC, "sensores.py"])
    time.sleep(0.6)

    print(" -> Subindo Painel Web Estilo Terminal (http://127.0.0.1:8080)...")
    painel = iniciar_background([PYTHON_EXEC, "painel_web.py"])
    time.sleep(1.0)
    webbrowser.open("http://127.0.0.1:8080")

    try:
        while True:
            print("\n" + "-" * 65)
            for cid in (1, 2, 3):
                ativo = controladores[cid] is not None and controladores[cid].poll() is None
                status = "ONLINE" if ativo else "PARADO (OFFLINE)"
                print(f"   Controlador {cid}: [{status}]")
            print("-" * 65)
            print(" Comandos:")
            print("   [1] Derrubar / Religar Controlador 1")
            print("   [2] Derrubar / Religar Controlador 2")
            print("   [3] Derrubar / Religar Controlador 3")
            print("   [4] Abrir Painel Web no navegador (http://127.0.0.1:8080)")
            print("   [0] Encerrar todos os processos")

            op = input("\nOpcao: ").strip()
            if op in ("1", "2", "3"):
                cid = int(op)
                proc = controladores[cid]
                if proc is not None and proc.poll() is None:
                    encerrar_processo(proc)
                    controladores[cid] = None
                    print(f" -> Controlador {cid} DERRUBADO (simulacao de falha por queda).")
                else:
                    controladores[cid] = iniciar_background([PYTHON_EXEC, "controlador.py", str(cid)])
                    print(f" -> Controlador {cid} RELIGADO (sincronizando com o cluster...).")
            elif op == "4":
                webbrowser.open("http://127.0.0.1:8080")
            elif op == "0":
                break
            else:
                print("Opcao invalida.")
    except KeyboardInterrupt:
        pass
    finally:
        print("\nEncerrando todos os processos do Smart Pitch...")
        encerrar_processo(painel)
        encerrar_processo(sensores)
        encerrar_processo(atuadores)
        for cid in (1, 2, 3):
            encerrar_processo(controladores[cid])
        print("Sistema encerrado com sucesso.")


def main() -> None:
    if "--janelas" in sys.argv:
        iniciar_modo_janelas()
    else:
        iniciar_modo_unificado()


if __name__ == "__main__":
    main()
