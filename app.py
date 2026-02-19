from flask import Flask, render_template, request, redirect, url_for, abort
from flask import flash
import sqlite3
import uuid
import os


app = Flask(__name__)
app.secret_key = "sua_chave_super_secreta"

# MAPA DAS DIMENSÕES
# ===============================
MAPA_DIMENSOES = {
    1: "Exigencias",
    2: "Exigencias",
    3: "Exigencias",
    4: "Exigencias",
    5: "Exigencias",
    6: "Exigencias",

    7: "Influencia",
    8: "Influencia",
    9: "Influencia",
    10: "Influencia",

    11: "Informacao",
    12: "Informacao",
    13: "Informacao",
    14: "Informacao",
    15: "Informacao",
    16: "Informacao",

    17: "Chefias",
    18: "Chefias",
    19: "Chefias",
    20: "Chefias",
    21: "Chefias",
    22: "Chefias",

    23: "Autoeficacia",

    24: "satisfação",
    25: "satisfação",
    26: "satisfação",
    27: "satisfação",
    28: "satisfação",

    29: "Saude",

    30: "Impacto",
    31: "Impacto",

    32: "Sintomas",
    33: "Sintomas",
    34: "Sintomas",
    35: "Sintomas",
    36: "Sintomas",
    37: "Sintomas",

    38: "Assedio",
    39: "Assedio",
    40: "Assedio",
    41: "Assedio"
}


DATABASE = "database.db"

# ======================================================
# 🔹 CONEXÃO BANCO
# ======================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = sqlite3.connect("database.db")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            limite_respostas INTEGER
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS respostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id TEXT,
            pergunta INTEGER,
            dimensao TEXT,
            valor INTEGER,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        )
    """)

    conn.commit()
    conn.close()



# ======================================================
# 🔹 LÓGICA COPSOQ 2.0
# ======================================================

def calcular_score_0_100(valores):
    media = sum(valores) / len(valores)
    score = ((media - 1) / 4) * 100
    return round(score, 2)


def classificar_dimensao(score, tipo):
    if tipo == "risco":
        if score <= 33:
            return "baixo"
        elif score <= 66:
            return "moderado"
        else:
            return "alto"
    else:  # proteção
        if score <= 33:
            return "alto"
        elif score <= 66:
            return "moderado"
        else:
            return "baixo"


def peso_classificacao(classificacao):
    pesos = {"alto": 3, "moderado": 2, "baixo": 1}
    return pesos.get(classificacao, 1)


def processar_dimensoes(empresa_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT dimensao, tipo, valor
        FROM respostas
        WHERE empresa_id = ?
    """, (empresa_id,))

    dados = cursor.fetchall()
    conn.close()

    if not dados:
        return []

    agrupado = {}

    for row in dados:
        nome = row["dimensao"]
        tipo = row["tipo"]
        valor = row["valor"]

        if nome not in agrupado:
            agrupado[nome] = {"tipo": tipo, "valores": []}

        agrupado[nome]["valores"].append(valor)

    dimensoes = []

    for nome, dados in agrupado.items():
        score = calcular_score_0_100(dados["valores"])
        classificacao = classificar_dimensao(score, dados["tipo"])

        dimensoes.append({
            "nome": nome,
            "tipo": dados["tipo"],
            "score": score,
            "classificacao": classificacao,
            "peso": peso_classificacao(classificacao)
        })

    return dimensoes


def calcular_ico(dimensoes):
    if not dimensoes:
        return 0, "baixa"

    total = len(dimensoes)
    soma_pesos = sum(d["peso"] for d in dimensoes)

    ico = (soma_pesos / (total * 3)) * 100
    ico = round(ico, 2)

    if ico <= 40:
        criticidade = "baixa"
    elif ico <= 70:
        criticidade = "moderada"
    else:
        criticidade = "alta"

    return ico, criticidade


# ALERTA CRITICO
def verificar_alerta_critico(resultados):
    """
    resultados = {"exigencias": 72, "chefias": 55, ...}
    """

    alto_risco = [
        nome for nome, score in resultados.items()
        if score >= 70
    ]

    quantidade_alto = len(alto_risco)

    # 🔴 Regra: 3 ou mais dimensões em alto risco
    alerta_critico = quantidade_alto >= 3

    return alerta_critico, alto_risco

