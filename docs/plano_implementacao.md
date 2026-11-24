# Plano de Implementação — Smart Pitch (1º Trabalho Prático de SD)

Este documento registra a estrutura incremental do projeto **Smart Pitch** na versão final entregue, organizada em blocos coesos de commits:

1. **Infraestrutura Docker & Configurações:**
   - `docker-compose.yml` com Broker MQTT Mosquitto (`:1883`) e 3 instâncias PostgreSQL 16 (`:5432`, `:5433`, `:5434`).
   - `requirements.txt` (`paho-mqtt`, `Pyro5`, `psycopg[binary]`) e `gramado/config.py`.
2. **Persistência PostgreSQL (`gramado/storage_db.py`):**
   - Repositório `StoragePostgres` dedicado por controlador com criação automática de tabelas (`estado_gramado` e `historico_eventos`) e gravação transacional.
3. **Camada IoT MQTT (`gramado/sensores.py` e `gramado/atuadores.py`):**
   - Publicação periódica de umidade, luminosidade e temperatura no tópico `estadio/gramado/sensores` e atuação em `estadio/gramado/atuadores`.
4. **Controlador de Processo (`gramado/controlador.py`):**
   - Regras de decisão (`AUTOMATICO`, `DIA_DE_JOGO`, `MANUAL`), *Sanity Check* de entrada/replicação, persistência em PostgreSQL, sincronização/replicação via Pyro5 e simulação didática de comprometimento.
5. **Comunicação Direta Cliente ↔ Controladores (`gramado/cliente_rpc.py` e `gramado/cliente.py`):**
   - Invocação direta de métodos Pyro5 nos controladores (sem servidor intermediário), garantindo tolerância a quedas (*failover*) e segurança (*Sanity Check* + votação por maioria TMR 2 de 3).
6. **Painel Centralizado Estilo Terminal (`gramado/painel_web.py` e `gramado/start_all.py`):**
   - Interface web escura estilo terminal (`http://127.0.0.1:8080`) sem dependências externas e gerenciador unificado em 1 único terminal.
7. **Documentação e Relatório Técnico (`docs/` e `README.md`):**
   - Diagrama simplificado, guia de estudos/apresentação e relatório técnico completo.
