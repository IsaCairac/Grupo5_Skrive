from flask import Flask, render_template, redirect, request, session, flash, jsonify
from flask_cors import CORS
import mysql.connector
from db_functions import *
from config import *
import google.generativeai as gemini
from datetime import date, datetime, timedelta
from fpdf import FPDF
from flask import make_response
import json
import requests
import re


app = Flask(__name__)
app.secret_key = SECRET_KEY 
CORS(app)   
gemini.configure(api_key=API_KEY)
model = gemini.GenerativeModel('gemini-1.5-flash')

# INDEX
@app.route("/")
def index(): 
    return render_template("index.html")  

# LOGIN
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if session:
            return redirect('/home')
        return render_template("login.html")
    
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        if email and senha:
            try:
                conexao, cursor = conectar_db()
                comandoSQL = "SELECT * FROM Professor WHERE email_prof = %s AND senha_prof = %s"
                cursor.execute(comandoSQL, (email, senha))
                usuario_encontrado = cursor.fetchone()
                
                if usuario_encontrado:
                    session['id_prof'] = usuario_encontrado[0]
                    session['nome_prof'] = usuario_encontrado[1]
                    session['disc_prof'] = usuario_encontrado[4]
                    return redirect('/dash')
                else:
                    return render_template('login.html', msg="Email/senha estão incorretos!")
            except mysql.connector.Error as e:
                print(e)
                return render_template('login.html', msg="Erro no banco de dados.")
            finally:
                encerrar_db(cursor, conexao)
        else:
            return render_template('login.html', msg="Por favor, preencha todos os campos.")
    
# ROTA LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect('/')

# ROTA 404 - PAGINA NÃO ENCONTRADA
@app.errorhandler(404)
def not_found(error):
    return render_template('erro.html'), 404

