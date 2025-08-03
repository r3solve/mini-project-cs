#!/usr/bin/env python3
"""
Test script to verify PostgreSQL connection functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.loaders import DatabaseLoader

def test_postgresql_connection():
    """Test PostgreSQL connection with sample credentials"""
    
    # Example PostgreSQL connection string
    # Replace with your actual PostgreSQL credentials
    postgres_url = "postgresql://username:password@localhost:5432/testdb"
    
    try:
        print("Testing PostgreSQL connection...")
        db_loader = DatabaseLoader(postgres_url)
        db_instance = db_loader.get_instance()
        db_type = db_loader.get_db_type()
        
        print(f"Successfully connected to {db_type} database!")
        print(f"Database dialect: {db_instance.dialect}")
        
        # Test a simple query
        result = db_instance.run("SELECT version();")
        print(f"Database version: {result}")
        
    except Exception as e:
        print(f"Connection failed: {str(e)}")
        print("\nTo test PostgreSQL connection:")
        print("1. Make sure PostgreSQL is installed and running")
        print("2. Create a test database")
        print("3. Update the connection string in this script with your credentials")
        print("4. Run: python test_postgresql.py")

def test_sqlite_connection():
    """Test SQLite connection"""
    
    sqlite_url = "sqlite:///Chinook.db"
    
    try:
        print("\nTesting SQLite connection...")
        db_loader = DatabaseLoader(sqlite_url)
        db_instance = db_loader.get_instance()
        db_type = db_loader.get_db_type()
        
        print(f"Successfully connected to {db_type} database!")
        print(f"Database dialect: {db_instance.dialect}")
        
        # Test a simple query
        result = db_instance.run("SELECT name FROM sqlite_master WHERE type='table';")
        print(f"Available tables: {result}")
        
    except Exception as e:
        print(f"SQLite connection failed: {str(e)}")

if __name__ == "__main__":
    print("Testing database connections...")
    
    # Test SQLite (should work with existing Chinook.db)
    test_sqlite_connection()
    
    # Test PostgreSQL (requires setup)
    test_postgresql_connection() 