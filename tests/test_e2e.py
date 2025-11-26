import uuid
import pytest
from playwright.sync_api import Page, expect

def test_add_and_borrow_book(page: Page):
    # Add a unique book
    page.goto("http://localhost:5000/add_book")

    unique_title = f"Test_Book_{uuid.uuid4().hex[:6]}"
    unique_isbn = str(uuid.uuid4().int)[:13]

    page.fill("#title", unique_title)
    page.fill("#author", "Test Author")
    page.fill("#isbn", unique_isbn)
    page.fill("#total_copies", "3")
    page.click("text=Add Book to Catalog")

    # Check
    expect(page.locator("body")).to_contain_text("successfully added")

    page.goto("http://localhost:5000/catalog")

    # Find the row
    row = page.locator(f"table tr:has-text('{unique_title}')")

    # Borrow
    patron_input = row.locator("input[name='patron_id']")
    expect(patron_input).to_be_visible()
    patron_input.fill("123456")  # You can parameterize this if needed

    borrow_button = row.locator("button:has-text('Borrow')")
    expect(borrow_button).to_be_enabled()
    borrow_button.click()

