"""
Camada local de comunicação direta Cliente <-> Controladores (Smart Pitch).
Não é um servidor intermediário: é importada diretamente pelo Cliente para
invocar métodos Pyro5 nos Controladores de Processo (portas 9091, 9092 e 9093),
aplicando tolerância a quedas (failover) e segurança contra falhas bizantinas
(Sanity Check + Votação por Maioria TMR 2 de 3).
"""

from collections import Counter
from datetime import datetime
import Pyro5.api

from config import (
    CONTROLADORES_CONFIG,
    ESTADOS_CLIMATIZACAO,
    ESTADOS_GROW_LIGHTS,
    ESTADOS_IRRIGACAO,
    MODOS_VALIDOS,
    obter_uri_controlador,
    validar_estado_plausivel,
)


class ClienteControladoresRPC:
    """Stub local que invoca métodos diretamente nas réplicas dos Controladores."""

    def __init__(self, timeout_rpc: float = 1.5):
        self.timeout_rpc = timeout_rpc

    def _assinatura_consenso(self, estado: dict) -> tuple:
        """Gera assinatura imutável do estado para votação por maioria (TMR)."""
        atuadores = estado.get("atuadores", {})
        sensores = estado.get("sensores", {})
        return (
            estado.get("modo_operacao"),
            atuadores.get("irrigacao"),
            atuadores.get("grow_lights"),
            atuadores.get("climatizacao"),
            round(float(sensores.get("umidade_solo", 0.0)), 1),
            round(float(sensores.get("temperatura_grama", 0.0)), 1),
        )

    def _resposta_comando_valida(self, resp: dict) -> bool:
        """Sanity Check para respostas de comandos remotos nos controladores."""
        if not isinstance(resp, dict) or not resp.get("sucesso"):
            return False
        atuadores = resp.get("atuadores", {})
        return (
            resp.get("modo_operacao") in MODOS_VALIDOS
            and isinstance(atuadores, dict)
            and atuadores.get("irrigacao") in ESTADOS_IRRIGACAO
            and atuadores.get("grow_lights") in ESTADOS_GROW_LIGHTS
            and atuadores.get("climatizacao") in ESTADOS_CLIMATIZACAO
        )

    def _executar_comando_em_replicas(self, fn_chamada, acao_desc: str) -> dict:
        """
        Invoca um método de comando diretamente em todos os controladores ativos,
        tolerando quedas e isolando respostas adulteradas via Sanity Check + maioria.
        """
        respostas_integras = []
        erros_validacao = []
        alertas = []

        for ctrl_id in CONTROLADORES_CONFIG:
            uri = obter_uri_controlador(ctrl_id)
            try:
                with Pyro5.api.Proxy(uri) as proxy:
                    proxy._pyroTimeout = self.timeout_rpc
                    resp = fn_chamada(proxy)

                if self._resposta_comando_valida(resp):
                    respostas_integras.append(resp)
                elif isinstance(resp, dict) and not resp.get("sucesso"):
                    erros_validacao.append(resp)
                else:
                    modo_ret = resp.get("modo_operacao") if isinstance(resp, dict) else resp
                    alertas.append(
                        f"Controlador {ctrl_id} retornou confirmacao adulterada ({modo_ret}) e foi descartado."
                    )
            except Exception:
                # Tolerância a falha por queda: prossegue para os demais controladores
                pass

        if not respostas_integras:
            if erros_validacao:
                return erros_validacao[0]
            return {
                "sucesso": False,
                "mensagem": f"Falha critica: nenhum controlador disponivel para {acao_desc}.",
            }

        votos = Counter(
            (r["modo_operacao"], tuple(sorted(r["atuadores"].items())))
            for r in respostas_integras
        )
        (modo_consenso, atuadores_tupla), num_votos = votos.most_common(1)[0]

        return {
            "sucesso": True,
            "modo_operacao": modo_consenso,
            "atuadores": dict(atuadores_tupla),
            "votos": num_votos,
            "alertas_seguranca": alertas,
        }

    def obter_visao_geral(self) -> dict:
        """
        Consulta diretamente as réplicas de controladores, tolera quedas e filtra
        controladores invadidos/com erro intermitente via Sanity Check + Votação TMR.
        """
        respostas_validas = {}
        status_controladores = {}
        alertas_seguranca = []

        for ctrl_id in CONTROLADORES_CONFIG:
            uri = obter_uri_controlador(ctrl_id)
            try:
                with Pyro5.api.Proxy(uri) as proxy:
                    proxy._pyroTimeout = self.timeout_rpc
                    estado_ctrl = proxy.obter_estado()

                plausivel, motivo = validar_estado_plausivel(estado_ctrl)
                if not plausivel:
                    status_controladores[ctrl_id] = f"INVADIDO/ERRO ({motivo})"
                    alertas_seguranca.append(
                        f"Controlador {ctrl_id} isolado pelo Sanity Check: {motivo}"
                    )
                else:
                    respostas_validas[ctrl_id] = estado_ctrl
                    status_controladores[ctrl_id] = "ONLINE (Integro)"
            except Exception:
                status_controladores[ctrl_id] = "OFFLINE (Inacessivel)"

        if not respostas_validas:
            return {
                "sucesso": False,
                "mensagem": "Nenhum controlador integro disponivel no momento.",
                "status_controladores": status_controladores,
                "alertas_seguranca": alertas_seguranca,
                "timestamp_consulta": datetime.now().strftime("%H:%M:%S"),
            }

        assinaturas = {
            ctrl_id: self._assinatura_consenso(est)
            for ctrl_id, est in respostas_validas.items()
        }
        contagem = Counter(assinaturas.values())
        assinatura_vencedora, votos_vencedores = contagem.most_common(1)[0]

        estado_consenso = None
        controladores_vencedores = []

        for ctrl_id, ass in assinaturas.items():
            if ass == assinatura_vencedora:
                controladores_vencedores.append(ctrl_id)
                if estado_consenso is None:
                    estado_consenso = respostas_validas[ctrl_id]
            else:
                status_controladores[ctrl_id] = "DIVERGENTE (Voto minoritario descartado)"
                alertas_seguranca.append(
                    f"Controlador {ctrl_id} divergiu da maioria "
                    f"(respondeu {ass[:4]}, maioria decidiu {assinatura_vencedora[:4]})"
                )

        return {
            "sucesso": True,
            "estado": estado_consenso,
            "status_controladores": status_controladores,
            "quorum": (
                f"{votos_vencedores}/{len(CONTROLADORES_CONFIG)} controladores concordam "
                f"(Ativos validos: {controladores_vencedores})"
            ),
            "alertas_seguranca": alertas_seguranca,
            "timestamp_consulta": datetime.now().strftime("%H:%M:%S"),
        }

    def definir_modo_operacao(self, novo_modo: str) -> dict:
        """Invoca diretamente definir_modo() nas réplicas ativas com votação por maioria."""
        res = self._executar_comando_em_replicas(
            lambda proxy: proxy.definir_modo(novo_modo),
            "executar definir_modo",
        )
        if res.get("sucesso"):
            res["mensagem"] = (
                f"Modo alterado para '{res['modo_operacao']}' com sucesso "
                f"(confirmado por {res['votos']} replica(s))."
            )
        return res

    def acionar_atuador(self, atuador: str, novo_estado: str) -> dict:
        """Invoca diretamente acionar_atuador_manual() nas réplicas ativas."""
        res = self._executar_comando_em_replicas(
            lambda proxy: proxy.acionar_atuador_manual(atuador, novo_estado),
            "executar o acionamento",
        )
        if res.get("sucesso"):
            res["mensagem"] = (
                f"Atuador '{atuador}' ajustado para '{novo_estado}' "
                f"(modo MANUAL, confirmado por {res['votos']} replica(s))."
            )
        return res

    def simular_invasao_controlador(self, ctrl_id: int, comprometido: bool) -> dict:
        """Ativa/desativa simulação de invasão diretamente no controlador escolhido."""
        ctrl_id = int(ctrl_id)
        if ctrl_id not in CONTROLADORES_CONFIG:
            return {"sucesso": False, "mensagem": f"Controlador {ctrl_id} inexistente."}

        uri = obter_uri_controlador(ctrl_id)
        try:
            with Pyro5.api.Proxy(uri) as proxy:
                proxy._pyroTimeout = self.timeout_rpc
                res = proxy.definir_comprometimento(comprometido)
                return {
                    "sucesso": True,
                    "mensagem": f"Controlador {ctrl_id} configurado como: {res['status']}",
                }
        except Exception as exc:
            return {
                "sucesso": False,
                "mensagem": f"Controlador {ctrl_id} esta offline ({exc}).",
            }
