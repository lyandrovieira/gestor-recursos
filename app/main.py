import streamlit as st
import sqlite3
import os
import time
import datetime
import pandas as pd
import shutil
from database import init_db

# CONFIGURAÇÕES E INICIALIZAÇÃO
DB_FILE = "/data/db/gestor.db"
UPLOAD_BASE_DIR = "/data/uploads"

init_db()

st.set_page_config(page_title="Gestor de Recursos", layout="wide")
st.title("📂 Gestor de Recursos e Documentação")

# FUNÇÕES

def listar_recursos():
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM recursos", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao acessar banco de dados: {e}")
        return pd.DataFrame()

def sincronizar_nomes_arquivos(id_recurso, novo_nome):
    #Atualiza o prefixo dos arquivos físicos, substituindo o antigo pelo novo.
    pasta = os.path.join(UPLOAD_BASE_DIR, str(id_recurso))
    if os.path.exists(pasta):
        prefixo_novo = novo_nome.strip().replace(" ", "_")
        for arq in os.listdir(pasta):
            caminho_antigo = os.path.join(pasta, arq)
            
            if os.path.isfile(caminho_antigo):
                # Se o arquivo já tem um underscore, é separado o prefixo antigo do resto do nome
                if "_" in arq:
                    # split('_', 1) divide apenas na primeira ocorrência
                    partes = arq.split("_", 1)
                    nome_real_arquivo = partes[1]
                else:
                    # Se não tem underscore, o nome inteiro é o nome real
                    nome_real_arquivo = arq
                
                novo_nome_arq = f"{prefixo_novo}_{nome_real_arquivo}"
                
                # Só renomeia se o nome final for realmente diferente do atual
                if arq != novo_nome_arq:
                    os.rename(caminho_antigo, os.path.join(pasta, novo_nome_arq))

def calcular_status_progresso(row):
    if row.get('concluido') == 1:
        return "✅ Concluído"

    hoje = datetime.date.today()
    try:
        prazo = datetime.datetime.strptime(row['data_limite'], '%Y-%m-%d').date()
    except:
        return "⚠️ Erro na Data"
    
    dias = (prazo - hoje).days
    
    path_pasta = os.path.join(UPLOAD_BASE_DIR, str(row['id']))
    qtd_atual = len([f for f in os.listdir(path_pasta) if os.path.isfile(os.path.join(path_pasta, f))]) if os.path.exists(path_pasta) else 0
    qtd_nec = int(row['qtd_necessaria']) if row['qtd_necessaria'] else 1
    qtd_percent = (qtd_atual / qtd_nec) * 100

    if dias > 10:
        return f"🟢 Em Dia - ({qtd_atual}/{qtd_nec}) documentos anexados - {dias} DIAS RESTANTES."
    elif 5 <= dias <= 10:
        status = "🟢 Em Dia" if qtd_percent >= 80 else "🟡 Atenção" if qtd_percent >= 50 else "🟠 Urgente"
        return f"{status} - ({qtd_atual}/{qtd_nec}) documentos anexados - {dias} DIAS RESTANTES."
    elif 0 <= dias < 5:
        status = "🟢 Em Dia" if qtd_percent >= 90 else "🟡 Atenção" if qtd_percent >= 70 else "🟠 Urgente"
        return f"{status} - ({qtd_atual}/{qtd_nec}) documentos anexados - {dias} DIAS RESTANTES."
    else:
        return f"🔴 Em Atraso - ({qtd_atual}/{qtd_nec}) documentos anexados - {abs(dias)} DIAS DE ATRASO."

def acao_sucesso(mensagem, icon="✅"):
    st.session_state.notificacao = (mensagem, icon)
    st.rerun()

if "notificacao" in st.session_state:
    msg, icon = st.session_state.notificacao
    st.toast(msg, icon=icon)
    del st.session_state.notificacao

# Carregamento centralizado dos dados
df_global = listar_recursos()

# INTERFACE

tabs = st.tabs(["📊 Painel", "🆕 Novo", "🖇️ Anexar", "🗑️ Excluir"])

