import os
import sqlite3
from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"

USER_DB = "database.db"
SENSOR_DB = "sensor.db"
sensor_data = {}

# Initialize user database
def init_user_db():
    if not os.path.exists(USER_DB):
        conn = sqlite3.connect(USER_DB)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                phone TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()

# Initialize sensor database
def init_sensor_db():
    if not os.path.exists(SENSOR_DB):
        conn = sqlite3.connect(SENSOR_DB)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                soil_moisture REAL,
                light_intensity REAL,
                soil_ph REAL,
                soil_temp REAL,
                ambient_temp REAL,
                ambient_humidity REAL,
                suitability TEXT,
                latitude REAL,
                longitude REAL
            )
        ''')
        conn.commit()
        conn.close()

init_user_db()
init_sensor_db()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(USER_DB)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        if cursor.fetchone():
            flash("Username already exists!", "danger")
            return redirect(url_for('register'))

        cursor.execute("INSERT INTO users (name, address, phone, username, password) VALUES (?, ?, ?, ?, ?)", 
                       (name, address, phone, username, password))
        conn.commit()
        conn.close()

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect(USER_DB)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user'] = username
            flash("Login successful!", "success")
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials!", "danger")

    return render_template('login.html')

def calculate_suitability(data):
    if data["soil_moisture"] and data["soil_ph"]:
        if 5.5 <= data["soil_ph"] <= 7.5 and data["soil_moisture"] > 40:
            return "Good"
        else:
            return "Poor"
    return "Unknown"

@app.route('/sensor', methods=['POST'])
def receive_sensor_data():
    global sensor_data
    sensor_data = request.json
    print("Received:", sensor_data)
    suitability = calculate_suitability(sensor_data)
    conn = sqlite3.connect(SENSOR_DB)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO sensor_data (
        timestamp, soil_moisture, light_intensity, soil_ph, soil_temp, 
        ambient_temp, ambient_humidity, suitability, latitude, longitude
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', (
    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    sensor_data.get("soil_moisture"),
    sensor_data.get("light_intensity"),
    sensor_data.get("soil_ph"),
    sensor_data.get("soil_temp"),
    sensor_data.get("ambient_temp"),
    sensor_data.get("ambient_humidity"),
    suitability,
    sensor_data.get("latitude"),
    sensor_data.get("longitude")
))

    conn.commit()
    conn.close()

    return jsonify({"status": "success"})

@app.route('/sensor', methods=['GET'])
def send_sensor_data():
    return jsonify(sensor_data)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/analytics')
def analytics():
    if 'user' not in session:
        flash("Please log in first!", "warning")
        return redirect(url_for('login'))
    return render_template('analytics.html')

@app.route('/api/sensor_data')
def api_sensor_data():
    conn = sqlite3.connect('sensor.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()

    data = []
    for row in rows:
        data.append({
            'timestamp': row['timestamp'],
            'soil_moisture': row['soil_moisture'],
            'light_intensity': row['light_intensity'],
            'soil_ph': row['soil_ph'],
            'soil_temp': row['soil_temp'],
            'ambient_temp': row['ambient_temp'],
            'ambient_humidity': row['ambient_humidity'],
            'suitability': analyze_suitability(row)  # Custom function
        })
    return jsonify(data)

def analyze_suitability(row):
    if (20 <= row['soil_moisture'] <= 60 and
        6.0 <= row['soil_ph'] <= 7.5 and
        15 <= row['soil_temp'] <= 30 and
        18 <= row['ambient_temp'] <= 35 and
        40 <= row['ambient_humidity'] <= 70):
        return "Optimal"
    else:
        return "Needs Attention"

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have logged out!", "info")
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

