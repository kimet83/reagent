from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_session import Session
import pymysql
from werkzeug.security import generate_password_hash,check_password_hash
from host import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_CHARSET
from barcode2 import analyze_barcode
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from typing import Any, Dict
import os
import subprocess
# from flask_sqlalchemy import SQLAlchemy
# from db import db, User, In_reagent, Instrument, Ref_lib, Make_reagent
# from sqlalchemy.exc import SQLAlchemyError
# from sqlalchemy.orm import aliased

global user_info

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
# app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset={DB_CHARSET}'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['SQLALCHEMY_ECHO'] = True
Session(app)
# db.init_app(app)

backup_dir = os.path.join(os.getcwd(), "backup")
if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

def backup_schedule():
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=backup_database, trigger='interval', hours=24)
    scheduler.start()

def backup_database():
    # 현재 날짜를 계산하여 백업 파일명에 사용
    current_time = datetime.now().strftime("%y%m%d")
    backup_file = os.path.join(backup_dir, f"backup_{current_time}.sql")

    # mysqldump를 사용하여 데이터베이스 백업
    command = f"mysqldump -h {DB_HOST} -P {DB_PORT} -u {DB_USER} -p{DB_PASSWORD} --default-character-set={DB_CHARSET} {DB_NAME} > {backup_file}"
    subprocess.run(command, shell=True, check=True)

    # 백업 파일이 생성된 후, 지난 2달 간의 백업 파일을 보관하고 나머지는 삭제
    delete_old_backups()

def delete_old_backups():
    # 현재 날짜에서 2달 전 날짜 계산
    two_months_ago = datetime.now() - timedelta(days=60)

    # 현재 백업 디렉토리의 모든 파일 검색
    files = os.listdir(backup_dir)

    # 파일마다 반복하면서 백업 파일 여부 확인
    for file in files:
        if file.startswith("backup_"):
            # 파일명에서 날짜 부분 추출
            file_date = file.split("_")[1].split(".")[0]
            
            # 파일의 날짜와 2달 전 날짜 비교하여 삭제
            if datetime.strptime(file_date, "%y%m%d") < two_months_ago:
                os.remove(os.path.join(backup_dir, file))

# scheduler = BackgroundScheduler()
# scheduler.start()
backup_schedule()

app.static_url_path = '/static'
app.static_folder = 'static'

def template_exists(template_name):
    try:
        app.jinja_env.get_template(template_name)
        return True
    except Exception:
        return False

# def monthly_task():
#     # 매월 1일에 실행할 작업을 이곳에 추가하세요.
#     print("매월 1일에 실행되는 작업입니다.")
#     today = datetime.today()

#     # 지난달의 마지막 날을 계산합니다.
#     last_day_of_last_month = today - timedelta(days=today.day)

#     # 지난달의 첫째 날을 계산합니다.
#     first_day_of_last_month = last_day_of_last_month.replace(day=1)

#     # 첫째 날과 마지막 날을 원하는 형식으로 출력합니다.
#     start = first_day_of_last_month.strftime("%Y-%m-%d")
#     end = last_day_of_last_month.strftime("%Y-%m-%d")

#     print("지난달 첫째 날:", start)
#     print("지난달 마지막 날:", end)

# scheduler.add_job(monthly_task, 'cron', day='1', hour='0', minute='0')

#db 접속 함수
def create_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,  # MariaDB 포트 (기본값은 3306입니다)
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset=DB_CHARSET  # 사용할 문자셋
    )

def execute_query(connection, query, params=None):
    with connection.cursor(pymysql.cursors.DictCursor) as cursor: # type: ignore
        cursor.execute(query, params)
        return cursor.fetchall()

# 오늘날짜 전송
@app.route('/current_date', methods=["GET"])
def current_date():
    now = datetime.now()
    current_month_start = date.today().replace(day=1)
    return jsonify({
        'start': current_month_start.strftime('%Y-%m-%d'),
        'end': now.strftime('%Y-%m-%d')
    })

def format_date(date_string):
    try:
        year = "20" + date_string[:2]
        month = date_string[2:4]
        day = date_string[4:6]
        date = datetime.strptime(f"{year}-{month}-{day}", '%Y-%m-%d')
        return date.strftime("%Y-%m-%d")
    except ValueError:
        return None

# 장비 및 유저 리스트 전송
@app.route("/instrument_and_user_list", methods=["GET"])
def instrument_and_user_list():
    try:
        conn = create_connection()
        username=session['user_info']['username']
        sql='select distinct instrument from REF_LIB i'
        data = execute_query(conn,sql)
        sql='select username, name from user where username != %s and available = "1"'
        data2 = execute_query(conn,sql,username)
        conn.close()
        return jsonify({'instrument':data,'user':data2})
    except Exception as e:
        return jsonify({'error': str(e)})
# @app.route("/instrument_and_user_list", methods=["GET"])
# def instrument_and_user_list():
#     try:
#         username = session['user_info']['username']
#         instrument_data = []
#         other_user_data = []
#         instruments = db.session.query(Instrument.instrument).distinct().all()
#         # for instrument in instruments:
#         #     instrument_data = {'instrument': instrument.instrument}
#         instrument_data = [{'instrument': instrument.instrument} for instrument in instruments]
#         other_users = User.query.filter(User.username != username).with_entities(User.username, User.name).all()
#         other_user_data = [{
#             'username': other_user.username, 
#             'name': other_user.name
#             } for other_user in other_users]
#         print(instruments)
#         return jsonify({'instrument': instrument_data, 'user': other_user_data})
#     except SQLAlchemyError as e:
#         print("error",e)
#         return jsonify({'error': str(e)})
    

#로그인 시스템
# @app.route('/', methods=['GET','POST'])
# def home():
#     try:
#         users = User.query.all()
#         if request.method == 'POST':
#             username = request.form['username']
#             password = request.form['password']
#             for user in users:
#                 if user.username == username and user.password == password:
#                     user_info = {
#                         'username': user.username,
#                         'name': user.name
#                     }
#                     session['user_info'] = user_info
#                     return redirect(url_for('index'))  # 로그인 성공 시 대시보드 페이지로 이동
        
#         return render_template('login.html')
#     except SQLAlchemyError as e:
#         print("error",e)
#         return jsonify({'error': str(e)})
    
@app.route('/', methods=['GET','POST'])
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    try:
        conn = create_connection()
        username = request.form['username']
        password = request.form['password']
        sql = 'select * from user where username = %s and available = "1" limit 1'
        users = execute_query(conn,sql,username)
        print(users)
        conn.close()
        if users:  # users가 비어있지 않을 때만 실행
            hash_passwd = users[0]['password']  # type: ignore # users는 리스트이므로 첫 번째 요소의 'password'를 가져옴
            if check_password_hash(hash_passwd, password):
                user_info: Dict[str, Any] = users[0] # type: ignore
                del user_info['password']
                session['user_info'] = user_info
                print('pass')
                return redirect(url_for('index'))  # 로그인 성공 시 대시보드 페이지로 이동
            else:
                return jsonify({'error': '사용자 이름 또는 비밀번호가 잘못되었습니다.'}), 401
        else:
            return jsonify({'error': '사용자 이름 또는 비밀번호가 잘못되었습니다.'}), 401
    except Exception as e:
        return jsonify({'error': str(e)})
        
        # 로그인 실패 처리

# @app.route('/edit_user', methods=['POST'])
# def edit_user():
#     conn = create_connection()
#     master_sql = 'select * from user where username = "dev"'
#     master = execute_query(conn,master_sql)
#     master_pw = master[0]['password'] # type: ignore
#     username = request.form['username']
#     oldpassword = request.form['oldpassword']
#     password = request.form['newpassword']
#     name = request.form['name']
#     sql = 'select * from user where username = %s limit 1'
#     users= execute_query(conn,sql,username)
#     if users:
#         hash_passwd = users[0]['password'] # type: ignore
#         if check_password_hash(hash_passwd,oldpassword) or check_password_hash(master_pw,oldpassword):
#             hashed_password = generate_password_hash(password)
#             sql = 'update user set password = %s, name = %s, available = "1" where username = %s'
#             execute_query(conn,sql,(hashed_password,name,username))
#             conn.commit()
#             conn.close()
#             return jsonify({"success":True})
#         else: 
#             print('password incorrect')
#             conn.close()
#             return jsonify({'error': 'incorrect'})
#     else:
#         hashed_password = generate_password_hash(password)
#         sql = 'insert into user (username, name, password) values (%s,%s,%s)'
#         execute_query(conn,sql,(username,name,hashed_password))
#         conn.commit()
#         conn.close()
#         return jsonify({"success":True})

@app.route('/edit_user', methods=['POST'])
def edit_user():
    conn = create_connection()
    master_sql = 'select * from user where username = "dev"'
    master = execute_query(conn, master_sql)

    if master:
        master_pw = master[0]['password']  # type: ignore
    else:
        return jsonify({'error': 'Master user not found'}), 500

    username = request.form['username']
    oldpassword = request.form['oldpassword']
    password = request.form['newpassword']
    name = request.form['name']

    sql = 'select * from user where username = %s limit 1'
    users = execute_query(conn, sql, (username,))

    if users:
        hash_passwd = users[0]['password']  # type: ignore
        if check_password_hash(hash_passwd, oldpassword) or (master_pw and check_password_hash(master_pw, oldpassword)):
            hashed_password = generate_password_hash(password)
            if password:

                sql = 'update user set password = %s, name = %s, available = "1" where username = %s'
                execute_query(conn, sql, (hashed_password, name, username))
                conn.commit()
            else:
                sql = 'update user set name = %s, available = "1" where username = %s'
                execute_query(conn, sql, (name, username))
                conn.commit()
            conn.close()
            return jsonify({"success": True})
        else:
            print('password incorrect')
            conn.close()
            return jsonify({'error': 'incorrect'}), 401
    else:
        hashed_password = generate_password_hash(password)
        sql = 'insert into user (username, name, password) values (%s, %s, %s)'
        execute_query(conn, sql, (username, name, hashed_password))
        conn.commit()
        conn.close()
        return jsonify({"success": True})


@app.route('/delete_user', methods=['POST'])
def delete_user():
    conn = create_connection()
    master_sql = 'select * from user where username = "dev"'
    master = execute_query(conn, master_sql)

    if master:
        master_pw = master[0]['password']  # type: ignore
    else:
        return jsonify({'error': 'Master user not found'}), 500

    username = request.form['username']
    password = request.form['password']

    sql = 'select * from user where username = %s limit 1'
    users = execute_query(conn, sql, (username,))

    if users:
        hash_passwd = users[0]['password']  # type: ignore
        if check_password_hash(hash_passwd, password) or (master_pw and check_password_hash(master_pw, password)):
            hashed_password = generate_password_hash(password)
            sql = 'delete from user where username = %s'
            execute_query(conn,sql,username)
            conn.commit()
            conn.close()
            return jsonify({"success": True})
        else:
            print('password incorrect')
            conn.close()
            return jsonify({'error': 'incorrect'}), 401
    else:
        return jsonify({'error': 'incorrect'}), 401
    

@app.route('/user_list', methods=['GET'])
def user_list():
    conn = create_connection()
    sql = 'select * from user order by available desc'
    data = execute_query(conn,sql)
    conn.close()
    return jsonify({'result': data})

@app.route('/reg_user', methods=['POST'])
def reg_user():
    conn = create_connection()
    username = request.form['username']
    name = request.form['name']
    password = request.form['password']
    sql = 'select * from user where username = %s'
    data = execute_query(conn,sql,username)
    
    if not data:
        hashed_password = generate_password_hash(password)
        print(hashed_password)
        sql1 = 'insert into user (username, name, password) values (%s,%s,%s)'
        print(sql1,username,name,hashed_password)
        execute_query(conn,sql1,(username,name,hashed_password))
        print("1")
        conn.commit()
        conn.close()
        return jsonify({"success":True})
    else:
        print("2")
        conn.close()
        return jsonify({'error': 'user_exist'})

@app.route('/disable_user', methods=['POST'])
def disable_user():
    conn = create_connection()
    username = request.form['username']
    available= request.form['available']
    sql = 'update user set available = %s where username = %s'
    execute_query(conn,sql,(available,username))
    conn.commit()
    conn.close()
    return jsonify({"success":True})





    # hash_passwd = " " * 250 
    # hash_passwd = users['password'] # type: ignore
    # if check_password_hash(hash_passwd,password): # type: ignore
    #     user_info = users
    #     del user_info['password'] # type: ignore
    #     session['user_info'] = user_info
    #     print('pass')
    #     return redirect(url_for('index'))  # 로그인 성공 시 대시보드 페이지로 이동
    # if request.method == 'POST':
    #     username = request.form['username']
    #     password = request.form['password']
    #     for user in users:
    #         if user['username'] == username and check_password_hash(user['password'],password): # type: ignore
    #             user_info = user
    #             del user_info['password'] # type: ignore
    #             session['user_info'] = user_info
    #             print('pass')
    #             return redirect(url_for('index'))  # 로그인 성공 시 대시보드 페이지로 이동
    #         else:
    #             print('fail')
    #             return render_template('login.html')
    # else:
            
    #     return render_template('login.html')

# 로그아웃
@app.route('/logout', methods=['POST'])
def logout():
    # print(session)
    if 'user_info' in session:
        # 세션에서 사용자 정보 제거
        session.pop('user_info', None)
        # print(session)
    return redirect(url_for('home'))



# 사용자변경    
@app.route('/user_change', methods=['POST'])
def user_change():
    try:
        username = request.form['username']
        conn = create_connection()
        sql = 'select * from user where username = %s'
        users = execute_query(conn,sql,username)
        conn.close()
        user_info=users[0]
        del user_info['password'] # type: ignore
        session['user_info'] = user_info
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({'error': str(e)})
# @app.route('/user_change', methods=['POST'])
# def user_change():
#     try:
#         username = request.form['username']
#         user = User.query.filter_by(username=username).first()
#         if user:
#             user_info = {
#                 'username': user.username,
#                 'name': user.name
#             }
#             session['user_info'] = user_info
#             return jsonify({"success": True})
#         else:
#             return jsonify({"error": "User not found"})
#     except SQLAlchemyError as e:
#         print("error",e)
#         return jsonify({'error': str(e)})

