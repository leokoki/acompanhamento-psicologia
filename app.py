import streamlit as st
import pandas as pd
from datetime import datetime

import database as db


# Mapeamento de DDD para estado (UF) usado para preencher o campo de estado automaticamente
DDD_TO_ESTADO = {
    # Norte / Nordeste / Centro-Oeste / Sudeste / Sul
    "68": "AC", "82": "AL", "96": "AP", "92": "AM", "97": "AM",
    "71": "BA", "73": "BA", "74": "BA", "75": "BA", "77": "BA",
    "85": "CE", "88": "CE",
    "61": "DF",
    "27": "ES", "28": "ES",
    "62": "GO", "64": "GO",
    "98": "MA", "99": "MA",
    "65": "MT", "66": "MT",
    "67": "MS",
    "31": "MG", "32": "MG", "33": "MG", "34": "MG",
    "35": "MG", "37": "MG", "38": "MG",
    "91": "PA", "93": "PA", "94": "PA",
    "83": "PB",
    "41": "PR", "42": "PR", "43": "PR", "44": "PR",
    "45": "PR", "46": "PR",
    "81": "PE", "87": "PE",
    "86": "PI", "89": "PI",
    "21": "RJ", "22": "RJ", "24": "RJ",
    "84": "RN",
    "69": "RO",
    "95": "RR",
    "51": "RS", "53": "RS", "54": "RS", "55": "RS",
    "47": "SC", "48": "SC", "49": "SC",
    "11": "SP", "12": "SP", "13": "SP", "14": "SP",
    "15": "SP", "16": "SP", "17": "SP", "18": "SP", "19": "SP",
    "79": "SE",
    "63": "TO",
}


# Função utilitária para converter um DDD digitado pelo usuário em uma sigla de estado (UF)
def ddd_to_estado(ddd: str) -> str:
    """Retorna a UF a partir do DDD, ou vazio se não encontrado."""
    if not ddd:
        return ""
    ddd = "".join(filter(str.isdigit, str(ddd)))[:3]
    return DDD_TO_ESTADO.get(ddd, "")


def tela_login():
    """Tela de login simples baseada em senhas configuradas no secrets.toml."""
    # Se já estiver autenticado, não mostra nada
    if "auth_role" in st.session_state and st.session_state.auth_role in ("admin", "viewer"):
        return

    st.title("Login - Acompanhamento Psicologia")

    if "auth_role" not in st.session_state:
        st.session_state.auth_role = None

    senha = st.text_input("Digite a senha", type="password")
    entrar = st.button("Entrar")

    if entrar:
        senha_admin = st.secrets["app"]["password"]
        senha_viewer = st.secrets["app"]["password_viewer"]

        if senha == senha_admin:
            st.session_state.auth_role = "admin"
            st.success("Login realizado como administrador.")
            st.rerun()
        elif senha == senha_viewer:
            st.session_state.auth_role = "viewer"
            st.success("Login realizado como visualizador.")
            st.rerun()
        else:
            st.error("Senha incorreta. Tente novamente.")

    # Se ainda não estiver autenticado, interrompe a execução do app aqui
    if st.session_state.auth_role is None:
        st.stop()


