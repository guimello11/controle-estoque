from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, date
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///estoque.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Produto(db.Model):
    __tablename__ = 'produto'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(200))
    quantidade = db.Column(db.Integer, nullable=False)
    preco_compra = db.Column(db.Float, nullable=False, default=0.0)
    preco_venda = db.Column(db.Float, nullable=False, default=0.0)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow)
    pedidos = db.relationship('Pedido', backref='produto', lazy=True)

class Pedido(db.Model):
    __tablename__ = 'pedido'
    id = db.Column(db.Integer, primary_key=True)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'compra' ou 'venda'
    quantidade = db.Column(db.Integer, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    data_pedido = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pendente')  # 'pendente', 'concluído', 'cancelado'
    observacoes = db.Column(db.Text)

class Reserva(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_cliente = db.Column(db.String(150), nullable=False)
    whatsapp = db.Column(db.String(20), nullable=False)
    data_reserva = db.Column(db.Date, nullable=False)
    horario = db.Column(db.Time, nullable=False)
    tipo_refeicao = db.Column(db.String(10), nullable=False)  # almoço ou jantar
    status = db.Column(db.String(20), default='confirmada')  # confirmada, cancelada, concluída
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    acao = db.Column(db.String(200), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    tipo = db.Column(db.String(50), nullable=False)  # 'produto', 'pedido', 'reserva', 'usuario'
    
    usuario = db.relationship('User', backref='logs')

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except:
        return None

def init_db():
    with app.app_context():
        db.create_all()
        # Verificar se existe usuário admin
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = User(username='admin', password_hash=hashed_password, is_admin=True)
            db.session.add(admin)
            db.session.commit()

def registrar_log(acao, tipo):
    if current_user.is_authenticated:
        log = Log(usuario_id=current_user.id, acao=acao, tipo=tipo)
        db.session.add(log)
        db.session.commit()

def verificar_estoque_baixo():
    produtos_baixo_estoque = Produto.query.filter(Produto.quantidade < 10).all()
    return produtos_baixo_estoque

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor, preencha todos os campos', 'danger')
            return render_template('login.html')
            
        try:
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                flash('Usuário ou senha inválidos', 'danger')
        except Exception as e:
            flash('Erro ao fazer login. Tente novamente.', 'danger')
            print(f"Login error: {e}")
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/usuarios')
@login_required
def usuarios():
    if not current_user.is_admin:
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    usuarios = User.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

@app.route('/adicionar_usuario', methods=['POST'])
@login_required
def adicionar_usuario():
    if not current_user.is_admin:
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    username = request.form['username']
    password = request.form['password']
    is_admin = 'is_admin' in request.form
    
    if User.query.filter_by(username=username).first():
        flash('Nome de usuário já existe', 'danger')
        return redirect(url_for('usuarios'))
    
    user = User(username=username, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    flash('Usuário criado com sucesso', 'success')
    return redirect(url_for('usuarios'))

@app.route('/deletar_usuario/<int:id>')
@login_required
def deletar_usuario(id):
    if not current_user.is_admin:
        flash('Acesso negado', 'danger')
        return redirect(url_for('index'))
    
    user = User.query.get_or_404(id)
    if user.username == 'admin':
        flash('Não é possível deletar o usuário admin', 'danger')
        return redirect(url_for('usuarios'))
    
    db.session.delete(user)
    db.session.commit()
    flash('Usuário deletado com sucesso', 'success')
    return redirect(url_for('usuarios'))

@app.route('/')
@login_required
def index():
    return redirect(url_for('produtos'))

@app.route('/produtos')
@login_required
def produtos():
    produtos = Produto.query.all()
    return render_template('produtos.html', produtos=produtos)

@app.route('/adicionar_produto', methods=['POST'])
@login_required
def adicionar_produto():
    if not current_user.is_admin:
        flash('Apenas administradores podem cadastrar produtos', 'danger')
        return redirect(url_for('produtos'))

    try:
        nome = request.form['nome']
        descricao = request.form.get('descricao', '')
        quantidade = int(request.form['quantidade'])
        preco_compra = float(request.form['preco_compra'])
        preco_venda = float(request.form['preco_venda'])
        
        produto = Produto(
            nome=nome,
            descricao=descricao,
            quantidade=quantidade,
            preco_compra=preco_compra,
            preco_venda=preco_venda,
            data_atualizacao=datetime.utcnow()
        )
        
        db.session.add(produto)
        db.session.commit()
        registrar_log(f'Adicionou produto: {nome}', 'produto')
        flash('Produto adicionado com sucesso!', 'success')
    except Exception as e:
        print(f"Erro ao adicionar produto: {str(e)}")
        flash('Erro ao adicionar produto!', 'danger')
        db.session.rollback()
    
    return redirect(url_for('produtos'))

@app.route('/retirar', methods=['POST'])
@login_required
def retirar():
    produto_id = request.form['produto_id']
    quantidade = int(request.form['quantidade'])
    
    produto = Produto.query.get_or_404(produto_id)
    if produto.quantidade >= quantidade:
        produto.quantidade -= quantidade
        produto.data_atualizacao = datetime.utcnow()
        
        # Registrar pedido de venda
        pedido = Pedido(
            produto_id=produto_id,
            tipo='venda',
            quantidade=quantidade,
            preco_unitario=produto.preco_venda,
            status='concluído'
        )
        db.session.add(pedido)
        db.session.commit()
        
        registrar_log(f'Retirou {quantidade} unidades de {produto.nome}', 'produto')
        
        if produto.quantidade < 10:
            flash(f'Atenção: O produto {produto.nome} está com estoque baixo ({produto.quantidade} unidades)!', 'warning')
        else:
            flash('Quantidade retirada com sucesso!', 'success')
    else:
        flash('Quantidade insuficiente em estoque!', 'danger')
    
    return redirect(url_for('produtos'))

@app.route('/produto/<int:id>')
@login_required
def get_produto(id):
    produto = Produto.query.get_or_404(id)
    return jsonify({
        'id': produto.id,
        'nome': produto.nome,
        'descricao': produto.descricao,
        'quantidade': produto.quantidade,
        'preco_compra': produto.preco_compra,
        'preco_venda': produto.preco_venda
    })

@app.route('/editar_produto/<int:id>', methods=['POST'])
@login_required
def editar_produto(id):
    if not current_user.is_admin:
        flash('Apenas administradores podem editar produtos', 'danger')
        return redirect(url_for('produtos'))

    produto = Produto.query.get_or_404(id)
    try:
        produto.nome = request.form['nome']
        produto.descricao = request.form.get('descricao', '')
        produto.quantidade = int(request.form['quantidade'])
        produto.preco_compra = float(request.form['preco_compra'])
        produto.preco_venda = float(request.form['preco_venda'])
        produto.data_atualizacao = datetime.utcnow()
        
        db.session.commit()
        registrar_log(f'Editou produto: {produto.nome}', 'produto')
        flash('Produto atualizado com sucesso!', 'success')
    except Exception as e:
        print(f"Erro ao editar produto: {str(e)}")
        flash('Erro ao editar produto!', 'danger')
        db.session.rollback()
    
    return redirect(url_for('produtos'))

@app.route('/excluir_produto/<int:id>')
@login_required
def excluir_produto(id):
    if not current_user.is_admin:
        flash('Apenas administradores podem excluir produtos', 'danger')
        return redirect(url_for('produtos'))

    produto = Produto.query.get_or_404(id)
    try:
        nome = produto.nome
        db.session.delete(produto)
        db.session.commit()
        registrar_log(f'Excluiu produto: {nome}', 'produto')
        flash('Produto excluído com sucesso!', 'success')
    except Exception as e:
        print(f"Erro ao excluir produto: {str(e)}")
        flash('Erro ao excluir produto!', 'danger')
        db.session.rollback()
    
    return redirect(url_for('produtos'))

@app.route('/pedidos')
@login_required
def pedidos():
    if not current_user.is_admin:
        flash('Acesso negado. Apenas administradores podem acessar esta página.', 'danger')
        return redirect(url_for('produtos'))
    pedidos = Pedido.query.order_by(Pedido.data_pedido.desc()).all()
    produtos = Produto.query.all()
    return render_template('pedidos.html', pedidos=pedidos, produtos=produtos)

@app.route('/adicionar_pedido', methods=['POST'])
@login_required
def adicionar_pedido():
    if not current_user.is_admin:
        flash('Acesso negado. Apenas administradores podem adicionar pedidos.', 'danger')
        return redirect(url_for('pedidos'))
        
    produto_id = request.form.get('produto_id')
    tipo = request.form.get('tipo')
    quantidade = request.form.get('quantidade')
    preco_unitario = request.form.get('preco_unitario')
    status = request.form.get('status')
    
    try:
        produto = Produto.query.get_or_404(produto_id)
        quantidade = int(quantidade)
        preco_unitario = float(preco_unitario)
        
        if tipo == 'venda' and quantidade > produto.quantidade:
            flash('Quantidade insuficiente em estoque!', 'danger')
            return redirect(url_for('pedidos'))
        
        pedido = Pedido(
            produto_id=produto_id,
            tipo=tipo,
            quantidade=quantidade,
            preco_unitario=preco_unitario,
            status=status
        )
        
        if tipo == 'compra':
            produto.quantidade += quantidade
            registrar_log(f'Compra de {quantidade} unidades de {produto.nome}', 'pedido')
        else:  # venda
            produto.quantidade -= quantidade
            registrar_log(f'Venda de {quantidade} unidades de {produto.nome}', 'pedido')
        
        db.session.add(pedido)
        db.session.commit()
        flash('Pedido adicionado com sucesso!', 'success')
    except ValueError:
        flash('Valores inválidos!', 'danger')
    except:
        flash('Erro ao adicionar pedido!', 'danger')
    
    return redirect(url_for('pedidos'))

@app.route('/editar_pedido/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_pedido(id):
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('pedidos'))

    pedido = Pedido.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            pedido.status = request.form.get('status')
            pedido.observacoes = request.form.get('observacoes')
            db.session.commit()
            registrar_log(f'Editou pedido {pedido.id}', 'pedido')
            flash('Pedido atualizado com sucesso!', 'success')
        except Exception as e:
            flash('Erro ao atualizar pedido.', 'danger')
            print(e)
        return redirect(url_for('pedidos'))

    return render_template('editar_pedido.html', pedido=pedido)

@app.route('/reservas')
@login_required
def reservas():
    data_filtro = request.args.get('data')
    if data_filtro:
        data = datetime.strptime(data_filtro, '%Y-%m-%d').date()
        reservas = Reserva.query.filter_by(data_reserva=data).order_by(Reserva.horario).all()
    else:
        data = date.today()
        reservas = Reserva.query.filter_by(data_reserva=data).order_by(Reserva.horario).all()
    return render_template('reservas.html', reservas=reservas, data_atual=data)

@app.route('/adicionar_reserva', methods=['POST'])
@login_required
def adicionar_reserva():
    if not current_user.is_admin:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('reservas'))

    nome_cliente = request.form.get('nome_cliente')
    whatsapp = request.form.get('whatsapp')
    data_str = request.form.get('data_reserva')
    horario_str = request.form.get('horario')
    tipo_refeicao = request.form.get('tipo_refeicao')

    try:
        data_reserva = datetime.strptime(data_str, '%Y-%m-%d').date()
        horario = datetime.strptime(horario_str, '%H:%M').time()

        reserva = Reserva(
            nome_cliente=nome_cliente,
            whatsapp=whatsapp,
            data_reserva=data_reserva,
            horario=horario,
            tipo_refeicao=tipo_refeicao
        )
        
        db.session.add(reserva)
        db.session.commit()
        registrar_log(f'Nova reserva para {nome_cliente} em {data_str}', 'reserva')
        flash('Reserva adicionada com sucesso!', 'success')
    except Exception as e:
        flash('Erro ao adicionar reserva.', 'danger')
        print(e)

    return redirect(url_for('reservas'))

@app.route('/editar_reserva/<int:id>', methods=['POST'])
@login_required
def editar_reserva(id):
    if not current_user.is_admin:
        flash('Apenas administradores podem editar reservas', 'danger')
        return redirect(url_for('reservas'))
    
    reserva = Reserva.query.get_or_404(id)
    try:
        reserva.nome_cliente = request.form['nome_cliente']
        reserva.whatsapp = request.form['whatsapp']
        reserva.data_reserva = datetime.strptime(request.form['data'], '%Y-%m-%d').date()
        reserva.horario = datetime.strptime(request.form['horario'], '%H:%M').time()
        reserva.tipo_refeicao = request.form['tipo_refeicao']
        reserva.status = request.form['status']
        
        db.session.commit()
        registrar_log(f'Editou reserva {reserva.id}', 'reserva')
        flash('Reserva atualizada com sucesso!', 'success')
    except:
        flash('Erro ao atualizar reserva!', 'danger')
    
    return redirect(url_for('reservas'))

@app.route('/excluir_reserva/<int:id>', methods=['POST'])
@login_required
def excluir_reserva(id):
    if not current_user.is_admin:
        flash('Apenas administradores podem excluir reservas', 'danger')
        return redirect(url_for('reservas'))
    
    reserva = Reserva.query.get_or_404(id)
    try:
        db.session.delete(reserva)
        db.session.commit()
        registrar_log(f'Excluiu reserva {reserva.id}', 'reserva')
        flash('Reserva excluída com sucesso!', 'success')
    except:
        flash('Erro ao excluir reserva!', 'danger')
    
    return redirect(url_for('reservas'))

@app.route('/logs')
@login_required
def logs():
    if not current_user.is_admin:
        flash('Acesso negado. Apenas administradores podem ver os logs.', 'error')
        return redirect(url_for('produtos'))
    
    logs = Log.query.order_by(Log.data_hora.desc()).all()
    return render_template('logs.html', logs=logs)

@app.route('/limpar_logs')
@login_required
def limpar_logs():
    if not current_user.is_admin:
        flash('Acesso negado. Apenas administradores podem limpar os logs.', 'error')
        return redirect(url_for('produtos'))
    
    try:
        Log.query.delete()
        db.session.commit()
        flash('Logs limpos com sucesso!', 'success')
    except Exception as e:
        print(f"Erro ao limpar logs: {str(e)}")
        flash('Erro ao limpar logs!', 'danger')
        db.session.rollback()
    
    return redirect(url_for('logs'))

@app.route('/verificar_estoque')
@login_required
def verificar_estoque():
    produtos = Produto.query.filter(Produto.quantidade < 10).all()
    return jsonify({
        'produtos': [{'nome': p.nome, 'quantidade': p.quantidade} for p in produtos]
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    init_db()
    app.run(host='0.0.0.0', port=port)
