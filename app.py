from flask import Flask, render_template, request, session, flash, redirect, url_for
import random
import string
import sqlite3
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-0219'


connection = sqlite3.connect('ggg.db')
cursor = connection.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS Пользователи (
        id INTEGER PRIMARY KEY,
        имя_пользователя TEXT UNIQUE NOT NULL,
        пароль TEXT NOT NULL,
        роль TEXT DEFAULT 'user'
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS Пароли (
        id INTEGER PRIMARY KEY,
        id_пользователя INTEGER NOT NULL,
        сайт TEXT NOT NULL,
        логин TEXT NOT NULL,
        пароль TEXT NOT NULL,
        FOREIGN KEY (id_пользователя) REFERENCES Пользователи (id)
    )
''')

connection.commit()
connection.close()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def root():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('generator'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        connection = sqlite3.connect('ggg.db')
        cursor = connection.cursor()
        cursor.execute('SELECT * FROM Пользователи WHERE имя_пользователя = ?', (username,))
        user = cursor.fetchone()
        connection.close()

        if user and user[2] == password:
            session['username'] = user[1]
            session['role'] = user[3]
            flash(f'Добро пожаловать, {username}!', 'success')
            return redirect(url_for('generator'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username' in session:
        return redirect(url_for('generator'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not password:
            flash('Все поля обязательны для заполнения', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')

        if len(username) < 3:
            flash('Имя пользователя должно содержать минимум 3 символа', 'error')
            return render_template('register.html')

        if len(password) < 4:
            flash('Пароль должен содержать минимум 4 символа', 'error')
            return render_template('register.html')

        connection = sqlite3.connect('ggg.db')
        cursor = connection.cursor()

        cursor.execute('SELECT MAX(id) FROM Пользователи')
        max_id = cursor.fetchone()[0] or 0
        new_id = max_id + 1

        try:
            cursor.execute(
                'INSERT INTO Пользователи (id, имя_пользователя, пароль, роль) VALUES (?, ?, ?, ?)',
                (new_id, username, password, 'user')
            )
            connection.commit()
            connection.close()
            flash('Регистрация прошла успешно! Теперь вы можете войти в систему.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            connection.close()
            flash('Пользователь с таким именем уже существует', 'error')

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))


@app.route('/generator', methods=['GET', 'POST'])
@login_required
def generator():
    passwords = []
    length = 12
    complexity = "medium"

    connection = sqlite3.connect('ggg.db')
    cursor = connection.cursor()
    cursor.execute('''
        SELECT п.* FROM Пароли п 
        JOIN Пользователи ю ON п.id_пользователя = ю.id 
        WHERE ю.имя_пользователя = ?
    ''', (session['username'],))

    saved_passwords = []
    for row in cursor.fetchall():
        saved_passwords.append({
            'id': row[0],
            'website': row[2],
            'login': row[3],
            'password': row[4]
        })
    connection.close()

    if request.method == 'POST':
        if 'generate' in request.form:
            try:
                length = int(request.form.get('length', 12))
                length = max(4, min(length, 50))
            except (ValueError, TypeError):
                length = 12

            complexity = request.form.get('complexity', 'medium')
            chars = {
                'easy': string.ascii_lowercase,
                'medium': string.ascii_letters + string.digits,
                'hard': string.ascii_letters + string.digits + "!@#$%^&*"
            }
            passwords = [''.join(random.choice(chars.get(complexity, chars['medium'])) for _ in range(length))]

        elif 'save' in request.form:
            website = request.form.get('website')
            login = request.form.get('login')
            password = request.form.get('password')

            if not website or not login or not password:
                flash('Пожалуйста, заполните все поля для сохранения пароля.', 'error')
            else:
                connection = sqlite3.connect('ggg.db')
                cursor = connection.cursor()

                # Получаем ID пользователя
                cursor.execute('SELECT id FROM Пользователи WHERE имя_пользователя = ?', (session['username'],))
                user_row = cursor.fetchone()

                if user_row:
                    # Находим максимальный ID для нового пароля
                    cursor.execute('SELECT MAX(id) FROM Пароли')
                    max_id = cursor.fetchone()[0] or 0
                    new_id = max_id + 1

                    cursor.execute(
                        'INSERT INTO Пароли (id, id_пользователя, сайт, логин, пароль) VALUES (?, ?, ?, ?, ?)',
                        (new_id, user_row[0], website, login, password)
                    )
                    connection.commit()
                    flash('Пароль сохранен!', 'success')

                    # Обновляем список паролей
                    cursor.execute('SELECT * FROM Пароли WHERE id_пользователя = ?', (user_row[0],))
                    saved_passwords = [{'id': row[0], 'website': row[2], 'login': row[3], 'password': row[4]} for row in
                                       cursor.fetchall()]
                    passwords = []
                connection.close()

        elif 'delete' in request.form:
            password_id = request.form.get('password_id')
            if password_id:
                connection = sqlite3.connect('ggg.db')
                cursor = connection.cursor()
                cursor.execute('''
                    DELETE FROM Пароли 
                    WHERE id = ? AND id_пользователя = (
                        SELECT id FROM Пользователи WHERE имя_пользователя = ?
                    )
                ''', (password_id, session['username']))
                connection.commit()

                if cursor.rowcount > 0:
                    flash('Пароль удален!', 'success')
                    # Обновляем список паролей
                    cursor.execute('SELECT id FROM Пользователи WHERE имя_пользователя = ?', (session['username'],))
                    user_row = cursor.fetchone()
                    if user_row:
                        cursor.execute('SELECT * FROM Пароли WHERE id_пользователя = ?', (user_row[0],))
                        saved_passwords = [{'id': row[0], 'website': row[2], 'login': row[3], 'password': row[4]} for
                                           row in cursor.fetchall()]
                else:
                    flash('Ошибка при удалении пароля', 'error')
                connection.close()

    return render_template('index.html',
                           passwords=passwords,
                           length=length,
                           complexity=complexity,
                           username=session.get('username'),
                           saved_passwords=saved_passwords)


@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html',
                           username=session.get('username'),
                           role=session.get('role'))


@app.route('/admin')
@login_required
def admin():
    if session.get('role') != 'admin':
        flash('У вас нет прав для доступа к этой странице', 'error')
        return redirect(url_for('generator'))

    connection = sqlite3.connect('ggg.db')
    cursor = connection.cursor()

    users_count = cursor.execute('SELECT COUNT(*) FROM Пользователи').fetchone()[0]
    passwords_count = cursor.execute('SELECT COUNT(*) FROM Пароли').fetchone()[0]

    connection.close()

    return render_template('admin.html',
                           username=session.get('username'),
                           users_count=users_count,
                           passwords_count=passwords_count)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)