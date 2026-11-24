"""
Módulo Controlador de Processo (Smart Pitch - Gramado).
Responsabilidades na Arquitetura de Sistemas Distribuídos:
  1. Assina o tópico de sensores no Broker MQTT, valida limites físicos e processa decisões.
  2. Publica comandos de atuação no Broker MQTT quando o estado dos atuadores muda.
  3. Mantém armazenamento persistente em banco PostgreSQL dedicado por réplica.
  4. Replica e sincroniza o estado armazenado com os demais controladores via Pyro5.
  5. Expõe métodos remotos baseados em objetos (Pyro5) diretamente para os Clientes.
  6. Permite simular comportamento bizantino (invasão/valores adulterados) para testes de segurança.

Uso:
  python gramado/controlador.py 1
  python gramado/controlador.py 2
  python gramado/controlador.py 3
"""

import copy
import json
import random
import sys
import threading
from datetime import datetime
import paho.mqtt.client as mqtt
import Pyro5.api
import Pyro5.errors

from config import (
    CONTROLADORES_CONFIG,
    DATABASES_CONFIG,
    ESTADOS_CLIMATIZACAO,
    ESTADOS_GROW_LIGHTS,
    ESTADOS_IRRIGACAO,
    LUMINOSIDADE_MINIMA_LUX,
    MODOS_VALIDOS,
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_KEEPALIVE,
    TEMPERATURA_MAXIMA_C,
    TEMPERATURA_MINIMA_C,
    TOPICO_ATUADORES,
    TOPICO_SENSORES,
    UMIDADE_IDEAL_PARADA,
    UMIDADE_MINIMA_IRRIGACAO,
    obter_uri_controlador,
    validar_estado_plausivel,
    validar_leituras_sensores,
)
from storage_db import StoragePostgres


