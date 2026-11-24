"""
Configurações do subsistema Smart Pitch (Módulo Gramado).
Centraliza endereços do Broker MQTT, tópicos Pub/Sub, portas dos objetos Pyro5
e limiares agronômicos para tomada de decisão.
"""

from pathlib import Path

# Diretório base do módulo gramado (onde os arquivos storage_*.json serão salvos)
DIRETORIO_GRAMADO = Path(__file__).resolve().parent
DIRETORIO_STORAGE = DIRETORIO_GRAMADO / "storage"

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
    1: {"host": HOST_PYRO, "port": 9091, "obj_name": "gramado.controlador.1"},
    2: {"host": HOST_PYRO, "port": 9092, "obj_name": "gramado.controlador.2"},
    3: {"host": HOST_PYRO, "port": 9093, "obj_name": "gramado.controlador.3"},
}


def obter_uri_controlador(ctrl_id: int) -> str:
    """Retorna a URI Pyro5 direta para o controlador informado."""
    cfg = CONTROLADORES_CONFIG[ctrl_id]
    return f"PYRO:{cfg['obj_name']}@{cfg['host']}:{cfg['port']}"


# =============================================================================
# 5. CONFIGURAÇÕES DOS BANCOS DE DADOS POSTGRESQL (1 BANCO POR CONTROLADOR)
# =============================================================================
DATABASES_CONFIG = {
    1: {
        "host": "localhost",
        "port": 5432,
        "dbname": "smart_pitch_1",
        "user": "smart_pitch",
        "password": "smart_pitch",
    },
    2: {
        "host": "localhost",
        "port": 5433,
        "dbname": "smart_pitch_2",
        "user": "smart_pitch",
        "password": "smart_pitch",
    },
    3: {
        "host": "localhost",
        "port": 5434,
        "dbname": "smart_pitch_3",
        "user": "smart_pitch",
        "password": "smart_pitch",
    },
}


def obter_dsn_banco(ctrl_id: int) -> str:
    """Retorna a string de conexão (DSN) PostgreSQL para o controlador informado."""
    cfg = DATABASES_CONFIG[ctrl_id]
    return (
        f"host={cfg['host']} port={cfg['port']} dbname={cfg['dbname']} "
        f"user={cfg['user']} password={cfg['password']}"
    )


def validar_leituras_sensores(sensores: dict) -> tuple[bool, str]:
    """Valida se as leituras de sensores estão dentro dos limites físicos reais."""
    if not isinstance(sensores, dict):
        return False, "Formato de sensores invalido"

    for campo, (min_val, max_val) in LIMITES_FISICOS.items():
        valor = sensores.get(campo)
        if valor is None or isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return False, f"Leitura ausente ou corrompida em '{campo}'"
        if not (min_val <= float(valor) <= max_val):
            return False, f"Valor fora dos limites fisicos em '{campo}': {valor} (esperado {min_val}..{max_val})"

    return True, "OK"


def validar_estado_plausivel(estado: dict) -> tuple[bool, str]:
    """
    Sanity Check: verifica se modo, atuadores e sensores de um estado
    respeitam as regras de domínio e limites físicos do Smart Pitch.
    """
    if not isinstance(estado, dict):
        return False, "Formato de resposta invalido"

    modo = estado.get("modo_operacao")
    if modo not in MODOS_VALIDOS:
        return False, f"Modo de operacao adulterado ({modo})"

    atuadores = estado.get("atuadores", {})
    if (
        not isinstance(atuadores, dict)
        or atuadores.get("irrigacao") not in ESTADOS_IRRIGACAO
        or atuadores.get("grow_lights") not in ESTADOS_GROW_LIGHTS
        or atuadores.get("climatizacao") not in ESTADOS_CLIMATIZACAO
    ):
        return False, f"Estados de atuadores invalidos ({atuadores})"

    return validar_leituras_sensores(estado.get("sensores", {}))

