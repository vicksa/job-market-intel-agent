# Tech Job Market Intelligence Agent

[![CI](https://github.com/vicksa/job-market-intel-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/vicksa/job-market-intel-agent/actions/workflows/ci.yml)

> Agente de IA que processa milhares de vagas tech em escala (Databricks) e entrega relatórios de tendência de mercado em linguagem natural, orquestrado por AWS.
> Objetivo: comprovar Databricks + AWS de verdade, reaproveitando o domínio que você já tem do `vagas-job-automation`.

---

## 🏗️ Arquitetura

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

**Por que separar bronze/silver/gold:** cada camada tem uma responsabilidade única e
testável isoladamente — bronze só valida schema, silver só extrai e enriquece, gold só
agrega. Isso evita reprocessar tudo quando só a lógica de extração de skills muda, e é
o vocabulário padrão de projetos Databricks reais.

**Trade-off da extração de skills (regex vs. LLM):** a v1 usa uma lista fixa de skills
conhecidas com matching de texto, rodando distribuído via UDF no Spark — é gratuito,
rápido e cobre a maioria dos casos. Uma extração via LLM pegaria variações e termos
fora da lista, mas custaria uma chamada de API por vaga; fica como v2, limitada a um
lote pequeno para não estourar custo.

---

## 🎯 Por que este projeto

Você já tem produtos de automação (`achadinhos`, `vagas-job-automation`) e agentes de IA (`ai-qa-orchestrator`). O que falta comprovar é **processamento de dados em escala** — e Databricks só faz sentido quando existe volume real para processar. Este projeto usa exatamente o domínio que você já entende (mercado de vagas tech) para gerar esse volume de forma honesta, sem inventar necessidade.

---

## 📐 Escopo do MVP

Um pipeline que, uma vez por semana:
1. Coleta vagas de tech de 1-2 fontes (ex: RemoteOK tem API pública simples — bom ponto de partida sem depender de scraping frágil de LinkedIn).
2. Salva os dados brutos no **S3** (camada raw).
3. No **Databricks**, processa esse lote: extrai skills, senioridade, stack, remoto/híbrido/presencial, faixa salarial (quando disponível) a partir do texto — grava tratado de volta no S3 (camada processed).
4. Compara com a semana anterior: o que subiu, o que caiu, o que é novo.
5. Um **agente de IA** (Claude/OpenAI) transforma esses números em um relatório curto e legível.
6. O relatório é entregue via Telegram (reaproveitando o padrão de bot que você já tem no `achadinhos`) ou e-mail.

**Fora de escopo (não fazer no MVP):** múltiplas fontes complexas de scraping autenticado, dashboard visual (o relatório em texto já é a entrega), histórico de mais de poucas semanas.

---

## 🧱 Stack

- **Fonte de dados:** API pública de vagas (ex: RemoteOK, We Work Remotely) — evita scraping frágil no início
- **AWS S3** — data lake (raw e processed)
- **Databricks** (Community Edition ou trial serve bem para portfólio) — processamento em PySpark
- **Delta Lake** (opcional, mas soma pontos) — versionamento das tabelas processadas
- **AWS Lambda** — cola as etapas do pipeline (dispara ingestão, dispara notebook do Databricks via API, dispara notificação)
- **AWS EventBridge** — agenda a execução semanal
- **AWS Secrets Manager** — credenciais de API e token do Databricks
- **Claude API ou OpenAI API** — geração do relatório em linguagem natural
- **Telegram Bot API** — entrega do relatório (reaproveita padrão do `achadinhos`)
- **Python** — scripts de ingestão e integração

---

## 🗂️ Estrutura de pastas sugerida

```
job-market-intel-agent/
├── ingestion/
│   ├── fetch_jobs.py            # busca vagas na API pública, salva raw no S3
│   └── config.py
├── databricks/
│   ├── 01_bronze_ingest.py      # lê raw do S3, valida schema, grava bronze
│   ├── 02_silver_extract.py     # extrai skills/senioridade/stack via regex ou LLM
│   ├── 03_gold_trends.py        # agrega tendências semana a semana
│   ├── 04_report_and_notify.py  # última task do job: gera e envia o relatório
│   └── notebooks/               # versão .ipynb dos scripts acima, se preferir notebook
├── agent/
│   ├── report_generator.py      # pega o gold do Databricks, gera relatório com LLM
│   └── prompts/
│       └── weekly_report.txt
├── delivery/
│   └── telegram_notifier.py
├── infra/
│   ├── lambda_trigger_pipeline.py
│   ├── eventbridge_rule.tf      # ou config equivalente
│   └── secrets_setup.md
├── test/
│   ├── test_fetch_jobs.py
│   └── test_report_generator.py
├── docker-compose.yml           # ambiente local para testar ingestão sem AWS real
├── .env.example
└── README.md
```

---

## 🔌 Fluxo detalhado (camada por camada, estilo medallion)

| Camada | O que acontece | Onde roda |
|---|---|---|
| **Raw** | JSON bruto das vagas, como veio da API | `ingestion/fetch_jobs.py` → S3 `raw/` |
| **Bronze** | Dados raw validados e com schema aplicado (sem transformação de conteúdo) | Databricks `01_bronze_ingest.py` |
| **Silver** | Skills, senioridade, stack, localização extraídos do texto de cada vaga | Databricks `02_silver_extract.py` |
| **Gold** | Agregados: contagem de skills por semana, comparação com semana anterior, tendências | Databricks `03_gold_trends.py` |
| **Relatório** | Gold vira texto em linguagem natural via LLM | `agent/report_generator.py` |
| **Entrega** | Relatório enviado via Telegram | `delivery/telegram_notifier.py` |

Esse padrão (raw → bronze → silver → gold) é a arquitetura medallion, comum em projetos reais de Databricks — vale citar isso no README, é vocabulário que recrutador de dados reconhece.

---

## 🤖 Onde a extração de skills acontece — duas opções

**Opção simples (comece aqui):** lista de skills conhecidas (Python, TypeScript, React, AWS, Docker, etc.) e regex/matching de texto contra essa lista, rodando distribuído no Spark via Databricks.

**Opção mais avançada (se quiser ir além):** usar o LLM para extrair skills de forma mais flexível, direto na camada silver, em vez de lista fixa. Fica mais caro (chamada de API por vaga) — pode limitar a um lote pequeno para não estourar custo, e é um ótimo ponto para discutir trade-off (custo vs. cobertura) em entrevista.

---

## 🔐 Secrets Manager — o que colocar lá

- Token de acesso ao Databricks (para o Lambda disparar os jobs via API)
- Token do bot do Telegram
- Chave da API do LLM (Claude/OpenAI)

---

## 🧪 Testes (não pule — é seu diferencial)

- **Unitário:** parsing de uma vaga individual (extração de skills a partir de um texto de exemplo).
- **Unitário:** `report_generator.py` com um gold de exemplo mockado, verificando que o prompt monta corretamente.
- **Integração:** pipeline de ingestão salvando corretamente no S3 (pode usar LocalStack para não depender de AWS real nos testes).
- **CI:** GitHub Actions rodando os testes Python a cada push, com badge no README.

---

## 🗺️ Roadmap de commits sugerido

1. `chore: setup projeto Python + estrutura de pastas`
2. `feat: fetch_jobs.py — ingestão da API pública de vagas`
3. `feat: upload do raw para S3`
4. `feat: notebook bronze — validação de schema no Databricks`
5. `feat: notebook silver — extração de skills e senioridade`
6. `feat: notebook gold — agregação de tendências semana a semana`
7. `feat: report_generator.py — geração de relatório via LLM`
8. `feat: telegram_notifier.py — entrega do relatório`
9. `feat: lambda_trigger_pipeline — orquestração via Lambda`
10. `feat: EventBridge — agendamento semanal`
11. `feat: Secrets Manager — credenciais centralizadas`
12. `test: testes unitários de extração e geração de relatório`
13. `test: integração da ingestão com LocalStack`
14. `ci: GitHub Actions rodando testes`
15. `docs: README com arquitetura medallion, diagrama e instruções de execução`

---

## 📝 O que o README final precisa ter

- Diagrama do fluxo raw → bronze → silver → gold → relatório → Telegram
- Exemplo real de um relatório gerado (cole um trecho de saída)
- Explicação da arquitetura medallion e por que Databricks entra na camada de processamento
- Como rodar localmente (ingestão + testes) sem depender de conta AWS/Databricks paga
- 1 parágrafo de decisões: por que separar bronze/silver/gold, trade-off da extração de skills (regex vs. LLM)
- Badge de status do CI

---

## ⏱️ Estimativa

Pipeline enxuto (uma fonte, extração por lista de skills, relatório simples) é viável em poucos dias de trabalho focado. A versão com extração via LLM na camada silver pode vir depois, como v2 — não é bloqueio para a primeira versão pública.

---

## 💡 Observação sobre Databricks Community/Trial

Databricks Community Edition é gratuito e suficiente para portfólio (roda notebooks PySpark sem custo). Se usar a versão trial paga, tome cuidado para não deixar o cluster rodando sem necessidade — documente isso no README, mostra consciência de custo, o que é visto como maturidade em vaga de dados/cloud.

---

## 🚀 Como rodar localmente

Os scripts em `databricks/` dependem de PySpark/Delta Lake e são pensados para rodar
dentro de um workspace Databricks — não são necessários para testar o resto do
pipeline localmente.

```bash
# 1. Instalar dependências (ingestão, agente, entrega, testes)
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
"status": "up"}, ...]`) e rode `python agent/report_generator.py gold_trends.json
2026-08-11` com `ANTHROPIC_API_KEY` configurada.

---

## 📄 Exemplo de relatório gerado

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
