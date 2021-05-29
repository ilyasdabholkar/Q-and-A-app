import os
from sqlite3.dbapi2 import Cursor 
from flask import Flask, request, redirect ,flash
from flask.globals import g, session
from flask.templating import render_template
from flask import url_for
from DB import get_db
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def get_user():
    user_result=None
    if 'user' in session:
        loggeduser = session['user']
        db = get_db()
        cursor = db.execute("SELECT id,name,password,expert,admin from users where name=?", [loggeduser])
        user_result = cursor.fetchone()
    return user_result

@app.route('/')
def home():
    loggeduser = get_user()
    db = get_db()
    query = '''SELECT questions.id,questions.question_text,askers.name as asker_name,experts.name as expert_name 
                FROM questions JOIN users AS askers ON askers.id=questions.askedby_id 
                JOIN users AS experts ON experts.id = questions.expert_id 
                WHERE questions.answer_text IS NOT NULL'''
    cursor = db.execute(query)
    results = cursor.fetchall()
    return render_template('home.html',loggeduser=loggeduser,results=results)


@app.route('/register', methods=['GET', 'POST'])
def register():
    loggeduser = get_user()
    try:
        if request.method == 'POST':
            user = request.form['user']
            passwd = request.form['pass']
            hashed_password = generate_password_hash(passwd, method='sha256')

            db = get_db()
            db.execute("INSERT INTO users(name,password,expert,admin) VALUES(?,?,?,?)", [user, hashed_password, 0, 0])
            db.commit()
            db.close()
            return "<h1>User registered</h1>"
    except sqlite3.IntegrityError:
        flash(f"User {user} already exists,try a different username")
    return render_template('register.html',loggeduser=loggeduser)

@app.route('/login', methods=['GET', 'POST'])
def login():
    loggeduser = get_user()
    if request.method == 'POST':
        user = request.form['user']
        passwd = request.form['pass']

        db = get_db()
        resultset = db.execute("SELECT name,password from users where name=?", [user])
        output = resultset.fetchone()
        #output will be None if username does not exist in database
        if output:
            #this block will be executed if output is not None
            hashed_password = output['password']
            if(check_password_hash(hashed_password, passwd)):
                #create a user session of usrname value from database
                session['user'] = output['name']
                return redirect(url_for('home'))
            else:
                flash("Password did not match")
        else:
            flash("User not found")
    return render_template('login.html',loggeduser=loggeduser)


@app.route('/ask',methods=['GET','POST'])
def ask_question():
    loggeduser = get_user()
    if not loggeduser:
        return redirect(url_for('login'))
    if (loggeduser['admin']==1 or loggeduser['expert']==1):
        return redirect(url_for('home'))
    db = get_db()

    if request.method == "POST":
       question = request.form['question-box']
       expert_id = request.form['expert']
       askedby_id = loggeduser['id']
       db.execute("INSERT INTO questions(question_text,askedby_id,expert_id) VALUES(?,?,?)",[question,askedby_id,expert_id])
       db.commit()
       return redirect(url_for('home'))
    
    exp_cursor = db.execute("SELECT * FROM users WHERE expert = 1")
    expertusers = exp_cursor.fetchall()
    return render_template('askquestion.html',loggeduser=loggeduser,experts=expertusers)


@app.route('/answer/<question_id>',methods=['GET','POST'])
def answer_question(question_id):
    loggeduser = get_user()
    if not loggeduser:
        return redirect(url_for('login'))
    if loggeduser['expert']==0:
        return redirect(url_for('home'))

    db = get_db()
    cursor = db.execute("SELECT id,question_text FROM questions WHERE id=?",[question_id])
    question = cursor.fetchone()
    if request.method == 'POST':
        answer = request.form['answer'] 
        db.execute("UPDATE questions SET answer_text=? WHERE id=?",[answer,question_id])
        db.commit()
        return redirect(url_for('unanswered'))
    return render_template('answerquestion.html',loggeduser=loggeduser,question=question)


@app.route('/unanswered')
def unanswered():
    loggeduser = get_user()
    if not loggeduser:
        return redirect(url_for('login'))
    if loggeduser['expert']==0:
        return redirect(url_for('home'))

    db = get_db()
    cursor = db.execute('''SELECT questions.id,questions.question_text,users.name 
                FROM questions JOIN users ON users.id = questions.askedby_id 
                WHERE questions.answer_text IS NULL AND questions.expert_id=?''',[loggeduser['id']])
    questions = cursor.fetchall()
    return render_template('unanswered.html',loggeduser=loggeduser,questions=questions)

