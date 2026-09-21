"""
Generated Playwright Python automation.
"""

import os

import pytest
from playwright.sync_api import (
    Page,
    expect,
    Playwright,
    sync_playwright,
)


BASE_URL = os.getenv(
    'BASE_URL',
    'https://opensource-demo.orangehrmlive.com/web/index.php/auth/login',
)


def test_tc_exec_001_verify_login_with_credentials(page: Page):
    """
    Test case: TC-EXEC-001
    Verify login with credentials
    """

    page.goto(BASE_URL)

    # Step 1: username
    page.get_by_placeholder('Username').fill('Admin')

    # Step 2: password
    page.get_by_placeholder('Password').fill('Admin@123')

    # Business outcome assertions
    # Assertion: Password field is visible
    expect(page.get_by_placeholder('Password')).to_be_visible()
