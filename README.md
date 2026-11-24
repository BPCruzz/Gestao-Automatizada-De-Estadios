# Gestão Automatizada de Estádios — Smart Pitch (1º Trabalho Prático de SD)

Implementação de um sistema distribuído para manutenção e gestão inteligente do gramado de uma arena multiuso (**Smart Pitch**), integrando comunicação **IoT Publish/Subscribe (MQTT)** com **comunicação direta baseada em Objetos Distribuídos (Pyro5)** e **replicação em 3 bancos PostgreSQL independentes**.

---

## Arquitetura do Sistema

O projeto segue a arquitetura proposta para o trabalho, onde o **Middleware** é formado pela comunicação direta baseada em objetos entre Cliente e Controladores, pela sincronização/tolerância a falhas entre réplicas e pela replicação em bancos separados — **sem servidor intermediário entre Cliente e Controladores**:

- **Sensores (`gramado/sensores.py`):** Publicam leituras periódicas de **Umidade do Solo (%)**, **Luminosidade PAR (lux)** e **Temperatura da Grama (°C)** no tópico `estadio/gramado/sensores`.
- **Atuadores (`gramado/atuadores.py`):** Assinam o tópico `estadio/gramado/atuadores` e acionam o **Sistema de Irrigação**, **Iluminação Artificial (Grow Lights)** e **Climatização Subterrânea**.
- **Controladores de Processo (`gramado/controlador.py`):** Executam em **3 réplicas** (`IDs 1, 2 e 3`, portas Pyro5 `9091`, `9092`, `9093`), aplicam *Sanity Check* nas entradas, processam as regras de decisão (`AUTOMATICO`, `DIA_DE_JOGO`, `MANUAL`), mantêm armazenamento persistente em **3 bancos PostgreSQL separados** (`gramado/storage_db.py`) e replicam o estado entre si via Pyro5.
- **Comunicação Direta Cliente ↔ Controladores (`gramado/cliente_rpc.py`):** Camada local importada pelo cliente (sem servidor nem porta extra) que invoca métodos Pyro5 **diretamente** nos controladores garantindo **Tolerância a Falhas por Queda (Failover)** e **Segurança contra Falhas Bizantinas** via *Sanity Check* + **Votação por Maioria TMR (2 de 3)**.
- **Interfaces do Cliente (`gramado/painel_web.py` e `gramado/cliente.py`):**
  - `painel_web.py`: Painel centralizado em estilo terminal (`http://127.0.0.1:8080`) com atualização automática em tempo real, comandos diretos e simulação de invasão.
  - `cliente.py`: Painel alternativo em linha de comando (CLI).

Veja o diagrama simplificado em [`docs/diagrama_sistema.md`](docs/diagrama_sistema.md).

---

## Estrutura de Pastas

```text
Gestao-Automatizada-De-Estadios/
├── docker-compose.yml          # Broker Mosquitto (:1883) + 3 bancos PostgreSQL (:5432, :5433, :5434)
├── mosquitto/
│   └── mosquitto.conf          # Configuração do Broker MQTT na porta 1883
├── requirements.txt            # Dependências Python (paho-mqtt, Pyro5 e psycopg[binary])
├── docs/
│   ├── diagrama_sistema.md     # Diagrama simplificado da arquitetura
│   ├── plano_implementacao.md  # Roteiro incremental de implementação
│   ├── guia_de_estudos.md      # Guia teórico/prático e roteiro de apresentação
│   └── relatorio_tecnico.md    # Relatório técnico completo do trabalho de SD
├── inicializacao_rapida/
│   ├── iniciar_smart_pitch.bat # Duplo-clique: sobe Docker e o gerenciador unificado
│   └── parar_smart_pitch.bat   # Duplo-clique: encerra processos e para o Docker
└── gramado/
    ├── config.py               # Configurações de MQTT, Pyro5, PostgreSQL e Sanity Check
    ├── storage_db.py           # Persistência transacional em PostgreSQL (StoragePostgres)
    ├── sensores.py             # Publicador MQTT de sensores do gramado
    ├── atuadores.py            # Assinante MQTT dos equipamentos físicos
    ├── controlador.py          # Controlador de processo com PostgreSQL, Sanity Check e replicação
    ├── cliente_rpc.py          # Camada local de invocação direta Pyro5 (Failover + TMR)
    ├── painel_web.py           # Painel Web centralizado estilo terminal (http://127.0.0.1:8080)
    ├── cliente.py              # Painel CLI alternativo do operador
    └── start_all.py            # Inicializador unificado (1 terminal) ou --janelas
```

---

## Como Executar

### 1. Pré-requisitos
- **Python 3.10+**
- **Docker** (para o Broker MQTT Mosquitto e os 3 bancos PostgreSQL)

### 2. Instalar dependências Python
```bash
pip install -r requirements.txt
```

### 3. Iniciar o Broker MQTT e os 3 bancos PostgreSQL via Docker
```bash
docker compose up -d
```

### 4. Iniciar o sistema completo (Modo Unificado — 1 Terminal + Painel Web)
```bash
python gramado/start_all.py
```
> O script inicia os **3 Controladores**, **Atuadores**, **Sensores** e o **Painel Web** (`http://127.0.0.1:8080`) em um único terminal, permitindo ainda derrubar/religar qualquer controlador pelas opções `[1]`, `[2]` e `[3]` para demonstrar tolerância a quedas.
>
> Caso prefira abrir em janelas separadas: `python gramado/start_all.py --janelas`.

### 5. Execução Manual (Opcional, terminal por terminal)
```bash
python gramado/controlador.py 1
python gramado/controlador.py 2
python gramado/controlador.py 3
python gramado/atuadores.py
python gramado/sensores.py
python gramado/painel_web.py
```
*(Ou `python gramado/cliente.py` para usar o cliente via terminal.)*

---

## Documentação e Relatório

- **[Diagrama Simplificado (`docs/diagrama_sistema.md`)](docs/diagrama_sistema.md)**
- **[Relatório Técnico Completo (`docs/relatorio_tecnico.md`)](docs/relatorio_tecnico.md)**
- **[Guia de Estudos e Apresentação (`docs/guia_de_estudos.md`)](docs/guia_de_estudos.md)**
- **[Plano de Implementação (`docs/plano_implementacao.md`)](docs/plano_implementacao.md)**
