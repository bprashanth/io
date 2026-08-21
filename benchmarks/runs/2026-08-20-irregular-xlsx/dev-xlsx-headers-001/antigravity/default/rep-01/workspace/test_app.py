import unittest
import threading
import time
import requests
import json
from parser import parse_excel_workbook
import server

class TestSchoolAttendancePortal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start server in background thread for testing
        cls.httpd = server.socketserver.TCPServer(('127.0.0.1', 8080), server.AttendanceRequestHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_parser(self):
        data = parse_excel_workbook('/workspace/school_attendance_nested.xlsx')
        self.assertEqual(data['sheets'], ['Attendance Report', 'Read Me', 'Enrolment Raw'])
        
        # Primary attendance checks
        primary = data['primary_attendance']
        self.assertEqual(len(primary), 3)
        tekari = next(b for b in primary if b['block'] == 'Tekari')
        self.assertEqual(tekari['attendance']['2022']['boys'], 78)
        self.assertEqual(tekari['attendance']['2023']['boys'], 82)
        self.assertEqual(tekari['attendance']['2022']['girls'], 75)
        self.assertEqual(tekari['attendance']['2023']['girls'], 80)
        self.assertEqual(tekari['yoy']['boys'], 4)
        self.assertEqual(tekari['yoy']['girls'], 5)

        wazirganj = next(b for b in primary if b['block'] == 'Wazirganj')
        self.assertEqual(wazirganj['attendance']['2022']['boys'], 72)
        self.assertEqual(wazirganj['attendance']['2023']['boys'], 76)
        self.assertEqual(wazirganj['attendance']['2022']['girls'], 70)
        self.assertEqual(wazirganj['attendance']['2023']['girls'], 74)

        atri = next(b for b in primary if b['block'] == 'Atri')
        self.assertEqual(atri['attendance']['2022']['boys'], 68)
        self.assertEqual(atri['attendance']['2023']['boys'], 73)
        self.assertEqual(atri['attendance']['2022']['girls'], 66)
        self.assertEqual(atri['attendance']['2023']['girls'], 71)

        # Enrolment check
        self.assertEqual(len(data['enrolment_raw']), 30)
        self.assertIn('Tekari', data['enrolment_summary'])
        self.assertEqual(data['enrolment_summary']['Tekari']['school_count'], 10)
        self.assertEqual(data['enrolment_summary']['Tekari']['total_enrolled'], 1165)

    def test_api_health(self):
        res = requests.get('http://127.0.0.1:8080/api/health')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json().get('status'), 'ok')

    def test_api_data(self):
        res = requests.get('http://127.0.0.1:8080/api/data')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn('primary_attendance', data)
        self.assertIn('raw_sheets', data)
        self.assertEqual(len(data['primary_attendance']), 3)

    def test_api_sheet(self):
        res = requests.get('http://127.0.0.1:8080/api/sheet?name=Attendance+Report')
        self.assertEqual(res.status_code, 200)
        sheet = res.json()
        self.assertEqual(sheet['name'], 'Attendance Report')
        self.assertEqual(sheet['max_row'], 17)
        self.assertEqual(sheet['max_col'], 5)
        self.assertTrue(len(sheet['merged_cells']) > 0)

    def test_static_files(self):
        for path in ['/', '/index.html', '/style.css', '/app.js', '/data.js', '/attendance_data.json']:
            res = requests.get(f'http://127.0.0.1:8080{path}')
            self.assertEqual(res.status_code, 200, f"Failed on path {path}")

if __name__ == '__main__':
    unittest.main()
