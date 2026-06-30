import sqlite3

def make_admin(username):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = 'admin' WHERE username = ?", (username,))
    conn.commit()
    count = cursor.rowcount
    conn.close()
    if count > 0:
        print(f"User '{username}' is now an admin.")
    else:
        print(f"User '{username}' not found.")

if __name__ == "__main__":
    target_username = input("Enter the username to make admin: ")
    if target_username:
        make_admin(target_username)
