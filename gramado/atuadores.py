"""
Módulo de Atuadores do Gramado (Smart Pitch).
Assina o tópico de comandos no Broker MQTT e atua sobre os 3 subsistemas físicos:
  1. Sistema de Irrigação (Sprinklers) -> LIGADO / DESLIGADO
  2. Iluminação Artificial (Grow Lights) -> LIGADO / DESLIGADO
  3. Climatização Subterrânea -> AQUECENDO / RESFRIANDO / DESLIGADO
"""

import json
import random
import paho.mqtt.client as mqtt

from config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_KEEPALIVE,
    TOPICO_ATUADORES,
)

# Estado local atual dos equipamentos físicos no campo
estado_fisico_atuadores = {
    "irrigacao": "DESLIGADO",
    "grow_lights": "DESLIGADO",
    "climatizacao": "DESLIGADO",
}


def ao_conectar(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print(f"[ATUADORES] Conectado ao Broker MQTT com sucesso!")
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

        mudou = False
        for chave in ("irrigacao", "grow_lights", "climatizacao"):
            novo_valor = atuadores_recebidos.get(chave)
            if novo_valor and estado_fisico_atuadores.get(chave) != novo_valor:
                estado_fisico_atuadores[chave] = novo_valor
                mudou = True

        status_str = (
            f"Irrigacao: {estado_fisico_atuadores['irrigacao']} | "
            f"Grow Lights: {estado_fisico_atuadores['grow_lights']} | "
            f"Climatizacao: {estado_fisico_atuadores['climatizacao']}"
        )

        if mudou:
            print(f"[{horario}] [MUDANCA FISICA via {origem}] -> {status_str}")
        else:
            print(f"[{horario}] [SINCRONIZADO via {origem}]   -> {status_str}")

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

