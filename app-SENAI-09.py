from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from google import genai
import os
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)
CORS(app) # Habilita CORS para todas as rotas

API_KEY = os.getenv("API_KEY")

# Verifica se a API_KEY foi carregada
if not API_KEY:
    print("[WARN] API_KEY não definida. Por favor, configure a variável de ambiente no seu arquivo .env.")
    # Em produção, você pode querer levantar um erro mais severo ou desligar o app.
    # Para desenvolvimento, podemos tentar continuar, mas as chamadas à IA falharão.
    client = None # Define client como None se a chave não estiver disponível
else:
    client = genai.Client(api_key=os.getenv("API_KEY"))
    print("[INFO] Cliente GenAI inicializado com sucesso.")


def gerar_historia(tema, genero="fantasia", extensao="media"):
    """
    Gera uma história usando a API do Gemini com base no tema, gênero e extensão.
    Inclui logs detalhados para depuração e lógica de normalização da resposta da IA.
    """
    if not client:
        print("[ERROR] Cliente GenAI não está inicializado. Verifique a API_KEY.")
        return {
            "erro": "Serviço de geração de história indisponível (chave de API ausente).",
            "detalhes": "Verifique a configuração da API_KEY no backend."
        }

    tamanhos = {
        "curta": "uma história curta de 100-150 palavras",
        "media": "uma história média de 200-300 palavras",
        "longa": "uma história longa de 400-500 palavras"
    }

    # Melhorando o prompt para tentar obter um formato de 'story' como array de strings (parágrafos)
    # E adicionando os campos de gênero e extensão para a IA retornar, facilitando o frontend.
    # Tornei o prompt ainda mais assertivo sobre o formato ARRAY de strings para 'story'.
    prompt = f"""
        Crie {tamanhos.get(extensao, 'uma história média')} no gênero {genero} com o tema: {tema}.
        A história deve ter uma narrativa envolvente e ser coerente com o tema e gênero.
        Se possível, inclua uma moral no final.
        O campo 'story' DEVE ser um ARRAY de strings, onde cada string é um parágrafo.
        Garanta que o campo 'story' nunca seja vazio.

        Formato de resposta em JSON (EXATAMENTE este formato, como um array de um objeto, sem marcações markdown):
    
        {{
            "title": "O Teste dos Horrores (e da Comédia)",
            "genero": "{genero}",
            "extensao": "{extensao}",
            "personagens": ["Carlinhos", "Dona Clotilde"],
            "story": [
                "A sala de aula era um caldeirão de nervos. O temido teste de história pairava sobre nós como uma nuvem de gafanhotos acadêmicos.",
                "Carlinhos, o mestre do 'chute' consciente, tentava colar discretamente, mas seu bigode postiço (parte de um disfarce elaborado para parecer mais inteligente) insistia em cair dentro do livro.",
                "Dona Clotilde, a professora, com seu radar anti-cola calibrado, flagrou-o. 'Carlinhos!', trovejou, 'Seu bigode está te denunciando!'. A sala inteira explodiu em risos.",
                "Carlinhos, vermelho como um tomate, colou o bigode de volta, dessa vez no queixo, e murmurou: 'Pelo menos acertei a questão sobre a Revolução Francesa, né?'.",
                "Dona Clotilde suspirou, mas um sorriso escapou-lhe. Até o terror acadêmico pode ter seus momentos de comédia."
            ],
            "moral": "Às vezes, a comédia inesperada pode aliviar a tensão."
        }}
    """

    print(f"[DEBUG BACKEND] Prompt enviado para a IA:\n{prompt[:500]}...") # Log do prompt

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json", # Pede para a IA retornar JSON
                "temperature": 0.7 # Adicionado para controlar a criatividade (0.0-1.0)
            }
        )
        
        print(f"[DEBUG BACKEND] Resposta bruta da IA (response.text):\n{response.text[:1000]}...") # Log da resposta bruta

        historia_data = None
        try:
            historia_data = json.loads(response.text)
            print(f"[DEBUG BACKEND] historia_data após json.loads: {historia_data}")
        except json.JSONDecodeError as e:
            # Se a IA não retornou um JSON válido, loga e levanta um erro específico.
            print(f"[ERROR BACKEND] Erro ao decodificar JSON da resposta da IA: {e}")
            print(f"[ERROR BACKEND] Resposta bruta que causou o erro: {response.text}")
            raise ValueError(f"Resposta da IA não é JSON válido: {e}. Resposta: {response.text[:500]}...")

        # === LÓGICA DE NORMALIZAÇÃO E GARANTIA DE FORMATO DA RESPOSTA DA IA ===
        # O objetivo é garantir que o resultado final seja sempre um array contendo um objeto história.

        if not isinstance(historia_data, list):
            # Se a IA retornou um único objeto ou algo mais, tenta encapsular.
            if isinstance(historia_data, dict):
                historia_data = [historia_data]
            else:
                # Se não é lista nem dicionário, é um formato inesperado.
                raise ValueError(f"Formato raiz da resposta da IA inesperado: {type(historia_data).__name__}. Conteúdo: {historia_data}")

        if not historia_data: # Verifica se o array está vazio após a normalização inicial
            print("[WARN BACKEND] A IA retornou um array JSON vazio.")
            # Retorna um erro específico se a IA falhou em gerar qualquer conteúdo.
            return {
                "erro": "A IA não conseguiu gerar uma história. O retorno estava vazio.",
                "detalhes": "Tente novamente com um tema diferente ou ajuste o prompt."
            }
        
        # Pega o primeiro (e esperado único) objeto da história do array
        historia_objeto = historia_data[0] 

        # Valida e normaliza o objeto da história
        if not isinstance(historia_objeto, dict):
            raise ValueError(f"O primeiro item do array da IA não é um dicionário: {type(historia_objeto).__name__}. Conteúdo: {historia_objeto}")

        # Garante que 'title' é uma string
        if 'title' not in historia_objeto or not isinstance(historia_objeto['title'], str):
            historia_objeto['title'] = "História Gerada" # Fallback para título
            print("[WARN BACKEND] Título ausente ou inválido na resposta da IA. Usando fallback.")

        # Garante que 'story' seja um array de strings
        if 'story' in historia_objeto:
            if isinstance(historia_objeto['story'], str):
                # Se 'story' é uma string, divide em parágrafos por quebras de linha
                # Ajuste a heurística de split se as respostas da IA variarem
                historia_objeto['story'] = [p.strip() for p in historia_objeto['story'].split('\n') if p.strip()]
            elif not isinstance(historia_objeto['story'], list):
                # Se não é string nem lista (tipo inesperado), tenta converter para array com o valor original
                historia_objeto['story'] = [str(historia_objeto['story'])] if historia_objeto['story'] else []
        else:
            historia_objeto['story'] = [] # Garante que 'story' exista como array vazio se a IA não o incluiu
            print("[WARN BACKEND] Campo 'story' ausente na resposta da IA. Criando array vazio.")

        # Garante que 'story' não seja um array vazio (pode acontecer se a IA gerar só espaços ou newlines)
        if not historia_objeto['story']:
             historia_objeto['story'] = ["Não foi possível gerar o conteúdo da história. Tente novamente."]
             print("[WARN BACKEND] O array 'story' estava vazio após normalização. Adicionando mensagem fallback.")

        # Garante que 'genero' e 'extensao' estejam no objeto final para o frontend,
        # caso a IA os ignore ou retorne valores padrão.
        if 'genero' not in historia_objeto or not historia_objeto['genero']:
            historia_objeto['genero'] = genero
            print(f"[WARN BACKEND] Gênero ausente ou inválido na IA. Usando '{genero}'.")
        if 'extensao' not in historia_objeto or not historia_objeto['extensao']:
            historia_objeto['extensao'] = extensao
            print(f"[WARN BACKEND] Extensão ausente ou inválida na IA. Usando '{extensao}'.")
        
        # Pode adicionar personagens e moral aqui também se a IA falhar em retornar ou formatar
        if 'personagens' not in historia_objeto or not isinstance(historia_objeto['personagens'], list):
            historia_objeto['personagens'] = [] # Garante que seja um array vazio se ausente/inválido
            print("[WARN BACKEND] Campo 'personagens' ausente ou inválido. Criando array vazio.")
        
        if 'moral' not in historia_objeto or not isinstance(historia_objeto['moral'], str):
            historia_objeto['moral'] = "" # Garante que seja string vazia se ausente/inválido
            print("[WARN BACKEND] Campo 'moral' ausente ou inválido. Criando string vazia.")


        # Retorna o array que contém o objeto da história (agora normalizado)
        # O frontend espera um array, então retornamos historia_data que já é um array [historia_objeto]
        print(f"[DEBUG BACKEND] Resposta final da função gerar_historia:\n{historia_data}")
        return historia_data

    except Exception as e:
        print(f"[ERROR BACKEND] Erro geral na função gerar_historia: {e}")
        return {
            "erro": "Não foi possível gerar a história devido a um erro interno.",
            "detalhes": str(e)
        }

