from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from app.models import verify_password, count_users, create_user, get_db, close_db
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated

@auth_bp.teardown_app_request
def teardown_db(exception):
    close_db(exception)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Primeiro acesso: redireciona para setup
    if count_users() == 0:
        return redirect(url_for('auth.setup'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = verify_password(username, password)
        if user:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard.index'))
        flash('Usuário ou senha inválidos.', 'error')

    return render_template('auth/login.html')

@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    if count_users() > 0:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        if not username or not password:
            flash('Preencha todos os campos.', 'error')
        elif password != confirm:
            flash('As senhas não coincidem.', 'error')
        elif len(password) < 8:
            flash('A senha deve ter pelo menos 8 caracteres.', 'error')
        else:
            create_user(username, password)
            flash('Usuário criado. Faça login para continuar.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/setup.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
