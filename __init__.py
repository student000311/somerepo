import argparse
import os
import sqlite3
from datetime import datetime
from tabulate import tabulate

# Funkcja tworząca połączenie z bazą danych
def create_connection(db_file):
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(e)
    return None

# Funkcja wykonująca zapytanie SQL na bazie danych
def execute_query(conn, query, params=()):
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if query.strip().split(' ', 1)[0].lower() == 'select':
            return cursor.fetchall()
        else:
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error as e:
        print(e)
        return None

# Funkcja tworząca tag w bazie danych
def create_tag(conn, tag_name):
    try:
        # Check if the tag already exists
        existing_tag = execute_query(conn, 'SELECT id FROM Tags WHERE tag_name = ?', (tag_name,))
        if existing_tag:
            print(f'Tag "{tag_name}" already exists in the database.')
            return
        # If the tag doesn't exist, insert it into the database
        execute_query(conn, 'INSERT INTO Tags (tag_name) VALUES (?)', (tag_name,))
        print(f'Tag "{tag_name}" created successfully.')
    except sqlite3.Error as e:
        print(e)

# Funkcja usuwająca tag z bazy danych
def delete_tag(conn, tag_name):
    try:
        # Check if the tag is used in the FileTag table
        tag_in_use = execute_query(conn, 'SELECT COUNT(*) FROM FileTag WHERE tag_id = (SELECT id FROM Tags WHERE tag_name = ?)', (tag_name,))
        if tag_in_use[0][0] > 0:
            print(f'Tag "{tag_name}" is associated with one or more files and cannot be deleted.')
            return
        # If the tag is not used, proceed with deletion
        execute_query(conn, 'DELETE FROM Tags WHERE tag_name = ?', (tag_name,))
        print(f'Tag "{tag_name}" deleted successfully.')
    except sqlite3.Error as e:
        print(e)


# Funkcja importująca plik do bazy danych
def import_file(conn, file_fullname, tags):
    try:
        with open(file_fullname, 'rb') as file:
            file_data = file.read()
        file_name = os.path.basename(file_fullname)
        date_added = datetime.now().strftime('%Y-%m-%d')
        file_id = execute_query(conn, 'INSERT INTO Files (name, data, date_added) VALUES (?, ?, ?)',
                                (file_name, file_data, date_added))
        if file_id:
            for tag in tags:
                tag_id = execute_query(conn, 'SELECT id FROM Tags WHERE tag_name = ?', (tag,))
                if not tag_id:
                    print(f'Tag "{tag}" does not exist. Please create it first.')
                    return
                else:
                    tag_id = tag_id[0][0]
                execute_query(conn, 'INSERT INTO FileTag (file_id, tag_id) VALUES (?, ?)', (file_id, tag_id))
            print('File imported successfully.')
    except IOError as e:
        print(e)

# Funkcja eksportująca plik z bazy danych
def export_file(conn, file_id, file_fullname):
    file_data = execute_query(conn, 'SELECT data FROM Files WHERE id = ?', (file_id,))
    if file_data:
        try:
            with open(file_fullname, 'wb') as file:
                file.write(file_data[0][0])
            print('File exported successfully.')
        except IOError as e:
            print(e)
    else:
        print('File not found in the database.')

# Funkcja wyszukująca pliki na podstawie nazwy lub tagów
def find_files(conn, name=None, tags=None):
    query = 'SELECT Files.id, Files.name, Files.date_added, ' \
            '(SELECT GROUP_CONCAT(Tags.tag_name) FROM Tags ' \
            'JOIN FileTag ON Tags.id = FileTag.tag_id ' \
            'WHERE FileTag.file_id = Files.id) AS tags ' \
            'FROM Files '
    params = ()
    if name:
        query += 'WHERE Files.name LIKE ? '
        params += (f'%{name}%',)
    if tags:
        if name:
            query += 'AND (SELECT COUNT(*) FROM Tags ' \
                     'JOIN FileTag ON Tags.id = FileTag.tag_id ' \
                     'WHERE FileTag.file_id = Files.id AND Tags.tag_name IN ({seq})) = ? '
        else:
            query += 'WHERE (SELECT COUNT(*) FROM Tags ' \
                     'JOIN FileTag ON Tags.id = FileTag.tag_id ' \
                     'WHERE FileTag.file_id = Files.id AND Tags.tag_name IN ({seq})) = ? '
        query = query.format(seq=','.join(['?']*len(tags)))
        params += tuple(tags) + (len(tags),)
    result = execute_query(conn, query, params)
    if result:
        headers = ["id", "file_name", "date_added", "tags"]
        print(tabulate(result, headers=headers, tablefmt="grid"))
    else:
        print('No files found.')

