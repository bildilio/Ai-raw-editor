import unittest
import numpy as np
from PIL import Image
from professional import correct

class TestProfessionalCorrection(unittest.TestCase):
    def setUp(self):
        a = np.zeros((48, 48, 3), dtype=np.uint8)
        a[:24] = [25, 30, 35]
        a[24:] = [235, 230, 225]
        self.image = Image.fromarray(a, 'RGB')

    def test_strength_zero_preserves_pixels(self):
        output, recipe = correct(self.image, strength=0)
        np.testing.assert_array_equal(np.asarray(output), np.asarray(self.image))

    def test_dimensions_and_type(self):
        output, recipe = correct(self.image, strength=.8)
        self.assertEqual(output.size, self.image.size)
        self.assertEqual(output.mode, 'RGB')
        self.assertIn('white_balance', recipe)

    def test_invalid_strength_is_clamped(self):
        output, recipe = correct(self.image, strength=10)
        self.assertEqual(recipe['strength'], 1.0)

if __name__ == '__main__':
    unittest.main()
