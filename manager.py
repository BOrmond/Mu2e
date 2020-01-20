import os
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from reader import read_cc, read_ldo
from sqlalchemy import create_engine
from urllib.parse import quote_plus
from markupsafe import Markup

project_dir = os.path.dirname(os.path.abspath(__file__))
database_file = "sqlite:///{}".format(os.path.join(project_dir, "Mu2eDatabase.db"))
UPLOAD_FOLDER1 = os.path.join(project_dir, "upload1")
UPLOAD_FOLDER2 = os.path.join(project_dir, "upload2")


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = database_file
app.config['UPLOAD_FOLDER1'] = UPLOAD_FOLDER1
app.config['UPLOAD_FOLDER2'] = UPLOAD_FOLDER2
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
ALLOWED_EXTENSIONS = {'csv'}

db = SQLAlchemy(app)
engine = create_engine(database_file)


class DMB(db.Model):
    index = db.Column(db.String(80), unique=True, nullable=False, primary_key=True)
    date = db.Column(db.DateTime(), nullable=False)
    ldo = db.Column(db.String(1000))
    continuity = db.Column(db.String(1000))
    crosstalk = db.Column(db.String(1000))
    chipID = db.Column(db.String(80))
    panelNum = db.Column(db.String(80))
    notes = db.Column(db.String(20000))

    def __repr__(self):
        cont = self.continuity
        cross = self.crosstalk
        if self.continuity == "":
            cont = "None"
        if self.crosstalk == "":
            cross = "None"

        return "\n\n\033[4mDMB\033[0m\nIndex: {}".format(self.index) + "\nDate: {}".format(self.date) \
               + "\nContinuity: {}".format(cont) + "\nCrosstalk: {}".format(cross)


class AMB(db.Model):
    index = db.Column(db.String(80), unique=True, nullable=False, primary_key=True)

    def __repr__(self):
        return "<AMB {}>".format(self.index)


class PreAmp(db.Model):
    index = db.Column(db.String(80), unique=True, nullable=False, primary_key=True)

    def __repr__(self):
        return "<PreAmp {}>".format(self.index)


class User(db.Model):
    name = db.Column(db.String(80), nullable=False)
    date = db.Column(db.DateTime(), nullable=False, primary_key=True)

    def __repr__(self):
        return self.name + "\t\t" + self.date.strftime("%b/%d/%Y %H:%M:%S")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/", methods=["GET", "POST"])
def home():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        recentUsers = User.query.order_by(User.date.desc()).limit(9)
        print(recentUsers, flush=True)
        return render_template('home.html', users=recentUsers)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.form['password'] == 'password' and request.form['username'] == 'admin':
        session['logged_in'] = True
        user = User(name=request.form["name"], date=datetime.now())
        db.session.add(user)
        db.session.commit()
        return home()
    else:
        flash("Incorrect Password")
        return render_template('login.html')


@app.route("/logout", methods=['GET', 'POST'])
def logout():
    session['logged_in'] = False
    return render_template('login.html')


@app.route("/addDMB", methods=["GET", "POST"])
def addDMB():
    if request.method == 'POST':

        voltages, contStr, crossStr, chipID, panel, notes = None, None, None, None, None, None

        if 'dmb' in request.form:

            index = request.form["index"]
            if DMB.query.filter(DMB.index == index).first():
                flash('Index already used', "create error")
                return redirect(request.url)

            if 'ldo' in request.files:
                filecount = 0
                if allowed_file(request.files['ldo'].filename):
                    ldo = request.files['ldo']
                    filecount += 1
                    filename = secure_filename(ldo.filename)
                    ldo.save(os.path.join(UPLOAD_FOLDER2, filename))
                elif request.files['ldo'].filename:
                    flash('Wrong file type (CSV only)', "submit error")
                if filecount > 0:
                    voltages = read_ldo(index)

            if 'cc' in request.files:
                filecount = 0
                cc = request.files.getlist('cc')
                for file in cc:
                    if allowed_file(file.filename):
                        filecount += 1
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(UPLOAD_FOLDER1, filename))
                    elif file:
                        flash('Wrong file type (CSV only)', "submit error")
                if filecount > 0:
                    cont, cross = read_cc()
                    contStr = ", ".join(str(i) for i in cont)
                    crossStr = ""
                    rows = []
                    keys = list(cross.keys())
                    for i in range(len(keys)):
                        joined = ", ".join(str(j) for j in cross[keys[i]])
                        rows += [(str(keys[i]) + "  " + joined)]
                    crossStr = ":".join(row for row in rows)

            if "ID" in request.form:
                chipID = request.form["ID"]

            if "Panel" in request.form:
                panel = request.form["Panel"]

            if "notes" in request.form:
                notes = request.form["notes"]

            dmb = DMB(index=index, date=datetime.now(), continuity=contStr, crosstalk=crossStr,
                      chipID=chipID, panelNum=panel, notes=notes, ldo=voltages)
            db.session.add(dmb)
            db.session.commit()

    recent = DMB.query.order_by(DMB.date.desc()).first()
    return render_template("addDMB.html", recent=recent)


