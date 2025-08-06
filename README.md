AI Tech Expert 🤖
Bem-vindo ao AI Tech Expert, um assistente de desktop inteligente desenvolvido em Python, que utiliza a API do Gemini para fornecer respostas especializadas e contextuais.

<!-- Sugestão: Coloque um screenshot da sua app com o nome 'screenshot.png' na pasta 'assets' -->

🚀 Sobre o Projeto
O AI Tech Expert não é apenas um chatbot. É uma ferramenta poderosa que combina a capacidade do modelo Gemini 1.5 Flash com uma base de conhecimento local, permitindo que a IA responda a perguntas com base nos seus próprios documentos (PDFs e TXTs). Além disso, a IA pode assumir diferentes perfis de especialista para fornecer respostas adaptadas às suas necessidades.

✨ Funcionalidades
Perfis de IA Dinâmicos: Alterne entre especialistas como "Engenheiro de Redes", "SysAdmin Linux" ou "Professor Didático" para obter respostas no tom e com o detalhe técnico que precisa.

Base de Conhecimento Local: Adicione os seus próprios documentos (PDFs, manuais, artigos) para que a IA os utilize como fonte primária de informação.

Interface Moderna: Desenvolvido com CustomTkinter para um visual limpo, com suporte para temas claro e escuro.

Gestão de Conversas: O seu histórico de conversas é guardado automaticamente. Continue conversas antigas ou apague as que já não são necessárias.

Robusto e Resiliente: Inclui lógica para gerir os limites de tokens da API e para tentar novamente em caso de erros de quota, garantindo uma experiência de uso fluida.

Segurança: A sua chave de API é guardada de forma segura no chaveiro do sistema operativo.

🛠️ Tecnologias Utilizadas
Linguagem: Python 3

Interface Gráfica (GUI): CustomTkinter

Servidor Local: Flask

Inteligência Artificial: Google Gemini API (gemini-1.5-flash-latest)

Base de Dados: SQLite

Leitura de PDFs: PyPDF2

Armazenamento Seguro de Chaves: Keyring

⚙️ Como Executar
Pré-requisitos
Python 3.10 ou superior

Uma chave de API do Google Gemini

Passos para Instalação
Clone o repositório:

git clone [https://github.com/EmersonRicardo0/AI-Tech-Expert.git](https://github.com/EmersonRicardo0/AI-Tech-Expert.git)
cd AI-Tech-Expert

Crie um ambiente virtual e instale as dependências:

# Crie o ambiente virtual
python3 -m venv venv

# Ative o ambiente (macOS/Linux)
source venv/bin/activate
# Ou no Windows (cmd.exe)
# venv\Scripts\activate.bat

# Instale as bibliotecas necessárias
pip install -r requirements.txt 

(Nota: Será necessário criar um ficheiro requirements.txt com as bibliotecas do projeto)

Execute o Servidor:
Abra um terminal e inicie o servidor Flask. Deixe este terminal a correr em segundo plano.

python server.py

Execute a Aplicação Principal:
Abra outro terminal (com o ambiente virtual ativado) e inicie a interface gráfica.

python main.py

Na primeira vez que executar, a aplicação irá pedir a sua chave de API do Gemini, que será guardada de forma segura.

📂 Estrutura do Projeto
/AI-Tech-Expert
|
├── assets/                 # Ícones e outros recursos visuais
│   ├── ai_icon.png
│   └── user_icon.png
├── app_gui.py              # Código da interface gráfica (front-end)
├── server.py               # Servidor Flask (back-end) que processa os pedidos
├── gemini_integration.py   # Módulo central para comunicar com a API do Gemini
├── database.py             # Gestão do banco de dados SQLite (base de conhecimento)
├── config.py               # Configurações e prompts dos perfis da IA
├── main.py                 # Ponto de entrada para iniciar a aplicação
└── requirements.txt        # Lista de dependências Python
