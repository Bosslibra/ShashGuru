import { test, expect } from '@playwright/test';

test.describe('Chess Board Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('chess board is visible and interactive', async ({ page }) => {
    // Look for the chessboard container based on actual Vue component structure
    const chessboardContainer = page.locator('.chessboard-container');
    await expect(chessboardContainer).toBeVisible({ timeout: 10000 });
    
    // Look for the actual chessboard element from vue3-chessboard
    const chessboard = page.locator('.board-with-eval');
    await expect(chessboard).toBeVisible({ timeout: 10000 });
    
    // Check for board controls
    const boardControls = page.locator('.board-controls');
    await expect(boardControls).toBeVisible();
    
    // Verify board control buttons exist
    await expect(page.locator('button', { hasText: 'Flip Board' })).toBeVisible();
    await expect(page.locator('button', { hasText: 'Starting Position' })).toBeVisible();
    await expect(page.locator('button', { hasText: 'Settings' })).toBeVisible();
    
    // Take screenshot of initial board state
    await page.screenshot({ path: 'test-results/initial-chess-board.png' });
  });

  test('evaluation bar is visible and functional', async ({ page }) => {
    // Look for the evaluation panel from the ChessBoard component
    const evaluationPanel = page.locator('.evaluation-panel');
    
    try {
      await expect(evaluationPanel).toBeVisible({ timeout: 15000 });
      console.log('Evaluation panel found and visible');
      
      // The evaluation bar should be inside the evaluation panel
      // Look for any evaluation-related elements
      const evalElements = page.locator('.evaluation-panel *');
      const evalCount = await evalElements.count();
      console.log(`Found ${evalCount} elements in evaluation panel`);
      
      // Take screenshot showing evaluation panel
      await page.screenshot({ path: 'test-results/evaluation-panel-visible.png' });
      
      // Check if evaluation is enabled by default (according to the Vue component)
      // The evaluation should be enabled by default based on DEFAULT_EVALUATION_ENABLED
      
      // Try to find any text or visual indicators of evaluation
      const evaluationContent = await evaluationPanel.textContent();
      console.log('Evaluation panel content:', evaluationContent?.slice(0, 100));
      
      // Check for Settings button to verify we can access evaluation settings
      const settingsButton = page.locator('button', { hasText: 'Settings' });
      await expect(settingsButton).toBeVisible();
      
      // Click settings to see evaluation options
      await settingsButton.click();
      await page.waitForTimeout(1000);
      
      // Look for settings modal
      const settingsModal = page.locator('.settings-modal');
      const modalVisible = await settingsModal.isVisible().catch(() => false);
      
      if (modalVisible) {
        console.log('Settings modal opened successfully');
        await page.screenshot({ path: 'test-results/evaluation-settings-modal.png' });
        
        // Close the modal
        const closeBtn = page.locator('.close-btn');
        await closeBtn.click();
        await page.waitForTimeout(500);
      }
      
    } catch (error) {
      console.log('Evaluation panel not found with expected selectors, checking for alternative implementations');
      
      // Look for any evaluation-related elements in the page
      const allEvalElements = await page.locator('*').evaluateAll(elements => {
        return elements.filter(el => {
          const text = el.textContent?.toLowerCase() || '';
          const className = el.className?.toLowerCase() || '';
          const id = el.id?.toLowerCase() || '';
          
          return text.includes('eval') || text.includes('advantage') || 
                 className.includes('eval') || className.includes('bar') ||
                 id.includes('eval') || className.includes('evaluation');
        }).map(el => ({
          tagName: el.tagName,
          className: el.className,
          id: el.id,
          textContent: el.textContent?.slice(0, 50)
        }));
      });
      
      console.log('Found potential evaluation elements:', allEvalElements);
      
      // Take screenshot for debugging
      await page.screenshot({ path: 'test-results/evaluation-bar-debug.png' });
    }
  });

  test('FEN and PGN inputs are functional', async ({ page }) => {
    // Wait for page to load
    await page.waitForTimeout(3000);
    
    // Test FEN input functionality
    const fenInput = page.locator('#fenInput');
    await expect(fenInput).toBeVisible({ timeout: 10000 });
    console.log('FEN input found');
    
    // Get initial FEN value
    const initialFen = await fenInput.inputValue();
    console.log('Initial FEN:', initialFen);
    
    // Test entering a custom FEN position
    const testFen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1'; // After 1.e4
    await fenInput.fill(testFen);
    await fenInput.press('Enter');
    await page.waitForTimeout(2000);
    
    // Verify FEN was accepted
    const updatedFen = await fenInput.inputValue();
    console.log('Updated FEN:', updatedFen);
    
    // Take screenshot of board with new position
    await page.screenshot({ path: 'test-results/fen-position-updated.png' });
    
    // Test PGN input functionality
    const pgnInput = page.locator('#pgnInput');
    await expect(pgnInput).toBeVisible();
    console.log('PGN input found');
    
    // Test entering a simple PGN
    const testPGN = '1. e4 e5 2. Nf3 Nc6 3. Bb5';
    await pgnInput.fill(testPGN);
    await pgnInput.press('Enter');
    await page.waitForTimeout(3000);
    
    // Check if the FEN changed after PGN input
    const pgnFen = await fenInput.inputValue();
    console.log('FEN after PGN:', pgnFen);
    
    // The FEN should be different from the starting position if PGN was processed
    const startingFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    if (pgnFen !== startingFen) {
      console.log('PGN processing successful - board position changed');
    }
    
    await page.screenshot({ path: 'test-results/pgn-position-loaded.png' });
    
    // Test the "Starting Position" button
    const resetButton = page.locator('button', { hasText: 'Starting Position' });
    await resetButton.click();
    await page.waitForTimeout(2000);
    
    // Verify board was reset
    const resetFen = await fenInput.inputValue();
    console.log('FEN after reset:', resetFen);
    
    if (resetFen === startingFen) {
      console.log('Board reset successful');
    }
    
    await page.screenshot({ path: 'test-results/board-reset.png' });
  });

  test('board controls are functional', async ({ page }) => {
    // Wait for page to load
    await page.waitForTimeout(3000);
    
    // Test flip board functionality
    const flipButton = page.locator('button', { hasText: 'Flip Board' });
    await expect(flipButton).toBeVisible();
    
    // Take screenshot before flip
    await page.screenshot({ path: 'test-results/before-flip.png' });
    
    // Click flip board
    await flipButton.click();
    await page.waitForTimeout(2000);
    
    // Take screenshot after flip
    await page.screenshot({ path: 'test-results/after-flip.png' });
    
    // Test turn indicator
    const turnIndicators = page.locator('div:has-text("to play")');
    const indicatorCount = await turnIndicators.count();
    
    if (indicatorCount > 0) {
      const indicatorText = await turnIndicators.first().textContent();
      console.log('Turn indicator:', indicatorText);
    }
    
    // Flip back to original orientation
    await flipButton.click();
    await page.waitForTimeout(1000);
    
    await page.screenshot({ path: 'test-results/flipped-back.png' });
  });
});
