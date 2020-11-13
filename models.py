from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from flask import Flask
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False

db = SQLAlchemy(app)

class User(UserMixin,db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String,nullable=False)
    password = db.Column(db.String,nullable=False)
    cash = db.Column(db.Float,nullable=False,default=float(10000))

    def __repr__(self):
        return f"<User {self.id}:{self.username}>"

class Portfolio(db.Model):
    __tablename__ = "portfolio"
    # one to one relationship
    user_id = db.Column(db.Integer,db.ForeignKey('users.id'),primary_key=True)
    company_id = db.Column(db.Integer,db.ForeignKey('company.id'),primary_key=True)
    shares = db.Column(db.Integer,nullable=False)

    user_data = db.relationship("User",foreign_keys=[user_id],backref='portfolio')
    company_data = db.relationship("Company",foreign_keys=[company_id],backref='portfolio')

    def __repr__(self):
        return f"<Portfolio {self.user_id}|{self.company_id}|{self.shares}>"

class Company(db.Model):
    __tablename__ = "company"
    id = db.Column(db.Integer,primary_key=True)
    symbol = db.Column(db.String(10),nullable=False,unique=True)
    name = db.Column(db.String,nullable=False,unique=True)

    def __repr__(self):
        return f"<Company {self.symbol}|{self.name}>"

class History(db.Model):
    __tablename__ = "history"
    id = db.Column(db.Integer,primary_key=True)
    user_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    company_id = db.Column(db.Integer,db.ForeignKey('company.id'))
    time = db.Column(db.DateTime,nullable=False)
    price = db.Column(db.Float,nullable=False)
    shares = db.Column(db.Integer,nullable=False)

    user_data = db.relationship("User",foreign_keys=[user_id],backref='history')
    company_data = db.relationship("Company",foreign_keys=[company_id],backref='history')

    def __repr__(self):
        return f"<History {self.user_id}|{self.company_id}|{self.shares}|{self.price}>"
