
from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 用于session加密

# 数据库初始化
def init_db():
    conn = sqlite3.connect('student_management.db')
    cursor = conn.cursor()

    # 用户表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 学生信息表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        gender TEXT NOT NULL,
        birth_date TEXT,
        address TEXT,
        phone TEXT,
        email TEXT,
        major_id INTEGER,
        class_id INTEGER,
        enrollment_date TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (major_id) REFERENCES majors (id),
        FOREIGN KEY (class_id) REFERENCES classes (id),
        FOREIGN KEY (created_by) REFERENCES users (id)
    )
    """)

    # 专业表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS majors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 班级表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        major_id INTEGER,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (major_id) REFERENCES majors (id)
    )
    """)

    # 课程表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        credits INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 学生选课表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS enrollments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        course_id INTEGER,
        semester TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students (id),
        FOREIGN KEY (course_id) REFERENCES courses (id)
    )
    """)

    # 成绩表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS grades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enrollment_id INTEGER,
        score REAL NOT NULL,
        teacher_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (enrollment_id) REFERENCES enrollments (id),
        FOREIGN KEY (teacher_id) REFERENCES users (id)
    )
    """)

    # 检查是否已有管理员用户，如果没有则创建
    cursor.execute("SELECT * FROM users WHERE role='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                      ("admin", "admin123", "admin@example.com", "admin"))

    conn.commit()
    conn.close()

# 登录验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# 管理员权限验证装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session or session.get("role") != "admin":
            flash("您没有权限访问此页面")
            return redirect(url_for("dashboard"))
        return f(*args, **kwargs)
    return decorated_function

# 获取数据库连接
def get_db_connection():
    conn = sqlite3.connect("student_management.db")
    conn.row_factory = sqlite3.Row
    return conn

# 首页
@app.route("/")
def index():
    if "user_id" in session:
        # 根据用户角色重定向到对应的仪表盘
        if session.get("role") == "admin":
            return redirect(url_for("users_dashboard"))
        else:
            return redirect(url_for("students_dashboard"))
    return redirect(url_for("login"))

# 登录页面
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user and user["password"] == password:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]
            flash("登录成功！")
            # 根据用户角色直接重定向到对应的仪表盘
            if user["role"] == "admin":
                return redirect(url_for("users_dashboard"))
            else:
                return redirect(url_for("students_dashboard"))
        else:
            flash("用户名或密码错误")

    return render_template("login.html")

# 注册页面
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]

        # 检查用户名是否已存在
        conn = get_db_connection()
        existing_user = conn.execute("SELECT * FROM users WHERE username = ? OR email = ?", 
                                    (username, email)).fetchone()

        if existing_user:
            flash("用户名或邮箱已存在")
            conn.close()
            return render_template("register.html")

        # 创建新用户
        conn.execute("INSERT INTO users (username, password, email) VALUES (?, ?, ?)",
                    (username, password, email))
        conn.commit()
        conn.close()

        flash("注册成功，请登录")
        return redirect(url_for("login"))

    return render_template("register.html")

# 登出
@app.route("/logout")
def logout():
    session.clear()
    flash("您已成功登出")
    return redirect(url_for("login"))

# 仪表盘
@app.route("/dashboard")
@login_required
def dashboard():
    # 根据用户角色重定向到不同的仪表盘页面
    if session.get("role") == "admin":
        return redirect(url_for("users_dashboard"))
    else:
        return redirect(url_for("students_dashboard"))

# 学生个人信息
@app.route("/my_profile")
@login_required
def my_profile():
    return render_template("students/profile.html")

