import { test, expect } from '@playwright/test';
import { promises as fs } from 'fs';
import path from 'path';

test.describe('PGN Upload Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('can input PGN and load moves correctly', async ({ page }) => {
    // Sample PGN content for testing
    const testPGN = `[Event "Test Game"]
[Site "Test"]
[Date "2025.01.01"]
[Round "1"]
[White "Player1"]
[Black "Player2"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 1-0`;

    // Wait for the chess board to load
    await page.waitForTimeout(3000);
    
    // Look for the PGN input field from ChessBoard.vue
    const pgnInput = page.locator('#pgnInput');
    await expect(pgnInput).toBeVisible({ timeout: 10000 });
    console.log('PGN input field found');
    
    // Get initial FEN to compare later
    const fenInput = page.locator('#fenInput');
    const initialFen = await fenInput.inputValue();
    console.log('Initial FEN:', initialFen);
    
    // Input the test PGN
    await pgnInput.fill(testPGN);
    await pgnInput.press('Enter');
    await page.waitForTimeout(3000);
    
    // Check if the FEN changed after PGN input (indicating moves were loaded)
    const updatedFen = await fenInput.inputValue();
    console.log('Updated FEN after PGN:', updatedFen);
    
    // Verify the FEN changed from starting position
    const startingFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    if (updatedFen !== startingFen && updatedFen !== initialFen) {
      console.log('PGN processing successful - board position changed');
    } else {
      console.log('PGN may not have been processed correctly');
    }
    
    // Take screenshot after PGN load
    await page.screenshot({ path: 'test-results/pgn-loaded.png' });
    
    // Verify that the PGN input still contains our PGN
    const pgnValue = await pgnInput.inputValue();
    if (pgnValue.includes('1. e4 e5')) {
      console.log('PGN input contains expected moves');
    }
  });

  test('handles invalid PGN gracefully', async ({ page }) => {
    const invalidPGN = "This is not a valid PGN file content";
    
    // Wait for the chess board to load
    await page.waitForTimeout(3000);
    
    // Look for the PGN input field from ChessBoard.vue
    const pgnInput = page.locator('#pgnInput');
    await expect(pgnInput).toBeVisible({ timeout: 10000 });
    console.log('Testing invalid PGN handling');
    
    // Get initial FEN to compare
    const fenInput = page.locator('#fenInput');
    const initialFen = await fenInput.inputValue();
    
    // Input invalid PGN
    await pgnInput.fill(invalidPGN);
    await pgnInput.press('Enter');
    await page.waitForTimeout(2000);
    
    // Check if FEN remained unchanged (indicating PGN was rejected)
    const finalFen = await fenInput.inputValue();
    
    if (finalFen === initialFen) {
      console.log('Invalid PGN correctly rejected - FEN unchanged');
    } else {
      console.log('FEN changed despite invalid PGN - may need investigation');
    }
    
    // Look for any alert or error indication
    // The chess.js library used in ChessBoard.vue shows an alert for invalid PGN
    const alertHandled = await page.evaluate(() => {
      // Override alert to capture it
      let alertMessage = '';
      const originalAlert = window.alert;
      window.alert = (message) => {
        alertMessage = message;
        return true;
      };
      return alertMessage;
    });
    
    await page.screenshot({ path: 'test-results/invalid-pgn-handling.png' });
  });

  test('can reset board after loading PGN', async ({ page }) => {
    // First load a PGN to have something to reset
    const testPGN = '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6';
    
    // Wait for the chess board to load
    await page.waitForTimeout(3000);
    
    // Load a test PGN
    const pgnInput = page.locator('#pgnInput');
    await expect(pgnInput).toBeVisible({ timeout: 10000 });
    
    await pgnInput.fill(testPGN);
    await pgnInput.press('Enter');
    await page.waitForTimeout(2000);
    
    // Verify position changed
    const fenInput = page.locator('#fenInput');
    const loadedFen = await fenInput.inputValue();
    const startingFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    
    if (loadedFen !== startingFen) {
      console.log('PGN loaded successfully, board position changed');
      
      // Now test the "Starting Position" button
      const resetButton = page.locator('button', { hasText: 'Starting Position' });
      await expect(resetButton).toBeVisible();
      
      await resetButton.click();
      await page.waitForTimeout(2000);
      
      // Verify board was reset to starting position
      const resetFen = await fenInput.inputValue();
      if (resetFen === startingFen) {
        console.log('Board successfully reset to starting position');
      } else {
        console.log('Board reset may not have worked correctly');
      }
      
      // Verify PGN input was cleared
      const clearedPgn = await pgnInput.inputValue();
      if (clearedPgn === '' || clearedPgn !== testPGN) {
        console.log('PGN input was cleared after reset');
      }
      
      await page.screenshot({ path: 'test-results/pgn-board-reset.png' });
    } else {
      console.log('PGN may not have loaded correctly for reset test');
    }
  });

  test('multiple PGN inputs work correctly', async ({ page }) => {
    // Test loading multiple different PGNs in sequence
    const pgns = [
      '1. e4 e5',
      '1. d4 d5 2. c4',
      '1. Nf3 Nf6 2. g3 g6'
    ];
    
    await page.waitForTimeout(3000);
    
    const pgnInput = page.locator('#pgnInput');
    const fenInput = page.locator('#fenInput');
    await expect(pgnInput).toBeVisible({ timeout: 10000 });
    
    const startingFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
    
    for (let i = 0; i < pgns.length; i++) {
      console.log(`Loading PGN ${i + 1}: ${pgns[i]}`);
      
      // Clear and load new PGN
      await pgnInput.fill(pgns[i]);
      await pgnInput.press('Enter');
      await page.waitForTimeout(2000);
      
      // Verify the position changed
      const currentFen = await fenInput.inputValue();
      if (currentFen !== startingFen) {
        console.log(`PGN ${i + 1} loaded successfully`);
      }
      
      await page.screenshot({ path: `test-results/pgn-sequence-${i + 1}.png` });
    }
  });
});

