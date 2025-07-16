from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from models import CartItem, Car, User
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

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(120))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'))
    user = db.relationship('User', backref='orders')
    car = db.relationship('Car')

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    car_id = db.Column(db.Integer, db.ForeignKey('car.id'), nullable=False)


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
def logout_admin():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/add-to-cart/<int:car_id>')
def add_to_cart(car_id):
    cart = session.get('cart', [])
    if car_id not in cart:
        cart.append(car_id)
    session['cart'] = cart
    return redirect(url_for('index'))

@app.route('/remove_from_cart/<int:car_id>')
def remove_from_cart(car_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    item = CartItem.query.filter_by(user_id=session['user_id'], car_id=car_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('cart'))


@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    items = CartItem.query.filter_by(user_id=session['user_id']).all()
    cars = [item.car for item in items]
    total = sum(car.price for car in cars)
    return render_template('cart.html', cars=cars, total=total)

@app.route('/clear-cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('cart'))

@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    items = CartItem.query.filter_by(user_id=session['user_id']).all()
    for item in items:
        order = Order(user_id=item.user_id, car_id=item.car_id)
        db.session.add(order)
        db.session.delete(item)  # Remove from cart

    db.session.commit()
    return render_template('checkout.html')

@app.route('/filter')
def filter_cars():
    brand = request.args.get('brand')
    fuel = request.args.get('fuel')
    year = request.args.get('year')

    query = Car.query
    if brand:
        query = query.filter_by(brand=brand)
    if fuel:
        query = query.filter_by(fuel=fuel)
    if year:
        query = query.filter_by(year=year)

    cars = query.all()
    return render_template('filtered_cars.html', cars=cars)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            return "User already exists."

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        return "Invalid credentials."

    return render_template('user_login.html')

@app.route('/search')
def search():
    query = request.args.get('query', '')
    results = Car.query.filter(
        (Car.brand.ilike(f"%{query}%")) |
        (Car.model.ilike(f"%{query}%")) |
        (Car.fuel.ilike(f"%{query}%")) |
        (Car.condition.ilike(f"%{query}%"))
    ).all()
    return render_template('search_results.html', cars=results, query=query)

@app.route('/profile')
def profile():
    
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('profile.html', username=session['username'])

@app.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    orders = Order.query.filter_by(user_id=session['user_id']).all()
    return render_template('orders.html', orders=orders)

@app.route('/admin/users')
def admin_users():
    if 'admin_logged_in' not in session:
        return redirect(url_for('admin_login'))
    users = User.query.all()
    return render_template('admin_users.html', users=users)

@app.route('/logout_user')
def logout_user():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('login'))




if __name__ == '__main__':
    with app.app_context():
        db.create_all()  
    app.run(debug=True)

