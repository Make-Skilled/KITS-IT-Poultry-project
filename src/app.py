from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from functools import wraps
import json
from web3 import Web3, HTTPProvider
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests

app = Flask(__name__)
app.secret_key = 'Poultry'

# Add these constants at the top of your file, after the imports
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "kr4785543@gmail.com"  # Replace with your email
SMTP_PASSWORD = "qhuzwfrdagfyqemk"     # Replace with your app password
ALERT_EMAIL = "sudheerthadikonda0605@poultry.com"       # Replace with owner's email

# ThingSpeak Configuration
WRITE_URL = "https://api.thingspeak.com/update"
OUTPUT_WRITE_API_KEY = "SJPIKXSQ27L3H5K2"  # Replace with your actual API key

def connectWithBlockchain(acc):
    web3 = Web3(HTTPProvider('http://127.0.0.1:7545'))
    if acc == 0:
        web3.eth.defaultAccount = web3.eth.accounts[0]
    else:
        web3.eth.defaultAccount = acc
    
    artifact_path = "../build/contracts/poultry.json"

    with open(artifact_path) as f:
        artifact_json = json.load(f)
        contract_abi = artifact_json['abi']
        contract_address = artifact_json['networks']['5777']['address']
    
    contract = web3.eth.contract(abi=contract_abi, address=contract_address)
    return contract, web3

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or not session['user'].get('logged_in'):
            flash("Please login to access this page", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():    
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/dashboard/early')
@login_required
def dashboard_early():
    return render_template('dashboard_early.html')

@app.route('/dashboard/mid')
@login_required
def dashboard_mid():
    return render_template('dashboard_mid.html')

@app.route('/dashboard/late')
@login_required
def dashboard_late():
    return render_template('dashboard_late.html')

@app.route("/register")
def register():
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form.get('email').lower()
            password = request.form.get('password')
            remember = request.form.get('remember-me')
            
            if not email or not password:
                flash("Email and password are required", "error")
                return render_template('login.html'), 400

            contract, web3 = connectWithBlockchain(0)
            if not contract or not web3:
                flash("Failed to connect to blockchain", "error")
                return render_template('login.html'), 500

            try:
                login_successful = contract.functions.userLogin(email, password).call()
                
                if login_successful:
                    user_details = contract.functions.getUserByEmail(email).call()
                    session['user'] = {
                        'fullname': user_details[0],
                        'email': user_details[1],
                        'logged_in': True
                    }
                    
                    if remember:
                        session.permanent = True
                    
                    flash("Login successful!", "success")
                    return redirect(url_for('dashboard'))
                else:
                    flash("Invalid email or password", "error")
                    return render_template('login.html'), 401

            except Exception as blockchain_error:
                print(f"Blockchain error during login: {blockchain_error}")
                flash("Login verification failed", "error")
                return render_template('login.html'), 500

        except Exception as e:
            print(f"Error during login: {e}")
            flash("An internal error occurred", "error")
            return render_template('login.html'), 500
    
    return render_template('login.html')

@app.route('/register', methods=['POST'])
def register_user():
    try:
        full_name = request.form.get('name')
        email = request.form.get('email').lower()
        password = request.form.get('password')
        
        if not full_name or not email or not password:
            flash("All fields are required", "error")
            return render_template('signup.html'), 400

        contract, web3 = connectWithBlockchain(0)
        if not contract or not web3:
            flash("Failed to connect to blockchain", "error")
            return render_template('signup.html'), 500

        try:
            tx_hash = contract.functions.addUser(full_name, email, password).transact()
            web3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as blockchain_error:
            print(f"Blockchain error during registration: {blockchain_error}")
            flash("Email already exists", "error")
            return render_template('signup.html'), 500

        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))

    except Exception as e:
        print(f"Error during registration: {e}")
        flash("An internal error occurred", "error")
        return render_template('signup.html'), 500

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out", "success")
    return redirect(url_for('index'))

