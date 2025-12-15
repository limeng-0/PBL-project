
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_from_directory
from flask_wtf.csrf import CSRFProtect
import sqlite3
from functools import wraps
from datetime import datetime
import os
import time
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # 用于session加密
csrf = CSRFProtect(app)  # 启用CSRF保护

# 数据库初始化
def init_db():
    conn = sqlite3.connect('student_management.db')
    cursor = conn.cursor()

    # 检查students表是否有avatar字段，如果没有则添加
    cursor.execute("PRAGMA table_info(students)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'avatar' not in columns:
        cursor.execute("ALTER TABLE students ADD COLUMN avatar TEXT")
        conn.commit()
        print("已添加avatar字段到students表")
    
    # 检查courses表是否有major_id字段，如果没有则添加
    cursor.execute("PRAGMA table_info(courses)")
    columns = [column[1] for column in cursor.fetchall()]

    if 'major_id' not in columns:
        cursor.execute("ALTER TABLE courses ADD COLUMN major_id INTEGER")
        conn.commit()
        print("已添加major_id字段到courses表")
    
    # 检查并添加其他新字段
    if 'teacher' not in columns:
        cursor.execute("ALTER TABLE courses ADD COLUMN teacher TEXT")
        conn.commit()
        print("已添加teacher字段到courses表")
    
    if 'class_time' not in columns:
        cursor.execute("ALTER TABLE courses ADD COLUMN class_time TEXT")
        conn.commit()
        print("已添加class_time字段到courses表")
    
    if 'location' not in columns:
        cursor.execute("ALTER TABLE courses ADD COLUMN location TEXT")
        conn.commit()
        print("已添加location字段到courses表")
    
    if 'max_students' not in columns:
        cursor.execute("ALTER TABLE courses ADD COLUMN max_students INTEGER DEFAULT 50")
        conn.commit()
        print("已添加max_students字段到courses表")

    # 用户表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        role TEXT NOT NULL DEFAULT 'user',
        name TEXT NOT NULL,
        student_id TEXT UNIQUE,
        student_record_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_record_id) REFERENCES students (id)
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
        avatar TEXT,
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
        major_id INTEGER,
        teacher TEXT,
        class_time TEXT,
        location TEXT,
        max_students INTEGER DEFAULT 50,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (major_id) REFERENCES majors (id)
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

    # 检查用户表是否有name、student_id和student_record_id字段，如果没有则添加
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]

    if "name" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN name TEXT")
        # 为现有用户设置默认名称
        cursor.execute("UPDATE users SET name = username WHERE name IS NULL")

    if "student_id" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN student_id TEXT")

    if "student_record_id" not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN student_record_id INTEGER")

    # 检查是否已有管理员用户，如果没有则创建
    cursor.execute("SELECT * FROM users WHERE role='admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, email, role, name) VALUES (?, ?, ?, ?, ?)",
                      ("admin", "admin123", "admin@example.com", "admin", "系统管理员"))

    # 检查是否已有测试学生用户，如果没有则创建
    cursor.execute("SELECT * FROM users WHERE username='student'")
    if not cursor.fetchone():
        # 先创建学生记录
        cursor.execute("INSERT INTO students (student_id, name, gender, major_id, class_id) VALUES (?, ?, ?, ?, ?)",
                      ("20210001", "张三", "男", 1, 1))
        student_id = cursor.lastrowid

        # 然后创建用户记录并关联到学生记录
        cursor.execute("INSERT INTO users (username, password, email, role, name, student_id, student_record_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      ("student", "student123", "student@example.com", "user", "张三", "20210001", student_id))

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
            session["name"] = user["name"] if "name" in user.keys() else ""
            session["student_id"] = user["student_id"] if "student_id" in user.keys() else ""
            session["student_record_id"] = user["student_record_id"] if "student_record_id" in user.keys() else None
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
    conn = get_db_connection()

    # 如果用户是学生，根据用户名获取其关联的学生记录
    if session.get("role") == "user":
        # 首先获取用户信息
        user = conn.execute("SELECT * FROM users WHERE username = ?", 
                          (session.get("username"),)).fetchone()

        if not user:
            conn.close()
            flash("无法获取用户信息")
            return redirect(url_for("dashboard"))

        # 如果用户表中有student_record_id，直接使用
        if user["student_record_id"]:
            student = conn.execute("""
                SELECT s.*, m.name as major_name, c.name as class_name
                FROM students s
                LEFT JOIN majors m ON s.major_id = m.id
                LEFT JOIN classes c ON s.class_id = c.id
                WHERE s.id = ?
            """, (user["student_record_id"],)).fetchone()
        # 否则根据学号查找学生记录
        elif user["student_id"]:
            student = conn.execute("""
                SELECT s.*, m.name as major_name, c.name as class_name
                FROM students s
                LEFT JOIN majors m ON s.major_id = m.id
                LEFT JOIN classes c ON s.class_id = c.id
                WHERE s.student_id = ?
            """, (user["student_id"],)).fetchone()

            # 如果找到了学生记录，更新用户表中的student_record_id
            if student:
                conn.execute("UPDATE users SET student_record_id = ? WHERE id = ?",
                            (student["id"], user["id"]))
                conn.commit()
        else:
            student = None

        conn.close()
        return render_template("students/profile.html", student=student)
    else:
        conn.close()
        flash("无法获取学生信息")
        return redirect(url_for("dashboard"))

# 修改个人信息
@app.route("/edit_profile", methods=['GET', 'POST'])
@login_required
def edit_profile():
    conn = get_db_connection()

    # 获取用户信息
    user = conn.execute("SELECT * FROM users WHERE username = ?", 
                      (session.get("username"),)).fetchone()

    if not user:
        conn.close()
        flash("无法获取用户信息")
        return redirect(url_for("dashboard"))

    # 获取学生记录ID
    student_record_id = user["student_record_id"] if user["student_record_id"] else None

    # 如果没有student_record_id，尝试根据学号查找
    if not student_record_id and user["student_id"]:
        student = conn.execute("SELECT * FROM students WHERE student_id = ?", 
                             (user["student_id"],)).fetchone()
        if student:
            student_record_id = student["id"]
            # 更新用户表
            conn.execute("UPDATE users SET student_record_id = ? WHERE id = ?",
                        (student_record_id, user["id"]))
            conn.commit()

    if request.method == 'POST':
        # 获取表单数据
        name = request.form.get("name")
        gender = request.form.get("gender")
        birth_date = request.form.get("birth_date")
        address = request.form.get("address")
        phone = request.form.get("phone")
        email = request.form.get("email")

        # 更新学生信息
        if student_record_id:
            conn.execute("""
                UPDATE students SET
                name = ?, gender = ?, birth_date = ?, address = ?, phone = ?, email = ?
                WHERE id = ?
            """, (name, gender, birth_date, address, phone, email, student_record_id))
            conn.commit()

        conn.close()
        flash("个人信息已更新")
        return redirect(url_for("my_profile"))

    # GET请求，获取当前学生信息
    student = None
    if student_record_id:
        student = conn.execute("SELECT * FROM students WHERE id = ?", 
                              (student_record_id,)).fetchone()

    conn.close()

    return render_template("students/edit_profile.html", student=student)

# 忘记密码
@app.route("/forgot_password", methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # 验证输入
        if not username or not password or not confirm_password:
            flash('请填写所有必填字段', 'danger')
            return render_template("forgot_password.html")

        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return render_template("forgot_password.html")

        # 查找用户
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user:
            # 更新密码
            conn.execute("UPDATE users SET password = ? WHERE id = ?", (password, user["id"]))
            conn.commit()
            conn.close()
            flash('密码已成功重置！', 'success')
            return redirect(url_for('login'))
        else:
            conn.close()
            flash('未找到该用户名', 'danger')
            return render_template("forgot_password.html")

    return render_template("forgot_password.html")

# 修改密码
@app.route("/change_password", methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        # 处理修改密码逻辑
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        # 验证输入
        if not old_password or not new_password or not confirm_password:
            flash('请填写所有字段', 'danger')
            return render_template("change_password.html")

        if new_password != confirm_password:
            flash('新密码和确认密码不匹配', 'danger')
            return render_template("change_password.html")

        if len(new_password) < 6:
            flash('新密码长度至少为6位', 'danger')
            return render_template("change_password.html")

        # 验证旧密码是否正确
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE id = ?", (session.get("user_id"),)).fetchone()

        if user and user["password"] == old_password:
            # 更新密码
            conn.execute("UPDATE users SET password = ? WHERE id = ?", 
                        (new_password, session.get("user_id")))
            conn.commit()
            conn.close()

            flash('密码已成功修改', 'success')
            return redirect(url_for('my_profile'))
        else:
            conn.close()
            flash('旧密码不正确', 'danger')
            return render_template("change_password.html")

    return render_template("change_password.html")

# 浏览课程
@app.route("/browse_courses")
@login_required
def browse_courses():
    conn = get_db_connection()
    
    # 获取用户信息
    user = conn.execute("SELECT * FROM users WHERE username = ?",
                      (session.get("username"),)).fetchone()
    
    if not user:
        conn.close()
        flash("无法获取用户信息")
        return redirect(url_for("dashboard"))
    
    # 获取学生记录ID
    student_record_id = user["student_record_id"] if user["student_record_id"] else None
    
    # 如果没有student_record_id，尝试根据学号查找
    if not student_record_id and user["student_id"]:
        student = conn.execute("SELECT * FROM students WHERE student_id = ?",
                             (user["student_id"],)).fetchone()
        if student:
            student_record_id = student["id"]
            # 更新用户表
            conn.execute("UPDATE users SET student_record_id = ? WHERE id = ?",
                        (student_record_id, user["id"]))
            conn.commit()
    
    # 获取所有专业
    majors = conn.execute("SELECT * FROM majors").fetchall()
    
    # 获取所有课程
    all_courses = conn.execute("SELECT DISTINCT id, name FROM courses ORDER BY name").fetchall()
    
    # 获取所有教师
    teachers_query = conn.execute("SELECT DISTINCT teacher FROM courses WHERE teacher IS NOT NULL AND teacher != '' ORDER BY teacher").fetchall()
    teachers = [teacher["teacher"] for teacher in teachers_query]
    
    # 打印调试信息
    print(f"课程数量: {len(all_courses)}")
    print(f"教师数量: {len(teachers)}")
    if all_courses:
        print(f"第一个课程: {all_courses[0]}")
    if teachers:
        print(f"第一个教师: {teachers[0]}")
    
    # 检查数据库中是否有课程数据
    total_courses = conn.execute("SELECT COUNT(*) as count FROM courses").fetchone()["count"]
    print(f"数据库中总课程数: {total_courses}")
    
    # 检查是否有教师数据
    courses_with_teacher = conn.execute("SELECT COUNT(*) as count FROM courses WHERE teacher IS NOT NULL AND teacher != ''").fetchone()["count"]
    print(f"有教师数据的课程数: {courses_with_teacher}")
    
    # 如果数据库中没有课程数据，添加一些示例数据
    if total_courses == 0:
        print("添加示例课程数据...")
        sample_courses = [
            ("CS101", "计算机科学导论", "张教授", "周一 8:00-10:00", "A101", 50, "计算机科学基础课程", 3),
            ("CS102", "数据结构", "李教授", "周二 14:00-16:00", "B203", 40, "数据结构与算法", 4),
            ("CS103", "操作系统", "王教授", "周三 10:00-12:00", "C305", 30, "操作系统原理与实践", 4),
            ("CS104", "计算机网络", "赵教授", "周四 14:00-16:00", "D201", 35, "计算机网络基础", 3),
            ("CS105", "数据库系统", "刘教授", "周五 8:00-10:00", "E102", 45, "数据库原理与应用", 3)
        ]
        
        for course in sample_courses:
            conn.execute("""
                INSERT INTO courses (code, name, teacher, class_time, location, max_students, description, credits) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, course)
        conn.commit()
        print("示例数据添加完成")
        
        # 重新获取课程和教师数据
        all_courses = conn.execute("SELECT DISTINCT id, name FROM courses ORDER BY name").fetchall()
        teachers_query = conn.execute("SELECT DISTINCT teacher FROM courses WHERE teacher IS NOT NULL AND teacher != '' ORDER BY teacher").fetchall()
        teachers = [teacher["teacher"] for teacher in teachers_query]
    
    # 获取查询参数
    search = request.args.get('search', '')
    teacher = request.args.get('teacher', '')
    credit = request.args.get('credit', '')
    
    # 构建查询语句
    query = "SELECT * FROM courses WHERE 1=1"
    params = []
    
    # 添加搜索条件
    if search:
        query += " AND (name LIKE ? OR code LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])
    
    # 添加教师搜索条件
    if teacher:
        query += " AND teacher LIKE ?"
        params.append(f'%{teacher}%')
    
    # 添加学分筛选条件
    if credit:
        query += " AND credits = ?"
        params.append(credit)
    
    # 执行查询
    courses = conn.execute(query, params).fetchall()
    
    # 获取每门课程的已选人数
    enroll_counts = {}
    for course in courses:
        count = conn.execute("SELECT COUNT(*) as count FROM enrollments WHERE course_id = ?",
                           (course["id"],)).fetchone()["count"]
        enroll_counts[course["id"]] = count
    
    # 获取该学生已选的课程ID列表
    selected_course_ids = []
    if student_record_id:
        selected_courses = conn.execute("SELECT course_id FROM enrollments WHERE student_id = ?",
                                      (student_record_id,)).fetchall()
        selected_course_ids = [course["course_id"] for course in selected_courses]
    
    conn.close()
    
    return render_template("students/browse_courses.html", 
                         courses=courses, 
                         majors=majors,
                         all_courses=all_courses,
                         teachers=teachers,
                         enroll_counts=enroll_counts,
                         selected_course_ids=selected_course_ids)

# 我的选课
@app.route("/my_selections")
@login_required
def my_selections():
    conn = get_db_connection()
    
    # 获取用户信息
    user = conn.execute("SELECT * FROM users WHERE username = ?",
                      (session.get("username"),)).fetchone()
    
    if not user:
        conn.close()
        flash("无法获取用户信息")
        return redirect(url_for("dashboard"))
    
    # 获取学生记录ID
    student_record_id = user["student_record_id"] if user["student_record_id"] else None
    
    # 如果没有student_record_id，尝试根据学号查找
    if not student_record_id and user["student_id"]:
        student = conn.execute("SELECT * FROM students WHERE student_id = ?",
                             (user["student_id"],)).fetchone()
        if student:
            student_record_id = student["id"]
            # 更新用户表
            conn.execute("UPDATE users SET student_record_id = ? WHERE id = ?",
                        (student_record_id, user["id"]))
            conn.commit()
    
    # 获取该学生已选的课程
    enrollments = []
    if student_record_id:
        enrollments = conn.execute("""
            SELECT e.id as enrollment_id, c.id as course_id, c.code, c.name, c.description, c.credits,
                   c.teacher, c.class_time, c.location, c.max_students,
                   e.semester, g.score
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            LEFT JOIN grades g ON e.id = g.enrollment_id
            WHERE e.student_id = ?
            ORDER BY e.semester DESC
        """, (student_record_id,)).fetchall()
    
    conn.close()
    
    return render_template("students/my_selections.html", enrollments=enrollments)

# 我的成绩
@app.route("/my_grades")
@login_required
def my_grades():
    conn = get_db_connection()

    # 获取用户信息
    user = conn.execute("SELECT * FROM users WHERE username = ?",
                      (session.get("username"),)).fetchone()

    if not user:
        conn.close()
        flash("无法获取用户信息")
        return redirect(url_for("dashboard"))

    # 获取学生记录ID
    student_record_id = user["student_record_id"] if user["student_record_id"] else None

    # 如果没有student_record_id，尝试根据学号查找
    if not student_record_id and user["student_id"]:
        student = conn.execute("SELECT * FROM students WHERE student_id = ?",
                             (user["student_id"],)).fetchone()
        if student:
            student_record_id = student["id"]
            # 更新用户表
            conn.execute("UPDATE users SET student_record_id = ? WHERE id = ?",
                        (student_record_id, user["id"]))
            conn.commit()

    # 获取学生成绩数据
    grades = []
    if student_record_id:
        grades = conn.execute("""
            SELECT g.id as grade_id, c.code, c.name as course_name, c.credits,
                   c.teacher as teacher_name, e.semester,
                   g.score
            FROM grades g
            JOIN enrollments e ON g.enrollment_id = e.id
            JOIN courses c ON e.course_id = c.id
            WHERE e.student_id = ?
            ORDER BY c.code
        """, (student_record_id,)).fetchall()

    conn.close()

    return render_template("students/my_grades.html", grades=grades)

# 学生仪表盘
@app.route("/students/dashboard")
@login_required
def students_dashboard():
    conn = get_db_connection()

    # 获取用户信息
    user = conn.execute("SELECT * FROM users WHERE username = ?", 
                      (session.get("username"),)).fetchone()

    if not user:
        conn.close()
        flash("无法获取用户信息")
        return redirect(url_for("dashboard"))

    # 获取学生记录ID
    student_record_id = user["student_record_id"] if user["student_record_id"] else None

    # 如果没有student_record_id，尝试根据学号查找
    if not student_record_id and user["student_id"]:
        student = conn.execute("SELECT * FROM students WHERE student_id = ?", 
                             (user["student_id"],)).fetchone()
        if student:
            student_record_id = student["id"]
            # 更新用户表
            conn.execute("UPDATE users SET student_record_id = ? WHERE id = ?",
                        (student_record_id, user["id"]))
            conn.commit()

    # 学生仪表盘数据
    if student_record_id:
        # 获取所有课程数量
        course_count = conn.execute("SELECT COUNT(*) as count FROM courses").fetchone()["count"]
        
        # 获取该学生的选课记录数
        enrollment_count = conn.execute("""
            SELECT COUNT(*) as count
            FROM enrollments
            WHERE student_id = ?
        """, (student_record_id,)).fetchone()["count"]

        # 获取平均成绩
        avg_grade = conn.execute("""
            SELECT AVG(g.score) as avg
            FROM grades g
            JOIN enrollments e ON g.enrollment_id = e.id
            WHERE e.student_id = ?
        """, (student_record_id,)).fetchone()["avg"]

        average_grade = "{:.2f}".format(avg_grade) if avg_grade else "0.00"

        # 获取已出成绩的课程数
        graded_courses = conn.execute("""
            SELECT COUNT(DISTINCT e.id) as count
            FROM enrollments e
            JOIN grades g ON e.id = g.enrollment_id
            WHERE e.student_id = ?
        """, (student_record_id,)).fetchone()["count"]

        # 获取未出成绩的课程数
        ungraded_courses = conn.execute("""
            SELECT COUNT(*) as count
            FROM enrollments
            WHERE student_id = ? AND id NOT IN (
                SELECT DISTINCT enrollment_id FROM grades
            )
        """, (student_record_id,)).fetchone()["count"]

        # 获取学生个人信息
        student = conn.execute("""
            SELECT s.*, m.name as major_name, c.name as class_name
            FROM students s
            LEFT JOIN majors m ON s.major_id = m.id
            LEFT JOIN classes c ON s.class_id = c.id
            WHERE s.id = ?
        """, (student_record_id,)).fetchone()
    else:
        # 如果没有学生记录，设置默认值
        course_count = conn.execute("SELECT COUNT(*) as count FROM courses").fetchone()["count"]
        enrollment_count = 0
        average_grade = "0.00"
        graded_courses = 0
        ungraded_courses = 0
        student = None

    conn.close()

    return render_template("students/dashboard.html",
                          student=student,
                          course_count=course_count,
                          my_selections_count=enrollment_count,
                          average_grade=average_grade,
                          graded_courses=graded_courses,
                          ungraded_courses=ungraded_courses,
                          student_count=1,  # 当前登录的学生数量为1
                          pending_grades=ungraded_courses)  # 待录入成绩等于未出成绩的课程数
    
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
@admin_required
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
    
    # 获取每门课程的已选人数
    enroll_counts = {}
    for course in courses:
        count = conn.execute("SELECT COUNT(*) as count FROM enrollments WHERE course_id = ?",
                           (course["id"],)).fetchone()["count"]
        enroll_counts[course["id"]] = count
    
    conn.close()
    return render_template("courses/index.html", courses=courses, enroll_counts=enroll_counts)

# 创建课程
@app.route("/courses/create", methods=["GET", "POST"])
@login_required
@admin_required
def create_course():
    if request.method == "POST":
        code = request.form["code"]
        name = request.form["name"]
        teacher = request.form.get("teacher")
        class_time = request.form.get("class_time")
        location = request.form.get("location")
        max_students = request.form.get("max_students", "50")
        description = request.form.get("description")
        credits = request.form.get("credits")

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO courses (code, name, teacher, class_time, location, max_students, description, credits) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                        (code, name, teacher, class_time, location, max_students, description, credits))
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
        teacher = request.form.get("teacher")
        class_time = request.form.get("class_time")
        location = request.form.get("location")
        description = request.form.get("description")
        credits = request.form.get("credits")

        try:
            conn.execute("UPDATE courses SET code = ?, name = ?, teacher = ?, class_time = ?, location = ?, description = ?, credits = ? WHERE id = ?", 
                        (code, name, teacher, class_time, location, description, credits, course_id))
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

# 学生选课AJAX接口
@app.route("/api/enroll_course", methods=["POST"])
@csrf.exempt  # 免除CSRF保护
@login_required
def enroll_course():
    conn = get_db_connection()

    try:
        # 获取课程ID
        if request.is_json:
            data = request.get_json()
            course_id = data.get('course_id')
        else:
            course_id = request.args.get('course_id')

        if not course_id:
            conn.close()
            return jsonify({"success": False, "message": "缺少课程ID"})

        # 获取当前登录用户信息
        user = conn.execute("SELECT * FROM users WHERE username = ?",
                          (session.get("username"),)).fetchone()

        if not user:
            conn.close()
            return jsonify({"success": False, "message": "无法获取用户信息"})

        # 获取学生记录ID
        student_record_id = user["student_record_id"]
        if not student_record_id and user["student_id"]:
            student = conn.execute("SELECT * FROM students WHERE student_id = ?",
                                 (user["student_id"],)).fetchone()
            if student:
                student_record_id = student["id"]
                # 更新用户表
                conn.execute("UPDATE users SET student_record_id = ? WHERE id = ?",
                            (student_record_id, user["id"]))
                conn.commit()

        if not student_record_id:
            conn.close()
            return jsonify({"success": False, "message": "无法找到学生记录"})

        # 获取当前学期
        current_semester = "2023-2024学年第一学期"  # 这里应该从系统设置或配置中获取

        # 检查是否已存在相同的选课记录
        existing = conn.execute("""
            SELECT * FROM enrollments
            WHERE student_id = ? AND course_id = ? AND semester = ?
        """, (student_record_id, course_id, current_semester)).fetchone()

        if existing:
            conn.close()
            return jsonify({"success": False, "message": "您已选择此课程"})

        # 检查课程是否已满员
        course = conn.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
        if course:
            enrolled_count = conn.execute("SELECT COUNT(*) as count FROM enrollments WHERE course_id = ?",
                                       (course_id,)).fetchone()["count"]
            max_students = course["max_students"] if course["max_students"] else 50

            if enrolled_count >= max_students:
                conn.close()
                return jsonify({"success": False, "message": "课程已满员"})

        # 创建选课记录
        conn.execute("""
            INSERT INTO enrollments (student_id, course_id, semester)
            VALUES (?, ?, ?)
        """, (student_record_id, course_id, current_semester))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "选课成功"})
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "message": f"选课过程中发生错误: {str(e)}"})

# 学生退课AJAX接口
@app.route("/api/drop_course", methods=["POST"])
@csrf.exempt  # 免除CSRF保护
@login_required
def drop_course():
    conn = get_db_connection()

    try:
        # 获取选课记录ID
        if request.is_json:
            data = request.get_json()
            enrollment_id = data.get('enrollment_id')
        else:
            enrollment_id = request.args.get('enrollment_id')

        if not enrollment_id:
            conn.close()
            return jsonify({"success": False, "message": "缺少选课记录ID"})

        # 获取当前登录用户信息
        user = conn.execute("SELECT * FROM users WHERE username = ?",
                          (session.get("username"),)).fetchone()

        if not user:
            conn.close()
            return jsonify({"success": False, "message": "无法获取用户信息"})

        # 获取学生记录ID
        student_record_id = user["student_record_id"]
        if not student_record_id and user["student_id"]:
            student = conn.execute("SELECT * FROM students WHERE student_id = ?",
                                 (user["student_id"],)).fetchone()
            if student:
                student_record_id = student["id"]

        # 验证选课记录是否属于当前学生
        enrollment = conn.execute("""
            SELECT e.*, c.name as course_name
            FROM enrollments e
            JOIN courses c ON e.course_id = c.id
            WHERE e.id = ? AND e.student_id = ?
        """, (enrollment_id, student_record_id)).fetchone()

        if not enrollment:
            conn.close()
            return jsonify({"success": False, "message": "找不到选课记录或无权限操作"})

        # 删除选课记录
        conn.execute("DELETE FROM enrollments WHERE id = ?", (enrollment_id,))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "message": "退课成功"})
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "message": f"退课过程中发生错误: {str(e)}"})

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
        students = conn.execute("SELECT id, student_id, name FROM students ORDER BY student_id").fetchall()
    else:
        # 普通用户只能看到自己创建的学生
        students = conn.execute("SELECT id, student_id, name FROM students WHERE created_by = ? ORDER BY student_id", 
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

    query += " ORDER BY g.id ASC"

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

        # 验证成绩输入
        try:
            score = float(request.form["grade"])
            if score < 0 or score > 100:
                flash("成绩必须在0-100之间")
                return redirect(request.url)
        except ValueError:
            flash("请输入有效的成绩数字")
            return redirect(request.url)

        # 检查学生是否存在
        student = conn.execute("SELECT id, created_by FROM students WHERE id = ?", (student_id,)).fetchone()
        if not student:
            flash("所选学生不存在")
            return redirect(request.url)

        # 检查课程是否存在
        course = conn.execute("SELECT id FROM courses WHERE id = ?", (course_id,)).fetchone()
        if not course:
            flash("所选课程不存在")
            return redirect(request.url)

        # 权限检查：普通用户只能为自己创建的学生录入成绩
        if session.get("role") != "admin" and student["created_by"] != session["user_id"]:
            flash("您没有权限为该学生录入成绩")
            return redirect(request.url)

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
    conn = get_db_connection()

    # 获取筛选条件
    student_id = request.args.get('student_id')
    course_id = request.args.get('course_id')
    semester = request.args.get('semester')

    # 构建查询
    query = """
        SELECT s.student_id as '学号', s.name as '姓名', 
               c.code as '课程代码', c.name as '课程名称', 
               e.semester as '学期', g.score as '成绩',
               u.username as '录入教师', g.created_at as '录入时间'
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

    # 权限检查：普通用户只能导出自己创建的学生成绩
    if session.get("role") != "admin":
        if not student_id and not course_id and not semester:
            query += " WHERE s.created_by = ?"
        else:
            query += " AND s.created_by = ?"
        params.append(session["user_id"])

    query += " ORDER BY s.student_id, e.semester, c.code"

    # 执行查询
    grades = conn.execute(query, params).fetchall()

    # 生成CSV内容
    import csv
    from io import StringIO
    from flask import Response

    # 创建一个内存中的文件对象
    output = StringIO()

    # 写入CSV数据
    if grades:
        # 获取列名
        fieldnames = [key for key in grades[0].keys()]
        writer = csv.DictWriter(output, fieldnames=fieldnames)

        # 写入表头
        writer.writeheader()

        # 写入数据行
        for grade in grades:
            writer.writerow({key: grade[key] for key in fieldnames})

    # 获取CSV内容
    csv_content = output.getvalue()
    output.close()
    conn.close()

    # 创建响应
    response = Response(
        csv_content,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=成绩导出_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        }
    )

    return response

# 头像上传路由
@app.route('/upload_avatar', methods=['POST'])
@csrf.exempt  # 豁免CSRF保护，因为这是文件上传
@login_required
def upload_avatar():
    try:
        if 'avatar' not in request.files:
            return jsonify({'success': False, 'message': '没有选择文件'})

        avatar = request.files['avatar']
        if avatar.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'})

        if avatar and allowed_file(avatar.filename):
            # 使用Flask内置的secure_filename确保文件名安全
            filename = secure_filename(avatar.filename)
            # 生成唯一文件名
            unique_filename = f"{session.get('username')}_{int(time.time())}_{filename}"

            # 构建文件路径
            avatar_path = f"uploads/avatars/{unique_filename}"
            full_path = os.path.join('static', avatar_path)

            # 保存文件
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                # 保存文件
                avatar.save(full_path)
                print(f"头像已保存到: {full_path}")

            except Exception as e:
                print(f"保存头像失败: {str(e)}")
                return jsonify({'success': False, 'message': f'保存文件失败: {str(e)}'})

            # 更新数据库
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
            except Exception as e:
                print(f"连接数据库失败: {str(e)}")
                return jsonify({'success': False, 'message': f'连接数据库失败: {str(e)}'})

            # 获取当前用户信息
            cursor.execute("SELECT * FROM users WHERE username = ?", (session.get('username'),))
            user = cursor.fetchone()

            if not user:
                conn.close()
                return jsonify({'success': False, 'message': '找不到用户记录'})

            # 尝试通过student_record_id查找学生记录
            student_record = None
            if user["student_record_id"]:
                cursor.execute("SELECT * FROM students WHERE id = ?", (user["student_record_id"],))
                student_record = cursor.fetchone()

            # 如果通过student_record_id找不到，尝试通过student_id查找
            if not student_record and user["student_id"]:
                cursor.execute("SELECT * FROM students WHERE student_id = ?", (user["student_id"],))
                student_record = cursor.fetchone()

                # 如果找到了学生记录，更新用户表中的student_record_id
                if student_record:
                    cursor.execute("UPDATE users SET student_record_id = ? WHERE id = ?", 
                                  (student_record["id"], user["id"]))
                    conn.commit()

            if student_record:
                # 更新头像路径
                try:
                    cursor.execute("UPDATE students SET avatar = ? WHERE id = ?", (avatar_path, student_record["id"]))
                    conn.commit()
                    print(f"已更新学生ID {student_record['id']} 的头像路径为: {avatar_path}")
                    conn.close()

                    return jsonify({'success': True, 'message': '头像上传成功', 'avatar_path': avatar_path})
                except Exception as e:
                    print(f"更新数据库失败: {str(e)}")
                    conn.close()
                    return jsonify({'success': False, 'message': f'更新数据库失败: {str(e)}'})
            else:
                print(f"找不到学生记录，用户名: {session.get('username')}")
                conn.close()
                return jsonify({'success': False, 'message': '找不到学生记录'})
        else:
            return jsonify({'success': False, 'message': '不支持的文件类型'})
    except Exception as e:
        print(f"上传头像过程中发生错误: {str(e)}")
        return jsonify({'success': False, 'message': f'上传头像过程中发生错误: {str(e)}'})

# 检查文件类型是否允许
def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 处理上传的头像文件的访问
@app.route('/uploads/avatars/<filename>')
def uploaded_avatar(filename):
    project_dir = os.path.dirname(os.path.abspath(__file__))
    upload_dir = os.path.join(project_dir, 'static', 'uploads', 'avatars')
    return send_from_directory(upload_dir, filename)

if __name__ == "__main__":
    init_db()  # 初始化数据库
    app.run(debug=True)
