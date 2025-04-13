import pandas as pd
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

connection = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user = os.getenv("DB_USER"),
    host = os.getenv("DB_HOST"),
    password = os.getenv("DB_PASSWORD")
)
cursor = connection.cursor()

ds = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'recipes_ingredients.csv'))

