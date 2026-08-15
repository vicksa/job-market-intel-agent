# Tech Job Market Intelligence Agent

[![CI](https://github.com/vicksa/job-market-intel-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/vicksa/job-market-intel-agent/actions/workflows/ci.yml)

Pipeline semanal que coleta vagas tech, processa o lote em escala no Databricks
(arquitetura medallion) e usa um LLM para transformar os números em um relatório de
tendências de mercado em linguagem natural, entregue via Telegram — tudo orquestrado
por AWS (S3, Lambda, EventBridge, Secrets Manager).

## Como funciona

```
RemoteOK API ─▶ ingestion/fetch_jobs.py ─▶ S3 raw/
                                               │
                                               ▼
                                   Databricks (PySpark, arquitetura medallion)
                                   01_bronze_ingest ─▶ 02_silver_extract ─▶ 03_gold_trends
                                                                                │
                                                                                ▼
                                          04_report_and_notify (agent/report_generator.py, LLM)
                                                                                │
                                                                                ▼
                                                delivery/telegram_notifier.py ─▶ Telegram
```

EventBridge dispara semanalmente uma Lambda (`infra/lambda_trigger_pipeline.py`), que
roda a ingestão e chama o job do Databricks via API. O job do Databricks executa as
camadas bronze → silver → gold e, como última tarefa, já gera e envia o relatório —
sem round-trip de volta pro Lambda.

| Camada | O que acontece | Onde roda |
|---|---|---|
| **Raw** | JSON bruto das vagas, como veio da API | `ingestion/fetch_jobs.py` → S3 `raw/` |
| **Bronze** | Dados validados e com schema aplicado, sem transformação de conteúdo | `databricks/01_bronze_ingest.py` |
| **Silver** | Skills, senioridade e modalidade de trabalho extraídas do texto de cada vaga | `databricks/02_silver_extract.py` |
| **Gold** | Contagem de vagas por skill por semana, comparada com a semana anterior | `databricks/03_gold_trends.py` |
| **Relatório** | Gold vira texto em linguagem natural via LLM | `agent/report_generator.py` |
| **Entrega** | Relatório enviado via Telegram | `delivery/telegram_notifier.py` |

## Stack

- **Fonte de dados:** [RemoteOK](https://remoteok.com/api) — API pública, sem scraping frágil
- **AWS S3** — data lake (raw / bronze / silver / gold)
- **Databricks** — processamento em PySpark + Delta Lake
- **AWS Lambda + EventBridge** — orquestração e agendamento semanal
- **AWS Secrets Manager** — credenciais centralizadas
- **Claude API** — geração do relatório em linguagem natural
- **Telegram Bot API** — entrega do relatório

## Estrutura

```
job-market-intel-agent/
├── ingestion/
│   ├── fetch_jobs.py            # busca vagas na API pública, salva raw no S3
│   └── config.py
├── databricks/
│   ├── 01_bronze_ingest.py      # lê raw do S3, valida schema, grava bronze
│   ├── 02_silver_extract.py     # extrai skills/senioridade/modalidade
│   ├── 03_gold_trends.py        # agrega tendências semana a semana
│   ├── 04_report_and_notify.py  # última task do job: gera e envia o relatório
│   └── notebooks/               # versão .ipynb dos scripts acima, se preferir notebook
├── agent/
│   ├── report_generator.py      # pega o gold, gera relatório com LLM
│   └── prompts/weekly_report.txt
├── delivery/
│   └── telegram_notifier.py
├── infra/
│   ├── lambda_trigger_pipeline.py
│   ├── eventbridge_rule.tf
│   └── secrets_setup.md
├── test/
├── docker-compose.yml            # LocalStack, para testar ingestão sem AWS real
└── .env.example
```

## Decisões de arquitetura

**Por que separar bronze/silver/gold:** cada camada tem uma responsabilidade única e
testável isoladamente — bronze só valida schema, silver só extrai e enriquece, gold só
agrega. Isso evita reprocessar tudo quando só a lógica de extração de skills muda, e é
o padrão medallion usado em projetos Databricks reais.

**Extração de skills — regex vs. LLM:** a v1 usa uma lista fixa de skills conhecidas
com matching de texto, rodando distribuído via UDF no Spark (`databricks/02_silver_extract.py`)
— gratuito, rápido, cobre a maioria dos casos. Uma extração via LLM pegaria variações e
termos fora da lista, mas custaria uma chamada de API por vaga; fica como v2, limitada
a um lote pequeno para não estourar custo.

## Secrets Manager

Um único secret (`job-market-intel-agent/secrets`) guarda:

- Token de acesso ao Databricks (Lambda dispara os jobs via API)
- Token do bot do Telegram
- Chave da API do LLM

Detalhes de setup em [`infra/secrets_setup.md`](infra/secrets_setup.md).

## Como rodar localmente

Os scripts em `databricks/` dependem de PySpark/Delta Lake e são pensados para rodar
dentro de um workspace Databricks — não são necessários para testar o resto do
pipeline localmente.

```bash
# 1. Instalar dependências
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# 2. Copiar e preencher as variáveis de ambiente
cp .env.example .env

# 3. Rodar os testes unitários (não precisam de AWS/Databricks/Telegram reais)
pytest test/ -v -m "not integration"

# 4. (Opcional) Testar a ingestão contra um S3 local com LocalStack
docker compose up -d localstack
pytest test/ -v -m integration
```

Para gerar um relatório de exemplo sem depender do Databricks, monte um JSON de gold
fake (`[{"skill": "python", "job_count": 42, "prev_week_count": 30, "delta": 12,
"status": "up"}, ...]`) e rode:

```bash
python agent/report_generator.py gold_trends.json 2026-08-11
```

com `ANTHROPIC_API_KEY` configurada.

## Exemplo de relatório gerado

```
📊 Relatório semanal de vagas tech — 11/08/2026

Python segue disparado: 42 vagas essa semana (+12 vs. semana passada), puxado por
posições de dados/backend. React e TypeScript também subiram, sinal de que frontend
moderno continua aquecido. Do outro lado, PHP caiu pela metade (-10) e Java segue
estável, sem grandes variações.

Novidade da semana: Rust apareceu em 3 vagas — ainda pouco volume, mas vale ficar de
olho se a tendência continuar.

Takeaway: se você está estudando para a próxima vaga, Python + um cloud provider
continua sendo a combinação mais procurada no mercado remoto.
```

*(Exemplo ilustrativo — o relatório real é gerado a partir dos dados agregados na
camada gold pela LLM configurada.)*

## Testes

- Unitários (`test/test_fetch_jobs.py`, `test/test_report_generator.py`) — mockam
  rede/S3/LLM, rodam em qualquer lugar.
- Integração (`test/test_ingestion_integration.py`) — sobe contra LocalStack, pulado
  automaticamente se o LocalStack não estiver rodando.
- CI via GitHub Actions em todo push/PR na `main`.

## Escopo

Fora do MVP: múltiplas fontes de scraping autenticado, dashboard visual (o relatório
em texto já é a entrega) e histórico de mais de poucas semanas.

Databricks Community Edition é gratuito e suficiente para rodar este projeto. Se usar
a versão trial paga, tome cuidado para não deixar o cluster ativo sem necessidade.
