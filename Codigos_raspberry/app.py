from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from uuid import uuid4
import os
from database.usuario.usuario_db import UsuarioDB
from werkzeug.security import generate_password_hash, check_password_hash
from database.usuario.contacto_db import ContactoDB
from database.dispositivos.raspberry_db import RaspberryDB

# Configurar rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_FOLDER = os.path.join(BASE_DIR, 'Pagina App de emergencia')

app = Flask(__name__, static_folder=WEB_FOLDER, static_url_path='')
CORS(app)

usuario_db = UsuarioDB()
contacto_db = ContactoDB()
raspberry_db = RaspberryDB()

# Configuración del servidor
SERVER_IP = os.getenv('SERVER_IP', '0.0.0.0')
SERVER_PORT = int(os.getenv('SERVER_PORT', 5000))
SSL_CERT_FILE = os.getenv('SSL_CERT_FILE')
SSL_KEY_FILE = os.getenv('SSL_KEY_FILE')
SSL_ADHOC = os.getenv('SSL_ADHOC', 'false').lower() == 'true'


def obtener_contexto_ssl():
    if SSL_CERT_FILE and SSL_KEY_FILE:
        return SSL_CERT_FILE, SSL_KEY_FILE

    if SSL_ADHOC:
        return 'adhoc'

    return None