@app.route('/question/<que_id>')
def question(que_id):
    loggeduser = get_user()
    db = get_db()
    query = '''SELECT questions.askedby_id,questions.id,questions.question_text,questions.answer_text,askers.name AS asker_name,
                experts.name as expert_name,questions.expert_id as exp_id FROM questions 
                JOIN users AS askers ON askers.id=questions.askedby_id 
                JOIN users AS experts ON experts.id = questions.expert_id 
                WHERE questions.id=?'''
    cursor = db.execute(query,[que_id])
    question = cursor.fetchone()
    return render_template('question.html',loggeduser=loggeduser,question=question)

@app.route('/users')
def users():
    loggeduser = get_user()
    #protect routes 
    if not loggeduser:
        return redirect(url_for('login'))
    if loggeduser['admin']==0:
        return redirect(url_for('home'))

    db = get_db()
    cursor = db.execute("SELECT * FROM users")
    result = cursor.fetchall()
    return render_template('users.html',loggeduser=loggeduser,result=result)

@app.route('/askedquestions')
def askedquestions():
    loggeduser = get_user()
    db = get_db()
    if not loggeduser:
        return redirect(url_for('login'))
    if loggeduser['expert']==1 and loggeduser['admin']==0:
        return redirect(url_for('home'))

    if loggeduser['admin']==0 and loggeduser['expert']==0:
        cursor = db.execute("SELECT * FROM questions where askedby_id = ?",[loggeduser['id']])
        results = cursor.fetchall()
    elif loggeduser['admin']==1:
        query = '''SELECT questions.id,questions.question_text,askers.name as asker_name,experts.name as expert_name 
                FROM questions JOIN users AS askers ON askers.id=questions.askedby_id 
                JOIN users AS experts ON experts.id = questions.expert_id 
                '''
        cursor = db.execute(query)
        results = cursor.fetchall()
    return render_template('askedquestions.html',loggeduser=loggeduser,data=results)



@app.route('/update/<que_id>')
def update_answer(que_id):
    loggeduser = get_user()
    if not loggeduser:
        return redirect(url_for('login'))
    if loggeduser['expert']==0:
        return redirect(url_for('home'))
    
    db = get_db()
    cursor = db.execute("SELECT answer_text from questions Where id = ?",[que_id])
    question_text = cursor.fetchone();
    query = '''SELECT questions.id,questions.question_text,questions.answer_text,askers.name AS asker_name,
                experts.name as expert_name,questions.expert_id as exp_id FROM questions 
                JOIN users AS askers ON askers.id=questions.askedby_id 
                JOIN users AS experts ON experts.id = questions.expert_id 
                WHERE questions.id=?'''
    cursor_question = db.execute(query,[que_id])
    question = cursor_question.fetchone()
    return render_template('answerquestion.html',loggeduser=loggeduser,answer=question_text,question=question)

@app.route('/logout')
def logout():
    #set session user value to None and redirect to home
    session.pop('user',None)
    return redirect(url_for('home'))

@app.route('/promote/<userid>')
def promote(userid):
    loggeduser = get_user()
    if not loggeduser:
        return redirect(url_for('login'))
    if loggeduser['admin']==0:
        return redirect(url_for('home'))

    db = get_db()
    db.execute("UPDATE users SET expert=1 WHERE id=?",[userid])
    db.commit()
    return redirect('/users')

@app.route('/demote/<userid>')
def demote(userid):
    loggeduser = get_user()
    if not loggeduser:
        return redirect(url_for('login'))
    if loggeduser['admin']==0:
        return redirect(url_for('home'))

    db = get_db()
    db.execute("UPDATE users SET expert=0 WHERE id=?",[userid])
    db.commit()
    return redirect('/users')

@app.route('/deleteuser/<userid>')
def deleteuser(userid):
    loggeduser = get_user()
    if not loggeduser:
        return redirect(url_for('login'))
    if loggeduser['admin']==0:
        return redirect(url_for('home'))

    db = get_db()
    db.execute("DELETE FROM users WHERE id=?",[userid])
    db.commit()
    return redirect('/users')

@app.route('/deletequestion/<questionid>')
def deletequestion(questionid):
    loggeduser = get_user()

    db = get_db()
    cursor = db.execute("SELECT * FROM questions where id=?",[questionid])
    uid = cursor.fetchone()

    adminuser = False
    expertuser = False
    validuser = False 

    #only admin and user who asked the question is able to access this route
    if not loggeduser:
        return redirect(url_for('login'))
    if loggeduser['expert']==1 and loggeduser['admin']==0:
        expertuser = True
    if loggeduser['id'] == uid['askedby_id']:
        validuser = True
    if loggeduser['admin']==1:
        adminuser = True
    if expertuser==True:
        return redirect(url_for('home'))
    elif adminuser==True or validuser==True:
        db.execute("DELETE FROM questions WHERE id=?",[questionid])
        db.commit()
        return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True)
