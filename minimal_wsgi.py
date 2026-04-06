"""Minimal WSGI app for Railway deployment diagnostics."""
import os
from flask import Flask, jsonify

app = Flask(__name__)

PORT = os.environ.get("PORT", "not_set")


@app.route("/health")
@app.route("/")
def health():
    return jsonify({
        "status": "ok",
        "port_env": PORT,
        "version": "minimal-2.0"
    })
