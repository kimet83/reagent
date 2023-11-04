from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_session import Session
import pymysql
import host
import barcode2
from datetime import datetime, date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

global user_info

# conn = sqlite3.connect('reagent.db')
# cursor = conn.cursor()

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
scheduler = BackgroundScheduler()
scheduler.start()

app.static_url_path = '/static'
app.static_folder = 'static'

def template_exists(template_name):
    try:
        app.jinja_env.get_template(template_name)
        return True
    except Exception:
        return False

def monthly_task():
    # 매월 1일에 실행할 작업을 이곳에 추가하세요.
    print("매월 1일에 실행되는 작업입니다.")
    today = datetime.today()

    # 지난달의 마지막 날을 계산합니다.
    last_day_of_last_month = today - timedelta(days=today.day)

    # 지난달의 첫째 날을 계산합니다.
    first_day_of_last_month = last_day_of_last_month.replace(day=1)

    # 첫째 날과 마지막 날을 원하는 형식으로 출력합니다.
    start = first_day_of_last_month.strftime("%Y-%m-%d")
    end = last_day_of_last_month.strftime("%Y-%m-%d")

    print("지난달 첫째 날:", start)
    print("지난달 마지막 날:", end)

scheduler.add_job(monthly_task, 'cron', day='1', hour='0', minute='0')

#db 접속 함수
def create_connection():
    return pymysql.connect(**host.host)

def execute_query(connection, query, params=None):
    with connection.cursor(pymysql.cursors.DictCursor) as cursor:
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

# 장비리스트 전송
@app.route("/select", methods=["GET"])
def select():
    conn = create_connection()
    user=session['user_info']['username']
    sql='select distinct instrument from instrument i'
    data = execute_query(conn,sql)
    sql='select username, name from user where username != %s'
    data2 = execute_query(conn,sql,user)
    conn.close()
    return jsonify({'instrument':data,'user':data2})

#로그인 시스템
@app.route('/', methods=['GET','POST'])
def home():
    conn = create_connection()
    sql = 'select * from user'
    users = execute_query(conn,sql)
    conn.close()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        for user in users:
            if user['username'] == username and user['password'] == password:
                user_info = user
                del user_info['password']
                session['user_info'] = user_info
                print(user_info)
                return redirect(url_for('index'))  # 로그인 성공 시 대시보드 페이지로 이동
    
    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    print(session)
    if 'user_info' in session:
        # 세션에서 사용자 정보 제거
        session.pop('user_info', None)
        print(session)
    return redirect(url_for('home'))



    
@app.route('/change', methods=['POST'])
def change():
    username = request.form['username']
    conn = create_connection()
    sql = 'select * from user where username = %s'
    users = execute_query(conn,sql,username)
    conn.close()
    user_info=users[0]
    del user_info['password']
    session['user_info'] = user_info
    return jsonify({'msg': '입력완료'})


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
@app.route("/barcode", methods=["POST"])
def inreagent():
    conn = create_connection()
    barcode_receive = request.form['barcode_give']
    # type_receive = request.form['type_give']
    print(barcode_receive)
    ref, lot, exp, gtin = barcode2.analyze_barcode(barcode_receive) #barcode analysis
    print(ref, lot, exp, gtin)
    exp = format_date(exp)
    sql = 'select * from REF_LIB where gtin= %s limit 1' #등록 항목 확인 process
    data = execute_query(conn,sql,gtin)
    print(exp)
    conn.close()
    barcode = {'gtin':gtin,'lot': lot, 'exp': exp, 'ref': ref}
    return jsonify({'info':data,'barcode':barcode})

# 시약 코멘트 확인;index.html
@app.route('/comment', methods=["POST"])
def comment():
    conn = create_connection()
    id = request.form['id']
    sql = 'select id,comment,lot from in_reagent where id=%s'
    data=execute_query(conn,sql,id)
    conn.close()
    
    return jsonify({'result': data})

# 시약 코멘트 저장; index.html
@app.route('/comment_save', methods=["POST"])
def comment_save():
    conn = create_connection()
    id = request.form['id']
    comment = request.form['comment']
    if comment =="":
        sql = 'update in_reagent set comment = null where id=%s'
        execute_query(conn,sql,id)
    else:
        sql = 'update in_reagent set comment = %s where id=%s'
        execute_query(conn,sql,(comment,id))
    conn.commit()
    conn.close()
    return jsonify({'msg': '입력완료'})