@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """Registro de usuario con email y contraseña (hash)."""
    try:
        datos = request.json
        if not datos or 'email' not in datos or 'password' not in datos:
            return jsonify({'error': 'email y password son requeridos'}), 400

        email = datos.get('email')
        nombre = datos.get('nombre', 'Usuario')
        password = datos.get('password')

        # Verificar si ya existe
        usuario_existente = usuario_db.obtener_usuario_por_email(email)
        if usuario_existente:
            return jsonify({'error': 'Usuario ya existe'}), 409

        usuario_id = str(uuid4())
        hashed = generate_password_hash(password)

        usuario_db.registrar_usuario(
            usuario_id=usuario_id,
            usuario_nombre=nombre,
            usuario_email=email,
            usuario_telefono='',
            usuario_activo=True,
            usuario_familiar_nombre='',
            usuario_familiar_telefono='',
            usuario_password=hashed
        )

        return jsonify({'usuario_id': usuario_id, 'mensaje': 'Usuario creado exitosamente'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login_user():
    """Inicio de sesión con email y password (verifica hash)."""
    try:
        datos = request.json
        if not datos or 'email' not in datos or 'password' not in datos:
            return jsonify({'error': 'email y password son requeridos'}), 400

        email = datos.get('email')
        password = datos.get('password')

        usuario = usuario_db.obtener_usuario_por_email(email)
        if not usuario:
            return jsonify({'error': 'Credenciales inválidas'}), 401

        # usuario tuple: id, nombre, email, telefono, activo, fam_nombre, fam_tel, password
        stored_hash = usuario[7]
        if not stored_hash:
            return jsonify({'error': 'Usuario no tiene contraseña establecida'}), 401

        if not check_password_hash(stored_hash, password):
            return jsonify({'error': 'Credenciales inválidas'}), 401

        usuario_id = str(usuario[0])
        return jsonify({'usuario_id': usuario_id, 'mensaje': 'Login exitoso'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/usuarios/<usuario_id>', methods=['GET'])
def obtener_usuario(usuario_id):
    """
    Obtiene los datos de un usuario específico.
    """
    try:
        usuarios = usuario_db.obtener_usuarios()
        
        for usuario in usuarios:
            if str(usuario[0]) == usuario_id:
                return jsonify({
                    'usuario_id': str(usuario[0]),
                    'nombre': usuario[1],
                    'email': usuario[2],
                    'telefono': usuario[3],
                    'activo': usuario[4],
                    'familiar_nombre': usuario[5],
                    'familiar_telefono': usuario[6]
                }), 200
        
        return jsonify({'error': 'Usuario no encontrado'}), 404
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/usuarios/<usuario_id>', methods=['PUT'])
def actualizar_usuario(usuario_id):
    """
    Actualiza los datos de un usuario.
    Puede actualizar: nombre, teléfono,familiar_nombre, familiar_telefono
    """
    try:
        datos = request.json
        
        # Obtener usuario actual
        usuarios = usuario_db.obtener_usuarios()
        usuario = None
        for u in usuarios:
            if str(u[0]) == usuario_id:
                usuario = u
                break
        
        if not usuario:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        # Actualizar con los datos proporcionados
        nombre = datos.get('nombre')
        telefono = datos.get('telefono')
        familiar_nombre = datos.get('familiar_nombre')
        familiar_telefono = datos.get('familiar_telefono')
        
        # Usar el nuevo método de actualización múltiple
        usuario_db.actualizar_usuario(
            usuario_id=usuario_id,
            nombre=nombre,
            telefono=telefono,
            familiar_nombre=familiar_nombre,
            familiar_telefono=familiar_telefono
        )
        
        return jsonify({
            'mensaje': 'Usuario actualizado correctamente',
            'usuario_id': usuario_id,
            'datos_actualizados': {
                'nombre': nombre,
                'telefono': telefono,
                'familiar_nombre': familiar_nombre,
                'familiar_telefono': familiar_telefono
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ================ ENDPOINTS DE CONTACTOS ================

@app.route('/api/usuarios/<usuario_id>/contactos', methods=['GET'])
def obtener_contactos_usuario(usuario_id):
    """
    Obtiene todos los contactos de un usuario.
    """
    try:
        contactos = contacto_db.obtener_contactos_usuario(usuario_id)
        
        contactos_lista = []
        for c in contactos:
            contactos_lista.append({
                'contacto_id': str(c[0]),
                'usuario_id': str(c[1]),
                'nombre': c[2],
                'telefono': c[3],
                'estado': c[4]
            })
        
        return jsonify({
            'contactos': contactos_lista,
            'total': len(contactos_lista)
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/usuarios/<usuario_id>/contactos', methods=['POST'])
def crear_contacto(usuario_id):
    """
    Crea un nuevo contacto de emergencia para un usuario.
    """
    try:
        datos = request.json
        
        if not datos or 'nombre' not in datos or 'telefono' not in datos:
            return jsonify({'error': 'nombre y telefono son requeridos'}), 400
        
        contacto_id = str(uuid4())
        
        contacto_db.guardar_contacto(
            contacto_id=contacto_id,
            usuario_id=usuario_id,
            contacto_nombre=datos['nombre'],
            contacto_telefono=datos['telefono'],
            contacto_estado=datos.get('estado', True)
        )
        
        return jsonify({
            'contacto_id': contacto_id,
            'mensaje': 'Contacto creado exitosamente'
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/contactos/<contacto_id>', methods=['PUT'])
def actualizar_contacto(contacto_id):
    """
    Actualiza un contacto de emergencia.
    """
    try:
        datos = request.json
        
        contacto_db.actualizar_contacto(
            contacto_id=contacto_id,
            contacto_nombre=datos.get('nombre'),
            contacto_telefono=datos.get('telefono'),
            contacto_estado=datos.get('estado')
        )
        
        return jsonify({
            'mensaje': 'Contacto actualizado correctamente',
            'contacto_id': contacto_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/contactos/<contacto_id>', methods=['DELETE'])
def eliminar_contacto(contacto_id):
    """
    Elimina un contacto de emergencia.
    """
    try:
        contacto_db.eliminar_contacto(contacto_id)
        
        return jsonify({
            'mensaje': 'Contacto eliminado correctamente',
            'contacto_id': contacto_id
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/raspberry/vincular', methods=['POST'])
def vincular_raspberry():
    datos = request.json

    usuario_id = datos.get("usuario_id")
    raspberry_id = datos.get("raspberry_id")

    raspberry_db.vincular_usuario(raspberry_id, usuario_id)
 
    return jsonify({
        "mensaje": "Raspberry vinculada correctamente",
        "raspberry_id": raspberry_id,
        "usuario_id": usuario_id
    }), 200


# ================ ENDPOINTS ESTÁTICOS ================

@app.route('/api/health', methods=['GET'])
def health():
    """
    Endpoint para verificar que el servidor está activo.
    """
    return jsonify({'status': 'ok'}), 200


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_static(path):
    """
    Sirve archivos estáticos de la carpeta web.
    Si el archivo no existe o es una carpeta, sirve index.html
    """
    # Construir la ruta del archivo
    file_path = os.path.join(WEB_FOLDER, path)
    
    # Si es un archivo que existe, servirlo
    if os.path.isfile(file_path):
        return send_from_directory(WEB_FOLDER, path)
    
    # Si no existe, servir index.html
    if os.path.isfile(os.path.join(WEB_FOLDER, 'index.html')):
        return send_from_directory(WEB_FOLDER, 'index.html')
    
    return jsonify({'error': 'Archivo no encontrado'}), 404


if __name__ == '__main__':
    ssl_context = obtener_contexto_ssl()
    protocolo = 'https' if ssl_context else 'http'

    print(f'Servidor disponible en {protocolo}://{SERVER_IP}:{SERVER_PORT}')
    if SSL_ADHOC and not SSL_CERT_FILE:
        print(
            'Aviso: el certificado adhoc no es confiable para Android. '
            'Usa SSL_CERT_FILE y SSL_KEY_FILE para Web Bluetooth.'
        )

    app.run(
        host=SERVER_IP,
        port=SERVER_PORT,
        debug=True,
        ssl_context=ssl_context
    )
