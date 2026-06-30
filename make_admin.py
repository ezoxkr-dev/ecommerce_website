import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def make_admin(username):
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not found in .env")
        return
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = 'admin' WHERE username = %s", (username,))
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