# 시약입고
@app.route("/save", methods=["POST"])
def save():
    conn = create_connection()
    date_receive = request.form['date_give']
    gtin_receive = request.form['gtin_give']
    exp_receive = request.form['exp_give']
    lot_receive = request.form['lot_give']
    ea_receive =  int(request.form['ea_give'])
    name_receive = request.form['name_give']
    instrument_receive = request.form['instrument_give']
    code_receive = request.form['code_give']
    temp_receive = request.form['temp_give']
    volume_receive = request.form['volume_give']
    total_ea_receive = request.form['total_ea_give']
    onboard_reeive = request.form['onboard_give']
    ref = request.form['ref']
    username = request.form['username']
    comment = request.form['comment']
    # print("volume", volume_receive)
    print(exp_receive)
    i = 0
    while i < ea_receive: #ea 만큼 해당 시약을 입고
        if comment == "":
            sql = 'insert into in_reagent (date, gtin, exp_date, lot, ref,in_id) values (%s, %s, %s, %s, %s,%s)'
            execute_query(conn,sql,(date_receive,gtin_receive,exp_receive,lot_receive,ref,username))
        else:

            sql = 'insert into in_reagent (date, gtin, exp_date, lot, ref,in_id,comment) values (%s, %s, %s, %s, %s,%s,%s)'
            execute_query(conn,sql,(date_receive,gtin_receive,exp_receive,lot_receive,ref,username,comment))
        i += 1
        conn.commit()

    sql = 'select * from REF_LIB where gtin = %s limit 1' #라이브러리에 데이터 유무 확인
    data = execute_query(conn,sql,gtin_receive)
    if not data: #데이터가 없을경우
        sql="INSERT  INTO REF_LIB (gtin, name, instrument, code, temp, volume, total_ea, onboard, ref) VALUES (%s,%s, %s, %s, %s, %s, %s, %s,%s) "
        execute_query(conn,sql,(gtin_receive,name_receive,instrument_receive,code_receive,temp_receive,volume_receive,total_ea_receive,onboard_reeive,ref))
    else :
        sql='update REF_LIB set name = %s, instrument = %s, code = %s, temp = %s, volume = %s, total_ea = %s, onboard = %s, ref = %s where gtin = %s'
        execute_query(conn,sql,(name_receive,instrument_receive,code_receive,temp_receive,volume_receive,total_ea_receive,onboard_reeive,ref,gtin_receive))
    conn.commit()
    conn.close()
    return jsonify({'msg': '입력완료'})

@app.route("/save_m", methods=["POST"])
def save_m():
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
    return jsonify({'msg': '입력완료'})


# 선택 삭제;index.html
@app.route("/del", methods=["POST"])
def del_post():
    conn = create_connection()
    id = request.form['del_give']
    # print(id)
    sql = 'DELETE FROM in_reagent WHERE id= %s'
    execute_query(conn,sql,id)
    conn.commit()
    conn.close()
    return jsonify({'msg': '삭제 완료!'})

# 출고바코드
@app.route("/out_barcode", methods=["POST"])
def out_barcode():
    conn = create_connection()
    out_date = request.form['date_give']
    barcode_receive = request.form['barcode_give']
    username=request.form['username']
    if barcode_receive=='0':
        gtin = request.form['gtin']
        lot = request.form['lot']
    else:
    # type_receive = request.form['type_give']
        ref, lot, exp, gtin = barcode2.analyze_barcode(barcode_receive) #barcode analysis
    # print(ref, lot, exp, gtin)
    sql = 'select total_ea, onboard from REF_LIB where gtin= %s limit 1' # 해당시약의 포장단위를 조회
    data = execute_query(conn,sql,gtin)
    data = data[0]
    # print(data)
    total_ea = data['total_ea']
    onboard = data['onboard']
    sql = 'select count(*) as onboarding from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where ir.gtin = %s and out_date is not NULL and close_date is NULL group by ir.gtin limit 1' #out_date is not NULL and close_date is NULL = Opened reagent
    data = execute_query(conn,sql,gtin)
    # print(data)
    
    if not data: #Opened reagent is NULL
        onboarding = 0
    else:
        data = data[0]
        onboarding = data['onboarding'] 
    # print(gtin,lot,out_date,total_ea, onboard, onboarding)
    
