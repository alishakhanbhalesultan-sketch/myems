from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Load .env file
load_dotenv(override=True)

app = Flask(__name__)

# Secret key is loaded from .env
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

if not app.config["SECRET_KEY"]:
    raise RuntimeError("SECRET_KEY is missing in your .env file.")


# =========================================================
# LOGIN REQUIRED DECORATOR
# =========================================================

def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


# =========================================================
# AUTHENTICATION - REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return redirect(url_for("register"))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )
        existing_user = cursor.fetchone()

        if existing_user:
            cursor.close()
            conn.close()
            flash("An account with this email already exists.", "error")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users (name, email, password)
            VALUES (%s, %s, %s)
            """,
            (name, email, hashed_password)
        )

        conn.commit()

        cursor.close()
        conn.close()

        flash("Account created successfully. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# =========================================================
# AUTHENTICATION - LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, name, email, password
            FROM users
            WHERE email = %s
            """,
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_email"] = user["email"]

            flash("Login successful.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "error")

    return render_template("login.html")


# =========================================================
# AUTHENTICATION - LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
@login_required
def dashboard():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM employees
    """)
    total_employees = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM employees
        WHERE status = 'Active'
    """)
    active_employees = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM employees
        WHERE status = 'On Leave'
    """)
    employees_on_leave = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM departments
    """)
    total_departments = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT *
        FROM employees
        ORDER BY id DESC
        LIMIT 5
    """)
    recent_employees = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "dashboard.html",
        total_employees=total_employees,
        active_employees=active_employees,
        employees_on_leave=employees_on_leave,
        total_departments=total_departments,
        recent_employees=recent_employees
    )


# =========================================================
# EMPLOYEES
# =========================================================

@app.route("/employees")
@login_required
def employees():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM employees
        ORDER BY id DESC
    """)

    employee_list = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "employees.html",
        employees=employee_list
    )


# =========================================================
# ADD EMPLOYEE
# =========================================================

@app.route("/employees/add", methods=["GET", "POST"])
@login_required
def add_employee():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get active departments
    cursor.execute("""
        SELECT department_name
        FROM departments
        WHERE status = 'Active'
        ORDER BY department_name
    """)

    department_list = cursor.fetchall()

    if request.method == "POST":

        employee_id = request.form["employee_id"]
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        department = request.form["department"]
        position = request.form["position"]
        joining_date = request.form["joining_date"]
        status = request.form["status"]

        cursor.execute("""
            INSERT INTO employees
            (
                employee_id,
                name,
                email,
                phone,
                department,
                position,
                joining_date,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            employee_id,
            name,
            email,
            phone,
            department,
            position,
            joining_date,
            status
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for("employees"))

    cursor.close()
    conn.close()

    return render_template(
        "add_employee.html",
        departments=department_list
    )


# =========================================================
# DELETE EMPLOYEE
# =========================================================

@app.route("/employees/delete/<int:id>")
@login_required
def delete_employee(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM employees
        WHERE id = %s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("employees"))


# =========================================================
# DEPARTMENTS
# =========================================================

@app.route("/departments")
@login_required
def departments():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            d.id,
            d.department_name,
            d.department_head,
            d.description,
            d.status,
            COUNT(e.id) AS employee_count
        FROM departments d
        LEFT JOIN employees e
            ON d.department_name = e.department
        GROUP BY
            d.id,
            d.department_name,
            d.department_head,
            d.description,
            d.status
        ORDER BY d.id DESC
    """)

    department_list = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM departments
    """)

    total_departments = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM departments
        WHERE status = 'Active'
    """)

    active_departments = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM employees
    """)

    total_employees = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM departments
        WHERE department_head IS NULL
        OR department_head = ''
    """)

    vacant_heads = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    return render_template(
        "departments.html",
        departments=department_list,
        total_departments=total_departments,
        active_departments=active_departments,
        total_employees=total_employees,
        vacant_heads=vacant_heads
    )


# =========================================================
# ADD DEPARTMENT
# =========================================================

@app.route("/departments/add", methods=["GET", "POST"])
@login_required
def add_department():

    if request.method == "POST":

        department_name = request.form["department_name"]
        department_head = request.form["department_head"]
        description = request.form["description"]
        status = request.form["status"]

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO departments
            (
                department_name,
                department_head,
                description,
                status
            )
            VALUES (%s, %s, %s, %s)
        """, (
            department_name,
            department_head,
            description,
            status
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for("departments"))

    return render_template("add_department.html")


# =========================================================
# DELETE DEPARTMENT
# =========================================================

@app.route("/departments/delete/<int:id>")
@login_required
def delete_department(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT department_name
        FROM departments
        WHERE id = %s
    """, (id,))

    department = cursor.fetchone()

    if department:

        department_name = department[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM employees
            WHERE department = %s
        """, (department_name,))

        employee_count = cursor.fetchone()[0]

        if employee_count == 0:

            cursor.execute("""
                DELETE FROM departments
                WHERE id = %s
            """, (id,))

            conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("departments"))


# =========================================================
# ATTENDANCE
# =========================================================

@app.route("/attendance")
@login_required
def attendance():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            e.id,
            e.employee_id,
            e.name,
            e.department,
            a.check_in,
            a.check_out,
            a.status
        FROM employees e
        LEFT JOIN attendance a
            ON e.employee_id = a.employee_id
            AND a.attendance_date = CURDATE()
        ORDER BY e.name
    """)

    attendance_list = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM employees
    """)

    total_employees = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM attendance
        WHERE attendance_date = CURDATE()
        AND status = 'Present'
    """)

    present_today = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM employees e
        LEFT JOIN attendance a
            ON e.employee_id = a.employee_id
            AND a.attendance_date = CURDATE()
        WHERE a.id IS NULL
        OR a.status = 'Absent'
    """)

    absent_today = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM attendance
        WHERE attendance_date = CURDATE()
        AND status = 'On Leave'
    """)

    on_leave = cursor.fetchone()["total"]

    if total_employees > 0:
        attendance_percentage = round(
            (present_today / total_employees) * 100,
            1
        )
    else:
        attendance_percentage = 0

    cursor.close()
    conn.close()

    return render_template(
        "attendance.html",
        attendance=attendance_list,
        total_employees=total_employees,
        present_today=present_today,
        absent_today=absent_today,
        on_leave=on_leave,
        attendance_percentage=attendance_percentage
    )


