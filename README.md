# 🤖 AI Tech Expert – Seu Assistente de IA Desktop para macOS

![GitHub release (latest by date)](https://img.shields.io/github/v/release/EmersonRicardo0/AI-Tech-Expert?style=flat-square)
![GitHub language count](https://img.shields.io/github/languages/count/EmersonRicardo0/AI-Tech-Expert?style=flat-square)
![License](https://img.shields.io/github/license/EmersonRicardo0/AI-Tech-Expert?style=flat-square)

---

> **AI Tech Expert** é um assistente inteligente desktop com interface moderna, IA poderosa e base de conhecimento personalizada — pensado para profissionais de TI que querem agilizar o dia a dia com inteligência artificial de ponta.

---

## 🎥 Demonstração Rápida

![Demonstração do AI Tech Expert](assets/demo.gif)

---

## 🚀 Sobre o Projeto

Este app vai muito além do chat básico: ele permite consultas inteligentes baseadas em documentos locais (PDFs, TXTs) e perfis dinâmicos de IA que se adaptam ao seu estilo técnico e tom preferido.

- **Perfis de Especialistas:** Escolha entre Engenheiro de Redes, SysAdmin Linux ou Professor Didático.
- **Base Personalizada:** Adicione seus próprios manuais e artigos para enriquecer as respostas.
- **Interface Moderna:** Visual clean com tema claro/escuro via CustomTkinter.
- **Segurança:** API key armazenada com segurança via Keyring.
- **Robustez:** Controle de tokens e tentativas automáticas para evitar travamentos.

---

## 📁 Estrutura do Projeto

```plaintext
AI-Tech-Expert/
├── assets/
│   ├── ai_icon.png
│   ├── user_icon.png
│   └── demo.gif
├── main.py
├── server.py
├── gemini_integration.py
├── database.py
├── config.py
├── requirements.txt
└── README.md
⚙️ Como Rodar Localmente
1. Clone o repositório
bash
Copiar
Editar
git clone https://github.com/EmersonRicardo0/AI-Tech-Expert.git
cd AI-Tech-Expert
2. Crie e ative o ambiente virtual
bash
Copiar
Editar
python3 -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate.bat # Windows (cmd)
3. Instale as dependências
bash
Copiar
Editar
pip install -r requirements.txt
4. Inicie o servidor Flask (em outro terminal)
bash
Copiar
Editar
python server.py
5. Rode a interface gráfica
bash
Copiar
Editar
python main.py
Na primeira execução, o app pedirá sua chave da API Gemini, que será armazenada com segurança via Keyring.

📦 Gerando o .app e .dmg no macOS
1. Gere o app .app usando py2app (se ainda não gerou)
bash
Copiar
Editar
python setup.py py2app
2. Crie a pasta release se não existir
bash
Copiar
Editar
mkdir -p release
3. Crie o arquivo .dmg
bash
Copiar
Editar
create-dmg 'dist/AI Tech Expert.app' \
  --overwrite \
  --dmg-title='AI Tech Expert' \
  --app-drop-link=~/Desktop \
  ./release
4. Teste o .dmg
Abra o .dmg na pasta release

Arraste o app para Aplicativos

Rode o AI Tech Expert normalmente

⚠️ Erros Comuns e Como Resolver
Erro	Possível causa	Solução
ENOENT: no such file or directory	Arquivo ou pasta não encontrados	Verifique caminhos e nomes corretos
Could not find 'dist/AI Tech Expert.app'	App não gerado ou caminho errado	Execute python setup.py py2app

🤝 Contribuições
Contribuições são muito bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

📜 Licença
MIT License © Emerson Silva Ricardo

Feito com ☕ e muito amor por Emerson Silva Ricardo.

🔗 Links Úteis

Google Gemini API

CustomTkinter

create-dmg (npm)



## ✉️ Contato

Desenvolvido com 💻 por **Emerson Silva Ricardo**
📧 [silvaemerson797@gmail.com](mailto:emerson.ricardo@gmail.com)

---

```

Se quiser, posso te ajudar a gerar esse `README.md` direto em um arquivo. Só dizer "gera o arquivo aí" que eu já te entrego prontinho pra usar!

Curtiu o visual e organização? Quer adicionar selo de build, GIF ou badge? Posso turbinar isso ainda mais! 💪
```
