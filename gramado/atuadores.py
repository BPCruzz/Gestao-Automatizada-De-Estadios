"""
Módulo de Atuadores do Gramado (Smart Pitch).
Assina o tópico de comandos no Broker MQTT e atua sobre os 3 subsistemas físicos:
  1. Sistema de Irrigação (Sprinklers) -> LIGADO / DESLIGADO
  2. Iluminação Artificial (Grow Lights) -> LIGADO / DESLIGADO
  3. Climatização Subterrânea -> AQUECENDO / RESFRIANDO / DESLIGADO

Inclui proteção contra comandos adulterados ou divergentes:
  - Sanity Check dos estados permitidos antes de processar.
  - Votação por maioria sobre janela temporal recente entre controladores ativos.
"""

from collections import Counter
import json
import random
import time
import paho.mqtt.client as mqtt

from config import (
    ESTADOS_CLIMATIZACAO,
    ESTADOS_GROW_LIGHTS,
    ESTADOS_IRRIGACAO,
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_KEEPALIVE,
    TOPICO_ATUADORES,
)

# Janela (segundos) para considerar votos recentes de cada controlador ativo
JANELA_VOTACAO_S = 10.0

# Estado local atual dos equipamentos físicos no campo
estado_fisico_atuadores = {
    "irrigacao": "DESLIGADO",
    "grow_lights": "DESLIGADO",
    "climatizacao": "DESLIGADO",
}

# Último comando válido recebido de cada controlador: {origem: (tupla_estados, timestamp)}
votos_atuadores: dict[str, tuple[tuple[str, str, str], float]] = {}


def _comando_valido(atuadores: dict) -> bool:
    """Sanity Check: garante que todos os estados pertencem ao domínio válido."""
    return (
        isinstance(atuadores, dict)
        and atuadores.get("irrigacao") in ESTADOS_IRRIGACAO
        and atuadores.get("grow_lights") in ESTADOS_GROW_LIGHTS
        and atuadores.get("climatizacao") in ESTADOS_CLIMATIZACAO
    )


def ao_conectar(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("[ATUADORES] Conectado ao Broker MQTT com sucesso!")
        client.subscribe(TOPICO_ATUADORES, qos=1)
        print(f"[ATUADORES] Assinando topico: {TOPICO_ATUADORES}\n")
    else:
        print(f"[ERRO] Falha na conexao MQTT. Codigo: {reason_code}")


def ao_receber_mensagem(client, userdata, msg):
    global estado_fisico_atuadores
    try:
        dados = json.loads(msg.payload.decode("utf-8"))
        atuadores_recebidos = dados.get("atuadores", {})
        origem = dados.get("origem", "Controlador")
        horario = dados.get("timestamp", "--:--:--")

        if not _comando_valido(atuadores_recebidos):
            print(f"[{horario}] [SEGURANCA ATUADORES] Comando invalido de {origem} bloqueado pelo Sanity Check!")
            return

        agora = time.time()
        tupla_cmd = (
            atuadores_recebidos["irrigacao"],
            atuadores_recebidos["grow_lights"],
            atuadores_recebidos["climatizacao"],
        )
        votos_atuadores[origem] = (tupla_cmd, agora)

        # Remove votos antigos de controladores que possam ter caído
        expirados = [k for k, (_, ts) in votos_atuadores.items() if agora - ts > JANELA_VOTACAO_S]
        for k in expirados:
            del votos_atuadores[k]

        contagem = Counter(cmd for cmd, _ in votos_atuadores.values())
        vencedor, num_votos = contagem.most_common(1)[0]
        total_ativos = len(votos_atuadores)

        if num_votos <= total_ativos / 2:
            print(f"[{horario}] [CONSENSO ATUADORES] Empate parcial ({num_votos}/{total_ativos}) — aguardando proximo voto...")
            return

        if tupla_cmd != vencedor:
            print(
                f"[{horario}] [SEGURANCA ATUADORES] Comando divergente de {origem} ignorado "
                f"(consenso {num_votos}/{total_ativos})"
            )
            return

        novos_estados = {
            "irrigacao": vencedor[0],
            "grow_lights": vencedor[1],
            "climatizacao": vencedor[2],
        }
        mudou = False
        for chave, novo_valor in novos_estados.items():
            if estado_fisico_atuadores.get(chave) != novo_valor:
                estado_fisico_atuadores[chave] = novo_valor
                mudou = True

        status_str = (
            f"Irrigacao: {estado_fisico_atuadores['irrigacao']} | "
            f"Grow Lights: {estado_fisico_atuadores['grow_lights']} | "
            f"Climatizacao: {estado_fisico_atuadores['climatizacao']}"
        )

        if mudou:
            print(f"[{horario}] [MUDANCA FISICA | Consenso {num_votos}/{total_ativos} via {origem}] -> {status_str}")
        else:
            print(f"[{horario}] [SINCRONIZADO | Consenso {num_votos}/{total_ativos} via {origem}] -> {status_str}")

    except Exception as exc:
        print(f"[ERRO] Mensagem MQTT invalida recebida: {exc}")


def main() -> None:
    print("=" * 60)
    print(" [ATUADORES SMART PITCH] Iniciando assinante MQTT...")
    print(f" Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    print("=" * 60)

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"smart_pitch_atuadores_{random.randint(1000, 9999)}",
    )
    client.on_connect = ao_conectar
    client.on_message = ao_receber_mensagem

    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE)
        client.loop_forever()
    except KeyboardInterrupt:
        print("\n[ATUADORES] Encerrando atuadores...")
        client.disconnect()
    except Exception as exc:
        print(f"[ERRO] Nao foi possivel conectar ao Broker MQTT: {exc}")
        print("Certifique-se de que o container Mosquitto esta rodando (docker compose up -d).")


if __name__ == "__main__":
    main()
