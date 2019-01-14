import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# check for environment variables
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

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


# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    # saving the user_id in a  variable
    user_id = session["user_id"]

    if request.method == "GET":
        rows_raw = db.execute("SELECT cash FROM users WHERE id  = :id",{"id":user_id})
        cash = rows_raw.fetchall()[0][0]
        users_raw = db.execute("SELECT* FROM portfolio WHERE id = :id ORDER BY shares",{"id":user_id})
        price = 0
        nusers = users_raw.fetchall()

        # updating the price in table portfolio with the current price and adding the total value of our shares
        for i in range(len(nusers)):
            stock = lookup(nusers[i][0])
            price += stock["price"]*nusers[i][2]

        return render_template("index.html", cash=usd(cash), users=nusers, total=usd(cash+price))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # remembering the user_id
    usid = session["user_id"]

    if request.method == "GET":
        return render_template("buy.html")

    elif request.method == "POST":

        # Ensure proper symbol usage
        form_symbol = request.form.get("symbol")
        dic = lookup(form_symbol)

        if not dic:
            return apology("Invalid Symbol")

        no_of_shares = request.form.get("shares")

        # ensuring that the user inputs the number of shares
        if not no_of_shares:
            return apology("Must provide Shares")

        price = dic["price"]*int(no_of_shares)
        uscash = db.execute("SELECT cash FROM users WHERE id = :id",{"id":usid})
        check = db.execute("SELECT * FROM portfolio WHERE symbol = :symbol AND id = :id",{"symbol":form_symbol, "id":usid})
        cash = uscash.fetchall()[0][0]

        # checking that prices of the stocks does not exceed the total amount of cash
        if (price > cash):
            return apology("cannot afford")

        # checking to remove the stock completely or just some shares and updating the required tables
        elif len(check.fetchall()) != 0:
            db.execute("UPDATE users SET cash = cash - :kash WHERE id = :id",{"kash":price,"id":usid})

            db.execute("UPDATE portfolio SET shares = shares + :share WHERE symbol = :symbol",{"share":no_of_shares, "symbol":form_symbol})

            db.execute("INSERT INTO history (symbol,name,shares,price,id,time) VALUES (:symbol,:name,:share,:pric,:id,:time)",
                       {"symbol":dic["symbol"], "name":dic["name"], "share":no_of_shares, "pric":price, "id":session["user_id"], "time":datetime.utcnow()})
            db.commit()
            return redirect("/")

        else:
            db.execute("UPDATE users SET cash = cash - :cash WHERE id = :id",{"cash":price, "id":usid})

            db.execute("INSERT INTO portfolio (symbol,name,shares,id,price) VALUES (:symbol,:name,:share,:id,:price)",
                       {"symbol":dic["symbol"], "name":dic["name"], "share":no_of_shares, "id":session["user_id"],"price":dic["price"]})

            db.execute("INSERT INTO history (symbol,name,shares,price,id,time) VALUES (:symbol,:name,:share,:pric,:id,:time)",
                       {"symbol":dic["symbol"], "name":dic["name"], "share":no_of_shares, "pric":price, "id":session["user_id"], "time":datetime.utcnow()})
            
            db.commit()
            return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    if request.method == "GET":
        items = db.execute("SELECT* FROM history WHERE id = :id",{"id":session["user_id"]})
        return render_template("history.html", items=items.fetchall())


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",{"username":request.form.get("username")})
        row = rows.fetchall()

        # Ensure username exists and password is correct
        if not check_password_hash(row[0][2], request.form.get("password")):
            return apology("invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = row[0][0]

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


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    # Displaying the page for quote
    if request.method == "GET":
        return render_template("quote.html")

    elif request.method == "POST":
        sym = lookup(request.form.get("symbol"))

        if not sym:
            return apology("Invalid Symbol")

        return render_template("quote1.html", name=sym)


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        uname = request.form.get("username")
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username")

        # Ensure password was submitted
        elif not (request.form.get("password") and request.form.get("confirmation")):
            return apology("must provide password")

        # Ensure that password and confirmation match
        elif not (request.form.get("password") == request.form.get("confirmation")):
            return apology("Both password's Do Not Match")

        if db.execute("SELECT* FROM users WHERE username = :usname", {"usname":uname}).fetchall() is None:
            return apology("Username Already exists")

        else:
            # entering the user in our database
            name = db.execute("INSERT INTO users (username,hash) VALUES (:username,:hash)",{"username":uname, "hash":generate_password_hash(request.form.get("password"))})
            db.commit()

        # logging in the user
        id = db.execute("SELECT id FROM users WHERE username = :username",{"username":uname})
        session["user_id"] = id.fetchone()[0] 

        # Redirect user to home page
        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # saving the user_id
    user_id = session["user_id"]

    if request.method == "GET":
        symbls = db.execute("SELECT symbol FROM portfolio WHERE id = :id", {"id":user_id})
        return render_template("sell.html", symbols=symbls.fetchall())

    elif request.method == "POST":
        # getting the required info from the html form and storing it if necessary
        form_symbol = str(request.form.get("symbol"))
        shares = int(request.form.get("shares"))
        rows = lookup(form_symbol)
        data = db.execute("SELECT shares FROM portfolio WHERE symbol = :symbol", {"symbol":form_symbol})
        user_shares = data.fetchall()

        if not shares:
            return apology("Must provide Shares")

        elif not rows:
            return apology("Must provide Symbol")

        elif shares > user_shares["shares"]:
            return apology("Not enough Shares")

        elif shares == user_shares["shares"]:
            db.execute("DELETE FROM portfolio WHERE symbol = :symbol AND id = :id", {"symbol":form_symbol, "id":user_id})

            db.execute("UPDATE users SET cash = cash + :kash WHERE id = :id", {"kash":rows["price"]*shares, "id":user_id})

            db.execute("INSERT INTO history (symbol,name,shares,price,id,time) VALUES (:symbol,:name,:share,:price,:id,:time)",
                       {"symbol":rows["symbol"], "name":rows["name"], "share":(-shares), "price":rows["price"]*shares, "id":user_id, "time":datetime.utcnow()})
            db.commit()
            return redirect("/")
        else:
            db.execute("UPDATE users SET cash = cash + :cash WHERE id = :id", {"cash":rows["price"]*shares, "id":user_id})

            db.execute("UPDATE portfolio SET shares = shares - :share WHERE id = :id AND symbol = :symbol",
                       {"share":shares, "id":user_id, "symbol":form_symbol})

            db.execute("INSERT INTO history (symbol,name,shares,price,id,time) VALUES (:symbol,:name,:share,:price,:id,:time)",
                       {"symbol":rows["symbol"], "name":rows["name"], "share":(-shares), "price":rows["price"]*shares, "id":user_id, "time":datetime.utcnow()})
            db.commit()
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
    user_id = session["user_id"]

    if request.method == "GET":
        return render_template("password.html")

    elif request.method == "POST":
        new_password = request.form.get("new_password")
        form_password = request.form.get("current_password")
        users = db.execute("SELECT * FROM users WHERE id  = :id", {"id":user_id})
        user = users.fetchall()

        if not request.form.get("confirmation") == new_password:
            return apology("Both New Passwords Do Not Match")

        elif not check_password_hash(user[0][2], form_password):
            return apology("Incorrect Current Password")

        else:
            db.execute("DELETE FROM users WHERE id  = :id", {"id":user_id})
            db.execute("INSERT INTO users (id,username,hash,cash) VALUES(:id,:username,:hash,:cash)",{"id":user_id, "username":user[0][1], "hash":generate_password_hash(new_password),"cash":user[0][3]})
            db.commit()
            return redirect("/")

app.run(host='0.0.0.0', port=80)