"""
Configurações globais do sistema Smart Pitch (Gestão Automatizada de Gramado).
Centraliza endereços do Broker MQTT, tópicos Pub/Sub, portas dos objetos Pyro5
e limiares agronômicos para tomada de decisão.
"""

# =============================================================================
# 1. CONFIGURAÇÕES DO BROKER MQTT
# =============================================================================
MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_KEEPALIVE = 60

# Tópicos MQTT (Sensores publicam / Controladores e Atuadores assinam)
TOPICO_SENSORES = "estadio/gramado/sensores"
TOPICO_ATUADORES = "estadio/gramado/atuadores"

# =============================================================================
# 2. LIMIARES AGRONÔMICOS DO GRAMADO (TOMADA DE DECISÃO AUTOMÁTICA)
# =============================================================================
# Umidade do solo (%)
UMIDADE_MINIMA_IRRIGACAO = 40.0   # Abaixo de 40% -> Liga a irrigação
UMIDADE_IDEAL_PARADA = 65.0       # Acima de 65%  -> Desliga a irrigação

# Luminosidade / Radiação Fotossintética PAR (lux)
LUMINOSIDADE_MINIMA_LUX = 12000.0  # Abaixo de 12.000 lux -> Liga Grow Lights

# Temperatura da zona radicular da grama (°C)
TEMPERATURA_MINIMA_C = 16.0       # Abaixo de 16°C -> Liga aquecimento subterrâneo
TEMPERATURA_MAXIMA_C = 27.0       # Acima de 27°C  -> Liga ventilação/resfriamento

# =============================================================================
# 3. LIMITES FÍSICOS DE SEGURANÇA (SANITY CHECK CONTRA INVASÃO/ERROS)
# =============================================================================
LIMITES_FISICOS = {
    "umidade_solo": (0.0, 100.0),          # % válida entre 0 e 100
    "luminosidade_lux": (0.0, 150000.0),   # lux válido entre 0 e 150.000
    "temperatura_grama": (-10.0, 60.0),    # °C válido entre -10 e 60
}

MODOS_VALIDOS = ("AUTOMATICO", "DIA_DE_JOGO", "MANUAL")
ESTADOS_IRRIGACAO = ("LIGADO", "DESLIGADO")
ESTADOS_GROW_LIGHTS = ("LIGADO", "DESLIGADO")
ESTADOS_CLIMATIZACAO = ("AQUECENDO", "RESFRIANDO", "DESLIGADO")

# =============================================================================
# 4. ENDEREÇOS DE OBJETOS DISTRIBUÍDOS (PYRO5 SEM NAMESERVER EXTERNO)
# =============================================================================
# Usamos portas fixas em localhost para eliminar a necessidade de subir
# um processo NameServer extra do Pyro5, simplificando a execução.
HOST_PYRO = "localhost"

CONTROLADORES_CONFIG = {
    1: {"host": HOST_PYRO, "port": 9091, "obj_name": "controlador.1"},
    2: {"host": HOST_PYRO, "port": 9092, "obj_name": "controlador.2"},
    3: {"host": HOST_PYRO, "port": 9093, "obj_name": "controlador.3"},
}

MIDDLEWARE_CONFIG = {
    "host": HOST_PYRO,
    "port": 9090,
    "obj_name": "smartpitch.middleware",
}


def obter_uri_controlador(ctrl_id: int) -> str:
    """Retorna a URI Pyro5 direta para o controlador informado."""
    cfg = CONTROLADORES_CONFIG[ctrl_id]
    return f"PYRO:{cfg['obj_name']}@{cfg['host']}:{cfg['port']}"


def obter_uri_middleware() -> str:
    """Retorna a URI Pyro5 direta para o Middleware."""
    cfg = MIDDLEWARE_CONFIG
    return f"PYRO:{cfg['obj_name']}@{cfg['host']}:{cfg['port']}"