# CADASTRO
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'GET':
        return render_template('cadastro.html')

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        disciplina = request.form['disciplina']
        print(senha)

        if nome and senha and disciplina and email:
            try:
                conexao, cursor = conectar_db()
                comandoSQL = """
                INSERT INTO Professor (nome_prof, email_prof, senha_prof, disc_prof)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(comandoSQL, (nome, email, senha, disciplina))
                conexao.commit()
                return render_template('login.html', cadastro_realizado=True)
            except mysql.connector.errors.IntegrityError:
                return render_template('cadastro.html', error=f"Este email {email} já está em uso.")
            except mysql.connector.Error as e:
                print(f"Erro ao cadastrar: {e}")
                return render_template('cadastro.html', error="Erro ao processar o cadastro. Tente novamente mais tarde.")
            finally:
                encerrar_db(cursor, conexao)
        else:
            return render_template("cadastro.html", error="Todos os campos são obrigatórios.")

    return render_template('cadastro.html')

#--------------------------------------------------------------
# VERIFICAR EMAIL
#--------------------------------------------------------------
@app.route('/verificar_email', methods=['POST'])
def verificar_email():
    email = request.form.get('email')
    if email:
        try:
            conexao, cursor = conectar_db()
            comandoSQL = "SELECT * FROM Professor WHERE email_prof = %s"
            cursor.execute(comandoSQL, (email,))
            usuario_encontrado = cursor.fetchone()
            
            if usuario_encontrado:
                return jsonify({'disponivel': False})  # Email já está em uso
            else:
                return jsonify({'disponivel': True})  # Email disponível
        except mysql.connector.Error as e:
            print(e)
            return jsonify({'error': "Erro no banco de dados."})
        finally:
            encerrar_db(cursor, conexao)
    return jsonify({'error': "Email não fornecido."})

#--------------------------------------------------------------
# PÁGINA DASHBORD
#--------------------------------------------------------------
@app.route("/dash")
def dash():
    return render_template('dash.html')

#--------------------------------------------------------------
# CORPO HEADER LOGADO
#--------------------------------------------------------------
@app.route("/home")
def home():
    return render_template('header_log.html')

# GERADOR
@app.route("/gerador")
def geradorpage(): 
    return render_template("gerador.html")  

# SALVAR TEXTO
@app.route("/texto", methods=['POST'])
def texto():
    if not session:
        return redirect("/login")
    
    id_prof = session.get('id_prof')
    titulo = request.form.get('titulo')
    conteudo = request.form.get('conteudo')

    # Verificando o que está sendo enviado
    print(request.form)

    if titulo and conteudo:
        try:
            conexao, cursor = conectar_db()
            comandoSQL = """
                INSERT INTO Texto (conteudo, titulo, data_envio, id_prof)
                VALUES (%s, %s, NOW(), %s)
            """
            cursor.execute(comandoSQL, (conteudo, titulo, id_prof))
            conexao.commit()
            session["id_texto"] = cursor.lastrowid # último texto

            return redirect("/criar_atividade")
        except mysql.connector.Error as e:
            print(f"Erro ao salvar o texto: {e}")
            return render_template('erro.html', erro=f"Erro ao salvar o texto: {e}")  # Retorno em caso de erro
        finally:
            encerrar_db(cursor, conexao)
    else:
        return render_template('erro.html', erro="Preencha todos os campos.")  # Retorno em caso de dados ausentes

# SALVAR ATIVIDADE 
@app.route("/criar_atividade", methods=['GET', 'POST'])
def salvar_atividade():
    if not session:
        return redirect("/login")
    
    id_prof = session.get("id_prof")

    if request.method == 'GET':
        try:
            id_ultimotexto = session.get("id_texto", None)
            conexao, cursor = conectar_db()
            comandoSQL = "SELECT * FROM Texto WHERE id_prof = %s"
            cursor.execute(comandoSQL, (id_prof,))
            textos = cursor.fetchall()
            if textos:
                return render_template("gerador_atividade.html", textos=textos, id_ultimotexto=id_ultimotexto)
            else:
                return redirect("/gerador")
        except mysql.connector.Error as e:
            print(f"Erro ao buscar o texto: {e}")
            return render_template('erro.html', erro=f"Ops! Não é possível criar uma atividade sem inserir um texto antes... Tente novamente!")
        finally:
            encerrar_db(cursor, conexao)

    if request.method == 'POST':
        # Capturar os parâmetros da atividade
        id_texto = request.form['id_texto']
        titulo = request.form['titulo']
        tipo_ativ = request.form['tipo_ativ']
        nivel_ativ = request.form['nivel_ativ']
        publico_ativ = request.form['publico_ativ']
        descricao = request.form['descricao']
        num_questoes = request.form['num_questoes']
        print(request.form)

        try:
            conexao, cursor = conectar_db()
            comandoSQL = """
                INSERT INTO Atividade (titulo, descricao, tipo_ativ, nivel_ativ, publico_ativ, num_questoes, id_texto)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(comandoSQL, (titulo, descricao, tipo_ativ, nivel_ativ, publico_ativ, num_questoes, id_texto))
            conexao.commit()
            session["id_ativ"] = cursor.lastrowid
            print("Atividade salva no BD!")

            # Redireciona para a rota correta dependendo do tipo da atividade
            if tipo_ativ.lower() == "dissertativa":
                return redirect("/questoes_dis")
            else:
                return redirect("/questoes")
        
        except mysql.connector.Error as e:
            return f"Erro ao salvar a atividade: {e}"
        except Exception as e:
            return f"Erro de back-end: {e}"
        finally:
            encerrar_db(cursor, conexao)