# =========================================================
# MARK PRESENT / CHECK IN
# =========================================================

@app.route(
    "/attendance/mark/<employee_id>",
    methods=["POST"]
)
@login_required
def mark_attendance(employee_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO attendance
        (
            employee_id,
            attendance_date,
            check_in,
            status
        )
        VALUES
        (
            %s,
            CURDATE(),
            CURTIME(),
            'Present'
        )
        ON DUPLICATE KEY UPDATE
            check_in = CURTIME(),
            status = 'Present'
    """, (employee_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("attendance"))


# =========================================================
# MARK ABSENT
# =========================================================

@app.route(
    "/attendance/absent/<employee_id>",
    methods=["POST"]
)
@login_required
def mark_absent(employee_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO attendance
        (
            employee_id,
            attendance_date,
            status
        )
        VALUES
        (
            %s,
            CURDATE(),
            'Absent'
        )
        ON DUPLICATE KEY UPDATE
            status = 'Absent',
            check_in = NULL,
            check_out = NULL
    """, (employee_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("attendance"))


# =========================================================
# CHECK OUT
# =========================================================

@app.route(
    "/attendance/checkout/<employee_id>",
    methods=["POST"]
)
@login_required
def checkout(employee_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE attendance
        SET check_out = CURTIME()
        WHERE employee_id = %s
        AND attendance_date = CURDATE()
        AND status = 'Present'
    """, (employee_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("attendance"))


# =========================================================
# LEAVE MANAGEMENT
# =========================================================

@app.route("/leave")
@login_required
def leave():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            l.id,
            l.employee_id,
            e.name,
            e.department,
            l.leave_type,
            l.start_date,
            l.end_date,
            DATEDIFF(l.end_date, l.start_date) + 1 AS days,
            l.reason,
            l.status
        FROM leave_requests l
        LEFT JOIN employees e
            ON l.employee_id = e.employee_id
        ORDER BY l.id DESC
    """)

    leave_list = cursor.fetchall()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM leave_requests
    """)

    total_requests = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM leave_requests
        WHERE status = 'Pending'
    """)

    pending_requests = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM leave_requests
        WHERE status = 'Approved'
    """)

    approved_requests = cursor.fetchone()["total"]

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM leave_requests
        WHERE status = 'Rejected'
    """)

    rejected_requests = cursor.fetchone()["total"]

    cursor.close()
    conn.close()

    return render_template(
        "leave.html",
        leaves=leave_list,
        total_requests=total_requests,
        pending_requests=pending_requests,
        approved_requests=approved_requests,
        rejected_requests=rejected_requests
    )


# =========================================================
# APPLY LEAVE
# =========================================================

@app.route("/leave/add", methods=["GET", "POST"])
@login_required
def add_leave():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            employee_id,
            name,
            department
        FROM employees
        ORDER BY name
    """)

    employee_list = cursor.fetchall()

    if request.method == "POST":

        employee_id = request.form["employee_id"]
        leave_type = request.form["leave_type"]
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        reason = request.form["reason"]

        cursor.execute("""
            INSERT INTO leave_requests
            (
                employee_id,
                leave_type,
                start_date,
                end_date,
                reason,
                status
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                %s,
                'Pending'
            )
        """, (
            employee_id,
            leave_type,
            start_date,
            end_date,
            reason
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return redirect(url_for("leave"))

    cursor.close()
    conn.close()

    return render_template(
        "apply_leave.html",
        employees=employee_list
    )


# =========================================================
# APPROVE LEAVE
# =========================================================

@app.route(
    "/leave/approve/<int:id>",
    methods=["POST"]
)
@login_required
def approve_leave(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE leave_requests
        SET status = 'Approved'
        WHERE id = %s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("leave"))


# =========================================================
# REJECT LEAVE
# =========================================================

@app.route(
    "/leave/reject/<int:id>",
    methods=["POST"]
)
@login_required
def reject_leave(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE leave_requests
        SET status = 'Rejected'
        WHERE id = %s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("leave"))


# =========================================================
# DELETE LEAVE
# =========================================================

@app.route(
    "/leave/delete/<int:id>",
    methods=["POST"]
)
@login_required
def delete_leave(id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM leave_requests
        WHERE id = %s
    """, (id,))

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("leave"))




if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )