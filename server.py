# /server.py

from flask import Flask, request, jsonify
import logging
import time
import sys
import google.generativeai as genai

# Importa as funções necessárias dos seus outros ficheiros
from database import init_db, log_metric, search_knowledge_base
from config import AI_PROFILES
from gemini_integration import generate_response_from_gemini, configure_gemini_api

# Renomeia a variável da app para evitar conflitos
server_app = Flask(__name__)

# --- FUNÇÃO DE GESTÃO DE TOKENS (REVISADA E OTIMIZADA) ---
def manage_token_limit(payload):
    """
    Verifica e ajusta o payload para não exceder o limite de tokens da API,
    usando um método de truncamento mais eficiente.
    """
    MAX_TOKENS = 1000000  # Limite seguro, um pouco abaixo do máximo real de 1,048,575

    # Configura a API para poder usar o contador de tokens
    if not configure_gemini_api():
        return payload

    def build_prompt(p):
        """Função auxiliar para construir o prompt completo para contagem."""
        return f"""
        {p['profile_instruction'].format(user_name=p['user_name'])}
        Histórico da Conversa Atual:
        {p['history']}
        Base de Conhecimento Relevante:
        ---
        {p['knowledge_context']}
        ---
        Pergunta do Utilizador ({p['user_name']}):
        "{p['prompt']}"
        """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Faz uma contagem inicial
        full_prompt_for_counting = build_prompt(payload)
        total_tokens = model.count_tokens(full_prompt_for_counting).total_tokens
        logging.info(f"Contagem de tokens inicial: {total_tokens}")

        if total_tokens > MAX_TOKENS:
            logging.warning(f"Contagem de tokens ({total_tokens}) excede o limite de {MAX_TOKENS}. A iniciar truncamento inteligente...")

            # Calcula o excesso e a quantidade de caracteres a remover (com uma margem)
            overflow_tokens = total_tokens - MAX_TOKENS
            # Multiplica por 4 para estimar caracteres e adiciona 10% de margem de segurança
            chars_to_remove = int(overflow_tokens * 4 * 1.1) 

            # Prioriza remover do contexto, que geralmente é a maior parte
            context_len = len(payload['knowledge_context'])
            if context_len > 0:
                removed_from_context = min(chars_to_remove, context_len)
                payload['knowledge_context'] = payload['knowledge_context'][:-removed_from_context]
                chars_to_remove -= removed_from_context
                logging.info(f"Removidos {removed_from_context} caracteres do contexto.")

            # Se ainda precisar remover, remove do histórico (o mais antigo primeiro)
            history_len = len(payload['history'])
            if chars_to_remove > 0 and history_len > 0:
                removed_from_history = min(chars_to_remove, history_len)
                payload['history'] = payload['history'][removed_from_history:]
                logging.info(f"Removidos {removed_from_history} caracteres do início do histórico.")

            # Recalcula para garantir e logar o resultado final
            final_prompt = build_prompt(payload)
            final_tokens = model.count_tokens(final_prompt).total_tokens
            logging.info(f"Nova contagem de tokens após truncar: {final_tokens}")
            if final_tokens > MAX_TOKENS:
                logging.error("O truncamento não foi suficiente. O prompt inicial pode ser excessivamente grande.")

    except Exception as e:
        logging.error(f"Erro ao contar/gerir tokens: {e}. A enviar o payload sem verificação.")

    return payload


@server_app.route('/chat', methods=['POST'])
def chat():
    """ Endpoint para receber as requisições de chat da interface gráfica. """
    start_time = time.time()
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Requisição inválida"}), 400

        user_prompt = data.get('prompt')
        history = data.get('history', '')
        user_name = data.get('user_name', 'Utilizador')
        profile_name = data.get('profile', list(AI_PROFILES.keys())[0])

        if not user_prompt:
            return jsonify({"error": "Prompt é obrigatório"}), 400
        
        # O servidor agora é responsável por buscar na base de conhecimento
        knowledge_context = search_knowledge_base(user_prompt)

        # Seleciona a instrução do perfil
        profile_instruction = AI_PROFILES.get(profile_name, AI_PROFILES[list(AI_PROFILES.keys())[0]])

        # Cria um payload para verificação de tokens
        payload_to_verify = {
            "prompt": user_prompt,
            "knowledge_context": knowledge_context,
            "history": history,
            "user_name": user_name,
            "profile_instruction": profile_instruction
        }

        # Garante que o payload não exceda o limite de tokens
        managed_payload = manage_token_limit(payload_to_verify)

        # Chama a função centralizada para obter a resposta da IA com o payload ajustado
        response_data = generate_response_from_gemini(
            managed_payload["prompt"],
            managed_payload["knowledge_context"],
            managed_payload["history"],
            managed_payload["user_name"],
            managed_payload["profile_instruction"]
        )

        # Loga a métrica de desempenho
        end_time = time.time()
        response_time = end_time - start_time
        used_kb = bool(knowledge_context)
        log_metric(response_time, used_kb, profile_name)

        return jsonify(response_data)

    except Exception as e:
        logging.error(f"Erro no servidor ao processar a requisição: {e}", exc_info=True)
        return jsonify({"error": f"Erro interno no servidor: {e}"}), 500

def run_server():
    """ Função principal para iniciar o servidor Flask. """
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR) # Oculta os logs padrão do Flask para um terminal mais limpo
    server_app.run(host='127.0.0.1', port=5000, debug=False)
