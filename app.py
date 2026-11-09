
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Cargar las variables del archivo .env
load_dotenv()

# Crear la aplicación Flask
app = Flask(__name__)

# Configuración general
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Configuración de MariaDB
app.config['MYSQL_HOST'] = os.getenv('DB_HOST')
app.config['MYSQL_USER'] = os.getenv('DB_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('DB_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('DB_NAME')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Activar protección CSRF
csrf = CSRFProtect(app)

# Inicializar conexión MySQL
mysql = MySQL(app)


# Página principal
@app.route('/')
def inicio():
    return render_template('index.html')


# Iniciar sesión
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('lCorreo', '').strip()
        password = request.form.get('lPass', '')

        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                """
                SELECT id_usuario, nombre, apellidos, email,
                       pass_hash, id_rol
                FROM usuarios
                WHERE email = %s
                """,
                (correo,)
            )
            usuario = cursor.fetchone()
            cursor.close()

            if usuario and check_password_hash(usuario['pass_hash'], password):
                session['id_usuario'] = usuario['id_usuario']
                session['nombre'] = usuario['nombre']
                session['id_rol'] = usuario['id_rol']

                flash('Bienvenido a Papelia.', 'success')
                return redirect(url_for('perfil'))

            flash('Correo o contraseña incorrectos.', 'danger')

        except Exception as error:
            print('Error al iniciar sesión:', error)
            flash('No fue posible iniciar sesión.', 'danger')

    return render_template('login.html')


# Registro de usuarios
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        correo = request.form.get('correo', '').strip()
        password = request.form.get('password', '')
        confirmar = request.form.get('confirmar_password', '')

        if not nombre or not correo or not password:
            flash('Completa todos los campos.', 'warning')
            return redirect(url_for('registro'))

        if password != confirmar:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('registro'))

        if len(password) < 8:
            flash('La contraseña debe tener al menos 8 caracteres.', 'warning')
            return redirect(url_for('registro'))

        try:
            cursor = mysql.connection.cursor()

            # Comprobar si el correo ya existe
            cursor.execute(
                'SELECT id_usuario FROM usuarios WHERE email = %s',
                (correo,)
            )

            if cursor.fetchone():
                cursor.close()
                flash('Este correo ya está registrado.', 'warning')
                return redirect(url_for('registro'))

            # Obtener el ID del rol Cliente
            cursor.execute(
                "SELECT id_rol FROM roles WHERE nombre_rol = %s",
                ('Cliente',)
            )
            rol = cursor.fetchone()

            if not rol:
                cursor.close()
                flash('No se encontró el rol Cliente.', 'danger')
                return redirect(url_for('registro'))

            password_hash = generate_password_hash(password)

            cursor.execute(
                """
                INSERT INTO usuarios (nombre, apellidos, email, pass_hash, id_rol)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (nombre, '', correo, password_hash, rol['id_rol'])
            )

            mysql.connection.commit()
            cursor.close()

            flash('Registro realizado correctamente.', 'success')
            return redirect(url_for('login'))

        except Exception as error:
            mysql.connection.rollback()
            print('Error en el registro:', error)
            flash('Ocurrió un error al registrar el usuario.', 'danger')

    return render_template('formulario.html')


# Perfil del usuario
@app.route('/perfil')
def perfil():
    if 'id_usuario' not in session:
        flash('Inicia sesión para acceder al perfil.', 'warning')
        return redirect(url_for('login'))

    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            """
            SELECT u.id_usuario, u.nombre, u.apellidos, u.email,
                   r.nombre_rol AS rol
            FROM usuarios u
            INNER JOIN roles r ON u.id_rol = r.id_rol
            WHERE u.id_usuario = %s
            """,
            (session['id_usuario'],)
        )
        usuario = cursor.fetchone()
        cursor.close()

        if not usuario:
            session.clear()
            flash('No se encontró el usuario.', 'danger')
            return redirect(url_for('login'))

        return render_template('perfil.html', usuario=usuario)

    except Exception as error:
        print('Error al cargar el perfil:', error)
        flash('No fue posible cargar el perfil.', 'danger')
        return redirect(url_for('inicio'))


# Cerrar sesión
@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada correctamente.', 'success')
    return redirect(url_for('inicio'))


# Catálogo de productos
@app.route('/catalogo')
def catalogo():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute(
            """
            SELECT p.id_producto, p.nombre, p.precio, p.stock,
                   c.nombre AS categoria
            FROM productos p
            INNER JOIN categorias c
            ON p.id_categoria = c.id_categoria
            ORDER BY p.nombre
            """
        )
        productos = cursor.fetchall()
        cursor.close()

        return render_template('catalogo.html', productos=productos)

    except Exception as error:
        print('Error al cargar el catálogo:', error)
        flash('No fue posible cargar el catálogo.', 'danger')
        return redirect(url_for('inicio'))


# Ejecutar el servidor
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