# 시약이 오픈된 시약이 한도보다 적을경우(1), 시약이 오픈된 시약이 한도와 같은 경우(2)
# 시약 오픈시 out_date만 기입, 추가오픈시 quantity +
# quantity = total_ea, close_date 기입
    if onboarding == onboard: #장착 최소한도보다 개봉 시약이 같을 경우
        sql = 'update in_reagent set close_date = %s, quantity= %s where gtin = %s  and out_date is not NULL and close_date is NULL order by date limit 1' #기존 오픈된 시약 중 오픈일 기입된 시약을 종료일 입력
        execute_query(conn,sql,(out_date,total_ea,gtin))
        conn.commit()
        sql = 'update in_reagent set out_date = %s, open_id = %s,quantity = 1 where gtin= %s and lot = %s and out_date is NULL order by date limit 1' #오픈되지 않은 시약을 한개 찾아 오픈일만 기입 process 1
        execute_query(conn,sql,(out_date, username, gtin, lot))
        conn.commit()
        print("1-1")
    else:
        sql = 'update in_reagent set out_date = %s, open_id = %s, quantity= 1 where gtin= %s and lot = %s  and out_date is NULL order by date limit 1' #오픈되지 않은 시약을 한개 찾아 오픈일만 기입 process 1
        execute_query(conn,sql,(out_date, username, gtin, lot))
        conn.commit()
        print("1-2")

    conn.close()
    return jsonify({'msg': '입력 완료!'})



@app.route("/add", methods=["POST"])
def add_post():
    conn = create_connection()
    id = request.form['id']
    out_date = request.form['out_date']
    sql= 'select quantity, total_ea from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where id= %s limit 1'
    data = execute_query(conn,sql,id)
    data=data[0]
    # print(data)
    quantity = data['quantity']
    # total_ea = data['total_ea']
    quantity = quantity + 1
    # print(quantity,total_ea)
    # if quantity == total_ea:
    #     sql = 'UPDATE in_reagent set quantity= %s, close_date = %s WHERE id= %s'
    #     execute_query(conn,sql,(quantity,out_date,id))
    #     conn.commit()
    # else:
    sql = 'UPDATE in_reagent set quantity= %s WHERE id= %s'
    execute_query(conn,sql,(quantity,id))
    conn.commit()
    conn.close()    
    return jsonify({'msg': '삭제 완료!'})

@app.route("/cancel", methods=["POST"])
def cancle_post():
    conn = create_connection()
    id = request.form['id']
    sql= 'select quantity from in_reagent where id= %s limit 1'
    data = execute_query(conn,sql,id)
    data=data[0]
    # print(data)
    quantity = data['quantity']
    quantity = quantity - 1
    # print(quantity)
    if quantity == 0 :
        sql = 'UPDATE in_reagent set quantity= 0, close_date = NULL WHERE id= %s'
        execute_query(conn,sql,(id))
        conn.commit()
    elif quantity < 0:
        sql = 'UPDATE in_reagent set quantity=0, out_date = NULL, close_date = NULL, open_id = NULL WHERE id= %s'
        execute_query(conn,sql,id)
        conn.commit()
    else:
        sql = 'UPDATE in_reagent set quantity= %s, close_date = NULL WHERE id= %s'
        execute_query(conn,sql,(quantity,id))
        conn.commit()
    conn.close()
    return jsonify({'msg': '삭제 완료!'})


@app.route("/out_search", methods=["POST"])
def out_search():
    conn = create_connection()
    start_receive = request.form['start_give']
    end_receive = request.form['end_give']
    code_receive = request.form['code_give']
    instrument_receive = request.form['instrument_give']
    gtin = request.form['gtin']
    print(start_receive, end_receive, instrument_receive, code_receive)

    # Initialize the base SQL query.
    sql = '''
    SELECT ir.id, SUBSTRING(ir.date,1,10) as date, rl.name, lot, SUBSTRING(ir.exp_date,1,10) as exp, ir.ref, rl.code, 
    SUBSTRING(ir.out_date,1,10) as out_date, SUBSTRING(ir.close_date,1,10) as close_date, quantity, rl.instrument, 
    rl.temp, CASE WHEN ir.exp_date < CURDATE() THEN "expired" ELSE "usable" END AS status, 
    CASE WHEN out_date is not NULL AND close_date is NULL THEN "using" 
    WHEN out_date is NULL THEN "not open" 
    WHEN close_date is not NULL THEN "used" END AS kit_status, u.name as in_user, u2.name as open_user, ir.comment 
    FROM in_reagent ir 
    LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin 
    LEFT JOIN `user` u ON ir.in_id = u.username 
    LEFT JOIN user u2 ON ir.open_id = u2.username 
    WHERE ir.out_date IS NOT NULL AND (
    (ir.out_date BETWEEN %s AND %s OR ir.close_date BETWEEN %s AND %s) '''

    params = [start_receive, end_receive, start_receive, end_receive]

    if gtin != 'all':
        sql += 'AND ir.gtin = %s '
        params.append(gtin)

    if instrument_receive != 'all':
        sql += 'AND rl.instrument = %s '
        params.append(instrument_receive)

    if code_receive != 'all':
        sql += 'AND rl.code = %s '
        params.append(code_receive)

    sql += ') ORDER BY rl.name, date, out_date, CASE WHEN close_date IS NULL THEN 1 ELSE 0 END, close_date'

    data = execute_query(conn, sql, tuple(params))
    conn.close()
    return jsonify({'result': data})

    
