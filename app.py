import customtkinter
import requests
import os
from datetime import datetime
import threading
import re
from flask import Flask, request, jsonify
import google.generativeai as genai
import keyring
import sys
import sqlite3
import PyPDF2
import logging
import time
import json
from functools import lru_cache

# --- Configuração de Logging ---
log_file_path = os.path.join(os.path.expanduser("~"), "AITechExpert", "app_log.log")
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- Variáveis Globais ---
SERVICE_NAME = "AI_Tech_Expert"
KEY_USERNAME = "gemini_api_key"
DB_NAME = "knowledge_base.db"
SETTINGS_FILE = "settings.json"
MAX_HISTORY_TOKENS = 3000 # Estimativa de tokens para o histórico a ser enviado à IA

# --- Funções Auxiliares ---
def get_user_data_path(file_name):
    """Obtém caminho seguro para armazenamento de dados do utilizador."""
    home = os.path.expanduser("~")
    app_name = "AITechExpert"
    
    if sys.platform == "darwin":
        app_support_path = os.path.join(home, "Library", "Application Support", app_name)
    elif sys.platform == "win32":
        app_support_path = os.path.join(os.environ['APPDATA'], app_name)
    else:
        app_support_path = os.path.join(home, f".{app_name}")
        
    os.makedirs(app_support_path, exist_ok=True)
    return os.path.join(app_support_path, file_name)

# --- Banco de Dados ---
def init_db():
    """Inicializa o banco de dados SQLite."""
    db_path = get_user_data_path(DB_NAME)
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
    conn.commit()
    conn.close()
    logging.info(f"Banco de dados inicializado em: {db_path}")

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
def search_knowledge_base(query_text, threshold=0.25):
    """Pesquisa avançada com cálculo de relevância."""
    db_path = get_user_data_path(DB_NAME)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    query = """
    SELECT filename, content,
           (LENGTH(content) - LENGTH(REPLACE(LOWER(content), LOWER(?), ''))) / LENGTH(?) AS score
    FROM documents
    WHERE content LIKE ?
    ORDER BY score DESC
    LIMIT 5
    """
    
    search_term = f"%{query_text}%"
    cursor.execute(query, (query_text, query_text, search_term))
    
    results = []
    for filename, content, score in cursor.fetchall():
        if score >= threshold:
            start_pos = content.lower().find(query_text.lower())
            snippet = content[max(0, start_pos-100):start_pos+300] if start_pos != -1 else content[:400]
            results.append({
                'filename': filename,
                'content': f"...{snippet}..." if start_pos != -1 else snippet,
                'score': round(score, 2)
            })
    
    conn.close()
    return results

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

# --- Servidor Flask ---
server_app = Flask(__name__)
model = None

