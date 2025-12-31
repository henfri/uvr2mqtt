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


if __name__ == '__main__':
    unittest.main()
