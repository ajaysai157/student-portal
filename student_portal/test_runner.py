"""Test runner that keeps the test suite out of the real media folder.

Without this the tests that upload a student photo write the file into
``media/student_images/`` of the working copy, which slowly fills the folder
with duplicated test images.  The runner therefore points ``MEDIA_ROOT`` at a
temporary directory for the duration of the test run and removes it
afterwards.
"""

import shutil
import tempfile

from django.test.runner import DiscoverRunner
from django.test.utils import override_settings


class MediaSafeTestRunner(DiscoverRunner):
    """Run the tests with a throw away ``MEDIA_ROOT``."""

    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self._media_root = tempfile.mkdtemp(prefix="college-portal-test-media-")
        self._media_override = override_settings(MEDIA_ROOT=self._media_root)
        self._media_override.enable()

    def teardown_test_environment(self, **kwargs):
        self._media_override.disable()
        shutil.rmtree(self._media_root, ignore_errors=True)
        super().teardown_test_environment(**kwargs)