@Pyro5.api.expose
class ControladorGramado:
    """Objeto distribuído que gerencia o processo do gramado e replica seu armazenamento."""

    def __init__(self, ctrl_id: int):
        self.ctrl_id = ctrl_id
        self.lock = threading.Lock()
        self.comprometido = False  # Flag para simular invasão / falha bizantina
        self.storage = StoragePostgres(self.ctrl_id)

        # Estado padrão inicial do controlador
        self.estado = {
            "controlador_id": self.ctrl_id,
            "versao": 0,
            "modo_operacao": "AUTOMATICO",
            "sensores": {
                "umidade_solo": 50.0,
                "luminosidade_lux": 15000.0,
                "temperatura_grama": 22.0,
                "timestamp": "--:--:--",
            },
            "atuadores": {
                "irrigacao": "DESLIGADO",
                "grow_lights": "DESLIGADO",
                "climatizacao": "DESLIGADO",
            },
            "ultima_atualizacao": datetime.now().strftime("%H:%M:%S"),
            "historico_recente": [],
        }

        self._carregar_storage_local()
        self.mqtt_client = self._iniciar_mqtt()

    # =========================================================================
    # ARMAZENAMENTO POSTGRESQL E REPLICAÇÃO ENTRE CONTROLADORES
    # =========================================================================
    def _carregar_storage_local(self) -> None:
        """Carrega o estado do PostgreSQL desta réplica ou inicializa o registro."""
        dados = self.storage.carregar_estado()
        if dados:
            plausivel, motivo = validar_estado_plausivel(dados)
            if plausivel:
                self.estado.update(dados)
                self.estado["controlador_id"] = self.ctrl_id
                db_name = DATABASES_CONFIG[self.ctrl_id]["dbname"]
                print(f"[CTRL {self.ctrl_id}] Estado carregado do PostgreSQL '{db_name}' (v{self.estado['versao']})")
                return
            print(f"[CTRL {self.ctrl_id}] Estado salvo descartado pelo Sanity Check: {motivo}")

        self._salvar_storage_local()

    def _salvar_storage_local(self) -> None:
        """Persiste o estado atual no banco PostgreSQL dedicado desta réplica."""
        self.storage.salvar_estado(self.estado)

    def _registrar_evento(self, descricao: str) -> None:
        """Adiciona um evento ao histórico replicado (mantendo os últimos 10 registros)."""
        evento = f"[{datetime.now().strftime('%H:%M:%S')}] {descricao}"
        historico = self.estado.get("historico_recente", [])
        historico.append(evento)
        self.estado["historico_recente"] = historico[-10:]

    def _aplicar_estado_remoto(self, estado_remoto: dict) -> None:
        """Sobrescreve o estado local com uma réplica validada e persiste no banco."""
        self.estado["versao"] = estado_remoto["versao"]
        self.estado["modo_operacao"] = estado_remoto["modo_operacao"]
        self.estado["sensores"] = copy.deepcopy(estado_remoto["sensores"])
        self.estado["atuadores"] = copy.deepcopy(estado_remoto["atuadores"])
        self.estado["ultima_atualizacao"] = estado_remoto["ultima_atualizacao"]
        self.estado["historico_recente"] = list(estado_remoto.get("historico_recente", []))
        self._salvar_storage_local()

    def _propagar_replicacao(self) -> None:
        """Envia o estado atualizado para as demais réplicas de controladores."""
        pacote = copy.deepcopy(self.estado)
        for outro_id in CONTROLADORES_CONFIG:
            if outro_id == self.ctrl_id:
                continue
            uri = obter_uri_controlador(outro_id)
            try:
                with Pyro5.api.Proxy(uri) as proxy:
                    proxy._pyroTimeout = 1.0
                    proxy.receber_replicacao(pacote)
            except Exception:
                # Se a réplica estiver desligada, ignora silenciosamente (tolerância a falhas)
                pass

    def sincronizar_ao_iniciar(self) -> None:
        """Ao subir, consulta réplicas ativas íntegras para recuperar o estado mais recente."""
        melhor_estado = None
        melhor_origem = None
        maior_versao = self.estado.get("versao", 0)

        for outro_id in CONTROLADORES_CONFIG:
            if outro_id == self.ctrl_id:
                continue
            uri = obter_uri_controlador(outro_id)
            try:
                with Pyro5.api.Proxy(uri) as proxy:
                    proxy._pyroTimeout = 1.0
                    estado_remoto = proxy.obter_estado_interno()

                plausivel, _ = validar_estado_plausivel(estado_remoto)
                if not plausivel:
                    continue

                versao_remota = estado_remoto.get("versao", 0)
                if versao_remota > maior_versao:
                    maior_versao = versao_remota
                    melhor_estado = estado_remoto
                    melhor_origem = outro_id
            except Exception:
                pass

        if melhor_estado is not None:
            with self.lock:
                self._aplicar_estado_remoto(melhor_estado)
            print(
                f"[CTRL {self.ctrl_id}] Sincronizado com Controlador {melhor_origem} "
                f"(versao {self.estado['versao']})"
            )

    # =========================================================================
    # INTEGRAÇÃO MQTT (SENSORES E ATUADORES)
    # =========================================================================
    def _iniciar_mqtt(self) -> mqtt.Client:
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"smart_pitch_ctrl_{self.ctrl_id}_{random.randint(1000, 9999)}",
        )
        client.on_connect = self._ao_conectar_mqtt
        client.on_message = self._ao_receber_sensor_mqtt

        try:
            client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE)
            client.loop_start()
        except Exception as exc:
            print(f"[CTRL {self.ctrl_id}] Aviso: Broker MQTT indisponivel no momento ({exc})")
        return client

    def _ao_conectar_mqtt(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code == 0:
            client.subscribe(TOPICO_SENSORES, qos=1)
            print(f"[CTRL {self.ctrl_id}] Conectado ao MQTT e assinando '{TOPICO_SENSORES}'")

    def _ao_receber_sensor_mqtt(self, client, userdata, msg) -> None:
        """Recebe leituras dos sensores, valida limites físicos e executa a tomada de decisão."""
        try:
            leituras = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            return

        plausivel, motivo = validar_leituras_sensores(leituras)
        if not plausivel:
            print(f"[CTRL {self.ctrl_id}] Leitura MQTT rejeitada pelo Sanity Check: {motivo}")
            return

        with self.lock:
            self.estado["sensores"] = {
                "umidade_solo": float(leituras["umidade_solo"]),
                "luminosidade_lux": float(leituras["luminosidade_lux"]),
                "temperatura_grama": float(leituras["temperatura_grama"]),
                "timestamp": leituras.get("timestamp", datetime.now().strftime("%H:%M:%S")),
            }

            atuadores_antes = copy.deepcopy(self.estado["atuadores"])
            self._aplicar_regras_decisao()
            atuadores_depois = self.estado["atuadores"]

            self.estado["versao"] += 1
            self.estado["ultima_atualizacao"] = datetime.now().strftime("%H:%M:%S")

            mudou_atuador = atuadores_antes != atuadores_depois
            if mudou_atuador:
                self._registrar_evento(
                    f"Decisao automatica ({self.estado['modo_operacao']}): "
                    f"Irrig={atuadores_depois['irrigacao']}, "
                    f"Luz={atuadores_depois['grow_lights']}, "
                    f"Clima={atuadores_depois['climatizacao']}"
                )
                self._publicar_comando_atuadores()

            self._salvar_storage_local()

        status_comprometido = " [MODO INVADIDO/ADULTERADO ATIVO]" if self.comprometido else ""
        print(
            f"[CTRL {self.ctrl_id}]{status_comprometido} Sensores: "
            f"Umid={self.estado['sensores']['umidade_solo']}% | "
            f"Luz={int(self.estado['sensores']['luminosidade_lux'])} lux | "
            f"Temp={self.estado['sensores']['temperatura_grama']}°C -> "
            f"Atuadores: {self.estado['atuadores']}"
        )

    def _aplicar_regras_decisao(self) -> None:
        """
        Lógica de tomada de decisão sobre o gramado (Smart Pitch) conforme o modo:
          - AUTOMATICO: avalia sensores de umidade, luz e temperatura.
          - DIA_DE_JOGO: trava irrigação e grow lights desligados durante a partida;
                         mantém apenas climatização subterrânea da raiz.
          - MANUAL: preserva os comandos definidos diretamente pelo operador.
        """
        modo = self.estado["modo_operacao"]
        umidade = self.estado["sensores"]["umidade_solo"]
        luz = self.estado["sensores"]["luminosidade_lux"]
        temp = self.estado["sensores"]["temperatura_grama"]

        if modo == "MANUAL":
            return

        # 1. Decisão de Climatização Subterrânea (ativa tanto em AUTOMATICO quanto em DIA_DE_JOGO)
        if temp < TEMPERATURA_MINIMA_C:
            self.estado["atuadores"]["climatizacao"] = "AQUECENDO"
        elif temp > TEMPERATURA_MAXIMA_C:
            self.estado["atuadores"]["climatizacao"] = "RESFRIANDO"
        else:
            self.estado["atuadores"]["climatizacao"] = "DESLIGADO"

        # 2. Restrição de segurança em DIA_DE_JOGO
        if modo == "DIA_DE_JOGO":
            self.estado["atuadores"]["irrigacao"] = "DESLIGADO"
            self.estado["atuadores"]["grow_lights"] = "DESLIGADO"
            return

        # 3. Modo AUTOMATICO: Irrigação (com histerese entre 40% e 65%) e Grow Lights
        if umidade < UMIDADE_MINIMA_IRRIGACAO:
            self.estado["atuadores"]["irrigacao"] = "LIGADO"
        elif umidade > UMIDADE_IDEAL_PARADA:
            self.estado["atuadores"]["irrigacao"] = "DESLIGADO"

        if luz < LUMINOSIDADE_MINIMA_LUX:
            self.estado["atuadores"]["grow_lights"] = "LIGADO"
        else:
            self.estado["atuadores"]["grow_lights"] = "DESLIGADO"

    def _publicar_comando_atuadores(self) -> None:
        """Publica o estado dos atuadores no tópico MQTT."""
        payload = {
            "origem": f"Controlador {self.ctrl_id}",
            "modo_operacao": self.estado["modo_operacao"],
            "atuadores": self.estado["atuadores"],
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
        try:
            self.mqtt_client.publish(TOPICO_ATUADORES, json.dumps(payload), qos=1)
        except Exception as exc:
            print(f"[CTRL {self.ctrl_id}] Erro ao publicar nos atuadores: {exc}")

    # =========================================================================
    # MÉTODOS REMOTOS (PYRO5) CHAMADOS PELOS CLIENTES OU OUTRAS RÉPLICAS
    # =========================================================================
    def obter_estado_interno(self) -> dict:
        """Usado para sincronização inicial entre réplicas."""
        with self.lock:
            if self.comprometido:
                return self._montar_resposta_comprometida()
            return copy.deepcopy(self.estado)

    def receber_replicacao(self, estado_remoto: dict) -> bool:
        """Recebe atualização de estado enviada por outro controlador, valida e grava no PostgreSQL."""
        plausivel, motivo = validar_estado_plausivel(estado_remoto)
        if not plausivel:
            print(f"[CTRL {self.ctrl_id}] Replicacao rejeitada pelo Sanity Check: {motivo}")
            return False

        with self.lock:
            if estado_remoto.get("versao", 0) >= self.estado.get("versao", 0):
                self._aplicar_estado_remoto(estado_remoto)
                return True
        return False

    def _montar_resposta_comprometida(self) -> dict:
        """Simula resposta adulterada/mentirosa sem corromper o banco de dados íntegro."""
        resposta = copy.deepcopy(self.estado)
        resposta["comprometido_simulado"] = True
        resposta["modo_operacao"] = "MANUAL"
        resposta["sensores"]["umidade_solo"] = 999.9      # Valor fisicamente absurdo
        resposta["sensores"]["temperatura_grama"] = -45.0  # Valor adulterado
        resposta["atuadores"]["irrigacao"] = "LIGADO"
        resposta["atuadores"]["grow_lights"] = "LIGADO"
        resposta["atuadores"]["climatizacao"] = "AQUECENDO"
        return resposta

    def obter_estado(self) -> dict:
        """
        Retorna o estado atual do gramado diretamente para o Cliente.
        Se este controlador estiver marcado como 'comprometido' (simulando invasão
        ou falha bizantina), retorna valores adulterados para testar a segurança.
        """
        with self.lock:
            if self.comprometido:
                return self._montar_resposta_comprometida()

            resposta = copy.deepcopy(self.estado)
            resposta["comprometido_simulado"] = False
            return resposta

    def definir_modo(self, novo_modo: str) -> dict:
        """Altera o modo de operação (AUTOMATICO, DIA_DE_JOGO, MANUAL) e replica."""
        novo_modo = novo_modo.upper().strip()
        if novo_modo not in MODOS_VALIDOS:
            return {"sucesso": False, "mensagem": f"Modo invalido: {novo_modo}"}

        if self.comprometido:
            return {
                "sucesso": True,
                "controlador_id": self.ctrl_id,
                "modo_operacao": "MODO_HACKED",
                "atuadores": {"irrigacao": "ERRO", "grow_lights": "ERRO", "climatizacao": "ERRO"},
            }

        with self.lock:
            self.estado["modo_operacao"] = novo_modo
            self._aplicar_regras_decisao()
            self.estado["versao"] += 1
            self.estado["ultima_atualizacao"] = datetime.now().strftime("%H:%M:%S")
            self._registrar_evento(f"Modo alterado pelo Cliente para {novo_modo}")
            self._salvar_storage_local()
            self._publicar_comando_atuadores()

        self._propagar_replicacao()

        return {
            "sucesso": True,
            "controlador_id": self.ctrl_id,
            "modo_operacao": self.estado["modo_operacao"],
            "atuadores": copy.deepcopy(self.estado["atuadores"]),
        }

    def acionar_atuador_manual(self, atuador: str, novo_estado: str) -> dict:
        """
        Permite ao cliente controlar manualmente um atuador específico.
        Coloca automaticamente o sistema em modo MANUAL e replica a decisão.
        """
        atuador = atuador.lower().strip()
        novo_estado = novo_estado.upper().strip()

        validacoes = {
            "irrigacao": ESTADOS_IRRIGACAO,
            "grow_lights": ESTADOS_GROW_LIGHTS,
            "climatizacao": ESTADOS_CLIMATIZACAO,
        }
        if atuador not in validacoes or novo_estado not in validacoes[atuador]:
            return {
                "sucesso": False,
                "mensagem": f"Comando invalido ({atuador}={novo_estado})",
            }

        if self.comprometido:
            return {
                "sucesso": True,
                "controlador_id": self.ctrl_id,
                "modo_operacao": "MODO_HACKED",
                "atuadores": {"irrigacao": "INVADIDO", "grow_lights": "INVADIDO", "climatizacao": "INVADIDO"},
            }

        with self.lock:
            self.estado["modo_operacao"] = "MANUAL"
            self.estado["atuadores"][atuador] = novo_estado
            self.estado["versao"] += 1
            self.estado["ultima_atualizacao"] = datetime.now().strftime("%H:%M:%S")
            self._registrar_evento(f"Comando manual: {atuador} -> {novo_estado}")
            self._salvar_storage_local()
            self._publicar_comando_atuadores()

        self._propagar_replicacao()

        return {
            "sucesso": True,
            "controlador_id": self.ctrl_id,
            "modo_operacao": self.estado["modo_operacao"],
            "atuadores": copy.deepcopy(self.estado["atuadores"]),
        }

    def definir_comprometimento(self, ativo: bool) -> dict:
        """
        Método didático para ativar/desativar a simulação de invasão (falha bizantina)
        neste controlador durante a apresentação do trabalho.
        """
        with self.lock:
            self.comprometido = bool(ativo)
            status = "COMPROMETIDO (Simulando Invasao/Erro)" if self.comprometido else "INTEGRO (Normal)"
            print(f"\n[ALERTA DE SIMULACAO] Controlador {self.ctrl_id} agora esta: {status}\n")
            return {
                "controlador_id": self.ctrl_id,
                "comprometido": self.comprometido,
                "status": status,
            }


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in ("1", "2", "3"):
        print("Uso correto: python gramado/controlador.py <ID_DO_CONTROLADOR>")
        print("Exemplo:     python gramado/controlador.py 1   (opcoes validas: 1, 2 ou 3)")
        sys.exit(1)

    ctrl_id = int(sys.argv[1])
    cfg = CONTROLADORES_CONFIG[ctrl_id]
    db_cfg = DATABASES_CONFIG[ctrl_id]

    print("=" * 65)
    print(f" [CONTROLADOR DE PROCESSO #{ctrl_id}] Iniciando no Smart Pitch...")
    print(f" Endpoint Pyro5 : {obter_uri_controlador(ctrl_id)}")
    print(f" Banco Postgres : {db_cfg['dbname']} ({db_cfg['host']}:{db_cfg['port']})")
    print("=" * 65)

    controlador = ControladorGramado(ctrl_id)
    controlador.sincronizar_ao_iniciar()

    daemon = Pyro5.api.Daemon(host=cfg["host"], port=cfg["port"])
    uri = daemon.register(controlador, objectId=cfg["obj_name"])
    print(f"[CTRL {ctrl_id}] Objeto remoto registrado com sucesso: {uri}\n")

    try:
        daemon.requestLoop()
    except KeyboardInterrupt:
        print(f"\n[CTRL {ctrl_id}] Encerrando controlador...")
    finally:
        controlador.mqtt_client.loop_stop()
        controlador.mqtt_client.disconnect()
        daemon.close()


if __name__ == "__main__":
    main()