# RESUMO EXECUTIVO
def gerar_resumo_executivo(ico, criticidade, resumo, alerta_critico):
    
    alto = resumo["alto"]
    moderado = resumo["moderado"]
    baixo = resumo["baixo"]

    texto = f"O Índice Geral de Risco Psicossocial (ICo) da organização é {ico}, "
    texto += f"classificado como criticidade {criticidade.lower()}. "

    texto += f"Foram identificadas {alto} dimensões em alto risco, "
    texto += f"{moderado} em nível moderado e {baixo} em nível baixo. "

    if alerta_critico:
        texto += (
            "Observa-se uma concentração relevante de dimensões em alto risco, "
            "caracterizando um cenário de alerta crítico que demanda atenção "
            "estratégica e intervenção prioritária."
        )
    else:
        texto += (
            "Não foi identificada concentração crítica de dimensões em alto risco, "
            "indicando um cenário relativamente estável, embora pontos específicos "
            "possam requerer monitoramento."
        )

    return texto

# ======================================================
# 🔹 ROTAS
# ======================================================
@app.route("/admin")
def admin():
    conn = get_db()
    empresas = conn.execute("SELECT * FROM empresas").fetchall()
    conn.close()

    return render_template("admin.html", empresas=empresas)

# HOME → lista empresas
@app.route("/", methods=["GET", "POST"])
def home():

    conn = get_db()

    if request.method == "POST":

        nome = request.form["nome"]   # ← corrigido
        limite = request.form["limite_respostas"]

        empresa_id = str(uuid.uuid4())[:8]

        conn.execute("""
            INSERT INTO empresas (id, nome, limite_respostas)
            VALUES (?, ?, ?)
        """, (empresa_id, nome, limite))

        conn.commit()
        conn.close()

        return redirect(url_for("home"))

    empresas = conn.execute("SELECT * FROM empresas").fetchall()
    conn.close()

    return render_template("admin.html", empresas=empresas)


# CRIAR EMPRESA
@app.route("/criar_empresa", methods=["GET", "POST"])
def criar_empresa():

    if request.method == "POST":

        nome = request.form["nome"]
        limite_respostas = request.form["limite_respostas"]

        conn = get_db()
        conn.execute("""
            INSERT INTO empresas (id, nome, limite_respostas)
            VALUES (?, ?, ?)
        """, (
            str(uuid.uuid4())[:8],
            nome,
            limite_respostas
        ))
        conn.commit()
        conn.close()

        return redirect(url_for("home"))
    return render_template("nova_empresa.html")




## ABRIR QUESTIONÁRIO
@app.route("/empresa/<empresa_id>", methods=["GET", "POST"])
def questionario(empresa_id):

    conn = get_db()

    empresa = conn.execute("""
        SELECT * FROM empresas WHERE id = ?
    """, (empresa_id,)).fetchone()

    total_respostas = conn.execute("""
        SELECT COUNT(*) FROM respostas WHERE empresa_id = ?
    """, (empresa_id,)).fetchone()[0]

    respondentes = total_respostas // 41 if total_respostas else 0
    limite = empresa["limite_respostas"] if empresa["limite_respostas"] else 0

    if limite > 0 and respondentes >= limite:
        conn.close()
        return render_template("encerrado.html")

    # 🔥 SÓ EXECUTA VALIDAÇÃO E SALVAMENTO SE FOR POST
    if request.method == "POST":

        total_perguntas = 41
        erro_validacao = False

        # 🔐 VALIDAÇÃO BACK-END
        for i in range(1, total_perguntas + 1):
            if not request.form.get(f"q{i}"):
                erro_validacao = True
                break

        if erro_validacao:
            conn.close()
            return render_template(
                "questionario.html",
                empresa=empresa,
                erro_validacao=True
            )

        # 🔽 Só salva se passou na validação
        for i in range(1, 42):
            valor = request.form.get(f"q{i}")

            if valor:
                conn.execute("""
                    INSERT INTO respostas (empresa_id, pergunta, dimensao, valor)
                    VALUES (?, ?, ?, ?)
                """, (
                    empresa_id,
                    i,
                    MAPA_DIMENSOES.get(i),
                    int(valor)
                ))

        conn.commit()
        conn.close()

        return redirect(url_for("obrigado"))

    # 🔥 SE FOR GET → MOSTRA O QUESTIONÁRIO SEM ERRO
    conn.close()
    return render_template(
        "questionario.html",
        empresa=empresa,
        erro_validacao=False
    )



@app.route("/obrigado")
def obrigado():
    return render_template("obrigado.html")

