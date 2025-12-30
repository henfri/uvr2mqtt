import unittest
from send_uvr_mqtt import sanitize_name


class TestSanitize(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(sanitize_name('Ausgang 15 (analog)  Modus (Hand/Auto)_mode'), 'ausgang_15_analog_modus_mode')

    def test_umlauts(self):
        self.assertEqual(sanitize_name('Küche Temperatur'), 'kueche_temperatur')

    def test_trim(self):
        self.assertEqual(sanitize_name('  Leading -- and trailing!! '), 'leading_and_trailing')


if __name__ == '__main__':
    unittest.main()