# GERADOR - GERA E EXIBE QUESTÕES
@app.route("/questoes")
def gerador():
    if not session:
        return redirect("/login")
    
    if not "id_ativ" in session:
        return redirect("/criar_atividade")

    id_ativ = session['id_ativ'] 

    try:
        conexao, cursor = conectar_db()
        cursor = conexao.cursor(dictionary=True)
        comandoSQL = '''
        SELECT atividade.*, texto.titulo, texto.conteudo FROM atividade
        JOIN texto ON atividade.id_texto = texto.id_texto
        WHERE atividade.id_ativ = %s
        '''
        cursor.execute(comandoSQL, (id_ativ,))
        atividade = cursor.fetchone()
   
        if atividade:
            # Gera o prompt e obter a resposta da API
            prompt = f"""
                De acordo com esse texto:
                Título: {atividade['titulo']}
                Texto: {atividade['conteudo']}
                Gere {atividade['num_questoes']} questões do tipo {atividade['tipo_ativ']} para {atividade['publico_ativ']} com o nível de dificuldade {atividade['nivel_ativ']}.
                Cada questão deve ter 4 alternativas, sendo apenas uma correta.     
                Gere um código SQL puro para inserir dados na tabela 'Questao', sem nenhuma formatação adicional, caracteres especiais ou escape de caracteres. A saída deve ser uma única linha de código SQL. Não tire o "%s" do último campo, pois é um ID gerado automaticamente. Os campos enunciado, alternativa1, alternativa2, alternativa3, alternativa4 devem ter no máximo 300 caracteres **e não podem conter vírgulas**. Faça apenas um (1) INSERT com o cadastro de todas questões, o campo 'correta' é do tipo número inteiro, separe os campos de cada INSERT com uma # como delimitador, não utilize vírgula para separá-los, conforme o modelo abaixo:
                INSERT INTO Questao (enunciado, alternativa1, alternativa2, alternativa3, alternativa4, correta, id_ativ) VALUES ('Qual propriedade dos compostos organicos permite que eles sejam usados como combustivel?'# 'Solubilidade'# 'Polaridade'# 'Combustibilidade'# 'Cadeia carbonica'# 3# %s);
            """

            resposta = model.generate_content(prompt)
            
            # Extrai o texto da resposta da API
            text = resposta.candidates[0].content.parts[0].text  # Acessa o texto da resposta da API

            # Procura o primeiro comando SQL com "INSERT INTO"
            start = text.find("INSERT INTO")  # Localiza a primeira ocorrência de "INSERT INTO"
            if start != -1:
                sql_commands = text[start:].strip()  # Extrai tudo a partir da primeira ocorrência de SQL
            else:
                sql_commands = "Nenhum comando SQL encontrado."

            if sql_commands:
                print("Comandos SQL recebidos:", sql_commands)  # Exibe os comandos SQL gerados
                print("Até aqui OK!")
                try:
                    conexao, cursor = conectar_db()
                    
                    # Extraia os valores dos campos com regex, considerando o delimitador #
                    import re
                    questoes_info = re.findall(r"VALUES\s*\((.*?)\)", sql_commands)

                    if questoes_info:
                        questoes_inserir = []
                        for questao in questoes_info:
                            # Divide os campos pelo delimitador #
                            valores = questao.split("#")
                            valores = [v.strip().strip("'") for v in valores]  # Remove espaços e aspas ao redor

                            # Verifica se o número de valores está correto
                            if len(valores) == 7:
                                # Substitui vírgulas por ponto e vírgula no enunciado e nas alternativas
                                enunciado = valores[0]
                                alt1 = valores[1]
                                alt2 = valores[2]
                                alt3 = valores[3]
                                alt4 = valores[4]
                                correta = valores[5]

                                try:
                                    # Adiciona a questão formatada na lista para inserção
                                    questoes_inserir.append((enunciado, alt1, alt2, alt3, alt4, int(correta), id_ativ))
                                except ValueError:
                                    print("Erro ao converter a alternativa correta em número:", correta)
                                    continue
                            else:
                                print("Erro ao processar a questão (campos inválidos ou vírgulas presentes):", valores)
                                # Reexecute a geração da resposta se houver erro nos valores
                                resposta = model.generate_content(prompt)
                                text = resposta.candidates[0].content.parts[0].text
                                start = text.find("INSERT INTO")
                                if start != -1:
                                    sql_commands = text[start:].strip()
                                else:
                                    sql_commands = "Nenhum comando SQL encontrado."
                                break  # Sai do loop para processar a nova resposta

                        # Executa a inserção se todas as questões estiverem formatadas corretamente
                        if questoes_inserir:
                            for questao in questoes_inserir:
                                print("Questão inserida no banco:", questao[0])  # Mostra o conteúdo da questão antes da inserção
                                cursor.execute("INSERT INTO Questao (enunciado, alternativa1, alternativa2, alternativa3, alternativa4, correta, id_ativ) VALUES (%s, %s, %s, %s, %s, %s, %s);", questao)
                            conexao.commit()

                    conexao.close()  # Fecha a conexão após inserir as questões

                    # Crie uma nova conexão para selecionar as questões
                    conexao, cursor = conectar_db()
                    cursor.execute("SELECT titulo FROM Atividade WHERE id_ativ = %s", (id_ativ,))
                    atividade = cursor.fetchone()
                    titulo_atividade = atividade[0]
                    comandoSQL = 'SELECT * FROM questao WHERE id_ativ = %s'
                    cursor.execute(comandoSQL, (id_ativ,))
                    questoes = cursor.fetchall()
                    conexao.commit()

                    return render_template("questoes.html", questoes=questoes, titulo_atividade=titulo_atividade, id_ativ=id_ativ)
                except mysql.connector.Error as e:
                    print(f"Erro de BD: {e}")
                    return f"Erro de BD: {e}"
                except Exception as e:
                    print(f"Erro de back-end: {e}")
                    return f"Erro de back-end: {e}"
                finally:
                    encerrar_db(cursor, conexao)

        return render_template("questoes.html", questoes=questoes)
    except mysql.connector.Error as e:
        print(f"Erro de BD: {e}")
        return f"Erro de BD: {e}"
    except Exception as e:
        print(f"Erro de back-end: {e}")
        return f"Erro de back-end: {e}"
    finally:
        encerrar_db(cursor, conexao)
         
