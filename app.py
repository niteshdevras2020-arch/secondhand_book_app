from flask import Flask, render_template, request, redirect, session, flash
import pymysql
import os
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = "secondhand_book_app_secret_123"


database_url = os.environ.get("DATABASE_URL")

if database_url:
    url = urlparse(database_url)
    db = pymysql.connect(
        host=url.hostname,
        user=url.username,
        password=url.password,
        database=url.path.lstrip('/'),
        port=url.port
    )
else:
    db = pymysql.connect(
        host="localhost",
        user="root",
        password="",
        database="secondhand_books"
    )

cursor = db.cursor()

@app.route('/')
def home():
    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        sql = "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)"
        val = (name, email, password, role)
        cursor.execute(sql, val)
        db.commit()

        return redirect('/')

    return render_template("register.html")

# ---------------- LOGIN ----------------
@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/login/<role>", methods=["GET", "POST"])
def login_role(role):

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        sql = "SELECT * FROM users WHERE email=%s AND password=%s AND role=%s"
        val = (email, password, role)

        cursor.execute(sql, val)
        user = cursor.fetchone()

        if user:
            session["user_id"] = user[0]
            session["role"] = role

            if role == "admin":
                return redirect("/dashboard")
            elif role == "seller":
                return redirect("/seller_dashboard")
            else:
                return redirect("/user_dashboard")

        else:
            flash(f"Invalid {role.capitalize()} Login!", "danger")
            return redirect(f"/login/{role}")

    return render_template("login_form.html", role=role)
# ---------------- ADD BOOK ----------------
@app.route("/books")
def view_books():
    search = request.args.get("search", "")

    cursor = db.cursor()

    if search:
        sql = "SELECT id, title, author, price, seller_id, status FROM books WHERE title LIKE %s OR author LIKE %s"
        val = ("%" + search + "%", "%" + search + "%")
        cursor.execute(sql, val)
    else:
        cursor.execute("SELECT id, title, author, price, seller_id, status FROM books")

    books = cursor.fetchall()
    return render_template("books.html", books=books, search=search)

@app.route("/buy/<int:book_id>", methods=["GET", "POST"])
def buy(book_id):

    if "user_id" not in session:
        return redirect("/login/user")

    if request.method == "POST":
        address = request.form["address"]
        phone = request.form["phone"]
        user_id = session["user_id"]

        cursor = db.cursor()

        cursor.execute(
            "INSERT INTO orders (book_id, user_id, address, phone) VALUES (%s, %s, %s, %s)",
            (book_id, user_id, address, phone)
        )

        cursor.execute(
            "UPDATE books SET status='sold' WHERE id=%s",
            (book_id,)
        )

        db.commit()

        flash("Order Placed Successfully!", "success")
        return redirect("/orders")

    return render_template("buy_form.html", book_id=book_id)

@app.route("/orders")
def view_orders():

    if "user_id" not in session:
        return redirect("/login")

    cursor = db.cursor()

    if session["role"] == "admin":
        cursor.execute("""
            SELECT orders.id, books.title, books.author, books.price, orders.order_date
            FROM orders
            JOIN books ON orders.book_id = books.id
            ORDER BY orders.id DESC
        """)
    else:
        cursor.execute("""
            SELECT orders.id, books.title, books.author, books.price, orders.order_date
            FROM orders
            JOIN books ON orders.book_id = books.id
            WHERE orders.user_id = %s
            ORDER BY orders.id DESC
        """, (session["user_id"],))

    orders = cursor.fetchall()
    return render_template("orders.html", orders=orders)

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/seller_dashboard")
def seller_dashboard():
    return render_template("seller_dashboard.html")


@app.route("/user_dashboard")
def user_dashboard():
    return render_template("user_dashboard.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/back")
def back():
    role = session.get("role", "user")

    if role == "admin":
        return redirect("/dashboard")
    elif role == "seller":
        return redirect("/seller_dashboard")
    else:
        return redirect("/user_dashboard")
    
@app.route("/seller_add_book_page")
def seller_add_book_page():
    if session.get("role") != "seller":
        return redirect("/")
    return render_template("seller_add_book.html")

@app.route("/seller_add_book", methods=["POST"])
def seller_add_book():
    title = request.form['title']
    author = request.form['author']
    price = request.form['price']

    seller_id = session["user_id"]

    cursor = db.cursor()

    sql = "INSERT INTO books (title, author, price, seller_id, status) VALUES (%s, %s, %s, %s, %s)"
    val = (title, author, price, seller_id, "available")

    cursor.execute(sql, val)
    db.commit()

    flash("Book Added Successfully!", "success")
    return redirect("/seller_dashboard")

@app.route("/seller_books")
def seller_books():
    if session.get("role") != "seller":
        return redirect("/")

    seller_id = session["user_id"]

    cursor = db.cursor()
    cursor.execute("SELECT id, title, author, price FROM books WHERE seller_id=%s", (seller_id,))
    books = cursor.fetchall()

    return render_template("seller_books.html", books=books)

@app.route("/seller/delete_book/<int:book_id>")
def seller_delete_book(book_id):
    if session.get("role") != "seller":
        return redirect("/")

    seller_id = session["user_id"]

    cursor = db.cursor()
    cursor.execute("DELETE FROM books WHERE id=%s AND seller_id=%s", (book_id, seller_id))
    db.commit()

    flash("Book Deleted Successfully!", "success")
    return redirect("/seller_books")

@app.route("/seller_orders")
def seller_orders():
    if session.get("role") != "seller":
        return redirect("/")

    seller_id = session["user_id"]

    cursor = db.cursor()
    cursor.execute("""
        SELECT orders.id, books.title, books.author, books.price, orders.order_date, orders.address, orders.phone, orders.status
        FROM orders
        JOIN books ON orders.book_id = books.id
        WHERE books.seller_id = %s
        ORDER BY orders.id DESC
    """, (seller_id,))

    orders = cursor.fetchall()
    return render_template("seller_orders.html", orders=orders)

@app.route("/update_status/<int:order_id>")
def update_status(order_id):
    cursor = db.cursor()
    cursor.execute("UPDATE orders SET status='Delivered' WHERE id=%s", (order_id,))
    db.commit()
    return redirect("/seller_orders")

@app.route("/admin/users")
def admin_users():
    if session.get("role") != "admin":
        return redirect("/")

    cursor = db.cursor()
    cursor.execute("SELECT id, name, email, role FROM users")
    users = cursor.fetchall()

    return render_template("admin_users.html", users=users)

@app.route("/admin/delete_user/<int:user_id>")
def delete_user(user_id):
    if session.get("role") != "admin":
        return redirect("/")

    cursor = db.cursor()
    cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
    db.commit()

    return redirect("/admin/users")

@app.route("/admin/books")
def admin_books():
    if session.get("role") != "admin":
        return redirect("/")

    cursor = db.cursor()
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()

    return render_template("admin_books.html", books=books)

@app.route("/admin/delete_book/<int:book_id>")
def delete_book(book_id):
    if session.get("role") != "admin":
        return redirect("/")

    cursor = db.cursor()
    cursor.execute("DELETE FROM books WHERE id=%s", (book_id,))
    db.commit()

    return redirect("/admin/books")


if __name__ == "__main__":
    app.run(debug=True)
