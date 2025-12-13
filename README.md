# 学生信息管理系统 (PBL 项目)

## 项目简介

这是一个基于Flask框架和SQLite数据库开发的学生信息管理系统，作为PBL（项目式学习）项目的一部分。系统旨在为教育机构提供一个高效、便捷的学生信息管理平台，支持学生和管理员两种角色，提供不同的功能模块。

## 功能特点

### 学生功能
- **个人信息管理**：学生可以查看和修改自己的个人信息
- **课程浏览**：查看所有可选课程信息
- **选课管理**：进行选课、退课操作
- **成绩查询**：查看自己的课程成绩
- **系统导航**：清晰直观的导航界面，便于使用

### 管理员功能
- **用户管理**：管理系统中的所有用户账户
- **学生信息管理**：添加、修改、删除学生信息
- **课程管理**：添加、修改、删除课程信息
- **成绩管理**：录入、修改学生成绩
- **数据统计**：提供各类数据统计和分析功能

## 技术架构

- **后端框架**：Flask
- **前端框架**：Bootstrap 5
- **数据库**：SQLite
- **模板引擎**：Jinja2
- **其他技术**：HTML5, CSS3, JavaScript

## 系统要求

- Python 3.7+
- Flask 2.0+
- 现代浏览器（Chrome, Firefox, Safari, Edge等）

## 安装指南

1. 克隆项目到本地
   ```bash
   git clone https://github.com/yourusername/student-management-system.git
   cd student-management-system
   ```

2. 创建并激活虚拟环境
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows系统使用 venv\Scripts\activate
   ```

3. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

4. 初始化数据库
   ```bash
   flask db init
   flask db migrate -m "Initial migration"
   flask db upgrade
   ```

5. 运行应用
   ```bash
   python app.py
   ```

## 使用说明

### 学生登录
1. 访问系统首页
2. 使用学生账号和密码登录
3. 登录后可以访问个人信息、课程浏览、选课管理、成绩查询等功能

### 管理员登录
1. 访问系统首页
2. 使用管理员账号和密码登录
3. 登录后可以访问用户管理、学生信息管理、课程管理、成绩管理等功能

## 项目结构

```
student-management-system/
├── app.py                 # 主应用文件
├── config.py              # 配置文件
├── models/                # 数据模型
│   ├── __init__.py
│   ├── user.py           # 用户模型
│   ├── course.py         # 课程模型
│   └── grade.py          # 成绩模型
├── routes/                # 路由
│   ├── __init__.py
│   ├── auth.py           # 认证路由
│   ├── admin.py          # 管理员路由
│   └── student.py        # 学生路由
├── templates/             # 模板文件
│   ├── base.html         # 基础模板
│   ├── admin_base.html   # 管理员基础模板
│   ├── student_base.html # 学生基础模板
│   ├── auth/             # 认证相关模板
│   ├── admin/            # 管理员相关模板
│   └── student/          # 学生相关模板
├── static/               # 静态文件
│   ├── css/              # CSS文件
│   ├── js/               # JavaScript文件
│   └── images/           # 图片文件
├── requirements.txt       # 依赖列表
└── README.md             # 项目说明
```

## 开发团队

- [团队成员1] - 项目负责人
- [团队成员2] - 后端开发
- [团队成员3] - 前端开发
- [团队成员4] - 数据库设计

## 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 更新日志

### v1.0.0 (2023-XX-XX)
- 初始版本发布
- 实现基本的学生和管理员功能
- 完成系统界面设计

## 联系我们

如果您有任何问题或建议，请通过以下方式联系我们：

- 邮箱：contact@example.com
- 电话：123-456-7890
- 地址：XX省XX市XX区XX路XX号