@app.route('/')
def index():
    """Rota de teste simples para verificar se a API está online."""
    return 'API ON!!'


@app.route('/historia', methods=['GET', 'POST', 'OPTIONS'])
def historia_route():
    """
    Endpoint principal para geração de histórias.
    Lida com requisições POST para gerar histórias e OPTIONS para preflight CORS.
    """
    # Lidar com requisições OPTIONS (preflight CORS)
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With' # Adicionado X-Requested-With
        return response, 200

    # Lidar com requisições GET (informação sobre o endpoint)
    if request.method == 'GET':
        response = jsonify({
            "mensagem": "Este é o endpoint da API para gerar histórias.",
            "uso": "Envie uma requisição POST para esta URL com JSON contendo 'tema', 'genero' (opcional), 'extensao' (opcional)."
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 200

    # Lidar com requisições POST (gerar história)
    elif request.method == 'POST':
        try:
            dados = request.get_json()
            print(f"[DEBUG ROUTE] Dados recebidos na rota /historia: {dados}")

            # Validação básica da requisição JSON
            if not dados or not isinstance(dados, dict):
                response = jsonify({'erro': 'Requisição inválida. Envie um JSON válido no corpo.'})
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 400

            tema = dados.get('tema', '').strip()
            # Validação do tema
            if len(tema) < 3:
                response = jsonify({'erro': 'O tema deve ter pelo menos 3 caracteres.'})
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 400

            genero = dados.get('genero', 'fantasia')
            extensao = dados.get('extensao', 'media')

            # Chama a função para gerar a história
            historia = gerar_historia(tema, genero, extensao)
            print(f"[DEBUG ROUTE] Retorno de gerar_historia(): {historia}")

            # Verifica se a função gerar_historia retornou um erro (um dicionário com a chave 'erro')
            if isinstance(historia, dict) and 'erro' in historia:
                response = jsonify(historia)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 500 # Erro interno ou da IA

            # --- CORREÇÃO: Envia o array retornado por gerar_historia diretamente ---
            # 'historia' DEVE ser um array [ { ... } ] neste ponto
            if not isinstance(historia, list) or not historia:
                print("[ERROR ROUTE] Formato inesperado de 'historia' retornado por gerar_historia. Não é um array válido.")
                response = jsonify({
                    'erro': 'Erro interno: O serviço de geração de história retornou um formato inválido.',
                    'detalhes': 'Verifique os logs do servidor para mais informações.'
                })
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 500

            response = jsonify(historia) # Envia diretamente o array
            # --- FIM DA CORREÇÃO ---

            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 200

        except Exception as e:
            # Captura erros inesperados no processamento da requisição POST
            print(f"[ERROR ROUTE] Erro inesperado na rota /historia: {e}")
            response = jsonify({
                'erro': 'Erro interno no servidor ao processar sua requisição.',
                'detalhes': str(e)
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 500


if __name__ == '__main__':

    app.run(debug=True, host='0.0.0.0')