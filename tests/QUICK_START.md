# ShashGuru E2E Test Suite - Quick Start Guide

## 🎯 Overview

This is a comprehensive end-to-end test suite for the ShashGuru chess website (http://shashguru.disi.unibo.it/) built with Playwright. The tests verify all major functionality including chess board interaction, AI chat, PGN handling, and live broadcast viewing.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd tests
npm install
npm run install  # Install Playwright browsers
```

### 2. Run All Tests
```bash
./run-tests.sh
# or
npm test
```

### 3. Run Tests with Visual Browser
```bash
./run-tests.sh headed
# or
npm run test:headed
```

### 4. Run Individual Test Categories
```bash
# Test website accessibility and navigation
./run-tests.sh test tests/01-accessibility.spec.js

# Test chess board functionality  
./run-tests.sh test tests/02-chess-board.spec.js

# Test AI chat features
./run-tests.sh test tests/03-ai-chat.spec.js

# Test PGN input and validation
./run-tests.sh test tests/04-pgn-upload.spec.js

# Test live broadcast section
./run-tests.sh test tests/05-live-section.spec.js
```

### 5. Interactive Test Mode
```bash
npm run test:ui
```

## 📋 Test Coverage

### ✅ Website Accessibility (01)
- Basic reachability and load time
- Navigation elements accessibility
- Responsive design across devices
- Core UI component rendering

### ✅ Chess Board Functionality (02)
- Board visibility and proper rendering
- Interactive move making on the board
- FEN input (#fenInput) and position validation
- PGN input (#pgnInput) and move sequence loading
- Board controls (Starting Position button)
- Evaluation bar display and updates

### ✅ AI Chat Features (03)
- Chat interface accessibility (.container-fill)
- Analyze button functionality
- Message input and submission (#input)
- AI response detection (.message)
- Thinking indicator during processing
- Conversation context maintenance

### ✅ PGN Input and Validation (04)
- Direct PGN input via #pgnInput field
- Position validation through FEN changes
- Invalid PGN error handling
- Board reset functionality after loading
- Multiple PGN sequence testing
- Integration with board controls

### ✅ Live Broadcast Section (05)
- Access to live section via navigation
- Event search functionality (#input-event, #search-button)
- Lichess broadcast URL and ID support
- Featured event display
- Error handling for invalid URLs/IDs
- Loading states and user feedback

## 🔧 Using the Test Runner Script

The included shell script provides convenient commands:

```bash
# Run all tests (default)
./run-tests.sh

# Run specific test file
./run-tests.sh test tests/02-chess-board.spec.js

# Run tests with browser visible
./run-tests.sh headed

# Generate and view HTML report
./run-tests.sh report

# Run with debugging
./run-tests.sh debug

# Show help
./run-tests.sh help
```

## 📊 Test Results

After running tests, you can:

1. **View HTML Report**: `./run-tests.sh report` or `npx playwright show-report`
2. **Check Screenshots**: Look in `test-results/` folder
3. **Review Console Logs**: All tests include detailed logging
4. **Debug with Traces**: Open `.zip` trace files for detailed analysis

## 🔍 Debugging Failed Tests

### Quick Debug Steps
1. **Run in headed mode**: `./run-tests.sh headed`
2. **Check screenshots**: All tests capture screenshots at key points
3. **Review logs**: Tests include comprehensive console output
4. **Use debug mode**: `npm run test:debug` for step-by-step debugging

### Screenshot Locations
Tests automatically capture screenshots:
- `test-results/accessibility-*.png`
- `test-results/chess-board-*.png`
- `test-results/ai-chat-*.png`
- `test-results/pgn-*.png`
- `test-results/live-*.png`

### Common Issues & Solutions
1. **Element not found**: Check console logs for selector attempts
2. **Timeout errors**: Increase wait times or check network
3. **AI chat not responding**: Check for .thinking-indicator and wait longer
4. **PGN not loading**: Verify #pgnInput selector and FEN changes

## 🌐 Cross-Browser Testing

Tests run on multiple browsers by default:
- **Chromium** (Desktop Chrome)
- **Firefox** 
- **WebKit** (Safari)

Run specific browser:
```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

## ⚙️ Configuration

Key settings in `playwright.config.js`:
- **Base URL**: `http://shashguru.disi.unibo.it`
- **Retries**: 2 retries on failure
- **Timeouts**: 30 seconds for actions, 60 seconds for navigation
- **Screenshots**: Captured on failure and key steps
- **Parallel**: Disabled for more stable execution

## 🎛️ Advanced Usage

### Run Specific Test Pattern
```bash
npx playwright test -g "chess board"
npx playwright test -g "AI chat"
```

### Run Single Test in Debug Mode
```bash
npx playwright test tests/02-chess-board.spec.js --debug
```

### Update Snapshots
```bash
npx playwright test --update-snapshots
```

### Generate Custom Report
```bash
npx playwright test --reporter=html --reporter=junit
```

## 🔧 Test Architecture

### Selector Strategy
Tests use precise selectors matching Vue.js components:
- **Input fields**: `#fenInput`, `#pgnInput`, `#input-event`
- **Containers**: `.chessboard-container`, `.container-fill`
- **Interactive elements**: `button`, `.message`, `.thinking-indicator`
- **Fallback patterns**: Multiple selector strategies for reliability

### Error Handling
- Graceful fallbacks when elements aren't found
- Comprehensive error message validation  
- Network request failure testing
- Invalid input handling verification

### Performance Considerations
- Strategic wait times for network requests
- Efficient screenshot capture
- Parallel test execution disabled for stability
- Retry logic for flaky network conditions

## 📈 CI/CD Integration

### GitHub Actions
The test suite includes automated CI/CD via `../.github/workflows/e2e-tests.yml`:
```yaml
- name: Run E2E Tests
  working-directory: ./tests
  run: |
    npm ci
    npx playwright install
    ./run-tests.sh
```

Features:
- Runs on push/PR to main branches
- Daily scheduled runs at 6 AM UTC
- Manual trigger with browser selection
- Multi-browser testing matrix
- Artifact collection for debugging
- Website health checks

### Local Development
For local testing:
1. Update `baseURL` in `playwright.config.js` if needed
2. Ensure target application is running
3. Run tests normally

## 🆘 Troubleshooting

### Installation Issues
```bash
# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
npm run install
```

### Browser Issues
```bash
# Install system dependencies
npx playwright install-deps
```

### Network Issues
- Check internet connection
- Verify website is accessible: http://shashguru.disi.unibo.it/
- Increase timeouts in config if needed

### Test Failures
1. **Check recent screenshots** in `test-results/`
2. **Review console logs** for detailed error information
3. **Run single test** to isolate issues
4. **Use debug mode** for step-by-step analysis

## 📝 Adding New Tests

### Creating New Test Files
1. Follow naming convention: `XX-feature.spec.js`
2. Use existing test structure as template
3. Include comprehensive error handling
4. Add meaningful console.log statements
5. Capture screenshots at decision points

### Example Test Structure
```javascript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should test feature', async ({ page }) => {
    // Test implementation with screenshots
    await page.screenshot({ path: 'test-results/feature-test.png' });
  });
});
```

## 📞 Support & Resources

For issues or questions:
1. **Check console logs**: Tests provide detailed debugging information
2. **Review screenshots**: Visual confirmation of test state
3. **Use trace viewer**: `npx playwright show-trace trace.zip`
4. **Playwright docs**: https://playwright.dev/docs

---

**Status**: ✅ All tests configured and running successfully  
**Last Updated**: August 29, 2025  
**Website**: http://shashguru.disi.unibo.it/  
**Browsers**: Chromium, Firefox, WebKit
