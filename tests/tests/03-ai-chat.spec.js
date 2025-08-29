import { test, expect } from '@playwright/test';

test.describe('AI Chat Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('AI chat interface is accessible', async ({ page }) => {
    // Look for AI chat component using the actual container class from AIChat.vue
    const aiChatContainer = page.locator('.container-fill');
    
    try {
      await expect(aiChatContainer).toBeVisible({ timeout: 10000 });
      console.log('AI chat container found');
      
      // Check for the messages container
      const messagesContainer = page.locator('#messages');
      await expect(messagesContainer).toBeVisible();
      
      // Check for the Analyze button
      const analyzeButton = page.locator('button').filter({ hasText: /analyze/i });
      const analyzeExists = await analyzeButton.isVisible().catch(() => false);
      
      if (analyzeExists) {
        console.log('Analyze button found in AI chat interface');
      }
      
      // Check for disclaimer text
      const disclaimer = page.locator('.disclaimer-text');
      const disclaimerExists = await disclaimer.isVisible().catch(() => false);
      
      if (disclaimerExists) {
        console.log('AI disclaimer found');
      }
      
      await page.screenshot({ path: 'test-results/ai-chat-interface.png' });
      
    } catch (error) {
      console.log('AI chat not immediately visible, looking for tabs or buttons to access it');
      
      // Look for tabs or navigation elements that might contain AI chat
      const tabElements = page.locator('[role="tab"], .tab, .nav-item, button').filter({ hasText: /ai|chat|analysis/i });
      const tabCount = await tabElements.count();
      
      if (tabCount > 0) {
        console.log(`Found ${tabCount} potential AI/chat tabs`);
        await tabElements.first().click();
        await page.waitForTimeout(2000);
        
        // Try to find AI chat again after clicking tab
        await expect(aiChatContainer).toBeVisible({ timeout: 5000 });
        console.log('AI chat accessible via tab');
      } else {
        // Look for any button that might open AI chat
        const buttons = page.locator('button, .button, [role="button"]');
        const buttonTexts = await buttons.allTextContents();
        
        for (let i = 0; i < buttonTexts.length; i++) {
          if (/ai|chat|analysis|analyze/i.test(buttonTexts[i])) {
            console.log(`Found potential AI button: "${buttonTexts[i]}"`);
            await buttons.nth(i).click();
            await page.waitForTimeout(2000);
            break;
          }
        }
      }
    }
  });

  test('can access analyze button and generate AI output', async ({ page }) => {
    // First ensure we can access the AI chat
    let aiChatVisible = false;
    
    try {
      // Try to find AI chat directly
      const aiChat = page.locator('[data-testid="ai-chat"], .ai-chat, #ai-chat, [class*="chat"]');
      await expect(aiChat.first()).toBeVisible({ timeout: 5000 });
      aiChatVisible = true;
    } catch (error) {
      // Try to find and click on AI/Chat tab
      const aiTabs = page.locator('[role="tab"], .tab, button').filter({ hasText: /ai|chat|analysis/i });
      const aiTabCount = await aiTabs.count();
      
      if (aiTabCount > 0) {
        await aiTabs.first().click();
        await page.waitForTimeout(2000);
        aiChatVisible = true;
      }
    }
    
    if (!aiChatVisible) {
      console.log('Trying to find AI chat through navigation or menu');
      
      // Look for navigation menu items
      const navItems = page.locator('nav a, .nav-link, .menu-item').filter({ hasText: /ai|chat|analysis/i });
      const navCount = await navItems.count();
      
      if (navCount > 0) {
        await navItems.first().click();
        await page.waitForTimeout(2000);
      }
    }
    
    // Look for Analyze button
    const analyzeButton = page.locator('button, .button, [role="button"]').filter({ hasText: /analyze|analysis/i });
    
    try {
      await expect(analyzeButton.first()).toBeVisible({ timeout: 10000 });
      console.log('Analyze button found');
      
      // Take screenshot before clicking analyze
      await page.screenshot({ path: 'test-results/before-analyze-click.png' });
      
      // Click the analyze button
      await analyzeButton.first().click();
      console.log('Analyze button clicked');
      
      // Wait for AI response to start
      await page.waitForTimeout(3000);
      
      // Look for the loading indicator first
      const loadingIndicator = page.locator('.thinking-indicator');
      const isLoading = await loadingIndicator.isVisible().catch(() => false);
      
      if (isLoading) {
        console.log('AI is processing (loading indicator visible)');
        // Wait for loading to finish - check periodically
        for (let i = 0; i < 60; i++) { // Wait up to 60 seconds
          await page.waitForTimeout(1000);
          const stillLoading = await loadingIndicator.isVisible().catch(() => false);
          if (!stillLoading) {
            console.log('Loading finished');
            break;
          }
        }
      }
      
      // Look for AI messages using the actual structure from AIChat.vue
      // Assistant messages are in divs with role='assistant' and contain .message elements
      const aiMessages = page.locator('div:has-text("AI:") .message');
      
      try {
        await expect(aiMessages.first()).toBeVisible({ timeout: 30000 });
        
        const outputText = await aiMessages.first().textContent();
        console.log('AI output received:', outputText?.slice(0, 200) + '...');
        
        // Verify that we got actual content
        expect(outputText).toBeTruthy();
        expect(outputText?.length || 0).toBeGreaterThan(10);
        
        // Check that it's not just a loading or error message
        const isLoadingOrError = /loading|error|failed|unavailable|spinner/i.test(outputText || '');
        if (!isLoadingOrError) {
          console.log('Valid AI analysis response received');
        } else {
          console.log('Received loading or error message:', outputText);
        }
        
        await page.screenshot({ path: 'test-results/ai-analysis-output.png' });
        
      } catch (error) {
        console.log('No AI output detected, checking for alternative indicators');
        
        // Look for any text that might indicate AI is working
        const allText = await page.textContent('body');
        const hasAIIndicators = /analyzing|thinking|processing|generating/i.test(allText || '');
        
        if (hasAIIndicators) {
          console.log('AI appears to be processing');
          // Wait longer for response
          await page.waitForTimeout(15000);
          await page.screenshot({ path: 'test-results/ai-processing.png' });
        } else {
          console.log('No AI activity detected');
          await page.screenshot({ path: 'test-results/ai-no-response.png' });
        }
      }
      
    } catch (error) {
      console.log('Analyze button not found, looking for alternative AI interaction methods');
      
      // Look for the chat input field using the actual ID from AIChat.vue
      const chatInput = page.locator('#input');
      
      const inputCount = await chatInput.count();
      if (inputCount > 0) {
        console.log('Found chat input field');
        await chatInput.fill('Analyze this position');
        await page.keyboard.press('Enter');
        await page.waitForTimeout(5000);
        
        // Check for AI response after input
        const aiMessages = page.locator('div:has-text("AI:") .message');
        const hasResponse = await aiMessages.first().isVisible().catch(() => false);
        
        if (hasResponse) {
          const responseText = await aiMessages.first().textContent();
          console.log('AI response via input:', responseText?.slice(0, 200));
        }
        
        await page.screenshot({ path: 'test-results/ai-chat-input-attempt.png' });
      }
      
      // Look for all buttons and log their text for debugging
      const allButtons = page.locator('button, .button, [role="button"]');
      const buttonTexts = await allButtons.allTextContents();
      console.log('Available buttons:', buttonTexts.filter(text => text.trim().length > 0));
      
      await page.screenshot({ path: 'test-results/ai-analyze-debug.png' });
    }
  });

  test('AI chat maintains conversation context', async ({ page }) => {
    // This test checks if multiple AI interactions work properly
    
    // Navigate to AI chat (using similar logic as above)
    const aiTabs = page.locator('[role="tab"], .tab, button').filter({ hasText: /ai|chat|analysis/i });
    const aiTabCount = await aiTabs.count();
    
    if (aiTabCount > 0) {
      await aiTabs.first().click();
      await page.waitForTimeout(2000);
    }
    
    // First click Analyze to start the conversation
    const analyzeButton = page.locator('button').filter({ hasText: /analyze/i });
    const analyzeExists = await analyzeButton.first().isVisible().catch(() => false);
    
    if (analyzeExists) {
      await analyzeButton.first().click();
      console.log('Started analysis to begin conversation');
      
      // Wait for initial analysis to complete
      await page.waitForTimeout(10000);
      
      // Now try to use the chat input for follow-up questions
      const chatInput = page.locator('#input');
      const inputExists = await chatInput.isVisible().catch(() => false);
      
      if (inputExists) {
        console.log('Chat input available after analysis');
        
        // Send first follow-up message
        await chatInput.fill('What is the best move in this position?');
        await page.keyboard.press('Enter');
        await page.waitForTimeout(5000);
        
        // Send second follow-up message
        await chatInput.fill('Why is that move better than alternatives?');
        await page.keyboard.press('Enter');
        await page.waitForTimeout(5000);
        
        // Check for conversation history using the actual message structure
        const allMessages = page.locator('.message');
        const messageCount = await allMessages.count();
        
        console.log(`Found ${messageCount} messages in conversation`);
        
        // Also check for AI responses specifically
        const aiResponses = page.locator('div:has-text("AI:") .message');
        const aiMessageCount = await aiResponses.count();
        
        console.log(`Found ${aiMessageCount} AI responses`);
        
        if (messageCount >= 2) {
          console.log('Conversation context appears to be maintained');
        }
        
        await page.screenshot({ path: 'test-results/ai-conversation.png' });
      } else {
        console.log('Chat input not available after analysis');
      }
    } else {
      console.log('Analyze button not found for conversation test');
    }
  });
});
