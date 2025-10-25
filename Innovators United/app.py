from flask import Flask, request, jsonify, render_template, session, redirect, url_for
import json
import os
from datetime import datetime, timedelta
import secrets
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-12345')

# Admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "ABPPS12345"

# Email configuration (for notifications)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS', "pratikpreetam1714@gmail.com")
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', "your-app-password")

# Load projects from JSON file
PROJECTS_FILE = "projects.json"
USERS_FILE = "users.json"

def send_notification_email(project_data):
    """Send email notification when new project is submitted"""
    try:
        # Email content
        subject = f"New Project Submitted - {project_data['websiteName']}"
        body = f"""
        New Project Submission Details:
        
        Project ID: {project_data['id']}
        Client Name: {project_data['userName']}
        Username: {project_data['username']}
        Email: {project_data['userEmail']}
        Phone: {project_data['userPhone']}
        
        Website Name: {project_data['websiteName']}
        Website Type: {project_data['websiteType']}
        Complexity: {project_data['complexity']}
        Total Cost: ₹{project_data['totalCost']}
        Advance Amount: ₹{project_data['advanceAmount']}
        
        Requirements:
        {project_data['description']}
        
        Delivery Date: {project_data['deliveryDate']}
        
        Please check the admin dashboard for more details.
        """
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = EMAIL_ADDRESS  # Send to yourself
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_ADDRESS, EMAIL_ADDRESS, text)
        server.quit()
        
        print("✅ Notification email sent successfully")
        return True
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False

def load_projects():
    if os.path.exists(PROJECTS_FILE):
        try:
            with open(PROJECTS_FILE, 'r') as f:
                return json.load(f)
        except:
            return []
    return []

def save_projects(projects):
    with open(PROJECTS_FILE, 'w') as f:
        json.dump(projects, f, indent=2)

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading users: {e}")
            return []
    else:
        save_users([])
        return []

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def generate_project_id(full_name):
    names = full_name.upper().split()
    if len(names) >= 2:
        first_part = names[0][:3] if len(names[0]) >= 3 else names[0].ljust(3, 'X')
        second_part = names[-1][:3] if len(names[-1]) >= 3 else names[-1].ljust(3, 'X')
        base_id = first_part + second_part
    else:
        base_id = names[0][:6].ljust(6, 'X') if len(names[0]) >= 6 else names[0].ljust(6, 'X')
    
    timestamp = str(int(datetime.now().timestamp()))[-4:]
    return f"{base_id}{timestamp}"

def count_previous_edits(project_id_prefix, projects):
    count = 0
    for project in projects:
        if project['id'].startswith(project_id_prefix):
            count += 1
    return count

@app.route('/')
def index():
    # Clear any existing session to ensure fresh start
    if not session.get('user_id') and not session.get('admin_logged_in'):
        session.clear()
    user_name = session.get('user_name')
    user_email = session.get('user_email')
    username = session.get('username')
    return render_template('index.html', user_name=user_name, user_email=user_email, username=username)

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Clear session when accessing login page
    if request.method == 'GET':
        session.clear()
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Check if admin login
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session['admin_logged_in'] = True
            session['admin_name'] = "Admin"
            return redirect(url_for('admin'))
        
        # Check user login
        users = load_users()
        user = None
        for u in users:
            if u.get('username') == username and u.get('password') == password:
                user = u
                break
        
        if user:
            session.clear()
            session['user_id'] = user.get('id')
            session['user_name'] = user.get('name')
            session['user_email'] = user.get('email')
            session['user_phone'] = user.get('phone')
            session['username'] = user.get('username')
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')
        
        if not name or not username or not email or not password or not phone:
            return render_template('signup.html', error='All fields are required')
        
        if not email.endswith('@gmail.com'):
            return render_template('signup.html', error='Only Gmail addresses are accepted')
        
        if not re.match(r'^\d{10}$', phone):
            return render_template('signup.html', error='Phone number must be 10 digits')
        
        users = load_users()
        
        if any(u.get('username') == username for u in users):
            return render_template('signup.html', error='Username already taken')
        
        email_users = [u for u in users if u.get('email') == email]
        if len(email_users) >= 10:
            return render_template('signup.html', error='Maximum 10 accounts allowed per email address')
        
        user_id = len(users) + 1
        new_user = {
            'id': user_id,
            'name': name,
            'username': username,
            'email': email,
            'password': password,
            'phone': phone,
            'created_at': datetime.now().isoformat()
        }
        
        users.append(new_user)
        save_users(users)
        
        session.clear()
        session['user_id'] = user_id
        session['user_name'] = name
        session['user_email'] = email
        session['user_phone'] = phone
        session['username'] = username
        
        return render_template('signup.html', success='Account created successfully! You can now login.')
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        session.clear()
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session['admin_logged_in'] = True
            session['admin_name'] = "Admin"
            return redirect(url_for('admin'))
        else:
            return render_template('admin_login.html', error='Invalid credentials')
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('index'))

# Success page route
@app.route('/success/<project_id>')
def success(project_id):
    if not session.get('user_id'):
        return redirect(url_for('login'))
    
    projects = load_projects()
    project = next((p for p in projects if p.get('id') == project_id), None)
    
    if not project:
        return redirect(url_for('index'))
    
    return render_template('success.html', project=project)

