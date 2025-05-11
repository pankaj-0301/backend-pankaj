import unittest

from nutrition_app import convert_to_grams  # Replace with your actual import

class TestQuantityConversion(unittest.TestCase):
    def test_oil_tbsp(self):
        self.assertAlmostEqual(convert_to_grams(1, "tbsp", "oil"), 13.0, places=2)
        self.assertAlmostEqual(convert_to_grams(2, "tbsp", "mustard oil"), 26.0, places=2)
    
    def test_sugar_tbsp(self):
        self.assertAlmostEqual(convert_to_grams(1, "tbsp", "sugar"), 12.5, places=2)
        self.assertAlmostEqual(convert_to_grams(3, "tbsp", "sugar"), 37.5, places=2)
    
    def test_flour_tbsp(self):
        self.assertAlmostEqual(convert_to_grams(1, "tbsp", "flour"), 8.0, places=2)
        self.assertAlmostEqual(convert_to_grams(2.5, "tbsp", "wheat flour"), 20.0, places=2)
    
    def test_unknown_unit(self):
        with self.assertRaises(ValueError):
            convert_to_grams(1, "cup", "oil")

if __name__ == "__main__":
    unittest.main()