# ENVIAR QUESTIONÁRIO
@app.route("/enviar_questionario/<empresa_id>", methods=["POST"])
def enviar_questionario(empresa_id):

    conn = get_db()

    # Mapeamento das perguntas por dimensão
    mapa_dimensoes = {
        "exigencias": range(1,7),
        "influencia": range(7,11),
        "apoio": range(11,17),
        "lideranca": range(17,23),
        "autoeficacia": [23],
        "satisfação": range(24,29),
        "saude_geral": [29],
        "vida_privada": range(30,32),
        "saude_mental": range(32,38),
        "assedio": range(38,42)
    }

    # Tipo da dimensão
    tipo_dimensao = {
        "exigencias": "risco",
        "saude_geral": "risco",
        "vida_privada": "risco",
        "saude_mental": "risco",
        "assedio": "risco",
        "influencia": "protecao",
        "apoio": "protecao",
        "lideranca": "protecao",
        "autoeficacia": "protecao",
        "satisfação": "protecao"
    }

    for dimensao, perguntas in mapa_dimensoes.items():

        valores = []

        for numero in perguntas:
            valor = request.form.get(f"q{numero}")
            if valor:
                valores.append(int(valor))

        if valores:
            media = sum(valores) / len(valores)

            conn.execute("""
                INSERT INTO respostas (empresa_id, dimensao, tipo, valor)
                VALUES (?, ?, ?, ?)
            """, (empresa_id, dimensao, tipo_dimensao[dimensao], media))

    conn.commit()
    conn.close()

    return redirect(url_for("dashboard", empresa_id=empresa_id))



@app.route("/dashboard/<empresa_id>")
def dashboard(empresa_id):

    conn = get_db()

    empresa = conn.execute("""
        SELECT * FROM empresas WHERE id = ?
    """, (empresa_id,)).fetchone()

    respostas = conn.execute("""
        SELECT * FROM respostas
        WHERE empresa_id = ?
    """, (empresa_id,)).fetchall()

    # ===============================
    # TOTAL DE RESPONDENTES
    # ===============================
    total_registros = len(respostas)
    respondentes = total_registros // 41 if total_registros else 0

    limite = empresa["limite_respostas"] if empresa["limite_respostas"] else 0

    # ===============================
    # TAXA DE ADESÃO
    # ===============================
    if limite > 0:
        taxa_adesao = round((respondentes / limite) * 100, 1)
    else:
        taxa_adesao = 0

    # ===============================
    # AGRUPAR DIMENSÕES
    # ===============================
    dimensoes = {}

    for r in respostas:
        dim = r["dimensao"]
        valor = r["valor"]

        if dim not in dimensoes:
            dimensoes[dim] = []

        dimensoes[dim].append(valor)

    # ===============================
    # SCORE 0–100
    # ===============================
    resultados = {}
    alto = 0
    moderado = 0
    baixo = 0

    for dim, valores in dimensoes.items():

        media = sum(valores) / len(valores)
        score = ((media - 1) / 4) * 100
        score = round(score, 1)

        resultados[dim] = score

        if score >= 70:
            alto += 1
        elif score >= 40:
            moderado += 1
        else:
            baixo += 1

    total_dimensoes = len(resultados)

    # ===============================
    # ICO
    # ===============================
    if resultados:
        ico = round(sum(resultados.values()) / total_dimensoes, 1)
    else:
        ico = 0

    # ===============================
    # CRITICIDADE BASEADA NO ICO
    # ===============================
    if ico < 40:
        criticidade = "Baixa"
    elif ico < 70:
        criticidade = "Moderada"
    else:
        criticidade = "Alta"

    # ===============================
    # RESUMO
    # ===============================
    resumo = {
        "alto": alto,
        "moderado": moderado,
        "baixo": baixo
    }

    # ===============================
    # ALERTA CRÍTICO (CONCENTRAÇÃO)
    # ===============================
    alerta_critico, dimensoes_alto_risco = verificar_alerta_critico(resultados)

    # ===============================
    # RESUMO EXECUTIVO
    # ===============================
    resumo_executivo = gerar_resumo_executivo(
        ico,
        criticidade,
        resumo,
        alerta_critico
    )
    
    conn.close()

    return render_template(
        "dashboard.html",
        empresa=empresa,
        respondentes=respondentes,
        limite=limite,
        taxa_adesao=taxa_adesao,
        resumo=resumo,
        criticidade=criticidade,
        ico=ico,
        resultados=resultados,
        alerta_critico=alerta_critico,
        dimensoes_alto_risco=dimensoes_alto_risco,
        resumo_executivo=resumo_executivo
    )

# ======================================================
# 🔹 EXECUÇÃO
# ======================================================

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
