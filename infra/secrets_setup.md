# Secrets Manager setup

O pipeline depende de quatro credenciais, guardadas em um único secret JSON no AWS
Secrets Manager (`job-market-intel-agent/secrets` por padrão).

## 1. Criar o secret

```bash
aws secretsmanager create-secret \
  --name job-market-intel-agent/secrets \
  --secret-string '{
    "databricks_token": "dapiXXXXXXXXXXXXXXXX",
    "telegram_bot_token": "123456:ABC-DEF...",
    "telegram_chat_id": "-100123456789",
    "llm_api_key": "sk-ant-..."
  }'
```

## 2. Onde cada credencial é usada

| Chave | Usado por | Como obter |
|---|---|---|
| `databricks_token` | `infra/lambda_trigger_pipeline.py` | Databricks → User Settings → Access Tokens |
| `telegram_bot_token` | `delivery/telegram_notifier.py` | @BotFather no Telegram |
| `telegram_chat_id` | `delivery/telegram_notifier.py` | `getUpdates` na API do bot, ou @userinfobot |
| `llm_api_key` | `agent/report_generator.py` | Console da Anthropic ou OpenAI |

O `llm_api_key` e as credenciais do Telegram usadas em `databricks/04_report_and_notify.py`
devem também ser configuradas como [Databricks secrets](https://docs.databricks.com/en/security/secrets/index.html),
já que esse script roda no cluster e não tem acesso direto ao Secrets Manager da AWS
a menos que o cluster tenha uma instance profile com permissão para isso.

## 3. Permissão da Lambda

A role de execução da Lambda precisa de `secretsmanager:GetSecretValue` restrito ao
ARN desse secret específico — não usar `*` no `Resource`.

## 4. Local / testes

Para rodar localmente sem Secrets Manager, defina as mesmas chaves como variáveis de
ambiente (veja `.env.example`) — o código lê de `os.environ` quando não está rodando
dentro da Lambda ou do cluster Databricks.
