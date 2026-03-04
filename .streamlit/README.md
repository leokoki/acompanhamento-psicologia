Este diretório é destinado a armazenar **chaves e credenciais sensíveis** usadas pelo projeto de acompanhamento de psicologia.

## O que colocar aqui

- Arquivo JSON da conta de serviço do Google Cloud (por exemplo: `gcp_service_account.json`).
- Outras credenciais que você **não** quer versionar no GitHub.

## Como usar com o Streamlit

O código atual (`database.py`) lê as credenciais a partir de `st.secrets["gcp_service_account"]`.

O fluxo recomendado é:

1. Coloque o seu JSON da conta de serviço aqui, por exemplo:
   - `secrets/gcp_service_account.json`
2. Abra esse arquivo e copie **todo** o conteúdo JSON.
3. Crie (ou edite) o arquivo `.streamlit/secrets.toml` na raiz do projeto e configure assim:

```toml
[gcp_service_account]
type = "service_account"
project_id = "seu-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n... \n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[app]
sheet_id = "ID_DA_SUA_PLANILHA_GOOGLE_SHEETS"
```

> Observação: **nunca** faça commit de arquivos reais com chaves (`*.json`, `secrets.toml`, etc.) para o GitHub. Use apenas arquivos de exemplo ou mantenha estes arquivos apenas localmente.

