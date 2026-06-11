#!/usr/bin/env python3
"""Test Flask app to verify basic functionality."""
from flask import Flask

app = Flask(__name__)

@app.route('/health')
def health():
    return {'status': 'ok'}, 200

if __name__ == '__main__':
    print("Starting test Flask app...")
    app.run(host='0.0.0.0', port=5000, debug=False)
