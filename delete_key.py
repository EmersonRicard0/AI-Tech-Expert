# delete_key.py
# Execute este script para remover a chave de API salva
# no cofre de senhas do seu sistema.

import keyring

# As variáveis devem ser as mesmas usadas no app.py
SERVICE_NAME = "AI_Tech_Expert"
KEY_USERNAME = "gemini_api_key"

try:
    # Tenta apagar a senha
    keyring.delete_password(SERVICE_NAME, KEY_USERNAME)
    print(f"✅ Chave de API para o serviço '{SERVICE_NAME}' foi removida com sucesso!")
    print("Na próxima vez que você executar o app.py, ele pedirá a chave novamente.")
except keyring.errors.PasswordDeleteError:
    print(f"🔑 Nenhuma chave encontrada para o serviço '{SERVICE_NAME}'. Nenhuma ação foi necessária.")
except Exception as e:
    print(f"❌ Ocorreu um erro ao tentar remover a chave: {e}")

