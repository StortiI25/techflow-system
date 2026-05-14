from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from pathlib import Path
from functools import wraps
import csv
import io
import os

app = Flask(__name__)
app.secret_key = "techflow_pim_top_secret"
DB_PATH = Path("database/techflow.db")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = db()
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS usuarios(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        perfil TEXT NOT NULL DEFAULT 'funcionario',
        foto TEXT,
        criado_em TEXT NOT NULL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS clientes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT,
        telefone TEXT,
        endereco TEXT,
        criado_em TEXT NOT NULL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS produtos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        categoria TEXT,
        preco REAL NOT NULL,
        estoque INTEGER NOT NULL DEFAULT 0,
        estoque_minimo INTEGER NOT NULL DEFAULT 3,
        criado_em TEXT NOT NULL
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS vendas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        usuario_id INTEGER,
        total REAL NOT NULL,
        data_venda TEXT NOT NULL,
        FOREIGN KEY(cliente_id) REFERENCES clientes(id),
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS venda_itens(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venda_id INTEGER NOT NULL,
        produto_id INTEGER NOT NULL,
        quantidade INTEGER NOT NULL,
        preco_unitario REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY(venda_id) REFERENCES vendas(id),
        FOREIGN KEY(produto_id) REFERENCES produtos(id)
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT,
        acao TEXT NOT NULL,
        data_hora TEXT NOT NULL
    )""")

    if not cur.execute("SELECT id FROM usuarios WHERE email=?", ("admin@techflow.com",)).fetchone():
        cur.execute("INSERT INTO usuarios(nome,email,senha,perfil,criado_em) VALUES(?,?,?,?,?)",
                    ("Administrador","admin@techflow.com",generate_password_hash("admin123"),"admin",datetime.now().isoformat()))

    if not cur.execute("SELECT id FROM clientes LIMIT 1").fetchone():
        for c in [("Carlos Silva","carlos@email.com","11999990000","São Paulo"),
                  ("Ana Souza","ana@email.com","11988887777","Campinas"),
                  ("Marcos Lima","marcos@email.com","11977776666","Santos")]:
            cur.execute("INSERT INTO clientes(nome,email,telefone,endereco,criado_em) VALUES(?,?,?,?,?)", (*c, datetime.now().isoformat()))

    if not cur.execute("SELECT id FROM produtos LIMIT 1").fetchone():
        for p in [("Sistema de Controle Mensal","Software",199.90,10,3),
                  ("Consultoria de UX","Serviço",450.00,5,2),
                  ("Dashboard Analítico","Software",299.90,8,3),
                  ("Treinamento Operacional","Serviço",350.00,6,2)]:
            cur.execute("INSERT INTO produtos(nome,categoria,preco,estoque,estoque_minimo,criado_em) VALUES(?,?,?,?,?,?)", (*p, datetime.now().isoformat()))

    conn.commit()
    conn.close()

def log(acao):
    conn = db()
    conn.execute("INSERT INTO logs(usuario,acao,data_hora) VALUES(?,?,?)",
                 (session.get("usuario_nome","Sistema"), acao, datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrap

def admin_required(f):
    @wraps(f)
    def wrap(*a, **kw):
        if session.get("usuario_perfil") != "admin":
            flash("Acesso permitido apenas para administrador.", "danger")
            return redirect(url_for("dashboard"))
        return f(*a, **kw)
    return wrap

@app.context_processor
def inject():
    return {"usuario_nome": session.get("usuario_nome"), "usuario_perfil": session.get("usuario_perfil")}

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        conn = db()
        user = conn.execute("SELECT * FROM usuarios WHERE email=?", (request.form["email"].lower(),)).fetchone()
        conn.close()
        if user and check_password_hash(user["senha"], request.form["senha"]):
            session["usuario_id"], session["usuario_nome"], session["usuario_perfil"] = user["id"], user["nome"], user["perfil"]
            log("Login realizado")
            return redirect(url_for("dashboard"))
        flash("E-mail ou senha inválidos.", "danger")
    return render_template("login.html")

@app.route("/registrar", methods=["GET","POST"])
def registrar():
    if request.method == "POST":
        if not request.form.get("aceite"):
            flash("Aceite o termo de proteção de dados.", "danger")
            return redirect(url_for("registrar"))
        conn = db()
        try:
            conn.execute("INSERT INTO usuarios(nome,email,senha,perfil,criado_em) VALUES(?,?,?,?,?)",
                         (request.form["nome"], request.form["email"].lower(), generate_password_hash(request.form["senha"]), "funcionario", datetime.now().isoformat()))
            conn.commit()
            flash("Conta criada com sucesso.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("E-mail já cadastrado.", "danger")
        finally:
            conn.close()
    return render_template("registrar.html")

@app.route("/esqueci-senha", methods=["GET","POST"])
def esqueci_senha():
    if request.method == "POST":
        flash("Simulação: link de recuperação enviado.", "info")
    return render_template("esqueci_senha.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = db()
    q = {
        "clientes": conn.execute("SELECT COUNT(*) c FROM clientes").fetchone()["c"],
        "produtos": conn.execute("SELECT COUNT(*) c FROM produtos").fetchone()["c"],
        "vendas": conn.execute("SELECT COUNT(*) c FROM vendas").fetchone()["c"],
        "faturamento": conn.execute("SELECT COALESCE(SUM(total),0) t FROM vendas").fetchone()["t"],
        "estoque_baixo": conn.execute("SELECT * FROM produtos WHERE estoque <= estoque_minimo ORDER BY estoque ASC").fetchall(),
        "logs": conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 5").fetchall()
    }
    conn.close()
    return render_template("dashboard.html", **q)

@app.route("/clientes", methods=["GET","POST"])
@login_required
def clientes():
    conn = db()
    if request.method == "POST":
        conn.execute("INSERT INTO clientes(nome,email,telefone,endereco,criado_em) VALUES(?,?,?,?,?)",
                     (request.form["nome"],request.form["email"],request.form["telefone"],request.form["endereco"],datetime.now().isoformat()))
        conn.commit(); conn.close(); log("Cadastrou cliente")
        flash("Cliente cadastrado.", "success")
        return redirect(url_for("clientes"))
    busca = request.args.get("q","")
    rows = conn.execute("SELECT * FROM clientes WHERE nome LIKE ? OR email LIKE ? ORDER BY id DESC", (f"%{busca}%",f"%{busca}%")).fetchall()
    conn.close()
    return render_template("clientes.html", clientes=rows, busca=busca)

@app.route("/clientes/editar/<int:id>", methods=["GET","POST"])
@login_required
def editar_cliente(id):
    conn = db()
    if request.method == "POST":
        conn.execute("UPDATE clientes SET nome=?,email=?,telefone=?,endereco=? WHERE id=?",
                     (request.form["nome"],request.form["email"],request.form["telefone"],request.form["endereco"],id))
        conn.commit(); conn.close(); log("Editou cliente")
        flash("Cliente atualizado.", "success")
        return redirect(url_for("clientes"))
    row = conn.execute("SELECT * FROM clientes WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("editar_cliente.html", c=row)

@app.route("/clientes/excluir/<int:id>")
@login_required
@admin_required
def excluir_cliente(id):
    conn=db(); conn.execute("DELETE FROM clientes WHERE id=?", (id,)); conn.commit(); conn.close(); log("Excluiu cliente")
    flash("Cliente excluído.", "success")
    return redirect(url_for("clientes"))

@app.route("/produtos", methods=["GET","POST"])
@login_required
def produtos():
    conn=db()
    if request.method=="POST":
        conn.execute("INSERT INTO produtos(nome,categoria,preco,estoque,estoque_minimo,criado_em) VALUES(?,?,?,?,?,?)",
                     (request.form["nome"],request.form["categoria"],float(request.form["preco"]),int(request.form["estoque"]),int(request.form["estoque_minimo"]),datetime.now().isoformat()))
        conn.commit(); conn.close(); log("Cadastrou produto")
        flash("Produto cadastrado.", "success")
        return redirect(url_for("produtos"))
    busca=request.args.get("q","")
    rows=conn.execute("SELECT * FROM produtos WHERE nome LIKE ? OR categoria LIKE ? ORDER BY id DESC", (f"%{busca}%",f"%{busca}%")).fetchall()
    conn.close()
    return render_template("produtos.html", produtos=rows, busca=busca)

@app.route("/produtos/editar/<int:id>", methods=["GET","POST"])
@login_required
def editar_produto(id):
    conn=db()
    if request.method=="POST":
        conn.execute("UPDATE produtos SET nome=?,categoria=?,preco=?,estoque=?,estoque_minimo=? WHERE id=?",
                     (request.form["nome"],request.form["categoria"],float(request.form["preco"]),int(request.form["estoque"]),int(request.form["estoque_minimo"]),id))
        conn.commit(); conn.close(); log("Editou produto")
        flash("Produto atualizado.", "success")
        return redirect(url_for("produtos"))
    row=conn.execute("SELECT * FROM produtos WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("editar_produto.html", p=row)

@app.route("/produtos/excluir/<int:id>")
@login_required
@admin_required
def excluir_produto(id):
    conn=db(); conn.execute("DELETE FROM produtos WHERE id=?", (id,)); conn.commit(); conn.close(); log("Excluiu produto")
    flash("Produto excluído.", "success")
    return redirect(url_for("produtos"))

@app.route("/vendas", methods=["GET","POST"])
@login_required
def vendas():
    conn=db()
    if request.method=="POST":
        cliente_id=request.form["cliente_id"]
        produtos=request.form.getlist("produto_id")
        quantidades=request.form.getlist("quantidade")
        total=0
        itens=[]
        for pid,qtd in zip(produtos,quantidades):
            if pid and qtd and int(qtd)>0:
                prod=conn.execute("SELECT * FROM produtos WHERE id=?", (pid,)).fetchone()
                subtotal=prod["preco"]*int(qtd)
                total+=subtotal
                itens.append((pid,int(qtd),prod["preco"],subtotal))
        if not itens:
            flash("Adicione pelo menos um item.", "danger")
            return redirect(url_for("vendas"))
        cur=conn.execute("INSERT INTO vendas(cliente_id,usuario_id,total,data_venda) VALUES(?,?,?,?)",
                         (cliente_id,session["usuario_id"],total,datetime.now().strftime("%Y-%m-%d")))
        venda_id=cur.lastrowid
        for pid,qtd,preco,subtotal in itens:
            conn.execute("INSERT INTO venda_itens(venda_id,produto_id,quantidade,preco_unitario,subtotal) VALUES(?,?,?,?,?)",
                         (venda_id,pid,qtd,preco,subtotal))
            conn.execute("UPDATE produtos SET estoque=estoque-? WHERE id=?", (qtd,pid))
        conn.commit(); conn.close(); log("Registrou venda com carrinho")
        flash("Venda registrada.", "success")
        return redirect(url_for("vendas"))
    clientes=conn.execute("SELECT * FROM clientes ORDER BY nome").fetchall()
    produtos=conn.execute("SELECT * FROM produtos ORDER BY nome").fetchall()
    vendas=conn.execute("""SELECT vendas.*, clientes.nome cliente FROM vendas LEFT JOIN clientes ON clientes.id=vendas.cliente_id ORDER BY vendas.id DESC""").fetchall()
    conn.close()
    return render_template("vendas.html", clientes=clientes, produtos=produtos, vendas=vendas)

@app.route("/relatorios")
@login_required
def relatorios():
    conn=db()
    vendas=conn.execute("""SELECT vendas.*, clientes.nome cliente FROM vendas LEFT JOIN clientes ON clientes.id=vendas.cliente_id ORDER BY vendas.id DESC""").fetchall()
    conn.close()
    return render_template("relatorios.html", vendas=vendas)

@app.route("/relatorios/csv")
@login_required
def export_csv():
    conn=db()
    rows=conn.execute("""SELECT vendas.id, clientes.nome cliente, vendas.total, vendas.data_venda FROM vendas LEFT JOIN clientes ON clientes.id=vendas.cliente_id""").fetchall()
    conn.close()
    output=io.StringIO()
    writer=csv.writer(output)
    writer.writerow(["ID","Cliente","Total","Data"])
    for r in rows: writer.writerow([r["id"],r["cliente"],r["total"],r["data_venda"]])
    resp=make_response(output.getvalue())
    resp.headers["Content-Disposition"]="attachment; filename=relatorio_vendas.csv"
    resp.headers["Content-Type"]="text/csv"
    return resp

@app.route("/usuarios", methods=["GET","POST"])
@login_required
@admin_required
def usuarios():
    conn=db()
    if request.method=="POST":
        conn.execute("INSERT INTO usuarios(nome,email,senha,perfil,criado_em) VALUES(?,?,?,?,?)",
                     (request.form["nome"],request.form["email"].lower(),generate_password_hash(request.form["senha"]),request.form["perfil"],datetime.now().isoformat()))
        conn.commit(); log("Cadastrou usuário")
    rows=conn.execute("SELECT id,nome,email,perfil,criado_em FROM usuarios ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("usuarios.html", usuarios=rows)

@app.route("/perfil", methods=["GET","POST"])
@login_required
def perfil():
    conn=db()
    user=conn.execute("SELECT * FROM usuarios WHERE id=?", (session["usuario_id"],)).fetchone()
    if request.method=="POST":
        nome=request.form["nome"]
        senha=request.form.get("senha","")
        if senha:
            conn.execute("UPDATE usuarios SET nome=?, senha=? WHERE id=?", (nome,generate_password_hash(senha),session["usuario_id"]))
        else:
            conn.execute("UPDATE usuarios SET nome=? WHERE id=?", (nome,session["usuario_id"]))
        conn.commit(); conn.close()
        session["usuario_nome"]=nome
        log("Atualizou perfil")
        flash("Perfil atualizado.", "success")
        return redirect(url_for("perfil"))
    conn.close()
    return render_template("perfil.html", user=user)

@app.route("/logs")
@login_required
@admin_required
def logs():
    conn=db()
    rows=conn.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 100").fetchall()
    conn.close()
    return render_template("logs.html", logs=rows)

@app.route("/sobre")
@login_required
def sobre():
    return render_template("sobre.html")

@app.route("/api/dashboard")
@login_required
def api_dashboard():
    conn=db()
    vendas=conn.execute("SELECT data_venda, SUM(total) total FROM vendas GROUP BY data_venda ORDER BY data_venda").fetchall()
    produtos=conn.execute("""SELECT produtos.nome, COALESCE(SUM(venda_itens.quantidade),0) qtd
    FROM produtos LEFT JOIN venda_itens ON venda_itens.produto_id=produtos.id GROUP BY produtos.id ORDER BY qtd DESC LIMIT 6""").fetchall()
    categorias=conn.execute("""SELECT categoria, COUNT(*) qtd FROM produtos GROUP BY categoria""").fetchall()
    conn.close()
    return jsonify({
        "vendas_labels":[r["data_venda"] for r in vendas] or ["01","02","03","04","05","06"],
        "vendas_valores":[r["total"] for r in vendas] or [0,0,0,0,0,0],
        "produtos_labels":[r["nome"] for r in produtos],
        "produtos_valores":[r["qtd"] for r in produtos],
        "cat_labels":[r["categoria"] or "Outros" for r in categorias],
        "cat_valores":[r["qtd"] for r in categorias]
    })


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
