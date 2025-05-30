import pandas as pd
import os

db = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resources', 'recipes_ingredients.csv'))

db.drop(['description', 'tags', 'id'], axis=1, inplace=True)

db.where(pd.notnull(db),None)

db['lang'] = "en"

db['created_by'] = None

db.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resources', 'upd_recipes_ingredients.csv'))
