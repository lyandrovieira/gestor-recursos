import streamlit as st
import sqlite3
import os
import datetime
import pandas as pd
from database import init_db

init_db()

st.set_page_config(page_title="Gestor de Recursos", layout="wide")
st.title("📂 Gestão de Documentos e Recursos")

UPLOAD_BASE_DIR = "/data/uploads"
DB_FILE = "/data/db/gestor.db"

# Função auxiliar para listar recursos
def listar_recursos():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT id, nome FROM recursos", conn)
    conn.close()
    return df

# Interface de escolha
aba1, aba2 = st.tabs(["🆕 Novo Recurso", "🖇️ Anexar a Existente"])

# --- ABA 1: NOVO RECURSO ---
with aba1:
    with st.form("form_novo"):
        nome = st.text_input("Nome do Recurso")
        valor = st.number_input("Valor (R$)", min_value=0.0)
        data_limite = st.date_input("Prazo Final")
        arquivo = st.file_uploader("Documento Inicial", type=["pdf", "png", "jpg"], key="new")
        submit_novo = st.form_submit_button("Criar e Salvar")

    if submit_novo and nome and arquivo:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO recursos (nome, valor, data_limite) VALUES (?, ?, ?)", 
                       (nome, valor, str(data_limite)))
        recurso_id = cursor.lastrowid
        
        # Lógica de Pasta
        recurso_path = os.path.join(UPLOAD_BASE_DIR, str(recurso_id))
        os.makedirs(recurso_path, exist_ok=True)
        
        save_path = os.path.join(recurso_path, arquivo.name.replace(" ", "_"))
        with open(save_path, "wb") as f:
            f.write(arquivo.getbuffer())
        
        cursor.execute("UPDATE recursos SET documento_path = ? WHERE id = ?", (save_path, recurso_id))
        conn.commit()
        conn.close()
        st.success(f"Recurso #{recurso_id} criado com sucesso!")

# --- ABA 2: ANEXAR DOCUMENTO ---
with aba2:
    df_existentes = listar_recursos()
    
    if df_existentes.empty:
        st.info("Nenhum recurso cadastrado ainda.")
    else:
        # Criamos uma lista formatada para o usuário escolher
        opcoes = {f"{row['nome']}": row['id'] for _, row in df_existentes.iterrows()}
        escolha = st.selectbox("Selecione o Recurso Destino:", options=list(opcoes.keys()))
        
        with st.form("form_anexo"):
            arquivo_anexo = st.file_uploader("Novo Documento", type=["pdf", "png", "jpg"], key="anexo")
            submit_anexo = st.form_submit_button("Anexar Arquivo")
        
        if submit_anexo and arquivo_anexo:
            id_destino = opcoes[escolha]
            recurso_path = os.path.join(UPLOAD_BASE_DIR, str(id_destino))
            os.makedirs(recurso_path, exist_ok=True) # Garante que a pasta existe
            
            nome_arq = arquivo_anexo.name.replace(" ", "_")
            file_path = os.path.join(recurso_path, nome_arq)
            
            # Evita sobrescrever se o nome for igual
            if os.path.exists(file_path):
                timestamp = datetime.datetime.now().strftime("%H%M%S")
                file_path = os.path.join(recurso_path, f"{timestamp}_{nome_arq}")
                
            with open(file_path, "wb") as f:
                f.write(arquivo_anexo.getbuffer())
                
            st.success(f"Arquivo anexado com sucesso ao Recurso ID {id_destino}!")

# Visualização no Rodapé
st.divider()
st.subheader("📊 Tabela de Controle")
st.dataframe(listar_recursos(), use_container_width=True)