@app.route("/instrument_select", methods=["POST"])
def instrument_select():    
    conn = create_connection()
    instrument_select = request.form['instrument_select']
    code_select = request.form['code_manual_search']
    print(instrument_select,code_select)
    if code_select=='all':
        sql = 'SELECT name, ir.gtin from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where rl.instrument = %s  group by name'
        data = execute_query(conn,sql,instrument_select)
    
    else:
        sql = 'SELECT name, ir.gtin from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where rl.instrument = %s and rl.code = %s  group by name'
        data = execute_query(conn,sql,(instrument_select,code_select))
    conn.close()
    print(data)
    return jsonify({'result':data})
    
@app.route("/reagent_select", methods=["POST"])
def reagent_select():
    conn = create_connection()
    instrument_select = request.form['instrument_select']
    reagent_select = request.form['gtin']
    # print(instrument_select,reagent_select)
    sql = 'select name, lot, ir.gtin from in_reagent ir left join REF_LIB rl on ir.gtin = rl.gtin where ir.out_date is null and instrument = %s and ir.gtin = %s group by name, lot'
    data = execute_query(conn,sql,(instrument_select,reagent_select))
    conn.close()
    return jsonify({'result':data})

@app.route("/instrument_select_in", methods=["POST"])
def instrument_select_in():    
    conn = create_connection()
    instrument_select = request.form['instrument_select']
    code_select = request.form['code_manual_search']
    print(instrument_select,code_select)
    if code_select=='all':
        sql = 'SELECT name, gtin from REF_LIB where instrument = %s and gtin is not NULL order by instrument, name, code'
        data = execute_query(conn,sql,instrument_select)
    
    else:
        sql = 'SELECT name, gtin from REF_LIB where instrument = %s and code = %s and gtin is not NULL order by name'
        data = execute_query(conn,sql,(instrument_select,code_select))
    conn.close()
    print(data)
    return jsonify({'result':data})



#입고 기간 검색;index.html
@app.route("/search", methods=["POST"])
def search1():
    conn = create_connection()
    start_receive = request.form['start_give']
    end_receive = request.form['end_give']
    instrument_receive = request.form['instrument_give']
    code_receive = request.form['code_give']
    gtin = request.form['gtin']
    
    sql_base = '''
        SELECT ir.id, SUBSTRING(ir.date,1,10) as date, rl.name, lot, SUBSTRING(ir.exp_date,1,10) as exp, ir.ref, rl.code,
        SUBSTRING(ir.out_date,1,10) as out_date, quantity, rl.instrument, rl.temp,
        CASE WHEN ir.exp_date < CURDATE() THEN "expired" ELSE "usable" END AS status,
        CASE WHEN out_date is not NULL AND close_date is NULL THEN "using"
             WHEN out_date is NULL THEN "not open"
             WHEN close_date is not NULL THEN "used" END AS kit_status,
        u.name as in_user, u2.name as open_user, ir.comment
        FROM in_reagent ir
        LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin
        LEFT JOIN `user` u ON ir.in_id = u.username
        LEFT JOIN `user` u2 ON ir.open_id = u2.username
        WHERE ir.date BETWEEN %s AND %s
    '''

    conditions = []
    params = [start_receive, end_receive]

    if gtin != 'all':
        conditions.append('rl.gtin = %s')
        params.append(gtin)
    
    if instrument_receive != 'all':
        conditions.append('rl.instrument = %s')
        params.append(instrument_receive)
    
    if code_receive != 'all':
        conditions.append('rl.code = %s')
        params.append(code_receive)
    
    if conditions:
        sql = f"{sql_base} AND {' AND '.join(conditions)} ORDER BY date DESC, rl.list, name, CASE WHEN out_date IS NULL THEN 1 ELSE 0 END, out_date"
    else:
        sql = f"{sql_base} ORDER BY date DESC, rl.list, name, CASE WHEN out_date IS NULL THEN 1 ELSE 0 END, out_date"
    
    data = execute_query(conn, sql, tuple(params))
    conn.close()
    
    return jsonify({'result': data})


