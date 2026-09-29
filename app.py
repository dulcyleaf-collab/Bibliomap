from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# Função para conectar à base de dados
def get_db_connection():
    conn = sqlite3.connect('bibliomap.db')
    conn.row_factory = sqlite3.Row
    return conn

# Criação das tabelas iniciais
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS acervo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tombo TEXT UNIQUE NOT NULL,
            titulo TEXT NOT NULL,
            autor TEXT NOT NULL,
            rua TEXT NOT NULL,
            estante TEXT NOT NULL,
            prateleira TEXT NOT NULL,
            status TEXT DEFAULT 'Disponível'
        )
    ''')
    conn.commit()
    conn.close()

# Inicializa a base de dados ao arrancar
init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    livros = conn.execute('SELECT * FROM acervo').fetchall()
    conn.close()
    return render_template('index.html', livros=livros)

if __name__ == '__main__':
    app.run(debug=True)
