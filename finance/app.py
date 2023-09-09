import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd
import datetime

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user_id = session["user_id"]

    # Query for symbol, SUMshares, price data from transactions database.
    transactions_db = db.execute(
        "SELECT symbol, SUM(shares) AS shares, price FROM transactions WHERE user_id = ?  GROUP BY symbol HAVING SUM(shares) > 0", user_id)
    cash_db = db.execute("SELECT cash FROM users WHERE id = ?", user_id)

    # use database for transactions_db
    database = transactions_db

    # Show the balance of user
    cash = cash_db[0]["cash"]
    # return jsonify(cash)

    # sum up the total price of stocks
    # total = int(database[x]['shares']) * float(database[x]['price'])
    # stocks = []
    total = 0

    for x in range(len(database)):
        # stock = lookup(database[x]['symbol'])
        # stocks.append(stock)

        # sum up the total
        total = int(database[x]['shares']) * float(database[x]['price'])
        total = total + 1

    return render_template("index.html", cash=cash, database=database, total=total+cash)

    # for x in range(len(database)):
    #     look up for  stock's company name
    #     stock = lookup(database[x]['symbol'])
    #
    #     total = int(database[x]['shares']) * float(database[x]['price'])
    #     return render_template("index.html", cash = cash, Symbol=database[x]['symbol'], company_name=stock['name'], shares=database[x]['shares'], price=database[x]['price'], total=total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # user reached route via get
    if request.method == "GET":
        return render_template("buy.html")

    # user reached route via post
    else:
        symbol = request.form.get("symbol")
        shares = request.form.get("shares")

        # Ensure symbol is submitted.
        if not symbol:
            return apology("Must Provide Symbol", 400)

        # Ensure shares is integer
        if int(shares) < 0:
            return apology("Shares Must Be Positive Integer", 400)

        # Ensure stock is existed.
        stock = lookup(symbol.upper())

        if stock is None:
            return apology("Symbol Does Not Existed", 400)

        # Ensure users have enough money to buy the stock
        # session 里的user_id 到底指的是啥呢
        # Remember which user has logged in
        # session["user_id"] = rows[0]["id"] 所以balance的是使用id 定行而不是username

        user_id = session["user_id"]
        balance = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        # return jsonify(balance) ->> [{"cash":10000}]
        balance_value = balance[0]["cash"]

        # do caculate
        if int(stock['price']) * int(shares) > balance_value:
            return apology("Not Enough Balance", 400)

        # update the new balance
        new_balance = balance_value - stock['price'] * int(shares)
        db.execute("UPDATE users SET cash = ? WHERE id = ?", new_balance, user_id)

        # record the transactions
        date = datetime.datetime.now()
        db.execute("INSERT INTO transactions (user_id, symbol, shares, price, date) VALUES (?, ?, ?, ?, ?)",
                   user_id, symbol, shares, stock["price"], date)

        # flash the page with 'BOUGHT!'
        flash("Bought!")
        return redirect("/")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    # Find the user who is now logged in.
    user_id = session["user_id"]

    # Query the database for this user's transactions.
    transactions_log = db.execute("SELECT symbol, shares, price, date FROM transactions WHERE user_id = ?", user_id)

    # pass the log to database in html
    return render_template("history.html", database=transactions_log)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

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
    # for get
    if request.method == "GET":
        return render_template("quote.html")

    # for post
    else:
        symbol = request.form.get("symbol")

        # ensure symbol is texted
        if not symbol:
            return apology("must provide symbol", 400)
        # look up for the symbol stock and upprcase the symbol
        stock = lookup(symbol.upper())

        if stock is None:
            return apology("Symbol Does Not Existed.", 400)

        # if success, return quoted info

        return render_template("quoted.html", Name=stock["name"], Price=stock["price"], Symbol=stock["symbol"])


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # define the variation in python where got from html
    username = request.form.get("username")
    password = request.form.get("password")
    confirmation = request.form.get("confirmation")

    # post method:
    if request.method == "POST":
        # ensure username, password, confirmation are submitted
        if not username:
            return apology("must provide username", 400)

        elif not password:
            return apology("must provide password", 400)

        elif not confirmation:
            return apology("must provide confirmation", 400)

        # confirm the password
        if password != confirmation:
            return apology("Password mismatch.", 400)

        # query database for username
        # rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # ensure username is not existed in the database
        # if len(rows) != 0:
            # return apology("The username has already existed.", 400)

        # hash a password
        hash = generate_password_hash(password)

        # insert a new account info
        try:
            new_user_id = db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, hash)

        except:
            return apology("The username has already existed.", 400)

        # remember new register's login state
        session["user_id"] = new_user_id

        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # User reached route via GET
    if request.method == "GET":
        # find the user who is now logging in
        user_id = session["user_id"]

        # Find the symbol that user has.
        user_transactions = db.execute(
            "SELECT symbol FROM transactions WHERE user_id = ? GROUP BY symbol HAVING SUM(shares) > 0", user_id)

        # Find the shares that user has.
        user_shares = db.execute("SELECT SUM(shares) AS shares FROM transactions WHERE user_id = ?", user_id)

        # # handle with not buying any stock  在这get的时候不需要
        # if user_shares[0]['shares'] is None:
        #     return render_template("sell.html")

        # shares_num = int(user_shares[0]['shares'])

        return render_template("sell.html",  database=user_transactions)


    # via POST
    else:
        user_id = session["user_id"]

        # update users database on cash
        symbol = request.form.get("symbol")

        # Find the shares that user has.
        user_shares = db.execute(
            "SELECT SUM(shares) AS shares FROM transactions WHERE user_id = ? AND symbol = ? GROUP BY symbol", user_id, symbol)
        # return jsonify(user_shares) ->>[]

        if user_shares == []:
            return apology("Do Not Have Any Stock.", 400)

        else:
            # look up from dict(user_shares) to get the number of shares*str and change into int
            shares_num = int(user_shares[0]['shares'])

            # Take the num of shares that input from user and change into int
            shares_get = int(request.form.get("shares"))

            if shares_get == 0:
                return apology("Invalid Shares.", 400)

            # Ensure user has enough shares to sell.
            if shares_num < shares_get or shares_get < 0:
                return apology("Too Much Shares", 400)

            # look up for today's stock price of this symbol
            stock = lookup(symbol)

            # take the cash balance
            balance = db.execute("SELECT cash FROM users WHERE id = ?", user_id)

            # return jsonify(balance) ->> [{"cash":10000}]
            balance_value = balance[0]["cash"]

            # caculate the new balance
            new_balance = balance_value + stock['price'] * shares_get
            # update the cash value in users database
            db.execute("UPDATE users SET cash = ? WHERE id = ?", new_balance, user_id)

            # record the transactions
            date = datetime.datetime.now()
            db.execute("INSERT INTO transactions (user_id, symbol, shares, price, date) VALUES (?, ?, ?, ?, ?)",
                    user_id, symbol, -shares_get, stock['price'], date)

            # flash the page
            flash("Sold!")
            return redirect("/")

