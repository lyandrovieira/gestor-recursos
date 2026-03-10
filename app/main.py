import streamlit as st
import sqlite3
import os
import shutil
from database import init_db

# Inicializa o banco (caminho /data/db/gestor.db definido no database.py)
init_db()

st.set_page_config(page_title="Gestor de Recursos", layout="wide")

st.title("📂 Registro de Novo Recurso e Documento")

# Definição de caminhos base (usando a nova estrutura de volumes)
UPLOAD_BASE_DIR = "/data/uploads"
DB_FILE = "/data/db/gestor.db"

with st.form("registro_recurso", clear_on_submit=True):
    col1, col2 = st.columns(2)
    
    with col1:
        nome = st.text_input("Nome do Recurso", placeholder="Ex: PDDE 2026")
        valor = st.number_input("Valor Recebido (R$)", min_value=0.0, step=100.0)
    
    with col2:
        data_limite = st.date_input("Prazo de Prestação de Contas")
        arquivo = st.file_uploader("Documento/Comprovante (PDF ou Imagem)", type=["pdf", "png", "jpg", "jpeg"])

    submit = st.form_submit_button("Salvar Registro")

if submit:
    if nome and arquivo:
        try:
            # 1. Salvar dados no SQLite
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO recursos (nome, valor, data_limite) VALUES (?, ?, ?)",
                (nome, valor, str(data_limite))
            )
            recurso_id = cursor.lastrowid # Pega o ID gerado automaticamente
            
            # 2. Criar diretório específico para o ID do recurso
            recurso_path = os.path.join(UPLOAD_BASE_DIR, str(recurso_id))
            os.makedirs(recurso_path, exist_ok=True)
            
            # 3. Salvar o arquivo fisicamente
            file_path = os.path.join(recurso_path, arquivo.name)
            with open(file_path, "wb") as f:
                f.write(arquivo.getbuffer())
            
            # 4. Atualizar o banco com o caminho do arquivo
            cursor.execute(
                "UPDATE recursos SET documento_path = ? WHERE id = ?",
                (file_path, recurso_id)
            )
            
            conn.commit()
            conn.close()
            
            st.success(f"✅ Recurso #{recurso_id} registrado! Arquivo salvo em: {file_path}")
            
        except Exception as e:
            st.error(f"Erro ao processar registro: {e}")
    else:
        st.warning("Por favor, preencha o nome e anexe um documento.")

st.divider()
st.subheader("📋 Recursos Cadastrados")

try:
    conn = sqlite3.connect(DB_FILE)
    # Usamos o Pandas para ler o SQL e transformar em uma tabela bonita
    import pandas as pd
    df = pd.read_sql_query("SELECT id, nome, valor, data_limite, status, documento_path FROM recursos", conn)
    conn.close()

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhum recurso cadastrado até o momento.")
except Exception as e:
    st.error(f"Erro ao carregar tabela: {e}")