def send_alert_email(sensor_type, value, threshold):
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = ALERT_EMAIL
        msg['Subject'] = f"⚠️ Alert: Abnormal {sensor_type} Level Detected"

        # Create email body
        body = f"""
        Warning: Abnormal {sensor_type} Level Detected!

        Current {sensor_type}: {value}
        Normal Range: {threshold}

        Please take immediate action to address this issue.

        This is an automated message from your Poultry Monitoring System.
        """

        msg.attach(MIMEText(body, 'plain'))

        # Create SMTP session
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        # Send email
        server.send_message(msg)
        server.quit()
        
        print(f"Alert email sent for {sensor_type}")
        return True
    except Exception as e:
        print(f"Failed to send alert email: {e}")
        return False

@app.route('/api/sensor-data', methods=['GET', 'POST'])
@app.route('/api/sensor-data/<stage>', methods=['GET', 'POST'])
@login_required
def get_sensor_data(stage=None):
    # Define optimal ranges based on stage
    optimal_ranges = {
        'early': {
            'temperature': {'min': 32, 'max': 35},
            'humidity': {'min': 60, 'max': 70},
            'gas': {'max': 400}
        },
        'mid': {
            'temperature': {'min': 29, 'max': 32},
            'humidity': {'min': 55, 'max': 65},
            'gas': {'max': 400}
        },
        'late': {
            'temperature': {'min': 26, 'max': 29},
            'humidity': {'min': 50, 'max': 60},
            'gas': {'max': 400}
        }
    }

    # If no stage provided, use 'mid' as default
    if not stage:
        stage = 'mid'

    # Handle both GET and POST requests
    if request.method == 'POST':
        # Get data from POST request
        data = request.get_json()
        temperature = float(data.get('temperature', 30.0))
        humidity = int(data.get('humidity', 65))
        gas = int(data.get('gas', 300))
    else:
        # Get data from GET parameters
        temperature = request.args.get('temperature', type=float, default=30.0)
        humidity = request.args.get('humidity', type=int, default=65)
        gas = request.args.get('gas', type=int, default=300)
    
    ranges = optimal_ranges[stage]
    
    # Check status and send alerts if needed
    if temperature < ranges['temperature']['min'] or temperature > ranges['temperature']['max']:
        send_alert_email("Temperature", f"{temperature}°C", 
                        f"{ranges['temperature']['min']}-{ranges['temperature']['max']}°C")
    
    if humidity < ranges['humidity']['min'] or humidity > ranges['humidity']['max']:
        send_alert_email("Humidity", f"{humidity}%", 
                        f"{ranges['humidity']['min']}-{ranges['humidity']['max']}%")
    
    if gas > ranges['gas']['max']:
        send_alert_email("Gas", f"{gas} ppm", 
                        f"Below {ranges['gas']['max']} ppm")
    
    data = {
        "temperature": temperature,
        "humidity": humidity,
        "gas": gas,
        "status": {
            "temperature": "normal" if ranges['temperature']['min'] <= temperature <= ranges['temperature']['max'] else "warning",
            "humidity": "normal" if ranges['humidity']['min'] <= humidity <= ranges['humidity']['max'] else "warning",
            "gas": "normal" if gas <= ranges['gas']['max'] else "warning"
        }
    }
    return jsonify(data)

@app.route('/toggle_control/<stage>', methods=['POST'])
@login_required
def toggle_control(stage):
    try:
        state = request.json.get('state', False)
        value = 1 if state else 2
        
        # Map stages to different ThingSpeak fields
        field_mapping = {
            'early': 'field1',
            'mid': 'field2',
            'late': 'field3'
        }
        
        if stage not in field_mapping:
            return jsonify({'success': False, 'error': 'Invalid stage'}), 400
            
        params = {
            'api_key': OUTPUT_WRITE_API_KEY,
            field_mapping[stage]: value
        }
        
        response = requests.get(WRITE_URL, params=params)
        if response.status_code == 200:
            return jsonify({'success': True, 'state': state, 'value': value})
        else:
            return jsonify({'success': False, 'error': 'Failed to update ThingSpeak'}), 400
            
    except Exception as e:
        print(f"Error in toggle_control for {stage} stage: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
