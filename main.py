# /main.py

import sys
import threading
import customtkinter
import keyring
import logging

# Importa os componentes dos outros módulos
from app_gui import App, ApiKeySetupWindow # Supondo que ApiKeySetupWindow está em app_gui.py
from server import run_server
from database import init_db, setup_logging
from config import SERVICE_NAME, KEY_USERNAME

def main():
    """Função principal para iniciar a aplicação."""
    # 1. Configurar logging
    setup_logging()

    # 2. Inicializar banco de dados
    init_db()

    # 3. Verificar chave de API
    api_key = keyring.get_password(SERVICE_NAME, KEY_USERNAME)
    if not api_key:
        logging.info("Chave de API não encontrada. A iniciar janela de configuração.")
        setup_window = ApiKeySetupWindow() # Esta classe precisa estar definida em app_gui.py
        setup_window.mainloop()
        # Após fechar a janela de setup, verifica novamente
        if not keyring.get_password(SERVICE_NAME, KEY_USERNAME):
            logging.error("Nenhuma chave de API foi fornecida. A sair.")
            sys.exit()

    # 4. Iniciar servidor Flask em background
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    logging.info("Servidor Flask iniciado em background.")
    
    # Adiciona um pequeno delay para garantir que o servidor suba antes da primeira requisição
    threading.Timer(2.0, lambda: logging.info("Servidor pronto.")).start()


    # 5. Iniciar a aplicação gráfica
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        logging.critical(f"Erro fatal na aplicação gráfica: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
