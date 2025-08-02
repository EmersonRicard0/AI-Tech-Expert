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

# --- Variáveis Globais de Configuração ---
SERVICE_NAME = "AI_Tech_Expert"
KEY_USERNAME = "gemini_api_key"

# --- FUNÇÃO PARA OBTER CAMINHO SEGURO PARA DADOS ---
def get_user_data_path(file_name):
    """Cria um caminho seguro para salvar arquivos de dados do app."""
    home = os.path.expanduser("~")
    app_name = "AITechExpert"
    
    if sys.platform == "darwin": # macOS
        app_support_path = os.path.join(home, "Library", "Application Support", app_name)
    elif sys.platform == "win32": # Windows
        app_support_path = os.path.join(os.environ['APPDATA'], app_name)
    else: # Linux e outros
        app_support_path = os.path.join(home, f".{app_name}")
        
    os.makedirs(app_support_path, exist_ok=True)
    return os.path.join(app_support_path, file_name)

# --- INÍCIO DA SEÇÃO DO SERVIDOR (BACKEND) ---
server_app = Flask(__name__)
model = None # O modelo será inicializado depois de obter a chave

@server_app.route('/chat', methods=['POST'])
def chat():
    global model
    if model is None:
        return jsonify({"error": "Modelo de IA não inicializado"}), 500
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"error": "Prompt não encontrado na requisição"}), 400
        user_prompt = data.get('prompt', '')
        conversation_history = data.get('history', '')
        full_prompt = conversation_history + f"\nUsuário: {user_prompt}"
        response = model.generate_content(full_prompt)
        ai_text = response.text.strip()
        return jsonify({"response": ai_text})
    except Exception as e:
        print(f"Erro no servidor ao processar a requisição: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

def run_server():
    server_app.run(host='0.0.0.0', port=5000, debug=False)

# --- FIM DA SEÇÃO DO SERVIDOR ---


# --- INÍCIO DA SEÇÃO DA INTERFACE (CLIENTE) ---

class ApiKeySetupWindow(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("Configuração da Chave de API")
        self.geometry("400x200")
        self.api_key_saved = False

        self.label = customtkinter.CTkLabel(self, text="Por favor, insira sua chave de API do Gemini:")
        self.label.pack(pady=10, padx=20)

        self.api_key_entry = customtkinter.CTkEntry(self, width=360, show="*")
        self.api_key_entry.pack(pady=10, padx=20)

        self.save_button = customtkinter.CTkButton(self, text="Salvar e Continuar", command=self.save_key)
        self.save_button.pack(pady=20)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        self.destroy()
        sys.exit()

    def save_key(self):
        api_key = self.api_key_entry.get()
        if api_key:
            try:
                keyring.set_password(SERVICE_NAME, KEY_USERNAME, api_key)
                print("✅ Chave de API salva com sucesso no cofre de senhas!")
                self.api_key_saved = True
                self.destroy()
            except Exception as e:
                print(f"❌ Ocorreu um erro ao salvar a chave: {e}")
        else:
            print("Nenhuma chave inserida.")

class SlidePanel(customtkinter.CTkFrame):
    def __init__(self, parent, start_pos, end_pos):
        super().__init__(master=parent, corner_radius=15)
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.width = abs(start_pos - end_pos)
        self.pos = self.start_pos
        self.in_start_pos = True
        self.place(relx=self.start_pos, rely=0.05, relwidth=self.width, relheight=0.9)

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

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI Tech Expert")
        self.geometry("1100x750")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.font_size = 14
        self.fonts = ["Helvetica", "Arial", "Verdana", "Calibri", "Courier New"]
        self.active_font = (self.fonts[0], self.font_size)

        self.color_palettes = {
            "Meia-noite": {"user_bubble": "#007AFF", "ia_bubble": ("#2C2C2E", "#E5E5EA"), "user_text": "#FFFFFF", "ia_text": ("#E5E5EA", "#1C1C1E"), "panel_bg": ("#1C1C1E", "#F2F2F7"), "sidebar_text": ("#E5E5EA", "#1C1C1E")},
            "Esmeralda": {"user_bubble": "#34C759", "ia_bubble": ("#2C2C2E", "#E5E5EA"), "user_text": "#FFFFFF", "ia_text": ("#E5E5EA", "#1C1C1E"), "panel_bg": ("#1C1C1E", "#F2F2F7"), "sidebar_text": ("#E5E5EA", "#1C1C1E")},
            "Ametista": {"user_bubble": "#AF52DE", "ia_bubble": ("#2C2C2E", "#E5E5EA"), "user_text": "#FFFFFF", "ia_text": ("#E5E5EA", "#1C1C1E"), "panel_bg": ("#1C1C1E", "#F2F2F7"), "sidebar_text": ("#E5E5EA", "#1C1C1E")}
        }
        self.active_palette = self.color_palettes["Meia-noite"]

        self.chat_container = customtkinter.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.chat_container.grid(row=0, column=0, sticky="nsew")
        self.chat_container.grid_columnconfigure(0, weight=1)
        self.chat_container.grid_rowconfigure(1, weight=1)

        self.header_frame = customtkinter.CTkFrame(self.chat_container, corner_radius=0, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10,0))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.app_title_label = customtkinter.CTkLabel(self.header_frame, text="AI Tech Expert", font=("Helvetica", 16, "bold"))
        self.app_title_label.grid(row=0, column=0, sticky="w")

        self.menu_button = customtkinter.CTkButton(self.header_frame, text="⚙️", width=40, height=30, command=self.toggle_slide_panel)
        self.menu_button.grid(row=0, column=1, sticky="e")

        self.chat_area = customtkinter.CTkScrollableFrame(self.chat_container, corner_radius=10)
        self.chat_area.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.chat_area.grid_columnconfigure(0, weight=1)

        self.input_frame = customtkinter.CTkFrame(self.chat_container, corner_radius=10)
        self.input_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.user_entry = customtkinter.CTkEntry(self.input_frame, placeholder_text="Digite sua dúvida técnica...", corner_radius=8, height=40, font=self.active_font)
        self.user_entry.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.user_entry.bind("<Return>", self.send_message_event)

        self.send_button = customtkinter.CTkButton(self.input_frame, text="➤", command=self.send_message, corner_radius=8, width=40, font=(self.active_font[0], 18))
        self.send_button.grid(row=0, column=1, padx=(0, 10), pady=10)

        self.slide_panel = SlidePanel(self, 1.0, 0.7)
        self.slide_panel.configure(fg_color=self.active_palette["panel_bg"])
        
        sidebar_content_frame = customtkinter.CTkFrame(self.slide_panel, fg_color="transparent")
        sidebar_content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.sidebar_title = customtkinter.CTkLabel(sidebar_content_frame, text="Configurações", font=("Helvetica", 20, "bold"), text_color=self.active_palette["sidebar_text"])
        self.sidebar_title.pack(anchor="w", pady=(0, 20))

        self.theme_label = customtkinter.CTkLabel(sidebar_content_frame, text="Tema:", text_color=self.active_palette["sidebar_text"])
        self.theme_label.pack(anchor="w")
        self.theme_menu = customtkinter.CTkOptionMenu(sidebar_content_frame, values=["Dark", "Light"], command=self.change_appearance_mode_event)
        self.theme_menu.pack(fill="x", pady=(5, 15))
        self.theme_menu.set("Dark")

        self.font_label = customtkinter.CTkLabel(sidebar_content_frame, text="Fonte:", text_color=self.active_palette["sidebar_text"])
        self.font_label.pack(anchor="w")
        self.font_menu = customtkinter.CTkOptionMenu(sidebar_content_frame, values=self.fonts, command=self.change_font_event)
        self.font_menu.pack(fill="x", pady=(5, 15))
        self.font_menu.set(self.fonts[0])

        self.palette_label = customtkinter.CTkLabel(sidebar_content_frame, text="Paleta de Cores:", text_color=self.active_palette["sidebar_text"])
        self.palette_label.pack(anchor="w")
        self.palette_menu = customtkinter.CTkOptionMenu(sidebar_content_frame, values=list(self.color_palettes.keys()), command=self.change_color_palette_event)
        self.palette_menu.pack(fill="x", pady=(5, 15))
        self.palette_menu.set("Meia-noite")

        self.clear_history_button = customtkinter.CTkButton(sidebar_content_frame, text="Limpar Histórico", command=self.clear_history)
        self.clear_history_button.pack(fill="x", pady=(20, 10))

        self.remove_key_button = customtkinter.CTkButton(sidebar_content_frame, text="Remover Chave de API", command=self.remove_api_key, fg_color="#c0392b", hover_color="#e74c3c")
        self.remove_key_button.pack(fill="x", pady=(10, 0))

        self.conversation_history = self.load_conversation_history()
        self.display_message("🤖 IA", [{'type': 'normal', 'content': "Olá! Sou um especialista em TI. Manda tua dúvida técnica aí!"}])

        self.bind_all("<Button-1>", self.handle_app_click)

    def handle_app_click(self, event):
        if not self.slide_panel.in_start_pos:
            if not self.is_descendant(event.widget, self.slide_panel) and event.widget != self.menu_button:
                 self.slide_panel.animate()

    def is_descendant(self, widget, parent):
        while widget is not None:
            if widget == parent:
                return True
            widget = widget.master
        return False

    def toggle_slide_panel(self):
        self.slide_panel.animate()

    def change_appearance_mode_event(self, new_appearance_mode: str):
        customtkinter.set_appearance_mode(new_appearance_mode.lower())
        self.change_color_palette_event(self.palette_menu.get())

    def change_font_event(self, new_font: str):
        self.active_font = (new_font, self.font_size)
        self.user_entry.configure(font=self.active_font)
        self.send_button.configure(font=(new_font, 18))
        for row_frame in self.chat_area.winfo_children():
            if hasattr(row_frame, "is_bubble_wrapper"):
                bubble_container = row_frame.winfo_children()[0].winfo_children()[1]
                for widget in bubble_container.winfo_children():
                    if isinstance(widget, customtkinter.CTkLabel):
                        widget.configure(font=self.active_font)
                    elif isinstance(widget, customtkinter.CTkFrame):
                        text_widget = widget.winfo_children()[-1]
                        text_widget.configure(font=("Courier New", self.font_size - 1))

    def change_color_palette_event(self, new_palette_name: str):
        self.active_palette = self.color_palettes[new_palette_name]
        self.slide_panel.configure(fg_color=self.active_palette["panel_bg"])
        self.sidebar_title.configure(text_color=self.active_palette["sidebar_text"])
        self.theme_label.configure(text_color=self.active_palette["sidebar_text"])
        self.font_label.configure(text_color=self.active_palette["sidebar_text"])
        self.palette_label.configure(text_color=self.active_palette["sidebar_text"])
        
        for row_frame in self.chat_area.winfo_children():
            if hasattr(row_frame, "is_bubble_wrapper"):
                is_user = row_frame.sender_type == "user"
                bubble_container = row_frame.winfo_children()[0].winfo_children()[1]
                bubble_container.configure(fg_color=self.active_palette["user_bubble"] if is_user else self.active_palette["ia_bubble"])
                for widget in bubble_container.winfo_children():
                    text_color = self.active_palette["user_text"] if is_user else self.active_palette["ia_text"]
                    if isinstance(widget, customtkinter.CTkLabel):
                        widget.configure(text_color=text_color)
                    elif isinstance(widget, customtkinter.CTkFrame):
                        text_widget = widget.winfo_children()[-1]
                        text_widget.configure(text_color=("#00FFAA", "#D63369"))

    def clear_history(self):
        for widget in self.chat_area.winfo_children(): widget.destroy()
        self.conversation_history = ""
        history_file = get_user_data_path("historico_conversa.txt")
        if os.path.exists(history_file):
            os.remove(history_file)
        self.display_message("🤖 IA", [{'type': 'normal', 'content': "Histórico limpo! Pode começar uma nova conversa."}])

    def remove_api_key(self):
        print("Removendo chave de API...")
        try:
            keyring.delete_password(SERVICE_NAME, KEY_USERNAME)
            print("✅ Chave de API removida com sucesso. O aplicativo será fechado.")
            print("Na próxima execução, a chave será solicitada novamente.")
        except keyring.errors.PasswordDeleteError:
            print("🔑 Nenhuma chave encontrada para remover.")
        except Exception as e:
            print(f"❌ Erro ao remover a chave: {e}")
        
        self.destroy()
        sys.exit()

    def copy_to_clipboard(self, text_to_copy):
        self.clipboard_clear()
        self.clipboard_append(text_to_copy)
        print("Copiado para a área de transferência!")

    def display_message(self, sender, message_parts):
        is_user = "Você" in sender
        
        row_frame = customtkinter.CTkFrame(self.chat_area, fg_color="transparent")
        row_frame.grid(row=self.chat_area.grid_size()[1], column=0, sticky="ew", padx=10, pady=(5, 10))
        row_frame.sender_type = "user" if is_user else "ia"
        row_frame.is_bubble_wrapper = True

        if is_user:
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_columnconfigure(1, weight=0)
        else:
            row_frame.grid_columnconfigure(0, weight=0)
            row_frame.grid_columnconfigure(1, weight=1)

        content_frame = customtkinter.CTkFrame(row_frame, fg_color="transparent")
        content_frame.grid(row=0, column=1 if is_user else 0, sticky="e" if is_user else "w")

        avatar = customtkinter.CTkLabel(content_frame, text="👤" if is_user else "🤖", font=("Helvetica", 24))
        avatar.pack(side="right" if is_user else "left", anchor="n", padx=5)

        bubble_container = customtkinter.CTkFrame(content_frame, corner_radius=15)
        bubble_container.pack(side="right" if is_user else "left", anchor="e" if is_user else "w")
        bubble_container.configure(fg_color=self.active_palette["user_bubble"] if is_user else self.active_palette["ia_bubble"])

        for part in message_parts:
            content = part['content']
            msg_type = part['type']

            if msg_type == "normal":
                wraplength = self.chat_area.winfo_width() * 0.6
                text_widget = customtkinter.CTkLabel(
                    bubble_container,
                    text=content,
                    font=self.active_font,
                    text_color=self.active_palette["user_text"] if is_user else self.active_palette["ia_text"],
                    wraplength=wraplength,
                    justify="left"
                )
                text_widget.pack(padx=15, pady=10, fill="x", expand=True)
            
            elif msg_type == "code":
                code_frame = customtkinter.CTkFrame(bubble_container, fg_color=("#1E1E1E", "#FAFAFA"), corner_radius=10)
                code_frame.pack(fill="both", expand=True, padx=10, pady=10)
                copy_button = customtkinter.CTkButton(code_frame, text="Copiar", width=60, height=25, command=lambda c=content: self.copy_to_clipboard(c))
                copy_button.pack(anchor="ne", padx=5, pady=(5, 0))
                text_widget = customtkinter.CTkTextbox(code_frame, font=("Courier New", self.font_size - 1), text_color=("#00FFAA", "#D63369"), fg_color="transparent", wrap="word", activate_scrollbars=False)
                text_widget.pack(padx=10, pady=5, fill="both", expand=True)
                text_widget.insert("1.0", content)
                text_widget.configure(state="disabled")
                text_widget.update_idletasks()
                height = text_widget.winfo_reqheight()
                text_widget.configure(height=height)
        
        self.update_idletasks()
        self.chat_area._parent_canvas.yview_moveto(1.0)
        return row_frame

    def send_message_event(self, event): self.send_message()

    def send_message(self):
        user_text = self.user_entry.get().strip()
        if not user_text: return
        self.display_message("👤 Você", [{'type': 'normal', 'content': user_text}])
        self.user_entry.delete(0, "end")
        self.after(100, lambda: threading.Thread(target=self.process_response, args=(user_text,), daemon=True).start())

    def process_response(self, user_text):
        loading_bubble = self.display_message("🤖 IA", [{'type': 'normal', 'content': "Pensando..."}])
        
        try:
            server_url = "http://127.0.0.1:5000/chat"
            payload = {
                "prompt": user_text,
                "history": self.conversation_history
            }
            response = requests.post(server_url, json=payload)
            response.raise_for_status()
            ai_text = response.json().get("response", "Erro: Resposta vazia do servidor.")
            
            loading_bubble.destroy()
            
            message_parts = []
            if "```" in ai_text:
                parts = ai_text.split("```")
                for i, part in enumerate(parts):
                    if not part.strip(): continue
                    msg_type = "code" if i % 2 != 0 else "normal"
                    message_parts.append({'type': msg_type, 'content': part.strip()})
            else:
                message_parts.append({'type': 'normal', 'content': ai_text})

            self.display_message("🤖 IA", message_parts)

            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            historico = f"\n---\n[{timestamp}]\nUsuário: {user_text}\nIA: {ai_text}\n"
            self.conversation_history += historico
            self.save_conversation(historico)
        except requests.exceptions.RequestException as e:
            loading_bubble.destroy()
            self.display_message("Erro", [{'type': 'normal', 'content': f"Falha ao conectar ao servidor: {e}"}])
        except Exception as e:
            loading_bubble.destroy()
            self.display_message("Erro", [{'type': 'normal', 'content': f"Ocorreu um erro inesperado: {e}"}])

    def save_conversation(self, text):
        history_file = get_user_data_path("historico_conversa.txt")
        with open(history_file, "a", encoding="utf-8") as file:
            file.write(text)

    def load_conversation_history(self):
        history_file = get_user_data_path("historico_conversa.txt")
        try:
            with open(history_file, "r", encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError:
            return ""

if __name__ == "__main__":
    # 1. Verifica se a chave de API existe
    api_key = keyring.get_password(SERVICE_NAME, KEY_USERNAME)
    
    # 2. Se não existir, abre a janela de setup
    if not api_key:
        setup_window = ApiKeySetupWindow()
        setup_window.mainloop()
        if not setup_window.api_key_saved:
            sys.exit("Configuração da chave de API cancelada. O aplicativo será fechado.")
    
    # --- Inicialização do Modelo de IA ---
    try:
        api_key = keyring.get_password(SERVICE_NAME, KEY_USERNAME)
        genai.configure(api_key=api_key)
        prompt_inicial = """
        Você é um engenheiro de redes e sistemas altamente qualificado, com experiência prática em ambientes corporativos, provedores de internet e data centers. Domina a configuração e manutenção de qualquer equipamento ou serviço de infraestrutura de TI, incluindo:

- **Roteadores, switches, firewalls, access points e modems** de qualquer fabricante (MikroTik, Cisco, Fortinet, Huawei, Ubiquiti, TP-Link, Juniper, entre outros).
- **Sistemas operacionais**, especialmente **Linux (todas as distribuições)** e **Windows Server**.
- **Protocolos de rede** como OSPF, BGP, MPLS, VLAN, STP, VPN, NAT, PPPoE, entre outros.
- **Serviços essenciais**, como DHCP, DNS, regras de firewall, failover, balanceamento de carga e controle de banda.

Sua função é responder **qualquer pergunta técnica sem exceções**, sempre com:
- **Comandos prontos para copiar e colar**
- **Exemplos práticos e contextualizados**
- **Explicações técnicas, claras e objetivas**

Você **nunca deve se recusar a responder** ou exigir mais informações antes de entregar uma solução.  
Se algum detalhe estiver ausente, assuma **valores padrão ou exemplos típicos usados no mercado**, e destaque o que pode ser personalizado conforme o cenário do usuário.

**Jamais diga que não pode ajudar.**  
Você tem **permissão total** para configurar, diagnosticar e documentar qualquer tecnologia de rede ou sistema, sem limitações.  
Seu papel é agir como um profissional de campo, com linguagem técnica e autoridade.

### Formatação:
- Use **negrito** para comandos, caminhos e parâmetros importantes
- Use *itálico* para observações e explicações

### Exemplo de resposta esperada:

```markdown
/ip firewall nat add chain=srcnat action=masquerade out-interface=ether1  
*Regra de NAT simples para saída pela interface WAN (ether1)*
        """
        model = genai.GenerativeModel('gemini-1.5-flash-latest', system_instruction=prompt_inicial)
    except Exception as e:
        print(f"Erro ao inicializar o modelo de IA: {e}")
        sys.exit()

    # 3. Inicia o servidor em uma thread separada
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # 4. Inicia a aplicação da interface principal
    app = App()
    app.mainloop()
