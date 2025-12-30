import unittest
from uvr import combine_html_xml, MyHTMLParser


class TestModusParsing(unittest.TestCase):
    def test_modus_with_br(self):
        # HTML with <br>
        html = "<div id=\"pos41\"><a>AUTO<br>  0,0 %</a></div>"
        beschreibung = ['Ausgang 15 (analog)  Modus (Hand/Auto)']
        id_conf = [41]
        xml_dict = {beschreibung[0]: 41}
        combined = combine_html_xml(MyHTMLParser, beschreibung, id_conf, xml_dict, html)
        key = list(xml_dict.keys())[0]
        self.assertIn(key + '_mode', combined)
        self.assertIn(key + '_percent', combined)
        self.assertEqual(combined[key + '_percent']['unit'], '%')

    def test_modus_single_line(self):
        html = "<div id=\"pos41\"><a>AUTO 0.0%</a></div>"
        beschreibung = ['Ausgang 15 (analog)  Modus (Hand/Auto)']
        id_conf = [41]
        xml_dict = {beschreibung[0]: 41}
        combined = combine_html_xml(MyHTMLParser, beschreibung, id_conf, xml_dict, html)
        key = list(xml_dict.keys())[0]
        self.assertIn(key + '_mode', combined)
        self.assertIn(key + '_percent', combined)


if __name__ == '__main__':
    unittest.main()