# PAINEL
with tabs[0]:
    st.header("📊 Painel de Controle")
    if not df_global.empty:
        for _, row in df_global.iterrows():
            status_texto = calcular_status_progresso(row) 
            with st.expander(f"{status_texto.split(' ')[0]} {row['nome']}"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**Status:** {status_texto}")
                    st.write(f"**Prazo Final:** {row['data_limite']}")
                    st.write(f"**Valor:** R$ {row['valor']:.2f}")
                
                with col2:
                    caminho_p = os.path.join(UPLOAD_BASE_DIR, str(row['id']))
                    arqs = os.listdir(caminho_p) if os.path.exists(caminho_p) else []
                    
                    # EDIÇÃO DE RECURSO
                    with st.popover("📝 Editar", use_container_width=True):
                        n_nome = st.text_input("Nome", value=row['nome'], key=f"n_{row['id']}")
                        n_val = st.number_input("Valor", value=float(row['valor']), key=f"v_{row['id']}")
                        n_prz = st.date_input("Prazo", value=datetime.datetime.strptime(row['data_limite'], '%Y-%m-%d').date(), key=f"p_{row['id']}")
                        n_qtd = st.number_input("Meta Docs", min_value=1, value=int(row['qtd_necessaria']), key=f"q_{row['id']}")
                        
                        if st.button("Confirmar Alterações", key=f"s_{row['id']}", type="primary", use_container_width=True):
                            n_nome = n_nome.strip()
                            # Validação de duplicidade
                            dup = df_global[(df_global['nome'] == n_nome) & (df_global['id'] != row['id'])]
                            
                            if not dup.empty:
                                st.error("Este nome já está sendo usado em outro recurso.")
                            elif not n_nome:
                                st.error("O nome não pode ser vazio.")
                            else:
                                with sqlite3.connect(DB_FILE) as conn:
                                    conn.execute("""
                                        UPDATE recursos 
                                        SET nome=?, valor=?, data_limite=?, qtd_necessaria=? 
                                        WHERE id=?
                                    """, (n_nome, n_val, str(n_prz), n_qtd, row['id']))
                                
                                # Chama a função corrigida que limpa o prefixo antigo
                                sincronizar_nomes_arquivos(row['id'], n_nome)
                                
                                st.cache_data.clear()
                                acao_sucesso(f"Recurso atualizado para {n_nome}!", icon="🔄")

                    # CONCLUSÃO
                    if row['concluido'] == 0:
                        if st.button("Concluir", type="primary", key=f"f_{row['id']}", use_container_width=True):
                            if len(arqs) >= row['qtd_necessaria']:
                                with sqlite3.connect(DB_FILE) as conn:
                                    conn.execute("UPDATE recursos SET concluido=1 WHERE id=?", (row['id'],))
                                st.toast("Concluído!", icon="✅")
                                time.sleep(1.5); st.rerun()
                            else:
                                st.error("Documentos insuficientes.")

                if arqs:
                    st.divider()
                    for a in arqs:
                        with open(os.path.join(caminho_p, a), "rb") as f:
                            st.download_button(label=f"📄 {a}", data=f.read(), file_name=a, key=f"d_{row['id']}_{a}")
    else:
        st.info("Sem recursos.")

# NOVO RECURSO
with tabs[1]:
    with st.form("f_novo", clear_on_submit=True):
        nome_n = st.text_input("Nome do Recurso")
        c1, c2, c3 = st.columns(3)
        v_n = c1.number_input("Valor", min_value=0.0)
        p_n = c2.date_input("Prazo")
        q_n = c3.number_input("Qtd. Docs", min_value=1, value=1)
        if st.form_submit_button("Salvar", type='primary') and nome_n:
            nome_n = nome_n.strip()
            if not df_global.empty and nome_n in df_global['nome'].values:
                st.error("Já existe um recurso registrado com o mesmo nome")
            else:
                with sqlite3.connect(DB_FILE) as conn:
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO recursos (nome, valor, data_limite, qtd_necessaria, concluido) VALUES (?,?,?,?,0)", 
                                   (nome_n, v_n, str(p_n), q_n))
                    nid = cursor.lastrowid
                os.makedirs(os.path.join(UPLOAD_BASE_DIR, str(nid)), exist_ok=True)
                st.toast("Criado!", icon="🆕")
                time.sleep(1.5); st.rerun()

# ANEXAR
with tabs[2]:
    df_ab = df_global[df_global['concluido'] == 0] if not df_global.empty else pd.DataFrame()
    if not df_ab.empty:
        opc = {f"{r['nome']}": r['id'] for _, r in df_ab.iterrows()}
        sel = st.selectbox("Recurso:", options=list(opc.keys()))
        upload = st.file_uploader("Arquivo")
        if st.button("Upload", type='primary') and upload:
            p_dest = os.path.join(UPLOAD_BASE_DIR, str(opc[sel]))
            
            # Pega o nome do recurso selecionado para criar o prefixo inicial
            prefixo_atual = sel.strip().replace(" ", "_")
            nome_limpo = upload.name.replace(" ", "_")
            
            # Salva já com o prefixo: RECURSO_arquivo.pdf
            n_file = f"{prefixo_atual}_{nome_limpo}"
            
            c_full = os.path.join(p_dest, n_file)

            if os.path.exists(c_full):
                st.warning("Arquivo já existe.")
            else:
                with open(c_full, "wb") as f: f.write(upload.getbuffer())
                st.toast("Anexado!", icon="🖇️")
                time.sleep(1.5); st.rerun()
    else:
        st.info("Sem processos abertos.")

# EXCLUIR
with tabs[3]:
    if not df_global.empty:
        opc_del = {f"{r['nome']}": r for _, r in df_global.iterrows()}
        sel_del = st.selectbox("Gerenciar:", options=list(opc_del.keys()))
        rec = opc_del[sel_del]
        p_ex = os.path.join(UPLOAD_BASE_DIR, str(rec['id']))
        arqs_ex = os.listdir(p_ex) if os.path.exists(p_ex) else []
        
        if arqs_ex:
            df_f = pd.DataFrame(arqs_ex, columns=["Arquivo"])
            ev = st.dataframe(df_f, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
            s_rows = ev.get("selection", {}).get("rows", [])
            if s_rows:
                a_del = df_f.iloc[s_rows[0]]["Arquivo"]
                if st.button(f"Excluir {a_del}", type="primary"):
                    os.remove(os.path.join(p_ex, a_del))
                    st.toast("Removido!", icon="🗑️")
                    time.sleep(1.5); st.rerun()
        
        st.divider()
        with st.expander("Zona de Perigo"):
            if st.button(f"Apagar {rec['nome']} permanentemente?", type='primary', use_container_width=True):
                with sqlite3.connect(DB_FILE) as conn:
                    conn.execute("DELETE FROM recursos WHERE id=?", (rec['id'],))
                if os.path.exists(p_ex): shutil.rmtree(p_ex)
                st.toast("Excluído!", icon="💥")
                time.sleep(1.5); st.rerun()