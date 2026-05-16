from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from pathlib import Path
from datetime import datetime, date, timedelta
import sqlite3
import csv
import io
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "estoqueflow_secret_dev")
DB_PATH = Path("database/estoqueflow.db")

def get_db():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def now_br():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def today_iso():
    return date.today().isoformat()

def log_action(acao, produto_id=None, produto_nome=None):
    conn = get_db()
    conn.execute(
        "INSERT INTO logs(usuario_id, usuario_nome, acao, produto_id, produto_nome, data_hora) VALUES(?,?,?,?,?,?)",
        (session.get("usuario_id"), session.get("usuario_nome", "Sistema"), acao, produto_id, produto_nome, now_br())
    )
    conn.commit()
    conn.close()

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("usuario_perfil") != "admin":
            flash("Acesso permitido apenas para administrador.", "danger")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_global():
    return {
        "usuario_nome": session.get("usuario_nome"),
        "usuario_perfil": session.get("usuario_perfil"),
        "request": request
    }

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        senha TEXT NOT NULL,
        perfil TEXT NOT NULL DEFAULT 'funcionario',
        tema TEXT DEFAULT 'dark',
        notificacoes TEXT DEFAULT 'sim',
        criado_em TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS clientes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT,
        telefone TEXT,
        endereco TEXT,
        criado_em TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS produtos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo_barras TEXT UNIQUE,
        nome TEXT NOT NULL,
        categoria TEXT,
        preco_custo REAL NOT NULL DEFAULT 0,
        preco_venda REAL NOT NULL DEFAULT 0,
        estoque INTEGER NOT NULL DEFAULT 0,
        estoque_minimo INTEGER NOT NULL DEFAULT 3,
        criado_em TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS movimentacoes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produto_id INTEGER NOT NULL,
        cliente_id INTEGER,
        usuario_id INTEGER,
        tipo TEXT NOT NULL,
        motivo TEXT NOT NULL,
        quantidade INTEGER NOT NULL,
        valor_unitario REAL NOT NULL,
        valor_total REAL NOT NULL,
        data_movimentacao TEXT NOT NULL,
        observacao TEXT,
        FOREIGN KEY(produto_id) REFERENCES produtos(id),
        FOREIGN KEY(cliente_id) REFERENCES clientes(id),
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        usuario_nome TEXT,
        acao TEXT NOT NULL,
        produto_id INTEGER,
        produto_nome TEXT,
        data_hora TEXT NOT NULL
    )
    """)

    if not cur.execute("SELECT id FROM usuarios WHERE email=?", ("admin@estoqueflow.com",)).fetchone():
        cur.execute("INSERT INTO usuarios(nome,email,senha,perfil,criado_em) VALUES(?,?,?,?,?)",
                    ("Administrador", "admin@estoqueflow.com", generate_password_hash("admin123"), "admin", now_br()))

    if not cur.execute("SELECT id FROM clientes LIMIT 1").fetchone():
        clientes = [
            ("Mercado Central LTDA", "contato@mercadocentral.com", "1132458899", "São Paulo"),
            ("TechNova Soluções", "financeiro@technova.com", "11987654321", "Campinas"),
            ("Alpha Distribuidora", "vendas@alphadistribuidora.com", "1140028922", "Guarulhos"),
            ("Loja Prime Imports", "contato@primeimports.com", "11999887766", "Santos"),
            ("Digital Max Comércio", "suporte@digitalmax.com", "1130304040", "Sorocaba")
        ]
        for c in clientes:
            cur.execute("INSERT INTO clientes(nome,email,telefone,endereco,criado_em) VALUES(?,?,?,?,?)", (*c, now_br()))

    if not cur.execute("SELECT id FROM produtos LIMIT 1").fetchone():
        produtos = [
            ("7891000000011", "Notebook Dell Inspiron 15", "Informática", 3000.00, 3899.90, 12, 3),
            ("7891000000028", "Monitor LG UltraWide 29", "Periféricos", 900.00, 1299.90, 8, 2),
            ("7891000000035", "Teclado Mecânico Redragon", "Periféricos", 150.00, 249.90, 20, 5),
            ("7891000000042", "Mouse Logitech G203", "Periféricos", 90.00, 159.90, 18, 5),
            ("7891000000059", "SSD Kingston 1TB", "Hardware", 350.00, 499.90, 14, 4),
            ("7891000000066", "Memória RAM Corsair 16GB", "Hardware", 230.00, 329.90, 10, 3),
            ("7891000000073", "Impressora Epson EcoTank", "Escritório", 850.00, 1199.90, 6, 2),
            ("7891000000080", "Cadeira Gamer ThunderX3", "Móveis", 620.00, 899.90, 5, 2)
        ]
        for p in produtos:
            cur.execute("""
                INSERT INTO produtos(codigo_barras,nome,categoria,preco_custo,preco_venda,estoque,estoque_minimo,criado_em)
                VALUES(?,?,?,?,?,?,?,?)
            """, (*p, now_br()))

    if not cur.execute("SELECT id FROM movimentacoes LIMIT 1").fetchone():
        movs = [
            (1, 1, "saida", "Venda", 1, "2026-05-10"),
            (2, 1, "saida", "Venda", 1, "2026-05-10"),
            (3, 2, "saida", "Venda", 2, "2026-05-11"),
            (4, 2, "saida", "Uso Interno", 3, "2026-05-11"),
            (5, 3, "entrada", "Compra de Fornecedor", 5, "2026-05-12"),
            (6, 3, "saida", "Venda", 1, "2026-05-12"),
            (7, 4, "saida", "Venda", 1, "2026-05-13"),
            (8, 5, "saida", "Produto Defeituoso", 1, "2026-05-14")
        ]
        for produto_id, cliente_id, tipo, motivo, quantidade, data_mov in movs:
            produto = cur.execute("SELECT * FROM produtos WHERE id=?", (produto_id,)).fetchone()
            valor = produto["preco_venda"] if tipo == "saida" else produto["preco_custo"]
            total = valor * quantidade
            cur.execute("""
                INSERT INTO movimentacoes(produto_id,cliente_id,usuario_id,tipo,motivo,quantidade,valor_unitario,valor_total,data_movimentacao,observacao)
                VALUES(?,?,?,?,?,?,?,?,?,?)
            """, (produto_id, cliente_id, 1, tipo, motivo, quantidade, valor, total, data_mov, "Movimentação inicial"))
            if tipo == "saida":
                cur.execute("UPDATE produtos SET estoque=estoque-? WHERE id=?", (quantidade, produto_id))
            else:
                cur.execute("UPDATE produtos SET estoque=estoque+? WHERE id=?", (quantidade, produto_id))

    if not cur.execute("SELECT id FROM logs LIMIT 1").fetchone():
        for acao in ["Sistema inicializado", "Clientes empresariais cadastrados", "Produtos reais importados", "Movimentações iniciais geradas"]:
            cur.execute("INSERT INTO logs(usuario_id,usuario_nome,acao,produto_id,produto_nome,data_hora) VALUES(?,?,?,?,?,?)",
                        (1, "Administrador", acao, None, None, now_br()))

    conn.commit()
    conn.close()

@app.route("/")
def home():
    if "usuario_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("home.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        senha = request.form.get("senha", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM usuarios WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["senha"], senha):
            session["usuario_id"] = user["id"]
            session["usuario_nome"] = user["nome"]
            session["usuario_email"] = user["email"]
            session["usuario_perfil"] = user["perfil"]
            log_action("Login realizado")
            return redirect(url_for("dashboard"))
        flash("E-mail ou senha inválidos.", "danger")
    return render_template("login.html")

@app.route("/registrar", methods=["GET", "POST"])
def registrar():
    if request.method == "POST":
        if not request.form.get("aceite"):
            flash("Aceite os termos de proteção de dados.", "danger")
            return redirect(url_for("registrar"))
        conn = get_db()
        try:
            conn.execute("INSERT INTO usuarios(nome,email,senha,perfil,criado_em) VALUES(?,?,?,?,?)",
                         (request.form["nome"], request.form["email"].lower(), generate_password_hash(request.form["senha"]), "funcionario", now_br()))
            conn.commit()
            flash("Conta criada com sucesso.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("E-mail já cadastrado.", "danger")
        finally:
            conn.close()
    return render_template("registrar.html")

@app.route("/logout")
def logout():
    if "usuario_id" in session:
        log_action("Logout realizado")
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    total_itens = conn.execute("SELECT COALESCE(SUM(estoque),0) total FROM produtos").fetchone()["total"]
    valor_estoque = conn.execute("SELECT COALESCE(SUM(estoque * preco_custo),0) total FROM produtos").fetchone()["total"]
    criticos = conn.execute("SELECT COUNT(*) total FROM produtos WHERE estoque <= estoque_minimo").fetchone()["total"]
    saidas_hoje = conn.execute("SELECT COALESCE(SUM(quantidade),0) total FROM movimentacoes WHERE tipo='saida' AND data_movimentacao=?", (today_iso(),)).fetchone()["total"]
    ultimas = conn.execute("""
        SELECT m.*, p.nome produto, c.nome cliente, u.nome usuario
        FROM movimentacoes m
        JOIN produtos p ON p.id=m.produto_id
        LEFT JOIN clientes c ON c.id=m.cliente_id
        LEFT JOIN usuarios u ON u.id=m.usuario_id
        ORDER BY m.id DESC LIMIT 5
    """).fetchall()
    estoque_baixo = conn.execute("SELECT * FROM produtos WHERE estoque <= estoque_minimo ORDER BY estoque ASC LIMIT 5").fetchall()
    conn.close()
    return render_template("dashboard.html", total_itens=total_itens, valor_estoque=valor_estoque, criticos=criticos, saidas_hoje=saidas_hoje, ultimas=ultimas, estoque_baixo=estoque_baixo)

@app.route("/api/dashboard")
@login_required
def api_dashboard():
    conn = get_db()
    inicio = date.today() - timedelta(days=6)
    dias = [(inicio + timedelta(days=i)).isoformat() for i in range(7)]
    entradas, saidas = [], []
    for d in dias:
        entradas.append(conn.execute("SELECT COALESCE(SUM(quantidade),0) t FROM movimentacoes WHERE tipo='entrada' AND data_movimentacao=?", (d,)).fetchone()["t"])
        saidas.append(conn.execute("SELECT COALESCE(SUM(quantidade),0) t FROM movimentacoes WHERE tipo='saida' AND data_movimentacao=?", (d,)).fetchone()["t"])
    vendidos = conn.execute("""
        SELECT p.nome, COALESCE(SUM(m.quantidade),0) qtd
        FROM produtos p
        LEFT JOIN movimentacoes m ON m.produto_id=p.id AND m.tipo='saida' AND m.motivo='Venda'
        GROUP BY p.id ORDER BY qtd DESC LIMIT 6
    """).fetchall()
    conn.close()
    return jsonify({"dias":[d[5:] for d in dias], "entradas":entradas, "saidas":saidas, "vendidos_labels":[r["nome"] for r in vendidos], "vendidos_valores":[r["qtd"] for r in vendidos]})

@app.route("/clientes", methods=["GET","POST"])
@login_required
def clientes():
    conn = get_db()

    if request.method == "POST":
        conn.execute(
            "INSERT INTO clientes(nome,email,telefone,endereco,criado_em) VALUES(?,?,?,?,?)",
            (
                request.form["nome"],
                request.form["email"],
                request.form["telefone"],
                request.form["endereco"],
                now_br()
            )
        )
        conn.commit()
        conn.close()
        log_action(f"Cliente cadastrado: {request.form['nome']}")
        return redirect(url_for("clientes"))

    busca = request.args.get("q", "")
    rows = conn.execute(
        "SELECT * FROM clientes WHERE nome LIKE ? OR email LIKE ? OR telefone LIKE ? ORDER BY id DESC",
        (f"%{busca}%", f"%{busca}%", f"%{busca}%")
    ).fetchall()

    total_clientes = conn.execute(
        "SELECT COUNT(*) total FROM clientes"
    ).fetchone()["total"]

    total_compras = conn.execute(
        "SELECT COUNT(*) total FROM movimentacoes WHERE tipo='saida'"
    ).fetchone()["total"]

    valor_total = conn.execute(
        "SELECT COALESCE(SUM(valor_total),0) total FROM movimentacoes WHERE tipo='saida'"
    ).fetchone()["total"]

    ticket_medio = valor_total / total_compras if total_compras else 0

    conn.close()

    return render_template(
        "clientes.html",
        clientes=rows,
        busca=busca,
        total_clientes=total_clientes,
        total_compras=total_compras,
        valor_total=valor_total,
        ticket_medio=ticket_medio
    )


@app.route("/clientes/<int:id>")
@login_required
def cliente_detalhe(id):
    conn = get_db()
    cliente = conn.execute("SELECT * FROM clientes WHERE id=?", (id,)).fetchone()
    movimentos = conn.execute("""
        SELECT m.*, p.nome produto FROM movimentacoes m JOIN produtos p ON p.id=m.produto_id
        WHERE m.cliente_id=? ORDER BY m.id DESC
    """, (id,)).fetchall()
    total = conn.execute("SELECT COALESCE(SUM(valor_total),0) total FROM movimentacoes WHERE cliente_id=? AND tipo='saida'", (id,)).fetchone()["total"]
    conn.close()
    return render_template("cliente_detalhe.html", cliente=cliente, movimentos=movimentos, total=total)

@app.route("/clientes/editar/<int:id>", methods=["GET","POST"])
@login_required
def editar_cliente(id):
    conn = get_db()
    if request.method == "POST":
        conn.execute("UPDATE clientes SET nome=?,email=?,telefone=?,endereco=? WHERE id=?",
                     (request.form["nome"],request.form["email"],request.form["telefone"],request.form["endereco"],id))
        conn.commit()
        conn.close()
        log_action(f"Cliente editado: {request.form['nome']}")
        return redirect(url_for("clientes"))
    c = conn.execute("SELECT * FROM clientes WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("editar_cliente.html", c=c)

@app.route("/clientes/excluir/<int:id>")
@login_required
@admin_required
def excluir_cliente(id):
    conn = get_db()
    conn.execute("DELETE FROM clientes WHERE id=?", (id,))
    conn.commit()
    conn.close()
    log_action(f"Cliente excluído: {id}")
    return redirect(url_for("clientes"))

@app.route("/produtos", methods=["GET","POST"])
@login_required
def produtos():
    conn = get_db()
    if request.method == "POST":
        conn.execute("""
            INSERT INTO produtos(codigo_barras,nome,categoria,preco_custo,preco_venda,estoque,estoque_minimo,criado_em)
            VALUES(?,?,?,?,?,?,?,?)
        """, (request.form["codigo_barras"],request.form["nome"],request.form["categoria"],float(request.form["preco_custo"]),float(request.form["preco_venda"]),int(request.form["estoque"]),int(request.form["estoque_minimo"]),now_br()))
        conn.commit()
        conn.close()
        log_action(f"Produto cadastrado: {request.form['nome']}")
        return redirect(url_for("produtos"))
    busca = request.args.get("q","")
    rows = conn.execute("SELECT * FROM produtos WHERE nome LIKE ? OR categoria LIKE ? OR codigo_barras LIKE ? ORDER BY id DESC", (f"%{busca}%",f"%{busca}%",f"%{busca}%")).fetchall()
    conn.close()
    return render_template("produtos.html", produtos=rows, busca=busca)

@app.route("/produto/codigo/<codigo>")
@login_required
def produto_por_codigo(codigo):
    conn = get_db()
    produto = conn.execute("SELECT * FROM produtos WHERE codigo_barras=?", (codigo,)).fetchone()
    conn.close()
    if not produto:
        flash("Produto não encontrado.", "warning")
        return redirect(url_for("movimentacoes"))
    return redirect(url_for("movimentacoes", produto_id=produto["id"]))

@app.route("/produtos/editar/<int:id>", methods=["GET","POST"])
@login_required
def editar_produto(id):
    conn = get_db()
    if request.method == "POST":
        conn.execute("UPDATE produtos SET codigo_barras=?,nome=?,categoria=?,preco_custo=?,preco_venda=?,estoque=?,estoque_minimo=? WHERE id=?",
                     (request.form["codigo_barras"],request.form["nome"],request.form["categoria"],float(request.form["preco_custo"]),float(request.form["preco_venda"]),int(request.form["estoque"]),int(request.form["estoque_minimo"]),id))
        conn.commit()
        conn.close()
        log_action(f"Produto editado: {request.form['nome']}", id, request.form["nome"])
        return redirect(url_for("produtos"))
    p = conn.execute("SELECT * FROM produtos WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("editar_produto.html", p=p)

@app.route("/produtos/excluir/<int:id>")
@login_required
@admin_required
def excluir_produto(id):
    conn = get_db()
    conn.execute("DELETE FROM produtos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    log_action(f"Produto excluído: {id}")
    return redirect(url_for("produtos"))

@app.route("/movimentacoes", methods=["GET","POST"])
@login_required
def movimentacoes():
    conn = get_db()

    if request.method == "POST":
        produto_id = request.form["produto_id"]
        tipo = request.form["tipo"]
        motivo = request.form["motivo"]
        quantidade = int(request.form["quantidade"])
        cliente_id = request.form.get("cliente_id") or None
        observacao = request.form.get("observacao", "")

        produto = conn.execute(
            "SELECT * FROM produtos WHERE id=?",
            (produto_id,)
        ).fetchone()

        if not produto:
            flash("Produto não encontrado.", "danger")
            conn.close()
            return redirect(url_for("movimentacoes"))

        estoque_atual = produto["estoque"]

        if tipo == "saida" and quantidade > estoque_atual:
            flash("Estoque insuficiente para realizar a saída.", "danger")
            conn.close()
            return redirect(url_for("movimentacoes"))

        novo_estoque = estoque_atual + quantidade if tipo == "entrada" else estoque_atual - quantidade

        conn.execute(
            "UPDATE produtos SET estoque=? WHERE id=?",
            (novo_estoque, produto_id)
        )

        valor_total = quantidade * float(produto["preco_venda"])

        conn.execute("""
            INSERT INTO movimentacoes(
                produto_id,tipo,motivo,quantidade,cliente_id,
                usuario,data_movimentacao,observacao,valor_total
            )
            VALUES(?,?,?,?,?,?,?,?,?)
        """, (
            produto_id,
            tipo,
            motivo,
            quantidade,
            cliente_id,
            session.get("usuario_nome","Administrador"),
            today_iso(),
            observacao,
            valor_total
        ))

        conn.commit()

        log_action(
            f"Movimentação {tipo} | Produto: {produto['nome']} | Quantidade: {quantidade}"
        )

        conn.close()

        flash("Movimentação registrada com sucesso!", "success")
        return redirect(url_for("movimentacoes"))

    produto_id = request.args.get("produto_id")

    produtos = conn.execute("""
        SELECT * FROM produtos
        ORDER BY nome
    """).fetchall()

    clientes = conn.execute("""
        SELECT * FROM clientes
        ORDER BY nome
    """).fetchall()

    rows = conn.execute("""
        SELECT
            m.*,
            p.nome AS produto,
            c.nome AS cliente
        FROM movimentacoes m
        LEFT JOIN produtos p ON p.id = m.produto_id
        LEFT JOIN clientes c ON c.id = m.cliente_id
        ORDER BY m.id DESC
        LIMIT 50
    """).fetchall()

    mov_hoje = conn.execute(
        "SELECT COUNT(*) total FROM movimentacoes WHERE data_movimentacao=?",
        (today_iso(),)
    ).fetchone()["total"]

    entradas_hoje = conn.execute(
        "SELECT COALESCE(SUM(quantidade),0) total FROM movimentacoes WHERE tipo='entrada' AND data_movimentacao=?",
        (today_iso(),)
    ).fetchone()["total"]

    saidas_hoje = conn.execute(
        "SELECT COALESCE(SUM(quantidade),0) total FROM movimentacoes WHERE tipo='saida' AND data_movimentacao=?",
        (today_iso(),)
    ).fetchone()["total"]

    estoque_total = conn.execute(
        "SELECT COALESCE(SUM(estoque),0) total FROM produtos"
    ).fetchone()["total"]

    conn.close()

    return render_template(
        "movimentacoes.html",
        produtos=produtos,
        clientes=clientes,
        movimentos=rows,
        produto_id=produto_id,
        mov_hoje=mov_hoje,
        entradas_hoje=entradas_hoje,
        saidas_hoje=saidas_hoje,
        estoque_total=estoque_total
    )


@app.route("/relatorios")
@login_required
def relatorios():
    conn = get_db()
    vendidos = conn.execute("""
        SELECT p.nome, SUM(m.quantidade) qtd, SUM(m.valor_total) total
        FROM movimentacoes m JOIN produtos p ON p.id=m.produto_id
        WHERE m.tipo='saida' AND m.motivo='Venda'
        GROUP BY p.id ORDER BY qtd DESC
    """).fetchall()
    criticos = conn.execute("SELECT * FROM produtos WHERE estoque <= estoque_minimo ORDER BY estoque ASC").fetchall()
    conn.close()
    return render_template("relatorios.html", vendidos=vendidos, criticos=criticos)

@app.route("/relatorios/produtos.csv")
@login_required
def export_produtos_csv():
    conn = get_db()
    rows = conn.execute("SELECT codigo_barras,nome,categoria,preco_custo,preco_venda,estoque,estoque_minimo FROM produtos ORDER BY nome").fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Codigo","Nome","Categoria","Custo","Venda","Estoque","Minimo"])
    for r in rows:
        writer.writerow([r["codigo_barras"], r["nome"], r["categoria"], r["preco_custo"], r["preco_venda"], r["estoque"], r["estoque_minimo"]])
    resp = make_response(output.getvalue())
    resp.headers["Content-Disposition"] = "attachment; filename=produtos_estoque.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp

@app.route("/relatorios/movimentacoes.csv")
@login_required
def export_mov_csv():
    conn = get_db()
    rows = conn.execute("""
        SELECT m.data_movimentacao,p.nome produto,m.tipo,m.motivo,m.quantidade,m.valor_total,c.nome cliente
        FROM movimentacoes m JOIN produtos p ON p.id=m.produto_id
        LEFT JOIN clientes c ON c.id=m.cliente_id ORDER BY m.id DESC
    """).fetchall()
    conn.close()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Data","Produto","Tipo","Motivo","Quantidade","Valor Total","Cliente"])
    for r in rows:
        writer.writerow([r["data_movimentacao"], r["produto"], r["tipo"], r["motivo"], r["quantidade"], r["valor_total"], r["cliente"]])
    resp = make_response(output.getvalue())
    resp.headers["Content-Disposition"] = "attachment; filename=movimentacoes.csv"
    resp.headers["Content-Type"] = "text/csv"
    return resp

@app.route("/historico")
@login_required
def historico():
    conn = get_db()
    usuario = request.args.get("usuario","")
    produto = request.args.get("produto","")
    data = request.args.get("data","")
    query = "SELECT * FROM logs WHERE 1=1"
    params = []
    if usuario:
        query += " AND usuario_nome LIKE ?"; params.append(f"%{usuario}%")
    if produto:
        query += " AND produto_nome LIKE ?"; params.append(f"%{produto}%")
    if data:
        query += " AND data_hora LIKE ?"; params.append(f"%{data}%")
    query += " ORDER BY id DESC LIMIT 150"
    logs = conn.execute(query, params).fetchall()
    conn.close()
    return render_template("historico.html", logs=logs, usuario=usuario, produto=produto, data=data)

@app.route("/usuarios", methods=["GET","POST"])
@login_required
@admin_required
def usuarios():
    conn = get_db()
    if request.method == "POST":
        conn.execute("INSERT INTO usuarios(nome,email,senha,perfil,criado_em) VALUES(?,?,?,?,?)",
                     (request.form["nome"], request.form["email"].lower(), generate_password_hash(request.form["senha"]), request.form["perfil"], now_br()))
        conn.commit()
        log_action(f"Usuário cadastrado: {request.form['nome']}")
    users = conn.execute("SELECT id,nome,email,perfil,criado_em FROM usuarios ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("usuarios.html", usuarios=users)

@app.route("/perfil", methods=["GET","POST"])
@login_required
def perfil():
    conn = get_db()
    if request.method == "POST":
        nome = request.form["nome"]
        tema = request.form["tema"]
        notificacoes = request.form["notificacoes"]
        senha = request.form.get("senha","")
        if senha:
            conn.execute("UPDATE usuarios SET nome=?,tema=?,notificacoes=?,senha=? WHERE id=?",
                         (nome, tema, notificacoes, generate_password_hash(senha), session["usuario_id"]))
        else:
            conn.execute("UPDATE usuarios SET nome=?,tema=?,notificacoes=? WHERE id=?",
                         (nome, tema, notificacoes, session["usuario_id"]))
        conn.commit()
        conn.close()
        session["usuario_nome"] = nome
        log_action("Perfil atualizado")
        return redirect(url_for("perfil"))
    user = conn.execute("SELECT * FROM usuarios WHERE id=?", (session["usuario_id"],)).fetchone()
    conn.close()
    return render_template("perfil.html", user=user)

@app.route("/sobre")
@login_required
def sobre():
    return render_template("sobre.html")

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
