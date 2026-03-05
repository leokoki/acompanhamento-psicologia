import streamlit as st
import pandas as pd
from datetime import datetime

import database as db

try:
    import altair as alt
except ImportError:
    alt = None


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

    with st.form("login_form"):
        senha = st.text_input("Digite a senha", type="password")
        entrar = st.form_submit_button("Entrar")

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


# Tela 1: dashboards alinhados ao notebook de análise (público + motivos + semanal/mensal)
def tela_dashboards():
    st.title("Acompanhamento de Contatos - Psicologia")

    leads_df = db.get_whatsapp_leads()

    if leads_df.empty:
        st.info("Ainda não há registros de contatos.")
        return

    # Coluna de data no formato YYYY-mm-dd (ex.: do Google Sheets)
    if "data_contato" in leads_df.columns:
        leads_df["data_contato"] = pd.to_datetime(
            leads_df["data_contato"], format="%Y-%m-%d", errors="coerce"
        )

    # Janelas de tempo (alinhado ao notebook: semana = últimos 7 dias, mês = desde dia 1)
    hoje = pd.Timestamp.today().normalize()
    inicio_semana = hoje - pd.Timedelta(days=6)
    inicio_mes = hoje.replace(day=1)
    leads_df["_data_norm"] = leads_df["data_contato"].dt.normalize()
    contatos_semana = leads_df[leads_df["_data_norm"] >= inicio_semana]
    contatos_mes = leads_df[leads_df["_data_norm"] >= inicio_mes]

    # ---------- Visão geral (métricas) ----------
    st.subheader("Visão geral")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Contatos na semana (últimos 7 dias)", len(contatos_semana))
    with col2:
        st.metric("Contatos no mês", len(contatos_mes))
    with col3:
        st.metric("Total de contatos", len(leads_df))

    # ---------- 1. Entender o público que está chegando ----------
    st.markdown("---")
    st.subheader("1. Público que está chegando")

    st.caption("Contatos por Estado (origem do público)")
    if "estado" in leads_df.columns and not leads_df["estado"].isna().all():
        estado_counts = (
            leads_df[leads_df["estado"].notna() & (leads_df["estado"] != "")]
            .groupby("estado")
            .size()
            .reset_index(name="quantidade")
            .sort_values("quantidade", ascending=True)
        )
        if not estado_counts.empty:
            st.bar_chart(estado_counts.set_index("estado")["quantidade"])
        else:
            st.info("Nenhum estado encontrado.")
    else:
        st.info("Nenhum estado encontrado.")

    col_sexo, col_dia_semana = st.columns(2)
    with col_sexo:
        st.caption("Contatos por Sexo")
        if "sexo" in leads_df.columns:
            sexo_counts = leads_df["sexo"].value_counts()
            if not sexo_counts.empty:
                st.bar_chart(sexo_counts)
            else:
                st.info("Sem dados de sexo.")
        else:
            st.info("Coluna 'sexo' não encontrada.")

    with col_dia_semana:
        st.caption("Contatos por dia da semana")
        if "data_contato" in leads_df.columns:
            df_ok = leads_df.dropna(subset=["data_contato"]).copy()
            if not df_ok.empty:
                mapa_dias = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sáb", 6: "Dom"}
                df_ok["dia_semana"] = df_ok["data_contato"].dt.dayofweek.map(mapa_dias)
                ordem = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
                por_dia = (
                    df_ok.groupby("dia_semana").size().reindex(ordem, fill_value=0).reset_index(name="quantidade")
                )
                st.bar_chart(por_dia.set_index("dia_semana")["quantidade"])
            else:
                st.info("Sem datas válidas.")
        else:
            st.info("Coluna 'data_contato' não encontrada.")

    st.caption("Contatos por dia (ao longo do tempo)")
    if "data_contato" in leads_df.columns:
        df_por_data = leads_df.dropna(subset=["data_contato"]).copy()
        df_por_data["_data"] = df_por_data["data_contato"].dt.strftime("%Y-%m-%d")
        por_data = df_por_data.groupby("_data").size().reset_index(name="quantidade")
        if not por_data.empty:
            st.bar_chart(por_data.set_index("_data")["quantidade"])
        else:
            st.info("Sem datas válidas para exibir.")

    # ---------- 2. Por que não fecharam ----------
    st.markdown("---")
    st.subheader("2. Por que não fecharam")

    if "motivo" in leads_df.columns:
        por_motivo = leads_df["motivo"].value_counts().reset_index(name="quantidade")
        por_motivo.columns = ["motivo", "quantidade"]
        col_barras, col_pizza = st.columns(2)
        with col_barras:
            st.caption("Contatos por motivo (não fechou)")
            if not por_motivo.empty:
                st.bar_chart(por_motivo.set_index("motivo")["quantidade"])
        with col_pizza:
            st.caption("Proporção por motivo")
            if not por_motivo.empty and alt is not None:
                chart_pie = (
                    alt.Chart(por_motivo)
                    .mark_arc(innerRadius=0)
                    .encode(
                        theta=alt.Theta("quantidade:Q", stack=True),
                        color=alt.Color("motivo:N", legend=alt.Legend(title="Motivo")),
                    )
                )
                st.altair_chart(chart_pie, use_container_width=True)
            elif not por_motivo.empty:
                st.bar_chart(por_motivo.set_index("motivo")["quantidade"])
    else:
        st.info("Coluna 'motivo' não encontrada.")

    st.caption("Motivo de não fechamento por Estado")
    if "estado" in leads_df.columns and "motivo" in leads_df.columns and alt is not None:
        cross = pd.crosstab(leads_df["estado"], leads_df["motivo"]).reset_index()
        cross_long = cross.melt(id_vars="estado", var_name="motivo", value_name="quantidade")
        cross_long = cross_long[cross_long["quantidade"] > 0]
        if not cross_long.empty:
            chart_cross = (
                alt.Chart(cross_long)
                .mark_bar()
                .encode(
                    x=alt.X("estado:N", title="Estado"),
                    y=alt.Y("quantidade:Q", title="Quantidade"),
                    color=alt.Color("motivo:N", legend=alt.Legend(title="Motivo")),
                )
            )
            st.altair_chart(chart_cross, use_container_width=True)
        else:
            st.info("Sem dados para motivo × estado.")
    elif "estado" in leads_df.columns and "motivo" in leads_df.columns:
        cross = pd.crosstab(leads_df["estado"], leads_df["motivo"])
        if not cross.empty:
            st.bar_chart(cross)
        else:
            st.info("Sem dados para motivo × estado.")

    st.caption("Motivos ao longo do tempo")
    if "data_contato" in leads_df.columns and "motivo" in leads_df.columns and alt is not None:
        df_ok = leads_df.dropna(subset=["data_contato"]).copy()
        df_ok["_data"] = df_ok["data_contato"].dt.strftime("%Y-%m-%d")
        cross_t = pd.crosstab(df_ok["_data"], df_ok["motivo"]).reset_index()
        cross_t_long = cross_t.melt(id_vars="_data", var_name="motivo", value_name="quantidade")
        cross_t_long = cross_t_long[cross_t_long["quantidade"] > 0]
        if not cross_t_long.empty:
            chart_stacked = (
                alt.Chart(cross_t_long)
                .mark_bar()
                .encode(
                    x=alt.X("_data:O", title="Data"),
                    y=alt.Y("quantidade:Q", title="Quantidade"),
                    color=alt.Color("motivo:N", legend=alt.Legend(title="Motivo")),
                )
            )
            st.altair_chart(chart_stacked, use_container_width=True)
        else:
            st.info("Sem dados para motivos ao longo do tempo.")
    elif "data_contato" in leads_df.columns and "motivo" in leads_df.columns:
        df_ok = leads_df.dropna(subset=["data_contato"]).copy()
        df_ok["_data"] = df_ok["data_contato"].dt.strftime("%Y-%m-%d")
        cross_t = pd.crosstab(df_ok["_data"], df_ok["motivo"])
        if not cross_t.empty:
            st.bar_chart(cross_t)
        else:
            st.info("Sem dados para motivos ao longo do tempo.")

    # ---------- 3. Análise semanal e mensal ----------
    st.markdown("---")
    st.subheader("3. Análise semanal e mensal")

    st.caption("Motivos: última semana vs mês atual")
    col_s, col_m = st.columns(2)
    with col_s:
        st.write("**Últimos 7 dias**")
        if not contatos_semana.empty and "motivo" in contatos_semana.columns:
            ms = contatos_semana.groupby("motivo").size().reset_index(name="quantidade")
            st.bar_chart(ms.set_index("motivo")["quantidade"])
        else:
            st.info("Sem contatos na semana.")
    with col_m:
        st.write("**Mês atual**")
        if not contatos_mes.empty and "motivo" in contatos_mes.columns:
            mm = contatos_mes.groupby("motivo").size().reset_index(name="quantidade")
            st.bar_chart(mm.set_index("motivo")["quantidade"])
        else:
            st.info("Sem contatos no mês.")

    st.caption("Público por Estado: semana vs mês")
    col_est_s, col_est_m = st.columns(2)
    with col_est_s:
        st.write("**Últimos 7 dias**")
        if not contatos_semana.empty and "estado" in contatos_semana.columns:
            es = (
                contatos_semana[contatos_semana["estado"].notna() & (contatos_semana["estado"] != "")]
                .groupby("estado")
                .size()
                .sort_values(ascending=True)
                .reset_index(name="quantidade")
            )
            if not es.empty:
                st.bar_chart(es.set_index("estado")["quantidade"])
            else:
                st.info("Sem estados na semana.")
        else:
            st.info("Sem contatos na semana.")
    with col_est_m:
        st.write("**Mês atual**")
        if not contatos_mes.empty and "estado" in contatos_mes.columns:
            em = (
                contatos_mes[contatos_mes["estado"].notna() & (contatos_mes["estado"] != "")]
                .groupby("estado")
                .size()
                .sort_values(ascending=True)
                .reset_index(name="quantidade")
            )
            if not em.empty:
                st.bar_chart(em.set_index("estado")["quantidade"])
            else:
                st.info("Sem estados no mês.")
        else:
            st.info("Sem contatos no mês.")

    st.caption("Evolução mês a mês")
    if "data_contato" in leads_df.columns:
        leads_df["_mes"] = leads_df["data_contato"].dt.to_period("M").astype(str)
        por_mes = leads_df.groupby("_mes").size().reset_index(name="quantidade")
        if not por_mes.empty:
            st.bar_chart(por_mes.set_index("_mes")["quantidade"])
        else:
            st.info("Sem dados por mês.")

    st.caption("Motivos por mês (empilhado)")
    if "data_contato" in leads_df.columns and "motivo" in leads_df.columns and alt is not None:
        df_m = leads_df.dropna(subset=["data_contato", "motivo"]).copy()
        df_m["_mes"] = df_m["data_contato"].dt.to_period("M").astype(str)
        cross_mes = pd.crosstab(df_m["_mes"], df_m["motivo"]).reset_index()
        cross_mes_long = cross_mes.melt(id_vars="_mes", var_name="motivo", value_name="quantidade")
        cross_mes_long = cross_mes_long[cross_mes_long["quantidade"] > 0]
        if not cross_mes_long.empty:
            chart_mes = (
                alt.Chart(cross_mes_long)
                .mark_bar()
                .encode(
                    x=alt.X("_mes:O", title="Mês"),
                    y=alt.Y("quantidade:Q", title="Quantidade"),
                    color=alt.Color("motivo:N", legend=alt.Legend(title="Motivo")),
                )
            )
            st.altair_chart(chart_mes, use_container_width=True)
        else:
            st.info("Sem dados para motivos por mês.")
    elif "data_contato" in leads_df.columns and "motivo" in leads_df.columns:
        leads_df["_mes"] = leads_df["data_contato"].dt.to_period("M").astype(str)
        cross_mes = pd.crosstab(leads_df["_mes"], leads_df["motivo"])
        if not cross_mes.empty:
            st.bar_chart(cross_mes)
        else:
            st.info("Sem dados para motivos por mês.")