# GERADOR - QUESTÕES DISSERTATIVAS
@app.route("/questoes_dis")
def gerador_questoes_dissertativas():
    if not session:
        return redirect("/login")
    
    if "id_ativ" not in session:
        return redirect("/criar_atividade")

    id_ativ = session["id_ativ"]

    try:
        conexao, cursor = conectar_db()
        cursor = conexao.cursor(dictionary=True)
        comandoSQL = '''
        SELECT atividade.*, texto.titulo, texto.conteudo FROM atividade
        JOIN texto ON atividade.id_texto = texto.id_texto
        WHERE atividade.id_ativ = %s
        '''
        cursor.execute(comandoSQL, (id_ativ,))
        atividade = cursor.fetchone()

        if atividade:
            prompt = f"""
                De acordo com esse texto:
                Título: {atividade['titulo']}
                Texto: {atividade['conteudo']}
                Gere {atividade['num_questoes']} questões dissertativas para {atividade['publico_ativ']} com o nível de dificuldade {atividade['nivel_ativ']}.
                As questões devem ser claras e relacionadas ao tema do texto.
                Retorne APENAS um código SQL puro para inserir dados na tabela 'QuestaoDis', sem nenhuma formatação adicional, caracteres especiais ou escape de caracteres. A saída deve ser uma única linha de código SQL. Não tire o "%s" do último campo, pois é um ID gerado automaticamente. O campo enunciado deve ter no máximo 300 caracteres **e não pode conter vírgulas**. Faça 1 INSERT para o cadastro de cada questão, separe cada INSERT com uma # como delimitador, conforme o modelo abaixo:
                INSERT INTO QuestaoDis (enunciado, id_ativ) VALUES ('Qual propriedade dos compostos organicos permite que eles sejam usados como combustivel?', %s); # INSERT INTO QuestaoDis (enunciado, id_ativ) VALUES ('Qual a principal função orgânica presente na molécula de etanol (C₂H₅OH)?', %s);
            """
            resposta = model.generate_content(prompt)
            questoes_dissertativas = resposta.candidates[0].content.parts[0].text
            print("Texto recebido da API:", questoes_dissertativas)

            # Localizar e separar comandos SQL
            start = questoes_dissertativas.find("INSERT INTO")
            if start != -1:
                sql_commands = questoes_dissertativas[start:].strip()
            else:
                return "Erro: Nenhum comando SQL encontrado."

            # Dividir os comandos usando o delimitador `#`
            comandos = [cmd.strip() for cmd in sql_commands.split("#") if cmd.strip()]

            # Verificar e executar comandos
            for comando in comandos:
                if comando.upper().startswith("INSERT INTO QUESTAODIS"):
                    try:
                        # Substituir o placeholder %s pelo valor real de id_ativ
                        comando_sql = comando.replace("%s", "%s")
                        cursor.execute(comando_sql, (id_ativ,))
                    except mysql.connector.Error as e:
                        return f"Erro ao executar comando SQL: {e}"
                else:
                    print(f"Comando ignorado: {comando}")

            conexao.commit()
            print("Comandos SQL executados com sucesso.")

            # Recuperar questões para exibição
            conexao, cursor = conectar_db()
            cursor.execute("SELECT titulo FROM Atividade WHERE id_ativ = %s", (id_ativ,))
            atividade = cursor.fetchone()
            titulo_atividade = atividade[0] if atividade else "Atividade não encontrada"
            cursor.execute("SELECT * FROM questaodis WHERE id_ativ = %s", (id_ativ,))
            questoes = cursor.fetchall()
            
            return render_template("questoes_dis.html", questoes=questoes, titulo_atividade=titulo_atividade, id_ativ=id_ativ)

    except Exception as e:
        return f"Erro de back-end: {e}"

    finally:
        encerrar_db(cursor, conexao)

