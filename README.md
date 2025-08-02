# AI Tech Expert

Este é um assistente de IA para macOS, construído com Python.

## Pré-requisitos

Para rodar este projeto, você precisará ter o Python 3 instalado. Recomenda-se o uso de um ambiente virtual para gerenciar as dependências do projeto.

## Configuração do Ambiente

Siga os passos abaixo para configurar o ambiente de desenvolvimento:

1.  **Crie o ambiente virtual:**
    Abra o terminal e navegue até a pasta do projeto. Em seguida, execute o comando:
    ```bash
    python3 -m venv venv
    ```

2.  **Ative o ambiente virtual:**
    No macOS, o comando para ativar o ambiente virtual é:
    ```bash
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    Com o ambiente virtual ativado, instale as bibliotecas necessárias para o projeto. No seu caso, a principal dependência é o `pyinstaller`.
    ```bash
    pip install pyinstaller
    ```

## Geração do Aplicativo e DMG

Este projeto usa o `pyinstaller` para criar um aplicativo executável (`.app`) e, em seguida, gerar um arquivo de instalação para macOS (`.dmg`).

1.  **Gere o executável (`.app`):**
    Certifique-se de que o ambiente virtual está ativado e execute o comando:
    ```bash
    pyinstaller --windowed --name "AI Tech Expert" --icon="tec.icns" app.py
    ```
    Isso criará uma pasta `dist` com o aplicativo "AI Tech Expert.app" dentro.

2.  **Gere o arquivo DMG (Opcional):**
    Para criar um instalador em formato DMG, você pode usar uma ferramenta como o `create-dmg` (se estiver no macOS).

    Primeiro, instale a ferramenta se ainda não a tiver:
    ```bash
    brew install create-dmg
    ```

    Em seguida, execute o comando (adaptado para o seu projeto):
    ```bash
    create-dmg \
      'AI Tech Expert.dmg' \
      'dist/AI Tech Expert.app' \
      --background-image 'caminho/para/imagem_de_fundo.png' \
      --window-pos 200 120 \
      --window-size 800 500 \
      --icon-size 100 \
      --icon 'AI Tech Expert.app' 200 190 \
      --app-drop-link 600 190
    ```
    * **Observação:** Você precisará ajustar os caminhos e as posições para o seu projeto. Este comando cria um DMG com um plano de fundo e um link para a pasta de aplicativos.



#Feito por Emerson Silva Ricardo
#email:silvaemerson797@gmail.com