# Tela 2: formulário para cadastrar novos contatos recebidos via WhatsApp
def tela_cadastro():
    st.title("Cadastro de Contatos - WhatsApp")

    with st.form("form_cadastro_contato"):
        col1, col2, col3 = st.columns(3)

        with col1:
            ddd = st.text_input("DDD*", max_chars=3)
            sexo = st.selectbox("Sexo*", ["M", "F"], index=1)
            fechou = st.selectbox("Fechou*", ["Sim", "Não"], index=1)

        with col2:
            numero = st.text_input("Número (opcional)", help="Somente o número, sem DDD.")
            motivo = st.selectbox(
                "Motivo*",
                ["Aguardando", "Não retornou", "Preço", "Público Errado", "Convênio"],
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

    # Coluna de data no formato YYYY-mm-dd: converter para date e exibir no form
    def _parse_data(valor_str):
        try:
            if pd.isna(valor_str) or valor_str == "":
                return None
            dt = pd.to_datetime(valor_str, format="%Y-%m-%d", errors="coerce")
            return dt.date() if pd.notna(dt) else None
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
                ["F", "M"],
                index=0 if registro.get("sexo", "F") == "F" else 1,
            )
            fechou = st.selectbox(
                "Fechou*",
                ["Não", "Sim"],
                index=0 if registro.get("fechou", "Não") == "Não" else 1,
            )

        with col2:
            numero = st.text_input(
                "Número (opcional)",
                value=str(registro.get("numero", "")) if pd.notna(registro.get("numero", "")) else "",
            )
            motivo_atual = motivo_original
            motivos = ["Aguardando", "Não retornou", "Preço", "Público Errado", "Convênio"]
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