# HISTORICO
@app.route('/historico')
def listar_atividades():
    if not session:
        return redirect("/login")

    try:
        if "id_prof" in session:
            id_profativo = session['id_prof']

        conexao, cursor = conectar_db()

        # Definindo os intervalos de tempo
        hoje = datetime.now()
        inicio_hoje = hoje.replace(hour=0, minute=0, second=0, microsecond=0)  # Início do dia
        ultimos_7_dias = hoje - timedelta(days=7)
        inicio_3_meses = hoje - timedelta(days=90)
        inicio_ano = hoje - timedelta(days=365)

        # Consultas SQL ajustadas para criar intervalos exclusivos e filtrar pelo id_prof
        comando_hoje = """
            SELECT Atividade.* 
            FROM Atividade
            INNER JOIN Texto ON Atividade.id_texto = Texto.id_texto
            WHERE Texto.id_prof = %s AND Atividade.data_hora >= %s
            ORDER BY Atividade.data_hora DESC
        """
        comando_7_dias = """
            SELECT Atividade.* 
            FROM Atividade
            INNER JOIN Texto ON Atividade.id_texto = Texto.id_texto
            WHERE Texto.id_prof = %s AND Atividade.data_hora BETWEEN %s AND %s
            ORDER BY Atividade.data_hora DESC
        """
        comando_3_meses = """
            SELECT Atividade.* 
            FROM Atividade
            INNER JOIN Texto ON Atividade.id_texto = Texto.id_texto
            WHERE Texto.id_prof = %s AND Atividade.data_hora BETWEEN %s AND %s
            ORDER BY Atividade.data_hora DESC
        """
        comando_ano = """
            SELECT Atividade.* 
            FROM Atividade
            INNER JOIN Texto ON Atividade.id_texto = Texto.id_texto
            WHERE Texto.id_prof = %s AND Atividade.data_hora BETWEEN %s AND %s
            ORDER BY Atividade.data_hora DESC
        """
        comando_mais_antigas = """
            SELECT Atividade.* 
            FROM Atividade
            INNER JOIN Texto ON Atividade.id_texto = Texto.id_texto
            WHERE Texto.id_prof = %s AND Atividade.data_hora < %s
            ORDER BY Atividade.data_hora DESC
        """

        # Executando as consultas
        cursor.execute(comando_hoje, (id_profativo, inicio_hoje))
        atividades_hoje = cursor.fetchall()

        cursor.execute(comando_7_dias, (id_profativo, ultimos_7_dias, inicio_hoje))
        atividades_7_dias = cursor.fetchall()

        cursor.execute(comando_3_meses, (id_profativo, inicio_3_meses, ultimos_7_dias))
        atividades_3_meses = cursor.fetchall()

        cursor.execute(comando_ano, (id_profativo, inicio_ano, inicio_3_meses))
        atividades_ano = cursor.fetchall()

        cursor.execute(comando_mais_antigas, (id_profativo, inicio_ano))
        atividades_mais_antigas = cursor.fetchall()

        # Renderizando o template com as listas de atividades
        return render_template(
            "historico.html",
            atividades_hoje=atividades_hoje,
            atividades_7_dias=atividades_7_dias,
            atividades_3_meses=atividades_3_meses,
            atividades_ano=atividades_ano,
            atividades_mais_antigas=atividades_mais_antigas,
            id_profativo=id_profativo
        )

    except mysql.connector.Error as e:
        print(f"Erro ao buscar o texto: {e}")
        return render_template('erro.html', erro=f"Erro ao buscar o texto: {e}")
    finally:
        encerrar_db(cursor, conexao)

# HISTÓRICO - QUESTÃO
@app.route("/historico_questao/<int:id_ativ>")
def exibir_questoes(id_ativ):
    if not session:
        return redirect("/login")

    # Conectando ao banco de dados
    conexao, cursor = conectar_db()

    # Obtendo o tipo e o título da atividade a partir da tabela Atividade
    comandoSQL_atividade = '''
    SELECT tipo_ativ, titulo FROM Atividade WHERE id_ativ = %s
    '''
    cursor.execute(comandoSQL_atividade, (id_ativ,))
    atividade = cursor.fetchone()

    if not atividade:
        return "Atividade não encontrada."

    tipo_atividade, titulo_atividade = atividade  # Descompactando os resultados

    # Obtendo as questões associadas à atividade
    if tipo_atividade == 'Dissertativa':
        comandoSQL = '''
        SELECT * FROM questaodis WHERE id_ativ = %s
        '''
        cursor.execute(comandoSQL, (id_ativ,))
        questoes = cursor.fetchall()

        if questoes:
            conexao.close()
            # Passando também o título para o template
            return render_template("historico_questao_dis.html", questoes=questoes, titulo=titulo_atividade)
        else:
            conexao.close()
            return "Nenhuma questão dissertativa encontrada para essa atividade."

    else:
        comandoSQL = '''
        SELECT * FROM Questao WHERE id_ativ = %s
        '''
        cursor.execute(comandoSQL, (id_ativ,))
        questoes = cursor.fetchall()

        if questoes:
            conexao.close()
            # Passando também o título para o template
            return render_template("historico_questao_multipla.html", questoes=questoes, titulo=titulo_atividade)
        else:
            conexao.close()
            return "Nenhuma questão encontrada para essa atividade."

