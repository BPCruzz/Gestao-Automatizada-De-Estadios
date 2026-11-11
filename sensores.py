"""
Módulo de Sensores do Gramado (Smart Pitch).
Simula a leitura periódica de 3 sensores no campo:
  1. Umidade do Solo (%)
  2. Luminosidade / Radiação PAR (lux)
  3. Temperatura da Grama (°C)

Publica os dados em formato JSON no tópico MQTT para que os controladores
possam processar e tomar decisões.
"""

import json
import math
import random
import time
from datetime import datetime
import paho.mqtt.client as mqtt

from config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_KEEPALIVE,
    TOPICO_SENSORES,
)


def criar_cliente_mqtt() -> mqtt.Client:
    """Cria e configura o cliente MQTT compatível com paho-mqtt 2.x."""
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"smart_pitch_sensores_{random.randint(1000, 9999)}",
    )
    return client


def gerar_leituras(passo: int) -> dict:
    """
    Gera leituras realistas que oscilam suavemente ao longo do tempo
    para exercitar todos os cenários dos controladores (seco/úmido,
    sombra/sol, frio/ideal/quente).
    """
    # Oscilação senoidal + pequeno ruído para cruzar os limiares automaticamente
    umidade = 52.0 + 22.0 * math.sin(passo * 0.25) + random.uniform(-1.5, 1.5)
    luminosidade = 14000.0 + 8000.0 * math.cos(passo * 0.20) + random.uniform(-300, 300)
    temperatura = 21.5 + 8.0 * math.sin(passo * 0.18) + random.uniform(-0.4, 0.4)

    return {
        "umidade_solo": round(max(10.0, min(95.0, umidade)), 1),
        "luminosidade_lux": round(max(500.0, luminosidade), 0),
        "temperatura_grama": round(temperatura, 1),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }


def main() -> None:
    print("=" * 60)
    print(" [SENSORES SMART PITCH] Iniciando publicador MQTT...")
    print(f" Broker: {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT}")
    print(f" Topico: {TOPICO_SENSORES}")
    print("=" * 60)

    client = criar_cliente_mqtt()

    try:
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE)
        client.loop_start()
    except Exception as exc:
        print(f"[ERRO] Nao foi possivel conectar ao Broker MQTT: {exc}")
        print("Certifique-se de que o container Mosquitto esta rodando (docker compose up -d).")
        return

    passo = 0
    try:
        while True:
            leituras = gerar_leituras(passo)
            payload = json.dumps(leituras)
            client.publish(TOPICO_SENSORES, payload, qos=1)

            print(
                f"[{leituras['timestamp']}] Publicado -> "
                f"Umidade: {leituras['umidade_solo']}% | "
                f"Luz: {int(leituras['luminosidade_lux'])} lux | "
                f"Temp: {leituras['temperatura_grama']} °C"
            )

            passo += 1
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n[SENSORES] Encerrando sensores...")
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()

