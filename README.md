# Gestão Automatizada de Estádios — Smart Pitch (1º Trabalho Prático de SD)

Implementação de um **Middleware de Objetos Distribuídos** integrado a uma camada **IoT Publish/Subscribe (MQTT)** para manutenção e gestão inteligente do gramado de uma arena multiuso (**Smart Pitch**).

---

## Arquitetura do Sistema

O projeto combina comunicação indireta via **Broker MQTT (Mosquitto)** para sensores e atuadores de campo com comunicação direta baseada em objetos remotos (**Pyro5**) entre Clientes, Middleware e um cluster replicado de Controladores de Processo:

- **Sensores (`gramado/sensores.py`):** Publicam leituras periódicas de **Umidade do Solo (%)**, **Luminosidade PAR (lux)** e **Temperatura da Grama (°C)** no tópico `estadio/gramado/sensores`.
- **Atuadores (`gramado/atuadores.py`):** Assinam o tópico `estadio/gramado/atuadores` e acionam o **Sistema de Irrigação**, **Iluminação Artificial (Grow Lights)** e **Climatização Subterrânea**.
- **Controladores de Processo (`gramado/controlador.py`):** Executam em **3 réplicas** (`IDs 1, 2 e 3`), processam as regras de decisão do gramado (`AUTOMATICO`, `DIA_DE_JOGO`, `MANUAL`), mantêm armazenamento local replicado em JSON (`gramado/storage/`) e expõem métodos remotos via Pyro5.
- **Middleware (`gramado/middleware.py`):** Intermedia o acesso do Cliente aos controladores garantindo **Tolerância a Falhas por Queda** e **Segurança contra Falhas Bizantinas / Invasão** por meio de *Sanity Check* + **Redundância Modular Tripla (TMR - Votação 2 de 3)**.
- **Cliente (`gramado/cliente.py`):** Painel interativo de terminal em tempo real para acompanhamento do gramado, envio de comandos e simulação de falhas/invasões.

---

## Estrutura de Pastas

```text
Gestao-Automatizada-De-Estadios/
├── docker-compose.yml          # Subida rápida do Broker MQTT Eclipse Mosquitto
├── mosquitto/
│   └── mosquitto.conf          # Configuração do Broker MQTT na porta 1883
├── requirements.txt            # Dependências Python (paho-mqtt e Pyro5)
├── docs/
│   ├── plano_implementacao.md  # Roteiro de desenvolvimento incremental
│   ├── guia_de_estudos.md      # Guia teórico/prático e roteiro de apresentação
│   └── relatorio_tecnico.md    # Relatório técnico completo do trabalho de SD
├── inicializacao_rapida/
│   ├── iniciar_smart_pitch.bat # Duplo-clique: sobe Docker e todos os terminais
│   └── parar_smart_pitch.bat   # Duplo-clique: fecha terminais e para o Docker
└── gramado/
    ├── config.py               # Configurações de MQTT, Pyro5 e limiares agronômicos
    ├── sensores.py             # Publicador MQTT de sensores do gramado
    ├── atuadores.py            # Assinante MQTT dos equipamentos físicos
    ├── controlador.py          # Controlador de processo com replicação de storage
    ├── middleware.py           # Middleware Pyro5 com tolerância a falhas e votação TMR
    ├── cliente.py              # Painel interativo do operador
    └── start_all.py            # Inicializador automático de todos os processos
```

---

## Como Executar

### 1. Pré-requisitos
- **Python 3.10+**
- **Docker** (para rodar o Broker MQTT Mosquitto)

### 2. Instalar dependências Python
```bash
pip install -r requirements.txt
```

### 3. Iniciar o Broker MQTT via Docker
```bash
docker compose up -d
```

### 4. Iniciar o sistema completo (Modo Automático)
```bash
python gramado/start_all.py
```
> O script abrirá automaticamente as janelas para os **3 Controladores**, **Middleware**, **Atuadores**, **Sensores** e o **Painel do Cliente**.

### 5. Execução Manual (Opcional, terminal por terminal)
Caso prefira abrir cada processo manualmente em terminais separados:
```bash
python gramado/controlador.py 1
python gramado/controlador.py 2
python gramado/controlador.py 3
python gramado/middleware.py
python gramado/atuadores.py
python gramado/sensores.py
python gramado/cliente.py
```

---

## Documentação e Relatório

Toda a documentação detalhada encontra-se na pasta [`docs/`](docs/):
- **[Relatório Técnico Completo (`docs/relatorio_tecnico.md`)](docs/relatorio_tecnico.md)**
- **[Guia de Estudos e Apresentação (`docs/guia_de_estudos.md`)](docs/guia_de_estudos.md)**
- **[Plano de Implementação (`docs/plano_implementacao.md`)](docs/plano_implementacao.md)**