# 각 파일 경로 링크
@app.route('/<path>')
def file_path(path):
    if 'user_info' in session:
        user_info = session['user_info']
        template_name = f'{path}.html'
        if template_exists(template_name):
            return render_template(template_name, user_info=user_info)
        else:
            return "템플릿이 존재하지 않습니다."
    else:
        return redirect(url_for('home'))


# 시약입고; index.html
# 로그인시 첫화면
@app.route('/index')
def index():
    # return render_template('index.html')

    if 'user_info' in session:
        user_info = session['user_info']
        # 여기에서 사용자 정보를 활용하여 페이지를 렌더링하거나 다른 작업을 수행할 수 있습니다.
        return render_template('index.html', user_info=user_info)
    else:
        return redirect(url_for('home'))  # 로그인되지 않은 경우 로그인 페이지로 리디렉션       

# 바코드 입력;index.html
@app.route("/in_reagent_barcode", methods=["POST"])
def in_reagent_barcode():
    try:
        conn = create_connection()
        barcode_receive = request.form['barcode_give']
        print(barcode_receive)
        ref, lot, exp, gtin = analyze_barcode(barcode_receive) #barcode analysis
        print(lot, exp, gtin)
        exp = format_date(exp)
        sql = 'select * from REF_LIB where gtin= %s limit 1' #등록 항목 확인 process
        data = execute_query(conn,sql,gtin)
        print(exp)
        conn.close()
        barcode = {'gtin':gtin,'lot': lot, 'exp': exp}
        return jsonify({'info':data,'barcode':barcode})
    except Exception as e:
        return jsonify({'error': str(e)})
# 시약 코멘트 확인;out_index.html js
@app.route('/comment', methods=["POST"])
def comment():
    try:
        conn = create_connection()
        id = request.form['id']
        sql = '''select ir.id,SUBSTRING(ir.date,1,10) as date, SUBSTRING(ir.out_date,1,10) as out_date, SUBSTRING(ir.close_date,1,10) as close_date,
        rl.name,ir.comment,
        ir.lot,
        SUBSTRING(ir.exp_date,1,10) as exp_date, rl.etc
        from in_reagent ir 
        left join REF_LIB rl on ir.gtin = rl.gtin 
        where ir.id=%s'''
        data=execute_query(conn,sql,id)
        conn.close()
        
        return jsonify({'result': data})
    except Exception as e:
        return jsonify({'error': str(e)})
# @app.route('/comment', methods=["POST"])
# def comment():
#     try:
#         id = request.form['id']
        
#         # 데이터베이스에서 코멘트 정보 조회
#         comment_info = In_reagent.query.with_entities(
#             In_reagent.id,
#             db.func.SUBSTRING(In_reagent.date, 1, 10).label('date'),
#             db.func.SUBSTRING(In_reagent.out_date, 1, 10).label('out_date'),
#             db.func.SUBSTRING(In_reagent.close_date, 1, 10).label('close_date'),
#             Ref_lib.name,
#             In_reagent.comment,
#             In_reagent.lot,
#             db.func.SUBSTRING(In_reagent.exp_date, 1, 10).label('exp_date'),
#             Ref_lib.etc
#         ).join(
#             Ref_lib, In_reagent.gtin == Ref_lib.gtin
#         ).filter(
#             In_reagent.id == id
#         ).all()
#         data = [{
#                 'id': row.id,
#                 'date': row.date[:10],
#                 'out_date': row.out_date[:10] if row.out_date else None,
#                 'close_date': row.close_date[:10] if row.close_date else None,
#                 'name': row.name,
#                 'comment': row.comment if row.comment else None,
#                 'lot': row.lot if row.lot else None,
#                 'exp_date': row.exp_date[:10] if row.exp_date else None,
#                 'etc': row.etc if row.etc else None
#         } for row in comment_info]
#         print("t")
#         print(data)
#         return jsonify({'result': data})
#     except SQLAlchemyError as e:
#         print("error",e)
#         return jsonify({'error': str(e)})

# 시약 코멘트 저장; out_index.html js
@app.route('/comment_save', methods=["POST"])
def comment_save():
    try:
        conn = create_connection()
        id = request.form['id']
        date = request.form['date']
        lot = request.form['lot']
        exp = request.form['exp']
        out_date = request.form['out_date']
        close_date = request.form['close_date']
        comment = request.form['comment']
        user_id  = request.form['user']
        sql = "select * from in_reagent where id = %s"
        data = execute_query(conn,sql,id)
        open_id = data[0]['open_id'] # type: ignore


        if comment =="" and out_date and close_date and open_id: # outdate, closedate, openid no commment
            sql = 'update in_reagent set comment = null, date = %s, lot = %s, exp_date = %s, out_date = %s, close_date = %s where id=%s'
            execute_query(conn,sql,(date,lot,exp,out_date,close_date,id))
        elif comment =="" and out_date and close_date and not open_id: #outdate, closedate, not openid no comment
            sql = 'update in_reagent set comment = null, date = %s, lot = %s, exp_date = %s, out_date = %s, close_date = %s, open_id = %s where id=%s'
            execute_query(conn,sql,(date,lot,exp,out_date,close_date,user_id,id))
        elif comment == "" and out_date and not close_date and open_id: # outdate, not closedate, openid no comment
            sql = 'update in_reagent set comment = null, date = %s, lot = %s, exp_date = %s, out_date = %s, close_date = NULL where id=%s'
            execute_query(conn,sql,(date,lot,exp,out_date,id))
        elif comment == "" and out_date and not close_date and not open_id: # outdate, not closedate, not openid no comment
            sql = 'update in_reagent set comment = null, date = %s, lot = %s, exp_date = %s, out_date = %s, close_date = NULL, open_id = %s where id=%s'
            execute_query(conn,sql,(date,lot,exp,out_date,user_id,id))
        elif comment == "" and not out_date : # not open no comment
            sql = 'update in_reagent set comment = null, date = %s, lot = %s, exp_date = %s, out_date = NULL, close_date = NULL, open_id = NULL where id=%s'
            execute_query(conn,sql,(date,lot,exp,id))
        elif comment and out_date and close_date and open_id: #outdate, closedate open_id
            sql = 'update in_reagent set comment = %s, date = %s, lot = %s, exp_date = %s, out_date = %s, close_date = %s where id=%s'
            execute_query(conn,sql,(comment,date,lot,exp,out_date,close_date,id))
        elif comment and out_date and close_date and not open_id: #outdate, closedate not open_id
            sql = 'update in_reagent set comment = %s, date = %s, lot = %s, exp_date = %s, out_date = %s, close_date = %s, open_id = %s where id=%s'
            execute_query(conn,sql,(comment,date,lot,exp,out_date,close_date,user_id,id))
        elif comment and out_date and not close_date and open_id: # not close openid
            sql = 'update in_reagent set comment = %s, date = %s, lot = %s, exp_date = %s, out_date = %s, close_date = NULL where id=%s'
            execute_query(conn,sql,(comment,date,lot,exp,out_date,id))
        elif comment and out_date and not close_date and not open_id: # not close not openid
            sql = 'update in_reagent set comment = %s, date = %s, lot = %s, exp_date = %s, out_date = %s, close_date = NULL, open_id = %s where id=%s'
            execute_query(conn,sql,(comment,date,lot,exp,out_date,user_id,id))
        elif comment and not out_date:
            sql = 'update in_reagent set comment = %s, date = %s, lot = %s, exp_date = %s, out_date = NULL, close_date = NULL, open_id = NULL where id=%s'
            execute_query(conn,sql,(comment,date,lot,exp,id))
        else:
            sql = 'update in_reagent set comment = %s, date = %s, lot = %s, exp_date = %s where id=%s'
            execute_query(conn,sql,(comment,date,lot,exp,id))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({'error': str(e)})
# @app.route('/comment_save', methods=["POST"])
# def comment_save():
#     try:
#         id = request.form['id']
#         date = request.form['date']
#         lot = request.form['lot']
#         exp = request.form['exp']
#         out_date = request.form['out_date']
#         close_date = request.form['close_date']
#         comment = request.form['comment']
#         user_id  = request.form['user']

#         in_reagent = In_reagent.query.filter_by(id=id).first()

#         if not in_reagent:
#             return jsonify({'error': 'InReagent with the given id not found'})

#         in_reagent.comment = comment or None
#         in_reagent.date = date
#         in_reagent.lot = lot
#         in_reagent.exp_date = exp

#         if out_date:
#             in_reagent.out_date = out_date
#         else:
#             in_reagent.out_date = None

#         if close_date:
#             in_reagent.close_date = close_date
#         else:
#             in_reagent.close_date = None

#         if user_id:
#             in_reagent.open_id = user_id
#         else:
#             in_reagent.open_id = None

#         db.session.commit()
        
#         return jsonify({"success": True})
#     except Exception as e:
#         return jsonify({'error': str(e)})
# 시약입고
@app.route("/save", methods=["POST"])
def save():
    try:
        conn = create_connection()
        date = request.form['date_give']
        gtin = request.form['gtin_give']
        exp = request.form['exp_give']
        lot = request.form['lot_give']
        ea =  int(request.form['ea_give'])
        name = request.form['name_give']
        instrument = request.form['instrument_give']
        code = request.form['code_give']
        temp_receive = request.form['temp_give']
        volume_receive = request.form['volume_give']
        unit_receive = request.form['unit']
        total_ea_receive = request.form['total_ea_give']
        onboard_receive = request.form['onboard_give']
        # ref = request.form['ref']
        username = request.form['username']
        comment = request.form['comment']
        name_short = request.form['name_short']
        make_onboard_day = request.form['make_onboard_day']
        etc = request.form['etc']
        # print("volume", volume_receive)
        print(exp)
        i = 0
        while i < ea: #ea 만큼 해당 시약을 입고
            if comment == "":
                sql = 'insert into in_reagent (date, gtin, exp_date, lot, in_id) values (%s, %s, %s, %s,%s)'
                execute_query(conn,sql,(date,gtin,exp,lot,username))
            else:

                sql = 'insert into in_reagent (date, gtin, exp_date, lot,in_id,comment) values (%s, %s, %s, %s,%s,%s)'
                execute_query(conn,sql,(date,gtin,exp,lot,username,comment))
            i += 1
            conn.commit()

        sql = 'select * from REF_LIB where gtin = %s limit 1' #라이브러리에 데이터 유무 확인
        data = execute_query(conn,sql,gtin)
        if not data: #데이터가 없을경우
            sql="INSERT  INTO REF_LIB (gtin, name, instrument, code, temp, volume, unit, total_ea, onboard,name_short,make_onboard_day,etc) VALUES (%s,%s,%s, %s, %s, %s, %s,%s,%s,%s,%s,%s) "
            execute_query(conn,sql,(gtin,name,instrument,code,temp_receive,volume_receive,unit_receive,total_ea_receive,onboard_receive,name_short,make_onboard_day,etc))
        else :
            sql='update REF_LIB set name = %s, instrument = %s, code = %s, temp = %s, volume = %s, unit = %s, total_ea = %s, onboard = %s, name_short = %s, make_onboard_day = %s, etc = %s where gtin = %s'
            execute_query(conn,sql,(name,instrument,code,temp_receive,volume_receive,unit_receive,total_ea_receive,onboard_receive,name_short,make_onboard_day,etc,gtin))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
            return jsonify({'error': str(e)})
    
# 시약 수기입고
@app.route("/in_reagent_manual", methods=["POST"])
def in_reagent_manual():
    try:
        conn = create_connection()
        date_receive = request.form['date_give']
        gtin_receive = request.form['gtin_give']
        exp_receive = request.form['exp_give']
        lot_receive = request.form['lot_give']
        ea_receive =  int(request.form['ea_give'])
        username = request.form['username']
        comment = request.form['comment']
        
        print(exp_receive)
        i = 0
        if comment == '':
            while i < ea_receive: #ea 만큼 해당 시약을 입고
                sql = 'insert into in_reagent (date, gtin, exp_date, lot,in_id) values (%s, %s, %s, %s,%s)'
                i += 1
                execute_query(conn,sql,(date_receive,gtin_receive,exp_receive,lot_receive,username))
                conn.commit()    
        else:
            while i < ea_receive: #ea 만큼 해당 시약을 입고
                sql = 'insert into in_reagent (date, gtin, exp_date, lot,in_id,comment) values (%s, %s, %s, %s,%s,%s)'
                i += 1
                execute_query(conn,sql,(date_receive,gtin_receive,exp_receive,lot_receive,username,comment))
                conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({'error': str(e)})

