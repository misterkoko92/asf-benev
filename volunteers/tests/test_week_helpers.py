from datetime import date

from django.test import SimpleTestCase

from volunteers import views


class WeekHelpersTests(SimpleTestCase):
    def test_max_iso_week(self):
        self.assertEqual(views._max_iso_week(2015), 53)
        self.assertEqual(views._max_iso_week(2021), 52)

    def test_iter_week_ranges_length(self):
        weeks = list(views._iter_week_ranges(2021))
        self.assertEqual(len(weeks), 52)
        self.assertEqual(weeks[0][0], 1)
        self.assertEqual(weeks[0][1], date.fromisocalendar(2021, 1, 1))
        self.assertEqual(weeks[-1][0], 52)
        self.assertEqual(weeks[-1][2], date.fromisocalendar(2021, 52, 7))

    def test_iter_week_ranges_with_week_53(self):
        weeks = list(views._iter_week_ranges(2020))
        self.assertEqual(len(weeks), 53)
        self.assertEqual(weeks[-1][0], 53)
        self.assertEqual(weeks[-1][2], date.fromisocalendar(2020, 53, 7))

    def test_build_week_days(self):
        week_start = date(2026, 1, 5)
        days = views._build_week_days(week_start)
        self.assertEqual(len(days), 7)
        self.assertEqual(days[0]["date"], week_start)
        self.assertEqual(days[0]["label"], "Lundi 05/01/2026")
        self.assertEqual(days[-1]["label"], "Dimanche 11/01/2026")
