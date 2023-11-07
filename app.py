from flask import Flask, render_template, request, redirect, url_for, session

from flask_wtf import FlaskForm
from wtforms.fields import DateField,StringField,SelectField
from wtforms.validators import DataRequired
from wtforms import validators, SubmitField,widgets, SelectMultipleField
from wtforms_components import TimeField
from datetime import datetime, timedelta, date
import time

from werkzeug.utils import secure_filename
import pymysql
pymysql.install_as_MySQLdb()
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import os
from constants import *

app = Flask(__name__)

app.secret_key = 'AKKKM'

# Enter your database connection details below
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'telemedicine'

# Intialize MySQL
mysql = MySQL(app)


@app.route('/login/', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        print(username)
        print(password)

        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = %s AND password = %s', (username, password,))
        
        # Fetch one record and return result
        account = cursor.fetchone()
        print(account)
        if account:
            session['loggedin'] = True
            session['id'] = account['User_ID']
            session['username'] = account['Username']

            # Redirect to doctor patient or admin home page
            if DOC in session['id']:
                # Doctor must be approved before logging in 
                cursor.execute('Select Approved from doctor where Doctor_ID = %s', account['User_ID'])
                records = cursor.fetchone()

                if records is not None:
                    approved_status = int(records[Approved])
                    if approved_status:
                        return redirect(url_for('doc_home'))
                return render_template('index.html', msg = "Approval not yet received!")
            elif PAT in session['id']:
                return redirect(url_for('pat_home'))
            elif ADMIN in session['id']:
                return redirect(url_for('admin_home'))
            else: 
                return render_template('index.html')

        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'
    # Show the login form with message (if any)
    return render_template('index.html', msg=msg)

@app.route('/login/logout')
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop('id', None)
   session.pop('username', None)
   # Redirect to login page
   return redirect(url_for('login'))

@app.route('/login/register', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong...
    msg = ''
    # Check if "username", "password" and "email" POST requests exist (user submitted form)
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form:
        # Create variables for easy access
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        fname = request.form['fname']
        lname =  request.form['lname']
        phonenumber =  request.form['phonenumber']
        address =  request.form['address']
        state =  request.form['state']
        city = request.form['city']
        ssn =  request.form['ssn']
        usertype =  request.form['usertype']
        gender = request.form['gender']
        dob = request.form['dob']

        # Check if account exists using MySQL
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE Username = %s', (username,))
        account = cursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers!'
        # elif not username or not password or not email:
        #     msg = 'Please fill out the form!'
        else:
            if usertype == doctor:
                specialization =  request.form['specialization']
                cursor.execute("SELECT user_id FROM telemedicine.accounts where User_ID like 'DOC%' ORDER BY user_id  DESC LIMIT 1;")
                records = cursor.fetchall()
                if records is None:
                    user_ID = DOC + "_1"
                else:
                    last_doctor_id = records[0]['user_id']
                    last_doctor_id_count = int(last_doctor_id.split('_')[1])
                    user_ID = DOC + '_' + str(last_doctor_id_count + 1 )
                address += " "+ state + " " + city
                cursor.execute('INSERT INTO accounts VALUES(%s, %s, %s)', (user_ID, username, password))
                cursor.execute('INSERT INTO doctor VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', 
                                (user_ID, ssn, fname, lname, dob, gender, phonenumber, address, specialization, 0))
                mysql.connection.commit()
                msg = 'You have successfully registered!'
                
            elif usertype == patient :
                cursor.execute("SELECT user_id FROM telemedicine.accounts where User_ID like 'PAT%' ORDER BY user_id  DESC LIMIT 1;")
                records = cursor.fetchall()

                # if its the first patient
                if records is None:
                    user_ID = PAT + "_1"
                else:
                    last_patient_id = records[0]['user_id']
                    last_patient_id_count = int(last_patient_id.split('_')[1])
                    user_ID = PAT + '_' + str(last_patient_id_count + 1 )
                address += " "+ state + " " + city
                cursor.execute('INSERT INTO accounts VALUES(%s, %s, %s)', (user_ID, username, password))
                cursor.execute('INSERT INTO patient VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', 
                                (user_ID, ssn, fname, lname, dob, gender, phonenumber, address))
                mysql.connection.commit()
                msg = 'You have successfully registered!'
    
    elif request.method == 'POST':
        msg = 'Please fill out the form!'


    return render_template('register.html', msg=msg)

def date_change(records):
    print(records)
    res = {}
    for i in records:
        day,month,year = i['DTime'].day,i['DTime'].month, i['DTime'].year
        if ((day,month,year) in res.keys()):
            res[(day,month,year)].append(i)
        else:
            res[(day,month,year)]=[i]
    #print(res)
    return res

def merge_record(records,pat_records):
    res = []
    for i in records:
        i['Medical_records']=[]
        for j in pat_records:
            if i['Patient_ID'] == j['Patient_ID']:
                i['Medical_records'].append(j['Medical_records'])
        res.append(i)
    return res

@app.route('/login/doc_home')
def doc_home():
    if 'loggedin' in session:
        # Doctor home page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE User_ID = %s', (session['id'],))
        account = cursor.fetchone()
        #cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT a.Appointment_ID, p.Fname , p.Lname,p.Patient_ID , s.Services, a.DTime ,a.Status FROM appointments as a, patient as p, services as s WHERE a.Patient_ID = p.Patient_ID AND a.Service_ID=s.Service_ID AND a.Status = 1 AND a.Doctor_ID= %s;",(account['User_ID']))
        records = cursor.fetchall()
        cursor.execute("Select * from patient_records;")
        pat_records = cursor.fetchall()
        #print(pat_records)
        #print(records)
        #x = [ i['DTime'].day for i in records]
        #print(x)
        merge_records = merge_record(records,pat_records)
        x = date_change(merge_records)
        #print(merge_records)
        return render_template('doc_home.html', username=session['username'], doc_app_records = x, date = x.keys())
    
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/login/profile')
def profile():
    # Check if user is loggedin
    if 'loggedin' in session:
        # We need all the account info for the user so we can display it on the profile page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE id = %s', (session['id'],))
        account = cursor.fetchone()
        # Show the profile page with account info
        return render_template('profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))

@app.route('/login/admin_home')
def admin_home():
    if 'loggedin' in session:
        # Admin home page display the doctor details
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM telemedicine.doctor;")
        records = cursor.fetchall()
        return render_template('admin_home.html', username=session['username'], doctor_records = records)
    
    return redirect(url_for('login'))

@app.route('/login/pat_home')
def pat_home():
    if 'loggedin' in session: 
        return render_template('pat_home.html', username=session['username'])

    return redirect(url_for('login')) 

@app.route('/login/pat_records')
def patient_records():
    if 'loggedin' in session: 
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM telemedicine.patient_records WHERE Patient_ID = %s;", session['id'])
        records = cursor.fetchall()
        return render_template('pat_records.html', username=session['username'], med_records = records)

    return redirect(url_for('login')) 

@app.route('/login/pat_info')
def patient_info():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        print(session['id'])
        cursor.execute("SELECT * FROM telemedicine.patient WHERE Patient_ID = %s;" , session['id'])
        pat_info = cursor.fetchone()
        return render_template('pat_info.html', username=session['username'], pat_info = pat_info)
    
    return redirect(url_for('login'))

@app.route('/login/uploader', methods=['GET', 'POST'])
def upload_records():
    if 'loggedin' in session: 
        if request.method == 'POST':
            f = request.files['file']
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            f.save(os.path.join("uploads_dir", secure_filename(f.filename)))
            medical_records = "uploads_dir/"+f.filename
            cursor.execute('INSERT INTO patient_records VALUES(%s, %s)', (session['id'], medical_records))
            mysql.connection.commit()
            cursor.execute("SELECT * FROM telemedicine.patient_records WHERE Patient_ID = %s;", session['id'])
            records = cursor.fetchall()
            return render_template('pat_records.html',  med_records = records)

    return redirect(url_for('login')) 


@app.route('/login/admin_profile')
def admin_profile():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE User_ID = %s', (session['id'],))
        account = cursor.fetchone()
        return render_template('admin_profile.html', account=account)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/login/admin_appointments')
def admin_appointments():
    return render_template('admin_home.html')

@app.route('/login/admin_services')
def admin_services():
    if 'loggedin' in session:
        # Admin service page
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM telemedicine.services;")
        records = cursor.fetchall()
    return render_template('admin_services.html', username=session['username'], services = records)


@app.route('/login/add_service', methods=['GET', 'POST'])
def add_service():
    msg = 'Not able to add'
    if request.method == 'POST':
        service_id = request.form['service_id']
        service_name = request.form['service_name']
        cost = request.form['cost']
       
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM services WHERE Service_ID = %s', (service_id,))
        existing_service = cursor.fetchone()
        
        # If service exists 
        if existing_service:
            msg = 'Service already exists!'
        else:
            cursor.execute('INSERT INTO Services VALUES(%s, %s, %s)', (service_id, service_name, cost))
            mysql.connection.commit()
            msg = 'You have successfully added a Service!'
    
    elif request.method == 'POST':
        msg = 'Please fill out the form!'

    return render_template('admin_add_services.html', msg=msg)

@app.route("/login/edit_doc/<string:doctor_id>", methods = ['GET', 'POST'])
def edit_doctor(doctor_id):
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM doctor WHERE Doctor_ID = %s', (doctor_id,))
        record = cursor.fetchone()
    
    return render_template('admin_edit_doctor.html', doc_details = record)

@app.route("/login/approve/<string:doctor_id>", methods = ['GET', 'POST'])
def approve_doc(doctor_id):
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE doctor SET Approved = 1 WHERE Doctor_ID = %s', (doctor_id))
        print("cursor", cursor.rowcount)
        mysql.connection.commit()
        if cursor.rowcount == 1:
            msg = "Successfully Approved " + str(doctor_id)
            
        else:
            msg = "Not able to approve " + str(doctor_id)    
    return redirect(url_for('admin_home'))

@app.route('/login/doc_appointments')
def doc_appointments():
    if 'loggedin' in session:
        # Admin home page display the doctor details
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE User_ID = %s', (session['id'],))
        account = cursor.fetchone()
        #cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT a.Appointment_ID, p.Fname , p.Lname , s.Services, a.DTime ,a.Status FROM appointments as a, patient as p, services as s WHERE a.Patient_ID = p.Patient_ID AND a.Service_ID=s.Service_ID AND a.Doctor_ID= %s;",(account['User_ID']))
        records = cursor.fetchall()
        return render_template('doc_appointments.html', username=session['username'], doc_app_records = records)

    return redirect(url_for('login'))

@app.route("/login/approve_appointment/<string:appointment_id>", methods = ['GET', 'POST'])
def approve_appointment(appointment_id):
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE appointments SET Status = 1 WHERE Appointment_ID = %s', (appointment_id))
        print("cursor", cursor.rowcount)
        print(appointment_id)
        mysql.connection.commit()
        if cursor.rowcount == 1:
            msg = "Successfully Approved " + str(appointment_id)
            
        else:
            msg = "Not able to approve " + str(appointment_id)    
    return redirect(url_for('doc_appointments'))

@app.route("/login/payments", methods=['GET'])
def payments():
    if 'loggedin' in session:
        print("payments")
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE User_ID = %s', (session['id'],))
        account = cursor.fetchone()
        #cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT pay.Transaction_ID, p.Fname , p.Lname ,s.Services, pay.Amount, pay.Date, pay.Status FROM appointments as a, payments as pay, services as s , patient as p WHERE pay.Appointment_ID = a.Appointment_ID AND a.Service_ID = s.Service_ID AND a.Patient_ID=p.Patient_ID AND a.Doctor_ID = %s AND a.Status=1;",(account['User_ID']))
        records = cursor.fetchall()
        return render_template('payments.html', username=session['username'],payment_list=records)
    return redirect(url_for('login'))

class InfoForm(FlaskForm):
    startdate = DateField('Start Date', format='%Y-%m-%d', validators=(validators.DataRequired(),))
    starttime = TimeField('From_Time')
    #date = DateField('Start Date', format='%Y-%m-%d', validators=(validators.DataRequired(),))
    endtime = TimeField('To_Time')
    #enddate = DateField('End Date', format='%Y-%m-%d', validators=(validators.DataRequired(),))
    submit = SubmitField('Submit')

def time_plus(origin,end):
    available_times = []
    while(origin < end):
        origin = origin + timedelta(minutes=30)
        available_times.append(origin.time())
    return available_times

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class SimpleForm(FlaskForm):
    example = MultiCheckboxField('label', coerce=int,
                               choices=[],
                               validators=[])
    submit = SubmitField('Submit')
    # example = RadioField('Label')

@app.route("/login/availibility", methods=['GET','POST'])
def doc_availibility():
    if 'loggedin' in session:
        print("availibility")
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE User_ID = %s', (session['id'],))
        account = cursor.fetchone()
        #cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("Select da.Availability_from, da.Availability_to, d.Fname, d.Lname From doctor as d, doctor_availability as da Where da.Doctor_ID = d.Doctor_ID AND d.Doctor_ID=%s;",(account['User_ID']))
        records = cursor.fetchall()
        avail_times = []
        form = InfoForm()
        sf = SimpleForm()
        if form.validate_on_submit():
            SD = form.startdate.data
            ST = form.starttime.data
            ET = form.endtime.data
            origin =datetime.combine(SD, ST)
            end = datetime.combine(SD,ET)
            print(origin,end)
            cursor1 = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor1.execute('INSERT INTO doctor_availability VALUES(%s, %s, %s)', (session['id'], origin.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S')))
            mysql.connection.commit()
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM accounts WHERE User_ID = %s', (session['id'],))
            account = cursor.fetchone()
            #cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute("Select da.Availability_from, da.Availability_to, d.Fname, d.Lname From doctor as d, doctor_availability as da Where da.Doctor_ID = d.Doctor_ID AND d.Doctor_ID=%s;",(account['User_ID']))
            records = cursor.fetchall()
            #avail_times.append(time_plus(origin) )
        
            #avail_times.append(x)
            '''
        if(avail_times and sf.validate_on_submit()):
            #print(avail_times[])
            sf.example.choices = [(i,x) for i,x in enumerate(avail_times[0])]

            if sf.validate_on_submit():
                    print( sf.example.data )'''
        return render_template('doc_availibility.html', username=session['username'],list = records, form=form, t = avail_times, sf=sf)
    

    return redirect(url_for('login'))

class Pat_APP(FlaskForm):
    docfname = SelectField('Doctor Name', validators=(validators.DataRequired(),))
    # doclname = StringField('Doctor Last Name', validators=(validators.DataRequired(),))
    services = SelectField('Services', validators=(validators.DataRequired(),))
    startdate = DateField('Start Date', format='%Y-%m-%d', validators=(validators.DataRequired(),))
    submit = SubmitField('Submit')

class APT_Time(FlaskForm):
    apttime = SelectField('Select Appointment Time', validators=(validators.DataRequired(),))
    submit = SubmitField('Submit')

# @app.route('/login/pat_apts', methods = ['GET','POST'])
# def select_aptDets():
    # if 'loggedin' in session: 
    #     cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #     print(session['id'])
    #     #cursor.execute("Select * from telemedicine.doctor;")
    #     #doctors = cursor.fetchall()
    #     #print(doctors)

        
    #     # cursor.execute("SELECT * FROM telemedicine.services;")
    #     # services = cursor.fetchall()
    #     # cursor.execute("SELECT Doctor_ID FROM telemedicine.doctor WHERE Fname = %s AND Lname = %s;",(x[0], x[1]))
    #     # doc_id = cursor.fetchone()
    #     # cursor.execute("SELECT * FROM telemedicine.doctor_availability WHERE Doctor_ID = %s;",doc_id['Doctor_ID'])
    #     # avail_records = cursor.fetchall()
    #     # x = [i['Availability_from'] for i in avail_records]
    #     # dates = []
    #     # y = [i['Availability_to'] for i in avail_records]
    #     # times = []
        

    #     #avail_times = time_plus()
    #     # for date in x :
    #     #     dates.append(date.strftime('%m/%d/%Y %I:%m%p'))
    #     return render_template('pat_aptdets.html',doctors = doctor)

@app.route('/login/apt_submit', methods = ['GET','POST'])
def pat_date():
    if 'loggedin' in session: 
        if request.method == 'POST':
            docfname = request.form['docfname']
            doclname = request.form['doclname']
            service = request.form['service']
            date = request.form['date']
            times = request.form['at_times']
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM services WHERE Services = %s;',service)
            service_id = cursor.fetchone() 
            print(service_id['Service_ID'])
            cursor.execute('SELECT * FROM doctor WHERE Fname = %s AND Lname = %s;',(docfname, doclname))
            doctor_id = cursor.fetchone() 
            print(doctor_id['Doctor_ID'])
            print("***********")
            cursor.execute('SELECT * FROM appointments;')
            apts = cursor.fetchall()
            print(int(apts[-1]['Appointment_ID']) + 1)
            apt_id = (int(apts[-1]['Appointment_ID']) + 1)
            da = datetime.combine(datetime.strptime(date, '%Y-%m-%d').date(), datetime.strptime(times, '%H:%M:%S').time())
            print(da)
            cursor1 = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor1.execute('INSERT INTO appointments VALUES(%s, %s, %s,%s, %s, %s)', (apt_id, doctor_id['Doctor_ID'], session['id'],service_id['Service_ID'],da.strftime('%Y-%m-%d %H:%M:%S'),0))
            mysql.connection.commit()
            print(docfname, doclname, service, date, times)
        
    
    return redirect(url_for('pat_appointments'))        
    #return render_template('pat_aptds.html',services = services, dates = dates, doc = doc, form= form)

@app.route('/login/pat_appointments',methods = ['GET','POST'])
def pat_appointments():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT a.Appointment_ID, d.Fname, d.Lname, s.Services, a.DTime FROM appointments as a, doctor as d, services as s WHERE a.Doctor_ID = d.Doctor_ID and s.Service_ID = a.Service_ID and a.Patient_ID = %s;',session['id'])
        apts1 = cursor.fetchall()         
        #print(apts1)
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM doctor;')
        doctors = cursor.fetchall() 
        cursor.execute('SELECT * FROM services;')
        services = cursor.fetchall() 
        form = Pat_APP()
        dfname = [ i['Fname']+' '+i['Lname'] for i in doctors]
        form.docfname.choices = dfname
        ser = [i['Services'] for i in services]
        form.services.choices = ser
        AT = []
        DOC =[]
        form1 = APT_Time()
        form1.apttime.choices = AT
        


        if form.validate_on_submit():
            SD = form.startdate.data
            #print(type(SD),str(SD))
            
            Name = form.docfname.data
            Ser = form.services.data
            DocFname = Name.split()[0]
            DocLname = Name.split()[1]
            #print(Ser, Name)
            DOC.append(DocFname)
            DOC.append(DocLname)
            DOC.append(Ser)
            DOC.append(SD)
            cursor.execute("SELECT Doctor_ID FROM telemedicine.doctor WHERE Fname = %s AND Lname = %s;",(DocFname, DocLname))
            doc_id = cursor.fetchone()
            cursor.execute("SELECT * FROM telemedicine.doctor_availability WHERE Doctor_ID = %s;",doc_id['Doctor_ID'])
            avail_records = cursor.fetchall()
            #print(avail_records)
            avail_times = []
            for i in avail_records:
                if str(SD) in  i['Availability_from'].strftime('%Y-%m-%d %H:%M:%S') :
                    origin = i['Availability_from']
                    end = i['Availability_to']
                    avail_times = time_plus(origin,end)
                    #print(avail_times)
                    AT.append(avail_times)
                    # cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
                    # cursor.execute('SELECT a.Appointment_ID, d.Fname, d.Lname, s.Services, a.DTime FROM appointments as a, doctor as d, services as s WHERE a.Doctor_ID = d.Doctor_ID and s.Service_ID = a.Service_ID and a.Doctor_ID = %s and a.Status = 1 ;',doc_id['Doctor_ID'])
                    # apts2 = cursor.fetchall() 
                    # print(apts2)
                    # times = [ i['DTime'].time() for i in apts2]
                    # print(type(times[0]),type(avail_times[0]), len(avail_times),len(times))
                    # avail_t = avail_times - times
                    # print(len(avail_t))
                    form1.apttime.choices = avail_times
            return render_template('pat_aptdets.html', doctors = doctors, form1 = form1, doc = DOC, AT=avail_times )
        
        
            #x = [ i['Availability_from'] for i in avail_records[''] ]
            # for i in x:
            #     if str(SD) in i:
            #         print(i)
            #print(x)
            #dates = []
            # y = [i['Availability_to'] for i in avail_records['']]
            # times = []

        return render_template('pat_appointments.html', doctors = doctors,form= form, form1 = form1, apts1 = apts1 )   


@app.route("/login/pat_payments", methods=['GET'])
def patpayments():
    if 'loggedin' in session:
        print("payments")
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE User_ID = %s', (session['id'],))
        account = cursor.fetchone()
        #cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT pay.Transaction_ID, p.Fname , p.Lname ,s.Services, pay.Amount, pay.Date, pay.Status FROM appointments as a, payments as pay, services as s , patient as p WHERE pay.Appointment_ID = a.Appointment_ID AND a.Service_ID = s.Service_ID AND a.Patient_ID=p.Patient_ID AND p.Patient_ID = %s AND a.Status=1;",(account['User_ID']))
        records = cursor.fetchall()
        return render_template('pat_payments.html', username=session['username'],payment_list=records)
    return redirect(url_for('login'))




if __name__=="__main__":
	app.run(debug=True)