# 출고바코드입력
@app.route("/out_barcode", methods=["POST"])
def out_barcode():
    try:
        conn = create_connection()
        out_date = request.form['date_give']
        barcode_receive = request.form['barcode_give']
        username=request.form['username']
        ea = int(request.form['ea'])

        # 바코드 출고 및 수동 출고 처리 프로세스
        if barcode_receive=='0':
            # gtin = request.form['gtin']
            lot = request.form['lot']
            name =request.form['name']
            sql = 'select ir.gtin from in_reagent ir left join REF_LIB rl on ir.gtin=rl.gtin where name=%s and lot=%s limit 1'
            data = execute_query(conn,sql,(name,lot))
            gtin = data[0]['gtin'] # type: ignore
            print(lot,name,gtin,username)
        else:
        # type_receive = request.form['type_give']
            ref, lot, exp, gtin = analyze_barcode(barcode_receive) #barcode analysis
            sql = 'select name from REF_LIB where gtin = %s'
            data = execute_query(conn,sql,gtin)
            name = data[0]['name'] # type: ignore
            print(lot,name,gtin)
        
        # print(ref, lot, exp, gtin)
        sql = 'select total_ea, onboard from REF_LIB where name= %s limit 1' # 해당시약의 포장단위를 조회
        data = execute_query(conn,sql,name)
        data = data[0]
        # print(data)
        #박스 당 단위 확인
        total_ea = data['total_ea'] # type: ignore
        #장비 장착 한도 확인
        onboard = data['onboard'] # type: ignore
        
        for i in range(ea):
            #장비 장착중 시약 개수 확인 onboarding
            sql = '''
                select count(*) as onboarding from in_reagent ir 
                left join REF_LIB rl on ir.gtin = rl.gtin 
                where rl.name = %s and out_date is not NULL and close_date is NULL 
                group by rl.name limit 1
                ''' #out_date is not NULL and close_date is NULL = Opened reagent
            data = execute_query(conn,sql,name)
            if not data: #Opened reagent is NULL
                onboarding = 0
            else:
                data = data[0]
                onboarding = data['onboarding']  # type: ignore
            print(total_ea,onboard,onboarding)
            sql = '''
                select quantity from in_reagent ir
                left join REF_LIB rl on ir.gtin = rl.gtin
                where rl.name = %s and out_date is not NULL and close_date is NULL 
                and total_ea >1 and quantity != total_ea
                order by date
                limit 1'''
            data = execute_query(conn,sql,name)
            
            if not data:
                quantity = total_ea
                print(total_ea,onboard,onboarding,quantity)
            else:
                quantity = int(data[0]['quantity']) # type: ignore
                print(total_ea,onboard,onboarding,quantity)
        # 시약이 오픈된 시약이 한도보다 적을경우(1), 시약이 오픈된 시약이 한도와 같은 경우(2)
        # 시약 오픈시 out_date만 기입, 추가오픈시 quantity +
        # quantity = total_ea, close_date 기입
            if onboarding == onboard and quantity < total_ea: #장착 최소한도보다 개봉 시약이 같고 오픈시약의 잔여가 있을 경우
                quantity = quantity+1
                sql = '''
                    update in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin set quantity = %s 
                    where name = %s and out_date is not NULL and close_date is NULL order by date limit 1'''
                execute_query(conn,sql,(quantity,name))
                conn.commit()

            elif onboarding == onboard and quantity == total_ea:
                sql = '''update in_reagent ir
                    left join REF_LIB rl on ir.gtin=rl.gtin 
                    set close_date = %s, quantity= %s 
                    where name = %s  and out_date is not NULL and close_date is NULL 
                    order by date limit 1''' #기존 오픈된 시약 중 오픈일 기입된 시약을 종료일 입력
                execute_query(conn,sql,(out_date,total_ea,name))
                conn.commit()
                sql = '''update in_reagent ir 
                    left join REF_LIB rl on ir.gtin=rl.gtin
                    set out_date = %s, open_id = %s,quantity = 1 
                    where name= %s and lot = %s and out_date is NULL 
                    order by date limit 1''' #오픈되지 않은 시약을 한개 찾아 오픈일만 기입 process 1
                execute_query(conn,sql,(out_date, username, name, lot))
                conn.commit()
                print("1-1")
            else:
                sql = '''update in_reagent ir 
                    left join REF_LIB rl on ir.gtin=rl.gtin 
                    set out_date = %s, open_id = %s, quantity= 1 
                    where name= %s and lot = %s  and out_date is NULL 
                    order by date limit 1''' #오픈되지 않은 시약을 한개 찾아 오픈일만 기입 process 1
                execute_query(conn,sql,(out_date, username, name, lot))
                conn.commit()
                print("1-2")

        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route("/make", methods=["POST"])
