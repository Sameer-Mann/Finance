import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbols):
    """Look up quote for symbol."""

    # Contact API
    response = requests.get(f"https://cloud.iexapis.com/stable/stock/market/batch?symbols={symbols}&types=quote&token=sk_ef9431148f1b424f81467ffbf7940f02")
    if response.status_code != 200:
        return None

    # Parse response
    try:
        return [{"price":value['quote']['latestPrice'],"name": value['quote']['companyName'],"symbol":key} for key,value in response.json().items()]
    except (KeyError, TypeError, ValueError):
        return None

def usd(value):
    """Format value as USD."""
    return (f"${value:,.2f}")
