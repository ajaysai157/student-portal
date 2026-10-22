"""The shared student directory: search, filter, pagination and access."""

from django.test import TestCase
from django.urls import reverse

from .factories import (
    make_admin,
    make_department,
    make_faculty,
    make_student,
    make_student_user,
)


class DirectoryAccessTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.department = make_department()

    def test_admin_can_open_the_directory(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("student_directory"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "students/directory.html")

    def test_faculty_can_open_the_directory(self):
        self.client.force_login(make_faculty())
        response = self.client.get(reverse("student_directory"))
        self.assertEqual(response.status_code, 200)

    def test_a_student_cannot_open_the_directory(self):
        self.client.force_login(make_student_user()[1])
        response = self.client.get(reverse("student_directory"))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_visitors_are_sent_to_the_login_page(self):
        response = self.client.get(reverse("student_directory"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])


class DirectorySearchTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.aiml = make_department(code="AIML", name="Artificial Intelligence")
        self.cse = make_department(code="CSE", name="Computer Science")
        make_student(student_id="23A91A6001", name="Ravi Kumar", department=self.aiml, section=1)
        make_student(student_id="23A91A6002", name="Priya Sharma", department=self.aiml, section=2)
        make_student(student_id="23A91A6003", name="Anil Verma", department=self.cse, section=1)
        self.client.force_login(self.admin)

    def test_the_directory_lists_every_student(self):
        response = self.client.get(reverse("student_directory"))
        self.assertEqual(response.context["total_results"], 3)

    def test_search_by_name(self):
        response = self.client.get(reverse("student_directory"), {"q": "priya"})
        self.assertEqual(response.context["total_results"], 1)
        self.assertEqual(response.context["page_obj"].object_list[0].student_name, "Priya Sharma")

    def test_search_by_student_id(self):
        response = self.client.get(reverse("student_directory"), {"q": "23A91A6003"})
        self.assertEqual(response.context["total_results"], 1)
        self.assertEqual(response.context["page_obj"].object_list[0].student_name, "Anil Verma")

    def test_a_search_that_matches_nothing_returns_an_empty_list(self):
        response = self.client.get(reverse("student_directory"), {"q": "nobody"})
        self.assertEqual(response.context["total_results"], 0)
        self.assertEqual(len(response.context["page_obj"]), 0)

    def test_filter_by_department(self):
        response = self.client.get(
            reverse("student_directory"), {"department": self.cse.pk}
        )
        self.assertEqual(response.context["total_results"], 1)

    def test_filter_by_section(self):
        response = self.client.get(reverse("student_directory"), {"section": 2})
        self.assertEqual(response.context["total_results"], 1)

    def test_search_and_filter_can_be_combined(self):
        response = self.client.get(
            reverse("student_directory"),
            {"q": "a", "department": self.aiml.pk, "section": 1},
        )
        self.assertEqual(response.context["total_results"], 1)

    def test_an_unknown_department_filter_returns_nothing(self):
        response = self.client.get(reverse("student_directory"), {"department": "9999"})
        self.assertEqual(response.context["total_results"], 0)

    def test_a_non_numeric_department_filter_returns_nothing(self):
        response = self.client.get(reverse("student_directory"), {"department": "abc"})
        self.assertEqual(response.context["total_results"], 0)

    def test_the_current_filters_are_kept_in_the_context(self):
        response = self.client.get(
            reverse("student_directory"), {"q": "priya", "department": self.aiml.pk}
        )
        self.assertEqual(response.context["current_q"], "priya")
        self.assertEqual(response.context["current_department"], str(self.aiml.pk))


class DirectoryPaginationTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.department = make_department()
        for index in range(15):
            make_student(
                student_id=f"23A91A70{index:02d}",
                name=f"Student {index:02d}",
                department=self.department,
            )
        self.client.force_login(self.admin)

    def test_the_first_page_holds_twelve_students(self):
        response = self.client.get(reverse("student_directory"))
        self.assertEqual(len(response.context["page_obj"]), 12)
        self.assertEqual(response.context["total_results"], 15)
        self.assertTrue(response.context["page_obj"].has_next())

    def test_the_second_page_holds_the_rest(self):
        response = self.client.get(reverse("student_directory"), {"page": 2})
        self.assertEqual(len(response.context["page_obj"]), 3)
        self.assertTrue(response.context["page_obj"].has_previous())

    def test_an_out_of_range_page_falls_back_to_the_last_page(self):
        response = self.client.get(reverse("student_directory"), {"page": 99})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 3)

    def test_the_filters_survive_a_page_change(self):
        response = self.client.get(
            reverse("student_directory"), {"q": "Student", "page": 2}
        )
        self.assertIn("q=Student", response.context["filter_querystring"])
        self.assertNotIn("page=", response.context["filter_querystring"])

    def test_faculty_and_admin_get_the_same_results(self):
        faculty = make_faculty()
        admin_response = self.client.get(reverse("student_directory"), {"q": "Student 01"})
        self.client.force_login(faculty)
        faculty_response = self.client.get(reverse("student_directory"), {"q": "Student 01"})
        self.assertEqual(
            admin_response.context["total_results"],
            faculty_response.context["total_results"],
        )
