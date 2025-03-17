from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session
from functools import wraps
import json
from web3 import Web3, HTTPProvider
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'Poultry'

# Add these constants at the top of your file, after the imports
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "kr4785543@gmail.com"  # Replace with your email
SMTP_PASSWORD = "qhuzwfrdagfyqemk"     # Replace with your app password
ALERT_EMAIL = "sudheerthadikonda0605@poultry.com"       # Replace with owner's email

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

@app.route('/api/sensor-data')
@login_required
def get_sensor_data():
    temperature = request.args.get('temperature', type=float, default=35.0)
    moisture = request.args.get('moisture', type=int, default=80)
    gas = request.args.get('gas', type=int, default=500)
    
    # Define thresholds
    temp_range = "22°C - 28°C"
    moisture_range = "50% - 70%"
    gas_range = "Below 400 ppm"

    # Check status and send alerts if needed
    if temperature < 22 or temperature > 28:
        send_alert_email("Temperature", f"{temperature}°C", temp_range)
    
    if moisture < 50 or moisture > 70:
        send_alert_email("Moisture", f"{moisture}%", moisture_range)
    
    if gas > 400:
        send_alert_email("Gas", f"{gas} ppm", gas_range)
    
    data = {
        "temperature": temperature,
        "moisture": moisture,
        "gas": gas,
        "status": {
            "temperature": "normal" if 22 <= temperature <= 28 else "warning",
            "moisture": "normal" if 50 <= moisture <= 70 else "warning",
            "gas": "normal" if gas <= 400 else "warning"
        }
    }
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)