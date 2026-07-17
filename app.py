from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = "eduinfo-secret-key"

DATABASE = "eduinfo.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_database():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            course TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)
    connection.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
""")

    connection.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS marks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            marks_obtained INTEGER NOT NULL,
            max_marks INTEGER NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    """)

    teacher = connection.execute(
        "SELECT * FROM teachers WHERE email = ?",
        ("teacher@eduinfo.com",)
    ).fetchone()

    if teacher is None:
        teacher_password = generate_password_hash("teacher123")

        connection.execute(
            """
            INSERT INTO teachers (name, email, password)
            VALUES (?, ?, ?)
            """,
            (
                "EduInfo Teacher",
                "teacher@eduinfo.com",
                teacher_password
            )
        )

    admin = connection.execute(
        "SELECT * FROM admins WHERE email = ?",
        ("admin@eduinfo.com",)
    ).fetchone()

    if admin is None:
        admin_password = generate_password_hash("admin123")

        connection.execute(
            """
            INSERT INTO admins (name, email, password)
            VALUES (?, ?, ?)
            """,
            (
                "EduInfo Admin",
                "admin@eduinfo.com",
                admin_password
            )
        )

    connection.commit()
    connection.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/student/register", methods=["GET", "POST"])
def student_register():

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        course = request.form["course"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()

        try:
            connection.execute(
                """
                INSERT INTO students (name, email, course, password)
                VALUES (?, ?, ?, ?)
                """,
                (name, email, course, hashed_password)
            )

            connection.commit()

        except sqlite3.IntegrityError:
            connection.close()

            flash(
                "Student with this email already exists.",
                "error"
            )

            return redirect(url_for("student_register"))

        connection.close()

        flash(
            "Student registered successfully! You can now login.",
            "success"
        )

        return redirect(url_for("student_login"))

    return render_template("student_register.html")


@app.route("/student/login", methods=["GET", "POST"])
def student_login():

    if "student_id" in session:
        return redirect(url_for("student_dashboard"))

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        connection = get_db_connection()

        student = connection.execute(
            "SELECT * FROM students WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if student and check_password_hash(
            student["password"],
            password
        ):
            session.clear()

            session["student_id"] = student["id"]
            session["student_name"] = student["name"]

            return redirect(url_for("student_dashboard"))

        flash(
            "Invalid email or password.",
            "error"
        )

        return redirect(url_for("student_login"))

    return render_template("student_login.html")


@app.route("/student/dashboard")
def student_dashboard():

    if "student_id" not in session:
        flash(
            "Please login to access your dashboard.",
            "error"
        )

        return redirect(url_for("student_login"))

    connection = get_db_connection()

    student = connection.execute(
        "SELECT * FROM students WHERE id = ?",
        (session["student_id"],)
    ).fetchone()

    connection.close()

    if student is None:
        session.clear()
        return redirect(url_for("student_login"))

    return render_template(
        "student_dashboard.html",
        student=student
    )


@app.route("/student/profile")
def student_profile():

    if "student_id" not in session:
        flash(
            "Please login to view your profile.",
            "error"
        )

        return redirect(url_for("student_login"))

    connection = get_db_connection()

    student = connection.execute(
        "SELECT * FROM students WHERE id = ?",
        (session["student_id"],)
    ).fetchone()

    connection.close()

    if student is None:
        session.clear()
        return redirect(url_for("student_login"))

    return render_template(
        "student_profile.html",
        student=student
    )


@app.route("/student/attendance")
def student_attendance():

    if "student_id" not in session:
        flash(
            "Please login to view your attendance.",
            "error"
        )

        return redirect(url_for("student_login"))

    connection = get_db_connection()

    attendance_records = connection.execute(
        """
        SELECT *
        FROM attendance
        WHERE student_id = ?
        ORDER BY date DESC
        """,
        (session["student_id"],)
    ).fetchall()

    connection.close()

    total_classes = len(attendance_records)

    present_classes = sum(
        1
        for record in attendance_records
        if record["status"] == "Present"
    )

    if total_classes > 0:
        attendance_percentage = round(
            (present_classes / total_classes) * 100,
            2
        )
    else:
        attendance_percentage = 0

    return render_template(
        "student_attendance.html",
        attendance_records=attendance_records,
        total_classes=total_classes,
        present_classes=present_classes,
        attendance_percentage=attendance_percentage
    )


@app.route("/student/marks")
def student_marks():

    if "student_id" not in session:
        flash(
            "Please login to view your marks.",
            "error"
        )

        return redirect(url_for("student_login"))

    connection = get_db_connection()

    marks_data = connection.execute(
        """
        SELECT *
        FROM marks
        WHERE student_id = ?
        ORDER BY subject ASC
        """,
        (session["student_id"],)
    ).fetchall()

    connection.close()

    marks_records = []

    total_obtained = 0
    total_max_marks = 0

    for record in marks_data:

        if record["max_marks"] > 0:
            percentage = round(
                (
                    record["marks_obtained"]
                    / record["max_marks"]
                ) * 100,
                2
            )
        else:
            percentage = 0

        if percentage >= 90:
            grade = "A+"

        elif percentage >= 80:
            grade = "A"

        elif percentage >= 70:
            grade = "B"

        elif percentage >= 60:
            grade = "C"

        elif percentage >= 50:
            grade = "D"

        else:
            grade = "F"

        marks_records.append({
            "subject": record["subject"],
            "marks_obtained": record["marks_obtained"],
            "max_marks": record["max_marks"],
            "percentage": percentage,
            "grade": grade
        })

        total_obtained += record["marks_obtained"]
        total_max_marks += record["max_marks"]

    total_subjects = len(marks_records)

    if total_max_marks > 0:
        overall_percentage = round(
            (total_obtained / total_max_marks) * 100,
            2
        )
    else:
        overall_percentage = 0

    return render_template(
        "student_marks.html",
        marks_records=marks_records,
        total_subjects=total_subjects,
        total_obtained=total_obtained,
        overall_percentage=overall_percentage
    )


@app.route("/student/logout")
def student_logout():

    session.clear()

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(url_for("student_login"))


@app.route("/teacher/login", methods=["GET", "POST"])
def teacher_login():

    if "teacher_id" in session:
        return redirect(url_for("teacher_dashboard"))

    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        connection = get_db_connection()

        teacher = connection.execute(
            "SELECT * FROM teachers WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if teacher and check_password_hash(
            teacher["password"],
            password
        ):
            session.clear()

            session["teacher_id"] = teacher["id"]
            session["teacher_name"] = teacher["name"]

            return redirect(url_for("teacher_dashboard"))

        flash(
            "Invalid teacher email or password.",
            "error"
        )

        return redirect(url_for("teacher_login"))

    return render_template("teacher_login.html")
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if "admin_id" in session:
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        connection = get_db_connection()

        admin = connection.execute(
            "SELECT * FROM admins WHERE email = ?",
            (email,)
        ).fetchone()

        connection.close()

        if admin and check_password_hash(admin["password"], password):

            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["name"]

            flash("Welcome Admin!", "success")
            return redirect(url_for("admin_dashboard"))

        flash("Invalid admin email or password.", "error")

    return render_template("admin_login.html")


@app.route("/admin/dashboard")
def admin_dashboard():

    if "admin_id" not in session:
        flash(
            "Please login to access the admin dashboard.",
            "error"
        )
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    admin = connection.execute(
        "SELECT * FROM admins WHERE id = ?",
        (session["admin_id"],)
    ).fetchone()

    total_students = connection.execute(
        "SELECT COUNT(*) as count FROM students"
    ).fetchone()["count"]

    total_teachers = connection.execute(
        "SELECT COUNT(*) as count FROM teachers"
    ).fetchone()["count"]

    total_attendance = connection.execute(
        "SELECT COUNT(*) as count FROM attendance"
    ).fetchone()["count"]

    total_marks = connection.execute(
        "SELECT COUNT(*) as count FROM marks"
    ).fetchone()["count"]

    connection.close()

    if admin is None:
        session.clear()
        flash(
            "Admin account not found. Please login again.",
            "error"
        )
        return redirect(url_for("admin_login"))

    return render_template(
        "admin_dashboard.html",
        admin=admin,
        total_students=total_students,
        total_teachers=total_teachers,
        total_attendance=total_attendance,
        total_marks=total_marks
    )


@app.route("/admin/students")
def admin_students():

    if "admin_id" not in session:
        flash(
            "Please login to access this page.",
            "error"
        )
        return redirect(url_for("admin_login"))

    search_query = request.args.get("q", "").strip()

    connection = get_db_connection()

    if search_query:
        students = connection.execute(
            """
            SELECT id, name, email, course
            FROM students
            WHERE name LIKE ? OR email LIKE ? OR course LIKE ?
            ORDER BY name
            """,
            (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%")
        ).fetchall()
    else:
        students = connection.execute(
            "SELECT id, name, email, course FROM students ORDER BY name"
        ).fetchall()

    total_students = len(students)

    connection.close()

    return render_template(
        "admin_students.html",
        students=students,
        total_students=total_students,
        search_query=search_query
    )


@app.route("/admin/delete-student/<int:student_id>", methods=["POST"])
def admin_delete_student(student_id):

    if "admin_id" not in session:
        flash(
            "Please login to access this page.",
            "error"
        )
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    student = connection.execute(
        "SELECT id FROM students WHERE id = ?",
        (student_id,)
    ).fetchone()

    if student is None:
        connection.close()
        flash("Student not found.", "error")
        return redirect(url_for("admin_students"))

    connection.execute(
        "DELETE FROM attendance WHERE student_id = ?",
        (student_id,)
    )
    connection.execute(
        "DELETE FROM marks WHERE student_id = ?",
        (student_id,)
    )
    connection.execute(
        "DELETE FROM students WHERE id = ?",
        (student_id,)
    )
    connection.commit()
    connection.close()

    flash("Student deleted successfully.", "success")
    return redirect(url_for("admin_students"))


@app.route("/admin/teachers", methods=["GET", "POST"])
def admin_teachers():

    if "admin_id" not in session:
        flash(
            "Please login to access this page.",
            "error"
        )
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()

        if not all([name, email, password]):
            flash("All teacher fields are required.", "error")
            connection.close()
            return redirect(url_for("admin_teachers"))

        hashed_password = generate_password_hash(password)

        try:
            connection.execute(
                """
                INSERT INTO teachers (name, email, password)
                VALUES (?, ?, ?)
                """,
                (name, email, hashed_password)
            )
            connection.commit()
            flash("Teacher added successfully.", "success")

        except sqlite3.IntegrityError:
            flash("Teacher with this email already exists.", "error")

        connection.close()
        return redirect(url_for("admin_teachers"))

    teachers = connection.execute(
        "SELECT id, name, email FROM teachers ORDER BY name"
    ).fetchall()

    total_teachers = len(teachers)

    connection.close()

    return render_template(
        "admin_teachers.html",
        teachers=teachers,
        total_teachers=total_teachers
    )


@app.route("/admin/delete-teacher/<int:teacher_id>", methods=["POST"])
def admin_delete_teacher(teacher_id):

    if "admin_id" not in session:
        flash(
            "Please login to access this page.",
            "error"
        )
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    teacher = connection.execute(
        "SELECT id FROM teachers WHERE id = ?",
        (teacher_id,)
    ).fetchone()

    if teacher is None:
        connection.close()
        flash("Teacher not found.", "error")
        return redirect(url_for("admin_teachers"))

    connection.execute(
        "DELETE FROM teachers WHERE id = ?",
        (teacher_id,)
    )
    connection.commit()
    connection.close()

    flash("Teacher deleted successfully.", "success")
    return redirect(url_for("admin_teachers"))


@app.route("/admin/attendance")
def admin_attendance():

    if "admin_id" not in session:
        flash(
            "Please login to access this page.",
            "error"
        )
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    attendance_records = connection.execute(
        """
        SELECT attendance.id, students.name AS student_name, attendance.subject,
               attendance.date, attendance.status
        FROM attendance
        JOIN students ON attendance.student_id = students.id
        ORDER BY attendance.date DESC, attendance.id DESC
        """
    ).fetchall()

    total_records = len(attendance_records)

    connection.close()

    return render_template(
        "admin_attendance.html",
        attendance_records=attendance_records,
        total_records=total_records
    )


@app.route("/admin/marks")
def admin_marks():

    if "admin_id" not in session:
        flash(
            "Please login to access this page.",
            "error"
        )
        return redirect(url_for("admin_login"))

    connection = get_db_connection()

    marks_records = connection.execute(
        """
        SELECT marks.id, students.name AS student_name, marks.subject,
               marks.marks_obtained, marks.max_marks
        FROM marks
        JOIN students ON marks.student_id = students.id
        ORDER BY marks.subject ASC, students.name ASC
        """
    ).fetchall()

    total_records = len(marks_records)

    connection.close()

    return render_template(
        "admin_marks.html",
        marks_records=marks_records,
        total_records=total_records
    )


@app.route("/admin/logout")
def admin_logout():

    session.clear()

    flash(
        "Admin logged out successfully.",
        "success"
    )

    return redirect(url_for("admin_login"))


@app.route("/teacher/dashboard")
def teacher_dashboard():

    if "teacher_id" not in session:
        flash(
            "Please login to access the teacher dashboard.",
            "error"
        )

        return redirect(url_for("teacher_login"))

    connection = get_db_connection()

    teacher = connection.execute(
        "SELECT * FROM teachers WHERE id = ?",
        (session["teacher_id"],)
    ).fetchone()

    connection.close()

    if teacher is None:
        session.clear()

        flash(
            "Teacher account not found. Please login again.",
            "error"
        )

        return redirect(url_for("teacher_login"))

    return render_template(
        "teacher_dashboard.html",
        teacher=teacher
    )


@app.route("/teacher/students")
def teacher_students():

    if "teacher_id" not in session:
        flash(
            "Please login to access this page.",
            "error"
        )
        return redirect(url_for("teacher_login"))

    connection = get_db_connection()

    students = connection.execute(
        "SELECT id, name, email, course FROM students ORDER BY name"
    ).fetchall()

    total_students = len(students)

    connection.close()

    return render_template(
        "teacher_students.html",
        students=students,
        total_students=total_students
    )


@app.route("/teacher/add-student", methods=["GET", "POST"])
def teacher_add_student():

    if "teacher_id" not in session:
        flash(
            "Please login to access this page.",
            "error"
        )
        return redirect(url_for("teacher_login"))

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        course = request.form["course"]
        password = request.form["password"]

        hashed_password = generate_password_hash(password)

        connection = get_db_connection()

        try:
            connection.execute(
                """
                INSERT INTO students (name, email, course, password)
                VALUES (?, ?, ?, ?)
                """,
                (name, email, course, hashed_password)
            )

            connection.commit()

        except sqlite3.IntegrityError:
            connection.close()

            flash(
                "Student with this email already exists.",
                "error"
            )

            return redirect(url_for("teacher_add_student"))

        connection.close()

        flash(
            "Student added successfully!",
            "success"
        )

        return redirect(url_for("teacher_students"))

    return render_template("teacher_add_student.html")


@app.route("/teacher/attendance", methods=["GET", "POST"])
def teacher_attendance():

    if "teacher_id" not in session:
        flash(
            "Please login to access this page.",
            "error"
        )
        return redirect(url_for("teacher_login"))

    connection = get_db_connection()

    if request.method == "POST":
        student_id = request.form.get("student_id")
        subject = request.form.get("subject", "").strip()
        date = request.form.get("date")
        status = request.form.get("status")

        if not all([student_id, subject, date, status]):
            flash("All fields are required.", "error")
            connection.close()
            return redirect(url_for("teacher_attendance"))

        student = connection.execute(
            "SELECT id FROM students WHERE id = ?",
            (student_id,)
        ).fetchone()

        if not student:
            flash("Selected student does not exist.", "error")
            connection.close()
            return redirect(url_for("teacher_attendance"))

        connection.execute(
            """
            INSERT INTO attendance (student_id, subject, date, status)
            VALUES (?, ?, ?, ?)
            """,
            (student_id, subject, date, status)
        )

        connection.commit()

        flash(
            "Attendance marked successfully!",
            "success"
        )

    students = connection.execute(
        "SELECT id, name FROM students ORDER BY name"
    ).fetchall()

    connection.close()

    return render_template(
        "teacher_attendance.html",
        students=students
    )


@app.route("/teacher/marks", methods=["GET", "POST"])
def teacher_marks():

    if "teacher_id" not in session:
        flash(
            "Please login to access this page.",
            "error"
        )
        return redirect(url_for("teacher_login"))

    connection = get_db_connection()

    if request.method == "POST":
        student_id = request.form.get("student_id")
        subject = request.form.get("subject", "").strip()
        marks_obtained = request.form.get("marks_obtained")
        max_marks = request.form.get("max_marks")

        if not all([student_id, subject, marks_obtained, max_marks]):
            flash("All fields are required.", "error")
            connection.close()
            return redirect(url_for("teacher_marks"))

        student = connection.execute(
            "SELECT id FROM students WHERE id = ?",
            (student_id,)
        ).fetchone()

        if not student:
            flash("Selected student does not exist.", "error")
            connection.close()
            return redirect(url_for("teacher_marks"))

        try:
            marks_obtained = int(marks_obtained)
            max_marks = int(max_marks)

            if marks_obtained < 0 or max_marks <= 0 or marks_obtained > max_marks:
                flash("Please enter valid marks. Marks must be non-negative and less than or equal to max marks.", "error")
                connection.close()
                return redirect(url_for("teacher_marks"))

        except ValueError:
            flash("Marks must be numbers.", "error")
            connection.close()
            return redirect(url_for("teacher_marks"))

        connection.execute(
            """
            INSERT INTO marks (student_id, subject, marks_obtained, max_marks)
            VALUES (?, ?, ?, ?)
            """,
            (student_id, subject, marks_obtained, max_marks)
        )

        connection.commit()

        flash(
            "Marks uploaded successfully!",
            "success"
        )

    students = connection.execute(
        "SELECT id, name FROM students ORDER BY name"
    ).fetchall()

    connection.close()

    return render_template(
        "teacher_marks.html",
        students=students
    )


@app.route("/teacher/logout")
def teacher_logout():

    session.clear()

    flash(
        "Teacher logged out successfully.",
        "success"
    )

    return redirect(url_for("teacher_login"))



if __name__ == "__main__":
    create_database()
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=True
    )