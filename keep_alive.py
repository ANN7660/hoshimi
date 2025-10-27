from flask import Flask
from threading import Thread

app = Flask(__name__)  # Changé de '' à __name__

@app.route('/')
def home():
    return "🤖 Heiwa Bot est en ligne ✅"

@app.route('/health')
def health():
    return {"status": "online", "bot": "Heiwa"}, 200

def run():
    app.run(host="0.0.0.0", port=8080, debug=False)

def keep_alive():
    t = Thread(target=run, daemon=True)  # Ajouté daemon=True
    t.start()
