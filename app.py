# os reads environment variables from the shell, keeping secrets
# (API keys, DB credentials) out of source code.
#
# RAM is volatile and SSD is not - this app runs in RAM for speed,
# but if the process terminates mid-execution, any unwritten state
# is lost. PostgreSQL, on the other hand, writes to disk and persists
# permanently, which is what actually guarantees data integrity here.

import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, session, redirect, url_for
from flask import jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from flask_session import Session
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from helpers import login_required
from rag import ask_rag

load_dotenv()

# Connecting PostgreSQL to SQLAlchemy is a three-step handoff:
# read the connection string, attach it to Flask's config, then let
# SQLAlchemy pull it back out to build the actual connection.

# Reads the DATABASE_URL set in the shell/.env (e.g.
# "postgresql://user:password@localhost:5432/driving_school").
database_address = os.environ.get('DATABASE_URL')

# Flask resolves templates/ and static/ relative to this file's
# location, which is why passing __name__ is enough for it to find
# them without an explicit path.
app = Flask(__name__)

# Attaches the connection string to Flask's config dict under the key
# SQLAlchemy expects, so SQLAlchemy can retrieve it when it initializes.
app.config['SQLALCHEMY_DATABASE_URI'] = database_address

# Debug check confirming the environment variable actually loaded.
print(f" TECHNICAL CHECK: The loaded database address is -> {database_address}")

# SQLAlchemy reads the URI back out of app.config and uses it to
# establish the actual connection to PostgreSQL.
db = SQLAlchemy(app)

from flask_migrate import Migrate
migrate = Migrate(app, db)

### Set up Session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

### Prevent caching
# Ensures every response tells the browser not to cache the page, so
# a logged-out user can't hit "back" and see a stale authenticated view.
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

#############################################################################################
#1 Instructors table blueprint
class Instructor(db.Model):
    __tablename__ = 'instructors'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

#2 Students table blueprint
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    dob = db.Column(db.Date)
    gender = db.Column(db.String(10))
    address = db.Column(db.Text)  # Text over String: no realistic upper bound on address length
    test_centre = db.Column(db.String(180))
    test_date = db.Column(db.Date)
    phone = db.Column(db.Integer, nullable=False)
    transmission = db.Column(db.String(10))
    hourly_rate = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    # instructor_id is nullable=False by design: unlike an optional FK
    # (e.g. a product's discount_id), a student without an instructor
    # isn't a valid record in this system.
    instructor_id = db.Column(db.Integer, db.ForeignKey('instructors.id'), nullable=False)

