import os
import psycopg2
from dotenv import load_dotenv
import pandas as pd

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

db = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resources', 'upd_recipes_ingredients.csv'))

cursor.execute("""
    DROP TABLE IF EXISTS recipes;
    CREATE TABLE recipes (
        id SERIAL PRIMARY KEY,
        name TEXT,
        ingredients TEXT,
        ingredients_raw TEXT,
        steps TEXT,
        servings FLOAT,
        serving_size TEXT,
        created_by TEXT DEFAULT NULL
        lang VARCHAR(5)
    );
""")

for i, row in db.iterrows():
    cursor.execute("""
        INSERT INTO recipes (name, ingredients, ingredients_raw, steps, servings, serving_size)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        row['name'],
        row['ingredients'],
        row['ingredients_raw'],
        row['steps'],
        row['servings'],
        row['serving_size']
    ))


connection.commit()
cursor.close()
connection.close()