@app.route("/viewDMB/<index>")
def view_dmb(index):
    dmb = DMB.query.filter(DMB.index == index).first()
    return render_template("view.html", dmb=dmb)


@app.route("/editDMB/<index>", methods=["GET", "POST"])
def edit_dmb(index):

    dmb = DMB.query.filter(DMB.index == index).first()
    if request.method == 'POST':

        index, voltages, contStr, crossStr, chipID, panel, notes = None, None, None, None, None, None, None

        if 'dmb' in request.form:

            if "index" in request.form:
                index = request.form["index"]
                if DMB.query.filter(DMB.index == index).first() == dmb:
                    flash('Index is the same', "create error")
                    return redirect(request.url)
                elif DMB.query.filter(DMB.index == index).first():
                    flash('DMB already exists', "create error")
                    return redirect(request.url)
                if index:
                    dmb.index = index

            if 'ldo' in request.files:
                filecount = 0
                if allowed_file(request.files['ldo'].filename):
                    ldo = request.files['ldo']
                    filecount += 1
                    filename = secure_filename(ldo.filename)
                    ldo.save(os.path.join(UPLOAD_FOLDER2, filename))
                elif request.files['ldo'].filename:
                    flash('Wrong file type (CSV only)', "submit error")
                if filecount > 0:
                    if not index:
                        voltages = read_ldo(dmb.index)
                    else:
                        voltages = read_ldo(index)
                    dmb.ldo = voltages

            if 'cc' in request.files:
                filecount = 0
                cc = request.files.getlist('cc')
                for file in cc:
                    if allowed_file(file.filename):
                        filecount += 1
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(UPLOAD_FOLDER1, filename))
                    elif file:
                        flash('Wrong file type (CSV only)', "submit error")
                if filecount > 0:
                    cont, cross = read_cc()
                    contStr = ", ".join(str(i) for i in cont)
                    crossStr = ""
                    rows = []
                    keys = list(cross.keys())
                    for i in range(len(keys)):
                        joined = ", ".join(str(j) for j in cross[keys[i]])
                        rows += [(str(keys[i]) + "  " + joined)]
                    crossStr = ":".join(row for row in rows)

                    dmb.continuity = contStr
                    dmb.crosstalk = crossStr

            if "ID" in request.form:
                chipID = request.form["ID"]
                if chipID:
                    dmb.chipID = chipID

            if "Panel" in request.form:
                panel = request.form["Panel"]
                if panel:
                    dmb.panelNum = panel

            if "notes" in request.form:
                notes = request.form["notes"]
                if notes:
                    dmb.notes = notes

        db.session.commit()

    return render_template("edit.html", current=dmb)


@app.route("/deleteDMB/<index>", methods=["GET", "POST"])
def delete_dmb(index):
    dmb = DMB.query.filter(DMB.index == index).first()
    if "delete" in request.form:
        db.session.delete(dmb)
        db.session.commit()
        return redirect("/search")
    if "cancel" in request.form:
        return redirect("/search")

    return render_template("delete.html", dmb=dmb)


@app.route("/search", methods=["GET", "POST"])
def search():

    dmbs = DMB.query.order_by(DMB.date.desc()).all()
    if "date" in request.form:
        dmbs = DMB.query.order_by(DMB.date).all()
    query = None
    if "search" in request.form:
        index = request.form["index"]
        if index == "":
            query = None
        else:
            query = DMB.query.filter(DMB.index == index).first()
            if not query:
                query = False

    return render_template("search.html", dmbs=dmbs, query=query)


@app.route("/delete", methods=["POST"])
def delete():
    index = request.form.get("index")
    dmb = DMB.query.filter_by(index=index).first()
    db.session.delete(dmb)
    db.session.commit()
    return redirect("/")


@app.template_filter('urlencode')
def urlencode_filter(s):
    if type(s) == 'Markup':
        s = s.unescape()
    s = s.encode('utf8')
    s = quote_plus(s)
    return Markup(s)


def drop_table(table):
    table.__table__.drop(engine)


if __name__ == "__main__":
    app.secret_key = os.urandom(12)
    app.run(debug=True, host='0.0.0.0', port=5000)
