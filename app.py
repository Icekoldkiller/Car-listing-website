from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from models import CartItem, Car, User,db
from flask_migrate import Migrate
import os

app = Flask(__name__)
app.secret_key = 'supersecret'
migrate = Migrate(app, db)

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

# --- Models --  

bookmarks = db.Table('bookmarks',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('car_id', db.Integer, db.ForeignKey('car.id'))
)  
 
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
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    seller = db.relationship('User', back_populates='listed_cars')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True)
    password_hash = db.Column(db.String(120))

    listed_cars = db.relationship('Car', back_populates='seller')
    bookmarked_cars = db.relationship('Car', secondary=bookmarks, backref='bookmarked_by')

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
    car = db.relationship('Car')


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

@app.route('/car/<int:car_id>')
def car_detail(car_id):
    car = Car.query.get_or_404(car_id)
    return render_template('car_detail.html', car=car)


@app.route('/logout')
def logout_admin():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id

            # Merge session cart with DB cart
            session_cart = session.pop('cart', [])
            for car_id in session_cart:
                exists = CartItem.query.filter_by(user_id=user.id, car_id=car_id).first()
                if not exists:
                    item = CartItem(user_id=user.id, car_id=car_id)
                    db.session.add(item)
            db.session.commit()

            flash('Logged in successfully.')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials.')
    return render_template('User_login.html')

@app.route('/add-to-cart/<int:car_id>')
def add_to_cart(car_id):
    if 'user_id' in session:
        existing = CartItem.query.filter_by(user_id=session['user_id'], car_id=car_id).first()
        if not existing:
            item = CartItem(user_id=session['user_id'], car_id=car_id)
            db.session.add(item)
            db.session.commit()
    else:
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
    return redirect(url_for('cart_page'))

@app.route('/cart')
def cart():
    if 'user_id' in session:
        items = CartItem.query.filter_by(user_id=session['user_id']).all()
        cars = [item.car for item in items]
    else:
        cart_ids = session.get('cart', [])
        cars = Car.query.filter(Car.id.in_(cart_ids)).all()
    total = sum(car.price for car in cars)
    return render_template('cart.html', cars=cars, total=total)


@app.route('/clear-cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('cart_page'))

@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        flash('You must be logged in to proceed to checkout.', 'error')
        return redirect(url_for('login'))

    return render_template('checkout.html')

@app.route('/finalize-checkout')
def finalize_checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    items = CartItem.query.filter_by(user_id=user_id).all()

    for item in items:
        order = Order(user_id=user_id, car_id=item.car_id)
        db.session.add(order)
        db.session.delete(item)

    db.session.commit()
    return redirect(url_for('orders'))

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
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to view your profile.")
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    return render_template('profile.html', user=user, user_cars=user.listed_cars, bookmarks=user.bookmarked_cars)

@app.route('/orders')
def orders():
    if 'user_id' not in session:
        flash('Please log in to view your order history.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_orders = Order.query.filter_by(user_id=user_id).all()
    return render_template('orders.html', orders=user_orders)

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

@app.route('/confirm-checkout', methods=['POST'])
def confirm_checkout():
    if 'user_id' not in session:
        flash('You must be logged in to place an order.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    items = CartItem.query.filter_by(user_id=user_id).all()
    for item in items:
        order = Order(user_id=user_id, car_id=item.car_id)
        db.session.add(order)
        db.session.delete(item)
    db.session.commit()

    flash('Order placed successfully!', 'success')
    return redirect(url_for('orders'))

@app.route('/add_car_user', methods=['GET', 'POST'])
def add_car_user():
    if request.method == 'POST':
        brand = request.form['brand']
        model = request.form['model']
        mileage = request.form['mileage']
        year = request.form['year']
        fuel = request.form['fuel']
        condition = request.form['condition']
        price = request.form['price']
        image_file = request.files['image']

        image_filename = None
        if image_file:
            image_filename = image_file.filename
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)

        car = Car(
            brand=brand,
            model=model,
            mileage=mileage,
            year=year,
            fuel=fuel,
            condition=condition,
            price=price,
            image=image_filename,
            seller_id=session.get('user_id')  # FIXED
        )
        db.session.add(car)
        db.session.commit()
        flash('Your car has been listed for sale!', 'success')
        return redirect(url_for('profile'))

    return render_template('add_car_user.html')


@app.route('/bookmark/<int:car_id>', methods=['POST'])
def bookmark(car_id):
    if 'user_id' not in session:
        flash("You must log in to bookmark cars.")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    car = Car.query.get_or_404(car_id)

    if car not in user.bookmarked_cars:
        user.bookmarked_cars.append(car)
        db.session.commit()
        flash("Car bookmarked!")
    else:
        flash("You’ve already bookmarked this car.")

    return redirect(url_for('car_detail', car_id=car_id))




if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
