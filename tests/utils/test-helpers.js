// Utility functions for Playwright tests

/**
 * Wait for an element to be visible with multiple selector strategies
 * @param {Page} page - Playwright page object
 * @param {string[]} selectors - Array of selectors to try
 * @param {number} timeout - Timeout in milliseconds
 * @returns {Locator|null} - Found locator or null
 */
export async function waitForAnySelector(page, selectors, timeout = 10000) {
  for (const selector of selectors) {
    try {
      const element = page.locator(selector);
      await element.first().waitFor({ state: 'visible', timeout: timeout / selectors.length });
      return element;
    } catch (error) {
      // Continue to next selector
    }
  }
  return null;
}

/**
 * Take a screenshot with timestamp and description
 * @param {Page} page - Playwright page object
 * @param {string} description - Description for the screenshot
 * @param {string} testName - Name of the test
 */
export async function takeScreenshot(page, description, testName) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filename = `test-results/${testName}-${description}-${timestamp}.png`;
  await page.screenshot({ path: filename, fullPage: true });
  console.log(`Screenshot saved: ${filename}`);
}

/**
 * Log page errors and warnings
 * @param {Page} page - Playwright page object
 * @returns {string[]} - Array of error messages
 */
export function setupErrorLogging(page) {
  const errors = [];
  const warnings = [];
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    } else if (msg.type() === 'warning') {
      warnings.push(msg.text());
    }
  });
  
  page.on('pageerror', error => {
    errors.push(`Page error: ${error.message}`);
  });
  
  return { errors, warnings };
}

/**
 * Wait for network requests to settle
 * @param {Page} page - Playwright page object
 * @param {number} timeout - Timeout in milliseconds
 */
export async function waitForNetworkIdle(page, timeout = 5000) {
  try {
    await page.waitForLoadState('networkidle', { timeout });
  } catch (error) {
    console.log('Network idle timeout reached, continuing...');
  }
}

/**
 * Check if chess moves are valid notation
 * @param {string} moveText - Text to check for chess notation
 * @returns {boolean} - True if contains valid chess notation
 */
export function isValidChessNotation(moveText) {
  // Basic chess notation patterns
  const patterns = [
    /\b[1-9]\d*\.\s*[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8][+#]?\b/, // Standard notation
    /\b[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8][+#]?\b/, // Move without number
    /\bO-O(-O)?\b/, // Castling
    /\b[a-h][1-8]=[QRBN]\b/ // Promotion
  ];
  
  return patterns.some(pattern => pattern.test(moveText));
}

/**
 * Extract chess moves from PGN text
 * @param {string} pgnText - PGN content
 * @returns {string[]} - Array of moves
 */
export function extractMovesFromPGN(pgnText) {
  const moves = [];
  const movePattern = /\d+\.\s*([KQRBN]?[a-h]?[1-8]?x?[a-h][1-8][+#]?)\s*([KQRBN]?[a-h]?[1-8]?x?[a-h][1-8][+#]?)?/g;
  
  let match;
  while ((match = movePattern.exec(pgnText)) !== null) {
    if (match[1]) moves.push(match[1]);
    if (match[2]) moves.push(match[2]);
  }
  
  return moves;
}

/**
 * Generate test PGN content
 * @param {string} gameType - Type of game (e.g., 'opening', 'endgame', 'tactics')
 * @returns {string} - PGN content
 */
export function generateTestPGN(gameType = 'opening') {
  const baseHeaders = `[Event "Test Game"]
[Site "Test"]
[Date "2025.01.01"]
[Round "1"]
[White "TestPlayer1"]
[Black "TestPlayer2"]
[Result "1-0"]

`;

  const games = {
    opening: '1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 1-0',
    endgame: '1. e4 c5 2. Nf3 d6 3. d4 cxd4 4. Nxd4 Nf6 5. Nc3 a6 6. Be3 e6 7. f3 Be7 8. Qd2 Qc7 9. O-O-O Nbd7 10. g4 b5 1-0',
    tactics: '1. e4 e5 2. f4 exf4 3. Nf3 g5 4. h4 g4 5. Ne5 Nf6 6. Bc4 d5 7. exd5 Bg7 8. d4 Nh5 9. Bb5+ c6 10. dxc6 bxc6 1-0'
  };

  return baseHeaders + (games[gameType] || games.opening);
}

/**
 * Wait for AI response with multiple indicators
 * @param {Page} page - Playwright page object
 * @param {number} timeout - Timeout in milliseconds
 * @returns {string|null} - AI response text or null
 */
export async function waitForAIResponse(page, timeout = 30000) {
  const responseSelectors = [
    '[data-testid="ai-response"]',
    '.ai-response',
    '.ai-message',
    '.chat-message',
    '.analysis-result',
    '.ai-output'
  ];
  
  const startTime = Date.now();
  
  while (Date.now() - startTime < timeout) {
    for (const selector of responseSelectors) {
      try {
        const element = page.locator(selector);
        const isVisible = await element.first().isVisible();
        
        if (isVisible) {
          const text = await element.first().textContent();
          if (text && text.trim().length > 10 && !isLoadingMessage(text)) {
            return text;
          }
        }
      } catch (error) {
        // Continue checking
      }
    }
    
    await page.waitForTimeout(1000);
  }
  
  return null;
}

/**
 * Check if text appears to be a loading message
 * @param {string} text - Text to check
 * @returns {boolean} - True if appears to be loading message
 */
export function isLoadingMessage(text) {
  const loadingPatterns = [
    /loading/i,
    /processing/i,
    /thinking/i,
    /analyzing/i,
    /please wait/i,
    /generating/i,
    /\.\.\./,
    /…/
  ];
  
  return loadingPatterns.some(pattern => pattern.test(text));
}

/**
 * Get all clickable chess squares
 * @param {Page} page - Playwright page object
 * @returns {Promise<Array>} - Array of square information
 */
export async function getChessSquares(page) {
  return await page.evaluate(() => {
    const squares = document.querySelectorAll('[data-square], [class*="square"], .square');
    return Array.from(squares).map((square, index) => ({
      index,
      square: square.getAttribute('data-square') || square.className,
      bounds: square.getBoundingClientRect(),
      isVisible: square.offsetParent !== null
    }));
  });
}

/**
 * Perform chess move by coordinates
 * @param {Page} page - Playwright page object
 * @param {string} from - From square (e.g., 'e2')
 * @param {string} to - To square (e.g., 'e4')
 * @returns {Promise<boolean>} - True if move was attempted
 */
export async function performChessMove(page, from, to) {
  const squares = await getChessSquares(page);
  
  const fromSquare = squares.find(s => s.square.includes(from));
  const toSquare = squares.find(s => s.square.includes(to));
  
  if (fromSquare && toSquare && fromSquare.isVisible && toSquare.isVisible) {
    try {
      // Try drag and drop
      await page.mouse.move(fromSquare.bounds.x + fromSquare.bounds.width / 2, 
                           fromSquare.bounds.y + fromSquare.bounds.height / 2);
      await page.mouse.down();
      await page.mouse.move(toSquare.bounds.x + toSquare.bounds.width / 2, 
                           toSquare.bounds.y + toSquare.bounds.height / 2);
      await page.mouse.up();
      
      await page.waitForTimeout(1000);
      return true;
    } catch (error) {
      console.log(`Error performing move ${from}-${to}:`, error.message);
      return false;
    }
  }
  
  return false;
}
