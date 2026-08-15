# Projeto Novo: Tech Job Market Intelligence Agent

> Agente de IA que processa milhares de vagas tech em escala (Databricks) e entrega relatórios de tendência de mercado em linguagem natural, orquestrado por AWS.
> Objetivo: comprovar Databricks + AWS de verdade, reaproveitando o domínio que você já tem do `vagas-job-automation`.

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
