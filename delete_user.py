import psycopg2
import os
from dotenv import load_dotenv
import sys

load_dotenv()

def delete_user(username_or_email):
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL not found in .env")
        return
        
    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    # First get the user ID
    cursor.execute('SELECT id, username, email FROM users WHERE username = %s OR email = %s', (username_or_email, username_or_email))
    user = cursor.fetchone()
    
    if not user:
        print(f"Error: User '{username_or_email}' not found.")
        conn.close()
        return
        
    user_id = user[0]
    username = user[1]
    
    print(f"Found user: {username} (ID: {user_id})")
    
    confirm = input(f"Are you sure you want to permanently delete user '{username}' and all their orders? (yes/no): ")
    
    if confirm.lower() == 'yes':
        # Delete orders first (foreign key constraint)
        cursor.execute('DELETE FROM orders WHERE user_id = %s', (user_id,))
        orders_deleted = cursor.rowcount
        
        # Delete user
        cursor.execute('DELETE FROM users WHERE id = %s', (user_id,))
        
        conn.commit()
        print(f"Successfully deleted user '{username}' and {orders_deleted} associated orders.")
    else:
        print("Deletion cancelled.")
        
    conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        delete_user(sys.argv[1])
    else:
        target = input("Enter username or email to delete: ")
        if target:
            delete_user(target)
