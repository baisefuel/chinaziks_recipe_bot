import csv
import unittest
import os

class TestCSVImport(unittest.TestCase):
    test_csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'resources', 'upd_recipes_ingredients.csv')

    def test_file_exists(self):
        """Проверяет, что файл существует"""
        self.assertTrue(os.path.exists(self.test_csv_path))
    
    def test_file_is_csv(self):
        """Проверяет, что файл имеет расширение .csv"""
        self.assertTrue(self.test_csv_path.endswith('.csv'))
    
    def test_csv_has_correct_headers(self):
        """Проверяет, что CSV содержит правильные заголовки"""
        with open(self.test_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            expected_headers = ['id', 'name','ingredients','ingredients_raw','steps','servings','serving_size','created_by']
            self.assertEqual(headers, expected_headers)
    
    def test_csv_has_data_rows(self):
        """Проверяет, что CSV содержит данные"""
        with open(self.test_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)
            rows = list(reader)
            self.assertGreater(len(rows), 0)

    if __name__ == 'main':
        unittest.main()