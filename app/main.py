import streamlit as st
import sqlite3
import os
import time
import datetime
import pandas as pd
import shutil
from database import init_db

DB_FILE = "/data/db/gestor.db"
UPLOAD_BASE_DIR = "/data/uploads"

init_db()

st.set_page_config(page_title="Gestor de Recursos", layout="wide")
st.title("📂 Gestor de Recursos e Documentação")

# CENTRALIZAÇÃO DA LISTAGEM
def listar_recursos():
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM recursos", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao acessar banco de dados: {e}")
        return pd.DataFrame()

# Carrega os dados uma única vez por ciclo de execução do script
df_global = listar_recursos()

# --- 2. FUNÇÕES DE APOIO ---

def calcular_status_progresso(row):
    if row.get('concluido') == 1:
        return "✅ Concluído"

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
    dias = (prazo - hoye if 'hoye' not in locals() else hoje).days # Pequena correção de variável
    dias = (prazo - hoje).days
    qtd_percent = (qtd_atual/qtd_nec)*100

    if dias > 10:
        return f"🟢 Em Dia ({qtd_atual}/{qtd_nec}) docs - {dias} dias rest."
    elif 5 <= dias <= 10:
        status = "🟢 Em Dia" if qtd_percent >= 80 else "🟡 Atenção" if qtd_percent >= 50 else "🟠 Urgente"
        return f"{status} ({qtd_atual}/{qtd_nec}) - {dias} dias rest."
    elif 0 <= dias < 5:
        status = "🟢 Em Dia" if qtd_percent >= 90 else "🟡 Atenção" if qtd_percent >= 70 else "🟠 Urgente"
        return f"{status} ({qtd_atual}/{qtd_nec}) - {dias} dias rest."
    else:
        return f"🔴 Em Atraso ({qtd_atual}/{qtd_nec}) - {abs(dias)} de atraso"

# INTERFACE

tabs = st.tabs(["📊 Painel", "🆕 Novo", "🖇️ Anexar", "🗑️ Excluir"])

# ABA PAINEL
with tabs[0]:
    st.header("📊 Painel de Controle")
    if not df_global.empty:
        for _, row in df_global.iterrows():
            status_texto = calcular_status_progresso(row) 
            with st.expander(f"{status_texto.split(' ')[0]} {row['nome']}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Status:** {status_texto}")
                    st.write(f"**Prazo:** {row['data_limite']}")
                    st.write(f"**Valor:** R$ {row['valor']:.2f}")
                
                with col2:
                    caminho_pasta = os.path.join(UPLOAD_BASE_DIR, str(row['id']))
                    arquivos = os.listdir(caminho_pasta) if os.path.exists(caminho_pasta) else []
                    st.write(f"📂 {len(arquivos)} arquivos" if arquivos else "📂 Vazio")

                    # SUB-SESSÃO: EDIÇÃO
                    with st.popover("📝 Editar Informações", use_container_width=True):
                        st.caption(f"Editando ID: {row['id']}")
                        
                        novo_nome = st.text_input("Nome do Recurso", value=row['nome'], key=f"ed_n_{row['id']}")                       
                        novo_valor = st.number_input("Novo Valor", value=float(row['valor']), key=f"ed_v_{row['id']}")
                        novo_prazo = st.date_input("Novo Prazo", value=datetime.datetime.strptime(row['data_limite'], '%Y-%m-%d').date(), key=f"ed_p_{row['id']}")
                        nova_qtd = st.number_input("Nova Qtd. Docs", min_value=1, value=int(row['qtd_necessaria']), key=f"ed_q_{row['id']}")
                        
                        if st.button("Salvar Alterações", key=f"save_{row['id']}", type="primary", use_container_width=True):
                            nome_editado = novo_nome.strip()
                            
                            # Verifica se o nome existe em OUTRA linha que não seja a atual (id diferente)
                            duplicado = df_global[(df_global['nome'] == nome_editado) & (df_global['id'] != row['id'])]
                            
                            if not duplicado.empty:
                                st.error(f"O nome '{nome_editado}' já está sendo usado por outro recurso.")
                            elif not nome_editado:
                                st.error("O nome não pode ficar vazio.")
                            else:
                                conn = sqlite3.connect(DB_FILE)
                                # Atualizamos o NOME também agora
                                conn.execute("""
                                    UPDATE recursos 
                                    SET nome=?, valor=?, data_limite=?, qtd_necessaria=? 
                                    WHERE id=?
                                """, (nome_editado, novo_valor, str(novo_prazo), nova_qtd, row['id']))
                                conn.commit()
                                conn.close()
                                st.toast("Dados e Nome atualizados!", icon="💾")
                                time.sleep(1)
                                st.rerun()

                    # SUB-SESSÃO: VALIDAÇÃO
                    if row['concluido'] == 0:
                        if st.button("Validar e Concluir", type="primary", key=f"val_{row['id']}", use_container_width=True):
                            if len(arquivos) >= row['qtd_necessaria']:
                                conn = sqlite3.connect(DB_FILE)
                                conn.execute("UPDATE recursos SET concluido = 1 WHERE id = ?", (row['id'],))
                                conn.commit()
                                conn.close()
                                st.toast(f"Recurso {row['nome']} finalizado!", icon="✅")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Faltam documentos! ({len(arquivos)}/{row['qtd_necessaria']})")

                if arquivos:
                    st.divider()
                    for arq in arquivos:
                        with open(os.path.join(caminho_pasta, arq), "rb") as f:
                            st.download_button(label=f"📄 {arq}", data=f.read(), file_name=arq, key=f"dl_{row['id']}_{arq}")
    else:
        st.info("Nenhum recurso cadastrado.")

