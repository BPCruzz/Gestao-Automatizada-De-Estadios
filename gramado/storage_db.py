"""
Módulo de Persistência em PostgreSQL (Smart Pitch - Gramado).
Cada controlador possui sua própria instância PostgreSQL independente,
garantindo armazenamento persistente e replicação entre bancos separados.
"""

import psycopg

from config import obter_dsn_banco


SQL_CRIAR_TABELAS = """
CREATE TABLE IF NOT EXISTS estado_gramado (
    id INTEGER PRIMARY KEY,
    controlador_id INTEGER NOT NULL,
    versao INTEGER NOT NULL,
    modo_operacao VARCHAR(30) NOT NULL,
    umidade_solo DOUBLE PRECISION NOT NULL,
    luminosidade_lux DOUBLE PRECISION NOT NULL,
    temperatura_grama DOUBLE PRECISION NOT NULL,
    sensor_timestamp VARCHAR(20) NOT NULL,
    irrigacao VARCHAR(20) NOT NULL,
    grow_lights VARCHAR(20) NOT NULL,
    climatizacao VARCHAR(20) NOT NULL,
    ultima_atualizacao VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS historico_eventos (
    id SERIAL PRIMARY KEY,
    descricao TEXT NOT NULL
);
"""


class StoragePostgres:
    """Repositório PostgreSQL dedicado a uma réplica do Controlador de Processo."""

    def __init__(self, ctrl_id: int):
        self.ctrl_id = ctrl_id
        self.dsn = obter_dsn_banco(ctrl_id)
        self._tabelas_criadas = False

    def _conectar(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, connect_timeout=3)

    def inicializar_tabelas(self) -> bool:
        """Cria as tabelas necessárias caso ainda não existam no banco."""
        try:
            with self._conectar() as conn:
                with conn.cursor() as cur:
                    cur.execute(SQL_CRIAR_TABELAS)
            self._tabelas_criadas = True
            return True
        except Exception as exc:
            print(f"[CTRL {self.ctrl_id}] Aviso ao inicializar PostgreSQL: {exc}")
            return False

    def _garantir_tabelas(self) -> bool:
        if self._tabelas_criadas:
            return True
        return self.inicializar_tabelas()

    def carregar_estado(self) -> dict | None:
        """Carrega o estado persistido e os últimos eventos do banco PostgreSQL."""
        if not self._garantir_tabelas():
            return None

        try:
            with self._conectar() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            versao,
                            modo_operacao,
                            umidade_solo,
                            luminosidade_lux,
                            temperatura_grama,
                            sensor_timestamp,
                            irrigacao,
                            grow_lights,
                            climatizacao,
                            ultima_atualizacao
                        FROM estado_gramado
                        WHERE id = 1
                        """
                    )
                    linha = cur.fetchone()
                    if linha is None:
                        return None

                    cur.execute(
                        """
                        SELECT descricao
                        FROM historico_eventos
                        ORDER BY id DESC
                        LIMIT 10
                        """
                    )
                    eventos = [row[0] for row in reversed(cur.fetchall())]

            return {
                "controlador_id": self.ctrl_id,
                "versao": int(linha[0]),
                "modo_operacao": linha[1],
                "sensores": {
                    "umidade_solo": float(linha[2]),
                    "luminosidade_lux": float(linha[3]),
                    "temperatura_grama": float(linha[4]),
                    "timestamp": linha[5],
                },
                "atuadores": {
                    "irrigacao": linha[6],
                    "grow_lights": linha[7],
                    "climatizacao": linha[8],
                },
                "ultima_atualizacao": linha[9],
                "historico_recente": eventos,
            }
        except Exception as exc:
            print(f"[CTRL {self.ctrl_id}] Aviso ao ler PostgreSQL: {exc}")
            return None

    def salvar_estado(self, estado: dict) -> bool:
        """Persiste o estado atual e o histórico recente de forma transacional."""
        if not self._garantir_tabelas():
            return False

        sensores = estado["sensores"]
        atuadores = estado["atuadores"]
        historico = estado.get("historico_recente", [])[-10:]

        try:
            with self._conectar() as conn:
                with conn.transaction():
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO estado_gramado (
                                id,
                                controlador_id,
                                versao,
                                modo_operacao,
                                umidade_solo,
                                luminosidade_lux,
                                temperatura_grama,
                                sensor_timestamp,
                                irrigacao,
                                grow_lights,
                                climatizacao,
                                ultima_atualizacao
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO UPDATE SET
                                controlador_id = EXCLUDED.controlador_id,
                                versao = EXCLUDED.versao,
                                modo_operacao = EXCLUDED.modo_operacao,
                                umidade_solo = EXCLUDED.umidade_solo,
                                luminosidade_lux = EXCLUDED.luminosidade_lux,
                                temperatura_grama = EXCLUDED.temperatura_grama,
                                sensor_timestamp = EXCLUDED.sensor_timestamp,
                                irrigacao = EXCLUDED.irrigacao,
                                grow_lights = EXCLUDED.grow_lights,
                                climatizacao = EXCLUDED.climatizacao,
                                ultima_atualizacao = EXCLUDED.ultima_atualizacao
                            """,
                            (
                                1,
                                self.ctrl_id,
                                int(estado["versao"]),
                                estado["modo_operacao"],
                                float(sensores["umidade_solo"]),
                                float(sensores["luminosidade_lux"]),
                                float(sensores["temperatura_grama"]),
                                str(sensores["timestamp"]),
                                atuadores["irrigacao"],
                                atuadores["grow_lights"],
                                atuadores["climatizacao"],
                                str(estado["ultima_atualizacao"]),
                            ),
                        )

                        cur.execute("DELETE FROM historico_eventos")
                        if historico:
                            cur.executemany(
                                "INSERT INTO historico_eventos (descricao) VALUES (%s)",
                                [(evento,) for evento in historico],
                            )
            return True
        except Exception as exc:
            print(f"[CTRL {self.ctrl_id}] Erro ao salvar no PostgreSQL: {exc}")
            return False
