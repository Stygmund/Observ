from flask import Flask
from logcore import get_logger

app = Flask(__name__)
logger = get_logger(__name__)

@app.route('/')
def index():
    logger.info("Index page accessed", extra={'context': {'endpoint': '/'}})
    return {'message': 'Hello from Deployment Paradigm!'}

@app.route('/health')
def health():
    logger.debug("Health check", extra={'context': {'status': 'healthy'}})
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
