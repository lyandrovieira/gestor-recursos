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

# FUNÇÕES

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
        return f"🟢 Em Dia ({qtd_atual}/{qtd_nec}) documentos - {dias} dias restantes"
    elif dias <= 10 and dias >=5:
        if qtd_percent >= 80:
            status = "🟢 Em Dia"
        elif qtd_percent >= 50:
            status = "🟡 Atenção"
        else:
            status = "🟠 Urgente"
        return f"{status} ({qtd_atual}/{qtd_nec}) documentos - {dias} dias restantes"
    elif dias <5 and dias >=0:
        if qtd_percent >= 90:
            status = "🟢 Em Dia"
        elif qtd_percent >= 70:
            status = "🟡 Atenção"
        else:
            status = "🟠 Urgente"
        return f"{status} ({qtd_atual}/{qtd_nec}) documentos - {dias} dias restantes"
    else:
        return f"🔴 Em Atraso ({qtd_atual}/{qtd_nec}) documentos - {abs(dias)} de atraso"

# INTERFACE

tabs = st.tabs(["📊 Painel", "🆕 Novo", "🖇️ Anexar", "🗑️ Excluir"])

# PAINEL
with tabs[0]:
    st.header("📊 Painel de Controle")

    if not df_painel.empty:
        for _, row in df_painel.iterrows():
            status_texto = calcular_status_progresso(row) 
            
            with st.expander(f"{status_texto.split(' ')[0]} {row['nome']}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Status:** {status_texto}")
                    st.write(f"**Prazo:** {row['data_limite']}")
                
                with col2:
                    caminho_pasta = os.path.join(UPLOAD_BASE_DIR, str(row['id']))
                    if os.path.exists(caminho_pasta):
                        arquivos = os.listdir(caminho_pasta)
                        if arquivos:
                            st.write(f"📂 {len(arquivos)} arquivos")
                        else:
                            st.write("📂 Vazio")

                    # Verificação de processos não concluídos
                    df_para_concluir = df_painel[df_painel['concluido'] == 0]
                    
                    if not df_para_concluir.empty:
                        if st.button("Validar e Concluir Processo", type="primary", key=row['id']):
                            id_alvo = row['id']
                            nome_alvo = row['nome']
                            qtd_nec = row['qtd_necessaria']
                            
                            # Verificação de arquivos física
                            pasta = os.path.join(UPLOAD_BASE_DIR, str(id_alvo))
                            qtd_atual = len([f for f in os.listdir(pasta)]) if os.path.exists(pasta) else 0
                            
                            if qtd_atual >= qtd_nec:
                                conn = sqlite3.connect(DB_FILE)
                                conn.execute("UPDATE recursos SET concluido = 1 WHERE id = ?", (id_alvo,))
                                conn.commit()
                                conn.close()
                                st.success(f"Sucesso! Recurso #{nome_alvo} marcado como Finalizado.")
                                st.rerun()
                            else:
                                st.error(f"Não é possível concluir. Faltam documentos! ({qtd_atual} de {qtd_nec} anexados)")
                    else:
                        st.write("Todos os processos atuais já estão finalizados.")

                # Seção de Downloads dentro do Expander
                if os.path.exists(caminho_pasta) and arquivos:
                    st.divider()
                    st.caption("Clique para baixar:")
                    for arq in arquivos:
                        caminho_full = os.path.join(caminho_pasta, arq)
                        with open(caminho_full, "rb") as f:
                            st.download_button(
                                label=f"📄 {arq}",
                                data=f.read(),
                                file_name=arq,
                                key=f"pnl_{row['id']}_{arq}",
                                use_container_width=True
                            )
                elif not os.path.exists(caminho_pasta) or not arquivos:
                    st.info("Nenhum documento anexado ainda.")
    else:
        st.info("Nenhum recurso em aberto.")

# NOVO
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

# ANEXAR
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

# EXCLUIR
with tabs[3]:
    df_gestao = listar_recursos()
    if not df_gestao.empty:
        st.subheader("🗑️ Exclusão")
        opcoes_del = {f"{row['id']} - {row['nome']}": row['id'] for _, row in df_gestao.iterrows()}
        escolha_del = st.selectbox("Selecione o recurso:", options=list(opcoes_del.keys()))

        id_alvo = opcoes_del[escolha_del]

        caminho_pasta = os.path.join(UPLOAD_BASE_DIR, str(id_alvo))
        arquivos = []
        if os.path.exists(caminho_pasta):
            arquivos = os.listdir(caminho_pasta)

        st.subheader("Arquivos Anexados")
        if arquivos:
            # Criação do DataFrame para a tabela
            df_files = pd.DataFrame(arquivos, columns=["Nome do Arquivo"])
            
            # Seleção de linha na tabela
            event = st.dataframe(
                df_files,
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )
            
            # Verifica se algo foi selecionado
            selecao = event.get("selection", {}).get("rows", [])
            if selecao:
                indice_linha = selecao[0]
                arquivo_selecionado = df_files.iloc[selecao[0]]["Nome do Arquivo"] if selecao else None
                caminho_completo = os.path.join(caminho_pasta, arquivo_selecionado)

                if st.button(f"Excluir {arquivo_selecionado}", type="primary", use_container_width=True):
                    try:
                        os.remove(caminho_completo)
                        st.success(f"Arquivo '{arquivo_selecionado}' removido com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir o arquivo: {e}")
           
        else:
            st.write("Nenhum arquivo encontrado nesta pasta.")
            arquivo_selecionado = None
