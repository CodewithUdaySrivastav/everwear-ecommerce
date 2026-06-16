from flask import Flask, render_template, session, redirect
from flask_mysqldb import MySQL
from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "everwear_secret"

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root@bs6SQL'
app.config['MYSQL_DB'] = 'everwear'

mysql = MySQL(app)

@app.route('/category/<category>')
def category_products(category):

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT * FROM products
        WHERE category=%s
        """,
        [category]
    )

    products = cur.fetchall()

    return render_template(
        'search_results.html',
        products=products,
        query=category
    )

@app.route('/admin/products')
def manage_products():

    if session.get('role') != 'admin':
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM products")

    products = cur.fetchall()

    return render_template(
        'manage_products.html',
        products=products
    )

@app.route('/admin/delete-product/<int:id>')
def delete_product(id):

    if session.get('role') != 'admin':
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute(
        "DELETE FROM products WHERE id=%s",
        [id]
    )

    mysql.connection.commit()

    return redirect('/admin/products')

@app.route('/admin/edit-product/<int:id>', methods=['GET','POST'])
def edit_product(id):

    if session.get('role') != 'admin':
        return redirect('/')

    cur = mysql.connection.cursor()

    if request.method == 'POST':

        name = request.form['name']
        price = request.form['price']
        image = request.form['image']
        description = request.form['description']
        category = request.form['category']

        cur.execute(
            """
            UPDATE products
            SET name=%s,
                price=%s,
                image=%s,
                description=%s,
                category=%s
            WHERE id=%s
            """,
            (name, price, image, description,category, id)
        )

        mysql.connection.commit()

        return redirect('/admin/products')

    cur.execute(
        "SELECT * FROM products WHERE id=%s",
        [id]
    )

    product = cur.fetchone()

    return render_template(
        'edit_product.html',
        product=product
    )

@app.route('/admin/add-product', methods=['GET', 'POST'])
def add_product():

    if session.get('role') != 'admin':
        return redirect('/')

    if request.method == 'POST':

        name = request.form['name']
        price = request.form['price']

        image = request.files['image']

        filename = secure_filename(image.filename)

        image.save(
            os.path.join(
                'static/uploads',
                filename
            )
        )

        image_path = '/static/uploads/' + filename

        description = request.form['description']
        category = request.form['category']

        cur = mysql.connection.cursor()

        cur.execute(
            """
            INSERT INTO products
            (name,price,image,description,category)
            VALUES(%s,%s,%s,%s,%s)
            """,
            (name, price, image_path, description, category)
        )

        mysql.connection.commit()

        return redirect('/')

    return render_template('add_product.html')

@app.route('/admin')
def admin():

    if session.get('role') != 'admin':
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM products")
    product_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM users")
    user_count = cur.fetchone()[0]

    order_count = 0

    return render_template(
        'admin.html',
        product_count=product_count,
        user_count=user_count,
        order_count=order_count
    )

@app.route('/register', methods=['GET','POST'])
def register():

    if request.method == 'POST':

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=%s",
            [email]
        )

        existing = cur.fetchone()

        if existing:

            flash("Email already exists")
            return redirect('/register')

        hashed_password = generate_password_hash(password)

        cur.execute(
            "INSERT INTO users(name,email,password) VALUES(%s,%s,%s)",
            (name,email,hashed_password)
        )

        mysql.connection.commit()

        flash("Account Created Successfully")

        return redirect('/login')

    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT * FROM users WHERE email=%s",
            [email]
        )

        user = cur.fetchone()

        if user and check_password_hash(user[3], password):

            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['role'] = user[4]

            return redirect('/')

        flash("Invalid Email or Password")

    return render_template('login.html')

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')

@app.route('/')
def home():

    search = request.args.get('search')

    cur = mysql.connection.cursor()

    if search:

        cur.execute(
            """
            SELECT * FROM products
            WHERE name LIKE %s
            """,
            ['%' + search + '%']
        )

    else:

        cur.execute(
            "SELECT * FROM products"
        )

    products = cur.fetchall()

    return render_template(
        'index.html',
        products=products
    )

@app.route('/search')
def search():

    query = request.args.get('q')

    cur = mysql.connection.cursor()

    cur.execute(
        """
        SELECT * FROM products
        WHERE name LIKE %s
        """,
        ['%' + query + '%']
    )

    products = cur.fetchall()

    return render_template(
        'search_results.html',
        products=products,
        query=query
    )

@app.route('/product/<int:id>')
def product_details(id):

    cur = mysql.connection.cursor()

    cur.execute(
        "SELECT * FROM products WHERE id=%s",
        [id]
    )

    product = cur.fetchone()

    return render_template(
        'product_details.html',
        product=product
    )
@app.route('/add_to_cart/<int:id>')
def add_to_cart(id):

    if 'cart' not in session:
        session['cart'] = {}

    cart = session['cart']

    pid = str(id)

    if pid in cart:
        cart[pid] += 1
    else:
        cart[pid] = 1

    session['cart'] = cart

    return redirect('/cart')

@app.route('/cart')
def cart():

    cart_items = []

    total = 0

    cart = session.get('cart', {})

    cur = mysql.connection.cursor()

    for pid, qty in cart.items():

        cur.execute(
            "SELECT * FROM products WHERE id=%s",
            [pid]
        )

        product = cur.fetchone()

        if product:

            subtotal = float(product[2]) * qty

            total += subtotal

            cart_items.append({
                'id': product[0],
                'name': product[1],
                'price': product[2],
                'image': product[3],
                'description': product[4],
                'qty': qty,
                'subtotal': subtotal
            })

    return render_template(
        'cart.html',
        cart_items=cart_items,
        total=total
    )

@app.route('/increase/<int:id>')
def increase(id):

    cart = session.get('cart', {})

    pid = str(id)

    if pid in cart:
        cart[pid] += 1

    session['cart'] = cart

    return redirect('/cart')
@app.route('/decrease/<int:id>')
def decrease(id):

    cart = session.get('cart', {})

    pid = str(id)

    if pid in cart:

        cart[pid] -= 1

        if cart[pid] <= 0:
            del cart[pid]

    session['cart'] = cart

    return redirect('/cart')
@app.route('/remove/<int:id>')
def remove(id):

    cart = session.get('cart', {})

    pid = str(id)

    if pid in cart:
        del cart[pid]

    session['cart'] = cart

    return redirect('/cart')

@app.route('/clear_cart')
def clear_cart():

    session.pop('cart', None)

    return "Cart Cleared"

if __name__ == '__main__':
    app.run(debug=True)


    