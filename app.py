from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import os
import datetime

app = Flask(__name__)
app.secret_key = "secretkey"

currentdirectory = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(currentdirectory, "users1.db")

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project_name TEXT NOT NULL,
            deadline TEXT NOT NULL,
            revenue REAL NOT NULL,
            platform TEXT NOT NULL,  -- New column for platform
            status TEXT NOT NULL,    -- New column for status
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    conn.commit()
    conn.close()

@app.route("/", methods=["GET", "POST"])
def main():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session["user_id"] = user[0]
            session["full_name"] = user[1]
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password. Please try again.", "error")
            return redirect(url_for("main"))
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        full_name = request.form["full_name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]
        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (full_name, email, password, role) VALUES (?, ?, ?, ?)", 
                           (full_name, email, password, role))
            conn.commit()
            conn.close()
            flash("Signup successful! Please log in.", "success")
            return redirect(url_for("main"))
        except sqlite3.IntegrityError:
            flash("Email already exists. Please use a different email.", "error")
    return render_template("signup.html")

@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        flash("Please log in to access the dashboard.", "error")
        return redirect(url_for("main"))

    user_id = session["user_id"]
    
    if request.method == "POST":
        project_name = request.form["project_name"]
        deadline = request.form["deadline"]
        revenue = request.form["revenue"]
        platform = request.form["platform"]
        status = request.form["status"]

        if project_name and deadline and revenue and platform and status:
            try:
                # Connect to the new database 'users1.db'
                conn = sqlite3.connect(os.path.join(currentdirectory, "users1.db"))
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO projects (user_id, project_name, deadline, revenue, platform, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, project_name, deadline, revenue, platform, status))
                conn.commit()
                conn.close()
                flash("Project added successfully!", "success")
            except sqlite3.Error as e:
                flash(f"Error: {e}", "error")
            return redirect(url_for("dashboard"))
        else:
            flash("All fields are required.", "error")

    # Fetch projects from the new 'users1.db'
    conn = sqlite3.connect(os.path.join(currentdirectory, "users1.db"))
    cursor = conn.cursor()
    cursor.execute("SELECT id, project_name, deadline, revenue, platform, status FROM projects WHERE user_id = ?", (user_id,))
    projects = cursor.fetchall()
    conn.close()

    return render_template("dashboard.html", projects=projects)


@app.route("/delete_project/<int:project_id>")
def delete_project(project_id):
    if "user_id" not in session:
        flash("Please log in to access the dashboard.", "error")
        return redirect(url_for("main"))
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    flash("Project deleted successfully!", "success")
    return redirect(url_for("dashboard"))

    
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("main"))

@app.route("/api/projects", methods=["GET"])
def api_projects():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    user_id = session["user_id"]
    
    # Connect to the database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Fetch projects for the user
    cursor.execute("SELECT project_name, deadline, revenue, platform, status FROM projects WHERE user_id = ?", (user_id,))
    projects = cursor.fetchall()
    
    # Fetch role distribution
    cursor.execute("SELECT role FROM users")
    roles = cursor.fetchall()
    
    # Fetch platform distribution for the user
    cursor.execute("SELECT platform FROM projects WHERE user_id = ?", (user_id,))
    platforms = cursor.fetchall()
    
    conn.close()
    
    # Process role data to count 3D artists, web devs, and content writers
    role_counts = {"3D Artist": 0, "Web Developer": 0, "Content Writer": 0}
    for role in roles:
        role_name = role[0]
        if role_name in role_counts:
            role_counts[role_name] += 1
    
    # Process platform data to count the number of projects per platform
    platform_counts = {}
    for platform in platforms:
        platform_name = platform[0]
        if platform_name in platform_counts:
            platform_counts[platform_name] += 1
        else:
            platform_counts[platform_name] = 1
    
    # Prepare project data
    project_data = [
        {
            "name": project[0],
            "deadline": project[1],
            "revenue": project[2],
            "platform": project[3],
            "status": project[4]
        }
        for project in projects
    ]
    
    # Send project data, role counts, and platform counts
    return jsonify({
        "projects": project_data,
        "role_counts": role_counts,
        "platform_counts": platform_counts  # Add platform distribution here
    })
   # Helper function to connect to the database
def get_db_connection():
    conn = sqlite3.connect('users1.db')  # Adjust the database path as needed
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/update_project/<int:project_id>', methods=['POST'])
def update_project(project_id):
    try:
        # Parse the incoming JSON data
        data = request.json
        print(f"Received data: {data}")  # Debugging output

        # Validate the required fields
        if not all(key in data for key in ('project_name', 'deadline', 'revenue', 'platform', 'status')):
            return jsonify(success=False, message="Missing fields"), 400

        # Connect to the database
        conn = get_db_connection()
        print(f"Connected to database")  # Debugging output

        # Prepare the SQL query and values
        query = """
            UPDATE projects
            SET project_name = ?, deadline = ?, revenue = ?, platform = ?, status = ?
            WHERE id = ?
        """
        
        values = (data['project_name'], data['deadline'], data['revenue'], data['platform'], data['status'], project_id)
        print(f"Executing query with values: {values}")  # Debugging output

        # Execute the query
        conn.execute(query, values)
        conn.commit()
        conn.close()
        print(f"Project {project_id} updated successfully")  # Debugging output

        # Respond with success
        return jsonify(success=True)
    
    except Exception as e:
        # Handle exceptions and send error response
        print(f"Error updating project: {e}")  # Debugging output for the error
        return jsonify(success=False, message="An error occurred while updating the project"), 500
    from datetime import datetime

def update_project_status():
    """
    Update the status of projects to 'Failed' if the deadline has passed and the status is not 'Completed'.
    """
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Get the current date in the correct format
    current_date = datetime.now().strftime("%Y-%m-%d")

    # Update projects where the deadline has passed and the status is not 'Completed'
    cursor.execute("""
        UPDATE projects
        SET status = 'Failed'
        WHERE deadline < ? AND status NOT IN ('Completed', 'Failed')
    """, (current_date,))

    conn.commit()
    conn.close()
        
init_db()
if __name__ == "__main__":
    app.run(debug=True)
