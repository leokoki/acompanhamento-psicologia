# Acompanhamento de Contatos - Psicologia

Aplicação em **Python + Streamlit** para acompanhar, de forma semanal e mensal, os contatos que chegam via **WhatsApp** interessados no serviço de psicologia.
Os dados são salvos em uma planilha do **Google Sheets**.

---

## Funcionalidades

- **Tela 1 – Dashboards**
  - Indicadores de quantidade de contatos na **semana**, no **mês** e **total**.
  - Gráfico de barras com **distribuição por estado (UF)** a partir do DDD.
  - Gráfico de barras com **número de contatos por dia da semana** (seg, ter, qua...).
  - Gráficos de barras com **motivos dos contatos** na **semana atual** e no **mês atual**.

- **Tela 2 – Cadastro de Contatos**
  - Campos: `DDD`, `Número (opcional)`, `Sexo (M/F)`, `Fechou (Sim/Não)`, `Motivo`, `Estado`.
  - Motivos possíveis: **Aguardando**, **Não retornou**, **Preço**.
  - Campo **Estado** é preenchido automaticamente com base no **DDD**.
  - Datas:
    - **Dia do contato** (escolhido na tela, padrão hoje).
    - **Dia da última atualização** (inicialmente igual ao dia do contato).

- **Tela 3 – Edição de Contatos**
  - Lista todos os registros vindos do Google Sheets.
  - Permite escolher um registro pelo **ID** e editar seus dados.
  - O campo **Estado** é recalculado automaticamente a partir do DDD.
  - Datas:
    - **Dia do contato** pode ser alterado.
    - **Dia da última atualização** é atualizada automaticamente para **hoje** sempre que o **motivo** é alterado.

---

## Estrutura de Arquivos

- `app.py` – Código principal do Streamlit (telas, gráficos e formulários).
- `database.py` – Conexão com o Google Sheets e funções de leitura/escrita.
- `.streamlit/secrets.toml` – Configuração de credenciais e `sheet_id` (não versionar com dados reais).
- `secrets/` – Pasta para guardar **arquivos sensíveis** (por exemplo, JSON da conta de serviço do GCP).
- `.gitignore` – Ignora `secrets/gcp_service_account.json` e outros arquivos temporários.

---

## Configuração de Credenciais (Google Sheets)

1. Crie um **projeto** no Google Cloud e gere uma **Service Account** com acesso ao Google Sheets/Drive.
2. Baixe o JSON da Service Account e salve localmente, por exemplo em:
   - `secrets/gcp_service_account.json`
3. Copie o conteúdo do JSON e configure o arquivo `.streamlit/secrets.toml` na raiz do projeto:

```toml
[gcp_service_account]
type = "service_account"
project_id = "seu-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."

[app]
sheet_id = "ID_DA_SUA_PLANILHA_GOOGLE_SHEETS"
```

4. Na sua planilha do Google Sheets, crie (no mínimo) a aba `whatsapp_leads` com as colunas:
   - `id`, `data_contato`, `ddd`, `numero`, `sexo`, `fechou`, `motivo`, `estado`, `data_ultima_atualizacao`

**Importante**: compartilhe a planilha com o e-mail da Service Account com permissão de edição.

---

## Como Rodar o Projeto

1. Crie e ative um ambiente virtual (opcional, mas recomendado):

```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

2. Instale as dependências principais:

```bash
pip install streamlit gspread oauth2client pandas
```

3. Na pasta `acompanhamento-psicologia`, rode o app:

```bash
streamlit run app.py
```

4. Acesse a URL exibida no terminal, normalmente:
   - `http://localhost:8501`

---

## Observações

- **Não** faça commit de arquivos com chaves reais (`gcp_service_account.json`, `secrets.toml` com dados reais, etc.).
- O projeto foi pensado para ser simples de manter e expandir (por exemplo, adicionar novos motivos, novos gráficos ou exportações).
*** End Patch】***
