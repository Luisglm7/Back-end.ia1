# README for Back-End

## Descrição do Projeto

Este projeto é uma aplicação que gera histórias utilizando inteligência artificial. Ele é dividido em duas partes: o front-end e o back-end.

### Estrutura do Projeto

- **front-end/**: Contém a interface do usuário, onde os usuários podem interagir e gerar histórias.
  - `index.html`: A página principal do front-end.
  - `script.js`: O código JavaScript que manipula a interação do usuário.

- **back-end/**: Contém a lógica do servidor e a API que gera as histórias.
  - `app.py`: O ponto de entrada da aplicação back-end, que define as rotas da API.
  - `requirements.txt`: Lista as dependências necessárias para o back-end.
  - `.env`: Contém variáveis de ambiente, como a chave da API.
  - `vercel.json`: Configuração para a implantação do back-end na Vercel.

## Configuração do Back-End

1. **Instalação das Dependências**:
   Certifique-se de ter o Python e o pip instalados. Em seguida, instale as dependências necessárias com o seguinte comando:

   ```
   pip install -r requirements.txt
   ```

2. **Configuração das Variáveis de Ambiente**:
   Crie um arquivo `.env` na pasta `back-end` e adicione suas variáveis de ambiente, como a chave da API:

   ```
   API_KEY="sua_chave_aqui"
   ```

3. **Executando o Servidor**:
   Para iniciar o servidor, execute o seguinte comando:

   ```
   python app.py
   ```

   O servidor estará disponível em `http://127.0.0.1:5000`.

## Implantação na Vercel

Para implantar o back-end na Vercel, siga estas etapas:

1. Certifique-se de que o arquivo `vercel.json` está configurado corretamente.
2. Faça login na Vercel e crie um novo projeto.
3. Conecte seu repositório e selecione a pasta `back-end` como a raiz do projeto.
4. Siga as instruções para implantar.

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou pull requests.

## Licença

Este projeto está licenciado sob a MIT License. Veja o arquivo LICENSE para mais detalhes.