def make():
    try:
        conn = create_connection()
        ea = int(request.form['ea'])
        # reagent_id = request.form['id']
        # reagent_quantity = int(request.form['reagent_quantity'])
        make_date = request.form['make_date']
        name = request.form['name']
        lot = request.form['lot']
        exp_date = request.form['exp_date']
        remain = int(request.form['remain'])
        total_ea = int(request.form['total_ea'])
        quantity = int(request.form['quantity'])
        make_onboard_date = request.form['make_onboard_date']
        make_user = request.form['make_user']
        in_date = request.form['in_date']
        instrument = request.form['instrument']
        print(instrument,make_date, name, lot, exp_date, in_date, remain, total_ea, make_onboard_date, make_user)
        
        for i in range(ea):
            sql = 'select total_ea, onboard from REF_LIB where name= %s limit 1' # 해당시약의 포장단위를 조회
            data = execute_query(conn,sql,name)
            data = data[0]
            # print(data)
            #박스 당 단위 확인
            # total_ea = data['total_ea'] # type: ignore
            #장비 장착 한도 확인
            onboard = data['onboard'] # type: ignore
            print(onboard)
            #장비 장착중 시약 개수 확인 onboarding
            sql = '''
                select count(*) as onboarding from make_reagent mr 
                left join (select ir.id,rl.name, ir.out_date, ir.close_date from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where ir.out_date is not null and ir.close_date is null) ir2 on ir2.id = mr.reagent_id 
                where mr.name = %s and mr.date is not NULL and mr.close_date is NULL
                group by mr.name
                ''' #out_date is not NULL and close_date is NULL = Opened reagent
            data = execute_query(conn,sql,name)
            if not data: #Opened reagent is NULL
                onboarding = 0
            else:
                data = data[0]
                onboarding = data['onboarding']  # type: ignore
            
            #해당 시약 아이디 검색
            print("onboarding",onboarding)
            reagent_id_search="""
                select id, name, lot, quantity, SUBSTRING(ir.date,1,10) as date,SUBSTRING(ir.out_date,1,10) as out_date from in_reagent ir 
                left join REF_LIB rl on ir.gtin = rl.gtin
                where name = %s and lot = %s and close_date is null and quantity = %s order by date, CASE WHEN out_date IS NULL THEN 1 ELSE 0 END, out_date, quantity desc limit 1
            #     """
            reagent_id_search_data = execute_query(conn,reagent_id_search,(name,lot,quantity))
            print(name,lot,in_date,reagent_id_search_data)
            # reagent_id_search_data = reagent_id_search_data[0]
            reagent_id = reagent_id_search_data[0]['id'] # type: ignore
            # quantity = int(reagent_id_search_data[0]['quantity'])  # type: ignore
            make_quantity = quantity+1
            # out_date = reagent_id_search_date[0]['out_date']
            # make_reagent 테이블 입력

            if make_quantity==1 and onboarding == onboard:
                print("type1")
                #close reagent
                reagent_close_search = '''
                    select id from in_reagent ir left join REF_LIB rl on ir.gtin=rl.gtin where rl.name = %s and ir.quantity = rl.total_ea and ir.close_date is null limit 1
                    '''
                data = execute_query(conn,reagent_close_search,name)
                data = data[0]['id'] # type: ignore
                reagent_close="""
                    update in_reagent set close_date = %s where id = %s
                    """
                execute_query(conn,reagent_close,(make_date, data))
                conn.commit()

                #maked vial close
                maked_reagent_close="""
                update make_reagent mr set close_date = %s where name = %s and reagent_id = %s and date is not null and close_date is null order by date limit 1
                """
                execute_query(conn,maked_reagent_close,(make_date,name,data))
                conn.commit()
                #make vial
                make_reagent_update_sql = '''
                INSERT  INTO make_reagent (reagent_id, name, date, lot, exp_date, make_onboard_date, make_user, in_date,quantity) VALUES (%s,%s,%s, %s, %s, %s, %s,%s,%s)
                '''
                execute_query(conn,make_reagent_update_sql,(reagent_id,name,make_date,lot,exp_date,make_onboard_date,make_user,in_date,make_quantity))
                conn.commit()

                #reagent open
                in_reagent_update = '''
                    update in_reagent ir set out_date = %s, quantity =%s, open_id=%s where id=%s and out_date is null
                    '''
                execute_query(conn,in_reagent_update,(make_date,make_quantity,make_user,reagent_id))
                conn.commit()

            elif make_quantity !=1 and onboard == onboarding:
                print("type2")
                #maked vial close
                maked_reagent_close="""
                update make_reagent mr set close_date = %s where name = %s and date is not null and close_date is null order by date limit 1
                """
                execute_query(conn,maked_reagent_close,(make_date,name))
                conn.commit()
                #make vial
                make_reagent_update_sql = '''
                INSERT  INTO make_reagent (reagent_id, name, date, lot, exp_date, make_onboard_date, make_user, in_date,quantity) VALUES (%s,%s,%s, %s, %s, %s, %s,%s,%s)
                '''
                execute_query(conn,make_reagent_update_sql,(reagent_id,name,make_date,lot,exp_date,make_onboard_date,make_user,in_date,make_quantity))
                conn.commit()
                in_reagent_update = '''
                    update in_reagent ir set quantity =%s where id=%s
                    '''
                execute_query(conn,in_reagent_update,(make_quantity,reagent_id))
                conn.commit()
            
            elif make_quantity ==1 and onboard!=onboarding:
                print("type3")
                make_reagent_update_sql = '''
                INSERT  INTO make_reagent (reagent_id, name, date, lot, exp_date, make_onboard_date, make_user, in_date,quantity) VALUES (%s,%s,%s, %s, %s, %s, %s,%s,%s)
                '''
                execute_query(conn,make_reagent_update_sql,(reagent_id,name,make_date,lot,exp_date,make_onboard_date,make_user,in_date,make_quantity))
                conn.commit()

                #reagent open
                in_reagent_update = '''
                    update in_reagent ir set out_date = %s, quantity =%s, open_id=%s where id=%s and out_date is null
                    '''
                execute_query(conn,in_reagent_update,(make_date,make_quantity,make_user,reagent_id))
                conn.commit()

            elif make_quantity != 1 and onboard!=onboarding  :
                print("type4")
                make_reagent_update_sql = '''
                INSERT  INTO make_reagent (reagent_id, name, date, lot, exp_date, make_onboard_date, make_user, in_date,quantity) VALUES (%s,%s,%s, %s, %s, %s, %s,%s,%s)
                '''
                execute_query(conn,make_reagent_update_sql,(reagent_id,name,make_date,lot,exp_date,make_onboard_date,make_user,in_date,make_quantity))
                conn.commit()
                #reagent open
                in_reagent_update = '''
                    update in_reagent ir set out_date = %s, quantity =%s, open_id=%s where id=%s and out_date is null
                    '''
                execute_query(conn,in_reagent_update,(make_date,make_quantity,make_user,reagent_id))
                conn.commit()
            else:
                print(reagent_id)
        conn.close()
        

        return jsonify({'msg': '제조시약 추가완료!'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route("/edit_maked_order", methods=["POST"])
def edit_maked_order():
    try:
        conn = create_connection()
        id = request.form['id']
        search_edit_maked_order= '''
            SELECT mr.id, SUBSTRING(mr.in_date,1,10) as in_date, SUBSTRING(ir.out_date,1,10) as out_date, mr.name, SUBSTRING(mr.date,1,10) as date, mr.lot, SUBSTRING(mr.exp_date,1,10) as exp, SUBSTRING(mr.make_onboard_date,1,10) as make_onboard_date, SUBSTRING(mr.close_date,1,10) as close_date, SUBSTRING(ir.close_date,1,10) as reagent_close_date, mr.reagent_id, mr.quantity as make_quantity, rl.total_ea, ir.quantity as reagent_quantity, mr.comment, ir.comment as reagent_comment, rl.make_onboard_day
            from  make_reagent mr
            left join in_reagent ir on mr.reagent_id = ir.id 
            left join REF_LIB rl on mr.name = rl.name
            where mr.id = %s
        '''
        data = execute_query(conn,search_edit_maked_order,id)
        conn.close()
        return jsonify({'result': data})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route("/edit_maked_save", methods=["POST"])
def edit_maked_save():
    try:
        conn = create_connection()
        id = request.form["id"]
        reagent_id = request.form["reagent_id"]
        in_date = request.form["in_date"]
        name = request.form["name"]
        out_date = request.form["out_date"]
        make_date = request.form["date"]
        lot =  request.form["lot"]
        exp = request.form["exp"]
        make_onboard_date = request.form["make_onboard_date"]
        close_date = request.form["close_date"]
        reagent_close_date = request.form["reagent_close_date"]
        total_ea = int(request.form["total_ea"])
        quantity = int(request.form["quantity"])
        reagent_quantity = int(request.form["reagent_quantity"])
        comment = request.form["comment"]
        reagent_comment = request.form["reagent_comment"]
        print(id,reagent_id, in_date, name, out_date, make_date, lot, exp, make_onboard_date, close_date, total_ea, quantity, reagent_quantity, comment, reagent_comment)

        #make_reagent edit
        if close_date:
            make_reagent_query = '''
                update make_reagent set date=%s, make_onboard_date=%s, close_date=%s, quantity=%s,comment=%s where id = %s
            '''
            execute_query(conn, make_reagent_query,(make_date,make_onboard_date,close_date,quantity, comment, id))
        else:
            make_reagent_query = '''
                update make_reagent set date=%s, make_onboard_date=%s, quantity=%s,comment=%s, close_date = null where id = %s
            '''
            execute_query(conn, make_reagent_query,(make_date,make_onboard_date,quantity, comment, id))
        conn.commit()
        make_reagent_query2 = '''
            update make_reagent set in_date=%s, lot=%s, exp_date=%s where reagent_id = %s
        '''
        execute_query(conn,make_reagent_query2,(in_date,lot,exp,reagent_id))
        conn.commit()
        if reagent_close_date:
            in_reagent_query = '''
                update in_reagent set date=%s, lot=%s, exp_date=%s, out_date=%s, close_date=%s, comment=%s,quantity=%s where id = %s
            '''
            execute_query(conn,in_reagent_query,(in_date,lot,exp,out_date,reagent_close_date,reagent_comment,reagent_quantity,reagent_id))
        else:
            in_reagent_query = '''
                update in_reagent set date=%s, lot=%s, exp_date=%s, out_date=%s, close_date = null, comment=%s, quantity=%s where id = %s
            '''
            execute_query(conn,in_reagent_query,(in_date,lot,exp,out_date,reagent_comment,reagent_quantity,reagent_id))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({'error': str(e)})


# 시약vial 오픈
@app.route("/add", methods=["POST"])
def add_post():
    try:
        conn = create_connection()
        reagent_id = request.form['id']
        out_date = request.form['out_date']
        make_user = request.form['user']
        reagent_search='''
            select * from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where id = %s
            '''
        data = execute_query(conn,reagent_search,reagent_id)
        name = data[0]['name'] # type: ignore
        in_date = data[0]['date'] # type: ignore
        exp_date = data[0]['exp_date'] # type: ignore
        lot = data[0]['lot'] # type: ignore
        make_reagent_update_sql = '''
                INSERT  INTO make_reagent (reagent_id, name, date, lot, exp_date, make_onboard_date, make_user, in_date,quantity) VALUES (%s,%s,%s, %s, %s, %s, %s,%s,%s)
                '''
        execute_query(conn,make_reagent_update_sql,(reagent_id,name,out_date,lot,exp_date,"2099-12-31",make_user,in_date,"0"))
        conn.commit()
        conn.close()    
        return jsonify({'msg': '삭제 완료!'})
    except Exception as e:
        return jsonify({'error': str(e)})


# @app.route("/add", methods=["POST"])
# def add_post():
#     conn = create_connection()
#     id = request.form['id']
#     out_date = request.form['out_date']
#     sql= '''
#         select quantity, total_ea from in_reagent ir 
#         left join REF_LIB rl on ir.gtin = rl.gtin 
#         where ir.id= %s limit 1
#         '''
#     data = execute_query(conn,sql,id)
#     data=data[0]
#     # print(data)
#     quantity = data['quantity'] # type: ignore
#     total_ea = data['total_ea'] # type: ignore
    
#     if quantity < total_ea:
#         quantity = quantity + 1
#         sql = 'UPDATE in_reagent set quantity= %s WHERE id= %s'
#         execute_query(conn,sql,(quantity,id))
#         conn.commit()
#     else:
#         sql = 'UPDATE in_reagent set close_date = %s where id = %s'
#         execute_query(conn,sql,(out_date,id))
#         conn.commit()
#     conn.close()    
#     return jsonify({'msg': '삭제 완료!'})

# 출고 취소 및 vial 오픈 취소
@app.route("/cancel", methods=["POST"])
def cancel_post():
    try:
        conn = create_connection()
        id = request.form['id']
        sql= '''
            select quantity,total_ea,close_date,out_date from in_reagent ir 
            left join REF_LIB rl on ir.gtin = rl.gtin 
            where id= %s limit 1
            '''
        data = execute_query(conn,sql,id)
        data=data[0]
        # print(data)
        quantity = int(data['quantity']) # type: ignore
        total_ea = int(data['total_ea']) # type: ignore
        close_date = data['close_date'] # type: ignore
        # out_date = data['out_date']
        if close_date:
            sql = '''
                Update in_reagent set close_date = NULL where id = %s'''
            execute_query(conn,sql,id)
            conn.commit()
            print("1")
        elif not close_date and total_ea >= quantity and quantity > 1 and total_ea != 1:
            quantity = quantity - 1
            sql = 'UPDATE in_reagent set quantity= %s WHERE id= %s'
            execute_query(conn,sql,(quantity,id))
            conn.commit()
            print("2")
        elif not close_date and total_ea >= quantity and quantity > 1 and total_ea == 1:
            sql = 'UPDATE in_reagent set quantity=0, out_date = NULL, open_id = NULL WHERE id= %s'
            execute_query(conn,sql,id)
            conn.commit()
            print("3")
        
        else:
            sql = 'UPDATE in_reagent set quantity=0, out_date = NULL, open_id = NULL WHERE id= %s'
            execute_query(conn,sql,id)
            conn.commit()
            print("3-1")
        conn.close()
        return jsonify({'msg': '삭제 완료!'})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route("/make_cancel_order", methods=["POST"])
def make_cancel_order():
    conn = create_connection()
    id = request.form['id']
    make_reagent_info='''
        select * from make_reagent where id = %s
        '''
    make_reagent_info_data = execute_query(conn,make_reagent_info,id)
    reagent_id = make_reagent_info_data[0]['reagent_id'] # type: ignore
    quantity = make_reagent_info_data[0]['quantity'] # type: ignore
    close_date = make_reagent_info_data[0]['close_date'] # type: ignore
    in_reagent_info = '''
        select * from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin
        where ir.id = %s
        '''
    in_reagent_info_data = execute_query(conn,in_reagent_info,reagent_id)
    reagent_quantity = in_reagent_info_data[0]['quantity'] # type: ignore
    total_ea = in_reagent_info_data[0]['total_ea'] # type: ignore
    reagent_close_date =  in_reagent_info_data[0]['close_date'] # type: ignore
    in_reagent_info2 = '''
        select * from make_reagent where reagent_id = %s and quantity = %s limit 1 offset 1
        '''
    in_reagent_info_data2 = execute_query(conn,in_reagent_info2,(reagent_id,quantity))
    
    print(in_reagent_info_data2)
    if quantity == reagent_quantity and close_date and not in_reagent_info_data2:
        make_reagent_sql = '''
            update make_reagent set close_date = null where id=%s
        '''
        execute_query(conn,make_reagent_sql,id)
        conn.commit()
        in_reagent_sql = '''
            update in_reagent set close_date = null where id=%s
        '''
        execute_query(conn,in_reagent_sql,reagent_id)
        conn.commit()
        print("1")
    elif quantity == reagent_quantity != 1 and not close_date and not in_reagent_info_data2:
        reagent_quantity = reagent_quantity-1
        make_reagent_sql = '''
            delete from make_reagent where id =%s
        '''
        execute_query(conn,make_reagent_sql,id)
        conn.commit()
        in_reagent_sql = '''
            update in_reagent set quantity = %s where id=%s
        '''
        execute_query(conn,in_reagent_sql,(reagent_quantity,reagent_id))
        conn.commit()
        print("2")

    elif quantity == reagent_quantity == 1 and not close_date and not in_reagent_info_data2:
        reagent_quantity = reagent_quantity-1
        make_reagent_sql = '''
            delete from make_reagent where id =%s
        '''
        execute_query(conn,make_reagent_sql,id)
        conn.commit()
        in_reagent_sql = '''
            update in_reagent set quantity = %s, open_id = null, out_date = null where id=%s
        '''
        execute_query(conn,in_reagent_sql,(reagent_quantity,reagent_id))
        conn.commit()
        print("3")
    
    else:
        make_reagent_sql = '''
            delete from make_reagent where id =%s
        '''
        execute_query(conn,make_reagent_sql,id)
        conn.commit()
        print("4")
    conn.close()
    return jsonify({'msg': '완료!'})

@app.route("/make_close_order", methods=["POST"])
def make_close_order():
    conn = create_connection()
    id = request.form['id']
    date = request.form['date']
    make_reagent_info='''
        select * from make_reagent where id = %s
        '''
    make_reagent_info_data = execute_query(conn,make_reagent_info,id)
    reagent_id = make_reagent_info_data[0]['reagent_id'] # type: ignore
    quantity = make_reagent_info_data[0]['quantity'] # type: ignore
    close_date = make_reagent_info_data[0]['close_date'] # type: ignore
    in_reagent_info = '''
        select * from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin
        where ir.id = %s
        '''
    in_reagent_info_data = execute_query(conn,in_reagent_info,reagent_id)
    reagent_quantity = in_reagent_info_data[0]['quantity'] # type: ignore
    total_ea = in_reagent_info_data[0]['total_ea'] # type: ignore
    reagent_close_date =  in_reagent_info_data[0]['close_date'] # type: ignore
    make_close_order_query = '''
        update make_reagent set close_date=%s where id=%s
        '''
    execute_query(conn,make_close_order_query,(date,id))
    conn.commit()

    if quantity == reagent_quantity==total_ea:
        in_reagent_query = '''
            update in_reagent  set close_date=%s where id=%s
        '''
        execute_query(conn,in_reagent_query,(date,reagent_id))
        conn.commit()
        conn.close()
    else:
        conn.close()

    return jsonify({'msg': '완료!'})
    
@app.route("/search_maked_reagent_list", methods=["POST"])
def search_maked_reagent_list():
    conn = create_connection()
    start = request.form['start']
    end = request.form['end']
    code = request.form['code']
    instrument = request.form['instrument']
    reagent = request.form['reagent']
    warning = request.form['warning']
    print('test1')
    sql = '''
            SELECT mr.id,mr.reagent_id, SUBSTRING(mr.in_date,1,10) as in_date,SUBSTRING(mr.date,1,10) as make_date, mr.name, mr.lot, SUBSTRING(mr.exp_date,1,10) as exp, substring(mr.make_onboard_date,1,10) as make_onboard_date,
            ir2.code, SUBSTRING(mr.close_date,1,10) as close_date, mr.quantity, ir2.instrument, ir2.total_ea,ir2.quantity as ir_quantity,
            ir2.temp, CASE WHEN mr.exp_date < CURDATE() THEN "expired" ELSE "usable" END AS status, 
            CASE WHEN mr.date is not NULL AND mr.close_date is NULL THEN "using" 
            WHEN mr.date is NULL THEN "not open" 
            WHEN mr.close_date is not NULL THEN "used" END AS kit_status,
            case when (mr.make_onboard_date - CURDATE())<3 and (mr.make_onboard_date - CURDATE())>=0 and mr.close_date is null then "warning"
                    when (mr.make_onboard_date - CURDATE())<0 and mr.close_date is null then "expired" else "normal" end as exp_stat,
            case when (ir2.exp_date - CURDATE())<30 and (ir2.exp_date - CURDATE())>=0 and ir2.close_date is null then "warning"
                    when (ir2.exp_date - CURDATE())<0 and mr.close_date is null then "expired" else "normal" end as reagent_exp_stat,u.name as make_user,
        (SELECT COUNT(*) 
            FROM in_reagent ir3
            left join REF_LIB rl2 on ir3.gtin = rl2.gtin
            WHERE ir2.name = rl2.name and ir3.out_date is null
            ) AS remain,ir2.comment as reagent_comment, mr.comment as comment
            FROM make_reagent mr 
            left join (select ir.id,ir.date,ir.exp_date,name,ir.lot,ir.out_date,ir.gtin,ir.close_date,ir.in_id,ir.open_id,ir.comment, rl.code,rl.temp,rl.volume,rl.instrument,rl.onboard,ir.quantity,rl.total_ea,rl.manufact,rl.unit,rl.name_short,rl.make_onboard_day,rl.etc,rl.print_form from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin) ir2 on mr.reagent_id=ir2.id
            LEFT JOIN `user` u ON mr.make_user  = u.username
            WHERE 
            (mr.date between %s and %s or mr.close_date between %s and %s) 
            '''

    params = [start,end,start,end]


    if reagent != 'all':
        sql += 'AND ir2.name = %s '
        params.append(reagent)

    if instrument != 'all':
        sql += 'AND ir2.instrument = %s '
        params.append(instrument)

    if code != 'all':
        sql += 'AND ir2.code = %s '
        params.append(code)
    if warning == 'warning':
        sql += '''OR ((
        
                    (mr.make_onboard_date - CURDATE())<3 and  mr.close_date is null
                ) or 
                (
                    (ir2.exp_date - CURDATE())<30 and ir2.close_date is null
                )
        ) '''       

    sql += ' ORDER BY ir2.instrument, ir2.code,ir2.name, ir2.out_date,mr.date, CASE WHEN make_date IS NULL THEN 1 ELSE 0 END, make_date,mr.reagent_id,mr.quantity,CASE WHEN mr.close_date IS NULL THEN 1 ELSE 0 END, mr.close_date'

    data = execute_query(conn, sql, tuple(params))
    conn.close()
    return jsonify({'result': data})



@app.route("/print_maked_reagent", methods=["POST"])
def print_maked_reagent():
    conn = create_connection()
    start = request.form['start']
    end = request.form['end']
    instrument = request.form['instrument']
    sql = '''
            SELECT mr.id,mr.reagent_id, SUBSTRING(mr.in_date,1,10) as in_date,SUBSTRING(mr.date,1,10) as make_date, mr.name, mr.lot, SUBSTRING(mr.exp_date,1,10) as exp, substring(mr.make_onboard_date,1,10) as make_onboard_date,
            ir2.code, SUBSTRING(mr.close_date,1,10) as close_date, mr.quantity, ir2.instrument, ir2.total_ea,ir2.quantity as ir_quantity,
            ir2.temp, CASE WHEN mr.exp_date < CURDATE() THEN "expired" ELSE "usable" END AS status, 
            CASE WHEN mr.date is not NULL AND mr.close_date is NULL THEN "using" 
            WHEN mr.date is NULL THEN "not open" 
            WHEN mr.close_date is not NULL THEN "used" END AS kit_status,
            case when (mr.make_onboard_date - CURDATE())<3 and (mr.make_onboard_date - CURDATE())>=0 and mr.close_date is null then "warning"
                    when (mr.make_onboard_date - CURDATE())<0 and mr.close_date is null then "expired" else "normal" end as exp_stat,
            case when (ir2.exp_date - CURDATE())<30 and (ir2.exp_date - CURDATE())>=0 and ir2.close_date is null then "warning"
                    when (ir2.exp_date - CURDATE())<0 and mr.close_date is null then "expired" else "normal" end as reagent_exp_stat,u.name as make_user,
        (SELECT COUNT(*) 
            FROM in_reagent ir3
            left join REF_LIB rl2 on ir3.gtin = rl2.gtin
            WHERE ir2.name = rl2.name and ir3.out_date is null
            ) AS remain,ir2.comment as reagent_comment, mr.comment as comment
            FROM make_reagent mr 
            left join (select ir.id,ir.date,ir.exp_date,name,ir.lot,ir.out_date,ir.gtin,ir.close_date,ir.in_id,ir.open_id,ir.comment, rl.code,rl.temp,rl.volume,rl.instrument,rl.onboard,ir.quantity,rl.total_ea,rl.manufact,rl.unit,rl.name_short,rl.make_onboard_day,rl.etc,rl.print_form from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin) ir2 on mr.reagent_id=ir2.id
            LEFT JOIN `user` u ON mr.make_user  = u.username
            WHERE ir2.make_onboard_day>0 and
            (mr.date between %s and %s or mr.close_date between %s and %s) 
            '''

    params = [start,end,start,end]


    if instrument != 'all':
        sql += 'AND ir2.instrument = %s '
        params.append(instrument)
    sql += ' ORDER BY make_date,ir2.code,ir2.name, ir2.out_date,mr.date, CASE WHEN make_date IS NULL THEN 1 ELSE 0 END, mr.reagent_id,mr.quantity,CASE WHEN mr.close_date IS NULL THEN 1 ELSE 0 END, mr.close_date'

    data = execute_query(conn, sql, tuple(params))
    conn.close()
    return jsonify({'result': data})

# 출고시약 검색
@app.route("/out_search", methods=["POST"])
def out_search():
    conn = create_connection()
    start_receive = request.form['start_give']
    end_receive = request.form['end_give']
    code_receive = request.form['code_give']
    instrument_receive = request.form['instrument_give']
    name = request.form['name']
    edit = request.form['edit']
    warning = request.form['warning']
    print(start_receive, end_receive, instrument_receive, code_receive)

    if edit == 'edit':
        # Initialize the base SQL query.
        sql = '''
        SELECT ir.id, SUBSTRING(ir.date,1,10) as date, rl.name, lot, SUBSTRING(ir.exp_date,1,10) as exp, rl.code, 
        SUBSTRING(ir.out_date,1,10) as out_date, SUBSTRING(ir.close_date,1,10) as close_date, quantity, rl.instrument, 
        rl.temp, CASE WHEN ir.exp_date < CURDATE() THEN "expired" ELSE "usable" END AS status, 
        CASE WHEN out_date is not NULL AND close_date is NULL THEN "using" 
        WHEN out_date is NULL THEN "not open" 
        WHEN close_date is not NULL THEN "used" END AS kit_status,
        case when (ir.exp_date - CURDATE())<30 and (ir.exp_date - CURDATE())>=0 and ir.close_date is null then "warning"
                when (ir.exp_date - CURDATE())<0 and ir.close_date is null then "expired" else "normal" end as exp_stat,
        u.name as in_user, u2.name as open_user, ir.comment, rl.total_ea,
        (SELECT COUNT(*) 
        FROM in_reagent ir2
        left join REF_LIB rl2 on ir2.gtin = rl2.gtin
        WHERE rl.name = rl2.name and ir2.out_date is null
            ) AS remain 
        FROM in_reagent ir 
        LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin 
        LEFT JOIN `user` u ON ir.in_id = u.username 
        LEFT JOIN user u2 ON ir.open_id = u2.username 
        where ((ir.date BETWEEN %s AND %s) or (ir.out_date BETWEEN %s AND %s OR ir.close_date BETWEEN %s AND %s)) 
        '''

        params = [start_receive,end_receive,start_receive,end_receive,start_receive,end_receive]

        

        if name != 'all':
            sql += 'AND rl.name = %s '
            params.append(name)

        if instrument_receive != 'all':
            sql += 'AND rl.instrument = %s '
            params.append(instrument_receive)

        if code_receive != 'all':
            sql += 'AND rl.code = %s '
            params.append(code_receive)
        if warning == 'warning':
            sql += '''OR (
                (ir.exp_date - CURDATE())<30 and ir.close_date is null) '''
            
            sql += '''OR ((
            
                        (ir.exp_date - CURDATE())<3 and  ir.close_date is null
                    ) or 
                    (
                        (ir.exp_date - CURDATE())<30 and ir.close_date is null
                    )
            ) '''   

        sql += ' ORDER BY rl.instrument, rl.code, rl.name, date, CASE WHEN out_date IS NULL THEN 1 ELSE 0 END,out_date, CASE WHEN close_date IS NULL THEN 1 ELSE 0 END, close_date'

        data = execute_query(conn, sql, tuple(params))

    else:
        sql2 = '''
            SELECT mr.id,mr.reagent_id
            FROM make_reagent mr 
            left join (select ir.id,ir.date,ir.exp_date,name,ir.lot,ir.out_date,ir.gtin,ir.close_date,ir.in_id,ir.open_id,ir.comment, rl.code,rl.temp,rl.volume,rl.instrument,rl.onboard,ir.quantity,rl.total_ea,rl.manufact,rl.unit,rl.name_short,rl.make_onboard_day,rl.etc,rl.print_form from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin) ir2 on mr.reagent_id=ir2.id
            LEFT JOIN `user` u ON mr.make_user  = u.username
            WHERE 
            (mr.date between %s and %s or mr.close_date between %s and %s) 
            '''

        params2 = [start_receive,end_receive,start_receive,end_receive]

        
        if name != 'all':
            sql2 += 'AND ir2.name = %s '
            params2.append(name)

        if instrument_receive != 'all':
            sql2 += 'AND ir2.instrument = %s '
            params2.append(instrument_receive)
        
        
        if code_receive != 'all':
            sql2 += 'AND ir2.code = %s '
            params2.append(code_receive)
        if warning == 'warning':
            sql2 += '''OR ((
            
                        (mr.make_onboard_date - CURDATE())<3 and  mr.close_date is null
                    ) or 
                    (
                        (ir2.exp_date - CURDATE())<30 and ir2.close_date is null
                    )
            ) '''       

        sql2 += 'group by mr.reagent_id'

        data_list = execute_query(conn, sql2, tuple(params2))

        sql3 = '''
            SELECT ir.id, SUBSTRING(ir.date,1,10) as date, rl.name, lot, SUBSTRING(ir.exp_date,1,10) as exp, rl.code, 
        SUBSTRING(ir.out_date,1,10) as out_date, SUBSTRING(ir.close_date,1,10) as close_date, quantity, rl.instrument, 
        rl.temp, CASE WHEN ir.exp_date < CURDATE() THEN "expired" ELSE "usable" END AS status, 
        CASE WHEN out_date is not NULL AND close_date is NULL THEN "using" 
        WHEN out_date is NULL THEN "not open" 
        WHEN close_date is not NULL THEN "used" END AS kit_status,
        case when (ir.exp_date - CURDATE())<30 and (ir.exp_date - CURDATE())>=0 and ir.close_date is null then "warning"
                when (ir.exp_date - CURDATE())<0 and ir.close_date is null then "expired" else "normal" end as exp_stat,
        u.name as in_user, u2.name as open_user, ir.comment, rl.total_ea,
        (SELECT COUNT(*) 
        FROM in_reagent ir2
        left join REF_LIB rl2 on ir2.gtin = rl2.gtin
        WHERE rl.name = rl2.name and ir2.out_date is null
            ) AS remain 
        FROM in_reagent ir 
        LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin 
        LEFT JOIN `user` u ON ir.in_id = u.username 
        LEFT JOIN user u2 ON ir.open_id = u2.username 
        where ir.id in ( '' '''

        params3 = []
        for row in data_list:
            id = row['reagent_id'] # type: ignore
            print(id)
            sql3 += ', %s '
            params3.append(id)
            print(sql3,params3)

        sql3 += ')'
        
        sql3 += ' ORDER BY rl.instrument, rl.code, rl.name, date, CASE WHEN out_date IS NULL THEN 1 ELSE 0 END,out_date, CASE WHEN close_date IS NULL THEN 1 ELSE 0 END, close_date'
        print(sql3)
        data = execute_query(conn, sql3, tuple(params3))

    sql1 = '''
            SELECT mr.id,mr.reagent_id, SUBSTRING(mr.in_date,1,10) as in_date,SUBSTRING(mr.date,1,10) as make_date, mr.name, mr.lot, SUBSTRING(mr.exp_date,1,10) as exp, substring(mr.make_onboard_date,1,10) as make_onboard_date,
            ir2.code, SUBSTRING(mr.close_date,1,10) as close_date, mr.quantity, ir2.instrument, ir2.total_ea,ir2.quantity as ir_quantity,
            ir2.temp, CASE WHEN mr.exp_date < CURDATE() THEN "expired" ELSE "usable" END AS status, 
            CASE WHEN mr.date is not NULL AND mr.close_date is NULL THEN "using" 
            WHEN mr.date is NULL THEN "not open" 
            WHEN mr.close_date is not NULL THEN "used" END AS kit_status,
            case when (mr.make_onboard_date - CURDATE())<3 and (mr.make_onboard_date - CURDATE())>=0 and mr.close_date is null then "warning"
                    when (mr.make_onboard_date - CURDATE())<0 and mr.close_date is null then "expired" else "normal" end as exp_stat,
            case when (ir2.exp_date - CURDATE())<30 and (ir2.exp_date - CURDATE())>=0 and ir2.close_date is null then "warning"
                    when (ir2.exp_date - CURDATE())<0 and mr.close_date is null then "expired" else "normal" end as reagent_exp_stat,u.name as make_user,
        (SELECT COUNT(*) 
            FROM in_reagent ir3
            left join REF_LIB rl2 on ir3.gtin = rl2.gtin
            WHERE ir2.name = rl2.name and ir3.out_date is null
            ) AS remain,ir2.comment as reagent_comment, mr.comment as comment
            FROM make_reagent mr 
            left join (select ir.id,ir.date,ir.exp_date,name,ir.lot,ir.out_date,ir.gtin,ir.close_date,ir.in_id,ir.open_id,ir.comment, rl.code,rl.temp,rl.volume,rl.instrument,rl.onboard,ir.quantity,rl.total_ea,rl.manufact,rl.unit,rl.name_short,rl.make_onboard_day,rl.etc,rl.print_form from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin) ir2 on mr.reagent_id=ir2.id
            LEFT JOIN `user` u ON mr.make_user  = u.username
            WHERE 
            (mr.date between %s and %s or mr.close_date between %s and %s) 
            '''

    params = [start_receive,end_receive,start_receive,end_receive]


    if name != 'all':
        sql1 += 'AND ir2.name = %s '
        params.append(name)

    if instrument_receive != 'all':
        sql1 += 'AND ir2.instrument = %s '
        params.append(instrument_receive)

    if code_receive != 'all':
        sql1 += 'AND ir2.code = %s '
        params.append(code_receive)
    if warning == 'warning':
        sql1 += '''OR ((
        
                    (mr.make_onboard_date - CURDATE())<3 and  mr.close_date is null
                ) or 
                (
                    (ir2.exp_date - CURDATE())<30 and ir2.close_date is null
                )
        ) '''       

    sql1 += ' ORDER BY ir2.instrument, ir2.code,ir2.name, ir2.out_date,mr.date, CASE WHEN make_date IS NULL THEN 1 ELSE 0 END, make_date,mr.reagent_id,mr.quantity,CASE WHEN mr.close_date IS NULL THEN 1 ELSE 0 END, mr.close_date'

    data2 = execute_query(conn, sql1, tuple(params))


    
    conn.close()
    return jsonify({'result1': data, 'result2': data2})




# @app.route("/out_search2", methods=["POST"])
# def out_search2():
#     start_receive = request.form['start_give']
#     end_receive = request.form['end_give']
#     code_receive = request.form['code_give']
#     instrument_receive = request.form['instrument_give']
#     name = request.form['name']
#     edit = request.form['edit']
#     warning = request.form['warning']
#     print(start_receive, end_receive, instrument_receive, code_receive)
#     user1 = aliased(User)
#     user2 = aliased(User)
#     base_query = db.session.query(In_reagent, Ref_lib, user1, user2)\
#         .outerjoin(Ref_lib, In_reagent.gtin == Ref_lib.gtin)\
#         .outerjoin(user1, In_reagent.in_id == user1.username)\
#         .outerjoin(user2, In_reagent.open_id == user2.username)\
#         .filter((In_reagent.out_date.between(start_receive, end_receive)) |
#                 (In_reagent.close_date.between(start_receive, end_receive)))

#     if warning == 'warning':
#         base_query = base_query.filter((In_reagent.exp_date - db.func.CURRENT_DATE()) < 30, In_reagent.close_date == None)

#     results = base_query.all()
#     data = []

#     for in_reagent, ref_lib, in_user, open_user in results:
#         data.append({
#             'id': in_reagent.id,
#             'date': str(in_reagent.date)[:10],
#             'name': ref_lib.name,
#             'lot': in_reagent.lot,
#             'exp': str(in_reagent.exp_date)[:10],
#             'code': ref_lib.code,
#             'out_date': str(in_reagent.out_date)[:10] if in_reagent.out_date else None,
#             'close_date': str(in_reagent.close_date)[:10] if in_reagent.close_date else None,
#             'quantity': in_reagent.quantity,
#             'instrument': ref_lib.instrument,
#             'temp': ref_lib.temp,
#             'status': "expired" if in_reagent.exp_date < db.func.CURRENT_DATE() else "usable",
#             'kit_status': "using" if in_reagent.out_date and not in_reagent.close_date else "not open" if not in_reagent.out_date else "used",
#             'exp_stat': "warning" if (in_reagent.exp_date - db.func.CURRENT_DATE()) < 30 and in_reagent.close_date is None else "expired" if (in_reagent.exp_date - db.func.CURRENT_DATE()) < 0 and in_reagent.close_date is None else "normal",
#             'in_user': in_user.name,
#             'open_user': open_user.name,
#             'comment': in_reagent.comment,
#             'total_ea': ref_lib.total_ea,
#             'remain': db.session.query(db.func.count())\
#                 .outerjoin(Ref_lib, In_reagent.gtin == Ref_lib.gtin)\
#                 .filter(Ref_lib.name == ref_lib.name, In_reagent.out_date == None).scalar()
#         })
#     print(data)
#     return jsonify({'result': data})

# @app.route("/out_search", methods=["POST"])
# def out_search():
#     conn = create_connection()
#     start_receive = request.form['start_give']
#     end_receive = request.form['end_give']
#     code_receive = request.form['code_give']
#     instrument_receive = request.form['instrument_give']
#     name = request.form['name']
#     edit = request.form['edit']
#     print(start_receive, end_receive, instrument_receive, code_receive,edit)

#     if edit == 'edit':
        
#         sql = '''
#         SELECT ir.id, SUBSTRING(ir.date,1,10) as date, rl.name, lot, SUBSTRING(ir.exp_date,1,10) as exp, ir.ref, rl.code, 
#         SUBSTRING(ir.out_date,1,10) as out_date, SUBSTRING(ir.close_date,1,10) as close_date, quantity, rl.instrument, 
#         rl.temp, CASE WHEN ir.exp_date < CURDATE() THEN "expired" ELSE "usable" END AS status, 
#         CASE WHEN out_date is not NULL AND close_date is NULL THEN "using" 
#         WHEN out_date is NULL THEN "not open" 
#         WHEN close_date is not NULL THEN "used" END AS kit_status,
#         case when (ir.exp_date - CURDATE())<30 and ir.close_date is null then "warning"
#                 when (ir.exp_date - CURDATE())<0 and ir.close_date is null then "expired" else "normal" end as exp_stat,
#         u.name as in_user, u2.name as open_user, ir.comment,
#        (SELECT COUNT(*) 
#         FROM in_reagent ir2
#         left join REF_LIB rl2 on ir2.gtin = rl2.gtin
#         WHERE rl.name = rl2.name and ir2.out_date is null
#           ) AS remain 
#         FROM in_reagent ir 
#         LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin 
#         LEFT JOIN `user` u ON ir.in_id = u.username 
#         LEFT JOIN user u2 ON ir.open_id = u2.username 
#         WHERE ir.date between %s and %s 
#         '''

#         params = [start_receive,end_receive]

#         if name != 'all':
#             sql += 'AND rl.name = %s '
#             params.append(name)

#         if instrument_receive != 'all':
#             sql += 'AND rl.instrument = %s '
#             params.append(instrument_receive)

#         if code_receive != 'all':
#             sql += 'AND rl.code = %s '
#             params.append(code_receive)

#         sql += ' ORDER BY rl.instrument, rl.code,rl.name, date, CASE WHEN out_date IS NULL THEN 1 ELSE 0 END, out_date,CASE WHEN close_date IS NULL THEN 1 ELSE 0 END, close_date'

#         data = execute_query(conn, sql, tuple(params))
#     else:
#         # Initialize the base SQL query.
#         sql = '''
#         SELECT ir.id, SUBSTRING(ir.date,1,10) as date, rl.name, lot, SUBSTRING(ir.exp_date,1,10) as exp, ir.ref, rl.code, 
#         SUBSTRING(ir.out_date,1,10) as out_date, SUBSTRING(ir.close_date,1,10) as close_date, quantity, rl.instrument, 
#         rl.temp, CASE WHEN ir.exp_date < CURDATE() THEN "expired" ELSE "usable" END AS status, 
#         CASE WHEN out_date is not NULL AND close_date is NULL THEN "using" 
#         WHEN out_date is NULL THEN "not open" 
#         WHEN close_date is not NULL THEN "used" END AS kit_status,
#         case when (ir.exp_date - CURDATE())<30 and ir.close_date is null then "warning"
#                 when (ir.exp_date - CURDATE())<0 and ir.close_date is null then "expired" else "normal" end as exp_stat,
#         u.name as in_user, u2.name as open_user, ir.comment,
#        (SELECT COUNT(*) 
#         FROM in_reagent ir2
#         left join REF_LIB rl2 on ir2.gtin = rl2.gtin
#         WHERE rl.name = rl2.name and ir2.out_date is null
#           ) AS remain 
#         FROM in_reagent ir 
#         LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin 
#         LEFT JOIN `user` u ON ir.in_id = u.username 
#         LEFT JOIN user u2 ON ir.open_id = u2.username 
#         WHERE ir.out_date IS NOT NULL AND (
#         (ir.out_date BETWEEN %s AND %s OR ir.close_date BETWEEN %s AND %s) '''

#         params = [start_receive, end_receive, start_receive, end_receive]

#         if name != 'all':
#             sql += 'AND rl.name = %s '
#             params.append(name)

#         if instrument_receive != 'all':
#             sql += 'AND rl.instrument = %s '
#             params.append(instrument_receive)

#         if code_receive != 'all':
#             sql += 'AND rl.code = %s '
#             params.append(code_receive)

#         sql += ') ORDER BY rl.instrument, rl.code, rl.name, date, CASE WHEN out_date IS NULL THEN 1 ELSE 0 END,out_date, CASE WHEN close_date IS NULL THEN 1 ELSE 0 END, close_date'

#         data = execute_query(conn, sql, tuple(params))
#     conn.close()
#     return jsonify({'result': data})

# 장비선택시 입고된 시약검색   
@app.route("/instrument_select", methods=["POST"])
def instrument_select():    
    conn = create_connection()
    instrument_select = request.form['instrument_select']
    code_select = request.form['code_manual_search']
    print(instrument_select,code_select)
    if code_select=='all' and instrument_select!='all':
        sql = 'SELECT name, ir.gtin from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where rl.instrument = %s  group by name'
        data = execute_query(conn,sql,instrument_select)
    elif code_select=='all' and instrument_select=='all':
        sql = 'SELECT name, ir.gtin from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin group by name'
        data = execute_query(conn,sql)
    elif code_select!='all' and instrument_select=='all':
        sql = 'SELECT name, ir.gtin from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where rl.code = %s  group by name'
        data = execute_query(conn,sql,code_select)
    
    else:
        sql = 'SELECT name, ir.gtin from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where rl.instrument = %s and rl.code = %s  group by name'
        data = execute_query(conn,sql,(instrument_select,code_select))
    conn.close()
    print(data)
    return jsonify({'result':data})

# 장비선택시 등룍된 시약검색
@app.route("/instrument_select_in", methods=["POST"])
def instrument_select_in():    
    conn = create_connection()
    instrument_select = request.form['instrument_select']
    code_select = request.form['code_manual_search']
    print(instrument_select,code_select)
    if code_select=='all' and instrument_select!='all':
        sql = 'SELECT name, gtin from REF_LIB where instrument = %s and gtin is not NULL group by name order by instrument, name, code'
        data = execute_query(conn,sql,instrument_select)
    elif code_select=='all' and instrument_select=='all':
        sql = 'SELECT name, gtin from REF_LIB where gtin is not NULL group by name order by instrument, name, code'
        data = execute_query(conn,sql)
    elif code_select!='all' and instrument_select=='all':
        sql = 'SELECT name, gtin from REF_LIB where code = %s and gtin is not NULL group by name order by instrument, name'
        data = execute_query(conn,sql,code_select)
    
    else:
        sql = 'SELECT name, gtin from REF_LIB where instrument = %s and code = %s and gtin is not NULL group by name order by name'
        data = execute_query(conn,sql,(instrument_select,code_select))
    conn.close()
    # print(data)
    return jsonify({'result':data})

@app.route("/search_make_reagent_list", methods=["POST"])
def search_make_reagent_list():    
    conn = create_connection()
    instrument_select = request.form['instrument_select']
    code_select = request.form['code_manual_search']
    print(instrument_select,code_select)
    if code_select=='all' and instrument_select!='all':
        sql = 'SELECT name, gtin from REF_LIB where instrument = %s and gtin is not NULL and make_onboard_day != 0 group by name order by instrument, name, code'
        data = execute_query(conn,sql,instrument_select)
    elif code_select=='all' and instrument_select=='all':
        sql = 'SELECT name, gtin from REF_LIB where gtin is not NULL and make_onboard_day != 0 group by name order by instrument, name, code'
        data = execute_query(conn,sql)
    elif code_select!='all' and instrument_select=='all':
        sql = 'SELECT name, gtin from REF_LIB where rl.code = %s and gtin is not NULL and make_onboard_day != 0 group by name order by instrument, name'
        data = execute_query(conn,sql,code_select)
    
    else:
        sql = 'SELECT name, gtin from REF_LIB where instrument = %s and code = %s and gtin is not NULL and make_onboard_day != 0 group by name order by name'
        data = execute_query(conn,sql,(instrument_select,code_select))
    conn.close()
    # print(data)
    return jsonify({'result':data})




# 미사용 시약 정보 검색 시약이름으로 검색   
@app.route("/reagent_select", methods=["POST"])
def reagent_select():
    conn = create_connection()
    instrument_select = request.form['instrument_select']
    reagent_select = request.form['name']
    # print(instrument_select,reagent_select)
    sql = 'select name, lot, ir.gtin from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where ir.out_date is null and instrument = %s and rl.name = %s group by name, lot'
    data = execute_query(conn,sql,(instrument_select,reagent_select))
    conn.close()
    return jsonify({'result':data})

# 시약 정보 검색 / 시약 gtin으로 검색
@app.route("/reagent_select2", methods=["POST"])
def reagent_select2():
    conn = create_connection()
    instrument_select = request.form['instrument_select']
    reagent_select = request.form['gtin']
    # print(instrument_select,reagent_select)
    sql = 'select name from REF_LIB where gtin = %s'
    data = execute_query(conn,sql,reagent_select)
    name = data[0]['name'] # type: ignore

    sql = 'select name, lot, ir.gtin, rl.etc from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where instrument = %s and rl.name = %s group by name, lot order by ir.lot desc limit 4'
    data = execute_query(conn,sql,(instrument_select,name))
    conn.close()
    return jsonify({'result':data})

# 시약정보검색 제조물질
@app.route("/make_reagent_select", methods=["POST"])
def make_reagent_select():
    conn = create_connection()
    instrument_select = request.form['instrument_select']
    reagent_select = request.form['name']
    if instrument_select == 'all':
        sql = 'select name, lot, ir.gtin,make_onboard_day from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where ir.close_date is null and quantity != total_ea and rl.name = %s group by name, lot'
        data = execute_query(conn,sql,(reagent_select))
    else:
    # print(instrument_select,reagent_select)
        sql = 'select name, lot, ir.gtin,make_onboard_day from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where ir.close_date is null and quantity != total_ea and instrument = %s and rl.name = %s group by name, lot'
        data = execute_query(conn,sql,(instrument_select,reagent_select))
    conn.close()
    return jsonify({'result':data})

# input datalist 시약 리스트
@app.route("/reagent", methods=["GET"]) # type: ignore
def reagent_list():
    conn = create_connection()
    sql = 'select name from REF_LIB group by name order by instrument, code, name'
    data = execute_query(conn, sql)
    conn.close()
    return jsonify({'result' : data})

# 제조물질 시약리스트
@app.route("/make_reagent_list", methods=["POST"]) # type: ignore
def make_reagent_list():
    instrument=request.form['instrument']
    print(instrument)
    conn = create_connection()
    if instrument == 'all':
        make_reagent_list='''
            select rl.name from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where ir.close_date is null and ir.quantity != rl.total_ea group by name order by instrument, code, name
        '''
        # sql = 'select name from REF_LIB where make_onboard_day != "0" group by name order by instrument, code, name'
        data = execute_query(conn, make_reagent_list)
    else:
        make_reagent_list='''
            select rl.name from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where ir.close_date is null and ir.quantity != rl.total_ea and instrument = %s group by name order by instrument, code, name
        '''
        # sql = 'select name from REF_LIB where make_onboard_day != "0" and instrument = %s group by name order by instrument, code, name'
        data = execute_query(conn, make_reagent_list,instrument)
    conn.close()
    return jsonify({'result' : data})

# 시약 입고 유효기간 자동입력
@app.route("/lot_search", methods=["POST"])
def lot_search():
    conn = create_connection()
    lot =  request.form['lot']
    gtin = request.form['gtin']
    sql = 'select name from REF_LIB where gtin = %s'
    data = execute_query(conn,sql,gtin)
    name = data[0]['name'] # type: ignore
    sql = 'select SUBSTRING(ir.exp_date,1,10) as exp_date from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where lot = %s and name = %s limit 1'
    data = execute_query(conn,sql,(lot,name))
    conn.close()
    return jsonify({'result' : data})

# 제조물질 유효기간 자동입력
@app.route("/lot_search2", methods=["POST"])
def lot_search2():
    conn = create_connection()
    lot =  request.form['lot']
    name = request.form['name']
    sql = '''select rl.instrument,ir.id,SUBSTRING(ir.date,1,10) as in_date, SUBSTRING(ir.exp_date,1,10) as exp_date, quantity, total_ea,rl.make_onboard_day from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where ir.close_date is null and quantity != total_ea and lot = %s and name = %s order by quantity desc limit 1'''
    lot_data = execute_query(conn,sql,(lot,name))
    count_sql = '''
            select rl.name, count(rl.name) as inventory from in_reagent ir
            left join REF_LIB rl on ir.gtin=rl.gtin 
            where ir.out_date is null and ir.close_date is null and name = %s
            group by rl.name, instrument
        '''
    count_data = execute_query(conn,count_sql,name)
    print(lot_data)
    conn.close()
    return jsonify({'result' : lot_data,'count_data' : count_data})

@app.route("/out_make_search", methods=["POST"]) # type: ignore
def out_make_search():
    conn = create_connection()
    search = request.form['search']
    check = search[:2]
    if check=="01":
        ref, lot, exp, gtin = analyze_barcode(search)

        gtin_search = '''
            select name from REF_LIB where gtin = %s
            '''
        data = execute_query(conn,gtin_search,gtin)
        if data:
            name = data[0]['name'] # type: ignore
            in_reagent_search = '''
                select rl.name,ir.lot,rl.instrument, SUBSTRING(ir.exp_date,1,10) as exp_date from in_reagent ir 
                left join REF_LIB rl on ir.gtin = rl.gtin 
                where ir.close_date is null and quantity != total_ea and lot = %s and name = %s
                order by quantity desc limit 1
                '''
            in_reagent_data = execute_query(conn,in_reagent_search,(lot,name))
        else:
            in_reagent_search = '''
                select rl.name,ir.lot,rl.instrument, SUBSTRING(ir.exp_date,1,10) as exp_date from in_reagent ir 
                left join REF_LIB rl on ir.gtin = rl.gtin 
                where ir.close_date is null and quantity != total_ea and lot = %s
                order by quantity desc limit 1
                '''
            in_reagent_data = execute_query(conn,in_reagent_search,lot)
    else:
        in_reagent_search = '''
            select rl.name,ir.lot,rl.instrument, SUBSTRING(ir.exp_date,1,10) as exp_date from in_reagent ir 
            left join REF_LIB rl on ir.gtin = rl.gtin 
            where ir.close_date is null and quantity != total_ea and name = %s
            order by quantity desc limit 1
            '''
        in_reagent_data = execute_query(conn,in_reagent_search,search)
    
    conn.close()
    return jsonify({'result' : in_reagent_data})

@app.route("/in_reagent_search", methods=["POST"])
def in_reagent_search():
    try:
        conn = create_connection()
        start_receive = request.form['start_give']
        end_receive = request.form['end_give']
        instrument_receive = request.form['instrument_give']
        code_receive = request.form['code_give']
        name = request.form['name']
        sql_base = '''
            SELECT ir.gtin,
            SUBSTRING(ir.date,1,10) as date,
            rl.name,
            lot,
            SUBSTRING(ir.exp_date,1,10) as exp,
            count(*) as ea,
            count(ir.out_date) as used_ea,
            rl.code,
            SUBSTRING(ir.out_date,1,10) as out_date, quantity,
            rl.instrument,
            rl.temp,
            CASE WHEN ir.exp_date < CURDATE() THEN "expired" ELSE "usable" END AS status,
            CASE WHEN out_date is not NULL AND close_date is NULL THEN "using"
                WHEN out_date is NULL THEN "not open"
                WHEN close_date is not NULL THEN "used" END AS kit_status,
            case when (ir.exp_date - CURDATE())<30 and ir.close_date is null then "warning"
                when (ir.exp_date - CURDATE())<0 and ir.close_date is null then "expired" else "normal" end as exp_stat,
            u.name as in_user,
            u2.name as open_user,
            ir.comment
            FROM in_reagent ir
            LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin
            LEFT JOIN `user` u ON ir.in_id = u.username
            LEFT JOIN `user` u2 ON ir.open_id = u2.username
            WHERE ir.date BETWEEN %s AND %s
        '''
        conditions = []
        params = [start_receive, end_receive]

        if name != 'all':
            conditions.append('rl.name = %s')
            params.append(name)
        
        if instrument_receive != 'all':
            conditions.append('rl.instrument = %s')
            params.append(instrument_receive)
        
        if code_receive != 'all':
            conditions.append('rl.code = %s')
            params.append(code_receive)
        
        if conditions:
            sql = f"{sql_base} AND {' AND '.join(conditions)} Group by ir.date, rl.name, ir.lot,ir.comment ORDER BY date DESC, rl.list, name, CASE WHEN out_date IS NULL THEN 1 ELSE 0 END, out_date"
        else:
            sql = f"{sql_base} Group by ir.date,rl.name,ir.lot,ir.comment ORDER BY date DESC, rl.list, name, CASE WHEN out_date IS NULL THEN 1 ELSE 0 END, out_date"
        
        data = execute_query(conn, sql, tuple(params))
        conn.close()
        return jsonify({'result': data})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route("/modify_save", methods=["POST"])
def modify_save():
    conn = create_connection()
    date = request.form['date']
    gtin = request.form['gtin']
    lot = request.form['lot']
    comment = request.form['comment']
    exp = request.form['exp']
    ea = int(request.form['ea'])
    in_user = request.form['user']
    modify_date = request.form['modify_date']
    modify_lot = request.form['modify_lot']
    modify_exp = request.form['modify_exp']
    modify_ea = int(request.form['modify_ea'])
    modify_comment = request.form['modify_comment']
    if not comment and not modify_comment:
        sql = '''
                update in_reagent 
                set date = %s,lot = %s,exp_date = %s,comment = NULL 
                Where date = %s and gtin = %s and lot = %s and exp_date = %s and comment is NULL
                '''
        execute_query(conn,sql,(modify_date,modify_lot,modify_exp,date,gtin,lot,exp))
        conn.commit()
        print('1')

        if ea > modify_ea >= 0:
            drop_ea = ea - modify_ea
            sql = 'DELETE FROM in_reagent WHERE date= %s and gtin = %s and lot = %s and exp_date = %s and comment is NULL and out_date is NULL limit %s'
            execute_query(conn,sql,(date,gtin,lot,exp,drop_ea))
            conn.commit()
            print('1-1')
            
            
            
        elif ea <= modify_ea:
            add_ea = modify_ea - ea
            i = 0
            while i < add_ea:
                sql = '''
                    Insert into in_reagent (date,gtin,lot,exp_date,in_id)
                    values 
                    (%s,%s,%s,%s,%s)
                    '''
                execute_query(conn,sql,(modify_date,gtin,modify_lot,modify_exp,in_user))
                i += 1
                conn.commit()
                print(i,'1-2-1')
            print('1-2')
    elif not comment:
        sql = '''
                update in_reagent 
                set date = %s,lot = %s,exp_date = %s,comment = %s 
                Where date = %s and gtin = %s and lot = %s and exp_date = %s and comment is NULL
                '''
        execute_query(conn,sql,(modify_date,modify_lot,modify_exp,modify_comment,date,gtin,lot,exp))
        conn.commit()
        print('2')

        if ea > modify_ea >= 0:
            drop_ea = ea - modify_ea
            sql = 'DELETE FROM in_reagent WHERE date= %s and gtin = %s and lot = %s and exp_date = %s and comment is NULL and out_date is NULL limit %s'
            execute_query(conn,sql,(date,gtin,lot,exp,drop_ea))
            conn.commit()
            print('2-1')
            
        elif ea <= modify_ea:
            add_ea = modify_ea - ea
            i = 0
            while i < add_ea:
                sql = '''
                    Insert into in_reagent (date,gtin,lot,exp_date,in_id,comment)
                    values 
                    (%s,%s,%s,%s,%s,%s)
                    '''
                execute_query(conn,sql,(modify_date,gtin,modify_lot,modify_exp,in_user,modify_comment))
                i += 1
                conn.commit()
            print('2-2')
    elif not modify_comment:
        sql = '''
                update in_reagent 
                set date = %s,lot = %s,exp_date = %s,comment = null 
                Where date = %s and gtin = %s and lot = %s and exp_date = %s and comment = %s
                '''
        execute_query(conn,sql,(modify_date,modify_lot,modify_exp,date,gtin,lot,exp,comment))
        conn.commit()

        if ea > modify_ea >= 0:
            drop_ea = ea - modify_ea

            
            sql = 'DELETE FROM in_reagent WHERE date= %s and gtin = %s and lot = %s and exp_date = %s and comment is NULL and out_date is NULL limit %s'
            execute_query(conn,sql,(modify_date,gtin,modify_lot,modify_exp,modify_comment,drop_ea))
            
            conn.commit()
            
        elif ea <= modify_ea:
            add_ea = modify_ea - ea
            i = 0
            while i < add_ea:
                sql = '''
                    Insert into in_reagent (date,gtin,lot,exp_date,in_id)
                    values 
                    (%s,%s,%s,%s,%s)
                    '''
                execute_query(conn,sql,(modify_date,gtin,modify_lot,modify_exp,in_user))
                i += 1
                conn.commit()
    else:
        sql = '''
                update in_reagent 
                set date = %s,lot = %s,exp_date = %s,comment = %s 
                Where date = %s and gtin = %s and lot = %s and exp_date = %s and comment = %s
                '''
        execute_query(conn,sql,(modify_date,modify_lot,modify_exp,modify_comment,date,gtin,lot,exp,comment))
        conn.commit()

        if ea > modify_ea >= 0:
            drop_ea = ea - modify_ea

            
            sql = 'DELETE FROM in_reagent WHERE date= %s and gtin = %s and lot = %s and exp_date = %s and comment =%s and out_date is NULL limit %s'
            execute_query(conn,sql,(date,gtin,lot,exp,comment,drop_ea))
            
            conn.commit()
            
        elif ea <= modify_ea:
            add_ea = modify_ea - ea
            i = 0
            while i < add_ea:
                sql = '''
                    Insert into in_reagent (date,gtin,lot,exp_date,in_id,comment)
                    values 
                    (%s,%s,%s,%s,%s,%s)
                    '''
                execute_query(conn,sql,(modify_date,gtin,modify_lot,modify_exp,in_user,modify_comment))
                i += 1
                conn.commit()
    
    
    conn.close()
    return jsonify({'msg': '수정 완료!'})



@app.route("/search_open", methods=["POST"])
def search_open():
    conn = create_connection()
    instrument_receive = request.form['instrument_give']
    code_receive = request.form['code_give']
    print(instrument_receive, code_receive)

    # Initialize the base SQL query.
    sql = '''
    SELECT ir.id, SUBSTRING(ir.date,1,10) as date, rl.name, lot, SUBSTRING(ir.exp_date,1,10) as exp, rl.code, 
    SUBSTRING(ir.out_date,1,10) as out_date, quantity, rl.instrument, rl.temp, rl.total_ea, 
    CASE WHEN ir.exp_date < CURDATE() THEN "expired" ELSE "usable" END AS status, 
    CASE WHEN out_date is not NULL AND close_date is NULL THEN "using" 
    WHEN out_date is NULL THEN "not open" 
    WHEN close_date is not NULL THEN "used" END AS kit_status,
    case when (ir.exp_date - CURDATE())<30 and ir.close_date is null then "warning"
        when (ir.exp_date - CURDATE())<0 and ir.close_date is null then "expired" 
        else "normal" end as exp_stat,
    u.name as in_user, u2.name as open_user, ir.comment 
    FROM in_reagent ir 
    LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin 
    LEFT JOIN `user` u ON ir.in_id = u.username 
    LEFT JOIN user u2 ON ir.open_id = u2.username 
    WHERE ir.out_date IS NOT NULL  and ir.close_date is NULL and ir.quantity <= rl.total_ea AND rl.total_ea > 1 '''

    params = []

    if instrument_receive != 'all':
        sql += 'AND rl.instrument = %s '
        params.append(instrument_receive)

    if code_receive != 'all':
        sql += 'AND rl.code = %s '
        params.append(code_receive)

    sql += 'ORDER BY list,rl.instrument,rl.code,rl.name,ir.out_date'

    data = execute_query(conn, sql, tuple(params))
    conn.close()
    return jsonify({'result': data})

@app.route("/search_open_without_maked", methods=["POST"])
def search_open_without_maked():
    conn = create_connection()
    instrument_receive = request.form['instrument_give']
    code_receive = request.form['code_give']
    reagent = request.form['reagent_give']
    print(instrument_receive, code_receive)

    # Initialize the base SQL query.
    sql = '''
    SELECT ir.id, SUBSTRING(ir.date,1,10) as date, rl.name, lot, SUBSTRING(ir.exp_date,1,10) as exp, rl.code, 
    SUBSTRING(ir.out_date,1,10) as out_date, quantity, rl.instrument, rl.temp, rl.total_ea, 
    CASE WHEN ir.exp_date < CURDATE() THEN "expired" ELSE "usable" END AS status, 
    CASE WHEN out_date is not NULL AND close_date is NULL THEN "using" 
    WHEN out_date is NULL THEN "not open" 
    WHEN close_date is not NULL THEN "used" END AS kit_status,
    case when (ir.exp_date - CURDATE())<30 and ir.close_date is null then "warning"
        when (ir.exp_date - CURDATE())<0 and ir.close_date is null then "expired" 
        else "normal" end as exp_stat,
    u.name as in_user, u2.name as open_user, ir.comment 
    FROM in_reagent ir 
    LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin 
    LEFT JOIN `user` u ON ir.in_id = u.username 
    LEFT JOIN user u2 ON ir.open_id = u2.username 
    WHERE ir.out_date IS NOT NULL AND rl.make_onboard_day = 0 and ir.close_date is NULL and ir.quantity <= rl.total_ea AND rl.total_ea > 1 '''

    params = []

    if instrument_receive != 'all':
        sql += 'AND rl.instrument = %s '
        params.append(instrument_receive)

    if code_receive != 'all':
        sql += 'AND rl.code = %s '
        params.append(code_receive)
    
    if reagent != 'all':
        sql += 'AND rl.name = %s '
        params.append(reagent)

    sql += 'ORDER BY list,rl.instrument,rl.code,rl.name,ir.out_date'

    data = execute_query(conn, sql, tuple(params))
    conn.close()
    return jsonify({'result': data})

# 제조물질장부 개봉시약리스트
@app.route("/search_open_maked", methods=["POST"])
def search_open_maked():
    conn = create_connection()
    instrument_receive = request.form['instrument']
    code_receive = request.form['code']
    reagent_receive = request.form['reagent']
    print(instrument_receive, code_receive)

    # Initialize the base SQL query.
    sql = '''
    SELECT ir.id, SUBSTRING(ir.date,1,10) as date, rl.name, lot, SUBSTRING(ir.exp_date,1,10) as exp, rl.code, 
    SUBSTRING(ir.out_date,1,10) as out_date, quantity, rl.instrument, rl.temp, rl.total_ea, 
    CASE WHEN ir.exp_date < CURDATE() THEN "expired" ELSE "usable" END AS status, 
    CASE WHEN out_date is not NULL AND close_date is NULL THEN "using" 
    WHEN out_date is NULL THEN "not open" 
    WHEN close_date is not NULL THEN "used" END AS kit_status,
    case when (ir.exp_date - CURDATE())<30 and ir.close_date is null then "warning"
        when (ir.exp_date - CURDATE())<0 and ir.close_date is null then "expired" 
        else "normal" end as exp_stat,
    u.name as in_user, u2.name as open_user, ir.comment 
    FROM in_reagent ir 
    LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin 
    LEFT JOIN `user` u ON ir.in_id = u.username 
    LEFT JOIN user u2 ON ir.open_id = u2.username 
    WHERE ir.out_date IS NOT NULL AND ir.close_date is NULL and ir.quantity <= rl.total_ea AND rl.total_ea > 1 '''

    params = []

    if instrument_receive != 'all':
        sql += 'AND rl.instrument = %s '
        params.append(instrument_receive)

    if code_receive != 'all':
        sql += 'AND rl.code = %s '
        params.append(code_receive)

    if reagent_receive != 'all':
        sql += 'AND rl.name = %s '
        params.append(reagent_receive)

    sql += 'ORDER BY list,rl.instrument,rl.code,rl.name,ir.out_date'

    data = execute_query(conn, sql, tuple(params))
    conn.close()
    return jsonify({'result': data})


#입고 통계 검색;total.html
@app.route("/total_count", methods=["POST"])
def total_count():
    conn = create_connection()
    start_receive = request.form['start_give']
    end_receive = request.form['end_give']
    instrument_receive = request.form['instrument_give']
    code_receive = request.form['code_give']
    name = request.form['name']

    sql_base = '''
        SELECT rl.instrument,rl.name,rl.code,
	(
		count(case when ir.out_date between %s and %s then 1 else NULL end)
		+count(CASE WHEN (ir.out_date is null or ir.out_date > %s) and ir.date <= %s THEN 1 ELSE NULL END)
		-count(case when ir.date between %s and %s then 1 else NULL end)
	) as early_month,
    count(case when ir.date between %s and %s then 1 else NULL end) as ea, 
    count(case when ir.out_date between %s and %s then 1 else NULL end) as used,
    count(case when ir.out_date is not null and ir.close_date is null then 1 else NULL end) as opened,
    COUNT(CASE WHEN (ir.out_date is null or ir.out_date > %s) and ir.date <= %s THEN 1 ELSE NULL END) as inventory,
    (rl.total_ea - (SELECT quantity 
        FROM in_reagent ir2 
        WHERE ir2.gtin = ir.gtin 
        AND ir2.close_date IS NULL 
        AND ir2.out_date IS NOT NULL limit 1)) as remain,
        (select count(*) from make_reagent mr where mr.name = rl.name and  mr.date between %s and %s ) as vial
    FROM in_reagent ir 
    LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin
    '''

    conditions = []
    params = [start_receive,end_receive,end_receive,end_receive,start_receive,end_receive,start_receive,end_receive,start_receive,end_receive,end_receive,end_receive,start_receive,end_receive]

    if name != 'all':
        conditions.append('rl.name = %s')
        params.append(name)

    if instrument_receive != 'all':
        conditions.append('rl.instrument = %s')
        params.append(instrument_receive)

    if code_receive != 'all':
        conditions.append('rl.code = %s')
        params.append(code_receive)

    if conditions:
        sql = f"{sql_base} WHERE {' AND '.join(conditions)} GROUP BY rl.name  ORDER BY rl.instrument, rl.code desc, rl.list, rl.name, ir.exp_date"
    else:
        sql = f"{sql_base} GROUP BY rl.name  ORDER BY rl.instrument, rl.code desc, rl.list, rl.name, ir.exp_date"
    print("quary : ",sql)

    data = execute_query(conn, sql, tuple(params))
    conn.close()

    return jsonify({'result': data})



@app.route("/reg_search", methods=["POST"])
def reg_search():
    conn = create_connection()
    instrument_receive = request.form['instrument_give']
    code_receive = request.form['code_give']
    gtin = request.form['gtin']
    name_search = '''
        select * from REF_LIB rl where gtin = %s
        '''
    name_data = execute_query(conn,name_search,gtin)
    
    print(name_data)
    sql_base = '''
        SELECT *
        FROM REF_LIB rl
        WHERE gtin is not NULL
    '''

    conditions = []
    params = []

    if gtin != 'all':
        name = name_data[0]['name'] # type: ignore
        conditions.append('name = %s')
        params.append(name)

    
    if instrument_receive != 'all':
        conditions.append('instrument = %s')
        params.append(instrument_receive)
    
    if code_receive != 'all':
        conditions.append('code = %s')
        params.append(code_receive)
    
    if conditions:
        sql = f"{sql_base} AND {' AND '.join(conditions)} ORDER BY instrument, code, name"
    else:
        sql = f"{sql_base} ORDER BY instrument, code, name"
    
    data = execute_query(conn, sql, tuple(params))
    conn.close()
    
    return jsonify({'result': data})

@app.route("/reagent_info", methods=["POST"])
def reagent_info():
    conn = create_connection()
    name = request.form['name']
    gtin = request.form['gtin']
    if gtin =='none':
        reagent_info_search = '''
            select * from REF_LIB where name = %s or gtin = %s
            '''
        data = execute_query(conn,reagent_info_search,(name,gtin))
    else :
        reagent_info_search = '''
            select * from REF_LIB where name = %s
            '''
        data = execute_query(conn,reagent_info_search,name)
    conn.close()
    return jsonify(data)



@app.route("/reg_barcode", methods=["POST"])
def reg_barcode():
    conn = create_connection()
    gtin = request.form['gtin']
    print(gtin)

    check = gtin[:2]
    if check=='01':
        gtin = gtin[2:16]
        
        sql = 'select * from REF_LIB where gtin= %s ' #등록 항목 확인 process
        data = execute_query(conn,sql,gtin)
        if data:
            name = data[0]['name'] # type: ignore
            sql = 'select * from REF_LIB where name = %s order by case when gtin = %s then 0 else 1 end'
            data = execute_query(conn,sql,(name,gtin))
        else:
            name = ""
        print("1",data,check,gtin)
    else:
        sql = 'select * from REF_LIB where name= %s order by gtin desc'
        data = execute_query(conn,sql,gtin)
        print("2",data,check,gtin)
    print(data)
    conn.close()
    return jsonify(data)

@app.route("/reg_edit", methods=["POST"])
def reg_edit():
    conn = create_connection()
    gtin = request.form['gtin']
    name = request.form['name']
    post_name = request.form['post_name']
    instrument = request.form['instrument']
    post_instrument = request.form['post_instrument']
    code = request.form['code']
    temp = request.form['temp']
    volume = request.form['volume']
    total_ea = request.form['total_ea']
    onboard = request.form['onboard']
    unit = request.form['unit']
    manufact = request.form['manufact']
    mode = request.form['mode']
    name_short = request.form['name_short']
    make_onboard = request.form['make_onboard']
    print_form = request.form['print_form']
    etc= request.form['etc']
    print(request)
    print(gtin,manufact,unit,mode)

    if mode == 'r':
        sql="INSERT  INTO REF_LIB (gtin, name, instrument, code, temp, volume, total_ea, onboard,unit,manufact,name_short,make_onboard_day,etc,print_form) VALUES (%s,%s, %s, %s, %s, %s, %s, %s,%s,%s,%s,%s,%s,%s) "
        execute_query(conn,sql,(gtin,name,instrument,code,temp,volume,total_ea,onboard,unit,manufact,name_short,make_onboard,etc,print_form))
        
    else :
        sql='update REF_LIB set name = %s, instrument = %s, code = %s, temp = %s, volume = %s, total_ea = %s, onboard = %s, unit = %s, manufact = %s, name_short = %s, make_onboard_day = %s, etc = %s, print_form = %s where name = %s and instrument = %s'
        execute_query(conn,sql,(name,instrument,code,temp,volume,total_ea,onboard,unit,manufact,name_short,make_onboard,etc,print_form,post_name, post_instrument))
    conn.commit()
    conn.close()
    return jsonify({'msg': '입력완료'})

@app.route("/del_reg", methods=["POST"])
def del_reg():
    conn = create_connection()
    gtin = request.form['gtin']

    sql = 'DELETE FROM REF_LIB WHERE gtin= %s'
    execute_query(conn,sql,gtin)
    conn.commit()
    conn.close()
    return jsonify({'msg': '삭제 완료!'})

#시약입출고장부
@app.route("/total_report_list", methods=["POST"])
def total_report_list():
    conn = create_connection()
    start_receive = request.form['start']
    end_receive = request.form['end']
    instrument_receive = request.form['instrument']
    
    sql = '''
    SELECT name, temp, volume, unit,manufact, %s as start, %s as end, rl.instrument, ir.gtin,name_short, rl.print_form from in_reagent ir 
    left join REF_LIB rl on ir.gtin = rl.gtin 
    where rl.instrument = %s group by rl.name ORDER by rl.instrument, code desc, list, rl.name, ir.gtin
    '''
   
    data = execute_query(conn, sql, (start_receive, end_receive, instrument_receive))

    conn.close()

    return jsonify({'result': data})

@app.route("/total_print_detail", methods=["POST"])
def total_print_detail():
    conn = create_connection()
    start_receive = request.form['start']
    end_receive = request.form['end']
    name = request.form['name']
    name_short = request.form['name_short']
    sql = '''
    SELECT SUBSTRING(ir.date,1,10) as date, lot, SUBSTRING(ir.exp_date,1,10) as exp_date, SUBSTRING(ir.out_date,1,10) as out_date, SUBSTRING(ir.close_date,1,10) as close_date, u.name as in_user, u2.name as open_user, ir.comment, rl.name_short,count(out_date) as out_count from in_reagent ir 
left join REF_LIB rl on ir.gtin = rl.gtin 
left join user u on ir.in_id  = u.username 
left join user u2 on ir.open_id = u2.username 
where rl.name_short = %s and ir.out_date is NOT NULL and (ir.out_date between %s and %s or ir.close_date BETWEEN %s and %s or ir.close_date is null)
group by ir.out_date, ir.close_date
ORDER by ir.date, ir.out_date , CASE WHEN ir.close_date IS NULL THEN 1 ELSE 0 END, close_date
    '''
    data = execute_query(conn, sql, (name_short,start_receive,end_receive,start_receive,end_receive))
    conn.close()

    return jsonify({'result': data})

@app.route("/total_print_detail2", methods=["POST"])
def total_print_detail2():
    conn = create_connection()
    start_receive = request.form['start']
    end_receive = request.form['end']
    name = request.form['name']
    name_short = request.form['name_short']
    sql = '''
    SELECT SUBSTRING(mr.in_date,1,10) as date, 
	   SUBSTRING(mr.exp_date,1,10) as exp_date, 
	   mr.lot, 
	   SUBSTRING(mr.date,1,10) as out_date,
	   SUBSTRING(mr.close_date,1,10) as close_date,
	   ir2.in_user as in_user,
	   u2.name as open_user,
	   mr.comment,
	   ir2.comment as reagent_comment,
	   ir2.name_short,ir2.total_ea,mr.quantity,
       (SELECT COUNT(*) 
    FROM in_reagent ir3
    left join REF_LIB rl3 on ir3.gtin = rl3.gtin
    WHERE mr.name = rl3.name and ((ir3.out_date is null or ir3.out_date >%s ) and (ir3.close_date > %s or ir3.close_date is null) and (ir3.date <%s))) AS remain
	   from make_reagent mr 
	   left join (
	   		select rl.name_short as name_short, u.username as in_user, ir.comment, ir.id,rl.total_ea
	   		from in_reagent ir
	   		left join REF_LIB rl on ir.gtin = rl.gtin
	   		left join `user` u on ir.in_id = u.username
	   ) ir2 on ir2.id = mr.reagent_id 
	   left join `user` u2 on mr.make_user = u2.username 
	   where ir2.name_short =%s and mr.date is not null and (mr.date between %s and %s or mr.close_date between %s and %s or (mr.close_date is null and mr.date < %s))
	   group by mr.date, mr.close_date 
	   order by mr.in_date, mr.date,  case when mr.close_date is null then 1 else 0 end, mr.close_date
    '''
    data = execute_query(conn, sql, (end_receive,end_receive,end_receive,name_short,start_receive,end_receive,start_receive,end_receive,end_receive))
    print(data)
    conn.close()

    return jsonify({'result': data})

@app.route("/total_print_in_detail", methods=["POST"])
def total_print_in_detail():
    conn = create_connection()
    start_receive = request.form['start']
    end_receive = request.form['end']
    name = request.form['name']
    name_short = request.form['name_short']
    
    sql = '''
    SELECT SUBSTRING(ir.date,1,10) as date, lot, SUBSTRING(ir.exp_date,1,10) as exp_date, count(*) as ea, u.name as in_user, ir.comment from in_reagent ir 
left join REF_LIB rl on ir.gtin = rl.gtin 
left join user u on ir.in_id  = u.username 
where rl.name_short = %s and (ir.date between %s and %s )
group by ir.date, rl.name, ir.lot
ORDER by ir.date, ir.out_date , CASE WHEN ir.close_date IS NULL THEN 1 ELSE 0 END, close_date
    '''
    data = execute_query(conn, sql, (name_short,start_receive,end_receive))
    conn.close()

    return jsonify({'result': data})

@app.route("/total_print_total", methods=["POST"])
def total_print_total():
    conn = create_connection()
    start_receive = request.form['start']
    end_receive = request.form['end']
    name = request.form['name']
    name_short = request.form['name_short']

    sql = '''
    SELECT CONCAT(rl.name, '_stat') AS stat, 
    SUBSTRING(ir.exp_date,1,10) as exp,
	(
		count(case when ir.out_date between %s and %s then 1 else NULL end)
		+count(CASE WHEN (ir.out_date is null or ir.out_date > %s) and ir.date <= %s THEN 1 ELSE NULL END)
		-count(case when ir.date between %s and %s then 1 else NULL end)
	) as early_month,
    count(case when ir.date between %s and %s then 1 else NULL end) as ea, 
    count(case when ir.out_date between %s and %s then 1 else NULL end) as used,
    count(case when ir.out_date is not null and ir.close_date is null then 1 else NULL end) as opened,
    COUNT(CASE WHEN (ir.out_date is null or ir.out_date > %s) and ir.date <= %s THEN 1 ELSE NULL END) as inventory
    FROM in_reagent ir 
    LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin
    Where rl.name_short = %s
    GROUP BY rl.name  ORDER BY rl.instrument, rl.code, rl.list, rl.name, ir.exp_date
    '''
    data = execute_query(conn, sql, (start_receive,end_receive,end_receive,end_receive,start_receive,end_receive,start_receive,end_receive,start_receive,end_receive,end_receive,end_receive,name_short))
    conn.close()
    print(data)

    return jsonify({'result': data})

@app.route("/total_print_total_month", methods=["POST"])
def total_print_total_month():
    conn = create_connection()
    start_receive = request.form['start']
    end_receive = request.form['end']
    instrument_receive = request.form['instrument']
    sql = '''
        SELECT rl.name,rl.code,
	(
		count(case when ir.out_date between %s and %s then 1 else NULL end)
		+count(CASE WHEN (ir.out_date is null or ir.out_date > %s) and ir.date <= %s THEN 1 ELSE NULL END)
		-count(case when ir.date between %s and %s then 1 else NULL end)
	) as early_month,
    count(case when ir.date between %s and %s then 1 else NULL end) as ea, 
    count(case when ir.out_date between %s and %s then 1 else NULL end) as used,
    count(case when ir.out_date is not null and ir.close_date is null then 1 else NULL end) as opened,
    COUNT(CASE WHEN (ir.out_date is null or ir.out_date > %s) and ir.date <= %s THEN 1 ELSE NULL END) as inventory,
    (rl.total_ea - (SELECT quantity 
        FROM in_reagent ir2 
        WHERE ir2.gtin = ir.gtin 
        AND ir2.close_date IS NULL 
        AND ir2.out_date IS NOT NULL limit 1)) as remain,
        (select count(*) from make_reagent mr where mr.name = rl.name and  mr.date between %s and %s ) as vial
    FROM in_reagent ir 
    LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin
    Where rl.instrument = %s
    GROUP BY rl.name  ORDER BY rl.instrument, rl.code desc, rl.list, rl.name, ir.exp_date
        '''
    data = execute_query(conn, sql,(start_receive,end_receive,end_receive,end_receive,start_receive,end_receive,start_receive,end_receive,start_receive,end_receive,end_receive,end_receive,start_receive,end_receive,instrument_receive))
    conn.close()
    return jsonify({'result': data})




if __name__ == '__main__':
   app.run('0.0.0.0', port=5001, debug=True)