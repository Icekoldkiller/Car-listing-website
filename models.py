from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(120))
    profile_pic = db.Column(db.String(120), nullable=True)  

    listed_cars = db.relationship('Car', back_populates='seller')
    orders = db.relationship('Order', backref='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(100), nullable=False)
    mileage = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    fuel = db.Column(db.String(50), nullable=True)
    condition = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(100), nullable=True)
    price = db.Column(db.Float, nullable=False)

    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    seller = db.relationship('User', back_populates='listed_cars')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'))

    car = db.relationship('Car')

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    car = db.relationship('Car')
