# /database.py

import sqlite3
import os
import sys
from datetime import datetime
import logging
from functools import lru_cache
import PyPDF2
import json
import re

from config import DB_NAME, HISTORY_FILE, LOG_FILE

# --- Configuração de Logging ---
def setup_logging():
    log_file_path = get_user_data_path(LOG_FILE)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler(sys.stdout)
        ]
    )

def get_user_data_path(file_name):
    """Obtém caminho seguro para armazenamento de dados do utilizador."""
    home = os.path.expanduser("~")
    app_name = "AITechExpert"
    app_support_path = os.path.join(home, app_name)
    os.makedirs(app_support_path, exist_ok=True)
    return os.path.join(app_support_path, file_name)

# --- Funções do Banco de Dados ---
def init_db():
    """Inicializa o banco de dados SQLite com as tabelas 'documents' e 'metrics'."""
    db_path = get_user_data_path(DB_NAME)
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                response_time REAL,
                used_knowledge_base BOOLEAN,
                profile_used TEXT
            )
        """)
        conn.commit()
        logging.info(f"Banco de dados inicializado em: {db_path}")
    except sqlite3.Error as e:
        logging.error(f"Erro ao inicializar o banco de dados: {e}")
    finally:
        if conn:
            conn.close()


def log_metric(response_time, used_knowledge_base, profile_used):
    """Registra uma métrica de uso no banco de dados."""
    db_path = get_user_data_path(DB_NAME)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute(
            "INSERT INTO metrics (timestamp, response_time, used_knowledge_base, profile_used) VALUES (?, ?, ?, ?)",
            (timestamp, response_time, used_knowledge_base, profile_used)
        )
        conn.commit()
    except Exception as e:
        logging.error(f"Erro ao registrar métrica: {e}")
    finally:
        conn.close()

def save_document_to_db(filename, content):
    """Guarda um documento na base de dados."""
    db_path = get_user_data_path(DB_NAME)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        cursor.execute(
            "INSERT INTO documents (filename, content, timestamp) VALUES (?, ?, ?)",
            (filename, content, timestamp)
        )
        conn.commit()
        logging.info(f"Documento '{filename}' guardado com sucesso.")
        return True
    except Exception as e:
        logging.error(f"Erro ao guardar documento: {e}")
        return False
    finally:
        conn.close()

def load_documents_from_db():
    """Carrega todos os documentos da base de dados."""
    db_path = get_user_data_path(DB_NAME)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, timestamp FROM documents ORDER BY timestamp DESC")
    documents = cursor.fetchall()
    conn.close()
    return documents

def delete_document_from_db(doc_id):
    """Remove um documento da base de dados."""
    db_path = get_user_data_path(DB_NAME)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()
        logging.info(f"Documento ID {doc_id} removido.")
        return True
    except Exception as e:
        logging.error(f"Erro ao remover documento: {e}")
        return False
    finally:
        conn.close()

@lru_cache(maxsize=100)
def search_knowledge_base(query_text):
    """
    Pesquisa na base de conhecimento, retornando apenas os trechos mais relevantes.
    """
    logging.info(f"A iniciar pesquisa na base de conhecimento para: '{query_text}'")
    
    keywords = set(re.findall(r'\b\w{3,}\b', query_text.lower()))
    if not keywords:
        logging.info("Nenhuma palavra-chave válida encontrada na pergunta.")
        return ""

    logging.info(f"Palavras-chave extraídas: {keywords}")

    db_path = get_user_data_path(DB_NAME)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query_parts = []
    params = []
    for keyword in keywords:
        query_parts.append("content LIKE ?")
        params.append(f"%{keyword}%")
    
    if not query_parts:
        return ""

    sql_query = "SELECT filename, content FROM documents WHERE " + " OR ".join(query_parts)
    
    try:
        cursor.execute(sql_query, params)
        relevant_docs = cursor.fetchall()
    except sqlite3.Error as e:
        logging.error(f"Erro na busca ao banco de dados: {e}")
        return ""
    finally:
        conn.close()

    if not relevant_docs:
        logging.info("Nenhum documento relevante encontrado na base de conhecimento.")
        return ""

    all_snippets = []
    for filename, content in relevant_docs:
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if not para.strip():
                continue
            
            score = 0
            found_keywords = set()
            for keyword in keywords:
                if keyword in para.lower():
                    score += para.lower().count(keyword)
                    found_keywords.add(keyword)
            
            if score > 0:
                all_snippets.append({
                    'filename': filename,
                    'content': para.strip(),
                    'score': score,
                    'keyword_count': len(found_keywords)
                })

    if not all_snippets:
        logging.info("Nenhum trecho relevante encontrado nos documentos.")
        return ""

    # Ordena pela pontuação e depois pelo número de palavras-chave únicas encontradas
    all_snippets.sort(key=lambda x: (x['score'], x['keyword_count']), reverse=True)
    # Pega os 3 trechos mais relevantes
    top_snippets = all_snippets[:3]
    
    context_parts = [f"FICHEIRO: {s['filename']}\nTRECHO RELEVANTE:\n---\n{s['content']}\n---" for s in top_snippets]
    final_context = "\n\n".join(context_parts)
    logging.info(f"Contexto gerado para a IA com {len(top_snippets)} trecho(s).")
    
    return final_context

# --- Funções de Manipulação de Ficheiros ---
def extract_text_from_file(file_path):
    """Extrai texto de PDF ou TXT."""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                return '\n'.join(page.extract_text() or '' for page in reader.pages)
        except Exception as e:
            logging.error(f"Erro ao ler PDF: {e}")
            return None
            
    elif ext == '.txt':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logging.error(f"Erro ao ler TXT: {e}")
            return None
            
    logging.warning(f"Formato não suportado: {ext}")
    return None

def save_history_to_file(history_data):
    """Salva todo o histórico de conversas num ficheiro JSON."""
    history_file_path = get_user_data_path(HISTORY_FILE)
    try:
        with open(history_file_path, "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Erro ao guardar histórico em JSON: {e}")

def load_history_from_file():
    """Carrega o histórico de conversas a partir de um ficheiro JSON."""
    history_file_path = get_user_data_path(HISTORY_FILE)
    if not os.path.exists(history_file_path):
        return []
    try:
        with open(history_file_path, "r", encoding="utf-8") as f:
            if os.path.getsize(history_file_path) > 0:
                data = json.load(f)
                return data if isinstance(data, list) else []
            else:
                return []
    except (json.JSONDecodeError, TypeError):
        logging.error("Erro ao ler o ficheiro de histórico JSON. A criar um novo.")
        return []
    except Exception as e:
        logging.error(f"Erro inesperado ao carregar histórico: {e}")
        return []