# Tela 1: dashboards com visão semanal, mensal e gráfico de contatos por estado
def tela_dashboards():
    st.title("Acompanhamento de Contatos - Psicologia")
    st.subheader("Visão Geral")

    leads_df = db.get_whatsapp_leads()

    if leads_df.empty:
        st.info("Ainda não há registros de contatos.")
        return

    # Garantir tipos de data
    if "data_contato" in leads_df.columns:
        leads_df["data_contato"] = pd.to_datetime(leads_df["data_contato"], errors="coerce")

    col1, col2, col3 = st.columns(3)

    hoje = pd.Timestamp.today().normalize()
    inicio_semana = hoje - pd.to_timedelta(hoje.weekday(), unit="D")
    inicio_mes = hoje.replace(day=1)

    contatos_semana = leads_df[leads_df["data_contato"] >= inicio_semana]
    contatos_mes = leads_df[leads_df["data_contato"] >= inicio_mes]

    with col1:
        st.metric("Contatos na semana", len(contatos_semana))
    with col2:
        st.metric("Contatos no mês", len(contatos_mes))
    with col3:
        st.metric("Total de contatos", len(leads_df))

    st.markdown("---")
    st.subheader("Distribuição por Estado (a partir do DDD)")

    if "estado" in leads_df.columns and not leads_df["estado"].isna().all():
        estado_counts = (
            leads_df[leads_df["estado"].notna() & (leads_df["estado"] != "")]
            .groupby("estado")
            .size()
            .reset_index(name="quantidade")
            .sort_values("quantidade", ascending=False)
        )

        if not estado_counts.empty:
            st.bar_chart(
                estado_counts.set_index("estado")["quantidade"],
            )
        else:
            st.info("Nenhum estado encontrado a partir dos DDDs cadastrados.")
    else:
        st.info("Nenhum estado encontrado a partir dos DDDs cadastrados.")

    # Gráfico 1: número de contatos por dia da semana
    st.markdown("---")
    st.subheader("Contatos por dia da semana")

    if "data_contato" in leads_df.columns:
        df_sem_data_nula = leads_df.dropna(subset=["data_contato"]).copy()
        if not df_sem_data_nula.empty:
            df_sem_data_nula["dia_semana_idx"] = df_sem_data_nula["data_contato"].dt.dayofweek
            mapa_dias = {
                0: "Seg",
                1: "Ter",
                2: "Qua",
                3: "Qui",
                4: "Sex",
                5: "Sáb",
                6: "Dom",
            }
            df_sem_data_nula["dia_semana"] = df_sem_data_nula["dia_semana_idx"].map(mapa_dias)
            ordem = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
            contatos_por_dia = (
                df_sem_data_nula.groupby("dia_semana")
                .size()
                .reindex(ordem, fill_value=0)
                .reset_index(name="quantidade")
            )

            st.bar_chart(
                contatos_por_dia.set_index("dia_semana")["quantidade"],
            )
        else:
            st.info("Não há datas de contato válidas para calcular os dias da semana.")
    else:
        st.info("A coluna 'data_contato' não foi encontrada na base.")

    # Gráfico 2: motivos semanal e mensal
    st.markdown("---")
    st.subheader("Motivos dos contatos - semanal x mensal")

    col_motivo_semana, col_motivo_mes = st.columns(2)

    with col_motivo_semana:
        st.caption("Últimos 7 dias (semana atual)")
        if "motivo" in contatos_semana.columns and not contatos_semana.empty:
            motivos_semana = (
                contatos_semana.groupby("motivo")
                .size()
                .reset_index(name="quantidade")
                .sort_values("quantidade", ascending=False)
            )
            st.bar_chart(
                motivos_semana.set_index("motivo")["quantidade"],
            )
        else:
            st.info("Não há contatos na semana atual para agrupar por motivo.")

    with col_motivo_mes:
        st.caption("Mês atual")
        if "motivo" in contatos_mes.columns and not contatos_mes.empty:
            motivos_mes = (
                contatos_mes.groupby("motivo")
                .size()
                .reset_index(name="quantidade")
                .sort_values("quantidade", ascending=False)
            )
            st.bar_chart(
                motivos_mes.set_index("motivo")["quantidade"],
            )
        else:
            st.info("Não há contatos no mês atual para agrupar por motivo.")


# Tela 2: formulário para cadastrar novos contatos recebidos via WhatsApp
def tela_cadastro():
    st.title("Cadastro de Contatos - WhatsApp")

    with st.form("form_cadastro_contato"):
        col1, col2, col3 = st.columns(3)

        with col1:
            ddd = st.text_input("DDD*", max_chars=3)
            sexo = st.selectbox("Sexo*", ["M", "F"])
            fechou = st.selectbox("Fechou*", ["Sim", "Não"])

        with col2:
            numero = st.text_input("Número (opcional)", help="Somente o número, sem DDD.")
            motivo = st.selectbox(
                "Motivo*",
                ["Aguardando", "Não retornou", "Preço"],
            )

        today = datetime.today().date()
        with col3:
            data_contato = st.date_input("Dia do contato", value=today, format="DD/MM/YYYY")
            data_ultima_atualizacao = st.date_input(
                "Dia da última atualização",
                value=today,
                format="DD/MM/YYYY",
                disabled=True,
            )

        estado = ddd_to_estado(ddd)
        st.text_input("Estado (auto pelo DDD)", value=estado, disabled=True)

        submitted = st.form_submit_button("Salvar contato")

    if submitted:
        if not ddd or not ddd.strip():
            st.error("Informe o DDD.")
            return

        if not estado:
            st.error("DDD não reconhecido. Verifique o DDD informado.")
            return

        data_contato_str = data_contato.strftime("%Y-%m-%d") if data_contato else ""
        data_ultima_atualizacao_str = data_contato_str

        sucesso = db.add_whatsapp_lead(
            ddd=ddd,
            numero=numero,
            sexo=sexo,
            fechou=fechou,
            motivo=motivo,
            estado=estado,
            data_contato=data_contato_str,
            data_ultima_atualizacao=data_ultima_atualizacao_str,
        )

        if sucesso:
            st.success("Contato salvo com sucesso no Google Sheets!")
        else:
            st.error("Não foi possível salvar o contato. Verifique a conexão com o Google Sheets.")


