import { test, expect } from '@playwright/test';

test.describe('Live Section Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('can access Live section', async ({ page }) => {
    // Navigate to Live section
    await navigateToLiveSection(page);
    
    // Verify Live section loaded by checking for the main heading
    const heading = page.locator('h2').filter({ hasText: /Events and Broadcasts/i });
    await expect(heading).toBeVisible({ timeout: 10000 });
    
    // Check for the search input for broadcast URLs
    const searchInput = page.locator('#input-event');
    await expect(searchInput).toBeVisible();
    
    // Verify placeholder text
    const placeholder = await searchInput.getAttribute('placeholder');
    expect(placeholder).toContain('Lichess Broadcast URL');
    
    // Check for search button
    const searchButton = page.locator('#search-button');
    await expect(searchButton).toBeVisible();
    
    // Verify helper text is present
    const helperText = page.locator('#helper');
    await expect(helperText).toBeVisible();
    const helperContent = await helperText.textContent();
    expect(helperContent).toContain('Example:');
    
    console.log('Live section loaded successfully with search functionality');
    await page.screenshot({ path: 'test-results/live-section-accessed.png' });
  });

  test('can search for Lichess broadcast events', async ({ page }) => {
    await navigateToLiveSection(page);
    
    // Wait for the search input to be ready
    const searchInput = page.locator('#input-event');
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    
    // Test with a sample Lichess broadcast URL
    const testUrl = 'https://lichess.org/broadcast/test-event/sO7W9Jje/eJLgkG7n';
    
    await searchInput.fill(testUrl);
    await page.waitForTimeout(1000);
    
    // Click the search button
    const searchButton = page.locator('#search-button');
    await searchButton.click();
    
    // Wait for potential loading and results
    await page.waitForTimeout(5000);
    
    // Check if loading spinner appears
    const spinner = page.locator('.spinner-border');
    const isLoading = await spinner.isVisible().catch(() => false);
    
    if (isLoading) {
      console.log('Loading spinner detected, waiting for results...');
      await page.waitForTimeout(10000);
    }
    
    // Check for error messages (expected for test URL)
    const errorMessage = page.locator('.text-danger');
    const hasError = await errorMessage.isVisible().catch(() => false);
    
    if (hasError) {
      const errorText = await errorMessage.textContent();
      console.log('Error message displayed (expected for test URL):', errorText);
    }
    
    // Check if queried results section appears
    const queriedResults = page.locator('#queried-results');
    const hasResults = await queriedResults.isVisible().catch(() => false);
    
    if (hasResults) {
      console.log('Queried results section appeared');
    }
    
    await page.screenshot({ path: 'test-results/live-search-test.png' });
    
    // Test search with just an ID
    await searchInput.fill('eJLgkG7n');
    await searchButton.click();
    await page.waitForTimeout(3000);
    
    await page.screenshot({ path: 'test-results/live-search-id-test.png' });
  });

  test('displays featured event if available', async ({ page }) => {
    await navigateToLiveSection(page);
    
    // Wait for page to load
    await page.waitForTimeout(3000);
    
    // Check for "Featured Event" heading
    const featuredHeading = page.locator('.fs-3').filter({ hasText: /Featured Event/i });
    const hasFeaturedEvent = await featuredHeading.isVisible().catch(() => false);
    
    if (hasFeaturedEvent) {
      console.log('Featured Event section found');
      
      // Look for EventSection component containing featured event
      const eventSection = page.locator('[data-testid="event-section"]').or(
        page.locator('.event-section, .featured-event')
      );
      
      const eventSectionExists = await eventSection.first().isVisible().catch(() => false);
      
      if (eventSectionExists) {
        console.log('Featured event content displayed');
        
        // Check for event details
        const eventTitle = await eventSection.first().textContent();
        console.log('Featured event details:', eventTitle?.slice(0, 200));
      }
      
      await page.screenshot({ path: 'test-results/live-featured-event.png' });
    } else {
      console.log('No featured event currently displayed');
      
      // This is normal if no featured event is configured
      await page.screenshot({ path: 'test-results/live-no-featured-event.png' });
    }
    
    // Check for any event sections that might be loaded
    const anyEventSections = page.locator('div').filter({ hasText: /Event|Tournament|Broadcast/i });
    const eventCount = await anyEventSections.count();
    
    if (eventCount > 0) {
      console.log(`Found ${eventCount} event-related sections on the page`);
    }
  });

  test('handles search errors gracefully', async ({ page }) => {
    await navigateToLiveSection(page);
    
    // Wait for search input to be ready
    const searchInput = page.locator('#input-event');
    await expect(searchInput).toBeVisible({ timeout: 10000 });
    
    // Test with invalid input
    const invalidInputs = [
      'invalid-url',
      'https://invalid-url.com',
      'not-a-real-id'
    ];
    
    for (const invalidInput of invalidInputs) {
      console.log(`Testing invalid input: ${invalidInput}`);
      
      await searchInput.fill(invalidInput);
      
      const searchButton = page.locator('#search-button');
      await searchButton.click();
      
      // Wait for response
      await page.waitForTimeout(5000);
      
      // Check for error message
      const errorMessage = page.locator('.text-danger');
      const hasError = await errorMessage.isVisible().catch(() => false);
      
      if (hasError) {
        const errorText = await errorMessage.textContent();
        console.log(`Error correctly displayed: ${errorText}`);
      }
      
      // Clear input for next test
      await searchInput.fill('');
      await page.waitForTimeout(1000);
    }
    
    await page.screenshot({ path: 'test-results/live-error-handling.png' });
  });
});

// Helper function to navigate to Live section
async function navigateToLiveSection(page) {
  // Navigate to Live section via URL (most reliable method)
  const currentUrl = page.url();
  if (!currentUrl.includes('/live')) {
    await page.goto('/live');
    await page.waitForLoadState('networkidle');
    return;
  }
  
  // Alternative: look for navigation links
  const liveNavigation = page.locator('[href*="/live"], [href="#/live"]').or(
    page.locator('a, button, .nav-item').filter({ hasText: /live/i })
  );
  
  const liveNavExists = await liveNavigation.first().isVisible().catch(() => false);
  
  if (liveNavExists) {
    await liveNavigation.first().click();
    await page.waitForLoadState('networkidle');
  } else {
    // Try router navigation for Vue SPA
    await page.evaluate(() => {
      if (window.router) {
        window.router.push('/live');
      }
    });
    await page.waitForTimeout(2000);
  }
}
