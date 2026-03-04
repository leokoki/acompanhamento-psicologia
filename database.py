import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime
import streamlit as st
import json


# Bloco de conexão genérica com o Google Sheets usando as credenciais do Streamlit
def get_sheets_client():
    """Conecta ao Google Sheets usando credenciais do Streamlit Secrets"""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    # Pega as credenciais do Streamlit Secrets
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    return client

def get_spreadsheet():
    """Retorna a planilha do Google Sheets"""
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            creds_dict,
            scopes=["https://www.googleapis.com/auth/spreadsheets", 
                    "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)

        # ✅ Agora vem dos Secrets
        sheet_id = st.secrets["app"]["sheet_id"]
        sheet = client.open_by_key(sheet_id)
        return sheet

    except Exception as e:
        st.error(f"Erro ao conectar com Google Sheets: {e}")
        return None


# Bloco de funções relacionadas à aba "clients" (cadastro de clientes da clínica)
def get_clients():
    """Retorna todos os clientes"""
    sheet = get_spreadsheet()
    worksheet = sheet.worksheet("clients")
    data = worksheet.get_all_records()
    df = pd.DataFrame(data)
    return df

def get_active_clients():
    """Retorna apenas clientes ativos"""
    df = get_clients()
    if not df.empty:
        return df[df['status'] == 'active']
    return df

def add_client(name, email, phone):
    """Adiciona um novo cliente"""
    try:
        sheet = get_spreadsheet()
        if sheet is None:
            return False

        worksheet = sheet.worksheet("clients")

        # ✅ Se email estiver vazio, usar email padrão
        if not email or email.strip() == "":
            email = "naotenho@gmail.com"

        # Pegar o próximo ID
        existing_data = worksheet.get_all_records()
        next_id = len(existing_data) + 1

        # Data atual
        created_at = datetime.now().strftime("%Y-%m-%d")

        # Adicionar linha
        new_row = [next_id, name, email, phone, created_at, "active"]
        worksheet.append_row(new_row)

        return True

    except Exception as e:
        st.error(f"❌ Erro ao adicionar cliente: {e}")
        return False


# Bloco de funções relacionadas à aba "sessions" (sessões realizadas com clientes)
def get_sessions():
    """Retorna todas as sessões com nome do cliente"""
    sheet = get_spreadsheet()
    sessions_ws = sheet.worksheet("sessions")
    clients_ws = sheet.worksheet("clients")

    sessions_data = sessions_ws.get_all_records()
    clients_data = clients_ws.get_all_records()

    sessions_df = pd.DataFrame(sessions_data)
    clients_df = pd.DataFrame(clients_data)

    if not sessions_df.empty and not clients_df.empty:
        # Merge para pegar o nome do cliente
        merged = sessions_df.merge(
            clients_df[['id', 'name']], 
            left_on='client_id', 
            right_on='id', 
            how='left'
        )
        merged.rename(columns={'name': 'client_name'}, inplace=True)
        merged.drop(columns=['id_y'], inplace=True)
        merged.rename(columns={'id_x': 'id'}, inplace=True)
        return merged

    return pd.DataFrame()

def add_session(client_id, session_date, amount, payment_method, notes=""):
    """Adiciona uma nova sessão"""
    sheet = get_spreadsheet()
    worksheet = sheet.worksheet("sessions")

    # Pega o próximo ID
    data = worksheet.get_all_records()
    next_id = len(data) + 1

    # Adiciona nova linha
    row = [
        next_id,
        client_id,
        session_date,
        amount,
        payment_method,
        notes
    ]
    worksheet.append_row(row)


# Bloco de funções de estatística/relatórios financeiros a partir das sessões
def get_monthly_revenue():
    """Retorna receita mensal dos últimos 12 meses"""
    df = get_sessions()

    if df.empty:
        return pd.DataFrame()

    df['session_date'] = pd.to_datetime(df['session_date'])
    df['month'] = df['session_date'].dt.to_period('M').astype(str)

    # Últimos 12 meses
    df = df[df['session_date'] >= pd.Timestamp.now() - pd.DateOffset(months=12)]

    monthly = df.groupby('month').agg({
        'amount': 'sum',
        'id': 'count'
    }).reset_index()

    monthly.columns = ['month', 'total_revenue', 'num_sessions']

    return monthly


def get_active_clients_per_month():
    """Retorna número de clientes ativos por mês"""
    df = get_sessions()

    if df.empty:
        return pd.DataFrame()

    df['session_date'] = pd.to_datetime(df['session_date'])
    df['month'] = df['session_date'].dt.to_period('M').astype(str)

    # Últimos 12 meses
    df = df[df['session_date'] >= pd.Timestamp.now() - pd.DateOffset(months=12)]

    monthly = df.groupby('month')['client_id'].nunique().reset_index()
    monthly.columns = ['month', 'active_clients']

    return monthly


def get_current_month_stats():
    """Retorna estatísticas do mês atual"""
    df = get_sessions()

    if df.empty:
        return {"receita": 0, "sessoes": 0, "change": 0}

    df['session_date'] = pd.to_datetime(df['session_date'])

    current_month = pd.Timestamp.now().to_period('M')
    previous_month = (pd.Timestamp.now() - pd.DateOffset(months=1)).to_period('M')

    current_data = df[df['session_date'].dt.to_period('M') == current_month]
    previous_data = df[df['session_date'].dt.to_period('M') == previous_month]

    current_revenue = current_data['amount'].sum() if not current_data.empty else 0
    previous_revenue = previous_data['amount'].sum() if not previous_data.empty else 0

    change = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue > 0 else 0

    return {
        "receita": current_revenue,
        "sessoes": len(current_data),
        "change": change
    }


def get_ytd_stats():
    """Retorna estatísticas do ano até agora"""
    df = get_sessions()

    if df.empty:
        return {"receita": 0, "change": 0}

    df['session_date'] = pd.to_datetime(df['session_date'])

    current_year = pd.Timestamp.now().year
    previous_year = current_year - 1
    current_month = pd.Timestamp.now().month

    current_ytd = df[
        (df['session_date'].dt.year == current_year)
    ]['amount'].sum()

    previous_ytd = df[
        (df['session_date'].dt.year == previous_year) &
        (df['session_date'].dt.month <= current_month)
    ]['amount'].sum()

    change = ((current_ytd - previous_ytd) / previous_ytd * 100) if previous_ytd > 0 else 0

    return {
        "receita": current_ytd,
        "change": change
    }


def get_sessions_per_client_current_month():
    """Retorna número de sessões por cliente no mês atual"""
    df = get_sessions()

    if df.empty:
        return pd.DataFrame()

    df['session_date'] = pd.to_datetime(df['session_date'])
    current_month = pd.Timestamp.now().to_period('M')

    current_data = df[df['session_date'].dt.to_period('M') == current_month]

    if current_data.empty:
        return pd.DataFrame()

    result = current_data.groupby('client_name').agg({
        'id': 'count',
        'amount': 'sum'
    }).reset_index()

    result.columns = ['name', 'num_sessions', 'total_amount']
    result = result.sort_values('num_sessions', ascending=False)

    return result


# ==========================
# WhatsApp Leads - Contatos
# ==========================
# Bloco específico para controlar os contatos que chegam via WhatsApp,
# em uma aba separada da planilha, usada pelo app de acompanhamento.
def get_whatsapp_leads_worksheet():
    """Retorna a worksheet de leads de WhatsApp; cria se não existir."""
    sheet = get_spreadsheet()
    if sheet is None:
        return None

    try:
        ws = sheet.worksheet("whatsapp_leads")
    except gspread.WorksheetNotFound:
        # Cria worksheet com cabeçalho padrão
        ws = sheet.add_worksheet(title="whatsapp_leads", rows=1000, cols=9)
        ws.update(
            "A1:I1",
            [[
                "id",
                "data_contato",
                "ddd",
                "numero",
                "sexo",
                "fechou",
                "motivo",
                "estado",
                "data_ultima_atualizacao",
            ]],
        )
    return ws


def get_whatsapp_leads():
    """Retorna todos os contatos de WhatsApp em um DataFrame.

    Implementado de forma defensiva para lidar com planilhas vazias,
    evitando o erro de IndexError do gspread quando não há linhas.
    """
    ws = get_whatsapp_leads_worksheet()
    if ws is None:
        return pd.DataFrame()

    try:
        # Lê todos os valores crus da worksheet
        values = ws.get_all_values()
    except Exception:
        # Em caso de qualquer problema na leitura, retorna DataFrame vazio
        return pd.DataFrame()

    # Se não houver nenhuma linha na planilha
    if not values:
        return pd.DataFrame()

    # Primeira linha é o cabeçalho
    header = values[0]
    rows = values[1:]

    # Se só há cabeçalho e nenhuma linha de dados
    if not rows:
        return pd.DataFrame(columns=header)

    df = pd.DataFrame(rows, columns=header)

    # Converter colunas numéricas/inteiras conhecidas
    if "id" in df.columns:
        df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("Int64")

    return df


def add_whatsapp_lead(ddd, numero, sexo, fechou, motivo, estado, data_contato, data_ultima_atualizacao):
    """Adiciona um novo contato de WhatsApp."""
    try:
        ws = get_whatsapp_leads_worksheet()
        if ws is None:
            return False

        # Lê todos os valores crus para calcular o próximo ID
        values = ws.get_all_values() or []

        # Se a planilha estiver completamente vazia (sem cabeçalho),
        # criamos o cabeçalho padrão e começamos do ID 1.
        if not values:
            ws.update(
                "A1:I1",
                [[
                    "id",
                    "data_contato",
                    "ddd",
                    "numero",
                    "sexo",
                    "fechou",
                    "motivo",
                    "estado",
                    "data_ultima_atualizacao",
                ]],
            )
            next_id = 1
        else:
            # Garante que existe pelo menos o cabeçalho
            header = values[0]
            if not header or header[0] != "id" or len(header) < 9:
                ws.update(
                    "A1:I1",
                    [[
                        "id",
                        "data_contato",
                        "ddd",
                        "numero",
                        "sexo",
                        "fechou",
                        "motivo",
                        "estado",
                        "data_ultima_atualizacao",
                    ]],
                )
                values = ws.get_all_values() or []

            # Coleta todos os IDs já existentes (coluna A a partir da linha 2)
            existing_ids = []
            for row in values[1:]:
                if row and len(row) > 0 and row[0]:
                    try:
                        existing_ids.append(int(row[0]))
                    except ValueError:
                        continue

            next_id = (max(existing_ids) + 1) if existing_ids else 1

        # Datas são recebidas já formatadas como string

        new_row = [
            next_id,
            data_contato,
            ddd,
            numero or "",
            sexo,
            fechou,
            motivo,
            estado,
            data_ultima_atualizacao or "",
        ]

        ws.append_row(new_row)
        return True
    except Exception as e:
        st.error(f"❌ Erro ao adicionar contato de WhatsApp: {e}")
        return False


def update_whatsapp_lead(lead_id: int, ddd, numero, sexo, fechou, motivo, estado, data_contato, data_ultima_atualizacao):
    """Atualiza um contato de WhatsApp existente identificado por id."""
    try:
        ws = get_whatsapp_leads_worksheet()
        if ws is None:
            return False

        records = ws.get_all_records()
        if not records:
            return False

        # Localizar linha pela coluna 'id'
        row_to_update = None
        data_contato_original = ""
        data_ultima_atualizacao_original = ""

        for idx, rec in enumerate(records, start=2):  # dados começam na linha 2
            if rec.get("id") == lead_id:
                row_to_update = idx
                data_contato_original = rec.get("data_contato", "")
                data_ultima_atualizacao_original = rec.get("data_ultima_atualizacao", "")
                break

        if row_to_update is None:
            return False

        updated_row = [
            lead_id,
            data_contato or data_contato_original,
            ddd,
            numero or "",
            sexo,
            fechou,
            motivo,
            estado,
            data_ultima_atualizacao or data_ultima_atualizacao_original,
        ]

        ws.update(f"A{row_to_update}:I{row_to_update}", [updated_row])
        return True
    except Exception as e:
        st.error(f"❌ Erro ao atualizar contato de WhatsApp: {e}")
        return False
