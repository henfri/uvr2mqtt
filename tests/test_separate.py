import unittest
from uvr import separate


class TestSeparate(unittest.TestCase):
    def test_temperature(self):
        v, u = separate('61,9 °C')
        self.assertAlmostEqual(v, 61.9)
        self.assertEqual(u, '°C')

    def test_percent(self):
        v, u = separate('0,0 %')
        self.assertAlmostEqual(v, 0.0)
        self.assertEqual(u, '%')

    def test_on_off(self):
        v, u = separate('EIN')
        self.assertEqual(v, 1.0)
        self.assertEqual(u, 'switch')

    def test_auto_hand(self):
        v, u = separate('AUTO')
        self.assertIsNone(v)
        self.assertEqual(u, 'OutputMode')

    def test_negative_value(self):
        v, u = separate('-59,4 kWh')
        self.assertAlmostEqual(v, -59.4)
        self.assertEqual(u, 'kWh')

    def test_unicode_minus_and_space(self):
        v, u = separate('\u2212 5,0 °C')
        self.assertAlmostEqual(v, -5.0)
        self.assertEqual(u, '°C')


if __name__ == '__main__':
    unittest.main()