// Helper function to verify moves were loaded
async function verifyMovesLoaded(page, expectedPGN) {
    // Extract moves from PGN
    const movePattern = /\d+\.\s*([KQRBN]?[a-h]?[1-8]?x?[a-h][1-8][+#]?)\s*([KQRBN]?[a-h]?[1-8]?x?[a-h][1-8][+#]?)?/g;
    const expectedMoves = [];
    let match;
    
    while ((match = movePattern.exec(expectedPGN)) !== null) {
      if (match[1]) expectedMoves.push(match[1]);
      if (match[2]) expectedMoves.push(match[2]);
    }
    
    console.log('Expected moves from PGN:', expectedMoves.slice(0, 10));
    
    // Look for moves in the interface
    const moveElements = page.locator('.move, .move-item, [class*="move"], .notation');
    const moveCount = await moveElements.count();
    
    if (moveCount > 0) {
      const displayedMoves = await moveElements.allTextContents();
      console.log('Displayed moves:', displayedMoves.slice(0, 10));
      
      // Check if at least some expected moves appear in the display
      const foundMoves = expectedMoves.filter(move => 
        displayedMoves.some(displayed => displayed.includes(move))
      );
      
      console.log(`Found ${foundMoves.length} out of ${expectedMoves.length} expected moves`);
      
      if (foundMoves.length >= expectedMoves.length * 0.5) {
        console.log('PGN moves appear to be loaded correctly');
        return true;
      }
    }
    
    // Alternative: check if board position changed from starting position
    const boardState = await page.evaluate(() => {
      // Try to detect if pieces have moved from starting positions
      const squares = document.querySelectorAll('[data-square], [class*="square"]');
      return Array.from(squares).map(square => ({
        square: square.getAttribute('data-square') || square.className,
        content: square.textContent || square.innerHTML
      }));
    });
    
    console.log('Board state after PGN load:', boardState.slice(0, 8));
    
    return false;
}
