import { test, expect } from '@playwright/test';

test('dashboard loads successfully', async ({ page }) => {
    await page.goto('/');

    // Check for the main heading or a specific element
    await expect(page).toHaveTitle(/Smart Stock Selector/i);

    // Check if the stock list is visible
    // await expect(page.locator('.stock-list-container')).toBeVisible();
});
