"""
Módulo Cliente (Painel de Controle e Monitoramento do Operador - Smart Pitch).
Conecta-se exclusivamente ao Middleware via comunicação baseada em objetos (Pyro5).

Permite:
  - Visualizar em tempo real sensores, atuadores, status das réplicas e quórum TMR.
  - Acompanhar alertas de segurança caso um controlador caia ou seja invadido.
  - Alterar o modo de operação (AUTOMATICO, DIA_DE_JOGO, MANUAL).
  - Controlar manualmente cada atuador do gramado.
  - Ativar/desativar simulação de invasão (falha bizantina) em um controlador para demonstração.
"""

import os
import time
import Pyro5.api

from config import obter_uri_middleware


def limpar_tela() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def obter_proxy_middleware() -> Pyro5.api.Proxy:
    uri = obter_uri_middleware()
    proxy = Pyro5.api.Proxy(uri)
    proxy._pyroTimeout = 3.0
    return proxy


def exibir_painel(visao: dict) -> None:
    print("=" * 74)
    print("   SMART PITCH — PAINEL DO CLIENTE (GESTAO AUTOMATIZADA DE GRAMADO)")
    print("=" * 74)

    if not visao.get("sucesso"):
        print(f" [ERRO CRITICO] {visao.get('mensagem')}")
        status_ctrls = visao.get("status_controladores", {})
        for cid, st in status_ctrls.items():
            print(f"   - Controlador {cid}: {st}")
        print("=" * 74)
        return

    estado = visao["estado"]
    sensores = estado["sensores"]
    atuadores = estado["atuadores"]
    status_ctrls = visao.get("status_controladores", {})
    alertas = visao.get("alertas_seguranca", [])

    print(f" Horario Middleware : {visao.get('timestamp_middleware')} | Versao Storage Replicado: v{estado.get('versao')}")
    print(f" Modo de Operacao   : [{estado.get('modo_operacao')}]")
    print(f" Quorum Consenso TMR: {visao.get('quorum')}")
    print("-" * 74)

    print(" [STATUS DO CLUSTER DE CONTROLADORES E REPLICACAO]")
    for cid, st in status_ctrls.items():
        marcador = "[OK]" if "ONLINE" in st else "[!!]"
        print(f"   {marcador} Controlador {cid}: {st}")

    if alertas:
        print("\n [ALERTAS DE SEGURANCA / TOLERANCIA A FALHAS BIZANTINAS]")
        for alerta in alertas:
            print(f"   >>> ALERTA: {alerta}")

    print("-" * 74)
    print(" [SENSORES DO GRAMADO (MQTT -> CONTROLADORES)]")
    print(f"   * Umidade do Solo          : {sensores.get('umidade_solo')} %   (Ideal: 40% a 65%)")
    print(f"   * Luminosidade PAR         : {int(sensores.get('luminosidade_lux', 0))} lux (Minimo: 12000 lux)")
    print(f"   * Temperatura da Raiz      : {sensores.get('temperatura_grama')} °C  (Ideal: 16°C a 27°C)")
    print(f"   * Ultima Leitura Sensor    : {sensores.get('timestamp')}")

    print("-" * 74)
    print(" [ATUADORES EM CAMPO (CONTROLADORES -> MQTT)]")
    print(f"   * Sistema de Irrigacao     : [{atuadores.get('irrigacao')}]")
    print(f"   * Iluminacao (Grow Lights) : [{atuadores.get('grow_lights')}]")
    print(f"   * Climatizacao Subterranea : [{atuadores.get('climatizacao')}]")

    historico = estado.get("historico_recente", [])
    if historico:
        print("-" * 74)
        print(" [ULTIMOS EVENTOS REPLICADOS NO STORAGE]")
        for item in historico[-4:]:
            print(f"   {item}")

    print("=" * 74)


def consultar_e_mostrar() -> None:
    try:
        with obter_proxy_middleware() as mw:
            visao = mw.obter_visao_geral()
            exibir_painel(visao)
    except Exception as exc:
        print(f"\n[ERRO] Nao foi possivel comunicar com o Middleware ({obter_uri_middleware()}): {exc}")
        print("Verifique se 'python gramado/middleware.py' esta em execucao.\n")


def monitorar_tempo_real() -> None:
    """Atualiza o painel automaticamente a cada 2 segundos até Ctrl+C."""
    try:
        while True:
            limpar_tela()
            consultar_e_mostrar()
            print("\n [MONITORAMENTO EM TEMPO REAL ATIVO] Pressione Ctrl+C para voltar ao menu...")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nRetornando ao menu principal...\n")


