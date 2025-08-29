# ShashGuru E2E Testing Suite

This directory contains comprehensive end-to-end tests for the ShashGuru chess application using Playwright. The test suite covers all major functionality including accessibility, chess board interactions, AI chat features, PGN handling, and live broadcast viewing.

## 🎯 Test Coverage

### Core Functionality Tests
- **Accessibility (01)**: Page loading, navigation, responsive design
- **Chess Board (02)**: Board rendering, move interactions, FEN/PGN input, evaluation bar
- **AI Chat (03)**: Chat interface, analysis requests, message handling, thinking indicators
- **PGN Upload (04)**: PGN input validation, board state changes, error handling, reset functionality
- **Live Section (05)**: Lichess broadcast search, featured events, error handling

### Advanced Features
- Cross-browser testing (Chromium, Firefox, WebKit)
- Screenshot capture for debugging
- Network request monitoring
- Error state validation
- Loading state verification

## 🏗️ Project Structure

```
tests/
├── tests/                          # Test files
│   ├── 01-accessibility.spec.js    # Basic accessibility & navigation
│   ├── 02-chess-board.spec.js      # Chess board functionality
│   ├── 03-ai-chat.spec.js          # AI chat features
│   ├── 04-pgn-upload.spec.js       # PGN handling & validation
│   └── 05-live-section.spec.js     # Live broadcasts & events
├── test-results/                   # Screenshots & artifacts
├── playwright-report/              # HTML test reports
├── playwright.config.js            # Playwright configuration
├── package.json                    # Dependencies & scripts
├── run-tests.sh                    # Test runner script
├── .gitignore                      # Git ignore rules
├── README.md                       # This file
└── QUICK_START.md                  # Quick start guide
```

## 🧪 Test Details

### 01-accessibility.spec.js
Tests basic application accessibility and navigation:
- Page loads without errors
- Navigation elements are accessible
- Responsive design works across viewports
- Core UI components render correctly

### 02-chess-board.spec.js
Comprehensive chess board testing:
- Board visibility and proper rendering
- Interactive move making on the board
- FEN input (#fenInput) and position validation
- PGN input (#pgnInput) and move sequence loading
- Board controls (Starting Position button)
- Evaluation bar display and updates
- Error handling for invalid positions

### 03-ai-chat.spec.js
AI chat functionality validation:
- Chat interface accessibility and visibility
- Analysis button functionality
- Message input and submission
- AI response detection and display
- Thinking indicator during processing
- Conversation context maintenance
- Error handling for failed requests

### 04-pgn-upload.spec.js
PGN handling and validation:
- Direct PGN input via #pgnInput field
- Position validation through FEN changes
- Invalid PGN error handling and user feedback
- Board reset functionality after PGN loading
- Multiple PGN sequence testing
- Integration with board controls

### 05-live-section.spec.js
Live broadcast and events functionality:
- Access to live section via navigation
- Lichess broadcast URL search functionality
- Event ID search and validation
- Featured event display and interaction
- Error handling for invalid URLs/IDs
- Loading states and user feedback

## 🔧 Technical Implementation

### Selectors & Components
The tests use precise selectors matching the Vue.js frontend:
- `#fenInput`, `#pgnInput` for chess position inputs
- `.chessboard-container`, `.board-with-eval` for board elements
- `.container-fill`, `.message` for chat components
- `#input-event`, `#search-button` for live event search
- Proper button selectors for interactive elements

### Error Handling
- Graceful fallbacks for missing elements
- Comprehensive error message validation
- Network request failure testing
- Invalid input handling verification

### Browser Coverage
- **Chromium**: Primary development browser
- **Firefox**: Cross-browser compatibility
- **WebKit**: Safari-like rendering testing

## 🚀 Running Tests

### Quick Commands
```bash
# Run all tests
./run-tests.sh

# Run specific test file
./run-tests.sh test tests/02-chess-board.spec.js

# Run in headed mode (visible browser)
./run-tests.sh headed

# Generate and view report
./run-tests.sh report
```

### Advanced Usage
```bash
# Run specific browser
npx playwright test --project=chromium

# Run with debugging
npx playwright test --debug

# Update screenshots
npx playwright test --update-snapshots
```

### NPM Scripts
```bash
# Install dependencies and browsers
npm install
npm run install

# Run tests
npm test
npm run test:ui      # Interactive mode
npm run test:headed  # Visible browser
npm run test:debug   # Debug mode
```

## 📊 Test Reports

After running tests, view results:
- **HTML Report**: `npx playwright show-report`
- **Screenshots**: Check `test-results/` directory
- **CI Results**: Available in GitHub Actions

## 🔍 Debugging

### Screenshot Capture
All tests automatically capture screenshots at key points:
- `test-results/accessibility-*.png`
- `test-results/chess-board-*.png`
- `test-results/ai-chat-*.png`
- `test-results/pgn-*.png`
- `test-results/live-*.png`

### Common Issues
1. **Timeout Errors**: Increase wait times for slow networks
2. **Selector Mismatches**: Verify frontend component structure
3. **Network Failures**: Check API availability and CORS settings
4. **Browser Compatibility**: Test across different browsers

### Debug Tools
- **Trace Viewer**: `npx playwright show-trace trace.zip`
- **Test Generator**: `npx playwright codegen`
- **Inspector**: Use `page.pause()` in tests

## 🌐 Target Environment

These tests run against the live ShashGuru application:
- **URL**: http://shashguru.disi.unibo.it/
- **Environment**: Production deployment
- **Dependencies**: Requires active internet connection

## 🧩 Integration

### CI/CD Pipeline
Tests integrate with GitHub Actions:
```yaml
- name: Run Playwright Tests
  run: |
    cd tests
    npm ci
    npx playwright install
    npx playwright test
```

### Local Development
The test suite works with local development:
1. Update `baseURL` in `playwright.config.js`
2. Ensure local server is running
3. Run tests normally

## 🤝 Contributing

When adding new tests:
1. Follow the existing naming convention (`XX-feature.spec.js`)
2. Use descriptive test names and console logging
3. Add screenshot capture for debugging
4. Update this README with new test descriptions
5. Ensure cross-browser compatibility
6. Test both success and error scenarios

### Code Style
- Use async/await for all asynchronous operations
- Include comprehensive error handling
- Add meaningful console.log statements
- Capture screenshots at decision points
- Use precise selectors matching the frontend

## 📝 Notes

- Tests are designed to be robust and handle real-world scenarios
- All selectors match the actual Vue.js frontend implementation
- Error states are explicitly tested for better reliability
- Loading states and network delays are properly handled
- Tests can run in parallel for faster execution
- Mobile viewports are tested for responsive design

## 🔗 Related Files

- `QUICK_START.md`: Quick setup and execution guide
- `playwright.config.js`: Detailed configuration options
- `run-tests.sh`: Convenient test runner script
- `.github/workflows/`: CI/CD pipeline definitions
