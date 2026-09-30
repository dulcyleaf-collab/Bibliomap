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
    identificador = db.Column(db.String(50), unique=True, nullable=False) # Matrícula ou CPF
    nome = db.Column(db.String(100), nullable=False)
    perfil = db.Column(db.String(20), nullable=False) # 'aluno' ou 'funcionario'

class Livro(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patrimonio = db.Column(db.String(50), unique=True, nullable=False) # Número Patrimonial
    titulo = db.Column(db.String(200), nullable=False)
    autor = db.Column(db.String(100), nullable=False)
    
    # Localização Inteligente
    rua = db.Column(db.String(20), nullable=False)
    estante = db.Column(db.String(20), nullable=False)
    prateleira = db.Column(db.String(20), nullable=False)
    posicao = db.Column(db.String(20), nullable=False)

    # Controle Patrimonial e Estado
    estado = db.Column(db.String(30), default='Bom') # Ex: Excelente, Bom, Danificado, Extraviado
    status = db.Column(db.String(30), default='Disponível') # Disponível, Emprestado, Baixado

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

# --- TEMPLATE BASE ---

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
            <a class="navbar-brand fw-bold text-dark" href="/">BiblioMap | SENAI Caxias</a>
            <div>
                {% if current_user.is_authenticated %}
                    <span class="me-3 text-dark fw-semibold">Olá, {{ current_user.nome }} ({{ current_user.perfil.capitalize() }})</span>
                    <a href="{{ url_for('relatorio') }}" class="btn btn-outline-dark btn-sm me-2">Relatórios</a>
                    <a href="{{ url_for('logout') }}" class="btn btn-danger btn-sm">Sair</a>
                {% endif %}
            </div>
        </div>
    </nav>

    <div class="container mb-5">
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
            flash('Informe a sua Matrícula ou CPF.')
            return redirect(url_for('login'))

        user = Usuario.query.filter_by(identificador=identificador).first()
        if not user:
            nome_padrao = f"Aluno ({identificador})" if perfil == 'aluno' else f"Funcionário ({identificador})"
            user = Usuario(identificador=identificador, nome=nome_padrao, perfil=perfil)
            db.session.add(user)
            db.session.commit()
        else:
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
                            <label class="form-label fw-bold">Selecione o Perfil:</label>
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
                            <label class="form-label fw-bold">Matrícula ou CPF:</label>
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
    agora = datetime.utcnow()

    dash_html = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
        {% if current_user.perfil == 'funcionario' %}
        <div class="card p-4 shadow-sm mb-4">
            <h4>1 & 3 & 4. Cadastro, Localização e Controle Patrimonial</h4>
            <form action="/cadastrar_livro" method="POST" class="row g-3 mt-1">
                <div class="col-md-2"><input type="text" name="patrimonio" placeholder="Nº Patrimonial" class="form-control" required></div>
                <div class="col-md-3"><input type="text" name="titulo" placeholder="Título" class="form-control" required></div>
                <div class="col-md-2"><input type="text" name="autor" placeholder="Autor" class="form-control" required></div>
                <div class="col-md-1"><input type="text" name="rua" placeholder="Rua" class="form-control" required></div>
                <div class="col-md-1"><input type="text" name="estante" placeholder="Estante" class="form-control" required></div>
                <div class="col-md-1"><input type="text" name="prateleira" placeholder="Prat." class="form-control" required></div>
                <div class="col-md-1"><input type="text" name="posicao" placeholder="Posição" class="form-control" required></div>
                <div class="col-md-1">
                    <select name="estado" class="form-select">
                        <option value="Excelente">Excelente</option>
                        <option value="Bom" selected>Bom</option>
                        <option value="Danificado">Danificado</option>
                    </select>
                </div>
                <div class="col-md-12 text-end">
                    <button type="submit" class="btn btn-success">Cadastrar Exemplar</button>
                </div>
            </form>
        </div>
        {% endif %}

        <div class="card p-4 shadow-sm">
            <h4 class="mb-3">Acervo e Endereçamento</h4>
            <div class="table-responsive">
                <table class="table table-striped align-middle">
                    <thead class="table-dark">
                        <tr>
                            <th>Patrimônio</th>
                            <th>Título / Autor</th>
                            <th>Localização (Rua/Est/Prat/Pos)</th>
                            <th>Estado</th>
                            <th>Status</th>
                            <th>Ações</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for livro in livros %}
                        <tr>
                            <td><strong>{{ livro.patrimonio }}</strong></td>
                            <td>{{ livro.titulo }} <br><small class="text-muted">{{ livro.autor }}</small></td>
                            <td>Rua {{ livro.rua }} | Est. {{ livro.estante }} | Prat. {{ livro.prateleira }} | Pos. {{ livro.posicao }}</td>
                            <td><span class="badge bg-secondary">{{ livro.estado }}</span></td>
                            <td>
                                {% if livro.status == 'Disponível' %}
                                    <span class="badge bg-success">Disponível</span>
                                {% elif livro.status == 'Emprestado' %}
                                    <span class="badge bg-warning text-dark">Emprestado</span>
                                {% else %}
                                    <span class="badge bg-danger">{{ livro.status }}</span>
                                {% endif %}
                            </td>
                            <td>
                                <a href="/qrcode/{{ livro.id }}" target="_blank" class="btn btn-sm btn-outline-dark me-1">QR Code</a>
                                
                                {% if livro.status == 'Disponível' %}
                                    <a href="/emprestar/{{ livro.id }}" class="btn btn-sm btn-primary me-1">Emprestar</a>
                                {% endif %}

                                {% if current_user.perfil == 'funcionario' %}
                                    <a href="/alterar_estado/{{ livro.id }}" class="btn btn-sm btn-outline-secondary me-1">Alterar Estado</a>
                                {% endif %}
                            </td>
                        </tr>
                        {% else %}
                        <tr><td colspan="6" class="text-center">Nenhum livro cadastrado.</td></tr>
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

