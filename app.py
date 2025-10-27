from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os, json, re, uuid
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

# ---------------- CONFIGURATION ----------------
app.secret_key = os.environ.get("SECRET_KEY", "innovators_united_secret_key")

EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS", "your_email@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "your_app_password")

PROJECTS_FILE = "projects.json"
USERS_FILE = "users.json"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "ABPPS12345"


# ---------------- EMAIL FUNCTION ----------------
def send_notification_email(project_data):
    """Send email notification when a new project is submitted"""
    try:
        subject = f"New Project Submitted - {project_data['websiteName']}"
        body = f"""
        New project details:

        Project ID: {project_data['id']}
        User: {project_data['userName']} ({project_data['userEmail']})
        Phone: {project_data.get('phone', 'Not provided')}
        Website: {project_data['websiteName']}
        Type: {project_data['websiteType']}
        Category: {project_data.get('category', 'Not specified')}
        Complexity: {project_data['complexity']}
        Total Cost: ₹{project_data['totalCost']}
        Advance: ₹{project_data['advanceAmount']}
        Delivery Date: {project_data['deliveryDate']}
        
        Description:
        {project_data['description']}
        """

        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = EMAIL_ADDRESS
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"⚠️ Email sending failed: {e}")


# ---------------- JSON HELPERS ----------------
def load_data(file_path):
    """Load JSON data safely"""
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump([], f)
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception:
        return []


def save_data(file_path, data):
    """Save JSON data safely"""
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)


# ---------------- ROUTES ----------------
@app.route("/")
def index():
    """Homepage route"""
    # Make sure data files exist
    if not os.path.exists(PROJECTS_FILE):
        save_data(PROJECTS_FILE, [])
    if not os.path.exists(USERS_FILE):
        save_data(USERS_FILE, [])

    # Load session info
    username = session.get("username", None)
    user_name = session.get("user_name", None)
    user_email = session.get("user_email", None)

    try:
        return render_template("index.html", username=username, user_name=user_name, user_email=user_email)
    except Exception as e:
        print(f"❌ Template render error: {e}")
        return f"Error loading template: {e}", 500


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Admin login
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.clear()
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))

        # User login
        users = load_data(USERS_FILE)
        user = next((u for u in users if u["username"] == username and u["password"] == password), None)

        if user:
            session["username"] = user["username"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name")
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")

        if not (name and username and email and password):
            return render_template("signup.html", error="All fields are required")

        if not email.endswith("@gmail.com"):
            return render_template("signup.html", error="Only Gmail addresses allowed")

        users = load_data(USERS_FILE)
        if any(u["username"] == username for u in users):
            return render_template("signup.html", error="Username already exists")

        new_user = {
            "id": len(users) + 1,
            "name": name,
            "username": username,
            "email": email,
            "password": password,
            "created_at": datetime.now().isoformat()
        }

        users.append(new_user)
        save_data(USERS_FILE, users)
        return render_template("signup.html", success="Account created successfully! You can now log in.")

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/admin")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    projects = load_data(PROJECTS_FILE)
    return render_template("admin.html", projects=projects)


# ---------------- UPDATED PROJECT CREATION WITH NEW FIELDS ----------------
@app.route("/api/projects", methods=["POST"])
def create_project():
    if not session.get("username"):
        return jsonify({"error": "Please log in first"}), 401

    data = request.json
    
    # ADDED: Required fields from second version
    required = ["websiteType", "complexity", "websiteName", "description", "deliveryOption", 
                "userName", "email", "phone", "category"]
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    user_name = session.get("user_name", "User")
    
    # ADDED: Use UUID for project ID from second version
    project_id = str(uuid.uuid4())[:8]

    # UPDATED: Pricing calculation with 40%/60% payment split
    prices = {"simple": 11000, "medium": 25000, "complex": 60000}
    base_cost = prices.get(data["complexity"], 0)

    # Auto-set medium price for WWW and E-commerce
    if data["websiteType"] in ["www", "ecommerce"]:
        base_cost = 25000  # Medium complexity price

    delivery_days = 5
    extra_charge = 0
    if data["deliveryOption"] == "1day":
        extra_charge = 5500
        delivery_days = 1
    elif data["deliveryOption"] == "2days":
        extra_charge = 5000
        delivery_days = 2

    total_cost = base_cost + extra_charge
    
    # UPDATED: 40% advance payment instead of 50%
    advance = total_cost * 0.4  # 40% advance

    # ADDED: Enhanced project data with new fields from second version
    project = {
        "id": project_id,
        "userName": data["userName"],  # From form data
        "userEmail": data["email"],    # From form data
        "phone": data["phone"],        # ADDED: Phone number
        "category": data["category"],  # ADDED: Project category
        "websiteType": data["websiteType"],
        "complexity": data["complexity"],
        "websiteName": data["websiteName"],
        "description": data["description"],
        "deliveryOption": data["deliveryOption"],
        "totalCost": total_cost,
        "advanceAmount": advance,      # Now 40% of total
        "finalAmount": total_cost - advance,  # ADDED: Final payment amount
        "status": "submitted",         # ADDED: Project status
        "createdAt": datetime.now().isoformat(),
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # ADDED: Submission timestamp
        "deliveryDate": (datetime.now() + timedelta(days=delivery_days)).strftime("%Y-%m-%d")
    }

    projects = load_data(PROJECTS_FILE)
    projects.append(project)
    save_data(PROJECTS_FILE, projects)

    send_notification_email(project)
    return jsonify({
        "success": True, 
        "projectId": project_id, 
        "totalCost": total_cost, 
        "advanceAmount": advance,
        "finalAmount": total_cost - advance
    })


# ---------------- ADDED FROM SECOND VERSION: SUCCESS PAGE ----------------
@app.route("/success/<project_id>")
def success_page(project_id):
    """Success page after project submission"""
    projects = load_data(PROJECTS_FILE)
    project = next((p for p in projects if p["id"] == project_id), None)
    if not project:
        return "Project not found", 404

    return render_template("success.html", project=project)


# ---------------- ADDED FROM SECOND VERSION: USER PROJECTS API ----------------
@app.route("/api/projects/user")
def get_user_projects():
    """Get projects for the logged-in user"""
    if not session.get("username"):
        return jsonify({"error": "Please log in first"}), 401

    username = session.get("username")
    projects = load_data(PROJECTS_FILE)
    
    # Filter projects by user (using username or userEmail)
    user_projects = [
        p for p in projects 
        if p.get('userName') == session.get('user_name') or p.get('userEmail') == session.get('user_email')
    ]
    
    return jsonify(user_projects)


# ---------------- DEBUG ROUTE ----------------
@app.route("/debug")
def debug_templates():
    """Debug route to confirm templates folder exists on Render"""
    template_path = os.path.join(os.getcwd(), "templates")
    if os.path.exists(template_path):
        return {
            "templates_folder": template_path,
            "files": os.listdir(template_path)
        }
    else:
        return {
            "error": "Templates folder missing!",
            "current_directory": os.getcwd()
        }


# ---------------- HEALTH CHECK ----------------
@app.route("/health")
def health():
    return jsonify({"status": "healthy", "message": "Innovators United API is running"})


# ---------------- MAIN ----------------
if __name__ == "__main__":
    # Ensure required JSON files exist
    if not os.path.exists(PROJECTS_FILE):
        save_data(PROJECTS_FILE, [])
    if not os.path.exists(USERS_FILE):
        save_data(USERS_FILE, [])

    port = int(os.environ.get("PORT", 5000))
    print(f"✅ Server running on http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)