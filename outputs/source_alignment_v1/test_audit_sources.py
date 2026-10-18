import unittest
from decimal import Decimal
from lxml import html
from audit_sources import parse_p300,parse_p2x,agrees,aliases,normal_name


class SourceAlignmentTests(unittest.TestCase):
    def test_p300_columns_carry_forward_and_censoring(self):
        doc=html.fromstring('''<html><table><tr><td>P300 HAT SPA</td></tr></table><table>
          <tr><td>1</td><td>Isomer 1</td><td>4.99</td></tr>
          <tr><td></td><td>Isomer 2</td><td>0.130</td><td>0.004</td><td>0.107</td></tr>
          <tr><td>2</td><td>Isomer 1</td><td>&gt;5</td></tr></table></html>''')
        rows=parse_p300(doc)
        self.assertEqual((rows[1]['example'],rows[1]['isomer']),(1,'isomer 2'))
        r={'standard_units':'nM','standard_relation':'=','standard_value':'130.0'}
        self.assertTrue(agrees(r,rows[1]['HAT_IC50_uM'],1000))
        self.assertFalse(agrees(r,rows[1]['full_length_IC50_uM'],1000))
        bound={'standard_units':'nM','standard_relation':'>','standard_value':'5000.0'}
        self.assertTrue(agrees(bound,rows[2]['HAT_IC50_uM'],1000))
        bound['standard_relation']='='
        self.assertFalse(agrees(bound,rows[2]['HAT_IC50_uM'],1000))

    def test_p2x_source_layouts_keep_columns_distinct(self):
        for padding in ['', '<td></td>']:
            doc=html.fromstring('<html><table><tr><td>hP2X2/3</td></tr></table><table><tr>'+padding+
                '<td>1</td><td>4</td><td>76</td></tr></table></html>')
            row=parse_p2x(doc)[0]
            self.assertEqual(row['P2X2_3_IC50_nM'],'76')
            self.assertEqual(row['P2X3_IC50_nM'],'4')

    def test_duplicate_source_keys_fail_instead_of_silently_overwriting(self):
        doc=html.fromstring('<html><table><td>hP2X2/3</td></table><table>'+
            '<tr><td>1</td><td>4</td><td>76</td></tr>'*2+'</table></html>')
        with self.assertRaisesRegex(ValueError,'Duplicate P2X source key'):parse_p2x(doc)

    def test_aliases_preserve_patent_specific_example_numbers(self):
        result=aliases('US10174016, Example 193::US10202369, Example 194')
        self.assertEqual([(r['patent'],r['example']) for r in result],[('US10174016',193),('US10202369',194)])
        result=aliases('US11274090, Example 20 Isomer 2::US11274090, Example 20 Isomer 4')
        self.assertEqual([r['isomer'] for r in result],['isomer 2','isomer 4'])

    def test_name_normalization_does_not_erase_stereochemistry(self):
        self.assertEqual(normal_name('N- [(1R)- 1-x]'),normal_name('n-[(1R)-1-x]'))
        self.assertNotEqual(normal_name('(1R)-x'),normal_name('(1S)-x'))


if __name__=='__main__':unittest.main()
