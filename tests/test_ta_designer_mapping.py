import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from uvr_parse import read_xml, combine_html_xml, MyHTMLParser

NEU_XML_PATH = Path(__file__).resolve().parent.parent / "Neu.xml"
DEBUG_HTML_DIR = Path(__file__).resolve().parent.parent / "debug_html"


class TestTADesignerMapping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ET.parse(NEU_XML_PATH)
        cls.root = cls.tree.getroot()

    def test_seite2_mapping_and_deduplication(self):
        """Verify Seite 2 mappings: solar power is pos49, status is pos61, fkt32 is pos63."""
        beschr, id_conf, xml_dict = read_xml(self.root, 2)

        # Expected total HTML DIVs (74 objects - 3 Pic_Obj = 71)
        self.assertEqual(len(id_conf), 71)

        # WMZ SOLAR Momentanleistung must map to pos49 (first instance), not pos63!
        self.assertEqual(xml_dict.get('WMZ SOLAR Momentanleistung'), 49)

        # WMZ_WW 1 Status must map to pos61, not pos62!
        self.assertEqual(xml_dict.get('WMZ_WW        1 Status Wa > Wb + diff'), 61)

        # WMZ_WW Ergebnis must map to pos63 (Funktion 32), not pos64!
        self.assertEqual(xml_dict.get('WMZ_WW        Ergebnis'), 63)

        # WMZ_WW 1 Freigabe Vergleich must map to pos69, not pos70 (the link button)!
        self.assertEqual(xml_dict.get('WMZ_WW        1 Freigabe Vergleich'), 69)

        # UI elements (CMI_Obj "Text", CMILinkObj "C.M.I. 2") must NOT be in xml_dict
        self.assertNotIn('Text', xml_dict)
        self.assertNotIn('C.M.I. 2', xml_dict)

    def test_seite1_mapping_and_healing_shift(self):
        """Verify Seite 1: links at pos13/14 are deferred, fixing the +2 shift."""
        beschr, id_conf, xml_dict = read_xml(self.root, 1)

        # Expected total DIVs (51 objects - 3 Pic_Obj = 48)
        self.assertEqual(len(id_conf), 48)

        # FBHEIZ. 1 Externer Schalter must map to pos44, not pos46 (Link button)
        self.assertEqual(xml_dict.get('FBHEIZ. 1 Externer Schalter'), 44)

        # HZ_ANF. Status Anforderung must map to pos45, not pos47 (Link button)
        self.assertEqual(xml_dict.get('HZ_ANF. Status Anforderung'), 45)

        # Deduplication of identical digital inputs
        self.assertIn('NW-Eingang digital 4  Wert', xml_dict)
        self.assertEqual(xml_dict['NW-Eingang digital 4  Wert'], 32)
        self.assertNotIn('NW-Eingang digital 4  Wert_2', xml_dict)

    def test_seite0_mapping(self):
        """Verify Seite 0: link at 63 is deferred, pos65 has pump status."""
        beschr, id_conf, xml_dict = read_xml(self.root, 0)
        self.assertEqual(len(id_conf), 67)
        self.assertEqual(xml_dict.get('KUEHLFKT. 2 Status Pumpe'), 65)

    def test_invariant_violation_fail_safe(self):
        """If HTML div count does not match expected XML divs, combine_html_xml returns empty dict."""
        beschr, id_conf, xml_dict = read_xml(self.root, 2)
        # HTML with only 2 divs when 71 are expected
        corrupt_html = '<div id="pos0">10,0 °C</div><div id="pos1">20,0 °C</div>'
        res = combine_html_xml(MyHTMLParser, beschr, id_conf, xml_dict, corrupt_html)
        self.assertEqual(res, {})


if __name__ == '__main__':
    unittest.main()