#ROTA EDITAR QUESTAO
@app.route("/editar_questao/<int:id_questao>")
def editar(id_questao):
    if not session:
        return redirect('/login')
    
    try:
        conexao, cursor = conectar_db()
        comandoSQL = "SELECT * FROM Questao WHERE id_questao = %s"
        cursor.execute(comandoSQL, (id_questao,))
        questao = cursor.fetchone()  # Alterado para fetchone()
        
        if questao:
            return render_template('editar_questao.html', questao=questao)
        else:
            flash("Questão não encontrada.", "erro")
            return redirect('/questoes')
    except mysql.connector.Error as e:
        print(f"Erro ao editar a questão: {e}")
        return f"Erro ao editar a questão: {e}"
    finally:
        encerrar_db(cursor, conexao)

# ATUALIZAR QUESTÃO
@app.route('/atualizar_questao/<int:id_questao>', methods=['POST'])
def atualizar_questao(id_questao):
    enunciado = request.form['enunciado']
    alternativa_a = request.form['alternativa_a']
    alternativa_b = request.form['alternativa_b']
    alternativa_c = request.form['alternativa_c']
    alternativa_d = request.form['alternativa_d']
    resposta_correta = request.form['resposta_correta']

    conexao, cursor = conectar_db()
    query = """
        UPDATE questao 
        SET enunciado = %s, alternativa1 = %s, alternativa2 = %s,
            alternativa3 = %s, alternativa4 = %s, correta = %s
        WHERE id_questao = %s
    """
    valores = (enunciado, alternativa_a, alternativa_b, alternativa_c, alternativa_d, resposta_correta, id_questao)
    cursor.execute(query, valores)
    conexao.commit()
    encerrar_db(cursor, conexao)

    return redirect('/historico')

#ROTA EDITAR QUESTAO DISSERTATIVA
@app.route("/editar_questao_dis/<int:id_questaodis>")
def editar_dis(id_questaodis):
    if not session:
        return redirect('/login')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = "SELECT * FROM QuestaoDis WHERE id_questaodis = %s"
        cursor.execute(comandoSQL, (id_questaodis,))
        questao = cursor.fetchone()  # Use fetchone para um único registro

        if questao:
            return render_template('editar_questao_dis.html', questao=questao)
        else:
            flash("Questão não encontrada.", "erro")
            return redirect('/historico')
    except mysql.connector.Error as e:
        print(f"Erro ao editar a questão: {e}")
        return f"Erro ao editar a questão: {e}"
    finally:
        encerrar_db(cursor, conexao)

# ATUALIZAR QUESTÃO DISSERTATIVA
@app.route('/atualizar_questao_dis/<int:id_questaodis>', methods=['POST'])
def atualizar_questao_dis(id_questaodis):
    enunciado = request.form['enunciado']

    conexao, cursor = conectar_db()
    query = """
        UPDATE questaodis
        SET enunciado = %s
        WHERE id_questaodis = %s
    """
    valores = (enunciado, id_questaodis)
    cursor.execute(query, valores)
    conexao.commit()
    encerrar_db(cursor, conexao)

    return redirect('/historico')

# EXCLUIR ATIVIDADE
@app.route("/excluir_atividade/<int:id_ativ>", methods=["POST"])
def excluir_atividade(id_ativ):
    if not session:
        return redirect("/login")
    try:
        # Conectar ao banco de dados
        conexao, cursor = conectar_db()

        # Verificar o tipo da atividade
        cursor.execute("SELECT tipo_ativ FROM Atividade WHERE id_ativ = %s", (id_ativ,))
        atividade = cursor.fetchone()

        if not atividade:
            flash("Atividade não encontrada.", "erro")
            return redirect("/historico")

        tipo_ativ = atividade[0]  # Obter o tipo da atividade

        # Excluir as questões com base no tipo da atividade
        if tipo_ativ == 'Dissertativa':
            cursor.execute("DELETE FROM questaodis WHERE id_ativ = %s", (id_ativ,))
        else:
            cursor.execute("DELETE FROM Questao WHERE id_ativ = %s", (id_ativ,))

        # Excluir a atividade
        cursor.execute("DELETE FROM Atividade WHERE id_ativ = %s", (id_ativ,))
        conexao.commit()

        # Encerrar a conexão
        encerrar_db(cursor, conexao)
        flash("Atividade excluída com sucesso!", "sucesso")
        return redirect("/historico")

    except mysql.connector.Error as erro:
        flash(f"Erro de BD: {erro}", "erro")
        return redirect("/historico")
    except Exception as erro:
        flash(f"Erro de back-end: {erro}", "erro")
        return redirect("/historico")
    
