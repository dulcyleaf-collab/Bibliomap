import io
import os
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import qrcode

app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave_secreta_bibliomap_senai'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bibliomap.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- MODELOS DE BANCO DE DADOS ---

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    identificador = db.Column(db.String(50), unique=True, nullable=False) # CPF ou Matrícula
    nome = db.Column(db.String(100), nullable=False)
    perfil = db.Column(db.String(20), nullable=False) # 'aluno' ou 'funcionario'

class Livro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patrimonio = db.Column(db.String(50), unique=True, nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(100), nullable=False)
    
    # Localização Inteligente
    rua = db.Column(db.String(20), nullable=False)
    estante = db.Column(db.String(20), nullable=False)
    prateleira = db.Column(db.String(20), nullable=False)
    posicao = db.Column(db.String(20), nullable=False)

    # Estado e Status
    estado = db.Column(db.String(30), default='Bom')
    status = db.Column(db.String(30), default='Disponível')

class Emprestimo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    livro_id = db.Column(db.Integer, db.ForeignKey('livro.id'), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    data_retirada = db.Column(db.DateTime, default=datetime.utcnow)
    data_previsao = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    data_devolucao = db.Column(db.DateTime, nullable=True)

    livro = db.relationship('Livro', backref='emprestimos')
    usuario = db.relationship('Usuario', backref='emprestimos')

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# --- TEMPLATE VISUAL ---

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BiblioMap | SENAI Caxias</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #f8fafc; color: #1e293b; }
        .navbar-custom { background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); box-shadow: 0 4px 20px -2px rgba(2, 132, 199, 0.25); }
        .brand-logo { font-weight: 700; letter-spacing: -0.5px; }
        .card-custom { border: 1px solid #e2e8f0; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); background: #ffffff; }
        .btn-primary-custom { background-color: #0284c7; border-color: #0284c7; border-radius: 10px; font-weight: 600; padding: 10px 20px; }
        .btn-primary-custom:hover { background-color: #0369a1; border-color: #0369a1; }
        .form-control, .form-select { border-radius: 10px; border: 1px solid #cbd5e1; padding: 10px 14px; }
        .badge-soft-success { background-color: #dcfce7; color: #15803d; font-weight: 600; padding: 6px 12px; border-radius: 20px; }
        .badge-soft-warning { background-color: #fef9c3; color: #a16207; font-weight: 600; padding: 6px 12px; border-radius: 20px; }
        .badge-soft-danger  { background-color: #fee2e2; color: #b91c1c; font-weight: 600; padding: 6px 12px; border-radius: 20px; }
        .badge-soft-secondary { background-color: #f1f5f9; color: #475569; font-weight: 600; padding: 6px 12px; border-radius: 20px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark navbar-custom mb-4">
        <div class="container py-1">
            <a class="navbar-brand brand-logo d-flex align-items-center gap-2" href="/">
                <i class="bi bi-journal-bookmark-fill fs-4"></i>
                <span>BiblioMap <span class="badge bg-white text-primary fs-6 fw-bold ms-1">SENAI</span></span>
            </a>
            <div>
                {% if current_user.is_authenticated %}
                    <span class="me-3 text-white-50 fw-medium">
                        <i class="bi bi-person-circle me-1 text-white"></i> {{ current_user.nome }} 
                        <span class="badge bg-white text-dark ms-1">{{ current_user.perfil.capitalize() }}</span>
                    </span>
                    <a href="{{ url_for('relatorio') }}" class="btn btn-light btn-sm fw-semibold me-2 rounded-3">
                        <i class="bi bi-bar-chart-line me-1"></i> Relatórios
                    </a>
                    <a href="{{ url_for('logout') }}" class="btn btn-outline-light btn-sm fw-semibold rounded-3">
                        <i class="bi bi-box-arrow-right"></i> Sair
                    </a>
                {% endif %}
            </div>
        </div>
    </nav>

    <div class="container mb-5">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert alert-info alert-dismissible fade show border-0 shadow-sm rounded-3 mb-4" role="alert">
                        <i class="bi bi-info-circle-fill me-2"></i> {{ message }}
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
            flash('Informe a sua Matrícula ou CPF.')
            return redirect(url_for('login'))

        user = Usuario.query.filter_by(identificador=identificador).first()
        if not user:
            nome_padrao = f"Aluno ({identificador})" if perfil == 'aluno' else f"Funcionário ({identificador})"
            user = Usuario(identificador=identificador, nome=nome_padrao, perfil=perfil)
            db.session.add(user)
            db.session.commit()

        login_user(user)
        return redirect(url_for('dashboard'))

    login_html = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
        <div class="row justify-content-center mt-4">
            <div class="col-md-5">
                <div class="card card-custom p-4 p-md-5">
                    <div class="text-center mb-4">
                        <div class="d-inline-flex align-items-center justify-content-center bg-primary-subtle text-primary rounded-circle mb-3" style="width: 64px; height: 64px;">
                            <i class="bi bi-shield-lock-fill fs-2"></i>
                        </div>
                        <h4 class="fw-bold">Acesso ao Sistema</h4>
                        <p class="text-muted small">BiblioMap SENAI Caxias</p>
                    </div>

                    <form method="POST">
                        <div class="mb-4">
                            <label class="form-label fw-semibold small text-uppercase text-muted">Perfil de Acesso</label>
                            <div class="row g-2">
                                <div class="col-6">
                                    <input type="radio" class="btn-check" name="perfil" id="aluno" value="aluno" checked>
                                    <label class="btn btn-outline-primary w-100 py-2 rounded-3 fw-semibold" for="aluno">Aluno</label>
                                </div>
                                <div class="col-6">
                                    <input type="radio" class="btn-check" name="perfil" id="funcionario" value="funcionario">
                                    <label class="btn btn-outline-primary w-100 py-2 rounded-3 fw-semibold" for="funcionario">Funcionário</label>
                                </div>
                            </div>
                        </div>

                        <div class="mb-4">
                            <label class="form-label fw-semibold small text-uppercase text-muted">Identificação</label>
                            <input type="text" name="identificador" class="form-control" placeholder="Digite a Matrícula ou CPF" required>
                        </div>

                        <button type="submit" class="btn btn-primary-custom w-100 text-white">Entrar no Sistema</button>
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
        {% if current_user.perfil == 'funcionario' %}
        <div class="card card-custom p-4 mb-4">
            <h5 class="fw-bold mb-3"><i class="bi bi-plus-circle-fill text-primary me-2"></i> Cadastrar Novo Exemplar</h5>
            <form action="/cadastrar_livro" method="POST" class="row g-3">
                <div class="col-md-2"><input type="text" name="patrimonio" placeholder="Nº Patrimônio" class="form-control" required></div>
                <div class="col-md-4"><input type="text" name="titulo" placeholder="Título do Livro" class="form-control" required></div>
                <div class="col-md-3"><input type="text" name="autor" placeholder="Autor" class="form-control" required></div>
                <div class="col-md-3">
                    <select name="estado" class="form-select">
                        <option value="Excelente">Estado: Excelente</option>
                        <option value="Bom" selected>Estado: Bom</option>
                        <option value="Danificado">Estado: Danificado</option>
                    </select>
                </div>
                
                <div class="col-12"><small class="text-muted fw-semibold">Endereçamento Físico:</small></div>
                <div class="col-md-3"><input type="text" name="rua" placeholder="Rua" class="form-control" required></div>
                <div class="col-md-3"><input type="text" name="estante" placeholder="Estante" class="form-control" required></div>
                <div class="col-md-3"><input type="text" name="prateleira" placeholder="Prateleira" class="form-control" required></div>
                <div class="col-md-3"><input type="text" name="posicao" placeholder="Posição" class="form-control" required></div>

                <div class="col-12 text-end mt-3">
                    <button type="submit" class="btn btn-primary-custom text-white">Cadastrar Livro</button>
                </div>
            </form>
        </div>
        {% endif %}

        <div class="card card-custom p-4">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h5 class="fw-bold m-0"><i class="bi bi-book-half text-primary me-2"></i> Acervo e QR Codes</h5>
                <span class="badge bg-light text-dark border px-3 py-2 rounded-pill fw-semibold">{{ livros|length }} Exemplares</span>
            </div>

            <div class="table-responsive">
                <table class="table table-hover align-middle">
                    <thead class="table-light">
                        <tr>
                            <th>Patrimônio</th>
                            <th>Livro / Autor</th>
                            <th>Endereço na Biblioteca</th>
                            <th>Status</th>
                            <th class="text-end">Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for livro in livros %}
                        <tr>
                            <td class="fw-bold text-secondary">#{{ livro.patrimonio }}</td>
                            <td>
                                <div class="fw-bold">{{ livro.titulo }}</div>
                                <div class="text-muted small">{{ livro.autor }}</div>
                            </td>
                            <td>
                                <span class="badge badge-soft-secondary">
                                    <i class="bi bi-geo-alt me-1"></i>Rua {{ livro.rua }} | Est. {{ livro.estante }} | Prat. {{ livro.prateleira }}
                                </span>
                            </td>
                            <td>
                                {% if livro.status == 'Disponível' %}
                                    <span class="badge badge-soft-success">Disponível</span>
                                {% elif livro.status == 'Emprestado' %}
                                    <span class="badge badge-soft-warning">Emprestado</span>
                                {% else %}
                                    <span class="badge badge-soft-danger">{{ livro.status }}</span>
                                {% endif %}
                            </td>
                            <td class="text-end">
                                <a href="/qrcode/{{ livro.id }}" target="_blank" class="btn btn-sm btn-outline-secondary rounded-2 me-1">
                                    <i class="bi bi-qr-code me-1"></i> Ver/Imprimir QR Code
                                </a>
                                
                                {% if livro.status == 'Disponível' %}
                                    <a href="/escanear_livro/{{ livro.id }}" class="btn btn-sm btn-primary rounded-2">
                                        <i class="bi bi-qr-code-scan me-1"></i> Emprestar
                                    </a>
                                {% endif %}
                            </td>
                        </tr>
                        {% else %}
                        <tr><td colspan="5" class="text-center py-4 text-muted">Nenhum livro cadastrado.</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    ''')
    return render_template_string(dash_html, livros=livros)

@app.route('/cadastrar_livro', methods=['POST'])
@login_required
def cadastrar_livro():
    if current_user.perfil != 'funcionario':
        flash('Apenas funcionários podem cadastrar livros.')
        return redirect(url_for('dashboard'))

    novo = Livro(
        patrimonio=request.form.get('patrimonio'),
        titulo=request.form.get('titulo'),
        autor=request.form.get('autor'),
        rua=request.form.get('rua'),
        estante=request.form.get('estante'),
        prateleira=request.form.get('prateleira'),
        posicao=request.form.get('posicao'),
        estado=request.form.get('estado')
    )
    db.session.add(novo)
    db.session.commit()
    flash('Livro cadastrado com sucesso!')
    return redirect(url_for('dashboard'))

# --- TELA DE ESCANEAR / REGISTRAR EMPRÉSTIMO ---

@app.route('/escanear_livro/<int:livro_id>', methods=['GET', 'POST'])
@login_required
def escanear_livro(livro_id):
    livro = Livro.query.get_or_404(livro_id)

    if request.method == 'POST':
        identificador_aluno = request.form.get('identificador_aluno', '').strip()
        nome_aluno = request.form.get('nome_aluno', '').strip()

        if not identificador_aluno:
            flash('Informe a Matrícula ou CPF do aluno.')
            return redirect(url_for('escanear_livro', livro_id=livro.id))

        # Busca ou cria o aluno no sistema
        aluno = Usuario.query.filter_by(identificador=identificador_aluno).first()
        if not aluno:
            nome_final = nome_aluno if nome_aluno else f"Aluno ({identificador_aluno})"
            aluno = Usuario(identificador=identificador_aluno, nome=nome_final, perfil='aluno')
            db.session.add(aluno)
            db.session.commit()
        elif nome_aluno:
            aluno.nome = nome_aluno
            db.session.commit()

        # Altera o status do livro e gera empréstimo por 7 dias
        livro.status = 'Emprestado'
        data_retirada = datetime.utcnow()
        data_previsao = data_retirada + timedelta(days=7)

        novo_emp = Emprestimo(
            livro_id=livro.id,
            usuario_id=aluno.id,
            data_retirada=data_retirada,
            data_previsao=data_previsao
        )
        db.session.add(novo_emp)
        db.session.commit()

        flash(f'Empréstimo do livro "{livro.titulo}" registado para {aluno.nome}! Devolução até: {data_previsao.strftime("%d/%m/%Y")} (Prazo de 7 dias).')
        return redirect(url_for('dashboard'))

    html = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', f'''
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card card-custom p-4">
                    <h5 class="fw-bold mb-3"><i class="bi bi-qr-code-scan text-primary me-2"></i> Registo de Empréstimo via QR Code</h5>
                    
                    <div class="bg-light p-3 rounded-3 mb-4 border">
                        <h6 class="fw-bold m-0">{livro.titulo}</h6>
                        <small class="text-muted">Patrimônio: #{livro.patrimonio} | Localização: Rua {livro.rua}, Estante {livro.estante}</small>
                    </div>

                    <form method="POST">
                        <div class="mb-3">
                            <label class="form-label fw-semibold">Matrícula ou CPF do Aluno:</label>
                            <input type="text" name="identificador_aluno" class="form-control" placeholder="Digite ou escaneie o documento do aluno" required>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label fw-semibold">Nome do Aluno (Opcional):</label>
                            <input type="text" name="nome_aluno" class="form-control" placeholder="Nome completo do aluno">
                        </div>

                        <div class="alert alert-warning d-flex align-items-center mb-4" role="alert">
                            <i class="bi bi-clock-history me-2 fs-5"></i>
                            <div><strong>Prazo do Empréstimo:</strong> O livro será registado por exatamente <strong>7 dias</strong>.</div>
                        </div>

                        <button type="submit" class="btn btn-primary-custom w-100 text-white">Confirmar e Registar Empréstimo</button>
                    </form>
                </div>
            </div>
        </div>
    ''')
    return render_template_string(html)

@app.route('/qrcode/<int:livro_id>')
@login_required
def gerar_qrcode(livro_id):
    livro = Livro.query.get_or_404(livro_id)
    # O QR Code guarda o link direto para o funcionário escanear com o telemóvel
    link_emprestimo = request.host_url.rstrip('/') + url_for('escanear_livro', livro_id=livro.id)

    img = qrcode.make(link_emprestimo)
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/devolver/<int:emp_id>')
@login_required
def devolver(emp_id):
    emp = Emprestimo.query.get_or_404(emp_id)
    emp.data_devolucao = datetime.utcnow()
    emp.livro.status = 'Disponível'
    db.session.commit()
    flash('Devolução registada com sucesso!')
    return redirect(url_for('relatorio'))

@app.route('/relatorio')
@login_required
def relatorio():
    livros = Livro.query.all()
    emprestimos_ativos = Emprestimo.query.filter_by(data_devolucao=None).all()
    agora = datetime.utcnow()

    rel_html = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h4 class="fw-bold m-0"><i class="bi bi-pie-chart-fill text-primary me-2"></i> Relatórios Gerenciais</h4>
            <a href="/" class="btn btn-outline-secondary rounded-3"><i class="bi bi-arrow-left me-1"></i> Voltar</a>
        </div>

        <div class="card card-custom p-4">
            <h5 class="fw-bold mb-3"><i class="bi bi-clock-history me-2 text-primary"></i> Livros Emprestados e Prazos (7 dias)</h5>
            <div class="table-responsive">
                <table class="table table-hover align-middle">
                    <thead class="table-light">
                        <tr>
                            <th>Livro</th>
                            <th>Aluno</th>
                            <th>Data Retirada</th>
                            <th>Devolução Prevista</th>
                            <th>Situação</th>
                            <th class="text-end">Ação</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for emp in emprestimos_ativos %}
                        <tr>
                            <td><strong>{{ emp.livro.titulo }}</strong> <br><small class="text-muted">#{{ emp.livro.patrimonio }}</small></td>
                            <td>{{ emp.usuario.nome }} <br><small class="text-muted">ID: {{ emp.usuario.identificador }}</small></td>
                            <td>{{ emp.data_retirada.strftime('%d/%m/%Y') }}</td>
                            <td>{{ emp.data_previsao.strftime('%d/%m/%Y') }}</td>
                            <td>
                                {% if emp.data_previsao < agora %}
                                    <span class="badge badge-soft-danger"><i class="bi bi-exclamation-triangle me-1"></i> ATRASADO</span>
                                {% else %}
                                    <span class="badge badge-soft-success">Dentro do prazo</span>
                                {% endif %}
                            </td>
                            <td class="text-end">
                                <a href="/devolver/{{ emp.id }}" class="btn btn-sm btn-outline-success rounded-2">Registar Devolução</a>
                            </td>
                        </tr>
                        {% else %}
                        <tr><td colspan="6" class="text-center py-4 text-muted">Nenhum livro emprestado no momento.</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    ''')

    return render_template_string(
        rel_html, 
        total=len(livros), 
        emp_count=len(emprestimos_ativos), 
        emprestimos_ativos=emprestimos_ativos, 
        agora=agora
    )

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
