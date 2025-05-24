import logging
from flask import Flask, render_template, request, Response, jsonify
from prometheus_flask_exporter import PrometheusMetrics
import sqlite3
import os
import base64
import pickle
import subprocess
import signal
import threading
import time

app = Flask(__name__)

# Configure logging
log_dir = "/app/logs"
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "app.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FaceRecgApp")

# Attach Prometheus metrics server on port 8000
metrics = PrometheusMetrics(app)

# metrics.start_http_server(port=8000)

# Global variables to track recognition service
recognition_process = None
recognition_active = False

def get_db_connection():
    db_path = os.path.join('/app/db', 'face_log.db')
    
    # Ensure DB directory exists
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Ensure the table exists
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS face_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        frame BLOB NOT NULL
    )
    ''')
    conn.commit()
    
    logger.debug("Database connection established and table ensured at %s", db_path)
    
    return conn

@app.route('/')
def index():
    logger.info("Serving index page, recognition_active=%s", recognition_active)
    return render_template('index.html', recognition_active=recognition_active)

@app.route('/view_logs')
def view_logs():
    try:
        conn = get_db_connection()
        logs = conn.execute('SELECT id, name, timestamp FROM face_log ORDER BY id DESC LIMIT 50').fetchall()
        conn.close()
        logger.info("Fetched %d logs for view_logs", len(logs))
        return render_template('logs.html', logs=logs)
    except Exception as e:
        logger.error("Error in /view_logs: %s", e)
        return f"Error accessing database: {str(e)}", 500

@app.route('/view_image/<int:id>')
def view_image(id):
    try:
        conn = get_db_connection()
        image_data = conn.execute('SELECT frame FROM face_log WHERE id = ?', (id,)).fetchone()
        conn.close()
        
        if image_data:
            frame_bytes = image_data['frame']
            encoded_img = base64.b64encode(frame_bytes).decode('utf-8')
            logger.info("Serving image for log id=%d", id)
            return render_template('image.html', image_data=encoded_img)
        else:
            logger.warning("Image not found for id=%d", id)
            return "Image not found", 404
    except Exception as e:
        logger.error("Error in /view_image: %s", e)
        return f"Error retrieving image: {str(e)}", 500

def is_container_running(container_name='recognition'):
    result = subprocess.run(
        ['docker', 'inspect', '-f', '{{.State.Running}}', container_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    running = result.stdout.strip() == 'true'
    logger.debug("Container '%s' running status: %s", container_name, running)
    return running

@app.route('/start_recognition', methods=['POST'])
def start_recognition():
    global recognition_process, recognition_active
    
    if recognition_active:
        logger.warning("Attempted to start recognition but it is already running")
        return jsonify({"status": "error", "message": "Recognition already running"})
    
    try:
        if not is_container_running('recognition'):
            start_proc = subprocess.run(
                ['docker', 'start', 'recognition'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            if start_proc.returncode != 0:
                logger.error("Failed to start recognition container: %s", start_proc.stderr)
                return jsonify({
                    "status": "error",
                    "message": f"Failed to start recognition container: {start_proc.stderr}"
                })
            logger.info("Recognition container started")
        
        process = subprocess.Popen(
            ["docker", "exec", "-d", "recognition", "python", "/app/recognition_service.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
            logger.error("Failed to start recognition script: %s", error_msg)
            return jsonify({
                "status": "error", 
                "message": f"Failed to start recognition script: {error_msg}"
            })
        
        time.sleep(3)
        
        check_proc = subprocess.run(
            ["docker", "exec", "recognition", "pgrep", "-f", "python /app/recognition_service.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if check_proc.returncode == 0 and check_proc.stdout.strip():
            recognition_active = True
            logger.info("Recognition script started successfully")
            return jsonify({"status": "success", "message": "Recognition started"})
        else:
            recognition_active = False
            logger.error("Recognition script failed to stay running")
            return jsonify({"status": "error", "message": "Recognition script failed to stay running"})
            
    except Exception as e:
        logger.error("Exception in /start_recognition: %s", e)
        return jsonify({"status": "error", "message": f"Failed to start recognition: {str(e)}"})

@app.route('/stop_recognition', methods=['POST'])
def stop_recognition():
    global recognition_active
    
    if not recognition_active:
        logger.warning("Attempted to stop recognition but it is not running")
        return jsonify({"status": "error", "message": "Recognition not running"})
    
    try:
        process = subprocess.Popen(
            ["docker", "exec", "recognition", "pkill", "-f", "python /app/recognition_service.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            recognition_active = False
            logger.info("Recognition script stopped successfully")
            return jsonify({"status": "success", "message": "Recognition stopped"})
        else:
            error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
            logger.error("Failed to stop recognition: %s", error_msg)
            return jsonify({
                "status": "error", 
                "message": f"Failed to stop recognition: {error_msg}"
            })
            
    except Exception as e:
        logger.error("Exception in /stop_recognition: %s", e)
        return jsonify({"status": "error", "message": f"Failed to stop recognition: {str(e)}"})

@app.route('/train', methods=['POST'])
def start_training():
    try:
        process = subprocess.Popen(
            ["docker", "exec", "training", "python", "/app/train_service.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            logger.info("Training completed successfully")
            return jsonify({"status": "success", "message": "Training completed successfully"})
        else:
            error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
            logger.error("Training failed: %s", error_msg)
            return jsonify({
                "status": "error", 
                "message": f"Training failed with exit code {process.returncode}",
                "stderr": error_msg
            })
    except Exception as e:
        logger.error("Exception in /train: %s", e)
        return jsonify({"status": "error", "message": f"Failed to start training: {str(e)}"})

@app.route('/status')
def status():
    encodings_path = os.path.join('/app/models', 'encodings.pkl')
    models_exist = os.path.exists(encodings_path)
    
    db_path = os.path.join('/app/db', 'face_log.db')
    db_exists = os.path.exists(db_path)
    record_count = 0
    
    if db_exists:
        try:
            conn = get_db_connection()
            record_count = conn.execute('SELECT COUNT(*) FROM face_log').fetchone()[0]
            conn.close()
            logger.info("Status checked: %d records in DB", record_count)
        except Exception as e:
            logger.error("Error checking database status: %s", e)
            db_exists = False
    
    try:
        process = subprocess.Popen(
            ["docker", "exec", "recognition", "pgrep", "-f", "python /app/recognition_service.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate()
        global recognition_active
        recognition_active = process.returncode == 0
        logger.info("Recognition active status checked: %s", recognition_active)
    except Exception as e:
        logger.error("Error checking recognition status: %s", e)
    
    return jsonify({
        "models_exist": models_exist,
        "db_exists": db_exists,
        "record_count": record_count,
        "recognition_active": recognition_active
    })

if __name__ == '__main__':
    logger.info("Starting Flask app")
    app.run(host='0.0.0.0', port=5002, debug=True)