def menu_alterar_modo() -> None:
    print("\nEscolha o Modo de Operacao do Gramado:")
    print("  [1] AUTOMATICO  (Controladores decidem sozinhos pelos sensores)")
    print("  [2] DIA_DE_JOGO (Bloqueia irrigacao e Grow Lights durante a partida)")
    print("  [3] MANUAL      (Operador controla cada atuador diretamente)")
    op = input("Opcao: ").strip()

    mapa = {"1": "AUTOMATICO", "2": "DIA_DE_JOGO", "3": "MANUAL"}
    if op not in mapa:
        print("Opcao invalida.")
        return

    try:
        with obter_proxy_middleware() as mw:
            res = mw.definir_modo_operacao(mapa[op])
            print(f"\n-> Resposta do Middleware: {res.get('mensagem')}")
            for alerta in res.get("alertas_seguranca", []):
                print(f"   [ALERTA SEGURANCA] {alerta}")
    except Exception as exc:
        print(f"[ERRO] Falha ao invocar metodo no Middleware: {exc}")


def menu_acionar_atuador() -> None:
    print("\nQual atuador deseja comandar manualmente?")
    print("  [1] Sistema de Irrigacao     (LIGADO / DESLIGADO)")
    print("  [2] Iluminacao Grow Lights   (LIGADO / DESLIGADO)")
    print("  [3] Climatizacao Subterranea (AQUECENDO / RESFRIANDO / DESLIGADO)")
    op_at = input("Escolha o atuador (1-3): ").strip()

    if op_at == "1":
        atuador = "irrigacao"
        estado = input("Digite o estado [1=LIGADO, 2=DESLIGADO]: ").strip()
        novo_estado = "LIGADO" if estado == "1" else "DESLIGADO"
    elif op_at == "2":
        atuador = "grow_lights"
        estado = input("Digite o estado [1=LIGADO, 2=DESLIGADO]: ").strip()
        novo_estado = "LIGADO" if estado == "1" else "DESLIGADO"
    elif op_at == "3":
        atuador = "climatizacao"
        estado = input("Digite o estado [1=AQUECENDO, 2=RESFRIANDO, 3=DESLIGADO]: ").strip()
        mapa_clima = {"1": "AQUECENDO", "2": "RESFRIANDO", "3": "DESLIGADO"}
        novo_estado = mapa_clima.get(estado, "DESLIGADO")
    else:
        print("Opcao invalida.")
        return

    try:
        with obter_proxy_middleware() as mw:
            res = mw.acionar_atuador(atuador, novo_estado)
            print(f"\n-> Resposta do Middleware: {res.get('mensagem')}")
            for alerta in res.get("alertas_seguranca", []):
                print(f"   [ALERTA SEGURANCA] {alerta}")
    except Exception as exc:
        print(f"[ERRO] Falha ao invocar metodo no Middleware: {exc}")


def menu_simular_seguranca() -> None:
    print("\n=== SIMULACAO DE SEGURANCA / FALHA BIZANTINA (CONTROLADOR INVADIDO) ===")
    ctrl_id = input("Qual Controlador (1, 2 ou 3) deseja alterar? ").strip()
    if ctrl_id not in ("1", "2", "3"):
        print("Controlador invalido.")
        return

    print("  [1] SIMULAR INVASAO / ERRO (Controlador passa a responder valores falsos)")
    print("  [2] RESTAURAR INTEGRIDADE  (Controlador volta a responder normalmente)")
    acao = input("Escolha (1 ou 2): ").strip()
    comprometido = acao == "1"

    try:
        with obter_proxy_middleware() as mw:
            res = mw.simular_invasao_controlador(int(ctrl_id), comprometido)
            print(f"\n-> {res.get('mensagem')}")
    except Exception as exc:
        print(f"[ERRO] Falha ao comunicar com o Middleware: {exc}")


def main() -> None:
    limpar_tela()
    consultar_e_mostrar()

    while True:
        print("\nACOES DISPONIVEIS NO CLIENTE:")
        print("  [1] Atualizar painel agora")
        print("  [2] Monitorar em tempo real (atualizacao automatica a cada 2s)")
        print("  [3] Alterar Modo de Operacao (AUTOMATICO / DIA_DE_JOGO / MANUAL)")
        print("  [4] Acionar Atuador Manualmente (Irrigacao / Grow Lights / Climatizacao)")
        print("  [5] [Teste SD] Simular Invasao/Falha Bizantina em um Controlador")
        print("  [0] Sair")

        escolha = input("\nEscolha uma opcao: ").strip()

        if escolha == "1":
            limpar_tela()
            consultar_e_mostrar()
        elif escolha == "2":
            monitorar_tempo_real()
        elif escolha == "3":
            menu_alterar_modo()
            consultar_e_mostrar()
        elif escolha == "4":
            menu_acionar_atuador()
            consultar_e_mostrar()
        elif escolha == "5":
            menu_simular_seguranca()
            consultar_e_mostrar()
        elif escolha == "0":
            print("Encerrando cliente Smart Pitch...")
            break
        else:
            print("Opcao invalida. Tente novamente.")


if __name__ == "__main__":
    main()

