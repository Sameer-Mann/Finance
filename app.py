import os
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, redirect, render_template, request, url_for, jsonify
from flask_login import (LoginManager, login_user,
                         current_user, logout_user, login_required)
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime
from helpers import apology, lookup, usd
from models import User, Portfolio, Company, History
from forms import LoginForm, RegistrationForm

# Configure application
app = Flask(__name__)

# check for environment variables
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['WTF_CSRF_SECRET_KEY'] = os.environb[b'WTF_SECRET_KEY']


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(id1):
    return User.query.get(int(id1))


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = current_user.id

    if request.method == "GET":
        tot = current_user.cash
        data = Portfolio.query.filter_by(
            user_id=user_id).order_by(Portfolio.shares).all()
        if len(data):
            stocks = lookup(",".join([
                    str(data[i].company_data.symbol) for i in range(len(data))
                    ]))
            tot += sum([stocks[i]['price']*data[i].shares
                        for i in range(len(data))])
        else:
            stocks = []
        prices = [x["price"] for x in stocks]
        return render_template("index.html", cash=usd(current_user.cash),
                               data=data, total=usd(tot),
                               price=prices, usd=usd)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    usid = current_user.id

    if request.method == "GET":
        return render_template("buy.html")

    form_symbol = request.form.get("symbol")
    dic = lookup(form_symbol)[0]

    if not dic:
        return apology("Invalid Symbol")

    no_of_shares = int(request.form.get("shares"))

    if not no_of_shares:
        return apology("Must provide Shares")

    price = dic["price"]*int(no_of_shares)

    if (price > current_user.cash):
        return apology("cannot afford")
    try:
        company_obj = Company.query.filter_by(symbol=form_symbol).first()
        if company_obj is None:
            db.session.add(Company(
                symbol=form_symbol, name=lookup(form_symbol)[0]["name"]))
            db.session.commit()

        company_obj = Company.query.filter_by(symbol=form_symbol).first()
        check = Portfolio.query.filter(
            Portfolio.company_id == company_obj.id and
            Portfolio.user_id == usid).first()

        if check is None:
            db.session.add(Portfolio(
                    user_id=usid, company_id=company_obj.id, shares=no_of_shares))
        else:
            x = Portfolio.query.filter(
                Portfolio.company_id == company_obj.id).filter(
                    Portfolio.user_id == usid).first()
            x.shares += no_of_shares
            db.session.merge(x)
        db.session.add(
            History(
                user_id=usid, company_id=company_obj.id, time=datetime.utcnow(),
                price=price, shares=no_of_shares))
        current_user.cash -= price
        db.session.merge(current_user)
        db.session.commit()
    except sqlalchemy.exc.IntegrityError as e:
        print(e)
    return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    if request.method == "GET":
        items = History.query.filter_by(user_id=current_user.id).all()
        return render_template("history.html", items=items)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    login_form = LoginForm()
    if login_form.validate_on_submit():
        user_object = User.query.filter_by(
            username=login_form.username.data).first()
        login_user(user_object)
        return redirect("/")

    return render_template("login.html", form=login_form)


@app.route("/logout")
def logout():
    """Log user out"""

    logout_user()

    # Redirect user to login form
    return redirect(url_for("login"))


@app.route("/quote", methods=["POST"])
@login_required
def quote():
    """Get stock quote."""
    # print(request.form)
    names = request.form.get("symbol")
    data = lookup(names)
    if data is None:
        return jsonify({"message": "Invalid Symbol"}),404
    if len(names.split(",")) == 1:
        data = data[0]
    # return render_template("quote1.html", name=data)
        return jsonify({
            "name": data["name"],
            "symbol": data["symbol"],
            "price": data["price"]
            })
    return jsonify([{"name": x["name"],
                    "symbol": x["symbol"],
                     "price": x["price"]
                     } for x in data])


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    reg_form = RegistrationForm()

    if reg_form.validate_on_submit():
        username = reg_form.username.data
        password = generate_password_hash(reg_form.password.data)

        user = User(username=username, password=password)
        db.session.add(user)
        db.session.commit()

        flash('Registered successfully. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template("register.html", form=reg_form)


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = current_user.id

    if request.method == "GET":
        symbls = [x.company_data.symbol for x in Portfolio.query.filter_by(
            user_id=current_user.id).all()]
        return render_template("sell.html", symbols=symbls)

    # getting the required info from the html form and storing it if necessary
    form_symbol = str(request.form.get("symbol"))
    shares = int(request.form.get("shares"))
    rows = lookup(form_symbol)[0]
    company_obj = Company.query.filter_by(symbol=rows["symbol"]).first()
    p_obj = Portfolio.query.filter(
        Portfolio.user_id == user_id).filter(
            Portfolio.company_id == company_obj.id).first()
    price = rows["price"]*shares

    if shares > p_obj.shares:
        return apology("Not enough Shares")
    current_user.cash += price
    db.session.merge(current_user)
    db.session.add(History(
        user_id=user_id, company_id=company_obj.id, time=datetime.utcnow(),
        price=price, shares=shares))
    p_obj.shares -= shares
    if p_obj.shares == 0:
        db.session.delete(p_obj)
    else:
        db.session.merge(p_obj)
    db.session.commit()
    return redirect("/")


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    # saving the user_id
    user_id = current_user.id

    if request.method == "GET":
        return render_template("password.html")

    elif request.method == "POST":
        new_password = request.form.get("new_password")
        form_password = request.form.get("current_password")
        users = db.execute(
            "SELECT * FROM users WHERE id  = :id", {"id": user_id})
        user = users.fetchall()

        if not request.form.get("confirmation") == new_password:
            return apology("Both New Passwords Do Not Match")

        elif not check_password_hash(user[0][2], form_password):
            return apology("Incorrect Current Password")

        else:
            db.execute("DELETE FROM users WHERE id  = :id", {"id": user_id})
            db.execute(
                "INSERT INTO users (id,username,hash,cash) \
                VALUES(:id,:username,:hash,:cash)",
                {
                    "id": user_id, "username": user[0][1],
                    "hash": generate_password_hash(new_password),
                    "cash": user[0][3]
                })
            db.commit()
            return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
