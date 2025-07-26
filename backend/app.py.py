from flask import Flask, render_template, request, redirect, url_for, session, make_response, render_template_string
import random
import mysql.connector
from questions import questions
import os
from io import BytesIO
from datetime import datetime
from xhtml2pdf import pisa

app = Flask(__name__)
app.secret_key = 'devops-exam-secret-key'  # Use hardcoded value for now

# ✅ Database connection using your local MariaDB setup
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='flaskuser',
        password='flaskpass',
        database='devops_exam'
    )

# ✅ Load certificate HTML template
def read_certificate_template():
    with open(os.path.join(os.path.dirname(__file__), 'certificate.html'), 'r') as file:
        return file.read()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start_exam():
    session['name'] = request.form['name']
    session['gender'] = request.form['gender']
    session['email'] = request.form['email']

    selected_questions = random.sample(questions, 15)
    for i, q in enumerate(selected_questions):
        q['index'] = i
    session['questions'] = selected_questions

    return render_template('exam.html', 
                           name=session['name'],
                           gender=session['gender'],
                           email=session['email'],
                           questions=selected_questions)

@app.route('/submit', methods=['POST'])
def submit_exam():
    try:
        questions_in_session = session.get('questions', [])
        for i in range(len(questions_in_session)):
            if f'question_{i}' not in request.form:
                return "Please answer all questions", 400

        db = get_db_connection()
        cursor = db.cursor()

        score = 0
        for i, q in enumerate(session['questions']):
            user_answer = request.form.get(f'question_{i}')
            if user_answer == q['answer']:
                score += 1

        cursor.execute(
            "INSERT INTO results (username, gender, email, score) VALUES (%s, %s, %s, %s)",
            (session['name'], session['gender'], session['email'], score)
        )
        db.commit()
        session['exam_score'] = score

        return render_template('result.html',
                               name=session.get('name'),
                               score=score,
                               total=len(questions_in_session))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error occurred while processing exam: {e}", 500
    finally:
        if 'db' in locals():
            db.close()

@app.route('/download_certificate')
def download_certificate():
    try:
        name = session.get('name', 'Exam Participant')
        score = session.get('exam_score', 0)

        template = read_certificate_template()
        rendered = render_template_string(template,
                                          name=name,
                                          score=score,
                                          date=datetime.now().strftime("%B %d, %Y"))

        pdf = BytesIO()
        pisa.CreatePDF(rendered, dest=pdf)
        pdf.seek(0)

        response = make_response(pdf.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=devops_certificate_{name.replace(" ", "_")}.pdf'
        return response
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Error generating certificate: {e}", 500

@app.route('/admin')
def admin_view():
    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT username, gender, email, score FROM results")
        records = cursor.fetchall()
        return render_template('admin.html', records=records)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Database error: {e}", 500
    finally:
        if 'db' in locals():
            db.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
