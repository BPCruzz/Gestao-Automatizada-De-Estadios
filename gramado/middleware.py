"""
Módulo Middleware Baseado em Objetos (Smart Pitch - Gramado).
Intermedia toda a comunicação entre os Clientes e o conjunto de Controladores de Processo.

Principais responsabilidades de Sistemas Distribuídos implementadas aqui:
  1. Transparência de Localização e Replicação: O cliente chama métodos apenas no
     Middleware, sem precisar conhecer o endereço ou quantidade de controladores.
  2. Tolerância a Falhas por Queda (Crash-Fault Tolerance): Se um ou mais controladores
     caírem, o Middleware mascara a falha de rede e garante retorno positivo ao cliente
     usando as réplicas sobreviventes.
  3. Segurança e Tolerância a Falhas Bizantinas (Controlador Invadido / Erros Intermitentes):
     Combina Validação Física (Sanity Check) + Redundância Modular Tripla (TMR) com
     Votação por Maioria (Quórum 2 de 3) para descartar respostas adulteradas.
"""

from collections import Counter
from datetime import datetime
import Pyro5.api
import Pyro5.errors

from config import (
    CONTROLADORES_CONFIG,
    ESTADOS_CLIMATIZACAO,
    ESTADOS_GROW_LIGHTS,
    ESTADOS_IRRIGACAO,
    LIMITES_FISICOS,
    MIDDLEWARE_CONFIG,
    MODOS_VALIDOS,
    obter_uri_controlador,
    obter_uri_middleware,
)


