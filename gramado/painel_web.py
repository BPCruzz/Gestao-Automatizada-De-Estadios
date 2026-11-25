"""
Painel Web Estilo Terminal do Cliente (Smart Pitch - Gramado).
Interface simples com fundo escuro que aproveita toda a tela para centralizar
as informações do sistema distribuído.

Conecta-se diretamente aos Controladores de Processo via ClienteControladoresRPC
(Pyro5 nas portas 9091, 9092 e 9093), sem servidor intermediário.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import webbrowser

from cliente_rpc import ClienteControladoresRPC
from config import CONTROLADORES_CONFIG, DATABASES_CONFIG


PAINEL_HOST = "127.0.0.1"
PAINEL_PORT = 8080

rpc = ClienteControladoresRPC()


HTML_PAINEL = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Smart Pitch // Terminal</title>
  <style>
    :root {
      --bg: #070a08;
      --panel: #0d130f;
      --panel-alt: #0a0f0c;
      --border: #1d2d22;
      --text: #dce8e0;
      --muted: #7f9688;
      --green: #22c55e;
      --amber: #f59e0b;
      --red: #ef4444;
      --cyan: #38bdf8;
    }
    * { box-sizing: border-box; }
    html, body {
      height: 100%;
      margin: 0;
      padding: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Consolas, "Courier New", monospace;
      font-size: 14px;
      line-height: 1.45;
    }
    .wrap {
      width: 100%;
      min-height: 100vh;
      padding: 16px 20px;
      display: grid;
      grid-template-rows: auto auto auto 1fr;
      gap: 14px;
    }
    .box {
      background: var(--panel);
      border: 1px solid var(--border);
      padding: 16px 18px;
      display: flex;
      flex-direction: column;
    }
    .header {
      flex-direction: row;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      border-left: 4px solid var(--green);
      padding: 14px 18px;
    }
    .title {
      font-size: 18px;
      font-weight: bold;
      color: var(--green);
      letter-spacing: 0.6px;
    }
    .meta {
      color: var(--muted);
      font-size: 13px;
    }
    .header-badges {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }
    .pill {
      background: var(--panel-alt);
      border: 1px solid var(--border);
      padding: 6px 12px;
      font-size: 13px;
    }
    .grid-top {
      display: grid;
      grid-template-columns: repeat(3, minmax(300px, 1fr));
      gap: 14px;
    }
    .grid-bottom {
      display: grid;
      grid-template-columns: 1.6fr 1fr;
      gap: 14px;
      min-height: 220px;
    }
    @media (max-width: 1100px) {
      .grid-top { grid-template-columns: 1fr; }
      .grid-bottom { grid-template-columns: 1fr; }
    }
    h2 {
      margin: 0 0 12px 0;
      font-size: 13px;
      color: var(--cyan);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      border-bottom: 1px dashed var(--border);
      padding-bottom: 8px;
    }
    .sensor-card {
      padding: 10px 0;
      border-bottom: 1px dotted #17231b;
    }
    .sensor-card:last-child { border-bottom: none; }
    .sensor-head {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 6px;
    }
    .sensor-val {
      font-size: 20px;
      font-weight: bold;
      color: var(--green);
    }
    .bar-track {
      width: 100%;
      height: 8px;
      background: #070b08;
      border: 1px solid var(--border);
      overflow: hidden;
    }
    .bar-fill {
      height: 100%;
      background: var(--green);
      transition: width 0.3s ease;
    }
    .row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px dotted #17231b;
      gap: 8px;
    }
    .row:last-child { border-bottom: none; }
    .val { font-weight: bold; }
    .ok { color: var(--green); }
    .warn { color: var(--amber); }
    .err { color: var(--red); }
    .alert-box {
      border: 1px solid var(--red);
      background: #1a0d0e;
      color: #fca5a5;
      padding: 10px 16px;
      display: none;
    }
    .btns {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }
    button {
      background: #121b15;
      color: var(--text);
      border: 1px solid var(--border);
      padding: 7px 12px;
      font-family: inherit;
      font-size: 12px;
      cursor: pointer;
    }
    button:hover {
      border-color: var(--green);
      color: var(--green);
    }
    button.active {
      border-color: var(--green);
      background: #132a1b;
      color: var(--green);
      font-weight: bold;
    }
    button.danger {
      border-color: #5c2020;
      color: #fca5a5;
    }
    button.danger:hover {
      border-color: var(--red);
      color: var(--red);
    }
    .ctrl-item {
      padding: 10px 0;
      border-bottom: 1px dotted #17231b;
    }
    .ctrl-item:last-child { border-bottom: none; }
    .ctrl-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .ctrl-sub {
      color: var(--muted);
      font-size: 12px;
      margin-top: 4px;
    }
    .logs {
      margin: 0;
      padding: 0;
      list-style: none;
      font-size: 13px;
      color: var(--text);
      overflow-y: auto;
      flex: 1;
    }
    .logs li {
      padding: 5px 0;
      border-bottom: 1px dotted #141f18;
    }
    .logs li:last-child { border-bottom: none; }
    .rules-list {
      margin: 0;
      padding: 0;
      list-style: none;
      font-size: 13px;
      color: var(--muted);
    }
    .rules-list li {
      padding: 6px 0;
      border-bottom: 1px dotted #141f18;
      display: flex;
      justify-content: space-between;
      gap: 8px;
    }
    .rules-list li:last-child { border-bottom: none; }
    .feedback {
      font-size: 13px;
      color: var(--green);
      min-height: 18px;
      padding: 0 2px;
    }
    .state-badge {
      padding: 3px 8px;
      border: 1px solid var(--border);
      background: var(--panel-alt);
      font-size: 13px;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="box header">
      <div>
        <div class="title">$ SMART_PITCH // PAINEL CENTRALIZADO DO GRAMADO</div>
        <div class="meta" id="meta-info">Conectando aos controladores via Pyro5...</div>
      </div>
      <div class="header-badges">
        <div class="pill">MODO: <span id="modo-atual" class="val ok">--</span></div>
        <div class="pill">QUORUM TMR: <span id="quorum-atual" class="val">--</span></div>
        <div class="pill">SYNC: <span class="val ok">LIVE 2s</span></div>
      </div>
    </div>

    <div class="alert-box" id="alert-box"></div>
    <div class="feedback" id="feedback">&gt; Aguardando comandos do operador...</div>

    <div class="grid-top">
      <div class="box">
        <h2>[1] Cluster de Controladores &amp; PostgreSQL</h2>
        <div id="lista-controladores">Carregando...</div>
      </div>

      <div class="box">
        <h2>[2] Sensores do Gramado (MQTT &rarr; Controladores)</h2>
        <div class="sensor-card">
          <div class="sensor-head">
            <span>Umidade do Solo <span class="meta">(Ideal 40-65%)</span></span>
            <span class="sensor-val" id="s-umidade">--</span>
          </div>
          <div class="bar-track"><div class="bar-fill" id="bar-umidade" style="width: 0%"></div></div>
        </div>
        <div class="sensor-card">
          <div class="sensor-head">
            <span>Luminosidade PAR <span class="meta">(Min 12000 lux)</span></span>
            <span class="sensor-val" id="s-luz">--</span>
          </div>
          <div class="bar-track"><div class="bar-fill" id="bar-luz" style="width: 0%"></div></div>
        </div>
        <div class="sensor-card">
          <div class="sensor-head">
            <span>Temperatura Raiz <span class="meta">(Ideal 16-27 °C)</span></span>
            <span class="sensor-val" id="s-temp">--</span>
          </div>
          <div class="bar-track"><div class="bar-fill" id="bar-temp" style="width: 0%"></div></div>
        </div>
        <div class="row" style="margin-top: auto;">
          <span class="meta">Ultima Leitura MQTT</span>
          <span class="val" id="s-ts">--:--:--</span>
        </div>
      </div>

      <div class="box">
        <h2>[3] Atuadores em Campo &amp; Comandos Diretos</h2>
        <div class="row"><span>Sistema de Irrigacao</span><span class="val state-badge" id="a-irrig">--</span></div>
        <div class="row"><span>Iluminacao (Grow Lights)</span><span class="val state-badge" id="a-luz">--</span></div>
        <div class="row"><span>Climatizacao Subterranea</span><span class="val state-badge" id="a-clima">--</span></div>

        <div style="margin-top: 14px;">
          <div class="meta">Alterar Modo de Operacao:</div>
          <div class="btns">
            <button id="btn-modo-AUTOMATICO" onclick="definirModo('AUTOMATICO')">AUTOMATICO</button>
            <button id="btn-modo-DIA_DE_JOGO" onclick="definirModo('DIA_DE_JOGO')">DIA_DE_JOGO</button>
            <button id="btn-modo-MANUAL" onclick="definirModo('MANUAL')">MANUAL</button>
          </div>
        </div>

        <div style="margin-top: 14px;">
          <div class="meta">Acionamento Manual de Atuadores:</div>
          <div class="btns">
            <button onclick="acionar('irrigacao', 'LIGADO')">Irrig: ON</button>
            <button onclick="acionar('irrigacao', 'DESLIGADO')">Irrig: OFF</button>
            <button onclick="acionar('grow_lights', 'LIGADO')">Luz: ON</button>
            <button onclick="acionar('grow_lights', 'DESLIGADO')">Luz: OFF</button>
            <button onclick="acionar('climatizacao', 'AQUECENDO')">Aquecer</button>
            <button onclick="acionar('climatizacao', 'RESFRIANDO')">Resfriar</button>
            <button onclick="acionar('climatizacao', 'DESLIGADO')">Clima: OFF</button>
          </div>
        </div>
      </div>
    </div>

    <div class="grid-bottom">
      <div class="box">
        <h2>[4] Historico de Eventos Replicados no PostgreSQL</h2>
        <ul class="logs" id="lista-historico">
          <li>Aguardando eventos...</li>
        </ul>
      </div>

      <div class="box">
        <h2>[5] Regras Agronomicas &amp; Protecoes SD</h2>
        <ul class="rules-list">
          <li><span>Irrigacao (Histerese)</span><span class="ok">&lt; 40% Liga | &gt; 65% Desliga</span></li>
          <li><span>Grow Lights (PAR)</span><span class="ok">&lt; 12.000 lux Liga</span></li>
          <li><span>Climatizacao Raiz</span><span class="ok">&lt; 16°C Aquece | &gt; 27°C Resfria</span></li>
          <li><span>Modo DIA_DE_JOGO</span><span class="warn">Trava Irrigacao e Luzes OFF</span></li>
          <li><span>Tolerancia a Quedas</span><span class="ok">Failover Direto Pyro5</span></li>
          <li><span>Seguranca Bizantina</span><span class="ok">Sanity Check + TMR 2 de 3</span></li>
        </ul>
      </div>
    </div>
  </div>

  <script>
    function classeStatus(st) {
      if (st.includes("ONLINE")) return "ok";
      if (st.includes("DIVERGENTE")) return "warn";
      return "err";
    }

    function classeAtuador(val) {
      if (val === "LIGADO" || val === "AQUECENDO") return "val state-badge ok";
      if (val === "RESFRIANDO") return "val state-badge warn";
      return "val state-badge meta";
    }

    function mostrarFeedback(msg, isErr = false) {
      const el = document.getElementById("feedback");
      el.className = "feedback " + (isErr ? "err" : "ok");
      el.textContent = "> " + msg;
    }

    async function postJson(url, body) {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      return resp.json();
    }

    async function definirModo(modo) {
      try {
        const res = await postJson("/api/modo", { modo });
        mostrarFeedback(res.mensagem || "Comando enviado.", !res.sucesso);
        atualizar();
      } catch (e) {
        mostrarFeedback("Erro ao alterar modo: " + e, true);
      }
    }

    async function acionar(atuador, estado) {
      try {
        const res = await postJson("/api/atuador", { atuador, estado });
        mostrarFeedback(res.mensagem || "Comando enviado.", !res.sucesso);
        atualizar();
      } catch (e) {
        mostrarFeedback("Erro ao acionar atuador: " + e, true);
      }
    }

    async function simularInvasao(ctrlId, comprometido) {
      try {
        const res = await postJson("/api/invasao", { ctrl_id: ctrlId, comprometido });
        mostrarFeedback(res.mensagem || "Atualizado.", !res.sucesso);
        atualizar();
      } catch (e) {
        mostrarFeedback("Erro ao simular invasao: " + e, true);
      }
    }

    async function atualizar() {
      try {
        const resp = await fetch("/api/estado");
        const dados = await resp.json();
        const infra = dados.infra || {};
        const statusCtrls = dados.status_controladores || {};
        const alertas = dados.alertas_seguranca || [];

        const alertBox = document.getElementById("alert-box");
        if (alertas.length > 0) {
          alertBox.style.display = "block";
          alertBox.innerHTML = alertas.map(a => "[ALERTA BIZANTINO] " + a).join("<br>");
        } else {
          alertBox.style.display = "none";
        }

        const listaCtrls = document.getElementById("lista-controladores");
        listaCtrls.innerHTML = Object.keys(statusCtrls).map(cid => {
          const st = statusCtrls[cid];
          const cls = classeStatus(st);
          const info = infra[cid] || {};
          const invadido = st.includes("INVADIDO") || st.includes("DIVERGENTE");
          const offline = st.includes("OFFLINE");
          const btn = offline
            ? ""
            : invadido
              ? `<button onclick="simularInvasao(${cid}, false)">Restaurar</button>`
              : `<button class="danger" onclick="simularInvasao(${cid}, true)">Simular Invasao</button>`;
          return `
            <div class="ctrl-item">
              <div class="ctrl-top">
                <span>Controlador ${cid}: <span class="val ${cls}">${st}</span></span>
                ${btn}
              </div>
              <div class="ctrl-sub">Pyro5 :${info.pyro_port || "?"} | PostgreSQL ${info.dbname || "?"} (:${info.db_port || "?"})</div>
            </div>
          `;
        }).join("");

        if (!dados.sucesso) {
          document.getElementById("meta-info").textContent =
            `Consulta: ${dados.timestamp_consulta || "--"} | ERRO: ${dados.mensagem}`;
          document.getElementById("modo-atual").textContent = "INDISPONIVEL";
          document.getElementById("quorum-atual").textContent = "0/3";
          return;
        }

        const est = dados.estado;
        const s = est.sensores;
        const a = est.atuadores;

        document.getElementById("meta-info").textContent =
          `Ultima Consulta: ${dados.timestamp_consulta} | Storage Replicado: v${est.versao} | Comunicacao Direta Pyro5`;
        document.getElementById("modo-atual").textContent = est.modo_operacao;
        document.getElementById("quorum-atual").textContent = dados.quorum;

        ["AUTOMATICO", "DIA_DE_JOGO", "MANUAL"].forEach(m => {
          const b = document.getElementById("btn-modo-" + m);
          if (b) b.className = est.modo_operacao === m ? "active" : "";
        });

        document.getElementById("s-umidade").textContent = s.umidade_solo + " %";
        document.getElementById("bar-umidade").style.width = Math.min(100, Math.max(0, s.umidade_solo)) + "%";

        const luzVal = Math.round(s.luminosidade_lux);
        document.getElementById("s-luz").textContent = luzVal + " lux";
        document.getElementById("bar-luz").style.width = Math.min(100, Math.max(0, (luzVal / 25000) * 100)) + "%";

        document.getElementById("s-temp").textContent = s.temperatura_grama + " °C";
        document.getElementById("bar-temp").style.width = Math.min(100, Math.max(0, ((s.temperatura_grama - 5) / 35) * 100)) + "%";

        document.getElementById("s-ts").textContent = s.timestamp;

        const elIrrig = document.getElementById("a-irrig");
        const elLuz = document.getElementById("a-luz");
        const elClima = document.getElementById("a-clima");
        elIrrig.textContent = a.irrigacao;
        elIrrig.className = classeAtuador(a.irrigacao);
        elLuz.textContent = a.grow_lights;
        elLuz.className = classeAtuador(a.grow_lights);
        elClima.textContent = a.climatizacao;
        elClima.className = classeAtuador(a.climatizacao);

        const hist = est.historico_recente || [];
        const ul = document.getElementById("lista-historico");
        ul.innerHTML = hist.length
          ? hist.slice().reverse().map(item => `<li>${item}</li>`).join("")
          : "<li>Nenhum evento registrado ainda.</li>";
      } catch (e) {
        document.getElementById("meta-info").textContent = "Erro ao atualizar painel: " + e;
      }
    }

    atualizar();
    setInterval(atualizar, 2000);
  </script>
</body>
</html>
"""