# ADM
@app.route("/adm", methods=['GET'])
def adm():
    conexao, cursor = conectar_db()

    cursor.execute('SELECT id_prof, nome_prof, email_prof, disc_prof FROM Professor')
    professores = cursor.fetchall()

    atividades_query = '''
        SELECT A.id_ativ, A.titulo, A.descricao, P.nome_prof 
        FROM Atividade A
        INNER JOIN Texto T ON A.id_texto = T.id_texto
        INNER JOIN Professor P ON T.id_prof = P.id_prof
    '''
    cursor.execute(atividades_query)
    atividades = cursor.fetchall()

    encerrar_db(cursor, conexao)

    return render_template("adm.html", professores=professores, atividades=atividades)

# ADM - EXCLUIR USUÁRIO
@app.route("/excluir_usuario/<int:professor_id>", methods=['POST'])
def excluir_usuario(professor_id):
    conexao, cursor = conectar_db()
    
    try:
        # Excluir os textos associados ao professor
        excluir_textos_query = "DELETE FROM Texto WHERE id_prof = %s"
        cursor.execute(excluir_textos_query, (professor_id,))

        # Excluir o professor
        excluir_professor_query = "DELETE FROM Professor WHERE id_prof = %s"
        cursor.execute(excluir_professor_query, (professor_id,))
        
        # Confirmar as alterações
        conexao.commit()
        encerrar_db(cursor, conexao)

        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Erro ao excluir o usuário: {e}")
        encerrar_db(cursor, conexao)
        return jsonify({'success': False, 'error': str(e)}), 500
    
# EDITAR_CONTA (USER)
@app.route('/editar_conta', methods=['POST'])
def editar_conta():
    if 'id_prof' not in session:
        return redirect('/login')

    novo_nome = request.form['nome']
    novo_email = request.form['email']
    nova_senha = request.form['senha']

    try:
        conexao, cursor = conectar_db()
        # Verifica se o campo de senha está vazio
        if nova_senha:
            comando_sql = """
                UPDATE Professor 
                SET nome_prof = %s, email_prof = %s, senha_prof = %s 
                WHERE id_prof = %s
            """
            cursor.execute(comando_sql, (novo_nome, novo_email, nova_senha, session['id_prof']))
        else:
            # Se não houver nova senha, atualiza apenas o nome e o email
            comando_sql = """
                UPDATE Professor 
                SET nome_prof = %s, email_prof = %s 
                WHERE id_prof = %s
            """
            cursor.execute(comando_sql, (novo_nome, novo_email, session['id_prof']))

        conexao.commit()
        return redirect('/minha_conta')

    except mysql.connector.Error as e:
        print(f"Erro ao atualizar dados: {e}")
        return redirect('/minha_conta')

    finally:
        encerrar_db(cursor, conexao)

# EXCLUIR_CONTA (USER)
@app.route('/excluir_conta', methods=['POST'])
def excluir_conta():
    if 'id_prof' not in session:
        return redirect('/login')

    id_prof = session['id_prof']  # Obtém o ID do professor da sessão

    try:
        conexao, cursor = conectar_db()

        # Excluir questões associadas às atividades do professor
        cursor.execute("""
            DELETE Questao 
            FROM Questao 
            INNER JOIN Atividade ON Questao.id_ativ = Atividade.id_ativ
            INNER JOIN Texto ON Atividade.id_texto = Texto.id_texto
            WHERE Texto.id_prof = %s
        """, (id_prof,))

        # Excluir atividades associadas aos textos do professor
        cursor.execute("""
            DELETE Atividade 
            FROM Atividade 
            INNER JOIN Texto ON Atividade.id_texto = Texto.id_texto
            WHERE Texto.id_prof = %s
        """, (id_prof,))

        # Excluir textos associados ao professor
        cursor.execute("""
            DELETE FROM Texto WHERE id_prof = %s
        """, (id_prof,))

        # Excluir o professor (usuário)
        cursor.execute("""
            DELETE FROM Professor WHERE id_prof = %s
        """, (id_prof,))

        # Confirma a exclusão
        conexao.commit()

        # Remove a sessão do usuário
        session.pop('id_prof', None)

        # Redireciona o usuário para a página de login
        return redirect('/login')

    except mysql.connector.Error as e:
        print(f"Erro ao excluir a conta: {e}")
        return jsonify({"msg": "Erro interno ao excluir a conta."}), 500
    finally:
        encerrar_db(cursor, conexao)

