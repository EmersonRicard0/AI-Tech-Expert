# /app_gui.py

import customtkinter
import requests
import os
from datetime import datetime
import threading
import sys
import json
import logging
import keyring
import re
from PIL import Image
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from CTkMessagebox import CTkMessagebox

from config import SETTINGS_FILE, AI_PROFILES, SERVICE_NAME, KEY_USERNAME
from database import (
    get_user_data_path, load_documents_from_db, delete_document_from_db,
    extract_text_from_file, save_document_to_db, search_knowledge_base,
    save_history_to_file, load_history_from_file
)

# --- CLASSES AUXILIARES DA UI ---

class SlidePanel(customtkinter.CTkFrame):
    def __init__(self, parent, start_pos, end_pos):
        super().__init__(master=parent, corner_radius=0)
        self.start_pos = start_pos
        self.end_pos = end_pos
        
        self.width = 0.25 # Largura fixa para a barra lateral
        self.place(relx=self.start_pos, rely=0.0, relwidth=self.width, relheight=1.0)

        self.pos = self.start_pos
        self.in_start_pos = True

    def animate(self):
        if self.in_start_pos:
            self.animate_forward()
        else:
            self.animate_backward()

    def animate_forward(self):
        if self.pos < self.end_pos:
            self.pos += 0.02
            self.place(relx=self.pos, rely=0.0, relwidth=self.width, relheight=1.0)
            self.after(10, self.animate_forward)
        else:
            self.in_start_pos = False

    def animate_backward(self):
        if self.pos > self.start_pos:
            self.pos -= 0.02
            self.place(relx=self.pos, rely=0.0, relwidth=self.width, relheight=1.0)
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
                CTkMessagebox(title="Erro", message=f"Falha ao guardar chave: {e}", icon="cancel")
        else:
            CTkMessagebox(title="Aviso", message="Por favor, insira uma chave válida", icon="warning")

    def on_closing(self):
        self.destroy()

class KnowledgeBaseWindow(customtkinter.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Base de Conhecimento")
        self.geometry("600x500")
        self.master = master
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.add_button = customtkinter.CTkButton(
            self, 
            text="Adicionar Documentos (PDF/TXT)",
            command=self.add_documents_threaded
        )
        self.add_button.grid(row=0, column=0, padx=20, pady=(10,5), sticky="ew")

        self.progress_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=1, column=0, padx=20, pady=0, sticky="ew")
        self.progress_frame.grid_columnconfigure(0, weight=1)

        self.status_label = customtkinter.CTkLabel(self.progress_frame, text="")
        self.status_label.pack(fill="x")

        self.progress_bar = customtkinter.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill="x", pady=(0, 5))
        
        self.progress_frame.grid_remove()
        
        self.doc_list_frame = customtkinter.CTkScrollableFrame(self)
        self.doc_list_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.doc_list_frame.grid_columnconfigure(0, weight=1)

        self.load_documents()

    def add_documents_threaded(self):
        file_paths = customtkinter.filedialog.askopenfilenames(
            title="Selecione os documentos",
            filetypes=[("Documentos", "*.pdf *.txt"), ("PDF", "*.pdf"), ("Texto", "*.txt")]
        )
        if file_paths:
            self.add_button.configure(state="disabled")
            self.progress_frame.grid()
            self.progress_bar.set(0)
            self.status_label.configure(text="A iniciar...")
            
            threading.Thread(target=self.process_documents, args=(file_paths,), daemon=True).start()

    def process_documents(self, file_paths):
        total_files = len(file_paths)
        success_count = 0
        failed_files = []
        
        for i, path in enumerate(file_paths):
            filename = os.path.basename(path)
            
            progress_value = (i + 1) / total_files
            status_text = f"A processar {i+1}/{total_files}: {filename[:30]}..."
            self.master.after(0, self.update_progress, progress_value, status_text)

            text = extract_text_from_file(path)
            if text and save_document_to_db(filename, text):
                success_count += 1
            else:
                failed_files.append(filename)
                
        self.master.after(0, self.on_processing_done, success_count, failed_files)

    def update_progress(self, value, text):
        self.progress_bar.set(value)
        self.status_label.configure(text=text)

    def on_processing_done(self, success_count, failed_files):
        self.add_button.configure(state="normal")
        self.progress_frame.grid_remove()
        self.load_documents()
        
        if success_count > 0:
            self.master.render_message("🤖 IA", [{'type': 'normal', 'content': f"{success_count} ficheiro(s) adicionados com sucesso!"}])
        if failed_files:
            self.master.render_message("🤖 IA", [{'type': 'normal', 'content': f"Falha ao processar: {', '.join(failed_files)}"}])

    def load_documents(self):
        for widget in self.doc_list_frame.winfo_children():
            widget.destroy()
        
        docs = load_documents_from_db()
        if not docs:
            customtkinter.CTkLabel(self.doc_list_frame, text="Nenhum documento na base de conhecimento").pack(pady=10)
            return

        for doc_id, filename, timestamp in docs:
            frame = customtkinter.CTkFrame(self.doc_list_frame, corner_radius=10)
            frame.pack(fill="x", pady=5, padx=5)
            frame.grid_columnconfigure(0, weight=1)
            customtkinter.CTkLabel(frame, text=f"📄 {filename}\nAdicionado em: {timestamp}", justify="left").grid(row=0, column=0, sticky="w", padx=10, pady=5)
            customtkinter.CTkButton(frame, text="Excluir", fg_color="red", hover_color="darkred", command=lambda id=doc_id: self.delete_document(id)).grid(row=0, column=1, sticky="e", padx=10, pady=5)

    def delete_document(self, doc_id):
        if delete_document_from_db(doc_id):
            self.load_documents()
            self.master.render_message("🤖 IA", [{'type': 'normal', 'content': f"Documento ID {doc_id} removido."}])
        else:
            CTkMessagebox(title="Erro", message=f"Falha ao remover documento ID {doc_id}", icon="cancel")


