from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import urllib.parse

app = Flask(__name__)
CORS(app)  # 🔓 Permitir conexión desde frontend (localhost:3000)

@app.route('/send-alert', methods=['POST'])
def send_alert():
    try:
        data = request.json
        phone = data.get('phone')
        apikey = data.get('apiCode')
        message = data.get('message', '⚠️ Alerta: caída detectada!')

        if not phone or not apikey:
            return jsonify({'status': 'error', 'message': 'Faltan datos (phone o apiCode)'}), 400

        # 🔐 Codificar correctamente el mensaje para URL
        encoded_message = urllib.parse.quote(message)

        # 🔗 Construir URL segura
        url = f'https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_message}&apikey={apikey}'

        print(f'📤 Enviando mensaje a {phone}...')
        response = requests.get(url)

        if response.status_code == 200:
            print('✅ Mensaje enviado correctamente!')
            return jsonify({'status': 'ok', 'response': response.text})
        else:
            print('❌ Error al enviar mensaje:', response.text)
            return jsonify({'status': 'error', 'response': response.text}), 500

    except Exception as e:
        print('⚠️ Excepción capturada:', str(e))
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
