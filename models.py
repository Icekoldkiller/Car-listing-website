from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(100), nullable=False)
    mileage = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    fuel = db.Column(db.String(50), nullable=False)
    condition = db.Column(db.String(50), nullable=False)
    image = db.Column(db.String(100), nullable=True)
    price = db.Column(db.Float, nullable=False)  
