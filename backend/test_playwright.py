from playwright.sync_api import Page


def test_example_page(page: Page):

    page.goto("https://example.com")

    assert page.title() == "Example Domain"

    assert page.locator("h1").inner_text() == "Example Domain"