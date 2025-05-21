import os
import psycopg2
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

connection = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user = os.getenv("DB_USER"),
    host = os.getenv("DB_HOST"),
    password = os.getenv("DB_PASSWORD")
)
cursor = connection.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS ratings (
        id SERIAL PRIMARY KEY,
        recipe_id INTEGER NOT NULL,
        user_id BIGINT NOT NULL,
        username TEXT,
        rating INTEGER CHECK (rating >= 1 AND rating <= 5),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
    );
""")

connection.commit()
cursor.close()
connection.close()