# Tela 3: listagem e edição de registros já salvos na planilha
def tela_edicao():
    st.title("Edição de Contatos")

    leads_df = db.get_whatsapp_leads()

    if leads_df.empty:
        st.info("Ainda não há registros para editar.")
        return

    st.subheader("Registros atuais")
    st.dataframe(leads_df)

    # Selecionar registro pelo ID
    if "id" not in leads_df.columns:
        st.error("A planilha de contatos não possui a coluna 'id'.")
        return

    ids = leads_df["id"].tolist()
    id_escolhido = st.selectbox("Selecione o ID para editar", ids)

    registro = leads_df[leads_df["id"] == id_escolhido].iloc[0]
    motivo_original = registro.get("motivo", "Aguardando")
    data_contato_original = registro.get("data_contato", "")
    data_ultima_atualizacao_original = registro.get("data_ultima_atualizacao", "")

    # Converter datas de string para date para exibir no form
    def _parse_data(valor_str):
        try:
            if pd.isna(valor_str) or valor_str == "":
                return None
            return pd.to_datetime(valor_str).date()
        except Exception:
            return None

    data_contato_date = _parse_data(data_contato_original)
    data_ultima_atualizacao_date = _parse_data(data_ultima_atualizacao_original)

    with st.form("form_edicao_contato"):
        col1, col2, col3 = st.columns(3)

        with col1:
            ddd = st.text_input("DDD*", value=str(registro.get("ddd", "")), max_chars=3)
            sexo = st.selectbox(
                "Sexo*",
                ["M", "F"],
                index=0 if registro.get("sexo", "M") == "M" else 1,
            )
            fechou = st.selectbox(
                "Fechou*",
                ["Sim", "Não"],
                index=0 if registro.get("fechou", "Não") == "Sim" else 1,
            )

        with col2:
            numero = st.text_input(
                "Número (opcional)",
                value=str(registro.get("numero", "")) if pd.notna(registro.get("numero", "")) else "",
            )
            motivo_atual = motivo_original
            motivos = ["Aguardando", "Não retornou", "Preço"]
            motivo_index = motivos.index(motivo_atual) if motivo_atual in motivos else 0
            motivo = st.selectbox("Motivo*", motivos, index=motivo_index)

        with col3:
            data_contato_input = st.date_input(
                "Dia do contato",
                value=data_contato_date or datetime.today().date(),
                format="DD/MM/YYYY",
            )
            data_ultima_atualizacao_input = st.date_input(
                "Dia da última atualização",
                value=data_ultima_atualizacao_date or datetime.today().date(),
                format="DD/MM/YYYY",
                disabled=True,
            )

        estado = ddd_to_estado(ddd)
        st.text_input("Estado (auto pelo DDD)", value=estado, disabled=True)

        submitted = st.form_submit_button("Salvar alterações")

    if submitted:
        if not ddd or not ddd.strip():
            st.error("Informe o DDD.")
            return

        if not estado:
            st.error("DDD não reconhecido. Verifique o DDD informado.")
            return

        # Datas em string para salvar
        data_contato_str = (
            data_contato_input.strftime("%Y-%m-%d") if data_contato_input else data_contato_original
        )

        # Se o motivo foi alterado, atualiza automaticamente a data da última atualização para hoje
        if motivo != motivo_original:
            nova_data_ultima_atualizacao = datetime.today().date()
            data_ultima_atualizacao_str = nova_data_ultima_atualizacao.strftime("%Y-%m-%d")
        else:
            # Mantém o valor original
            if data_ultima_atualizacao_date:
                data_ultima_atualizacao_str = data_ultima_atualizacao_date.strftime("%Y-%m-%d")
            else:
                data_ultima_atualizacao_str = ""

        sucesso = db.update_whatsapp_lead(
            lead_id=int(id_escolhido),
            ddd=ddd,
            numero=numero,
            sexo=sexo,
            fechou=fechou,
            motivo=motivo,
            estado=estado,
            data_contato=data_contato_str,
            data_ultima_atualizacao=data_ultima_atualizacao_str,
        )

        if sucesso:
            st.success("Registro atualizado com sucesso no Google Sheets!")
        else:
            st.error("Não foi possível atualizar o registro. Verifique a planilha no Google Sheets.")


# Função principal que configura a página e faz o roteamento entre as três telas
def main():
    st.set_page_config(
        page_title="Acompanhamento Psicologia - WhatsApp",
        layout="wide",
    )

    # Controle de autenticação
    tela_login()

    role = st.session_state.get("auth_role", "viewer")

    st.sidebar.title("Navegação")

    st.sidebar.markdown(f"**Perfil:** {'Admin' if role == 'admin' else 'Visualizador'}")
    if st.sidebar.button("Sair"):
        st.session_state.auth_role = None
        st.rerun()

    if role == "admin":
        opcoes = ("Dashboards", "Cadastro", "Edição")
    else:
        opcoes = ("Dashboards",)

    pagina = st.sidebar.radio("Ir para", opcoes)

    if pagina == "Dashboards":
        tela_dashboards()
    elif pagina == "Cadastro":
        tela_cadastro()
    else:
        tela_edicao()


if __name__ == "__main__":
    main()