@app.route('/emprestar/<int:livro_id>')
@login_required
def emprestar(livro_id):
    livro = Livro.query.get_or_404(livro_id)
    if livro.status != 'Disponível':
        flash('Livro indisponível para empréstimo.')
        return redirect(url_for('dashboard'))

    livro.status = 'Emprestado'
    novo_emp = Emprestimo(livro_id=livro.id, usuario_id=current_user.id)
    db.session.add(novo_emp)
    db.session.commit()
    flash(f'Livro "{livro.titulo}" emprestado com sucesso! Previsão de devolução: {novo_emp.data_previsao.strftime("%d/%m/%Y")}')
    return redirect(url_for('dashboard'))

@app.route('/devolver/<int:emp_id>')
@login_required
def devolver(emp_id):
    emp = Emprestimo.query.get_or_404(emp_id)
    emp.data_devolucao = datetime.utcnow()
    emp.livro.status = 'Disponível'
    db.session.commit()
    flash('Devolução registrada com sucesso!')
    return redirect(url_for('relatorio'))

@app.route('/alterar_estado/<int:livro_id>', methods=['GET', 'POST'])
@login_required
def alterar_estado(livro_id):
    if current_user.perfil != 'funcionario':
        flash('Acesso negado.')
        return redirect(url_for('dashboard'))

    livro = Livro.query.get_or_404(livro_id)
    if request.method == 'POST':
        livro.estado = request.form.get('estado')
        novo_status = request.form.get('status')
        if novo_status:
            livro.status = novo_status
        db.session.commit()
        flash('Situação patrimonial atualizada!')
        return redirect(url_for('dashboard'))

    html = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', f'''
        <div class="card p-4 shadow-sm col-md-6 mx-auto">
            <h4>Controle Patrimonial: {livro.titulo}</h4>
            <form method="POST">
                <div class="mb-3">
                    <label class="form-label">Estado de Conservação:</label>
                    <select name="estado" class="form-select">
                        <option value="Excelente" {"selected" if livro.estado=='Excelente' else ""}>Excelente</option>
                        <option value="Bom" {"selected" if livro.estado=='Bom' else ""}>Bom</option>
                        <option value="Danificado" {"selected" if livro.estado=='Danificado' else ""}>Danificado</option>
                    </select>
                </div>
                <div class="mb-3">
                    <label class="form-label">Situação/Status:</label>
                    <select name="status" class="form-select">
                        <option value="Disponível" {"selected" if livro.status=='Disponível' else ""}>Disponível</option>
                        <option value="Extraviado" {"selected" if livro.status=='Extraviado' else ""}>Extraviado (Perdido)</option>
                        <option value="Baixado" {"selected" if livro.status=='Baixado' else ""}>Baixado (Descartado)</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-primary w-100">Salvar Alterações</button>
            </form>
        </div>
    ''')
    return render_template_string(html)

@app.route('/qrcode/<int:livro_id>')
@login_required
def gerar_qrcode(livro_id):
    livro = Livro.query.get_or_404(livro_id)
    texto = f"SENAI CAXIAS - BIBLIOMAP\nPATRIMÓNIO: {livro.patrimonio}\nTÍTULO: {livro.titulo}\nLOCAL: Rua {livro.rua}, Estante {livro.estante}, Prat. {livro.prateleira}, Pos. {livro.posicao}\nESTADO: {livro.estado}"

    img = qrcode.make(texto)
    buf = io.BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/relatorio')
@login_required
def relatorio():
    livros = Livro.query.all()
    emprestimos_ativos = Emprestimo.query.filter_by(data_devolucao=None).all()
    agora = datetime.utcnow()

    rel_html = HTML_TEMPLATE.replace('{% block content %}{% endblock %}', '''
        <h3 class="mb-4">5. Relatórios Gerenciais</h3>
        
        <div class="row text-center mb-4">
            <div class="col-md-3"><div class="p-3 bg-white border rounded shadow-sm"><h5>Total Acervo</h5><h3>{{ total }}</h3></div></div>
            <div class="col-md-3"><div class="p-3 bg-white border rounded shadow-sm"><h5 class="text-warning">Emprestados</h5><h3>{{ emp_count }}</h3></div></div>
            <div class="col-md-3"><div class="p-3 bg-white border rounded shadow-sm"><h5 class="text-danger">Danificados</h5><h3>{{ danificados }}</h3></div></div>
            <div class="col-md-3"><div class="p-3 bg-white border rounded shadow-sm"><h5 class="text-dark">Extraviados/Baixados</h5><h3>{{ extraviados }}</h3></div></div>
        </div>

        <div class="card p-4 shadow-sm mb-4">
            <h5>Empréstimos Ativos e Controle de Atrasos</h5>
            <table class="table table-bordered mt-2 align-middle">
                <thead class="table-secondary">
                    <tr>
                        <th>Livro</th>
                        <th>Retirado Por</th>
                        <th>Data Retirada</th>
                        <th>Previsão Devolução</th>
                        <th>Situação</th>
                        <th>Ação</th>
                    </tr>
                </thead>
                <tbody>
                    {% for emp in emprestimos_ativos %}
                    <tr>
                        <td>{{ emp.livro.titulo }} ({{ emp.livro.patrimonio }})</td>
                        <td>{{ emp.usuario.nome }}</td>
                        <td>{{ emp.data_retirada.strftime('%d/%m/%Y') }}</td>
                        <td>{{ emp.data_previsao.strftime('%d/%m/%Y') }}</td>
                        <td>
                            {% if emp.data_previsao < agora %}
                                <span class="badge bg-danger">ATRASADO</span>
                            {% else %}
                                <span class="badge bg-success">Em dia</span>
                            {% endif %}
                        </td>
                        <td>
                            <a href="/devolver/{{ emp.id }}" class="btn btn-sm btn-outline-success">Registrar Devolução</a>
                        </td>
                    </tr>
                    {% else %}
                    <tr><td colspan="6" class="text-center">Nenhum empréstimo ativo no momento.</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <a href="/" class="btn btn-secondary">Voltar ao Painel Geral</a>
    ''')

    danificados = Livro.query.filter_by(estado='Danificado').count()
    extraviados = Livro.query.filter(Livro.status.in_(['Extraviado', 'Baixado'])).count()

    return render_template_string(
        rel_html, 
        total=len(livros), 
        emp_count=len(emprestimos_ativos), 
        danificados=danificados, 
        extraviados=extraviados, 
        emprestimos_ativos=emprestimos_ativos, 
        agora=agora
    )

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
