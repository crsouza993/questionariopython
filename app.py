import sqlite3
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)
DATABASE = "copsoq.db"

# =====================================================
# CONEXÃO
# =====================================================
def conectar():
    return sqlite3.connect(DATABASE)


# =====================================================
# BANCO
# =====================================================
def inicializar_banco():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            data_criacao TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS respostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            pergunta INTEGER NOT NULL,
            resposta INTEGER NOT NULL,
            data_hora TEXT NOT NULL,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS mapeamento_copsoq (
            pergunta INTEGER PRIMARY KEY,
            subescala TEXT NOT NULL,
            nome_subescala TEXT NOT NULL
        )
    """)

    c.execute("""
        INSERT OR IGNORE INTO mapeamento_copsoq (pergunta, subescala, nome_subescala) VALUES
        (1,'exigencias_quantitativas','Exigências quantitativas'),
        (2,'ritmo_trabalho','Ritmo de trabalho'),
        (3,'exigencias_cognitivas','Exigências cognitivas'),
        (4,'exigencias_emocionais','Exigências emocionais'),
        (5,'exigencias_cognitivas','Exigências cognitivas'),
        (6,'exigencias_emocionais','Exigências emocionais'),
        (7,'influencia_trabalho','Influência no trabalho'),
        (8,'influencia_trabalho','Influência no trabalho'),
        (9,'desenvolvimento','Possibilidades de desenvolvimento'),
        (10,'previsibilidade','Previsibilidade'),
        (11,'reconhecimento','Reconhecimento'),
        (12,'clareza_papeis','Clareza de papéis'),
        (13,'reconhecimento','Reconhecimento'),
        (14,'justica','Justiça'),
        (15,'apoio_superior','Apoio social do superior'),
        (16,'apoio_colegas','Apoio social de colegas'),
        (17,'qualidade_lideranca','Qualidade da liderança'),
        (18,'qualidade_lideranca','Qualidade da liderança'),
        (19,'confianca_gestao','Confiança na gestão'),
        (20,'confianca_gestao','Confiança na gestão'),
        (21,'justica','Justiça'),
        (22,'organizacao_trabalho','Organização do trabalho'),
        (23,'autoeficacia','Autoeficácia'),
        (24,'sentido_trabalho','Sentido do trabalho'),
        (25,'sentido_trabalho','Sentido do trabalho'),
        (26,'comprometimento','Comprometimento com o trabalho'),
        (27,'satisfacao_trabalho','Satisfação no trabalho'),
        (28,'inseguranca_emprego','Insegurança no emprego'),
        (29,'saude_geral','Saúde geral'),
        (30,'conflito_trabalho_familia','Conflito trabalho-família'),
        (31,'conflito_trabalho_familia','Conflito trabalho-família'),
        (32,'problemas_sono','Problemas de sono'),
        (33,'exaustao_fisica','Exaustão física'),
        (34,'exaustao_emocional','Exaustão emocional'),
        (35,'irritabilidade','Irritabilidade'),
        (36,'ansiedade','Ansiedade'),
        (37,'depressao','Depressão'),
        (38,'assedio_moral','Assédio moral'),
        (39,'assedio_sexual','Assédio sexual'),
        (40,'ameaca_violencia','Ameaça de violência'),
        (41,'violencia_fisica','Violência física')
    """)

    conn.commit()
    conn.close()


inicializar_banco()


# =====================================================
# REGRAS
# =====================================================
def interpretar_risco(media):
    if media <= 2:
        return "Baixo risco"
    elif media <= 3.5:
        return "Risco moderado"
    return "Alto risco"


# =====================================================
# SERVICE – CORREÇÃO
# =====================================================
def gerar_correcao(empresa_id):
    conn = conectar()
    c = conn.cursor()

    c.execute("""
        SELECT 
            m.nome_subescala,
            ROUND(AVG(r.resposta), 2) AS media
        FROM respostas r
        JOIN mapeamento_copsoq m ON r.pergunta = m.pergunta
        WHERE r.empresa_id = ?
        GROUP BY m.nome_subescala
        ORDER BY MIN(m.pergunta)
    """, (empresa_id,))

    dados = c.fetchall()
    conn.close()

    tabela = []
    for nome, media in dados:
        tabela.append({
            "subescala": nome,
            "media": media,
            "risco": interpretar_risco(media)
        })

    return tabela



# =====================================================
# ROTAS
# =====================================================

# ADMIN – criar empresas e pegar linksimport uuid
@app.route("/admin", methods=["GET", "POST"])
def admin():
    conn = conectar()
    c = conn.cursor()

    erro = None

    if request.method == "POST":
        nome = request.form["nome"].strip()

        # 🔍 verifica se empresa já existe
        c.execute("SELECT id FROM empresas WHERE nome = ?", (nome,))
        empresa_existente = c.fetchone()

        if empresa_existente:
            erro = "Empresa já cadastrada"
        else:
            token = uuid.uuid4().hex[:8]
            data = datetime.now().isoformat()

            c.execute("""
                INSERT INTO empresas (nome, token, data_criacao)
                VALUES (?, ?, ?)
            """, (nome, token, data))

            conn.commit()

    c.execute("SELECT id, nome, token FROM empresas")
    empresas = c.fetchall()

    conn.close()
    return render_template("admin.html", empresas=empresas, erro=erro)

# EXCLUIR EMPRESA
@app.route("/admin/excluir/<int:empresa_id>", methods=["POST"])
def excluir_empresa(empresa_id):
    conn = conectar()
    c = conn.cursor()

    # 1️⃣ apagar respostas da empresa
    c.execute("DELETE FROM respostas WHERE empresa_id = ?", (empresa_id,))

    # 2️⃣ apagar a empresa
    c.execute("DELETE FROM empresas WHERE id = ?", (empresa_id,))

    conn.commit()
    conn.close()

    return redirect(url_for("admin"))

# QUESTIONÁRIO POR EMPRESA
@app.route("/q/<token>", methods=["GET", "POST"])
def questionario_empresa(token):
    conn = conectar()
    c = conn.cursor()

    # busca empresa existente
    c.execute("SELECT id, nome FROM empresas WHERE token = ?", (token,))
    empresa = c.fetchone()

    if not empresa:
        return "Empresa não encontrada", 404

    empresa_id = empresa[0]

    if request.method == "POST":
        for i in range(1, 42):
            resposta = request.form.get(f"q{i}")
            if resposta:
                c.execute("""
                    INSERT INTO respostas (empresa_id, pergunta, resposta, data_hora)
                    VALUES (?, ?, ?, datetime('now'))
                """, (empresa_id, i, int(resposta)))

        conn.commit()
        conn.close()
        return render_template("obrigado.html")

    conn.close()
    return render_template("questionario.html", empresa=empresa)

# DASHBOARD
@app.route("/dashboard/<int:empresa_id>")
def dashboard(empresa_id):
    tabela = gerar_correcao(empresa_id)

    if not tabela:
        return "Sem dados para esta empresa", 404

    resumo = gerar_resumo(tabela)

    return render_template(
        "dashboard.html",
        tabela=tabela,
        resumo=resumo
    )



# CORREÇÃO POR EMPRESA
#@app.route("/correcao/<int:empresa_id>")
#def correcao(empresa_id):
 #   tabela = gerar_correcao(empresa_id)
  #  resumo = gerar_resumo(tabela)

   # return render_template(
    #    "dashboard.html",
     #   tabela=tabela,
      #  resumo=resumo
    #)


def gerar_resumo(tabela):
    total_subescalas = len(tabela)

    media_geral = round(
        sum(item["media"] for item in tabela) / total_subescalas, 2
    ) if total_subescalas > 0 else 0

    if media_geral <= 2:
        risco_geral = "Baixo risco"
    elif media_geral <= 3.5:
        risco_geral = "Risco moderado"
    else:
        risco_geral = "Alto risco"

    return {
        "total_subescalas": total_subescalas,
        "media_geral": media_geral,
        "risco_geral": risco_geral
    }


@app.route("/obrigado")
def obrigado():
    return "<h2>Obrigado! Questionário enviado com sucesso.</h2>"


# =====================================================
# START
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)