# MINHA CONTA
@app.route('/minha_conta', methods=['GET', 'POST'])
def minha_conta():
    if 'id_prof' not in session:
        return redirect('/login')

    try:
        conexao, cursor = conectar_db()
        comandoSQL = "SELECT nome_prof, email_prof FROM Professor WHERE id_prof = %s"
        cursor.execute(comandoSQL, (session['id_prof'],))
        usuario = cursor.fetchone()

        if usuario:
            return render_template('minha_conta.html', usuario=usuario)
        else:
            return "Usuário não encontrado.", 404
    except mysql.connector.Error as e:
        print(f"Erro ao buscar dados: {e}")
        return "Erro ao carregar os dados.", 500
    finally:
        encerrar_db(cursor, conexao)

# BAIXAR PDF
@app.route("/baixar_pdf/<int:id_ativ>")
def baixar_pdf(id_ativ):
    if not session:
        return redirect("/login")
    
    try:
        conexao, cursor = conectar_db()

        # Recuperar título da atividade e tipo
        cursor.execute("SELECT titulo, tipo_ativ FROM atividade WHERE id_ativ = %s", (id_ativ,))
        atividade = cursor.fetchone()

        # Verificar se a atividade foi encontrada
        if not atividade:
            return "Atividade não encontrada.", 404

        # Recuperar questões
        cursor.execute("SELECT enunciado FROM questaodis WHERE id_ativ = %s", (id_ativ,))
        questoes_dissertativas = cursor.fetchall()

        # Criar PDF
        pdf = FPDF()
        pdf.add_page()

        # Usar Arial em todo o documento
        pdf.set_font("Arial", size=12)

        # Adicionar título da atividade com a cor #febc04
        pdf.set_font("Arial", style="B", size=18)
        pdf.set_text_color(254, 188, 4)  # Cor #febc04
        pdf.cell(200, 10, txt=f"{atividade[0]}", ln=True, align='C')

        # Resetando a cor do texto para preto após o título
        pdf.set_text_color(0, 0, 0)

        # Verificar o tipo de atividade e adicionar conteúdo
        if atividade[1] == "Dissertativa":
            # Adicionar questões dissertativas
            if questoes_dissertativas:
                pdf.set_font("Arial", size=14)
                pdf.ln(10)  # Espaço
                for i, questao in enumerate(questoes_dissertativas, start=1):
                    if len(questao) > 0:
                        pdf.multi_cell(0, 10, txt=f"{i}. {questao[0]}")
                    else:
                        pdf.multi_cell(0, 10, txt=f"{i}. Questão sem enunciado disponível.")
            else:
                pdf.multi_cell(0, 10, txt="Nenhuma questão dissertativa encontrada para esta atividade.")

        else:
            # Se a atividade não for dissertativa, baixar as questões geradas pela API
            cursor.execute("SELECT enunciado, alternativa1, alternativa2, alternativa3, alternativa4 FROM questao WHERE id_ativ = %s", (id_ativ,))
            questoes_api = cursor.fetchall()

            if questoes_api:
                pdf.set_font("Arial", size=14)
                pdf.ln(10)  # Espaço
                for i, questao in enumerate(questoes_api, start=1):
                    enunciado = questao[0]
                    alt1 = questao[1]
                    alt2 = questao[2]
                    alt3 = questao[3]
                    alt4 = questao[4]
                    pdf.multi_cell(0, 10, txt=f"{i}. {enunciado}")
                    pdf.multi_cell(0, 10, txt=f"A) {alt1}")
                    pdf.multi_cell(0, 10, txt=f"B) {alt2}")
                    pdf.multi_cell(0, 10, txt=f"C) {alt3}")
                    pdf.multi_cell(0, 10, txt=f"D) {alt4}")
                    pdf.ln(5)  # Espaço entre as questões
            else:
                pdf.multi_cell(0, 10, txt="Nenhuma questão gerada encontrada para esta atividade.")

        # Sanitizar o título para evitar problemas com caracteres inválidos no nome do arquivo
        titulo_sanitizado = "".join(c for c in atividade[0] if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')

        # Salvar em memória e retornar como resposta
        response = make_response(pdf.output(dest='S').encode('latin1'))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{titulo_sanitizado}.pdf"'
        return response

    except Exception as e:
        return f"Erro ao gerar PDF: {e}", 500

    finally:
        encerrar_db(cursor, conexao)


if TESTE:
    if __name__ == '__main__':
        app.run(debug=True)
