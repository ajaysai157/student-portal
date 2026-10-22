"""Authentication and session tests."""

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from app1.permissions import role_of

from .factories import make_admin, make_student_user


class LandingPageTests(TestCase):
    def test_landing_page_is_public(self):
        response = self.client.get(reverse("landing"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "landing.html")

    def test_signed_in_user_is_sent_to_the_dashboard(self):
        admin = make_admin()
        self.client.force_login(admin)
        response = self.client.get(reverse("landing"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("dashboard"))


class DashboardRoutingTests(TestCase):
    def test_admin_is_sent_to_the_admin_dashboard(self):
        self.client.force_login(make_admin())
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("admin_dashboard"))
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 200)

    def test_faculty_is_sent_to_the_faculty_dashboard(self):
        from .factories import make_faculty

        self.client.force_login(make_faculty())
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response["Location"], reverse("faculty_dashboard"))
        self.assertEqual(self.client.get(reverse("faculty_dashboard")).status_code, 200)

    def test_student_is_sent_to_the_student_dashboard(self):
        from .factories import make_student_user

        self.client.force_login(make_student_user()[1])
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response["Location"], reverse("student_dashboard"))
        self.assertEqual(self.client.get(reverse("student_dashboard")).status_code, 200)

    def test_user_without_a_role_sees_the_account_overview(self):
        from django.contrib.auth.models import User

        user = User.objects.create_user(username="plain", password="x")
        self.client.force_login(user)
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response["Location"], reverse("account_overview"))

    def test_a_student_cannot_open_the_admin_dashboard(self):
        from .factories import make_student_user

        self.client.force_login(make_student_user()[1])
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 403)

    def test_a_faculty_member_cannot_open_the_admin_dashboard(self):
        from .factories import make_faculty

        self.client.force_login(make_faculty())
        self.assertEqual(self.client.get(reverse("admin_dashboard")).status_code, 403)

    def test_an_admin_cannot_open_the_student_dashboard(self):
        self.client.force_login(make_admin())
        self.assertEqual(self.client.get(reverse("student_dashboard")).status_code, 403)


class LoginTests(TestCase):
    def test_valid_credentials_log_the_user_in(self):
        make_admin()
        response = self.client.post(
            reverse("login"),
            {"username": "admin_user", "password": "Admin-pass-123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("dashboard"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_wrong_password_is_rejected(self):
        make_admin()
        response = self.client.post(
            reverse("login"),
            {"username": "admin_user", "password": "wrong-password"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "Please enter a correct username")

    def test_unknown_user_is_rejected(self):
        response = self.client.post(
            reverse("login"),
            {"username": "nobody", "password": "Admin-pass-123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_inactive_account_cannot_sign_in(self):
        admin = make_admin()
        admin.is_active = False
        admin.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("login"),
            {"username": "admin_user", "password": "Admin-pass-123"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_keeps_the_next_parameter(self):
        make_admin()
        target = reverse("student_directory")
        response = self.client.post(
            f"{reverse('login')}?next={target}",
            {"username": "admin_user", "password": "Admin-pass-123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], target)

    def test_login_ignores_an_external_next_url(self):
        make_admin()
        response = self.client.post(
            f"{reverse('login')}?next=https://evil.example.com/",
            {"username": "admin_user", "password": "Admin-pass-123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("dashboard"))


class LogoutTests(TestCase):
    def test_logout_clears_the_session(self):
        admin = make_admin()
        self.client.force_login(admin)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("landing"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post(self):
        admin = make_admin()
        self.client.force_login(admin)
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 405)
        self.assertIn("_auth_user_id", self.client.session)


class ProtectedPageTests(TestCase):
    def test_anonymous_visitor_is_redirected_to_the_login_page(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])
        self.assertIn("next=", response["Location"])

    def test_inactive_session_is_dropped_and_the_user_is_sent_to_login(self):
        admin = make_admin()
        self.client.force_login(admin)
        admin.is_active = False
        admin.save(update_fields=["is_active"])

        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])
        self.assertNotIn("_auth_user_id", self.client.session)


class PasswordChangeTests(TestCase):
    def test_a_user_can_change_their_own_password(self):
        admin = make_admin()
        self.client.force_login(admin)

        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": "Admin-pass-123",
                "new_password1": "Brand-new-pass-456",
                "new_password2": "Brand-new-pass-456",
            },
        )
        self.assertRedirects(response, reverse("password_change_done"))

        admin.refresh_from_db()
        self.assertTrue(admin.check_password("Brand-new-pass-456"))

    def test_the_old_password_must_be_correct(self):
        admin = make_admin()
        self.client.force_login(admin)

        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": "not-the-password",
                "new_password1": "Brand-new-pass-456",
                "new_password2": "Brand-new-pass-456",
            },
        )
        self.assertEqual(response.status_code, 200)
        admin.refresh_from_db()
        self.assertTrue(admin.check_password("Admin-pass-123"))


class RoleDetectionTests(TestCase):
    def test_superuser_is_an_admin(self):
        from .factories import make_superuser

        self.assertEqual(role_of(make_superuser()), "admin")

    def test_group_members_get_their_role(self):
        self.assertEqual(role_of(make_admin()), "admin")
        self.assertEqual(role_of(make_student_user()[1]), "student")

    def test_a_user_without_a_group_has_no_role(self):
        user = User.objects.create_user(username="plain", password="x")
        self.assertIsNone(role_of(user))
