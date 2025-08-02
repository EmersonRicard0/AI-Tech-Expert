# server.py
# Este é o seu backend. Ele protege a chave de API.
# Para rodar, instale as bibliotecas: pip install Flask google-generativeai

from flask import Flask, request, jsonify
import google.generativeai as genai
import os

app = Flask(__name__)

# --- Configuração Segura da API do Gemini ---
try:
    # Lê a chave da API a partir de uma variável de ambiente chamada 'GEMINI_API_KEY'
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("A variável de ambiente GEMINI_API_KEY não foi definida.")
    genai.configure(api_key=api_key)
except Exception as e:
    print(f"Erro fatal ao configurar a API no servidor: {e}")
    exit()

# --- Prompt inicial especializado ---
prompt_inicial = """
Você é um especialista em TI, focado em configurações de equipamentos de rede (roteadores, switches, firewalls), sistemas operacionais (Linux) e segurança.

Sua principal função é fornecer **configurações, comandos e explicações técnicas claras e objetivas** para as perguntas do usuário.
Use formatação markdown como negrito (**texto**) e itálico (*texto*) para enfatizar pontos importantes.

Você deve:
- Conhecer configurações de marcas como Cisco, Mikrotik, Juniper, etc.
- Fornecer comandos de sistemas operacionais como Linux, Windows Server, etc.
- Explicar conceitos técnicos de forma clara.
- Gerar scripts em Python que usem bibliotecas como `paramiko`, `netmiko`, `nmap`, `os`, `tkinter`, `customtkinter`, entre outras.

Se a pergunta **não for relacionada a TI**, educadamente recuse a responder.
"""

model = genai.GenerativeModel(
    'gemini-1.5-flash-latest',
    system_instruction=prompt_inicial
)

@app.route('/chat', methods=['POST'])
def chat():
    """
    Este é o ponto de entrada (endpoint) que o seu app cliente vai chamar.
    """
    try:
        data = request.get_json()
        if not data or 'prompt' not in data:
            return jsonify({"error": "Prompt não encontrado na requisição"}), 400

        user_prompt = data.get('prompt', '')
        conversation_history = data.get('history', '')
        
        full_prompt = conversation_history + f"\nUsuário: {user_prompt}"
        
        # O servidor faz a chamada para a IA do Google
        response = model.generate_content(full_prompt)
        ai_text = response.text.strip()

        # O servidor devolve a resposta da IA para o seu app cliente
        return jsonify({"response": ai_text})

    except Exception as e:
        print(f"Erro no servidor ao processar a requisição: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

if __name__ == '__main__':
    # Roda o servidor na sua máquina local na porta 5000
    app.run(host='0.0.0.0', port=5000)