# ABA NOVO
with tabs[1]:
    with st.form("novo_recurso", clear_on_submit=True):
        nome = st.text_input("Nome do Recurso")
        c1, c2, c3 = st.columns(3)
        valor = c1.number_input("Valor", min_value=0.0)
        data_limite = c2.date_input("Prazo")
        qtd_necessaria = c3.number_input("Qtd. Docs Necessários", min_value=1, value=1)
        submit = st.form_submit_button("Salvar")
        
    if submit and nome:
        nome_limpo = nome.strip()
        if not df_global.empty and nome_limpo in df_global['nome'].values:
            st.error(f"Erro: O nome '{nome_limpo}' já está registrado.")
        else:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO recursos (nome, valor, data_limite, qtd_necessaria, concluido) VALUES (?, ?, ?, ?, 0)",
                           (nome_limpo, valor, str(data_limite), qtd_necessaria))
            new_id = cursor.lastrowid
            conn.commit()
            conn.close()
            os.makedirs(os.path.join(UPLOAD_BASE_DIR, str(new_id)), exist_ok=True)
            st.toast("Recurso cadastrado!", icon="🆕")
            time.sleep(1)
            st.rerun()

# ABA ANEXAR
with tabs[2]:
    df_abertos = df_global[df_global['concluido'] == 0] if not df_global.empty else pd.DataFrame()
    if not df_abertos.empty:
        opcoes = {f"{row['id']} - {row['nome']}": row['id'] for _, row in df_abertos.iterrows()}
        escolha = st.selectbox("Selecione o Recurso:", options=list(opcoes.keys()))
        arq = st.file_uploader("Escolha o arquivo")
        
        if st.button("Fazer Upload") and arq:
            id_dest = opcoes[escolha]
            nome_arq = arq.name.replace(" ", "_")
            pasta = os.path.join(UPLOAD_BASE_DIR, str(id_dest))
            caminho_full = os.path.join(pasta, nome_arq)
            
            if os.path.exists(caminho_full):
                st.warning(f"O arquivo '{nome_arq}' já existe. Exclua-o na aba 'Excluir' se quiser substituir.")
            else:
                os.makedirs(pasta, exist_ok=True)
                with open(caminho_full, "wb") as f:
                    f.write(arq.getbuffer())
                st.toast("Upload concluído!", icon="🖇️")
                time.sleep(1)
                st.rerun()
    else:
        st.info("Não há processos abertos.")

# ABA EXCLUIR
with tabs[3]:
    if not df_global.empty:
        st.subheader("🗑️ Gerenciar Arquivos")
        opcoes_del = {f"{row['id']} - {row['nome']}": row for _, row in df_global.iterrows()}
        escolha_del = st.selectbox("Selecione o recurso:", options=list(opcoes_del.keys()))
        
        recurso_sel = opcoes_del[escolha_del]
        caminho_pasta = os.path.join(UPLOAD_BASE_DIR, str(recurso_sel['id']))
        arquivos = os.listdir(caminho_pasta) if os.path.exists(caminho_pasta) else []

        if arquivos:
            df_files = pd.DataFrame(arquivos, columns=["Nome do Arquivo"])
            event = st.dataframe(df_files, use_container_width=True, hide_index=True, 
                                 on_select="rerun", selection_mode="single-row")
            
            selecao = event.get("selection", {}).get("rows", [])
            if selecao:
                arq_nome = df_files.iloc[selecao[0]]["Nome do Arquivo"]
                if st.button(f"Excluir {arq_nome}", type="primary", use_container_width=True):
                    os.remove(os.path.join(caminho_pasta, arq_nome))
                    st.toast("Arquivo removido!", icon="🗑️")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("Esta pasta não possui arquivos.")
        
        st.divider()
        with st.expander("⚠️ Zona de Perigo"):
            st.write("Apagar o recurso excluirá o registro no banco e TODOS os documentos anexados.")
            if st.button(f"Apagar '{recurso_sel['nome']}' permanentemente", use_container_width=True):
                conn = sqlite3.connect(DB_FILE)
                conn.execute("DELETE FROM recursos WHERE id = ?", (recurso_sel['id'],))
                conn.commit()
                conn.close()
                if os.path.exists(caminho_pasta):
                    shutil.rmtree(caminho_pasta)
                st.toast("Recurso excluído!", icon="💥")
                time.sleep(1)
                st.rerun()
    else:
        st.info("Nada para gerenciar.")