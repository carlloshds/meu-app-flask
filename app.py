from flask import Flask, render_template, request, redirect, flash, jsonify, session, url_for
import sqlite3
import pyotp
import os

app = Flask(__name__)
app.secret_key = "goiabada12"

# Criar banco de dados
def conectar_banco():
    conn = sqlite3.connect("contas_ps.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            chave_otp TEXT,
            codigos_backup TEXT
        )
    ''')
    conn.commit()
    return conn, cursor

# Página inicial (Gerar Código)
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form['email']
        conn, cursor = conectar_banco()
        cursor.execute("SELECT chave_otp, codigos_backup FROM contas WHERE email = ?", (email,))
        resultado = cursor.fetchone()
        conn.close()

        if resultado:
            chave_otp, codigos_backup = resultado
            if chave_otp:
                totp = pyotp.TOTP(chave_otp)
                codigo_tp = totp.now()
                return render_template("gerar.html", email=email, codigo=codigo_tp, tipo="Código OTP (30s)")

            elif codigos_backup:
                codigos_lista = codigos_backup.split(",")
                if codigos_lista:
                    codigo_backup = codigos_lista.pop(0)
                    novos_codigos = ",".join(codigos_lista)
                    conn, cursor = conectar_banco()
                    cursor.execute("UPDATE contas SET codigos_backup = ? WHERE email = ?", (novos_codigos, email))
                    conn.commit()
                    conn.close()
                    return render_template("gerar.html", email=email, codigo=codigo_backup, tipo="Código de Backup (Uso Único)")

        return render_template("gerar.html", erro="Conta não encontrada ou sem códigos disponíveis.")

    return render_template("gerar.html")

# Login do Admin
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        senha = request.form['senha']
        if senha == "goiabada12":
            session['admin'] = True
            return redirect('/painel')
        else:
            flash("Senha incorreta!", "danger")
    return render_template("login.html")

# Painel Administrativo (protegido)
@app.route('/painel')
def painel():
    if not session.get('admin'):
        return redirect('/login')
    
    conn, cursor = conectar_banco()
    cursor.execute("SELECT email FROM contas")
    contas = cursor.fetchall()
    conn.close()
    return render_template("painel.html", contas=contas)

# Cadastrar Nova Conta
@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    if not session.get('admin'):
        return redirect('/login')

    if request.method == 'POST':
        email = request.form['email']
        chave_otp = request.form.get('chave_otp', '') or None
        codigos_backup = request.form.get('codigos_backup', '').replace("\n", " ").strip() or None

        if codigos_backup:
            codigos_backup = " ".join(codigos_backup.split()).replace(" ", ",")

        conn, cursor = conectar_banco()
        cursor.execute("SELECT email FROM contas WHERE email = ?", (email,))
        conta_existente = cursor.fetchone()

        if conta_existente:
            flash("Erro: Este e-mail já está cadastrado!", "danger")
        else:
            cursor.execute("INSERT INTO contas (email, chave_otp, codigos_backup) VALUES (?, ?, ?)", 
                           (email, chave_otp, codigos_backup))
            conn.commit()
            flash("Conta cadastrada com sucesso!", "success")

        conn.close()
        return redirect('/painel')

    return render_template("cadastrar.html")

# Excluir Conta
@app.route('/excluir', methods=['POST'])
def excluir():
    if not session.get('admin'):
        return redirect('/login')

    email = request.form['email']
    conn, cursor = conectar_banco()
    cursor.execute("DELETE FROM contas WHERE email = ?", (email,))
    conn.commit()
    conn.close()
    flash("Conta removida com sucesso!", "success")
    return redirect('/painel')

# Logout
@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect('/')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