# 修改密码
@app.route("/change_password", methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        # 处理修改密码逻辑
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # 这里应该验证旧密码是否正确，并更新密码
        # 示例代码，实际应用中应该有更严格的验证
        if new_password != confirm_password:
            flash('新密码和确认密码不匹配', 'danger')
        else:
            flash('密码已成功修改', 'success')
            return redirect(url_for('my_profile'))

    return render_template("change_password.html")

# 浏览课程
@app.route("/browse_courses")
@login_required
def browse_courses():
    return render_template("students/browse_courses.html")

# 我的选课
@app.route("/my_selections")
@login_required
def my_selections():
    return render_template("students/my_selections.html")

# 我的成绩
@app.route("/my_grades")
@login_required
def my_grades():
    return render_template("students/my_grades.html")

# 学生仪表盘
@app.route("/students/dashboard")
@login_required
def students_dashboard():
    conn = get_db_connection()
    
    # 普通用户仪表盘数据
    student_count = conn.execute("SELECT COUNT(*) as count FROM students WHERE created_by = ?", 
                               (session["user_id"],)).fetchone()["count"]
    
    # 获取该用户创建的学生的选课记录数
    enrollment_count = conn.execute("""
        SELECT COUNT(*) as count 
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        WHERE s.created_by = ?
    """, (session["user_id"],)).fetchone()["count"]
    
    # 获取平均成绩
    avg_grade = conn.execute("""
        SELECT AVG(e.grade) as avg
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        WHERE s.created_by = ? AND e.grade IS NOT NULL
    """, (session["user_id"],)).fetchone()["avg"]
    
    average_grade = "{:.2f}".format(avg_grade) if avg_grade else "0.00"
    
    # 获取待录入成绩数
    pending_grades = conn.execute("""
        SELECT COUNT(*) as count 
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        WHERE s.created_by = ? AND e.grade IS NULL
    """, (session["user_id"],)).fetchone()["count"]
    
    conn.close()
    
    return render_template("students/dashboard.html",
                          student_count=student_count,
                          enrollment_count=enrollment_count,
                          average_grade=average_grade,
                          pending_grades=pending_grades)

# 管理员仪表盘
@app.route("/users/dashboard")
@login_required
@admin_required
def users_dashboard():
    conn = get_db_connection()
    
    # 管理员仪表盘数据
    student_count = conn.execute("SELECT COUNT(*) as count FROM students").fetchone()["count"]
    major_count = conn.execute("SELECT COUNT(*) as count FROM majors").fetchone()["count"]
    class_count = conn.execute("SELECT COUNT(*) as count FROM classes").fetchone()["count"]
    course_count = conn.execute("SELECT COUNT(*) as count FROM courses").fetchone()["count"]
    user_count = conn.execute("SELECT COUNT(*) as count FROM users").fetchone()["count"]
    enrollment_count = conn.execute("SELECT COUNT(*) as count FROM enrollments").fetchone()["count"]
    
    conn.close()
    
    return render_template("users/dashboard.html",
                          student_count=student_count,
                          major_count=major_count,
                          class_count=class_count,
                          course_count=course_count,
                          user_count=user_count,
                          enrollment_count=enrollment_count)

# 用户管理 - 管理员专用
@app.route("/users")
@login_required
@admin_required
def users():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users ORDER BY id ASC").fetchall()
    conn.close()
    return render_template("users/index.html", users=users)

# 创建用户 - 管理员专用
@app.route("/users/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_user():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        role = request.form["role"]

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)",
                        (username, password, email, role))
            conn.commit()
            flash("用户创建成功")
            return redirect(url_for("users"))
        except sqlite3.IntegrityError:
            flash("用户名或邮箱已存在")
        finally:
            conn.close()

    return render_template("users/create.html")

# 编辑用户 - 管理员专用
@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_user(user_id):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        role = request.form["role"]
        password = request.form.get("password")

        if password:
            conn.execute("UPDATE users SET username = ?, email = ?, role = ?, password = ? WHERE id = ?",
                        (username, email, role, password, user_id))
        else:
            conn.execute("UPDATE users SET username = ?, email = ?, role = ? WHERE id = ?",
                        (username, email, role, user_id))

        conn.commit()
        flash("用户信息更新成功")
        return redirect(url_for("users"))

    conn.close()
    return render_template("users/edit.html", user=user)

