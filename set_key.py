# set_key.py
# Execute este script UMA ÚNICA VEZ para salvar sua chave de API
# de forma segura no cofre de senhas do seu sistema operacional.
#
# Primeiro, instale a biblioteca: pip install keyring

import keyring
import getpass

# Nome do serviço (pode ser o nome do seu app)
SERVICE_NAME = "AI_Tech_Expert"
# Nome de usuário (para identificar a chave)
USERNAME = "gemini_api_key"

print("--- Configuração Segura da Chave de API ---")
print(f"A chave será salva no serviço '{SERVICE_NAME}' com o nome de usuário '{USERNAME}'.")

# Pede a chave de forma segura, sem mostrá-la na tela
api_key = getpass.getpass("Por favor, cole sua chave de API do Gemini e pressione Enter: ")

if api_key:
    try:
        # Salva a chave no cofre de senhas do sistema
        keyring.set_password(SERVICE_NAME, USERNAME, api_key)
        print("\n✅ Chave de API salva com sucesso no cofre de senhas do seu sistema!")
        print("Você já pode apagar este script (set_key.py) e o arquivo .env, se desejar.")
    except Exception as e:
        print(f"\n❌ Ocorreu um erro ao salvar a chave: {e}")
else:
    print("\nNenhuma chave inserida. Operação cancelada.")

