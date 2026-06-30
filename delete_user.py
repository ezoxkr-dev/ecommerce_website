import sqlite3
import sys

def delete_user(username_or_email):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get the user id
    cursor.execute('SELECT id, username, email FROM users WHERE username = ? OR email = ?', (username_or_email, username_or_email))
    user = cursor.fetchone()
    
    if not user:
        print(f"User '{username_or_email}' not found.")
        conn.close()
        return
        
    user_id = user[0]
    username = user[1]
    
    confirm = input(f"Are you sure you want to delete user '{username}' (ID: {user_id}) and all their orders? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        conn.close()
        return
        
    # Delete orders first 
    cursor.execute('DELETE FROM orders WHERE user_id = ?', (user_id,))
    orders_deleted = cursor.rowcount
    
    # Delete the user
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    
    conn.commit()
    print(f"Deleted user '{username}' and {orders_deleted} associated orders.")
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        delete_user(sys.argv[1])
    else:
        target = input("Enter username or email of the user to delete: ")
        if target:
            delete_user(target)
