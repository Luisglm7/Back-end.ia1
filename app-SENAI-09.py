from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
from google import genai
import os
from dotenv import load_dotenv
import json

load_dotenv()

app = Flask(__name__)
CORS(app)  # Habilita CORS para todas as rotas

API_KEY = os.getenv("API_KEY")
API_KEY_FALLBACK = os.getenv("API_KEY_FALLBACK")

def criar_cliente_genai():
    try:
        return genai.Client(api_key=API_KEY)
    except Exception as e:
        print(f"[AVISO] Erro com chave principal: {e}")
        try:
            return genai.Client(api_key=API_KEY_FALLBACK)
        except Exception as e2:
            print(f"[ERRO] Chave reserva também falhou: {e2}")
            return None

client = criar_cliente_genai()

def gerar_historia(tema, genero="fantasia", extensao="media"):
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

    prompt = f"""
        Crie {tamanhos.get(extensao, 'uma história média')} no gênero {genero} com o tema: {tema}.
        A história deve ter uma narrativa envolvente e ser coerente com o tema e gênero.
        Se possível, inclua uma moral no final.
        O campo 'story' DEVE ser um ARRAY de strings, onde cada string é um parágrafo.
        Garanta que o campo 'story' nunca seja vazio.

        Formato de resposta em JSON (EXATAMENTE este formato, como um array de um objeto):
    
        {{
            "title": "O Teste dos Horrores (e da Comédia)",
            "genero": "{genero}",
            "extensao": "{extensao}",
            "personagens": ["Carlinhos", "Dona Clotilde"],
            "story": [
                "A sala de aula era um caldeirão de nervos..."
            ],
            "moral": "Às vezes, a comédia inesperada pode aliviar a tensão."
        }}
    """

    print(f"[DEBUG BACKEND] Prompt enviado para a IA:\n{prompt[:500]}...")

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "temperature": 0.7
            }
        )

        historia_data = None
        try:
            historia_data = json.loads(response.text)
            print(f"[DEBUG BACKEND] historia_data após json.loads: {historia_data}")
        except json.JSONDecodeError as e:
            print(f"[ERROR BACKEND] Erro ao decodificar JSON da resposta da IA: {e}")
            print(f"[ERROR BACKEND] Resposta bruta que causou o erro: {response.text}")
            raise ValueError(f"Resposta da IA não é JSON válido: {e}. Resposta: {response.text[:500]}...")

        if not isinstance(historia_data, list):
            if isinstance(historia_data, dict):
                historia_data = [historia_data]
            else:
                raise ValueError(f"Formato raiz da resposta da IA inesperado: {type(historia_data).__name__}. Conteúdo: {historia_data}")

        if not historia_data:
            return {
                "erro": "A IA não conseguiu gerar uma história. O retorno estava vazio.",
                "detalhes": "Tente novamente com um tema diferente ou ajuste o prompt."
            }

        historia_objeto = historia_data[0]

        if not isinstance(historia_objeto, dict):
            raise ValueError(f"O primeiro item do array da IA não é um dicionário: {type(historia_objeto).__name__}. Conteúdo: {historia_objeto}")

        if 'title' not in historia_objeto or not isinstance(historia_objeto['title'], str):
            historia_objeto['title'] = "História Gerada"

        if 'story' in historia_objeto:
            if isinstance(historia_objeto['story'], str):
                historia_objeto['story'] = [p.strip() for p in historia_objeto['story'].split('\n') if p.strip()]
            elif not isinstance(historia_objeto['story'], list):
                historia_objeto['story'] = [str(historia_objeto['story'])] if historia_objeto['story'] else []
        else:
            historia_objeto['story'] = []

        if not historia_objeto['story']:
            historia_objeto['story'] = ["Não foi possível gerar o conteúdo da história. Tente novamente."]

        if 'genero' not in historia_objeto or not historia_objeto['genero']:
            historia_objeto['genero'] = genero
        if 'extensao' not in historia_objeto or not historia_objeto['extensao']:
            historia_objeto['extensao'] = extensao

        if 'personagens' not in historia_objeto or not isinstance(historia_objeto['personagens'], list):
            historia_objeto['personagens'] = []

        if 'moral' not in historia_objeto or not isinstance(historia_objeto['moral'], str):
            historia_objeto['moral'] = ""

        return historia_data

    except Exception as e:
        print(f"[ERROR BACKEND] Erro geral na função gerar_historia: {e}")
        return {
            "erro": "Não foi possível gerar a história devido a um erro interno.",
            "detalhes": str(e)
        }

@app.route('/')
def index():
    return 'API ON!!'

@app.route('/historia', methods=['GET', 'POST', 'OPTIONS'])
def historia_route():
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-Requested-With'
        return response, 200

    if request.method == 'GET':
        response = jsonify({
            "mensagem": "Este é o endpoint da API para gerar histórias.",
            "uso": "Envie uma requisição POST para esta URL com JSON contendo 'tema', 'genero' (opcional), 'extensao' (opcional)."
        })
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response, 200

    elif request.method == 'POST':
        try:
            dados = request.get_json()
            print(f"[DEBUG ROUTE] Dados recebidos na rota /historia: {dados}")

            if not dados or not isinstance(dados, dict):
                response = jsonify({'erro': 'Requisição inválida. Envie um JSON válido no corpo.'})
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 400

            tema = dados.get('tema', '').strip()
            if len(tema) < 3:
                response = jsonify({'erro': 'O tema deve ter pelo menos 3 caracteres.'})
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 400

            genero = dados.get('genero', 'fantasia')
            extensao = dados.get('extensao', 'media')

            historia = gerar_historia(tema, genero, extensao)
            print(f"[DEBUG ROUTE] Retorno de gerar_historia(): {historia}")

            if isinstance(historia, dict) and 'erro' in historia:
                response = jsonify(historia)
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 500

            if not isinstance(historia, list) or not historia:
                print("[ERROR ROUTE] Formato inesperado de 'historia' retornado por gerar_historia. Não é um array válido.")
                response = jsonify({
                    'erro': 'Erro interno: O serviço de geração de história retornou um formato inválido.',
                    'detalhes': 'Verifique os logs do servidor para mais informações.'
                })
                response.headers['Access-Control-Allow-Origin'] = '*'
                return response, 500

            response = jsonify(historia)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 200

        except Exception as e:
            print(f"[ERROR ROUTE] Erro inesperado na rota /historia: {e}")
            response = jsonify({
                'erro': 'Erro interno no servidor ao processar sua requisição.',
                'detalhes': str(e)
            })
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response, 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
