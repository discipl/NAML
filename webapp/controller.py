from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import InputRequired, Email, Length
from flask_sqlalchemy  import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import Flask, send_file, request, jsonify, render_template,redirect
from werkzeug.utils import secure_filename

import sys,os
sys.path.append('webapp/')
sys.path.append('database/')
#sys.path.append('machine_learning/')
sys.path.append('test/')

import model
import model_properties
import ml_model_v1 as ml
#import performance_tests as pt
import subprocess
#import update_dababase as database

UPLOAD_FOLDER = 'java/emails/msg/'
ALLOWED_EXTENSIONS = set(['msg'])


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SECRET_KEY'] = 'bigdatarepublic@secretkey2017'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////database.db'
Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

current_model_name = None
########################################################################################################################
#LOG IN CLASSES
########################################################################################################################
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(80))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class LoginForm(FlaskForm):
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])
    remember = BooleanField('remember me')

class RegisterForm(FlaskForm):
    email = StringField('email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    username = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])

########################################################################################################################
#UPLOAD FUNCTIONS
########################################################################################################################

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

########################################################################################################################
#EXTRA FUNCTIONS
########################################################################################################################
def create_user_email_im_dir(username):
    print('Creating directory of email images of '+str(username) )
    dir_path = 'static/Images/Emails/Users/'
    directory = username
    if not os.path.exists(dir_path+directory):
        os.makedirs(dir_path+directory+'/'+'feature_importance_email_NA')
        os.makedirs(dir_path+directory+'/'+'feature_importance_email_NA'+'/'+ 'etr')
        os.makedirs(dir_path+directory+'/'+'feature_importance_email_NA'+'/'+ 'mnb')
        os.makedirs(dir_path + directory + '/' + 'feature_importance_email_NA' + '/' + 'rf')
        os.makedirs(dir_path+directory+'/'+'pie_probability_NA')
        os.makedirs(dir_path+directory+'/'+'pie_probability_NA'+'/'+ 'etr')
        os.makedirs(dir_path+directory+'/'+'pie_probability_NA'+'/'+ 'mnb')
        os.makedirs(dir_path + directory + '/' + 'pie_probability_NA' + '/' + 'rf')
        with open(dir_path+directory+'/json_email_data_NA.txt',"w") as email_data_file:
            email_data_file.write("{}")

########################################################################################################################
#REQUESTS HANDLING
########################################################################################################################
@app.route('/', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if check_password_hash(user.password, form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect('/controleboard/')

        return '<h1>Invalid username or password</h1>'
        #return '<h1>' + form.username.data + ' ' + form.password.data + '</h1>'

    return render_template('login.html', form=form)

@app.route('/controleboard/',methods=['GET','POST'] )
@login_required
def index():
    print(request.method)
    if request.method == 'POST':
        print('Caught post request...')
        post_data = request.get_json()
        print(post_data)
        model.correct_predictions_from_input(post_data['mail_id'],post_data['truth_class'] )
        with open('static/data/corrections/corr.txt','a') as file:
            file.write( str(post_data['mail_id']+' ; ' +str(post_data['truth_class'])) )
            file.write('\n')

    return send_file("templates/index_controleboard.html")#,form=form )


@app.route('/signup/', methods=['GET', 'POST'])
@login_required
def signup():
    if current_user.username != 'admin':
        return redirect('/')
    form = RegisterForm()

    if form.validate_on_submit():
        print('Creating new User...')
        hashed_password = generate_password_hash(form.password.data, method='sha256')
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        create_user_email_im_dir(new_user.username)

        return '<h1>New user has been created!</h1>'
        #return '<h1>' + form.username.data + ' ' + form.email.data + ' ' + form.password.data + '</h1>'

    return render_template('signup.html', form=form)

#add temporarily
@app.route('/corrections/', methods=['GET'])
@login_required
def get_corrections():
    """
    View which is called whenever the '/s/' this url is requested
    """
    try:
        file_corr = 'static/data/corrections/corr.txt'
        with open(file_corr, 'r') as file:
            corrections = file.read()
    except:
        print('file not found...')
        corrections = ''
        pass
    return jsonify(corrections)

@app.route('/s/', methods=['GET'])
@login_required
def search_query():
    """
    View which is called whenever the '/s/' this url is requested
    """
    return jsonify(model.get_mails_of(username=current_user.username,address=current_user.email))

@app.route('/global_performances/',methods=['GET','POST'] )
@login_required
def index_performance():
    images = dict()
    images['pie'] = ''
    form = model_properties.MNBInputForm(request.form)
    if request.method == 'POST':
        post_data = request.get_json()
        print(os.listdir(os.getcwd() + '/../machine_learning/'))

        if 'new_model' in post_data.keys():####---------> is dit stuk nog nodig?????
            current_model_name = post_data['new_model']
            print('Update model name '+ current_model_name + ' ...')
            post_filenames()

        if 'message' in post_data.keys():
            print(post_data)
            if(post_data['message']== 'TRAIN'):
                print(post_data)
                ml.generate_new_images_manual_fit(name_model =post_data['model_name'],
                                            thres = float(post_data['threshold']),
                                            weight_taak = float(post_data['weight_taak']),
                                            weight_non_taak = float(post_data['weight_non_taak']) )
            if (post_data['message'] == 'AUTO_TRAIN'):
                print('Start Grid Search...')
                ml.generate_new_images_auto_fit(name_model=post_data['model_name'])
                #subprocess.call(['python', os.getcwd() + '/../machine_learning/ml_model_v1.py'])
    if current_user.username == 'admin':
        return send_file("templates/index_global_performance_admin.html")
    else:
        return send_file("templates/index_global_performance_user.html")



#######################################################################################################################
@app.route('/images/',methods=['GET','POST'] )
@login_required
def post_filenames():
    current_model_name = 'Extreme Random Forest'
    if request.method == 'POST':
        post_data = request.get_json()
        if 'new_model' in post_data.keys():
            current_model_name = post_data['new_model']
            print('Update model name '+ current_model_name + ' ...')

    images = model_properties.update_model_performance_image(current_model_name)
    print(images)
    return jsonify(images)
########################################################################################################################

@app.route('/email_data/',methods=['GET','POST'] )
@login_required
def post_emailnames():
    if request.method == 'POST':
        post_data = request.get_json()
        if 'mail_id' in post_data.keys():
            new_mail_id = post_data['mail_id']
            print('Update email data and images of '+str(current_user.username))
            #print( ml.get_mail_test(new_mail_id) )
            ml.add_new_email_images(new_mail_id, user=current_user.username)
        if 'message' in post_data.keys():
            if post_data['message'] == 'RESET':
                def clean_dir(pathdir, extra_dir='/'):
                    '''
                    :param pathdir: 
                    :return: deletes all .png and .txt within the dir
                    '''
                    for filename in os.listdir(pathdir + extra_dir):
                        if (filename.split('.')[1] == 'txt') or (filename.split('.')[1] == 'png'):
                            print('Deleting File: ' + str(filename))
                            os.remove(pathdir + extra_dir + filename)

                dir_path = 'static/Images/Emails/Users/'
                directory = current_user.username
                clean_dir(dir_path + directory + '/' + 'feature_importance_email_NA' + '/' + 'etr/')
                clean_dir(dir_path + directory + '/' + 'feature_importance_email_NA' + '/' + 'mnb/')
                clean_dir(dir_path + directory + '/' + 'feature_importance_email_NA' + '/' + 'rf')
                clean_dir(dir_path + directory + '/' + 'pie_probability_NA' + '/' + 'etr/')
                clean_dir(dir_path + directory + '/' + 'pie_probability_NA' + '/' + 'mnb/')
                clean_dir(dir_path + directory + '/' + 'pie_probability_NA' + '/' + 'rf/')

                os.remove(dir_path + directory + '/' + 'json_email_data_NA.txt')
                with open(dir_path + directory + '/' + 'json_email_data_NA.txt', "w") as email_data_file:
                    email_data_file.write("{}")

    return jsonify(model.get_Email_names(current_user.username))


@app.route('/emails/',methods=['GET','POST'] )
@login_required
def index_emails():
    return send_file("templates/index_email.html" )

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')

@app.route('/upload_emails/',methods=['GET','POST'] )
@login_required
def index_upload_emails():
    if current_user.username != 'admin':
        return redirect('/')
    if request.method == 'POST':
        print(request.files)
        if 'file' in request.files:
            uploaded_files = request.files.getlist("file")
            for file in uploaded_files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return redirect('/global_performances/')

@app.route('/update_database/',methods=['GET','POST'] )
@login_required
def index_update_database():
    if request.method == 'POST':
        post_data = request.get_json()
        if 'message' in post_data.keys():
            if post_data['message'] == 'UPDATE_DATABASE':
                model.update_mail_database(path_database='static/data/databases/', filename_database='database_NA_v1.db',
                               path_mails='java/emails/processed/')
                for filename in os.listdir('java/emails/processed/'):
                    if (filename.split('.')[1] == 'txt') or (filename.split('.')[1] == 'png'):
                        print('Deleting File: ' + str(filename))
                        os.remove('processed/'+ filename)
    return redirect('/')
if __name__ == '__main__':
    app.run(debug = True, host='0.0.0.0')#,port=80)
    #app.run(host='0.0.0.0',port=80)