# --- CLASSE PRINCIPAL DA APLICAÇÃO ---

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Tech Expert")
        self.geometry("1200x800")
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self._scrollbar_hide_timer = None

        # --- CORES E FONTES ESTILO MODERNO ---
        self.APP_BG_COLOR = ("#ffffff", "#212121")
        self.SIDEBAR_COLOR = ("#f0f0f0", "#2b2b2b")
        self.CHAT_AREA_COLOR = ("#ffffff", "#212121")
        self.USER_BUBBLE_COLOR = "#007aff"
        self.AI_BUBBLE_COLOR = ("#e5e5ea", "#3b3b3b")
        self.TEXT_COLOR = ("#000000", "#ffffff")
        self.AI_TEXT_COLOR = ("#000000", "#f2f2f7")
        self.FONT_FAMILY = "Helvetica Neue"

        self.configure(fg_color=self.APP_BG_COLOR)

        try:
            base_path = os.path.dirname(os.path.realpath(__file__))
            assets_path = os.path.join(base_path, "assets")
            self.user_icon = customtkinter.CTkImage(Image.open(os.path.join(assets_path, "user_icon.png")), size=(36, 36))
            self.ai_icon = customtkinter.CTkImage(Image.open(os.path.join(assets_path, "ai_icon.png")), size=(36, 36))
        except FileNotFoundError:
            logging.error("Ficheiros de ícone não encontrados na pasta 'assets'. Usando emojis como fallback.")
            self.user_icon = None
            self.ai_icon = None
        
        self.font_size = 15
        self.active_font = (self.FONT_FAMILY, self.font_size)
        self.user_name_var = customtkinter.StringVar(value="Utilizador")
        self.selected_profile_var = customtkinter.StringVar(value=list(AI_PROFILES.keys())[0])
        
        self.history_data = load_history_from_file()
        self.current_chat_messages = []
        self.viewed_chat_messages = []
        self.is_viewing_history = False
        
        self._load_settings()
        self.setup_ui()
        self.start_new_chat(is_initial_start=True)

    def on_closing(self):
        """Salva a conversa atual antes de fechar a aplicação."""
        if self.current_chat_messages and len(self.current_chat_messages) > 0 and not self.is_viewing_history:
            logging.info("A salvar a conversa atual antes de sair...")
            session_to_save = {
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "messages": self.current_chat_messages
            }
            self.history_data.append(session_to_save)
            save_history_to_file(self.history_data)
        self.destroy()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- ÁREA PRINCIPAL DO CHAT ---
        self.main_chat_frame = customtkinter.CTkFrame(self, fg_color=self.CHAT_AREA_COLOR, corner_radius=0)
        self.main_chat_frame.grid(row=0, column=0, sticky="nsew")
        self.main_chat_frame.grid_columnconfigure(0, weight=1)
        self.main_chat_frame.grid_rowconfigure(1, weight=1)

        self.chat_area = customtkinter.CTkScrollableFrame(self.main_chat_frame, corner_radius=0, fg_color="transparent")
        self.chat_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=0)
        self.chat_area.grid_columnconfigure(0, weight=1)

        # --- MENSAGEM DE BOAS-VINDAS CENTRAL ---
        self.welcome_label = customtkinter.CTkLabel(
            self.main_chat_frame,
            text=f"Em que posso ajudá-lo hoje, {self.user_name_var.get()}?",
            font=(self.FONT_FAMILY, 32, "bold"),
            text_color=("gray60", "gray50")
        )

        # --- TOPO DA ÁREA DO CHAT ---
        chat_header = customtkinter.CTkFrame(self.main_chat_frame, fg_color="transparent", height=50)
        chat_header.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        
        left_header_frame = customtkinter.CTkFrame(chat_header, fg_color="transparent")
        left_header_frame.pack(side="left", fill="y", padx=0, pady=0)

        menu_button = customtkinter.CTkButton(
            left_header_frame, 
            text="☰", 
            width=36, 
            height=36,
            fg_color="transparent",
            hover_color=("gray90", "gray20"),
            font=(self.FONT_FAMILY, 24),
            command=self.toggle_sidebar
        )
        menu_button.pack(side="left", padx=(0, 10))
        
        title_label = customtkinter.CTkLabel(left_header_frame, text="AI Tech Expert", font=(self.FONT_FAMILY, 18, "bold"))
        title_label.pack(side="left")

        profile_frame = customtkinter.CTkFrame(chat_header, fg_color="transparent")
        profile_frame.pack(side="right", fill="y")

        customtkinter.CTkLabel(profile_frame, text="Perfil IA:", font=(self.FONT_FAMILY, 14)).pack(side="left", padx=(0,5))
        self.profile_menu = customtkinter.CTkOptionMenu(
            profile_frame,
            values=list(AI_PROFILES.keys()),
            variable=self.selected_profile_var,
            command=self.on_profile_change,
            font=(self.FONT_FAMILY, 14)
        )
        self.profile_menu.pack(side="left")

        # --- CAMPO DE ENTRADA ---
        self.input_frame = customtkinter.CTkFrame(self.main_chat_frame, corner_radius=25, height=50)
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(10, 20))
        
        self.send_button = customtkinter.CTkButton(
            self.input_frame, 
            text="➤", 
            width=44, 
            height=44, 
            font=(self.active_font[0], 24), 
            corner_radius=22,
            command=self.send_message
        )
        self.send_button.pack(side="right", padx=3, pady=3)

        self.user_input = customtkinter.CTkEntry(self.input_frame, placeholder_text="Pergunte alguma coisa...", height=48, font=self.active_font, border_width=0, fg_color="transparent")
        self.user_input.pack(side="left", fill="x", expand=True, padx=(20, 5), pady=3)
        self.user_input.bind("<Return>", lambda e: self.send_message())
        

        # --- PAINEL LATERAL UNIFICADO ---
        self.sidebar_panel = SlidePanel(self, -0.25, 0)
        self.sidebar_panel.configure(fg_color=self.SIDEBAR_COLOR)
        self.setup_sidebar()

        # --- LÓGICA DA BARRA DE ROLAGEM ---
        self.chat_scrollbar = self.chat_area._scrollbar
        self.chat_scrollbar.configure(width=12)
        self.hide_scrollbar() # Começa escondida

        # Eventos para mostrar a barra de rolagem
        self.chat_area.bind("<MouseWheel>", self.show_scrollbar)
        self.chat_scrollbar.bind("<B1-Motion>", self.show_scrollbar)

    def show_scrollbar(self, event=None):
        """Mostra a barra de rolagem e agenda para escondê-la."""
        self.chat_scrollbar.configure(fg_color=("gray85", "gray20"), button_color=("#6E6E6E", "#9E9E9E"))
        if self._scrollbar_hide_timer is not None:
            self.after_cancel(self._scrollbar_hide_timer)
        self._scrollbar_hide_timer = self.after(1500, self.hide_scrollbar)

    def hide_scrollbar(self):
        """Esconde a barra de rolagem tornando-a da cor do fundo."""
        bg_color = self.main_chat_frame.cget("fg_color")
        self.chat_scrollbar.configure(fg_color=bg_color, button_color=bg_color, button_hover_color=bg_color)

    def setup_sidebar(self):
        # Frame para o cabeçalho da barra lateral
        sidebar_header = customtkinter.CTkFrame(self.sidebar_panel, fg_color="transparent")
        sidebar_header.pack(fill="x", padx=10, pady=10)
        sidebar_header.grid_columnconfigure(0, weight=1)

        # Título
        customtkinter.CTkLabel(sidebar_header, text="Menu", font=(self.FONT_FAMILY, 16, "bold")).grid(row=0, column=0, sticky="w")

        # Botão para fechar
        customtkinter.CTkButton(sidebar_header, text="←", width=40, font=(self.FONT_FAMILY, 20), command=self.toggle_sidebar).grid(row=0, column=1, sticky="e")

        # --- ABAS (TABS) DENTRO DO PAINEL ---
        self.tab_view = customtkinter.CTkTabview(self.sidebar_panel, fg_color="transparent")
        self.tab_view.pack(fill="both", expand=True, padx=5, pady=5)
        self.tab_view.add("Conversas")
        self.tab_view.add("Definições")
        
        # --- CONTEÚDO DA ABA "CONVERSAS" ---
        conversas_tab = self.tab_view.tab("Conversas")
        conversas_tab.grid_columnconfigure(0, weight=1)
        conversas_tab.grid_rowconfigure(1, weight=1)
        
        self.new_chat_button = customtkinter.CTkButton(conversas_tab, text="Nova Conversa", command=self.start_new_chat, font=(self.FONT_FAMILY, 14, "bold"), height=40)
        self.new_chat_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        
        self.history_list_frame = customtkinter.CTkScrollableFrame(conversas_tab, label_text="Chats Anteriores")
        self.history_list_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.history_list_frame.grid_columnconfigure(0, weight=1)
        self.update_history_sidebar()

        # --- CONTEÚDO DA ABA "DEFINIÇÕES" ---
        settings_tab = self.tab_view.tab("Definições")
        
        customtkinter.CTkLabel(settings_tab, text="Personalização", font=(self.FONT_FAMILY, 16, "bold")).pack(anchor="w", pady=(10,10), padx=10)
        customtkinter.CTkLabel(settings_tab, text="Tema:", font=(self.FONT_FAMILY, 14)).pack(anchor="w", padx=10)
        theme_menu = customtkinter.CTkOptionMenu(settings_tab, values=["Dark", "Light", "System"], command=self.change_theme)
        theme_menu.pack(fill="x", pady=(5,15), padx=10)
        theme_menu.set(customtkinter.get_appearance_mode())
        
        customtkinter.CTkLabel(settings_tab, text="Seu Nome:", font=(self.FONT_FAMILY, 14)).pack(anchor="w", pady=(10,0), padx=10)
        name_entry = customtkinter.CTkEntry(settings_tab, textvariable=self.user_name_var)
        name_entry.pack(fill="x", pady=(5,15), padx=10)
        self.user_name_var.trace_add("write", self._save_settings)

        customtkinter.CTkLabel(settings_tab, text="Gestão de Dados", font=(self.FONT_FAMILY, 16, "bold")).pack(anchor="w", pady=(20,10), padx=10)
        
        customtkinter.CTkButton(settings_tab, text="Gerir Base de Conhecimento", command=self.open_knowledge_base).pack(fill="x", pady=5, padx=10)
        customtkinter.CTkButton(settings_tab, text="Exportar Conversa para PDF", command=self.export_conversation_to_pdf).pack(fill="x", pady=5, padx=10)
        customtkinter.CTkButton(settings_tab, text="Limpar Histórico", command=self.clear_history).pack(fill="x", pady=5, padx=10)
        customtkinter.CTkButton(settings_tab, text="Remover Chave de API", fg_color="#c0392b", hover_color="#e74c3c", command=self.remove_api_key).pack(fill="x", pady=(15, 5), padx=10)

    def send_message(self):
        text = self.user_input.get().strip()
        if not text: return
        
        message = {"sender": "👤 Você", "parts": [{'type': 'normal', 'content': text}]}
        self.current_chat_messages.append(message)
        self.render_message(message["sender"], message["parts"])
        
        self.user_input.delete(0, "end")
        threading.Thread(target=self.get_ai_response, args=(text,), daemon=True).start()

    def get_ai_response(self, user_text):
        loading_message = {"sender": "🤖 IA", "parts": [{'type': 'normal', 'content': "A processar..."}]}
        loading_widget = self.render_message(loading_message["sender"], loading_message["parts"])
        
        try:
            # Simplificamos o payload, o servidor agora faz a busca na base de conhecimento
            payload = {
                "prompt": user_text,
                "history": self.get_formatted_history(),
                "user_name": self.user_name_var.get(),
                "profile": self.selected_profile_var.get()
            }
            
            response = requests.post("http://127.0.0.1:5000/chat", json=payload, timeout=90)
            response.raise_for_status()
            ai_data = response.json()

            if isinstance(ai_data, dict) and "error" in ai_data:
                 raise Exception(ai_data["error"])

            self.after(0, self.process_ai_response, ai_data, loading_widget)
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de conexão: {e}")
            self.after(0, loading_widget.destroy)
            error_msg = {"sender": "🤖 IA", "parts": [{'type': 'normal', 'content': f"Não foi possível conectar ao servidor. Verifique se o 'server.py' está em execução.\nErro: {e}"}]}
            self.current_chat_messages.append(error_msg)
            self.render_message(error_msg["sender"], error_msg["parts"])

        except Exception as e:
            logging.error(f"Ocorreu um erro: {e}")
            self.after(0, loading_widget.destroy)
            error_message = {"sender": "🤖 IA", "parts": [{'type': 'normal', 'content': f"Ocorreu um erro: {e}"}]}
            self.current_chat_messages.append(error_message)
            self.render_message(error_message["sender"], error_message["parts"])
    
    def get_formatted_history(self):
        """Formata o histórico de mensagens para ser enviado à API."""
        MAX_HISTORY_MESSAGES = 20 # Limita o histórico enviado para as últimas 20 trocas
        recent_messages = self.current_chat_messages[-MAX_HISTORY_MESSAGES:]
        
        history_for_payload = []
        for msg in recent_messages:
            if msg.get('parts'):
                sender_name = "Utilizador" if "Você" in msg['sender'] else "IA"
                full_content = ' '.join(p['content'] for p in msg['parts'] if p.get('content'))
                history_for_payload.append(f"{sender_name}: {full_content}")
        
        return "\n".join(history_for_payload)

    def on_profile_change(self, new_profile):
        """Chamado quando o perfil da IA é alterado no menu suspenso."""
        logging.info(f"Perfil de IA alterado para: {new_profile}")
        self.render_message("🤖 IA", [{'type': 'normal', 'content': f"Perfil alterado para **{new_profile}**. As próximas respostas usarão este perfil."}])

    def process_ai_response(self, ai_data, loading_widget):
        if loading_widget and loading_widget.winfo_exists():
            loading_widget.destroy()

        parts = []
        if "solucao" in ai_data and ai_data["solucao"]: parts.append({'type': 'normal', 'content': ai_data["solucao"]})
        if "codigo" in ai_data and ai_data["codigo"]: parts.append({'type': 'code', 'content': ai_data["codigo"]})
        if "verificacao" in ai_data and ai_data["verificacao"]: parts.append({'type': 'normal', 'content': f"**Verificação:**\n{ai_data['verificacao']}"})
        if "fonte_contexto" in ai_data and ai_data["fonte_contexto"]: parts.append({'type': 'normal', 'content': f"*{ai_data['fonte_contexto']}*"})
        
        if not parts: parts.append({'type': 'normal', 'content': "Não obtive uma resposta válida."})

        message = {"sender": "🤖 IA", "parts": parts}
        self.current_chat_messages.append(message)
        self.render_message(message["sender"], message["parts"])

    def render_message(self, sender, parts):
        # Esconde a mensagem de boas-vindas assim que a primeira mensagem for renderizada
        self.welcome_label.place_forget()

        is_user = "Você" in sender
        row = customtkinter.CTkFrame(self.chat_area, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(10,10), anchor="e" if is_user else "w")
        if (is_user and self.user_icon) or (not is_user and self.ai_icon):
            icon = self.user_icon if is_user else self.ai_icon
            avatar = customtkinter.CTkLabel(row, image=icon, text="")
        else:
            avatar = customtkinter.CTkLabel(row, text="👤" if is_user else "🤖", font=(self.FONT_FAMILY, 24))
        
        bubble = customtkinter.CTkFrame(row, corner_radius=18, fg_color=self.USER_BUBBLE_COLOR if is_user else self.AI_BUBBLE_COLOR)
        
        if is_user:
            avatar.pack(side="right", anchor="n", padx=(10,0))
            bubble.pack(side="right", anchor="e")
        else:
            avatar.pack(side="left", anchor="n", padx=(0,10))
            bubble.pack(side="left", anchor="w")

        for part in parts:
            if part['type'] == 'normal':
                customtkinter.CTkLabel(bubble, text=part['content'], font=self.active_font, text_color="white" if is_user else self.AI_TEXT_COLOR, wraplength=self.chat_area.winfo_width() * 0.7, justify="left").pack(padx=15, pady=12, fill="x", expand=True)
            elif part['type'] == 'code':
                code_frame = customtkinter.CTkFrame(bubble, fg_color=("#2b2b2b", "#f5f5f5"), corner_radius=10)
                code_frame.pack(fill="both", expand=True, padx=10, pady=10)
                customtkinter.CTkButton(code_frame, text="Copiar", width=60, height=25, command=lambda c=part['content']: self.copy_to_clipboard(c)).pack(anchor="ne", padx=5, pady=(5,0))
                textbox = customtkinter.CTkTextbox(code_frame, font=("Courier New", self.font_size-1), text_color=("#39FF14", "#00008B"), fg_color="transparent", wrap="word", activate_scrollbars=False)
                textbox.pack(padx=10, pady=5, fill="both", expand=True)
                textbox.insert("1.0", part['content'])
                textbox.configure(state="disabled")
                self.after(50, lambda: textbox.configure(height=textbox.winfo_reqheight()))
        self.after(100, lambda: self.chat_area._parent_canvas.yview_moveto(1.0))
        return row

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        logging.info("Texto copiado para a área de transferência.")

    def export_conversation_to_pdf(self):
        if self.is_viewing_history:
            messages_to_export = self.viewed_chat_messages
        else:
            messages_to_export = self.current_chat_messages

        if not messages_to_export:
            CTkMessagebox(title="Aviso", message="Não há nenhuma conversa visível para exportar.", icon="warning")
            return
        
        try:
            file_path = customtkinter.filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF Documents", "*.pdf")],
                title="Salvar Conversa como PDF"
            )
            if not file_path:
                return

            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            styles['h1'].fontName = 'Helvetica-Bold'
            styles['h1'].alignment = 1 # Center
            styles['BodyText'].fontName = 'Helvetica'
            styles['Code'].fontName = 'Courier'

            story.append(Paragraph("Histórico da Conversa - AI Tech Expert", styles['h1']))
            story.append(Spacer(1, 0.25 * inch))

            for message in messages_to_export:
                sender = message.get("sender", "")
                parts = message.get("parts", [])

                if "Você" in sender:
                    story.append(Paragraph("<b>Você:</b>", styles['BodyText']))
                else:
                    story.append(Paragraph("<b>IA:</b>", styles['BodyText']))

                for part in parts:
                    content = part.get("content", "").replace('\n', '<br/>\n')
                    if part.get("type") == "code":
                        story.append(Paragraph(f"<pre>{content}</pre>", styles['Code']))
                    else:
                        story.append(Paragraph(content, styles['Normal']))
                
                story.append(Spacer(1, 0.2 * inch))

            doc.build(story)
            CTkMessagebox(title="Sucesso", message=f"Conversa exportada com sucesso para:\n{file_path}", icon="check")

        except Exception as e:
            logging.error(f"Erro ao exportar PDF: {e}")
            CTkMessagebox(title="Erro", message=f"Ocorreu um erro ao gerar o PDF:\n{e}", icon="cancel")

    def change_theme(self, theme):
        customtkinter.set_appearance_mode(theme.lower())
        self._save_settings()

    def clear_history(self):
        msg = CTkMessagebox(title="Limpar Histórico", message="Tem a certeza que deseja apagar TODO o histórico de conversas?", icon="warning", option_1="Cancelar", option_2="Sim")
        if msg.get() == 'Sim':
            self.history_data = []
            save_history_to_file(self.history_data)
            self.start_new_chat()
            self.update_history_sidebar()

    def remove_api_key(self):
        msg = CTkMessagebox(title="Remover Chave", message="Tem a certeza que deseja remover a sua chave de API? A aplicação será fechada.", icon="warning", option_1="Cancelar", option_2="Sim")
        if msg.get() == 'Sim':
            try:
                keyring.delete_password(SERVICE_NAME, KEY_USERNAME)
                logging.info("Chave de API removida.")
                self.destroy()
                sys.exit()
            except Exception as e:
                logging.error(f"Erro ao remover chave: {e}")
                CTkMessagebox(title="Erro", message=f"Falha ao remover chave: {e}", icon="cancel")
    
    def toggle_settings(self):
        self.sidebar_panel.animate()

    def toggle_sidebar(self):
        self.sidebar_panel.animate()

    def open_knowledge_base(self):
        if not hasattr(self, "kb_window") or not self.kb_window.winfo_exists():
            self.kb_window = KnowledgeBaseWindow(self)
            self.kb_window.focus()
        else:
            self.kb_window.focus()

    def start_new_chat(self, is_initial_start=False):
        if not is_initial_start and self.current_chat_messages and len(self.current_chat_messages) > 0 and not self.is_viewing_history:
            session_to_save = {
                "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "messages": self.current_chat_messages
            }
            self.history_data.append(session_to_save)
            save_history_to_file(self.history_data)
            self.update_history_sidebar()

        self.current_chat_messages = []
        self.clear_chat_area()

        self.is_viewing_history = False
        self.user_input.configure(state="normal")
        self.send_button.configure(state="normal")
        
    def continue_historical_chat(self, session_index):
        """Carrega uma conversa antiga para continuar de onde parou, sem a remover do histórico."""
        self.clear_chat_area()
        
        # Carrega a conversa selecionada para a sessão atual
        session_to_continue = self.history_data[session_index]
        self.current_chat_messages = session_to_continue["messages"]
        
        # Renderiza todas as mensagens da conversa carregada
        for message in self.current_chat_messages:
            self.render_message(message["sender"], message["parts"])
        
        # Habilita a entrada para que o utilizador possa continuar a conversa
        self.is_viewing_history = False
        self.user_input.configure(state="normal")
        self.send_button.configure(state="normal")
        self.toggle_sidebar() # Fecha a barra lateral para uma melhor experiência

    def delete_historical_chat(self, session_index):
        """Apaga uma conversa específica do histórico."""
        msg = CTkMessagebox(title="Apagar Conversa", message="Tem a certeza que deseja apagar esta conversa?", icon="warning", option_1="Cancelar", option_2="Sim")
        if msg.get() == "Sim":
            del self.history_data[session_index]
            save_history_to_file(self.history_data)
            self.update_history_sidebar()
            # Se a conversa apagada era a que estava a ser vista, inicia um novo chat
            if self.is_viewing_history:
                self.start_new_chat()

    def clear_chat_area(self):
        for widget in self.chat_area.winfo_children():
            widget.destroy()
        # Mostra a mensagem de boas-vindas quando a área de chat está limpa
        self.welcome_label.place(relx=0.5, rely=0.4, anchor="center")

    def update_history_sidebar(self):
        for widget in self.history_list_frame.winfo_children():
            widget.destroy()
        
        if not self.history_data:
            return

        for index, session in reversed(list(enumerate(self.history_data))):
            preview_text = session["messages"][0]["parts"][0]["content"][:25] + "..." if session["messages"] else "Conversa vazia"
            
            # Cria um frame para cada item do histórico
            item_frame = customtkinter.CTkFrame(self.history_list_frame)
            item_frame.pack(fill="x", pady=2)
            item_frame.grid_columnconfigure(0, weight=1)

            # Botão para continuar a conversa
            chat_button = customtkinter.CTkButton(
                item_frame, 
                text=f"{preview_text}",
                command=lambda i=index: self.continue_historical_chat(i),
                anchor="w",
                font=(self.FONT_FAMILY, 13)
            )
            chat_button.grid(row=0, column=0, padx=(0, 5), sticky="ew")

            # Botão para apagar a conversa
            delete_button = customtkinter.CTkButton(
                item_frame,
                text="X",
                command=lambda i=index: self.delete_historical_chat(i),
                width=30,
                fg_color="transparent",
                hover_color="#c0392b"
            )
            delete_button.grid(row=0, column=1, padx=(0, 5))

    def _save_settings(self, *args):
        settings = {
            "appearance_mode": customtkinter.get_appearance_mode(),
            "user_name": self.user_name_var.get()
        }
        try:
            with open(get_user_data_path(SETTINGS_FILE), "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
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
                    if "user_name" in settings and settings["user_name"]:
                        self.user_name_var.set(settings["user_name"])
        except Exception as e:
            logging.error(f"Erro ao carregar definições: {e}")