#3 Lessons table blueprint
class Lesson(db.Model):
    __tablename__ = 'lessons'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Float, nullable=False)
    payment_status = db.Column(db.String(20), default='Unpaid')
    notes = db.Column(db.Text)

    # Both foreign keys are required: a lesson without a student or
    # an instructor has no meaning in this schema.
    instructor_id = db.Column(db.Integer, db.ForeignKey('instructors.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)

    # backref gives Lesson objects a .student attribute and, in the
    # other direction, gives Student objects a .lessons attribute -
    # both generated from this one line, without writing a join by hand.
    student = db.relationship('Student', backref='lessons')
#########################################################################################

@app.route('/')
@login_required
def home():

    current_year = datetime.now().year
    current_month = datetime.now().month

    # Only this instructor's active students - filtering happens at
    # the query level, not after loading everything into Python.
    all_students = Student.query.filter_by(is_active=True, instructor_id=session['user_id']).all()

    # ==========================================================
    # Donut chart data: earnings aggregated per student
    # ==========================================================
    # Without GROUP BY, a student with 3 lessons produces 3 separate rows.
    # GROUP BY Student.id merges those into a single row per student,
    # which is what allows func.sum() to add up their earnings into one
    # total rather than three separate lesson amounts.
    #
    # .label('total_earnings') names the computed column. Without it:
    #   row[1]                  <- works, but breaks if columns are reordered
    # With it:
    #   row.total_earnings      <- still works even if columns are reordered
    #
    # This matters because the columns below are unlabeled positional
    # values (row[0] for name, row[1] for total), so this query is only
    # safe as long as nothing reorders them - the same risk applies to
    # any unlabeled, unordered query result, including the missing
    # order_by() on the lesson notes query in student_portfolio() further
    # down this file.

    donut_query = db.session.query(
        Student.name,
        func.sum(Lesson.duration * Student.hourly_rate).label('total_earnings')
    ).join(
        Student, Lesson.student_id == Student.id
    ).filter(
        Student.instructor_id == session['user_id'],
        func.extract('year', Lesson.date) == current_year,
        func.extract('month', Lesson.date) == current_month,
        Lesson.payment_status == 'Paid'  # only paid lessons count toward earnings
    ).group_by(
        Student.id
    ).all()

    # Splits the query result into the two flat lists script.js expects.
    current_month_students = [row[0] for row in donut_query]   # ['Judy', 'Tommy']
    current_month_earnings = [float(row[1]) for row in donut_query]  # [450.0, 200.0]

    # ==========================================================
    # Weekly outlook data
    # ==========================================================

    # Calculates this week's Monday-to-Sunday range.
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    week_range_str = f"{start_of_week.strftime('%Y-%m-%d')} to {end_of_week.strftime('%Y-%m-%d')}"

    # Pulls every lesson falling within that range.
    weekly_lessons = db.session.query(
        Lesson.date, Lesson.time, Student.name, Lesson.duration
    ).join(
        Student, Lesson.student_id == Student.id
    ).filter(
        Lesson.date >= start_of_week.date(), 
        Lesson.date <= end_of_week.date()
    ).order_by(Lesson.date, Lesson.time).all()

    # db.session.query() returns plain tuples, accessed by position:
    #   row[0] -> date, row[1] -> time, row[2] -> student, row[3] -> duration
    # If a column gets added or reordered later, every row[n] silently
    # points at the wrong value - no error, just wrong data downstream.
    #
    # The dict below converts each tuple into a named record instead:
    #   {'date': ..., 'time': ..., 'student': ..., 'duration': ...}
    # so the template reads lesson.date / lesson.student by name, and
    # stays correct even if the query's column order changes later.
    #
    # Lesson.query.all() sidesteps this problem entirely by returning
    # real Lesson objects with named attributes (lesson.date) directly -
    # it's used in place of db.session.query() in routes below wherever
    # no join or aggregation is needed.

    weekly_outlook = [
        {'date': row[0].strftime('%Y-%m-%d'), 'time': row[1].strftime('%H:%M'), 
         'student': row[2], 'duration': float(row[3])} for row in weekly_lessons
    ]

    return render_template('index.html', students=all_students, current_month_students=current_month_students, current_month_earnings=current_month_earnings, weekly_outlook=weekly_outlook, week_range_str=week_range_str)

@app.route('/addstudent', methods=['POST'])
@login_required
def student():
    # Reads the new-student form fields from the modal.
    input_name = request.form.get('student_name')
    input_address = request.form.get('address')
    input_phone = request.form.get('phone')
    input_dob = request.form.get('DOB')
    input_gender = request.form.get('gender')
    input_transmission = request.form.get('transmission')      
    input_hourlyrate = request.form.get('hourly_rate')
    input_testcentre = request.form.get('test_centre')
    input_testdate = request.form.get('test_date')

    # Builds a Student instance directly from the model - no raw SQL.
    new_student = Student(
        name=input_name,
        address=input_address, 
        phone=input_phone, 
        dob=input_dob, 
        gender=input_gender, 
        transmission=input_transmission,    
        hourly_rate=int(input_hourlyrate),
        test_centre=input_testcentre, 
        test_date=input_testdate,
        instructor_id=session["user_id"] 
    )

    # Stages the new row for insertion.
    db.session.add(new_student)

    # Commits the transaction, writing the row to PostgreSQL.
    db.session.commit()

    return redirect('/')

# <int:student_id> converts the URL segment to an integer before it
# reaches the function - necessary because URLs are always transmitted
# as plain text, regardless of the column's actual type in the database.
@app.route('/portfolio/<int:student_id>')
@login_required
def student_portfolio(student_id):
    # Stores the active student in the session so later routes
    # (add lesson, chat) know which student is in context without the
    # frontend having to pass the ID again on every request.
    session['current_student_id'] = student_id

    # .get_or_404() looks up by primary key and returns a 404
    # automatically if no matching row exists.
    current_student = Student.query.get_or_404(student_id)

    # Builds the target result (lesson rows plus a computed earnings
    # column) first, then joins and filters to produce it - the query
    # reads back-to-front relative to how the SQL actually executes.
    my_lessons = db.session.query(
        Lesson, (Lesson.duration * Student.hourly_rate).label('lesson_earnings')).join(Student).filter(Lesson.student_id == student_id).order_by(Lesson.id)
    
    return render_template('studentportfolio.html', student=current_student, lessons=my_lessons)

@app.route('/schedule')
@login_required
def time():
    return render_template('schedule.html')

@app.route('/addlesson', methods=['POST'])
@login_required
def lesson():

    # Reads the active student from the session rather than the form,
    # since the frontend never sends the ID explicitly.
    active_student_id = session.get('current_student_id')

    if not active_student_id:
        return jsonify({'success': False, 'message': 'Session expired'}), 401
    
    student = Student.query.get(active_student_id)
    if not student:
        return jsonify({'success': False, 'message': 'Student not found'}), 404
    
    input_date = request.form.get('date')
    input_time = request.form.get('time')
    input_duration = float(request.form.get('duration'))
    input_payment = request.form.get('payment_status')

    # Earnings are computed here rather than stored, so a later change
    # to a student's hourly rate never invalidates past records.
    hourly_rate = float(student.hourly_rate or 0)
    lesson_earnings = hourly_rate * input_duration

    new_lesson = Lesson (
        date=input_date,
        time=input_time,
        duration=input_duration,
        payment_status=input_payment,
        student_id=active_student_id,
        instructor_id=session['user_id']
    )

    db.session.add(new_lesson)
    db.session.commit()

    # Returns JSON instead of redirecting, so the frontend can insert
    # the new lesson row via AJAX without a full page reload.
    return jsonify({
        'success': True,
        'lesson': {
            'id': new_lesson.id,
            'date': str(new_lesson.date),
            'time': str(new_lesson.time),
            'duration': new_lesson.duration,
            'payment_status': new_lesson.payment_status,
            'earnings': lesson_earnings
        }
    })

# Auto-saves progress notes on blur (see script.js), so instructors
# never have to remember to click a separate save button.
@app.route('/update_spec', methods=['POST'])
@login_required
def update_spec():
    data = request.get_json()
    lesson = Lesson.query.get(data['id'])
    if lesson:
        lesson.notes = data['note']
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/finance')
@login_required
def finance():

    current_year = datetime.now().year
    current_month = datetime.now().month

    # ==========================================================
    # Finance table data: per-lesson detail, no aggregation
    # ==========================================================
    # Unlike the dashboard's donut chart, this view needs every
    # individual lesson for the month, not a per-student total -
    # so there's no group_by here.
    table_query = db.session.query(
        Lesson.date,
        Lesson.time,
        Student.name,
        Lesson.duration,
        (Lesson.duration * Student.hourly_rate).label('lesson_earnings'),
        Lesson.payment_status
    ).join(
        Student, Lesson.student_id == Student.id
    ).filter(
        func.extract('year', Lesson.date) == current_year,
        func.extract('month', Lesson.date) == current_month
    ).order_by(
        Lesson.date.desc(), Lesson.time.desc()  # most recent lesson first
    ).all()

    # Converted to dicts for the same reason as weekly_outlook above:
    # key-based access in the template survives a later column reorder.
    current_month_records = [
        {
            'date': row[0].strftime('%Y-%m-%d') if row[0] else '',
            'time': row[1].strftime('%H:%M:%S') if row[1] else '',
            'student_name': row[2],
            'duration': float(row[3]),
            'earnings': float(row[4]),
            'payment_status': row[5]
        } for row in table_query
    ]
    return render_template("finance.html", current_month_records=current_month_records)

@app.route('/remove_student', methods=['POST'])
@login_required
def remove_student():
    student_id = request.form.get('student_id')
    student = Student.query.get(student_id)
    if student:
        student.is_active = False
        db.session.commit()
    return redirect('/')

# POST-Redirect-GET: redirecting here instead of rendering a template
# directly means the browser's last active request becomes a GET,
# so refreshing the page after this route runs is always safe and
# never resubmits the form.

@app.route('/remove_lesson', methods=['POST'])
@login_required
def remove_lesson():

    data = request.get_json()

    lesson = Lesson.query.get(data['id'])

    if lesson:

        db.session.delete(lesson)
        db.session.commit()

        return jsonify({'success': True})

    return jsonify({'success': False}), 404

@app.route('/get_lessons')
@login_required
def get_lessons():
    lessons = Lesson.query.join(Student).all()
    event_list = []
    
    for l in lessons:
        # Combines date and time into a single datetime for FullCalendar.
        start_datetime = datetime.combine(l.date, l.time)

        # Converts duration in hours to minutes for the timedelta below.
        duration_minutes = int(l.duration * 60)
        
        end_datetime = start_datetime + timedelta(minutes=duration_minutes)
        
        event_list.append({
            "title": l.student.name,
            "start": start_datetime.isoformat(),
            "end": end_datetime.isoformat()
        })
    return jsonify(event_list)

@app.route('/chat', methods=["POST"])
@login_required
def chat():
    data = request.get_json()

    question = data.get("question")

    if not question:
        return jsonify({
            "error": "No question provided."
        }), 400


    active_student_id = session.get("current_student_id")

    if not active_student_id:
        return jsonify({
            "error": "No student selected."
        }), 400


    lessons = Lesson.query.filter_by(
        student_id=active_student_id
    ).all()


    answer = ask_rag(
        question,
        lessons
    )


    return jsonify({
        "answer": answer
    })

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Already logged in - skip the login page and go straight to home.
    if session.get("user_id"):
        return redirect("/")
    
    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        # Ensure username was submitted
        if not username:
            return "must provide username, 403"

        # Ensure password was submitted
        if not password:
            return "must provide password, 403"

        # .first() returns the matching Instructor row, or None if no
        # match exists - and stops scanning as soon as it finds one.
        user = Instructor.query.filter_by(username=username).first()

        # Covers both cases in one check: no such user, or a user that
        # exists but whose password hash doesn't match.
        if user is None or not check_password_hash(user.password_hash, password):
            return "invalid username and/or password, 403"

        # Remember which user has logged in
        session["user_id"] = user.id

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Already logged in - registering again isn't a valid action, so
    # redirect to home instead.
    if session.get("user_id"):
        return redirect("/")
    
    # Handles the form submission.
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Ensure user submits username
        if not username:
            return "must provide username, 400"

        # Ensure user submits password
        elif not password:
            return "must provide password, 400"

        # Ensure user submits confirmation password
        elif not confirmation:
            return "must provide confirmation password, 400"

        # Ensure user's password matches confirmation
        elif password != confirmation:
            return "password must match confirmation, 400"

        # Rejects the registration if the username is already taken.
        existing_user = Instructor.query.filter_by(username=username).first()
        if existing_user:
            return "username already taken, 400"

        # Creates the new instructor row with a hashed password -
        # the plaintext password is never stored.
        new_instructor = Instructor(
            username=username,
            password_hash=generate_password_hash(password)
        )
        
        db.session.add(new_instructor)
        db.session.commit()

        # Logs the new instructor in immediately after registration.
        session["user_id"] = new_instructor.id

        return redirect("/")

    # User reached route via GET
    else:
        return render_template("register.html")
    

with app.app_context():
    print("Creating tables...")
    db.create_all()
    print("Tables created!")