# 删除用户 - 管理员专用
@app.route("/users/<int:user_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash("用户删除成功")
    return redirect(url_for("users"))

# 学生信息管理
@app.route("/students")
@login_required
def students():
    conn = get_db_connection()

    if session.get("role") == "admin":
        students = conn.execute("""
            SELECT s.*, m.name as major_name, c.name as class_name, u.username as created_by_name
            FROM students s
            LEFT JOIN majors m ON s.major_id = m.id
            LEFT JOIN classes c ON s.class_id = c.id
            LEFT JOIN users u ON s.created_by = u.id
            ORDER BY s.id ASC
        """).fetchall()
    else:
        # 普通用户只能看到自己创建的学生信息
        students = conn.execute("""
            SELECT s.*, m.name as major_name, c.name as class_name
            FROM students s
            LEFT JOIN majors m ON s.major_id = m.id
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.created_by = ?
            ORDER BY s.id ASC
        """, (session["user_id"],)).fetchall()

    conn.close()
    return render_template("students/index.html", students=students)

# 创建学生信息
@app.route("/students/create", methods=["GET", "POST"])
@login_required
def create_student():
    conn = get_db_connection()

    if request.method == "POST":
        student_id = request.form["student_id"]
        name = request.form["name"]
        gender = request.form["gender"]
        birth_date = request.form.get("birth_date")
        address = request.form.get("address")
        phone = request.form.get("phone")
        email = request.form.get("email")
        major_id = request.form.get("major_id")
        class_id = request.form.get("class_id")
        enrollment_date = request.form.get("enrollment_date")

        try:
            conn.execute("""
                INSERT INTO students 
                (student_id, name, gender, birth_date, address, phone, email, major_id, class_id, enrollment_date, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (student_id, name, gender, birth_date, address, phone, email, major_id, class_id, enrollment_date, session["user_id"]))
            conn.commit()
            flash("学生信息创建成功")
            return redirect(url_for("students"))
        except sqlite3.IntegrityError:
            # 获取专业和班级列表
            majors = conn.execute("SELECT * FROM majors ORDER BY name").fetchall()
            classes = conn.execute("SELECT * FROM classes ORDER BY name").fetchall()
            # 返回表单数据和错误信息
            return render_template("students/create.html", 
                                  majors=majors, 
                                  classes=classes,
                                  student_id=student_id,
                                  name=name,
                                  gender=gender,
                                  birth_date=birth_date,
                                  address=address,
                                  phone=phone,
                                  email=email,
                                  major_id=major_id,
                                  class_id=class_id,
                                  enrollment_date=enrollment_date,
                                  error="该学号已存在，请使用其他学号")
        finally:
            conn.close()

    # 获取专业和班级列表
    majors = conn.execute("SELECT * FROM majors ORDER BY name").fetchall()
    classes = conn.execute("SELECT * FROM classes ORDER BY name").fetchall()
    conn.close()

    return render_template("students/create.html", majors=majors, classes=classes)

# 编辑学生信息
@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    conn = get_db_connection()

    # 获取学生信息
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()

    # 权限检查：普通用户只能编辑自己创建的学生信息
    if session.get("role") != "admin" and student["created_by"] != session["user_id"]:
        flash("您没有权限编辑此学生信息")
        return redirect(url_for("students"))

    if request.method == "POST":
        name = request.form["name"]
        gender = request.form["gender"]
        birth_date = request.form.get("birth_date")
        address = request.form.get("address")
        phone = request.form.get("phone")
        email = request.form.get("email")
        major_id = request.form.get("major_id")
        class_id = request.form.get("class_id")
        enrollment_date = request.form.get("enrollment_date")

        conn.execute("""
            UPDATE students SET 
            name = ?, gender = ?, birth_date = ?, address = ?, phone = ?, 
            email = ?, major_id = ?, class_id = ?, enrollment_date = ?
            WHERE id = ?
        """, (name, gender, birth_date, address, phone, email, major_id, class_id, enrollment_date, student_id))

        conn.commit()
        flash("学生信息更新成功")
        return redirect(url_for("students"))

    # 获取专业和班级列表
    majors = conn.execute("SELECT * FROM majors ORDER BY name").fetchall()
    classes = conn.execute("SELECT * FROM classes ORDER BY name").fetchall()
    conn.close()

    return render_template("students/edit.html", student=student, majors=majors, classes=classes)

# 删除学生信息
@app.route("/students/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student(student_id):
    conn = get_db_connection()

    # 获取学生信息
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()

    # 权限检查：普通用户只能删除自己创建的学生信息
    if session.get("role") != "admin" and student["created_by"] != session["user_id"]:
        flash("您没有权限删除此学生信息")
        return redirect(url_for("students"))

    conn.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()
    flash("学生信息删除成功")
    return redirect(url_for("students"))

# 专业管理
@app.route("/majors")
@login_required
def majors():
    conn = get_db_connection()
    majors = conn.execute("SELECT * FROM majors ORDER BY id ASC").fetchall()
    conn.close()
    return render_template("majors/index.html", majors=majors)

# 创建专业
@app.route("/majors/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_major():
    if request.method == "POST":
        name = request.form["name"]
        description = request.form.get("description")

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO majors (name, description) VALUES (?, ?)", (name, description))
            conn.commit()
            flash("专业创建成功")
            return redirect(url_for("majors"))
        except sqlite3.IntegrityError:
            flash("专业名称已存在")
        finally:
            conn.close()

    return render_template("majors/create.html")

# 编辑专业
@app.route("/majors/<int:major_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_major(major_id):
    conn = get_db_connection()
    major = conn.execute("SELECT * FROM majors WHERE id = ?", (major_id,)).fetchone()

    if request.method == "POST":
        name = request.form["name"]
        description = request.form.get("description")

        try:
            conn.execute("UPDATE majors SET name = ?, description = ? WHERE id = ?", 
                        (name, description, major_id))
            conn.commit()
            flash("专业信息更新成功")
            return redirect(url_for("majors"))
        except sqlite3.IntegrityError:
            flash("专业名称已存在")
        finally:
            conn.close()

    conn.close()
    return render_template("majors/edit.html", major=major)

# 删除专业
@app.route("/majors/<int:major_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_major(major_id):
    conn = get_db_connection()

    # 检查是否有学生使用该专业
    students = conn.execute("SELECT COUNT(*) as count FROM students WHERE major_id = ?", 
                           (major_id,)).fetchone()["count"]

    if students > 0:
        flash(f"该专业下还有 {students} 名学生，无法删除")
    else:
        conn.execute("DELETE FROM majors WHERE id = ?", (major_id,))
        conn.commit()
        flash("专业删除成功")

    conn.close()
    return redirect(url_for("majors"))

# 班级管理
@app.route("/classes")
@login_required
def classes():
    conn = get_db_connection()
    classes = conn.execute("""
        SELECT c.*, m.name as major_name 
        FROM classes c
        LEFT JOIN majors m ON c.major_id = m.id
        ORDER BY c.id ASC
    """).fetchall()
    conn.close()
    return render_template("classes/index.html", classes=classes)

# 创建班级
@app.route("/classes/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_class():
    conn = get_db_connection()

    if request.method == "POST":
        name = request.form["name"]
        major_id = request.form.get("major_id")
        description = request.form.get("description")

        try:
            conn.execute("INSERT INTO classes (name, major_id, description) VALUES (?, ?, ?)", 
                        (name, major_id, description))
            conn.commit()
            flash("班级创建成功")
            return redirect(url_for("classes"))
        except sqlite3.IntegrityError:
            flash("班级名称已存在")
        finally:
            conn.close()

    # 获取专业列表
    majors = conn.execute("SELECT * FROM majors ORDER BY name").fetchall()
    conn.close()

    return render_template("classes/create.html", majors=majors)

# 编辑班级
@app.route("/classes/<int:class_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_class(class_id):
    conn = get_db_connection()
    class_info = conn.execute("""
        SELECT c.*, m.name as major_name 
        FROM classes c
        LEFT JOIN majors m ON c.major_id = m.id
        WHERE c.id = ?
    """, (class_id,)).fetchone()

    if request.method == "POST":
        name = request.form["name"]
        major_id = request.form.get("major_id")
        description = request.form.get("description")

        try:
            conn.execute("UPDATE classes SET name = ?, major_id = ?, description = ? WHERE id = ?", 
                        (name, major_id, description, class_id))
            conn.commit()
            flash("班级信息更新成功")
            return redirect(url_for("classes"))
        except sqlite3.IntegrityError:
            flash("班级名称已存在")
        finally:
            conn.close()

    # 获取专业列表
    majors = conn.execute("SELECT * FROM majors ORDER BY name").fetchall()
    conn.close()

    return render_template("classes/edit.html", class_info=class_info, majors=majors)

# 删除班级
@app.route("/classes/<int:class_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_class(class_id):
    conn = get_db_connection()

    # 检查是否有学生使用该班级
    students = conn.execute("SELECT COUNT(*) as count FROM students WHERE class_id = ?", 
                           (class_id,)).fetchone()["count"]

    if students > 0:
        flash(f"该班级下还有 {students} 名学生，无法删除")
    else:
        conn.execute("DELETE FROM classes WHERE id = ?", (class_id,))
        conn.commit()
        flash("班级删除成功")

    conn.close()
    return redirect(url_for("classes"))

# 课程管理
@app.route("/courses")
@login_required
def courses():
    conn = get_db_connection()
    courses = conn.execute("SELECT * FROM courses ORDER BY id ASC").fetchall()
    conn.close()
    return render_template("courses/index.html", courses=courses)

# 创建课程
@app.route("/courses/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_course():
    if request.method == "POST":
        code = request.form["code"]
        name = request.form["name"]
        description = request.form.get("description")
        credits = request.form.get("credits")

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO courses (code, name, description, credits) VALUES (?, ?, ?, ?)", 
                        (code, name, description, credits))
            conn.commit()
            flash("课程创建成功")
            return redirect(url_for("courses"))
        except sqlite3.IntegrityError:
            flash("课程代码已存在")
        finally:
            conn.close()

    return render_template("courses/create.html")

# 编辑课程
@app.route("/courses/<int:course_id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit_course(course_id):
    conn = get_db_connection()
    course = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()

    if request.method == "POST":
        code = request.form["code"]
        name = request.form["name"]
        description = request.form.get("description")
        credits = request.form.get("credits")

        try:
            conn.execute("UPDATE courses SET code = ?, name = ?, description = ?, credits = ? WHERE id = ?", 
                        (code, name, description, credits, course_id))
            conn.commit()
            flash("课程信息更新成功")
            return redirect(url_for("courses"))
        except sqlite3.IntegrityError:
            flash("课程代码已存在")
        finally:
            conn.close()

    conn.close()
    return render_template("courses/edit.html", course=course)

# 删除课程
@app.route("/courses/<int:course_id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_course(course_id):
    conn = get_db_connection()

    # 检查是否有学生选了该课程
    enrollments = conn.execute("SELECT COUNT(*) as count FROM enrollments WHERE course_id = ?", 
                             (course_id,)).fetchone()["count"]

    if enrollments > 0:
        flash(f"该课程已有 {enrollments} 名学生选课，无法删除")
    else:
        conn.execute("DELETE FROM courses WHERE id = ?", (course_id,))
        conn.commit()
        flash("课程删除成功")

    conn.close()
    return redirect(url_for("courses"))

# 选课管理
@app.route("/enrollments")
@login_required
def enrollments():
    conn = get_db_connection()

    if session.get("role") == "admin":
        enrollments = conn.execute("""
            SELECT e.*, s.name as student_name, s.student_id, c.name as course_name, c.code
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN courses c ON e.course_id = c.id
            ORDER BY e.id ASC
        """).fetchall()
    else:
        # 普通用户只能看到自己创建的学生选课信息
        enrollments = conn.execute("""
            SELECT e.*, s.name as student_name, s.student_id, c.name as course_name, c.code
            FROM enrollments e
            JOIN students s ON e.student_id = s.id
            JOIN courses c ON e.course_id = c.id
            WHERE s.created_by = ?
            ORDER BY e.id ASC
        """, (session["user_id"],)).fetchall()

    conn.close()
    return render_template("enrollments/index.html", enrollments=enrollments)

# 创建选课记录
@app.route("/enrollments/create", methods=["GET", "POST"])
@login_required
def create_enrollment():
    conn = get_db_connection()

    if request.method == "POST":
        student_id = request.form["student_id"]
        course_id = request.form["course_id"]
        semester = request.form["semester"]

        # 检查是否已存在相同的选课记录
        existing = conn.execute("""
            SELECT * FROM enrollments 
            WHERE student_id = ? AND course_id = ? AND semester = ?
        """, (student_id, course_id, semester)).fetchone()

        if existing:
            flash("该学生在此学期已选择此课程")
        else:
            conn.execute("""
                INSERT INTO enrollments (student_id, course_id, semester)
                VALUES (?, ?, ?)
            """, (student_id, course_id, semester))
            conn.commit()
            flash("选课记录创建成功")
            return redirect(url_for("enrollments"))

    # 获取学生和课程列表
    if session.get("role") == "admin":
        students = conn.execute("SELECT * FROM students ORDER BY name").fetchall()
    else:
        # 普通用户只能看到自己创建的学生
        students = conn.execute("SELECT * FROM students WHERE created_by = ? ORDER BY name", 
                               (session["user_id"],)).fetchall()

    courses = conn.execute("SELECT * FROM courses ORDER BY code").fetchall()
    conn.close()

    return render_template("enrollments/create.html", students=students, courses=courses)

# 编辑选课记录
@app.route("/enrollments/<int:enrollment_id>/edit", methods=["GET", "POST"])
@login_required
def edit_enrollment(enrollment_id):
    conn = get_db_connection()

    # 获取选课记录
    enrollment = conn.execute("""
        SELECT e.*, s.name as student_name, s.student_id, c.name as course_name, c.code
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        JOIN courses c ON e.course_id = c.id
        WHERE e.id = ?
    """, (enrollment_id,)).fetchone()

    # 权限检查：普通用户只能编辑自己创建的学生选课记录
    if session.get("role") != "admin":
        student = conn.execute("SELECT created_by FROM students WHERE id = ?", 
                              (enrollment["student_id"],)).fetchone()
        if student["created_by"] != session["user_id"]:
            flash("您没有权限编辑此选课记录")
            return redirect(url_for("enrollments"))

    if request.method == "POST":
        student_id = request.form["student_id"]
        course_id = request.form["course_id"]
        semester = request.form["semester"]
        grade = request.form.get("grade")

        conn.execute("""
            UPDATE enrollments SET student_id = ?, course_id = ?, semester = ?, grade = ? WHERE id = ?
        """, (student_id, course_id, semester, grade, enrollment_id))

        conn.commit()
        flash("选课记录更新成功")
        return redirect(url_for("enrollments"))

    # 获取所有学生和课程列表
    students = conn.execute("SELECT id, student_id, name FROM students").fetchall()
    courses = conn.execute("SELECT id, code, name FROM courses").fetchall()
    conn.close()
    return render_template("enrollments/edit.html", enrollment=enrollment, students=students, courses=courses)

# 删除选课记录
@app.route("/enrollments/<int:enrollment_id>/delete", methods=["POST"])
@login_required
def delete_enrollment(enrollment_id):
    conn = get_db_connection()

    # 获取选课记录
    enrollment = conn.execute("SELECT * FROM enrollments WHERE id = ?", (enrollment_id,)).fetchone()

    # 权限检查：普通用户只能删除自己创建的学生选课记录
    if session.get("role") != "admin":
        student = conn.execute("SELECT created_by FROM students WHERE id = ?", 
                              (enrollment["student_id"],)).fetchone()
        if student["created_by"] != session["user_id"]:
            flash("您没有权限删除此选课记录")
            return redirect(url_for("enrollments"))

    conn.execute("DELETE FROM enrollments WHERE id = ?", (enrollment_id,))
    conn.commit()
    conn.close()
    flash("选课记录删除成功")
    return redirect(url_for("enrollments"))

# 学生成绩查看
@app.route("/students/<int:student_id>/grades")
@login_required
def student_grades(student_id):
    conn = get_db_connection()

    # 获取学生信息（包括专业和班级名称）
    student = conn.execute("""
        SELECT s.*, m.name as major_name, c.name as class_name
        FROM students s
        LEFT JOIN majors m ON s.major_id = m.id
        LEFT JOIN classes c ON s.class_id = c.id
        WHERE s.id = ?
    """, (student_id,)).fetchone()

    # 权限检查：普通用户只能查看自己创建的学生成绩
    if session.get("role") != "admin" and student["created_by"] != session["user_id"]:
        flash("您没有权限查看此学生成绩")
        return redirect(url_for("students"))

    # 获取学生成绩（包括没有成绩的选课记录）
    enrollments = conn.execute("""
        SELECT e.*, c.name as course_name, c.code, c.credits, g.score
        FROM enrollments e
        JOIN courses c ON e.course_id = c.id
        LEFT JOIN grades g ON e.id = g.enrollment_id
        WHERE e.student_id = ?
        ORDER BY e.semester DESC
    """, (student_id,)).fetchall()

    conn.close()
    return render_template("students/grades.html", student=student, grades=enrollments)

# 成绩管理
@app.route("/grades")
@login_required
def grades():
    conn = get_db_connection()

    # 获取筛选条件
    student_id = request.args.get('student_id')
    course_id = request.args.get('course_id')
    semester = request.args.get('semester')

    # 构建查询
    query = """
        SELECT g.id, s.name as student_name, s.student_id, 
               c.name as course_name, e.semester, g.score, 
               g.created_at, u.username as teacher_name
        FROM grades g
        JOIN enrollments e ON g.enrollment_id = e.id
        JOIN students s ON e.student_id = s.id
        JOIN courses c ON e.course_id = c.id
        LEFT JOIN users u ON g.teacher_id = u.id
    """
    params = []

    # 添加筛选条件
    if student_id:
        query += " WHERE s.id = ?"
        params.append(student_id)

    if course_id:
        if not student_id:
            query += " WHERE c.id = ?"
        else:
            query += " AND c.id = ?"
        params.append(course_id)

    if semester:
        if not student_id and not course_id:
            query += " WHERE e.semester = ?"
        else:
            query += " AND e.semester = ?"
        params.append(semester)

    # 权限检查：普通用户只能看到自己创建的学生成绩
    if session.get("role") != "admin":
        if not student_id and not course_id and not semester:
            query += " WHERE s.created_by = ?"
        else:
            query += " AND s.created_by = ?"
        params.append(session["user_id"])

    query += " ORDER BY g.created_at DESC"

    # 执行查询
    grades = conn.execute(query, params).fetchall()

    # 计算统计数据
    total_grades = len(grades)
    scores = [grade["score"] for grade in grades if grade["score"] is not None]
    average_score = sum(scores) / len(scores) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0

    # 获取学生列表
    if session.get("role") == "admin":
        students = conn.execute("SELECT id, name, student_id FROM students ORDER BY name").fetchall()
    else:
        students = conn.execute("SELECT id, name, student_id FROM students WHERE created_by = ? ORDER BY name", 
                               (session["user_id"],)).fetchall()

    # 获取课程列表
    courses = conn.execute("SELECT id, name FROM courses ORDER BY name").fetchall()

    conn.close()

    return render_template("grades/index.html", 
                          grades=grades, 
                          total_grades=total_grades,
                          average_score=average_score,
                          max_score=max_score,
                          min_score=min_score,
                          students=students,
                          courses=courses)

# 创建成绩
@app.route("/grades/create", methods=["GET", "POST"])
@login_required
def create_grade():
    conn = get_db_connection()

    if request.method == "POST":
        student_id = request.form["student_id"]
        course_id = request.form["course_id"]
        semester = request.form["semester"]
        score = float(request.form["grade"])

        # 检查是否已存在相同的选课记录
        enrollment = conn.execute("""
            SELECT * FROM enrollments
            WHERE student_id = ? AND course_id = ? AND semester = ?
        """, (student_id, course_id, semester)).fetchone()

        if not enrollment:
            # 创建选课记录
            cursor = conn.execute("""
                INSERT INTO enrollments (student_id, course_id, semester)
                VALUES (?, ?, ?)
            """, (student_id, course_id, semester))
            enrollment_id = cursor.lastrowid
        else:
            enrollment_id = enrollment["id"]

        # 检查是否已存在成绩记录
        existing_grade = conn.execute("""
            SELECT * FROM grades WHERE enrollment_id = ?
        """, (enrollment_id,)).fetchone()

        if existing_grade:
            # 更新现有记录
            conn.execute("""
                UPDATE grades SET score = ?, updated_at = CURRENT_TIMESTAMP
                WHERE enrollment_id = ?
            """, (score, enrollment_id))
            flash("成绩更新成功")
        else:
            # 创建新成绩记录
            conn.execute("""
                INSERT INTO grades (enrollment_id, score, teacher_id)
                VALUES (?, ?, ?)
            """, (enrollment_id, score, session["user_id"]))
            flash("成绩录入成功")

        conn.commit()
        conn.close()
        return redirect(url_for("grades"))

    # 获取学生和课程列表
    if session.get("role") == "admin":
        students = conn.execute("SELECT id, name, student_id FROM students ORDER BY name").fetchall()
    else:
        students = conn.execute("SELECT id, name, student_id FROM students WHERE created_by = ? ORDER BY name",
                               (session["user_id"],)).fetchall()

    courses = conn.execute("SELECT id, name FROM courses ORDER BY name").fetchall()
    conn.close()

    return render_template("grades/create.html", students=students, courses=courses)

# 编辑成绩
@app.route("/grades/<int:grade_id>/edit", methods=["GET", "POST"])
@login_required
def edit_grade(grade_id):
    conn = get_db_connection()

    # 获取成绩记录
    grade = conn.execute("""
        SELECT g.*, e.student_id, e.course_id, e.semester, 
               s.name as student_name, s.student_id as student_number, 
               c.name as course_name, c.code
        FROM grades g
        JOIN enrollments e ON g.enrollment_id = e.id
        JOIN students s ON e.student_id = s.id
        JOIN courses c ON e.course_id = c.id
        WHERE g.id = ?
    """, (grade_id,)).fetchone()

    # 权限检查：普通用户只能编辑自己创建的学生成绩
    if session.get("role") != "admin":
        student = conn.execute("SELECT created_by FROM students WHERE id = ?",
                              (grade["student_id"],)).fetchone()
        if student["created_by"] != session["user_id"]:
            flash("您没有权限编辑此成绩记录")
            return redirect(url_for("grades"))

    if request.method == "POST":
        new_score = float(request.form["grade"])

        conn.execute("""
            UPDATE grades SET score = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (new_score, grade_id))
        conn.commit()
        flash("成绩更新成功")
        return redirect(url_for("grades"))

    conn.close()
    return render_template("grades/edit.html", grade=grade)

# 删除成绩
@app.route("/grades/<int:grade_id>/delete", methods=["POST"])
@login_required
def delete_grade(grade_id):
    conn = get_db_connection()

    # 获取成绩记录
    grade = conn.execute("""
        SELECT g.*, e.student_id, s.created_by as student_creator
        FROM grades g
        JOIN enrollments e ON g.enrollment_id = e.id
        JOIN students s ON e.student_id = s.id
        WHERE g.id = ?
    """, (grade_id,)).fetchone()

    # 权限检查：普通用户只能删除自己创建的学生成绩
    if session.get("role") != "admin" and grade["student_creator"] != session["user_id"]:
        flash("您没有权限删除此成绩记录")
        return redirect(url_for("grades"))

    conn.execute("DELETE FROM grades WHERE id = ?", (grade_id,))
    conn.commit()
    conn.close()
    flash("成绩删除成功")
    return redirect(url_for("grades"))

# 批量导入成绩
@app.route("/grades/import", methods=["GET", "POST"])
@login_required
def import_grades():
    if request.method == "POST":
        # 这里应该实现文件上传和解析逻辑
        flash("批量导入功能正在开发中")
        return redirect(url_for("grades"))

    return render_template("grades/import.html")

# 导出成绩
@app.route("/grades/export")
@login_required
def export_grades():
    # 这里应该实现导出逻辑
    flash("导出功能正在开发中")
    return redirect(url_for("grades"))

if __name__ == "__main__":
    init_db()  # 初始化数据库
    app.run(debug=True)
