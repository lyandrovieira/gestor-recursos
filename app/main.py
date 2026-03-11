import streamlit as st
import sqlite3
import os
import datetime
import pandas as pd
import shutil
from database import init_db

DB_FILE = "/data/db/gestor.db"
UPLOAD_BASE_DIR = "/data/uploads"

init_db()

st.set_page_config(page_title="Gestor de Recursos", layout="wide")
st.title("📂 Gestor de Recursos e Documentação")

# --- FUNÇÕES ---

def listar_recursos():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM recursos", conn)
    conn.close()
    return df

def calcular_status_progresso(row):
    # Se já foi marcado manualmente como concluído
    if row.get('concluido') == 1:
        return "✅ FINALIZADO"

    hoje = datetime.date.today()
    try:
        prazo = datetime.datetime.strptime(row['data_limite'], '%Y-%m-%d').date()
    except:
        return "⚠️ Erro na Data"
    
    path_pasta = os.path.join(UPLOAD_BASE_DIR, str(row['id']))
    qtd_atual = 0
    if os.path.exists(path_pasta):
        qtd_atual = len([f for f in os.listdir(path_pasta) if os.path.isfile(os.path.join(path_pasta, f))])
    
    qtd_nec = int(row['qtd_necessaria']) if row['qtd_necessaria'] else 1
    dias = (prazo - hoje).days

    qtd_percent = (qtd_atual/qtd_nec)*100

    if dias > 10:
        return f"🟢 Em Dia ({qtd_atual}/{qtd_nec}) documentos - Dias restantes: {dias}"
    elif dias <= 10 and dias >=5:
        if qtd_percent >= 80:
            status = "🟢 Em Dia"
        elif qtd_percent >= 50:
            status = "🟡 Atenção"
        else:
            status = "🟠 Urgente"
        return f"{status} ({qtd_atual}/{qtd_nec}) documentos - Dias restantes: {dias}"
    elif dias <5 and dias >=0:
        if qtd_percent >= 90:
            status = "🟢 Em Dia"
        elif qtd_percent >= 70:
            status = "🟡 Atenção"
        else:
            status = "🟠 Urgente"
        return f"{status} ({qtd_atual}/{qtd_nec}) documentos - Dias restantes: {dias}"
    else:
        return f"🔴 Em Atraso ({qtd_atual}/{qtd_nec}) documentos - Dias de atraso: {abs(dias)}"

# --- INTERFACE ---

tabs = st.tabs(["📊 Painel", "🆕 Novo", "🖇️ Anexar", "⚙️ Ações e Limpeza"])

# 📊 PAINEL
with tabs[0]:
    df_geral = listar_recursos()
    if not df_geral.empty:
        df_geral['Situação'] = df_geral.apply(calcular_status_progresso, axis=1)
        
        st.subheader("📋 Status dos Processos")
        st.dataframe(
            df_geral[['id', 'nome', 'valor', 'data_limite', 'Situação']],
            column_config={
                "valor": st.column_config.NumberColumn("Valor", format="R$ %.2f"),
                "data_limite": st.column_config.DateColumn("Prazo"),
            },
            use_container_width=True, hide_index=True
        )
    else:
        st.info("Nenhum recurso cadastrado.")

# 🆕 NOVO
with tabs[1]:
    with st.form("novo"):
        nome = st.text_input("Nome do Recurso")
        c1, c2, c3 = st.columns(3)
        valor = c1.number_input("Valor", min_value=0.0)
        data_limite = c2.date_input("Prazo")
        qtd_necessaria = c3.number_input("Qtd. Docs Necessários", min_value=1, value=1)
        submit = st.form_submit_button("Salvar")
        
    if submit and nome:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO recursos (nome, valor, data_limite, qtd_necessaria, concluido) VALUES (?, ?, ?, ?, 0)",
            (nome, valor, str(data_limite), qtd_necessaria)
        )
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        os.makedirs(os.path.join(UPLOAD_BASE_DIR, str(new_id)), exist_ok=True)
        st.success("Cadastrado com sucesso!")
        st.rerun()

# 🖇️ ANEXAR
with tabs[2]:
    df_anexo = listar_recursos()
    # Filtra apenas os que não estão concluídos para anexar novos docs
    df_abertos = df_anexo[df_anexo['concluido'] == 0]
    
    if not df_abertos.empty:
        opcoes = {f"{row['id']} - {row['nome']}": row['id'] for _, row in df_abertos.iterrows()}
        escolha = st.selectbox("Selecione o Recurso:", options=list(opcoes.keys()))
        arq = st.file_uploader("Escolha o arquivo")
        if st.button("Fazer Upload") and arq:
            id_dest = opcoes[escolha]
            pasta = os.path.join(UPLOAD_BASE_DIR, str(id_dest))
            os.makedirs(pasta, exist_ok=True)
            with open(os.path.join(pasta, arq.name.replace(" ", "_")), "wb") as f:
                f.write(arq.getbuffer())
            st.success("Arquivo anexado!")
            st.rerun()
    else:
        st.info("Não há processos abertos para anexação.")

# ⚙️ AÇÕES E LIMPEZA
with tabs[3]:
    df_gestao = listar_recursos()
    if not df_gestao.empty:
        st.subheader("🏁 Concluir Processo")
        # Apenas os que ainda não estão concluídos
        df_para_concluir = df_gestao[df_gestao['concluido'] == 0]
        
        if not df_para_concluir.empty:
            opcoes_concluir = {f"{row['id']} - {row['nome']}": row for _, row in df_para_concluir.iterrows()}
            escolha_c = st.selectbox("Recurso para finalizar:", options=list(opcoes_concluir.keys()))
            
            if st.button("Validar e Concluir Processo", type="primary"):
                recurso = opcoes_concluir[escolha_c]
                id_alvo = recurso['id']
                qtd_nec = recurso['qtd_necessaria']
                
                # Verificação de arquivos física
                pasta = os.path.join(UPLOAD_BASE_DIR, str(id_alvo))
                qtd_atual = len([f for f in os.listdir(pasta)]) if os.path.exists(pasta) else 0
                
                if qtd_atual >= qtd_nec:
                    conn = sqlite3.connect(DB_FILE)
                    conn.execute("UPDATE recursos SET concluido = 1 WHERE id = ?", (id_alvo,))
                    conn.commit()
                    conn.close()
                    st.success(f"Sucesso! Recurso #{id_alvo} marcado como Finalizado.")
                    st.rerun()
                else:
                    st.error(f"Não é possível concluir. Faltam documentos! ({qtd_atual} de {qtd_nec} anexados)")
        else:
            st.write("Todos os processos atuais já estão finalizados.")

        st.divider()
        st.subheader("🗑️ Exclusão")
        opcoes_del = {f"{row['id']} - {row['nome']}": row['id'] for _, row in df_gestao.iterrows()}
        escolha_del = st.selectbox("Recurso para excluir permanentemente:", options=list(opcoes_del.keys()))
        if st.button("Confirmar Exclusão", help="Isso apagará os arquivos no Debian também"):
            id_del = opcoes_del[escolha_del]
            conn = sqlite3.connect(DB_FILE)
            conn.execute("DELETE FROM recursos WHERE id=?", (id_del,))
            conn.commit()
            conn.close()
            shutil.rmtree(os.path.join(UPLOAD_BASE_DIR, str(id_del)), ignore_errors=True)
            st.rerun()