# Plano de Implementação — Smart Pitch (1º Trabalho Prático de SD)

Este documento descreve o roteiro passo a passo do desenvolvimento do sistema de **Gestão Automatizada de Gramado Esportivo (Smart Pitch)**. O trabalho é dividido em entregas incrementais, onde cada etapa corresponde a **1 commit**.

---

## Regras de Trabalho
1. **Controle de Versão:** Apenas o autor do projeto cria branches e executa commits.
2. **Entregas Incrementais:** Uma etapa é desenvolvida e validada por vez (equivalente a um commit).
3. **Documentação Contínua:** Toda a documentação técnica, guia de estudos e relatório ficam centralizados na pasta `docs/`.
4. **Mensagens de Commit:** Ao final de cada etapa, é fornecida uma mensagem de commit simples e direta (sem prefixos como `feat:`, `chore:`, etc.).

---

## Etapas de Desenvolvimento (Commits)

### Etapa 1 — Estrutura Base, Documentação Inicial e Broker MQTT (Atual)
- **Objetivo:** Configurar o ambiente do projeto, subir o broker MQTT via Docker e criar o plano de implementação e o guia de estudos.
- **Arquivos:**
  - `.gitignore`
  - `requirements.txt` (`paho-mqtt`, `Pyro5`)
  - `docker-compose.yml` e `mosquitto/mosquitto.conf`
  - `docs/plano_implementacao.md`
  - `docs/guia_de_estudos.md`

### Etapa 2 — Configurações Globais, Sensores e Atuadores (MQTT Pub/Sub)
- **Objetivo:** Implementar a camada de IoT do gramado que conversa exclusivamente com o Broker MQTT.
- **Elementos do Smart Pitch:**
  1. **Umidade do Solo (%)** $\rightarrow$ **Irrigação** (`LIGADO` / `DESLIGADO`)
  2. **Luminosidade PAR (lux)** $\rightarrow$ **Iluminação Artificial / Grow Lights** (`LIGADO` / `DESLIGADO`)
  3. **Temperatura da Grama (°C)** $\rightarrow$ **Climatização Subterrânea** (`AQUECENDO` / `RESFRIANDO` / `DESLIGADO`)
- **Arquivos:**
  - `config.py` (portas, tópicos MQTT, limiares agronômicos e endereços Pyro5)
  - `sensores.py` (publica leituras periódicas nos tópicos MQTT)
  - `atuadores.py` (assina tópicos de comando no MQTT e exibe mudanças de estado)

### Etapa 3 — Controlador de Processo e Armazenamento Replicado
- **Objetivo:** Implementar o Controlador que assina os dados dos sensores no MQTT, toma decisões automáticas sobre os atuadores, expõe métodos remotos via Pyro5 e replica os dados armazenados entre os controladores.
- **Destaques de SD:**
  - Suporte a múltiplas instâncias (`python controlador.py 1`, `2`, `3`).
  - Persistência em arquivo (`storage_controlador_X.json`) com **sincronização/replicação** entre réplicas.
  - Modo de simulação de falha/invasão (retornar valores adulterados quando ativado para teste de segurança).
- **Arquivos:**
  - `controlador.py`

### Etapa 4 — Middleware com Tolerância a Falhas e Segurança (Votação TMR)
- **Objetivo:** Implementar o Middleware baseado em objetos distribuídos que intermedia o Cliente e os Controladores.
- **Destaques de SD:**
  - **Tolerância a Falhas por Queda (Crash):** Se um controlador cair, o Middleware continua atendendo o cliente usando as réplicas ativas.
  - **Segurança / Falhas Bizantinas (TMR):** Consulta as 3 réplicas de controladores e aplica **Votação por Maioria (2 de 3)** combinada com verificação de plausibilidade (Sanity Check), isolando respostas de controladores invadidos ou com erro intermitente.
- **Arquivos:**
  - `middleware.py`

### Etapa 5 — Cliente Interativo (CLI) e Script de Inicialização
- **Objetivo:** Criar a interface de terminal para o operador do estádio visualizar o gramado em tempo real, enviar ações (mudar modo para `AUTOMATICO`, `DIA_DE_JOGO` ou `MANUAL`, acionar atuadores) e simular quedas/invasões de controladores para demonstração.
- **Arquivos:**
  - `cliente.py`
  - `start_all.py` (script prático para abrir os processos em janelas/terminais locais)

### Etapa 6 — Relatório Técnico e README Final
- **Objetivo:** Redigir o relatório exigido na especificação explicando a arquitetura, o funcionamento e a solução adotada para cada questão do trabalho, além das instruções completas no `README.md`.
- **Arquivos:**
  - `docs/relatorio_tecnico.md`
  - `README.md`

