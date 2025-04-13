import pandas as pd
import os

ds = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources', 'recipes_ingredients.csv'))
