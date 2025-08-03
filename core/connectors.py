import psycopg2

# Connect to the School database
conn = psycopg2.connect(
    dbname="school",
    user="postgres",
    password="jack11",
    host="localhost"
)