class PainelHandler(BaseHTTPRequestHandler):
    """Servidor HTTP local da interface do Cliente (sem camada intermediária)."""

    def _enviar_json(self, status_code: int, payload: dict) -> None:
        corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _ler_json(self) -> dict:
        tamanho = int(self.headers.get("Content-Length", "0"))
        if tamanho <= 0:
            return {}
        bruto = self.rfile.read(tamanho).decode("utf-8")
        return json.loads(bruto)

    def log_message(self, format, *args) -> None:
        pass

    def do_GET(self) -> None:
        if self.path == "/":
            corpo = HTML_PAINEL.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)
            return

        if self.path == "/api/estado":
            visao = rpc.obter_visao_geral()
            visao["infra"] = {
                str(cid): {
                    "pyro_port": CONTROLADORES_CONFIG[cid]["port"],
                    "db_port": DATABASES_CONFIG[cid]["port"],
                    "dbname": DATABASES_CONFIG[cid]["dbname"],
                }
                for cid in CONTROLADORES_CONFIG
            }
            self._enviar_json(200, visao)
            return

        self._enviar_json(404, {"sucesso": False, "mensagem": "Rota nao encontrada"})

    def do_POST(self) -> None:
        try:
            dados = self._ler_json()
        except Exception:
            self._enviar_json(400, {"sucesso": False, "mensagem": "JSON invalido"})
            return

        if self.path == "/api/modo":
            res = rpc.definir_modo_operacao(str(dados.get("modo", "")))
            self._enviar_json(200, res)
            return

        if self.path == "/api/atuador":
            res = rpc.acionar_atuador(
                str(dados.get("atuador", "")),
                str(dados.get("estado", "")),
            )
            self._enviar_json(200, res)
            return

        if self.path == "/api/invasao":
            res = rpc.simular_invasao_controlador(
                int(dados.get("ctrl_id", 0)),
                bool(dados.get("comprometido", False)),
            )
            self._enviar_json(200, res)
            return

        self._enviar_json(404, {"sucesso": False, "mensagem": "Rota nao encontrada"})


def iniciar_servidor(abrir_navegador: bool = True) -> None:
    url = f"http://{PAINEL_HOST}:{PAINEL_PORT}"
    servidor = ThreadingHTTPServer((PAINEL_HOST, PAINEL_PORT), PainelHandler)
    print("=" * 65)
    print(" [PAINEL WEB SMART PITCH] Interface Estilo Terminal Ativa")
    print(f" Acesse em: {url}")
    print("=" * 65)
    if abrir_navegador:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\n[PAINEL WEB] Encerrando interface...")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    iniciar_servidor(abrir_navegador=True)