# API Routes
@app.route('/api/projects', methods=['POST'])
def create_project():
    try:
        if not session.get('user_id'):
            return jsonify({'error': 'Please login first'}), 401
            
        data = request.json
        
        required_fields = ['websiteType', 'complexity', 'websiteName', 'description', 'deliveryOption']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        users = load_users()
        current_user = next((u for u in users if u.get('id') == session['user_id']), None)
        
        if not current_user:
            return jsonify({'error': 'User not found'}), 400
        
        project_id_prefix = generate_project_id(current_user.get('name', 'User'))
        projects = load_projects()
        edit_count = count_previous_edits(project_id_prefix, projects)
        
        pricing = {'simple': 11000, 'medium': 25000, 'complex': 60000}
        base_cost = pricing.get(data['complexity'], 0)
        
        delivery_charges = 0
        delivery_days = 5
        
        if data['deliveryOption'] == '1day':
            delivery_charges = 5500
            delivery_days = 1
        elif data['deliveryOption'] == '2days':
            delivery_charges = 5000
            delivery_days = 2
        
        edit_charges = max(0, (edit_count - 2)) * 5000
        total_cost = base_cost + edit_charges + delivery_charges
        
        # Calculate advance amount (50% of total cost)
        advance_amount = total_cost * 0.5
        
        project = {
            'id': project_id_prefix,
            'userId': session['user_id'],
            'userName': current_user.get('name', ''),
            'userEmail': current_user.get('email', ''),
            'userPhone': current_user.get('phone', ''),
            'username': current_user.get('username', ''),
            'websiteType': data['websiteType'],
            'complexity': data['complexity'],
            'websiteName': data['websiteName'],
            'description': data['description'],
            'deliveryOption': data['deliveryOption'],
            'deliveryCharges': delivery_charges,
            'totalCost': total_cost,
            'advanceAmount': advance_amount,
            'editCount': edit_count + 1,
            'editCharges': edit_charges,
            'status': 'pending',
            'paymentStatus': 'pending',
            'advancePaid': False,
            'fullPaid': False,
            'createdAt': datetime.now().isoformat(),
            'deliveryDate': (datetime.now() + timedelta(days=delivery_days)).strftime('%Y-%m-%d'),
            'websiteUrl': '',
            'billGenerated': False,
            'attachments': data.get('attachments', [])
        }
        
        projects.append(project)
        save_projects(projects)
        
        # Send notification email
        send_notification_email(project)
        
        return jsonify({
            'success': True,
            'projectId': project_id_prefix,
            'message': 'Project submitted successfully!',
            'totalCost': total_cost,
            'advanceAmount': advance_amount,
            'editCount': edit_count + 1,
            'deliveryCharges': delivery_charges,
            'project': project
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects', methods=['GET'])
def get_all_projects():
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
    projects = load_projects()
    return jsonify(projects)

@app.route('/api/projects/user', methods=['GET'])
def get_user_projects():
    if not session.get('user_id'):
        return jsonify({'error': 'Please login first'}), 401
    
    projects = load_projects()
    user_projects = [p for p in projects if p.get('userId') == session['user_id']]
    return jsonify(user_projects)

@app.route('/api/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    projects = load_projects()
    project = next((p for p in projects if p.get('id') == project_id), None)
    if project:
        return jsonify(project)
    else:
        return jsonify({'error': 'Project not found'}), 404

@app.route('/api/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    try:
        data = request.json
        projects = load_projects()
        project = next((p for p in projects if p.get('id') == project_id), None)
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        for key, value in data.items():
            if key in project:
                project[key] = value
        
        save_projects(projects)
        return jsonify({'success': True, 'message': 'Project updated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_id>/bill', methods=['POST'])
def generate_bill(project_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    try:
        data = request.json
        projects = load_projects()
        project = next((p for p in projects if p.get('id') == project_id), None)
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        project['billGenerated'] = True
        project['websiteUrl'] = data.get('websiteUrl', '')
        project['billDate'] = datetime.now().isoformat()
        
        save_projects(projects)
        return jsonify({'success': True, 'message': 'Bill generated successfully'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/projects/<project_id>/payment', methods=['POST'])
def update_payment(project_id):
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Unauthorized'}), 401
        
    try:
        data = request.json
        payment_type = data.get('type')  # 'advance' or 'full'
        
        projects = load_projects()
        project = next((p for p in projects if p.get('id') == project_id), None)
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        if payment_type == 'advance':
            project['advancePaid'] = True
            project['paymentStatus'] = 'advance_paid'
        elif payment_type == 'full':
            project['fullPaid'] = True
            project['paymentStatus'] = 'completed'
        
        save_projects(projects)
        return jsonify({'success': True, 'message': f'{payment_type} payment marked as paid'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Health check route
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'message': 'Innovators United API is running'})

if __name__ == '__main__':
    # Initialize data files
    if not os.path.exists(PROJECTS_FILE):
        save_projects([])
        print("📁 Created projects.json")
    
    if not os.path.exists(USERS_FILE):
        save_users([])
        print("📁 Created users.json")
    
    # Get port from environment variable or default to 5000
    port = int(os.environ.get("PORT", 5000))
    
    print("🚀 Starting Innovators United Web Application...")
    print(f"📊 Projects file: {PROJECTS_FILE}")
    print(f"👥 Users file: {USERS_FILE}")
    print(f"📧 Email: {EMAIL_ADDRESS}")
    print(f"🌐 Server starting on http://0.0.0.0:{port}")
    print("📍 Access the application at http://localhost:5000")
    print("⏹️  Press Ctrl+C to stop the server")
    
    # Run the application
    app.run(host='0.0.0.0', port=port, debug=False)