import unittest
from app import app, create_database, get_db_connection


class AdminModuleTests(unittest.TestCase):
    def setUp(self):
        create_database()
        self.client = app.test_client()

    def _login_as_admin(self):
        with self.client.session_transaction() as session:
            session['admin_id'] = 1
            session['admin_name'] = 'EduInfo Admin'

    def test_homepage_nav_links_point_to_real_pages(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('href="/student/login"', html)
        self.assertIn('href="/teacher/login"', html)
        self.assertIn('href="/admin/login"', html)
        self.assertNotIn('href="#"', html)

    def test_admin_routes_render_successfully(self):
        self._login_as_admin()

        for route in ['/admin/dashboard', '/admin/students', '/admin/teachers', '/admin/attendance', '/admin/marks']:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f'{route} should load successfully')

    def test_admin_can_manage_students_and_teachers(self):
        self._login_as_admin()

        connection = get_db_connection()
        connection.execute(
            "INSERT INTO students (name, email, course, password) VALUES (?, ?, ?, ?)",
            ('Test Student', 'student@test.com', 'Computer Science', 'pw123')
        )
        student_id = connection.execute('SELECT last_insert_rowid()').fetchone()[0]
        connection.commit()
        connection.close()

        student_response = self.client.get('/admin/students?q=Test')
        self.assertEqual(student_response.status_code, 200)
        self.assertIn('Test Student', student_response.get_data(as_text=True))

        delete_student_response = self.client.post(f'/admin/delete-student/{student_id}', follow_redirects=True)
        self.assertEqual(delete_student_response.status_code, 200)
        self.assertIn('Student deleted successfully.', delete_student_response.get_data(as_text=True))

        add_teacher_response = self.client.post('/admin/teachers', data={
            'name': 'Test Teacher',
            'email': 'teacher2@test.com',
            'password': 'teacher123'
        }, follow_redirects=True)
        self.assertEqual(add_teacher_response.status_code, 200)
        self.assertIn('Teacher added successfully.', add_teacher_response.get_data(as_text=True))

        connection = get_db_connection()
        teacher = connection.execute('SELECT id FROM teachers WHERE email = ?', ('teacher2@test.com',)).fetchone()
        connection.close()
        self.assertIsNotNone(teacher)

        delete_teacher_response = self.client.post(f'/admin/delete-teacher/{teacher[0]}', follow_redirects=True)
        self.assertEqual(delete_teacher_response.status_code, 200)
        self.assertIn('Teacher deleted successfully.', delete_teacher_response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
