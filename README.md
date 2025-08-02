# AI Tech Expert

Este é um assistente de IA construído com Python, que utiliza a API do Gemini. Ele pode ser executado em macOS e Windows.

## Pré-requisitos

Para rodar este projeto, você precisará ter:
- **Python 3** instalado.
- Uma **chave de API do Google Gemini**. Você pode obter uma chave em [Google AI Studio](https://ai.google.dev/docs/get_started_and_auth).

É altamente recomendado o uso de um ambiente virtual para gerenciar as dependências do projeto.

## Configuração do Ambiente

Siga os passos abaixo para configurar o ambiente de desenvolvimento:

1.  **Crie o ambiente virtual:**
    Abra o terminal ou o prompt de comando e navegue até a pasta do projeto. Em seguida, execute o comando:
    ```bash
    python -m venv venv
    ```
    *Obs: Em alguns sistemas, o comando pode ser `python3`.*

2.  **Ative o ambiente virtual:**
    -   **No macOS:**
        ```bash
        source venv/bin/activate
        ```
    -   **No Windows:**
        ```bash
        venv\Scripts\activate
        ```

3.  **Instale as dependências:**
    Com o ambiente virtual ativado, instale as bibliotecas necessárias para o projeto. A principal dependência é o `pyinstaller`.
    ```bash
    pip install pyinstaller
    ```

### Configuração da API do Gemini

Para que o aplicativo funcione, é necessário configurar a sua chave de API do Gemini.

1.  **Obtenha sua chave:**
    Acesse o [Google AI Studio](https://ai.google.dev/docs/get_started_and_auth), siga as instruções para criar uma chave e copie-a.

2.  **Defina a chave de API:**
    Utilize o script `set_key.py` para salvar sua chave de API de forma segura no sistema. Execute o seguinte comando, substituindo `SUA_CHAVE_AQUI` pela sua chave real:
    ```bash
    python set_key.py SUA_CHAVE_AQUI
    ```
    Este script irá salvar sua chave de API como uma variável de ambiente, garantindo que ela não seja exposta no código.

---

## Geração do Aplicativo

Este projeto usa o `pyinstaller` para criar um aplicativo executável.

### Para macOS

1.  **Gere o executável (`.app`):**
    Certifique-se de que o ambiente virtual está ativado e execute o comando:
    ```bash
    pyinstaller --windowed --name "AI Tech Expert" --icon="tec.icns" app.py
    ```
    Isso criará uma pasta `dist` com o aplicativo "AI Tech Expert.app" dentro.

2.  **Gere o arquivo DMG (Opcional):**
    Para criar um instalador em formato DMG, você pode usar uma ferramenta como o `create-dmg` (se estiver no macOS). Se não o tiver, instale-o com `brew install create-dmg` e depois execute um comando similar a este:
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
    * **Observação:** Você precisará ajustar os caminhos e as posições para o seu projeto.

### Para Windows

1.  **Gere o executável (`.exe`):**
    Certifique-se de que o ambiente virtual está ativado e execute o comando:
    ```bash
    pyinstaller --onefile --windowed --name "AI Tech Expert" app.py
    ```
    * **`--onefile`**: Esta opção cria um único arquivo executável (`.exe`), o que facilita a distribuição.
    * **`--windowed`**: Esta opção garante que o aplicativo não abra uma janela de console.

    O executável "AI Tech Expert.exe" será criado dentro da pasta `dist`.

---

## Licença

[Adicione aqui o tipo de licença do seu projeto, como MIT ou GNU GPL.]

#Feito por Emerson Silva Ricardo
#email:silvaemerson797@gmail.com