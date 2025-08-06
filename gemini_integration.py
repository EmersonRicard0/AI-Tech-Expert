# /gemini_integration.py

import google.generativeai as genai
import logging
import time
import keyring
import json
import re
from config import SERVICE_NAME, KEY_USERNAME

# --- Configuração e Geração de Resposta ---

def configure_gemini_api():
    """Busca a chave de API e configura o SDK do Gemini."""
    try:
        api_key = keyring.get_password(SERVICE_NAME, KEY_USERNAME)
        if not api_key:
            logging.error("Chave de API do Gemini não encontrada no keyring.")
            return False
        genai.configure(api_key=api_key)
        return True
    except Exception as e:
        logging.error(f"Erro ao configurar a API do Gemini: {e}")
        return False

def generate_response_from_gemini(user_prompt, knowledge_context, history, user_name, profile_instruction):
    """
    Gera uma resposta usando a API do Gemini, com lógica de retry automático
    para lidar com limites de quota (erro 429).
    """
    if not configure_gemini_api():
        return {"error": "Falha ao configurar a API do Gemini. Verifique a sua chave."}

    # Constrói o prompt completo para a IA
    full_prompt = f"""
{profile_instruction.format(user_name=user_name)}

Histórico da Conversa Atual:
{history}

Base de Conhecimento Relevante:
---
{knowledge_context if knowledge_context else "Nenhum contexto da base de conhecimento foi encontrado para esta pergunta."}
---

Pergunta do Utilizador ({user_name}):
"{user_prompt}"
"""

    model = genai.GenerativeModel(
        'gemini-1.5-flash-latest',
        safety_settings={
            'HARM_CATEGORY_DANGEROUS': 'BLOCK_NONE',
            'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
            'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE'
        }
    )
    
    # --- LÓGICA DE RETRY COM EXPONENTIAL BACKOFF ---
    max_retries = 4
    base_delay_seconds = 5

    for attempt in range(max_retries):
        try:
            response = model.generate_content(full_prompt)
            
            # Limpa e tenta converter a resposta para JSON
            try:
                clean_text = re.sub(r'```json\s*|\s*```', '', response.text.strip(), flags=re.DOTALL)
                json_response = json.loads(clean_text)
                return json_response
            except json.JSONDecodeError:
                logging.warning("A resposta da IA não era um JSON válido. A usar fallback.")
                return {
                    "solucao": response.text.strip(),
                    "codigo": "", "verificacao": "", "fonte_contexto": ""
                }

        except Exception as e:
            if "429" in str(e) and "quota" in str(e).lower():
                if attempt < max_retries - 1:
                    delay = base_delay_seconds * (2 ** attempt)
                    logging.warning(f"Quota da API excedida. A tentar novamente em {delay}s... (Tentativa {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                else:
                    logging.error(f"Quota da API excedida após {max_retries} tentativas.")
                    return {"error": "Limite de requisições à API atingido. Tente novamente num minuto."}
            else:
                logging.error(f"Erro inesperado na API Gemini: {e}")
                return {"error": f"Erro na API Gemini: {e}"}
    
    return {"error": "Não foi possível obter uma resposta da API após várias tentativas."}