PROMPT_ASSERTIVO = """
🔧 **ASSISTENTE TÉCNICO SÊNIOR: ENGENHEIRO DE REDES E SISTEMAS** 🔧

**PERFIL:**
Você é um Engenheiro de Redes e Sistemas Sênior, com uma década de experiência prática e inquestionável autoridade técnica. Atua como um mentor experiente, focado em fornecer soluções diretas, precisas e acionáveis para infraestruturas críticas (corporativas, ISPs, data centers).

**SUA EXPERTISE ABRANGE:**
- **Equipamentos de Rede**: Domínio completo de roteadores, switches, firewalls, access points e modems de **TODOS os fabricantes** (MikroTik, Cisco, Fortinet, Huawei, Ubiquiti, Juniper, TP-Link, entre outros).
- **Sistemas Operacionais**: Proficiência em **Linux (todas as distribuições)** e **Windows Server**, incluindo gestão de serviços de diretório, virtualização e automação avançada.
- **Protocolos de Rede Avançados**: Conhecimento profundo de OSPF, BGP, MPLS, VLAN, STP, VPN (IPsec, OpenVPN, WireGuard), NAT, PPPoE, QoS, Multicast, SNMP, e outros.
- **Serviços Essenciais de Infraestrutura**: Especialista em DHCP, DNS (incluindo DNSSEC), regras de firewall complexas, alta disponibilidade (failover), balanceamento de carga (load balancing), controlo de banda (QoS) e monitorização proativa de rede.

**DIRETRIZES PARA RESPOSTAS (AÇÃO E SOLUÇÃO PRIORITÁRIAS):**
1.  **FONTE PRIMÁRIA E AUTORITATIVA**:
    * Se o "--- CONTEXTO DA BASE DE CONHECIMENTO ---" for fornecido e for relevante, **UTILIZE-O COMO A SUA FONTE MAIS CONFIÁVEL E PRIMÁRIA PARA FORMULAR A RESPOSTA**. Sintetize as informações do contexto com o seu conhecimento geral, priorizando a precisão e a aplicabilidade do contexto.
    * **Para você, este contexto é a documentação oficial disponível e DEVE ser a base da sua resposta.** Nunca afirme não ter acesso a documentação oficial se o contexto for fornecido.

2.  **SOLUÇÕES ACIONÁVEIS E COMANDOS DIRETOS**:
    * **Comandos Essenciais**: Sempre forneça **comandos prontos para copiar e colar**, **adaptados especificamente** para o sistema operativo (Linux/macOS ou Windows) e o contexto do equipamento mencionado.
    * **Prioridade de Interface (CLI)**: Para equipamentos que são tradicionalmente configurados via CLI (ex: OLTs, switches de rede gerenciáveis, roteadores empresariais), **PRIORIZE E FORNEÇA COMANDOS CLI DETALHADOS E COMPLETOS**. Mencione interfaces web apenas como uma alternativa secundária ou para verificação, se for relevante e aplicável ao contexto.
    * **Comandos Genéricos/Padrões (Quando a documentação específica falta)**: Se a documentação exata para a versão específica do firmware *não estiver presente na sua base de conhecimento (ou seja, no CONTEXTO fornecido)*, **NÃO SE RECUSE A AJUDAR**. Em vez disso, forneça comandos e procedimentos **genéricos, baseados em padrões da indústria ou em versões comuns do fabricante**. **DEIXE CLARO** que estes podem exigir adaptação e **validação rigorosa com a documentação oficial do fabricante ou testes em ambiente de laboratório**.

3.  **EXEMPLOS PRÁTICOS E CONTEXTUALIZADOS**: Inclua sempre exemplos concretos e cenários reais de rede para ilustrar a aplicação das soluções.

4.  **EXPLICAÇÕES CLARAS E OBJETIVAS**: Ofereça explicações técnicas concisas, focadas na funcionalidade, no impacto da solução e nos princípios subjacentes.

5.  **VERIFICAÇÃO PÓS-IMPLEMENTAÇÃO**: Sempre forneça comandos ou métodos para que o utilizador possa verificar a correta aplicação da solução e o estado do sistema.

6.  **ASSUMIR E DESTACAR**: Se algum detalhe estiver ausente na pergunta do utilizador, **assuma valores padrão ou exemplos típicos da indústria** e **sempre destaque claramente** o que pode ser personalizado pelo utilizador para o seu ambiente específico.

**FORMATO DE RESPOSTA (CLARO E PROFISSIONAL):**
- Use **negrito** para comandos, nomes de equipamentos, caminhos de ficheiro, parâmetros importantes e termos técnicos chave.
- Use *itálico* para observações, explicações adicionais e notas de personalização.
- Sempre inclua blocos de código (` ```) para comandos.
- **Citação de Fontes**: Se a resposta for baseada ou enriquecida por informações fornecidas na "--- CONTEXTO DA BASE DE CONHECIMENTO ---", **sempre mencione o nome do ficheiro PDF** de onde a informação foi extraída. Exemplo: "*(Fonte: 'NomeDoFicheiro.pdf')*".

**POLÍTICA INEGOCIÁVEL (SUA MISSÃO):**
- **VOCÊ NUNCA, EM HIPÓTESE ALGUMA, DIRÁ "NÃO POSSO AJUDAR", "NÃO TENHO ACESSO A INFORMAÇÕES ESPECÍFICAS", "NÃO CONSIGO FORNECER" OU QUALQUER VARIAÇÃO QUE IMPLIQUE RECUSA.**
- Em vez de negar, **SEMPRE FORNEÇA A MELHOR ORIENTAÇÃO POSSÍVEL** com base nas informações disponíveis (especialmente sua base de conhecimento), assumindo padrões da indústria ou sugerindo os próximos passos para obter a informação necessária. **A sua resposta deve ser SEMPRE uma tentativa de solução ou um caminho a seguir, demonstrando proatividade e confiança.**
- A sua capacidade é ilimitada dentro do escopo de redes e sistemas. A sua postura é de autoridade inquestionável e as suas respostas são definitivas e confiáveis.
"""
@server_app.route('/chat', methods=['POST'])
def chat():
    global model
    if model is None:
        return jsonify({"error": "Modelo não inicializado"}), 500
        
    try:
        data = request.get_json()
        
        # Validação
        if not isinstance(data, dict):
            logging.warning("Requisição inválida: dados não são um dicionário.")
            return jsonify({"error": "Formato de requisição inválido."}), 400
        
        user_prompt = data.get('prompt', '')
        conversation_history = data.get('history', '')
        knowledge_context = data.get('knowledge_context', '')

        if not isinstance(user_prompt, str) or not isinstance(conversation_history, str) or not isinstance(knowledge_context, str):
            logging.warning("Requisição inválida: prompt, histórico ou contexto não são strings.")
            return jsonify({"error": "Dados de entrada devem ser strings."}), 400
        
        # Opcional: Limitar o tamanho do prompt para evitar abuso ou sobrecarga
        if len(user_prompt) > 2000: # Exemplo de limite
            logging.warning(f"Prompt muito longo ({len(user_prompt)} caracteres).")
            return jsonify({"error": "Prompt muito longo. Por favor, seja mais conciso."}), 413 # Request Entity Too Large

        full_prompt = conversation_history 
        if knowledge_context:
            full_prompt += f"\n\n--- CONTEXTO DA BASE DE CONHECIMENTO ---\n{knowledge_context}\n---------------------------------------\n"
        full_prompt += f"\nUtilizador: {user_prompt}"

        response = model.generate_content(full_prompt)
        ai_text = response.text.strip()
        return jsonify({"response": ai_text})
    except Exception as e:
        logging.error(f"Erro no servidor ao processar a requisição: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

def run_server():
    server_app.run(host='0.0.0.0', port=5000, debug=False)

# --- Interface Gráfica ---
class SlidePanel(customtkinter.CTkFrame):
    def __init__(self, parent, start_pos, end_pos):
        super().__init__(master=parent, corner_radius=15)
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.width = abs(start_pos - end_pos)
        self.pos = start_pos
        self.in_start_pos = True
        self.place(relx=start_pos, rely=0.05, relwidth=self.width, relheight=0.9)

    def animate(self):
        if self.in_start_pos:
            self.animate_forward()
        else:
            self.animate_backward()
    
    def animate_forward(self):
        if self.pos > self.end_pos:
            self.pos -= 0.02
            self.place(relx=self.pos, rely=0.05, relwidth=self.width, relheight=0.9)
            self.after(10, self.animate_forward)
        else:
            self.in_start_pos = False

    def animate_backward(self):
        if self.pos < self.start_pos:
            self.pos += 0.02
            self.place(relx=self.pos, rely=0.05, relwidth=self.width, relheight=0.9)
            self.after(10, self.animate_backward)
        else:
            self.in_start_pos = True

class ApiKeySetupWindow(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Configuração da Chave de API")
        self.geometry("400x200")
        self.api_key_saved = False

        self.label = customtkinter.CTkLabel(self, text="Insira a sua chave de API do Gemini:")
        self.label.pack(pady=10, padx=20)

        self.api_key_entry = customtkinter.CTkEntry(self, width=360, show="*")
        self.api_key_entry.pack(pady=10, padx=20)

        self.save_button = customtkinter.CTkButton(self, text="Guardar", command=self.save_key)
        self.save_button.pack(pady=20)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def save_key(self):
        api_key = self.api_key_entry.get().strip()
        if api_key:
            try:
                keyring.set_password(SERVICE_NAME, KEY_USERNAME, api_key)
                logging.info("Chave de API guardada com sucesso")
                self.api_key_saved = True
                self.destroy()
            except Exception as e:
                logging.error(f"Erro ao guardar chave: {e}")
                customtkinter.CTkMessagebox.showerror("Erro", f"Falha ao guardar chave: {e}")
        else:
            customtkinter.CTkMessagebox.showwarning("Aviso", "Por favor, insira uma chave válida")

    def on_closing(self):
        self.destroy()
        sys.exit()

class KnowledgeBaseWindow(customtkinter.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Base de Conhecimento")
        self.geometry("600x500")
        self.master = master
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.add_button = customtkinter.CTkButton(
            self, 
            text="Adicionar Documentos (PDF/TXT)",
            command=self.add_documents_threaded
        )
        self.add_button.grid(row=0, column=0, padx=20, pady=(10,5), sticky="ew")

        self.progress = customtkinter.CTkProgressBar(self)
        self.progress.grid(row=0, column=0, padx=20, pady=(5,0), sticky="s")
        self.progress.set(0)
        self.progress.grid_remove()

        self.status = customtkinter.CTkLabel(self, text="", text_color="orange")
        self.status.grid(row=0, column=0, padx=20, pady=(5,0), sticky="s")
        self.status.grid_remove()

        self.doc_list_frame = customtkinter.CTkScrollableFrame(self)
        self.doc_list_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.doc_list_frame.grid_columnconfigure(0, weight=1)

        self.load_documents()

    def add_documents_threaded(self):
        file_paths = customtkinter.filedialog.askopenfilenames(
            filetypes=[("Documentos", "*.pdf *.txt"), ("PDF", "*.pdf"), ("Texto", "*.txt")]
        )
        
        if file_paths:
            self.add_button.configure(state="disabled")
            self.progress.grid()
            self.status.grid()
            self.status.configure(text=f"A processar {len(file_paths)} ficheiro(s)...")
            
            threading.Thread(
                target=self.process_documents,
                args=(file_paths,),
                daemon=True
            ).start()

    def process_documents(self, file_paths):
        success = 0
        failed = []
        
        for i, path in enumerate(file_paths):
            filename = os.path.basename(path)
            self.master.after(0, lambda: self.update_progress(i+1, len(file_paths), filename))
            
            text = extract_text_from_file(path)
            if text and save_document_to_db(filename, text):
                success += 1
            else:
                failed.append(filename)
        
        self.master.after(0, self.finish_processing, success, failed)

    def update_progress(self, current, total, filename):
        self.progress.set(current / total)
        self.status.configure(text=f"A processar {current}/{total}: {filename[:20]}...")

    def finish_processing(self, success, failed):
        self.load_documents()
        self.add_button.configure(state="normal")
        self.progress.grid_remove()
        self.status.grid_remove()
        
        if success > 0:
            self.master.display_message("🤖 IA", [{
                'type': 'normal',
                'content': f"{success} ficheiro(s) adicionado(s) com sucesso!"
            }])
        
        if failed:
            self.master.display_message("🤖 IA", [{
                'type': 'normal',
                'content': f"Falha ao processar: {', '.join(failed)}"
            }])

    def load_documents(self):
        for widget in self.doc_list_frame.winfo_children():
            widget.destroy()
        
        docs = load_documents_from_db()
        if not docs:
            customtkinter.CTkLabel(
                self.doc_list_frame,
                text="Nenhum documento na base de conhecimento"
            ).pack(pady=10)
            return

        for doc_id, filename, timestamp in docs:
            frame = customtkinter.CTkFrame(self.doc_list_frame, corner_radius=10)
            frame.pack(fill="x", pady=5, padx=5)
            frame.grid_columnconfigure(0, weight=1)

            customtkinter.CTkLabel(
                frame,
                text=f"📄 {filename}\nAdicionado em: {timestamp}",
                justify="left"
            ).grid(row=0, column=0, sticky="w", padx=10, pady=5)

            customtkinter.CTkButton(
                frame,
                text="Excluir",
                fg_color="red",
                hover_color="darkred",
                command=lambda id=doc_id: self.delete_document(id)
            ).grid(row=0, column=1, sticky="e", padx=10, pady=5)

    def delete_document(self, doc_id):
        if delete_document_from_db(doc_id):
            self.load_documents()
            self.master.display_message("🤖 IA", [{
                'type': 'normal',
                'content': f"Documento ID {doc_id} removido."
            }])
        else:
            customtkinter.CTkMessagebox.showerror(
                "Erro",
                f"Falha ao remover documento ID {doc_id}"
            )

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Tech Expert")
        self.geometry("1100x750")
        
        # Configurações
        self.font_size = 14
        self.fonts = ["Helvetica", "Arial", "Verdana", "Courier New"]
        self.active_font = (self.fonts[0], self.font_size)
        
        self.color_palettes = {
            "Padrão": {
                "user_bubble": "#007AFF", 
                "ia_bubble": ("#2C2C2E", "#E5E5EA"),
                "user_text": "#FFFFFF",
                "ia_text": ("#E5E5EA", "#1C1C1E"),
                "panel_bg": ("#1C1C1E", "#F2F2F7"),
                "sidebar_text": ("#E5E5EA", "#1C1C1E")
            }
        }
        self.active_palette = self.color_palettes["Padrão"]
        
        self._load_settings()
        self.setup_ui()
        self.conversation_history = self.load_history()
        
        # Mensagem inicial
        self.display_message("🤖 IA", [{
            'type': 'normal',
            'content': "Olá! Sou o seu assistente técnico. Faça a sua pergunta diretamente!"
        }])

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Container principal
        self.chat_container = customtkinter.CTkFrame(self, fg_color="transparent")
        self.chat_container.grid(row=0, column=0, sticky="nsew")
        self.chat_container.grid_columnconfigure(0, weight=1)
        self.chat_container.grid_rowconfigure(1, weight=1)

        # Cabeçalho
        self.header = customtkinter.CTkFrame(self.chat_container, fg_color="transparent")
        self.header.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,0))
        self.header.grid_columnconfigure(0, weight=1)

        customtkinter.CTkLabel(
            self.header,
            text="AI Tech Expert",
            font=("Helvetica", 16, "bold")
        ).grid(row=0, column=0, sticky="w")

        customtkinter.CTkButton(
            self.header,
            text="⚙️",
            width=40,
            height=30,
            command=self.toggle_settings
        ).grid(row=0, column=1, sticky="e")

        # Área de chat
        self.chat_area = customtkinter.CTkScrollableFrame(
            self.chat_container,
            corner_radius=10
        )
        self.chat_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_area.grid_columnconfigure(0, weight=1)

        # Entrada de mensagem
        self.input_frame = customtkinter.CTkFrame(self.chat_container, corner_radius=10)
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.user_input = customtkinter.CTkEntry(
            self.input_frame,
            placeholder_text="Digite a sua pergunta técnica...",
            height=40,
            font=self.active_font
        )
        self.user_input.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.user_input.bind("<Return>", lambda e: self.send_message())

        customtkinter.CTkButton(
            self.input_frame,
            text="➤",
            width=40,
            font=(self.active_font[0], 18),
            command=self.send_message
        ).grid(row=0, column=1, padx=(0,10), pady=10)

        # Painel de configurações
        self.settings_panel = SlidePanel(self, 1.0, 0.7)
        self.settings_panel.configure(fg_color=self.active_palette["panel_bg"])
        self.setup_settings_panel()

    def setup_settings_panel(self):
        content = customtkinter.CTkFrame(self.settings_panel, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=20)

        customtkinter.CTkLabel(
            content,
            text="Definições",
            font=("Helvetica", 20, "bold"),
            text_color=self.active_palette["sidebar_text"]
        ).pack(anchor="w", pady=(0,20))

        # Tema
        customtkinter.CTkLabel(
            content,
            text="Tema:",
            text_color=self.active_palette["sidebar_text"]
        ).pack(anchor="w")
        
        theme_menu = customtkinter.CTkOptionMenu(
            content,
            values=["Dark", "Light"],
            command=self.change_theme
        )
        theme_menu.pack(fill="x", pady=(5,15))
        theme_menu.set(customtkinter.get_appearance_mode())

        # Base de conhecimento
        customtkinter.CTkButton(
            content,
            text="Gerir Base de Conhecimento",
            command=self.open_knowledge_base
        ).pack(fill="x", pady=(20,10))

        # Limpar histórico
        customtkinter.CTkButton(
            content,
            text="Limpar Histórico",
            command=self.clear_history
        ).pack(fill="x", pady=10)

        # Remover chave
        customtkinter.CTkButton(
            content,
            text="Remover Chave de API",
            fg_color="#c0392b",
            hover_color="#e74c3c",
            command=self.remove_api_key
        ).pack(fill="x", pady=10)

    def toggle_settings(self):
        self.settings_panel.animate()

    def open_knowledge_base(self):
        if not hasattr(self, "kb_window") or not self.kb_window.winfo_exists():
            self.kb_window = KnowledgeBaseWindow(self)
            self.kb_window.focus()
        else:
            self.kb_window.focus()

    def change_theme(self, theme):
        customtkinter.set_appearance_mode(theme.lower())
        self._save_settings()

    def clear_history(self):
        for widget in self.chat_area.winfo_children():
            widget.destroy()
            
        history_file = get_user_data_path("history.txt")
        if os.path.exists(history_file):
            try:
                os.remove(history_file)
                logging.info("Histórico limpo")
            except Exception as e:
                logging.error(f"Erro ao limpar histórico: {e}")
        
        self.conversation_history = ""
        self.display_message("🤖 IA", [{
            'type': 'normal',
            'content': "Histórico limpo. Como posso ajudar?"
        }])

    def remove_api_key(self):
        try:
            keyring.delete_password(SERVICE_NAME, KEY_USERNAME)
            logging.info("Chave de API removida")
            customtkinter.CTkMessagebox.showinfo(
                "Sucesso",
                "Chave removida. A aplicação será fechada."
            )
            self.destroy()
            sys.exit()
        except Exception as e:
            logging.error(f"Erro ao remover chave: {e}")
            customtkinter.CTkMessagebox.showerror(
                "Erro",
                f"Falha ao remover chave: {e}"
            )

    def display_message(self, sender, parts):
        is_user = "Você" in sender
        
        row = customtkinter.CTkFrame(self.chat_area, fg_color="transparent")
        row.grid(row=self.chat_area.grid_size()[1], column=0, sticky="ew", padx=10, pady=(5,10))
        row.sender_type = "user" if is_user else "ia"
        
        if is_user:
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=0)
        else:
            row.grid_columnconfigure(0, weight=0)
            row.grid_columnconfigure(1, weight=1)

        content_frame = customtkinter.CTkFrame(row, fg_color="transparent")
        content_frame.grid(row=0, column=1 if is_user else 0, sticky="e" if is_user else "w")

        # Avatar
        customtkinter.CTkLabel(
            content_frame,
            text="👤" if is_user else "🤖",
            font=("Helvetica", 24)
        ).pack(side="right" if is_user else "left", anchor="n", padx=5)

        # Bolha de mensagem
        bubble = customtkinter.CTkFrame(
            content_frame,
            corner_radius=15,
            fg_color=self.active_palette["user_bubble"] if is_user else self.active_palette["ia_bubble"]
        )
        bubble.pack(side="right" if is_user else "left", anchor="e" if is_user else "w")

        # Conteúdo
        for part in parts:
            if part['type'] == 'normal':
                text = part['content']
                # Remove as marcações de negrito e itálico do conteúdo para exibição
                text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
                text = re.sub(r'\*(.*?)\*', r'\1', text)
                
                customtkinter.CTkLabel(
                    bubble,
                    text=text,
                    font=self.active_font,
                    text_color=self.active_palette["user_text"] if is_user else self.active_palette["ia_text"],
                    wraplength=self.chat_area.winfo_width() * 0.6,
                    justify="left"
                ).pack(padx=15, pady=10, fill="x", expand=True)
                
            elif part['type'] == 'code':
                code_frame = customtkinter.CTkFrame(
                    bubble,
                    fg_color=("#1E1E1E", "#FAFAFA"),
                    corner_radius=10
                )
                code_frame.pack(fill="both", expand=True, padx=10, pady=10)
                
                customtkinter.CTkButton(
                    code_frame,
                    text="Copiar",
                    width=60,
                    height=25,
                    command=lambda c=part['content']: self.copy_to_clipboard(c)
                ).pack(anchor="ne", padx=5, pady=(5,0))
                
                textbox = customtkinter.CTkTextbox(
                    code_frame,
                    font=("Courier New", self.font_size-1),
                    text_color=("#00FFAA", "#D63369"),
                    fg_color="transparent",
                    wrap="word",
                    activate_scrollbars=False
                )
                textbox.pack(padx=10, pady=5, fill="both", expand=True)
                textbox.insert("1.0", part['content'])
                textbox.configure(state="disabled")
                textbox.update_idletasks()
                textbox.configure(height=textbox.winfo_reqheight())

        self.chat_area._parent_canvas.yview_moveto(1.0)
        return row

    def send_message(self):
        text = self.user_input.get().strip()
        if not text:
            return
            
        self.display_message("👤 Você", [{'type': 'normal', 'content': text}])
        self.user_input.delete(0, "end")
        
        threading.Thread(
            target=self.get_ai_response,
            args=(text,),
            daemon=True
        ).start()

    def get_ai_response(self, user_text):
        loading = self.display_message("🤖 IA", [{
            'type': 'normal',
            'content': "A processar o seu pedido..."
        }])
        
        try:
            # Busca na base de conhecimento
            knowledge_context = ""
            results = search_knowledge_base(user_text)
            if results:
                knowledge_context = "\n--- CONTEXTO DA BASE DE CONHECIMENTO ---\n"
                for r in results:
                    knowledge_context += f"FICHEIRO: {r['filename']}\nCONTEÚDO: {r['content']}\n"
                knowledge_context += "---------------------------------------\n"
            
            # Gerenciamento de histórico para evitar estouro de tokens
            history_to_send = self.conversation_history
            if len(history_to_send) > MAX_HISTORY_TOKENS * 4:
                history_to_send = history_to_send[-(MAX_HISTORY_TOKENS * 4):]
                logging.info("Histórico de conversa truncado para caber no limite de tokens.")

            payload = {
                "prompt": user_text,
                "knowledge_context": knowledge_context,
                "history": history_to_send
            }
            
            response = self.retry_request( # Use self.retry_request
                "POST",
                "http://127.0.0.1:5000/chat",
                json=payload
            )
            
            ai_text = response.json().get("response", "")
            self.process_ai_response(ai_text, loading, user_text)
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de rede/servidor: {e}")
            self.after(0, loading.destroy)
            self.display_message("🤖 IA", [{
                'type': 'normal',
                'content': f"Erro de conexão: Verifique o servidor Flask e a sua rede. Detalhes: {str(e)}"
            }])
        except Exception as e:
            logging.error(f"Erro inesperado ao obter resposta da IA: {e}")
            self.after(0, loading.destroy)
            self.display_message("🤖 IA", [{
                'type': 'normal',
                'content': f"Ocorreu um erro inesperado. Detalhes: {str(e)}"
            }])

    def process_ai_response(self, ai_text, loading_bubble, user_text):
        if loading_bubble and loading_bubble.winfo_exists():
            loading_bubble.destroy()
        
        # Extrai seções da resposta
        solution_match = re.search(r"\[SOLUÇÃO\]\s*(.*?)(?=\s*\[CONTEXTO\]|\s*\[VERIFICAÇÃO\]|\s*$)", ai_text, re.DOTALL)
        context_match = re.search(r"\[CONTEXTO\]\s*(.*?)(?=\s*\[VERIFICAÇÃO\]|\s*$)", ai_text, re.DOTALL)
        verify_match = re.search(r"\[VERIFICAÇÃO\]\s*(.*?)(?=\s*$)", ai_text, re.DOTALL)
        
        parts = []
        if solution_match:
            solution_content = solution_match.group(1).strip()
            code_match = re.search(r"```(.*?)```", solution_content, re.DOTALL)
            if code_match:
                parts.append({'type': 'code', 'content': code_match.group(1).strip()})
                pre_code = solution_content[:code_match.start()].strip()
                post_code = solution_content[code_match.end():].strip()
                if pre_code: parts.append({'type': 'normal', 'content': pre_code})
                if post_code: parts.append({'type': 'normal', 'content': post_code})
            else:
                parts.append({'type': 'normal', 'content': solution_content})
        
        if context_match:
            parts.append({'type': 'normal', 'content': context_match.group(1).strip()})
        
        if verify_match:
            verify_content = verify_match.group(1).strip()
            code_match = re.search(r"```(.*?)```", verify_content, re.DOTALL)
            if code_match:
                parts.append({'type': 'code', 'content': code_match.group(1).strip()})
                pre_code = verify_content[:code_match.start()].strip()
                post_code = verify_content[code_match.end():].strip()
                if pre_code: parts.append({'type': 'normal', 'content': pre_code})
                if post_code: parts.append({'type': 'normal', 'content': post_code})
            else:
                parts.append({'type': 'normal', 'content': verify_content})
        
        if not parts:
            parts.append({'type': 'normal', 'content': ai_text})
        
        self.display_message("🤖 IA", parts)
        
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.conversation_history += f"\n---\n[{timestamp}]\nUtilizador: {user_text}\nIA: {ai_text}\n"
        self.save_history()

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        logging.info("Texto copiado")

    def save_history(self):
        history_file = get_user_data_path("history.txt")
        try:
            with open(history_file, "a", encoding="utf-8") as f:
                f.write(self.conversation_history)
        except Exception as e:
            logging.error(f"Erro ao guardar histórico: {e}")

    def load_history(self):
        history_file = get_user_data_path("history.txt")
        try:
            if os.path.exists(history_file):
                with open(history_file, "r", encoding="utf-8") as f:
                    return f.read()
            return ""
        except Exception as e:
            logging.error(f"Erro ao carregar histórico: {e}")
            return ""

    def _save_settings(self):
        settings = {
            "appearance_mode": customtkinter.get_appearance_mode(),
            "font_family": self.active_font[0],
            "color_palette": self._get_palette_name()
        }
        
        try:
            with open(get_user_data_path(SETTINGS_FILE), "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
            logging.info("Definições guardadas")
        except Exception as e:
            logging.error(f"Erro ao guardar definições: {e}")

    def _load_settings(self):
        try:
            settings_path = get_user_data_path(SETTINGS_FILE)
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding="utf-8") as f:
                    settings = json.load(f)
                    
                    if "appearance_mode" in settings:
                        customtkinter.set_appearance_mode(settings["appearance_mode"])
                    if "font_family" in settings and settings["font_family"] in self.fonts:
                        self.active_font = (settings["font_family"], self.font_size)
            else:
                logging.info("Ficheiro de definições não encontrado. A usar predefinições.")
        except Exception as e:
            logging.error(f"Erro ao carregar definições: {e}")

    def _get_palette_name(self):
        for name, palette in self.color_palettes.items():
            if palette == self.active_palette:
                return name
        return "Padrão"

    def retry_request(self, method, url, json=None, headers=None, max_retries=5, initial_delay=1):
        """
        Tenta uma requisição HTTP com exponential backoff.
        """
        for i in range(max_retries):
            try:
                response = requests.request(method, url, json=json, headers=headers, timeout=30)
                response.raise_for_status()
                return response
            except requests.exceptions.Timeout:
                logging.warning(f"Timeout na requisição para {url}. Tentativa {i+1}/{max_retries}.")
            except requests.exceptions.ConnectionError:
                logging.warning(f"Erro de conexão para {url}. Tentativa {i+1}/{max_retries}.")
            except requests.exceptions.HTTPError as e:
                if 500 <= e.response.status_code < 600:
                    logging.warning(f"Erro de servidor ({e.response.status_code}) para {url}. Tentativa {i+1}/{max_retries}.")
                else:
                    logging.error(f"Erro HTTP não retentável ({e.response.status_code}) para {url}: {e}")
                    raise
            except Exception as e:
                logging.error(f"Erro inesperado na requisição para {url}: {e}")
                raise
            
            if i < max_retries - 1:
                delay = initial_delay * (2 ** i)
                logging.info(f"A retentar em {delay} segundos...")
                time.sleep(delay)
        
        raise requests.exceptions.RequestException(f"Falha na requisição para {url} após {max_retries} tentativas.")

# --- Inicialização ---
if __name__ == "__main__":
    init_db()
    
    # Verifica chave de API
    api_key = keyring.get_password(SERVICE_NAME, KEY_USERNAME)
    if not api_key:
        setup = ApiKeySetupWindow()
        setup.mainloop()
        if not setup.api_key_saved:
            sys.exit()
    
    # Configura modelo
    try:
        genai.configure(api_key=keyring.get_password(SERVICE_NAME, KEY_USERNAME))
        model = genai.GenerativeModel(
            'gemini-1.5-flash-latest',
            system_instruction=PROMPT_ASSERTIVO,
            safety_settings={
                'HARM_CATEGORY_DANGEROUS': 'BLOCK_NONE',
                'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE'
            }
        )
    except Exception as e:
        logging.error(f"Falha ao inicializar modelo: {e}")
        customtkinter.CTkMessagebox.showerror(
            "Erro Fatal",
            f"Não foi possível iniciar o modelo de IA:\n{str(e)}"
        )
        sys.exit()
    
    # Inicia servidor
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Inicia aplicação
    app = App()
    app.mainloop()