@app.route("/search2", methods=["POST"])
def search2():
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
    WHEN close_date is not NULL THEN "used" END AS kit_status, u.name as in_user, u2.name as open_user, ir.comment 
    FROM in_reagent ir 
    LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin 
    LEFT JOIN `user` u ON ir.in_id = u.username 
    LEFT JOIN user u2 ON ir.open_id = u2.username 
    WHERE ir.out_date IS NOT NULL AND ir.quantity < rl.total_ea AND rl.total_ea > 1 '''

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


#입고 통계 검색;total.html
@app.route("/total_count", methods=["POST"])
def total_count():
    conn = create_connection()
    start_receive = request.form['start_give']
    end_receive = request.form['end_give']
    instrument_receive = request.form['instrument_give']
    code_receive = request.form['code_give']
    gtin = request.form['gtin']

    sql_base = '''
        SELECT ir.gtin, SUBSTRING(ir.date,1,10) as date, rl.name, ir.lot, SUBSTRING(ir.exp_date,1,10) as exp,
        count(case when ir.date between %s and %s then 1 else NULL end) as ea, 
        count(case when ir.out_date between %s and %s then 1 else NULL end) as used,
        rl.instrument, rl.code, COUNT(CASE WHEN ir.out_date is NULL THEN 1 ELSE NULL END) as inventory
        FROM in_reagent ir 
        LEFT JOIN REF_LIB rl ON ir.gtin = rl.gtin
    '''

    conditions = []
    params = [start_receive, end_receive, start_receive, end_receive]

    if gtin != 'all':
        conditions.append('rl.gtin = %s')
        params.append(gtin)

    if instrument_receive != 'all':
        conditions.append('rl.instrument = %s')
        params.append(instrument_receive)

    if code_receive != 'all':
        conditions.append('rl.code = %s')
        params.append(code_receive)

    if conditions:
        sql = f"{sql_base} WHERE {' AND '.join(conditions)} GROUP BY ir.lot HAVING inventory != 0 OR ea != 0 OR used != 0 ORDER BY rl.instrument, rl.code, rl.list, ir.exp_date"
    else:
        sql = f"{sql_base} GROUP BY ir.lot HAVING inventory != 0 OR ea != 0 OR used != 0 ORDER BY rl.instrument, rl.code, rl.list, ir.exp_date"

    data = execute_query(conn, sql, tuple(params))
    conn.close()

    return jsonify({'result': data})

@app.route("/reg_search", methods=["POST"])
def reg_search():
    conn = create_connection()
    instrument_receive = request.form['instrument_give']
    code_receive = request.form['code_give']
    gtin = request.form['gtin']
    
    sql_base = '''
        SELECT *
        FROM REF_LIB rl
        WHERE gtin is not NULL
    '''

    conditions = []
    params = []

    if gtin != 'all':
        conditions.append('gtin = %s')
        params.append(gtin)
    
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

@app.route("/reg_barcode", methods=["POST"])
def reg_barcode():
    conn = create_connection()
    gtin = request.form['gtin']
    sql = 'select * from REF_LIB where gtin= %s ' #등록 항목 확인 process
    data = execute_query(conn,sql,gtin)
    # print(data)
    conn.close()
    # if not data: # 라이브러리에 데이터가 없는 경우
    #     data={}
    # else: # 라이브러리에 데이터 존재
    #     print(data)
    # data[0]['gtin']=gtin
    # print(data)
    return jsonify(data)

@app.route("/edit", methods=["POST"])
def edit():
    conn = create_connection()
    gtin_receive = request.form['gtin_give']
    name_receive = request.form['name_give']
    instrument_receive = request.form['instrument_give']
    code_receive = request.form['code_give']
    temp_receive = request.form['temp_give']
    volume_receive = request.form['volume_give']
    total_ea_receive = request.form['total_ea_give']
    onboard_reeive = request.form['onboard_give']
    mode = request.form['mode']

    if mode == 'r':
        sql="INSERT  INTO REF_LIB (gtin, name, instrument, code, temp, volume, total_ea, onboard) VALUES (%s,%s, %s, %s, %s, %s, %s, %s) "
        execute_query(conn,sql,(gtin_receive,name_receive,instrument_receive,code_receive,temp_receive,volume_receive,total_ea_receive,onboard_reeive))
        
    else :
        sql='update REF_LIB set name = %s, instrument = %s, code = %s, temp = %s, volume = %s, total_ea = %s, onboard = %s where gtin = %s'
        execute_query(conn,sql,(name_receive,instrument_receive,code_receive,temp_receive,volume_receive,total_ea_receive,onboard_reeive,gtin_receive))
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





if __name__ == '__main__':
   app.run('0.0.0.0', port=5001, debug=True)
