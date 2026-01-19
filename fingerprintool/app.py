from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

def get_client_ip():
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0]
    else:
        ip = request.remote_addr
    return ip

@app.route('/')
def index():
    ip_addr = get_client_ip()
    return render_template('index.html', ip=ip_addr)

@app.route('/api/ip')
def api_ip():
    return jsonify({"ip": get_client_ip()})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
