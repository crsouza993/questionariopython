import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

DATABASE = "copsoq.db"

# -------------------------
# CONEXÃO
# -------------------------
def conectar():
    return sqlite3.connect(DATABASE)

# -------------------------
# CRIAÇÃO DO BANCO
# -------------------------
def inicializar_banco():
    conn = conectar()
    c = conn.cursor()

    # -------------------------
    # TABELA DE EMPRESAS
    # -------------------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            data_criacao TEXT NOT NULL
        )
    """)

    # -------------------------
    # TABELA DE RESPOSTAS
    # -------------------------
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

    # -------------------------
    # TABELA DE MAPEAMENTO COPSOQ
    # -------------------------
    c.execute("""
        CREATE TABLE IF NOT EXISTS mapeamento_copsoq (
            pergunta INTEGER PRIMARY KEY,
            subescala TEXT NOT NULL,
            nome_subescala TEXT NOT NULL
        )
    """)

    # Inserção do mapeamento (executa só uma vez)
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

# -------------------------
# REGRAS
# -------------------------
def interpretar_risco(media):
    if media <= 2:
        return "Baixo risco"
    elif media <= 3.5:
        return "Risco moderado"
    else:
        return "Alto risco"

ESCALA_SAUDE = {
    5: "Excelente",
    4: "Muito boa",
    3: "Boa",
    2: "Razoável",
    1: "Deficitária"
}

# -------------------------
# CORREÇÃO
# -------------------------
def gerar_correcao():
    conn = conectar()
    c = conn.cursor()

    # Média geral por subescala
    c.execute("""
        SELECT 
            m.subescala,
            m.nome_subescala,
            ROUND(AVG(r.resposta), 2) AS media
        FROM respostas r
        JOIN mapeamento_copsoq m ON r.pergunta = m.pergunta
        GROUP BY m.subescala, m.nome_subescala
    """)

    medias = {
        row[0]: {
            "nome": row[1],
            "media": row[2],
            "risco": interpretar_risco(row[2])
        }
        for row in c.fetchall()
    }

    # Lista de perguntas em ordem
    c.execute("""
        SELECT 
            m.subescala,
            m.nome_subescala,
            m.pergunta
        FROM mapeamento_copsoq m
        ORDER BY m.pergunta
    """)

    perguntas = c.fetchall()
    conn.close()

    tabela_final = []

    for subescala, nome, pergunta in perguntas:
        if subescala in medias:
            tabela_final.append({
                "subescala": nome,
                "pergunta": pergunta,
                "media": medias[subescala]["media"],
                "risco": medias[subescala]["risco"]
            })

    return tabela_final



# -------------------------
# ROTAS
# -------------------------
@app.route("/", methods=["GET", "POST"])
def questionario():
    if request.method == "POST":
        conn = conectar()
        c = conn.cursor()

        for i in range(1, 42):
            resposta = request.form.get(f"q{i}")
            if resposta:
                c.execute("""
                    INSERT INTO respostas (pergunta, resposta, data_hora)
                    VALUES (?, ?, ?)
                """, (i, int(resposta), datetime.now().isoformat()))

        conn.commit()
        conn.close()
        return redirect(url_for("obrigado"))

    return render_template("questionario.html")

@app.route("/correcao")
def correcao():
    tabela = gerar_correcao()
    return render_template("correcao.html", tabela=tabela)

@app.route("/obrigado")
def obrigado():
    return "<h2>Obrigado! Questionário enviado com sucesso.</h2>"

# -------------------------
# START
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
