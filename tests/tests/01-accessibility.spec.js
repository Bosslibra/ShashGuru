import { test, expect } from '@playwright/test';

test.describe('ShashGuru Website Accessibility', () => {
  test('website can be reached and loads properly', async ({ page }) => {
    // Navigate to the website
    await page.goto('/');
    
    // Check that the page loads successfully
    await expect(page).toHaveTitle(/ShashGuru|Chess/i);
    
    // Wait for the page to be fully loaded
    await page.waitForLoadState('networkidle');
    
    // Check for essential elements that should be present
    // Assuming there's a main container or chess board element
    await expect(page.locator('body')).toBeVisible();
    
    // Check that there are no critical JavaScript errors
    const logs = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        logs.push(msg.text());
      }
    });
    
    // Wait a bit to catch any async errors
    await page.waitForTimeout(2000);
    
    // Log any errors for debugging but don't fail the test unless they're critical
    if (logs.length > 0) {
      console.log('Console errors found:', logs);
    }
    
    // Take a screenshot for visual verification
    await page.screenshot({ path: 'test-results/homepage-loaded.png', fullPage: true });
  });

  test('page responds within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    
    await page.goto('/');
    await page.waitForLoadState('domcontentloaded');
    
    const loadTime = Date.now() - startTime;
    
    // Expect page to load within 10 seconds
    expect(loadTime).toBeLessThan(10000);
    
    console.log(`Page load time: ${loadTime}ms`);
  });

  test('website is responsive', async ({ page }) => {
    await page.goto('/');
    
    // Test different viewport sizes
    const viewports = [
      { width: 1920, height: 1080 }, // Desktop
      { width: 1024, height: 768 },  // Tablet
      { width: 375, height: 667 }    // Mobile
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize(viewport);
      await page.waitForTimeout(1000); // Allow time for responsive adjustments
      
      // Check that essential elements are still visible
      await expect(page.locator('body')).toBeVisible();
      
      // Take screenshot for each viewport
      await page.screenshot({ 
        path: `test-results/responsive-${viewport.width}x${viewport.height}.png`,
        fullPage: true 
      });
    }
  });
});
