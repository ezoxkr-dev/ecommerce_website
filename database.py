import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def init_db():
    database_url = os.getenv("DATABASE_URL")
    if not database_url or database_url == "postgres://user:password@hostname:5432/dbname":
        print("Please configure a valid DATABASE_URL in your .env file.")
        return

    conn = psycopg2.connect(database_url)
    cursor = conn.cursor()
    
    # Drop existing tables for fresh schema
    cursor.execute('DROP TABLE IF EXISTS orders CASCADE')
    cursor.execute('DROP TABLE IF EXISTS users CASCADE')
    
    # Create Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'customer',
            reset_token TEXT,
            reset_expiry TIMESTAMP
        )
    ''')
    
    # Create Orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            order_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            product TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            code TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            admin_message TEXT,
            rating INTEGER,
            review TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized with new schema (PostgreSQL).")