@Pyro5.api.expose
class MiddlewareGramado:
    """
    Objeto distribuído central acessado pelos Clientes.
    Coordena chamadas remotas aos 3 Controladores de Processo aplicando consenso.
    """

    def __init__(self):
        self.timeout_rpc = 1.5

    # =========================================================================
    # CAMADA DE SEGURANÇA: SANITY CHECK + VOTAÇÃO POR MAIORIA (TMR)
    # =========================================================================
    def _validar_estado_plausivel(self, estado: dict) -> tuple[bool, str]:
        """
        1ª Barreira de Defesa (Sanity Check):
        Verifica se os dados retornados por um controlador respeitam os limites físicos
        e os estados válidos do domínio do gramado.
        """
        if not isinstance(estado, dict):
            return False, "Formato de resposta invalido"

        modo = estado.get("modo_operacao")
        if modo not in MODOS_VALIDOS:
            return False, f"Modo de operacao adulterado ({modo})"

        atuadores = estado.get("atuadores", {})
        if (
            atuadores.get("irrigacao") not in ESTADOS_IRRIGACAO
            or atuadores.get("grow_lights") not in ESTADOS_GROW_LIGHTS
            or atuadores.get("climatizacao") not in ESTADOS_CLIMATIZACAO
        ):
            return False, f"Estados de atuadores invalidos ({atuadores})"

        sensores = estado.get("sensores", {})
        for campo, (min_val, max_val) in LIMITES_FISICOS.items():
            valor = sensores.get(campo)
            if valor is None or not isinstance(valor, (int, float)):
                return False, f"Leitura ausente ou corrompida em '{campo}'"
            if not (min_val <= float(valor) <= max_val):
                return False, f"Valor fora dos limites fisicos em '{campo}': {valor} (esperado {min_val}..{max_val})"

        return True, "OK"

    def _assinatura_consenso(self, estado: dict) -> tuple:
        """
        Gera uma tupla imutável representando a decisão do controlador para
        permitir a votação por maioria (TMR - Triple Modular Redundancy).
        """
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

    # =========================================================================
    # MÉTODOS REMOTOS EXPOSTOS AO CLIENTE
    # =========================================================================
    def obter_visao_geral(self) -> dict:
        """
        Consulta todas as réplicas de controladores, tolera quedas (crash) e filtra
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

                plausivel, motivo = self._validar_estado_plausivel(estado_ctrl)
                if not plausivel:
                    status_controladores[ctrl_id] = f"INVADIDO/ERRO ({motivo})"
                    alertas_seguranca.append(
                        f"Controlador {ctrl_id} isolado pelo Sanity Check: {motivo}"
                    )
                    print(f"[SEGURANCA MIDDLEWARE] Controlador {ctrl_id} reprovado: {motivo}")
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
                "timestamp_middleware": datetime.now().strftime("%H:%M:%S"),
            }

        # 2ª Barreira de Defesa: Votação por Maioria (TMR) entre as respostas fisicamente válidas
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
                alerta = (
                    f"Controlador {ctrl_id} divergiu da maioria "
                    f"(respondeu {ass[:4]}, maioria decidiu {assinatura_vencedora[:4]})"
                )
                alertas_seguranca.append(alerta)
                print(f"[CONSENSO TMR] {alerta}")

        return {
            "sucesso": True,
            "estado": estado_consenso,
            "status_controladores": status_controladores,
            "quorum": f"{votos_vencedores}/{len(CONTROLADORES_CONFIG)} controladores concordam (Ativos validos: {controladores_vencedores})",
            "alertas_seguranca": alertas_seguranca,
            "timestamp_middleware": datetime.now().strftime("%H:%M:%S"),
        }

    def definir_modo_operacao(self, novo_modo: str) -> dict:
        """
        Invoca a mudança de modo (AUTOMATICO, DIA_DE_JOGO, MANUAL) em todas as réplicas
        ativas e valida o retorno por maioria, garantindo sucesso ao cliente mesmo
        que um controlador caia ou esteja invadido.
        """
        respostas_integras = []
        alertas = []

        for ctrl_id in CONTROLADORES_CONFIG:
            uri = obter_uri_controlador(ctrl_id)
            try:
                with Pyro5.api.Proxy(uri) as proxy:
                    proxy._pyroTimeout = self.timeout_rpc
                    resp = proxy.definir_modo(novo_modo)

                if not resp.get("sucesso"):
                    return resp

                modo_retornado = resp.get("modo_operacao")
                atuadores_ret = resp.get("atuadores", {})
                if (
                    modo_retornado in MODOS_VALIDOS
                    and atuadores_ret.get("irrigacao") in ESTADOS_IRRIGACAO
                ):
                    respostas_integras.append(resp)
                else:
                    alerta = f"Controlador {ctrl_id} retornou confirmacao adulterada ({modo_retornado}) e foi descartado."
                    alertas.append(alerta)
                    print(f"[SEGURANCA MIDDLEWARE] {alerta}")
            except Exception:
                # Tolerância a falha por queda: continua nas demais réplicas
                pass

        if not respostas_integras:
            return {
                "sucesso": False,
                "mensagem": "Falha critica: nenhum controlador disponivel para executar definir_modo.",
            }

        # Votação majoritária sobre o resultado da operação
        votos = Counter(
            (r["modo_operacao"], tuple(sorted(r["atuadores"].items())))
            for r in respostas_integras
        )
        (modo_consenso, atuadores_tupla), num_votos = votos.most_common(1)[0]

        print(
            f"[MIDDLEWARE] definir_modo('{novo_modo}') concluido com sucesso! "
            f"Consenso: {num_votos} replica(s) integra(s)."
        )
        return {
            "sucesso": True,
            "mensagem": f"Modo alterado para '{modo_consenso}' com sucesso (confirmado por {num_votos} replica(s)).",
            "modo_operacao": modo_consenso,
            "atuadores": dict(atuadores_tupla),
            "alertas_seguranca": alertas,
        }

    def acionar_atuador(self, atuador: str, novo_estado: str) -> dict:
        """
        Aciona manualmente um atuador (irrigacao, grow_lights, climatizacao)
        em todas as réplicas ativas, mascarando quedas e respostas corrompidas.
        """
        respostas_integras = []
        alertas = []

        for ctrl_id in CONTROLADORES_CONFIG:
            uri = obter_uri_controlador(ctrl_id)
            try:
                with Pyro5.api.Proxy(uri) as proxy:
                    proxy._pyroTimeout = self.timeout_rpc
                    resp = proxy.acionar_atuador_manual(atuador, novo_estado)

                if not resp.get("sucesso"):
                    return resp

                atuadores_ret = resp.get("atuadores", {})
                if (
                    resp.get("modo_operacao") in MODOS_VALIDOS
                    and atuadores_ret.get("irrigacao") in ESTADOS_IRRIGACAO
                    and atuadores_ret.get("grow_lights") in ESTADOS_GROW_LIGHTS
                    and atuadores_ret.get("climatizacao") in ESTADOS_CLIMATIZACAO
                ):
                    respostas_integras.append(resp)
                else:
                    alerta = f"Controlador {ctrl_id} respondeu valores invalidos ao acionar '{atuador}' e foi isolado."
                    alertas.append(alerta)
                    print(f"[SEGURANCA MIDDLEWARE] {alerta}")
            except Exception:
                pass

        if not respostas_integras:
            return {
                "sucesso": False,
                "mensagem": "Nenhum controlador disponivel para executar o acionamento.",
            }

        votos = Counter(
            tuple(sorted(r["atuadores"].items())) for r in respostas_integras
        )
        atuadores_tupla, num_votos = votos.most_common(1)[0]

        print(
            f"[MIDDLEWARE] acionar_atuador('{atuador}', '{novo_estado}') concluido! "
            f"Consenso: {num_votos} replica(s)."
        )
        return {
            "sucesso": True,
            "mensagem": (
                f"Atuador '{atuador}' ajustado para '{novo_estado}' "
                f"(modo MANUAL, confirmado por {num_votos} replica(s))."
            ),
            "atuadores": dict(atuadores_tupla),
            "alertas_seguranca": alertas,
        }

    def simular_invasao_controlador(self, ctrl_id: int, comprometido: bool) -> dict:
        """
        Método auxiliar para fins de demonstração do trabalho: ativa ou desativa
        a simulação de invasão/erro intermitente no controlador escolhido.
        """
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


def main() -> None:
    cfg = MIDDLEWARE_CONFIG
    print("=" * 68)
    print(" [MIDDLEWARE SMART PITCH] Iniciando servidor de objetos Pyro5...")
    print(f" Endpoint Middleware : {obter_uri_middleware()}")
    print(" Controladores monitorados (TMR - Quórum 2 de 3):")
    for cid in CONTROLADORES_CONFIG:
        print(f"   -> Controlador {cid}: {obter_uri_controlador(cid)}")
    print("=" * 68)

    middleware = MiddlewareGramado()
    daemon = Pyro5.api.Daemon(host=cfg["host"], port=cfg["port"])
    uri = daemon.register(middleware, objectId=cfg["obj_name"])
    print(f"[MIDDLEWARE] Pronto e aguardando chamadas remotas dos Clientes em: {uri}\n")

    try:
        daemon.requestLoop()
    except KeyboardInterrupt:
        print("\n[MIDDLEWARE] Encerrando middleware...")
    finally:
        daemon.close()


if __name__ == "__main__":
    main()

