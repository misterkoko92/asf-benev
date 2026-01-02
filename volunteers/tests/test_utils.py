from django.test import SimpleTestCase

from volunteers.utils import format_phone, generate_short_name, normalize_phone_number, split_phone


class ShortNameTests(SimpleTestCase):
    def test_generate_short_name_simple(self):
        self.assertEqual(generate_short_name("Pierre"), "P.")

    def test_generate_short_name_hyphen(self):
        self.assertEqual(generate_short_name("Jean-Pierre"), "J-P.")

    def test_generate_short_name_space(self):
        self.assertEqual(generate_short_name("Jean Pierre"), "J-P.")

    def test_generate_short_name_apostrophe(self):
        self.assertEqual(generate_short_name("El'Pierre"), "E-P.")

    def test_generate_short_name_empty(self):
        self.assertEqual(generate_short_name(""), "")


class PhoneUtilsTests(SimpleTestCase):
    def test_normalize_phone_number(self):
        self.assertEqual(normalize_phone_number("06 01 02 03"), "06010203")

    def test_split_phone_with_country(self):
        self.assertEqual(split_phone("+33 6 01 02"), ("+33", "60102"))

    def test_split_phone_without_country(self):
        self.assertEqual(split_phone("06010203"), ("+33", "06010203"))

    def test_format_phone(self):
        self.assertEqual(format_phone("+33", "6 01 02"), "+33 60102")

    def test_format_phone_default_country(self):
        self.assertEqual(format_phone("", "60102"), "+33 60102")
