import io
import os
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import qrcode

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bibliomap.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS DE BANCO DE DADOS ---

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    identificador = db.Column(db.String(50), unique=True, nullable=False) # Armazena Matrícula ou CPF
    nome = db.Column(db.String(100), nullable=False)
    perfil = db.Column(db.String(20), nullable=False) # 'aluno' ou 'funcionario'

class Livro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tombo = db.Column(db.String(50), unique=True, nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(100), nullable=False)
    rua = db.Column(db.String(20), nullable=False)
    estante = db.Column(db.String(20), nullable=False)
    prateleira = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Disponível')

class Emprestimo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    livro_id = db.Column(db.Integer, db.ForeignKey('livro.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data_retirada = db.Column(db.DateTime, default=datetime.utcnow)
    data_devolucao = db.Column(db.DateTime, nullable=True)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# --- TEMPLATE HTML BASE ---

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>BiblioMap | SENAI Caxias</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .bg-senai { background-color: #8dc6e4; }
    </style>
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg bg-senai mb-4 shadow-sm">
        <div class="container">
            <a class="navbar-brand fw-bold text-dark" href="#">BiblioMap | SENAI Caxias</a>
            <div>
                {% if current_user.is_authenticated %}
                    <span class="me-3 text-dark fw-semibold">Olá, {{ current_user.nome }} ({{ current_user.perfil.capitalize() }})</span>
                    <a href="{{ url_for('logout') }}" class="btn btn-outline-dark btn-sm">Sair</a>
                {% endif %}
            </div>
        </div>
    </nav>

    <div class="container">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-info alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        {% block content %}{% endblock %}
    </div>
</body>
</html>
"""

# --- ROTAS DA APLICAÇÃO ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identificador = request.form.get('identificador', '').strip()
        perfil = request.form.get('perfil')

        if not identificador:
            flash('Por favor, insira a sua Matrícula ou CPF.')
            return redirect(url_for('login'))

        # Procura o usuário pelo identificador (Matrícula ou CPF)
        user = Usuario.query.filter_by(identificador=identificador).first()

        if not user:
            # Caso ainda não exista, cria o cadastro com o perfil selecionado
            nome_padrao = f"Aluno ({identificador})" if perfil == 'aluno' else f"Funcionário ({identificador})"
            user = Usuario(identificador=identificador, nome=nome_padrao, perfil=perfil)
            db.session.add(user)
            db.session.commit()
        else:
            # Atualiza o perfil caso o usuário mude a seleção no login
            user.perfil = perfil
            db.session.commit()

        login_user(user)
        return redirect(url_for('dashboard'))

    login_html = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
        <div class="row justify-content-center mt-5">
            <div class="col-md-5">
                <div class="card p-4 shadow">
                    <h4 class="mb-3 text-center fw-bold">Acesso ao Sistema</h4>
                    <form method="POST">
                        <div class="mb-3">
                            <label class="form-label font-weight-bold">Selecione o Perfil:</label>
                            <div class="d-flex gap-3">
                                <div class="form-check">
                                    <input class="form-check-input" type="radio" name="perfil" id="aluno" value="aluno" checked>
                                    <label class="form-check-label" for="aluno">Aluno</label>
                                </div>
                                <div class="form-check">
                                    <input class="form-check-input" type="radio" name="perfil" id="funcionario" value="funcionario">
                                    <label class="form-check-label" for="funcionario">Funcionário</label>
                                </div>
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Matrícula ou CPF:</label>
                            <input type="text" name="identificador" class="form-control" placeholder="Digite sua Matrícula ou CPF" required>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Entrar</button>
                    </form>
                </div>
            </div>
        </div>
    ''')
    return render_template_string(login_html)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def dashboard():
    livros = Livro.query.all()

    dash_html = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
        <div class="card p-4 shadow-sm mb-4">
            <h4>Gestão de Endereçamento e Acervo</h4>
            <p class="text-muted">Sistema de rastreabilidade e controle patrimonial do acervo bibliográfico.</p>
            {% if current_user.perfil == 'funcionario' %}
            <form action="/cadastrar_livro" method="POST" class="row g-3 mt-2">
                <div class="col-md-2"><input type="text" name="tombo" placeholder="Tombo / Patrimônio" class="form-control" required></div>
                <div class="col-md-3"><input type="text" name="titulo" placeholder="Título do Livro" class="form-control" required></div>
                <div class="col-md-3"><input type="text" name="autor" placeholder="Autor" class="form-control" required></div>
                <div class="col-md-1"><input type="text" name="rua" placeholder="Rua" class="form-control" required></div>
                <div class="col-md-1"><input type="text" name="estante" placeholder="Estante" class="form-control" required></div>
                <div class="col-md-1"><input type="text" name="prateleira" placeholder="Prat." class="form-control" required></div>
                <div class="col-md-1"><button type="submit" class="btn btn-success w-100">Cadastrar</button></div>
            </form>
            {% endif %}
        </div>

        <div class="card p-4 shadow-sm">
            <div class="d-flex justify-content-between align-items-center mb-3">
                <h4>Consulta de Exemplares e Localização</h4>
                <a href="/relatorio" class="btn btn-secondary btn-sm">Ver Relatórios</a>
            </div>
            <table class="table table-striped align-middle">
                <thead class="table-dark">
                    <tr>
                        <th>Tombo / Patrimônio</th>
                        <th>Título</th>
                        <th>Autor</th>
                        <th>Rua</th>
                        <th>Estante</th>
                        <th>Prateleira</th>
                        <th>Status</th>
                        <th>QR Code</th>
                    </tr>
                </thead>
                <tbody>
                    {% for livro in livros %}
                    <tr>
                        <td>{{ livro.tombo }}</td>
                        <td>{{ livro.titulo }}</td>
                        <td>{{ livro.autor }}</td>
                        <td>{{ livro.rua }}</td>
                        <td>{{ livro.estante }}</td>
                        <td>{{ livro.prateleira }}</td>
                        <td><span class="badge bg-{{ 'success' if livro.status == 'Disponível' else 'warning' }}">{{ livro.status }}</span></td>
                        <td>
                            <a href="/qrcode/{{ livro.id }}" target="_blank" class="btn btn-sm btn-outline-primary">Ver QR Code</a>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="8" class="text-center">Nenhum livro cadastrado no sistema.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    ''')
    return render_template_string(dash_html, livros=livros)

@app.route('/cadastrar_livro', methods=['POST'])
@login_required
def cadastrar_livro():
    if current_user.perfil != 'funcionario':
        flash('Apenas funcionários podem cadastrar novos livros.')
        return redirect(url_for('dashboard'))

    novo_livro = Livro(
        tombo=request.form.get('tombo'),
        titulo=request.form.get('titulo'),
        autor=request.form.get('autor'),
        rua=request.form.get('rua'),
        estante=request.form.get('estante'),
        prateleira=request.form.get('prateleira')
    )
    db.session.add(novo_livro)
    db.session.commit()
    flash('Livro cadastrado com sucesso!')
    return redirect(url_for('dashboard'))

@app.route('/qrcode/<int:livro_id>')
@login_required
def gerar_qrcode(livro_id):
    livro = Livro.query.get_or_404(livro_id)
    conteudo = f"LIVRO: {livro.titulo}\nTOMBO: {livro.tombo}\nLOCALIZAÇÃO: Rua {livro.rua}, Estante {livro.estante}, Prateleira {livro.prateleira}"

    img = qrcode.make(conteudo)
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/relatorio')
@login_required
def relatorio():
    total_livros = Livro.query.count()
    disponiveis = Livro.query.filter_by(status='Disponível').count()
    emprestados = total_livros - disponiveis

    rel_html = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
        <div class="card p-4 shadow-sm">
            <h4>Relatório Geral do Acervo</h4>
            <hr>
            <div class="row text-center mb-4">
                <div class="col-md-4"><div class="p-3 bg-light border rounded"><h5>Total de Livros</h5><h3>{{ total }}</h3></div></div>
                <div class="col-md-4"><div class="p-3 bg-light border rounded"><h5 class="text-success">Disponíveis</h5><h3>{{ disp }}</h3></div></div>
                <div class="col-md-4"><div class="p-3 bg-light border rounded"><h5 class="text-warning">Emprestados</h5><h3>{{ emp }}</h3></div></div>
            </div>
            <a href="/" class="btn btn-primary">Voltar ao Painel</a>
        </div>
    ''')
    return render_template_string(rel_html, total=total_livros, disp=disponiveis, emp=emprestados)

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
