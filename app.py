from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__, static_folder='static')
app.secret_key = 'your_secret_key'

# Function to establish SQLite connection
def get_db_connection():
    conn = sqlite3.connect('wypozyczalnia.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template(
        'index.html', navbar=render_template(
            'navbar.html', logged_in= True if 'user_id' in session else False
            )
        )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        student_id = request.form['student_id']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM Users WHERE student_id = ? AND password = ?', (student_id, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['user_id']
            return redirect(url_for('search'))
        else:
            return render_template(
                'login_page.html', error='Błędny użytkownik lub hasło', navbar=render_template(
                    'navbar.html', logged_in= True if 'user_id' in session else False
                    )
                )
    return render_template(
        'login_page.html', error=None, navbar=render_template(
            'navbar.html', logged_in= True if 'user_id' in session else False
            )
        )

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/search') # , methods=['GET', 'POST']
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    search_term = request.args.get('search_term')
    if search_term:
        conn = get_db_connection()
        db_books = conn.execute('SELECT * FROM Books WHERE title LIKE ?', ('%' + search_term + '%',)).fetchall()
        conn.close()

        books = []
        for db_book in db_books:
            book = {
                'title': db_book['title'],
                'author': db_book['author'],
                'genre': db_book['genre'],
                'description': db_book['description'],
                'year': db_book['year'],
                'quantity': db_book['count'],
                'isbn': db_book['isbn'],
                'image': db_book['book_img'],  # Assuming book_img is the image URL
                'id': db_book['book_id']  # Assuming /book/<book_id> is the route to view book details
            }
            books.append(book)

        return render_template(
            'search_page.html', books=books, navbar=render_template(
                'navbar.html', logged_in= True if 'user_id' in session else False
                )
            )

    conn = get_db_connection()
    db_books = conn.execute('SELECT * FROM Books').fetchall()
    conn.close()

    books = []
    for db_book in db_books:
        book = {
            'title': db_book['title'],
            'author': db_book['author'],
            'genre': db_book['genre'],
            'description': db_book['description'],
            'year': db_book['year'],
            'quantity': db_book['count'],
            'isbn': db_book['isbn'],
            'image': db_book['book_img'],  # Assuming book_img is the image URL
            'id': db_book['book_id']  # Assuming /book/<book_id> is the route to view book details
        }
        books.append(book)

    return render_template(
        'search_page.html', books=books, navbar=render_template(
            'navbar.html', logged_in= True if 'user_id' in session else False
            )
        )

@app.route('/book/<int:book_id>')
def book(book_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    db_book = conn.execute('SELECT * FROM Books WHERE book_id = ?', (book_id,)).fetchone()
    conn.close()

    book = {
        'title': db_book['title'],
        'author': db_book['author'],
        'genre': db_book['genre'],
        'description': db_book['description'],
        'year': db_book['year'],
        'quantity': db_book['count'],
        'isbn': db_book['isbn'],
        'image': db_book['book_img'],  # Assuming book_img is the image URL
        'id': db_book['book_id']  # Assuming /book/<book_id> is the route to view book details
    }

    if db_book is None:
        return render_template(
            'error.html', message='Book not found', navbar=render_template( # TODO
                'navbar.html', logged_in= True if 'user_id' in session else False
                )
            ), 404
    return render_template(
        'book_page.html', book=book, navbar=render_template(
            'navbar.html', logged_in= True if 'user_id' in session else False
            )
        )

@app.route('/borrow/<int:book_id>')
def borrow(book_id):
    conn = get_db_connection()
    conn.execute('INSERT INTO Borrowed_Books (user_id, book_id, date_borrowed, date_of_return) VALUES (?, ?, CURRENT_DATE, DATE("now", "+7 days"))', (session['user_id'], book_id))
    conn.commit()
    conn.close()
    return redirect(url_for('borrowed_books'))

@app.route('/borrowed_books')
def borrowed_books():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    user_id = session['user_id']
    db_borrowed_books = conn.execute('''
        SELECT Books.book_img, Books.title, Books.book_id, Borrowed_Books.date_of_return
        FROM Borrowed_Books
        INNER JOIN Books ON Borrowed_Books.book_id = Books.book_id
        WHERE Borrowed_Books.user_id = ?
    ''', (user_id,)).fetchall()
    conn.close()

    books = []
    for db_book in db_borrowed_books:
        book = {
            'title': db_book['title'],
            'image': db_book['book_img'],  # Assuming book_img is the image URL
            'id': db_book['book_id'],  # Assuming /book/<book_id> is the route to view book details
            'date_of_return': db_book['date_of_return'],
        }
        books.append(book)
        print(book['title'])
    
    return render_template(
        'borrowed_books_page.html', books=books, navbar=render_template(
            'navbar.html', logged_in= True if 'user_id' in session else False
            )
        )




if __name__ == '__main__':
    app.run(debug=True)