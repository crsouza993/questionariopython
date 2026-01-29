from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime
import matplotlib.pyplot as plt
import os

app = Flask(__name__)

# -------------------------
# BANCO
# -------------------------
def conectar():
    return sqlite3.connect("database.db")

def criar_banco():
    conn = conectar()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            codigo TEXT UNIQUE,
            ativa INTEGER DEFAULT 1
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS respostas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER,
            pergunta INTEGER,
            resposta INTEGER,
            data_resposta TEXT
        )
    """)

    conn.commit()
    conn.close()

criar_banco()

# -------------------------
# CADASTRO DE EMPRESAS (ADMIN)
# -------------------------
@app.route("/empresas", methods=["GET", "POST"])
def empresas():
    conn = conectar()
    c = conn.cursor()

    if request.method == "POST":
        nome = request.form["nome"]
        codigo = request.form["codigo"]
        c.execute("INSERT INTO empresas (nome, codigo) VALUES (?,?)", (nome, codigo))
        conn.commit()

    c.execute("SELECT * FROM empresas")
    empresas = c.fetchall()
    conn.close()

    return render_template("empresas.html", empresas=empresas)

# -------------------------
# QUESTIONÁRIO POR EMPRESA
# -------------------------
@app.route("/questionario/<codigo_empresa>", methods=["GET", "POST"])
def questionario(codigo_empresa):
    conn = conectar()
    c = conn.cursor()

    c.execute("SELECT id, nome FROM empresas WHERE codigo=? AND ativa=1", (codigo_empresa,))
    empresa = c.fetchone()

    if not empresa:
        return "Empresa não encontrada ou inativa", 404

    empresa_id, nome_empresa = empresa

    if request.method == "POST":
        for i in range(1, 11):
            resposta = request.form.get(f"q{i}")
            c.execute("""
                INSERT INTO respostas (empresa_id, pergunta, resposta, data_resposta)
                VALUES (?,?,?,?)
            """, (empresa_id, i, resposta, datetime.now()))
        conn.commit()
        conn.close()
        return redirect("/obrigado")

    conn.close()
    return render_template("questionario.html", empresa=nome_empresa)

@app.route("/obrigado")
def obrigado():
    return render_template("obrigado.html")

# -------------------------
# PAINEL POR EMPRESA
# -------------------------
@app.route("/painel/<codigo_empresa>")
def painel(codigo_empresa):
    conn = conectar()
    c = conn.cursor()

    c.execute("SELECT id, nome FROM empresas WHERE codigo=?", (codigo_empresa,))
    empresa = c.fetchone()
    if not empresa:
        return "Empresa não encontrada", 404

    empresa_id, nome_empresa = empresa

    blocos = {
        "Carga de Trabalho": [1, 2],
        "Liderança": [3, 4],
        "Clima Organizacional": [5, 6],
        "Reconhecimento": [7, 8],
        "Equilíbrio Vida-Trabalho": [9, 10]
    }

    resultados = {}

    for bloco, perguntas in blocos.items():
        c.execute(f"""
            SELECT COUNT(*),
                   SUM(CASE WHEN resposta >= 4 THEN 1 ELSE 0 END)
            FROM respostas
            WHERE empresa_id=? AND pergunta IN ({','.join(map(str, perguntas))})
        """, (empresa_id,))
        total, positivas = c.fetchone()
        resultados[bloco] = round((positivas / total) * 100, 1) if total else 0

    conn.close()
    gerar_grafico(resultados)

    return render_template("painel.html",
                           resultados=resultados,
                           empresa=nome_empresa)

# -------------------------
# GRÁFICO
# -------------------------
def gerar_grafico(resultados):
    plt.figure()
    plt.bar(resultados.keys(), resultados.values())
    plt.ylabel("Respostas positivas (%)")
    plt.title("Avaliação Psicossocial")
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig("static/grafico.png")
    plt.close()

# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
