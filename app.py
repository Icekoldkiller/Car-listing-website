from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.secret_key = 'supersecret'

# Database setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cars.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Image upload config
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Models ---
class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(50), nullable=False)
    mileage = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    brand = db.Column(db.String(50), nullable=False)
    fuel = db.Column(db.String(20), nullable=False)
    condition = db.Column(db.String(20), nullable=False)
    image = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)

# --- Routes ---

@app.route('/')
def index():
    brand = request.args.get('brand')
    year = request.args.get('year')

    cars = Car.query
    if brand:
        cars = cars.filter(Car.brand.ilike(f"%{brand}%"))
    if year:
        try:
            cars = cars.filter_by(year=int(year))
        except ValueError:
            pass
    cars = cars.all()

    return render_template('index.html', cars=cars)

@app.route('/add', methods=['GET', 'POST'])
def add_car():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            return "Invalid image file!"

        new_car = Car(
            model=request.form['model'],
            mileage=request.form['mileage'],
            year=int(request.form['year']),
            brand=request.form['brand'],
            fuel=request.form['fuel'],
            condition=request.form['condition'],
            price=float(request.form['price']),
            image=filename
        )
        db.session.add(new_car)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('add_car.html')

@app.route('/admin')
def admin():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    cars = Car.query.all()
    return render_template('admin.html', cars=cars)

@app.route('/delete/<int:car_id>')
def delete_car(car_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    car = Car.query.get_or_404(car_id)
    db.session.delete(car)
    db.session.commit()
    return redirect(url_for('admin'))

@app.route('/edit/<int:car_id>', methods=['GET', 'POST'])
def edit_car(car_id):
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))

    car = Car.query.get_or_404(car_id)

    if request.method == 'POST':
        car.model = request.form['model']
        car.mileage = request.form['mileage']
        car.year = int(request.form['year'])
        car.brand = request.form['brand']
        car.fuel = request.form['fuel']
        car.condition = request.form['condition']
        car.price = float(request.form['price'])

        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            car.image = filename

        db.session.commit()
        return redirect(url_for('car_detail', car_id=car.id))

    return render_template('edit_car.html', car=car)

@app.route('/car/<int:car_id>')
def car_detail(car_id):
    car = Car.query.get_or_404(car_id)
    return render_template('car_detail.html', car=car)

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == '1234':
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/add-to-cart/<int:car_id>')
def add_to_cart(car_id):
    cart = session.get('cart', [])
    if car_id not in cart:
        cart.append(car_id)
    session['cart'] = cart
    return redirect(url_for('index'))

@app.route('/remove-from-cart/<int:car_id>')
def remove_from_cart(car_id):
    cart = session.get('cart', [])
    if car_id in cart:
        cart.remove(car_id)
    session['cart'] = cart
    return redirect(url_for('cart'))


@app.route('/cart')
def cart():
    cart_ids = session.get('cart', [])
    cars = Car.query.filter(Car.id.in_(cart_ids)).all()
    return render_template('cart.html', cars=cars)

@app.route('/checkout')
def checkout():
    session.pop('cart', None)
    return "Thank you for your purchase!"


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)

