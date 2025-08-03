# PostgreSQL Support for LazyQL

This update adds PostgreSQL support to the LazyQL application, allowing you to connect to both SQLite and PostgreSQL databases.

## New Features

### Database Type Selection
- Choose between SQLite and PostgreSQL from the dropdown menu
- Dynamic UI that shows/hides relevant connection fields based on database type

### SQLite Connection
- Browse and select SQLite database files (.db, .sqlite3)
- Supports both relative and absolute file paths

### PostgreSQL Connection
- Host configuration (default: localhost)
- Port configuration (default: 5432)
- Database name
- Username and password fields
- Secure password field (hidden input)

## Installation

### Prerequisites
1. Install PostgreSQL on your system
2. Create a PostgreSQL database for testing

### Dependencies
The following dependency has been added to `requirements.txt`:
```
psycopg2-binary==2.9.9
```

Install the new dependency:
```bash
pip install psycopg2-binary==2.9.9
```

## Usage

### Connecting to PostgreSQL
1. Open the application
2. Go to the "DB Connections" tab
3. Select "postgresql" from the database type dropdown
4. Fill in your PostgreSQL connection details:
   - **Host**: Your PostgreSQL server address (e.g., localhost)
   - **Port**: PostgreSQL port (default: 5432)
   - **Database**: Name of your database
   - **Username**: Your PostgreSQL username
   - **Password**: Your PostgreSQL password
5. Click "Connect"

### Connecting to SQLite
1. Select "sqlite" from the database type dropdown
2. Click "Browse" to select your SQLite database file
3. Click "Connect"

## Technical Details

### Database Loader Updates
- `DatabaseLoader` now supports both SQLite and PostgreSQL
- Automatic database type detection from connection URL
- Appropriate test queries for each database type:
  - SQLite: `SELECT type, name, tbl_name, sql FROM sqlite_master;`
  - PostgreSQL: `SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';`

### SQL Dialect Handling
- Dynamic SQL dialect detection in `GeminiModelLoader`
- Proper dialect specification in system messages for LLM queries
- Support for PostgreSQL-specific SQL syntax

### UI Improvements
- Dynamic field visibility based on database type
- Improved error handling and user feedback
- Secure password field for PostgreSQL connections

## Testing

Run the test script to verify connections:
```bash
python test_postgresql.py
```

This will test both SQLite and PostgreSQL connections (requires PostgreSQL setup).

## Error Handling

The application now provides specific error messages for:
- Missing required fields
- Connection failures
- Database type detection errors
- SQL dialect issues

## Security Notes

- Passwords are hidden in the UI but stored in memory during the session
- Consider using environment variables for production PostgreSQL credentials
- Connection strings are logged for debugging (remove in production)

## Migration from SQLite-only

Existing SQLite functionality remains unchanged. The application will:
- Default to SQLite database type
- Maintain backward compatibility with existing SQLite databases
- Preserve all existing features and UI elements 