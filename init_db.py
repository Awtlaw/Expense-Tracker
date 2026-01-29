"""
Database initialization script
Creates tables and indexes for the Expense Tracker application
"""

import sqlite3
import os

DATABASE = "database.db"

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create income table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS income (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            source TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Create expenses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    # Create budgets table (for future budget feature)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            budget_limit REAL NOT NULL,
            month TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, category, month)
        )
    ''')
    
    # Create indexes for performance optimization
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_income_user_id ON income(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_income_date ON income(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(date)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_budgets_user_id ON budgets(user_id)')
    
    conn.commit()
    conn.close()
    
    print(f"✓ Database '{DATABASE}' initialized successfully!")

if __name__ == "__main__":
    init_db()
