"""
Backup/Simplified version of the Flask app for Vercel deployment
This version has minimal dependencies and simplified imports
"""
from flask import Flask, request, jsonify
import os
import sys
import logging

# Simple logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'excel-translator-simple',
        'version': '1.0.0',
        'environment': {
            'python_version': sys.version,
            'working_directory': os.getcwd(),
            'has_deepl_key': bool(os.environ.get('DEEPL_API_KEY')),
            'environment_vars': list(os.environ.keys())
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

@app.route('/test')
def test():
    """Test endpoint to verify basic functionality"""
    return jsonify({
        'message': 'Test successful',
        'timestamp': str(os.times()),
        'platform': sys.platform
    })

# For Vercel
def handler(environ, start_response):
    return app(environ, start_response)

if __name__ == '__main__':
    app.run(debug=True)