# Funkcja tworząca nowy plik w bazie danych
def create_file(conn, file_name, tags):
    try:
        date_added = datetime.now().strftime('%Y-%m-%d')
        file_id = execute_query(conn, 'INSERT INTO Files (name, date_added) VALUES (?, ?)',
                                (file_name, date_added))
        if file_id:
            for tag in tags:
                tag_id = execute_query(conn, 'SELECT id FROM Tags WHERE tag_name = ?', (tag,))
                if not tag_id:
                    print(f'Tag "{tag}" does not exist. Please create it first.')
                    return
                else:
                    tag_id = tag_id[0][0]
                execute_query(conn, 'INSERT INTO FileTag (file_id, tag_id) VALUES (?, ?)', (file_id, tag_id))
            print('File created successfully.')
    except sqlite3.Error as e:
        print(e)

# Funkcja usuwająca plik z bazy danych
def delete_file(conn, file_id):
    try:
        execute_query(conn, 'DELETE FROM Files WHERE id = ?', (file_id,))
        print('File deleted successfully.')
    except sqlite3.Error as e:
        print(e)

# Funkcja dodająca tagi do istniejącego pliku
def add_tags(conn, file_id, tags):
    try:
        for tag in tags:
            tag_id = execute_query(conn, 'SELECT id FROM Tags WHERE tag_name = ?', (tag,))
            if not tag_id:
                print(f'Tag "{tag}" does not exist. Please create it first.')
                return
            else:
                tag_id = tag_id[0][0]
            execute_query(conn, 'INSERT INTO FileTag (file_id, tag_id) VALUES (?, ?)', (file_id, tag_id))
        print('Tags added successfully.')
    except sqlite3.Error as e:
        print(e)

# Funkcja usuwająca tagi z istniejącego pliku
def remove_tags(conn, file_id, tags):
    try:
        for tag in tags:
            tag_id = execute_query(conn, 'SELECT id FROM Tags WHERE tag_name = ?', (tag,))
            if tag_id:
                execute_query(conn, 'DELETE FROM FileTag WHERE file_id = ? AND tag_id = ?', (file_id, tag_id[0][0]))
        print('Tags removed successfully.')
    except sqlite3.Error as e:
        print(e)

# Funkcja otwierająca plik z bazy danych
def open_file(conn, file_id):
    file_data = execute_query(conn, 'SELECT data FROM Files WHERE id = ?', (file_id,))
    if file_data:
        # Tutaj można dodać kod otwierający plik w odpowiednim programie
        print('File opened successfully.')
    else:
        print('File not found in the database.')

# Główna funkcja obsługująca argumenty wiersza poleceń
def main():
    parser = argparse.ArgumentParser(description='Semantic File System CLI')
    parser.add_argument('command', choices=['import', 'export', 'find', 'create', 'delete', 'add_tags', 'remove_tags', 'open', 'create_tag', 'delete_tag'], help='Command to execute')
    parser.add_argument('--full_name', help='Full name of the file in filesystem')
    parser.add_argument('--id', type=int, help='ID of the file in the database')
    parser.add_argument('--name', help='Name of the file')
    parser.add_argument('--tags', nargs='+', help='Tags associated with the file')
    parser.add_argument('--tag', help='Tag name')
    args = parser.parse_args()

    db_file = 'db.db'
    conn = create_connection(db_file)

    if conn:
        if args.command == 'create_tag':
            create_tag(conn, args.tag)
        elif args.command == 'delete_tag':
            delete_tag(conn, args.tag)
        elif args.command == 'import':
            import_file(conn, args.full_name, args.tags)
        elif args.command == 'export':
            export_file(conn, args.id, args.full_name)
        elif args.command == 'find':
            find_files(conn, args.name, args.tags)
        elif args.command == 'create':
            create_file(conn, args.name, args.tags)
        elif args.command == 'delete':
            delete_file(conn, args.id)
        elif args.command == 'add_tags':
            add_tags(conn, args.id, args.tags)
        elif args.command == 'remove_tags':
            remove_tags(conn, args.id, args.tags)
        elif args.command == 'open':
            open_file(conn, args.id)
        conn.close()
    else:
        print('Error: Unable to establish connection to the database.')

if __name__ == '__main__':
    main()
