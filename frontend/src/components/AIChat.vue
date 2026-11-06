<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import MarkdownIt from 'markdown-it'
import { useChatStore } from '@/stores/chat'

const chat = useChatStore()
const {
  visibleMessages,
  messages,
  loading,
  toAnalyse,
  styles: analysisStyles,
  style: selectedStyle,
  checkingLocalBackend,
  isLocalBackendAvailable,
} = storeToRefs(chat)

const md = new MarkdownIt()

const userInput = ref('')
const messagesEl = ref<HTMLElement | null>(null)
const copiedIndex = ref<number | null>(null)
const isClipboardCopyingAvailable = ref(true)

/** Index of the last message: only that one can be regenerated. */
const lastIndex = computed(() => messages.value.length - 1)

function renderedMarkdown(content: string) {
  return md.render(content)
}

function scrollToBottom() {
  nextTick(() => messagesEl.value?.scrollTo({ top: messagesEl.value.scrollHeight, behavior: 'smooth' }))
}

async function send() {
  const question = userInput.value
  if (!question.trim() || loading.value) return
  userInput.value = ''
  await chat.ask(question)
}

async function copyMessage(index: number, text: string) {
  try {
    await navigator.clipboard.writeText(text)
    copiedIndex.value = index
    setTimeout(() => {
      if (copiedIndex.value === index) copiedIndex.value = null
    }, 1000)
  } catch (err) {
    console.error('Copying failed:', err)
  }
}

watch(messages, scrollToBottom, { deep: true })

onMounted(() => {
  isClipboardCopyingAvailable.value = !!navigator.clipboard?.writeText
  chat.init()
  scrollToBottom()
})
</script>


<template>
    <div class="container-fill d-flex flex-column  overflow-auto p-3 me-0  rounded-4 w-100 h-100">
        <!-- Chat Messages -->
        <div id="messages" ref="messagesEl" class="flex-grow-1 h-100 overflow-auto" style="scroll-behavior: smooth;">

            <div v-for="message in visibleMessages" :key="message.index">
                <div v-if="message.role === 'user'" class="d-flex mb-1 justify-content-end">
                    <div class="p-3 px-4 rounded-4 ms-5" id="usermessage">
                        <div class="text-break text-start message" v-html="md.render(message.content)"></div>

                    </div>
                </div>

                <div v-else-if="message.role === 'assistant'" class="p-3 pe-4 rounded-4 me-5">
                    <h6 class="mb-0">AI:</h6>
                    <div class="text-break text-start message" v-html="renderedMarkdown(message.content)"></div>
                    <!-- Action buttons (copy / retry) -->
                    <div v-if="!loading && isClipboardCopyingAvailable " class="d-flex message-actions">
                        <span v-if="copiedIndex !== message.index" class="material-icons-outlined p-2 fs-5" role="button" title="Copia"
                            @click="copyMessage(message.index, message.content)">
                            content_copy
                        </span>
                        <span v-else class="material-icons-outlined p-2 fs-5" role="button" title="Copiato!">
                            check
                        </span>
                        <span v-if="message.index === lastIndex" class="material-icons-outlined p-2 fs-5" role="button" title="Rigenera"
                            @click="chat.regenerate()">
                            refresh
                        </span>
                    </div>
                </div>
            </div>
            <div v-if="loading" class="thinking-indicator p-3 pe-4 rounded-4 me-5">
                <div class="text-break text-start ">
                    <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                </div>
            </div>
        </div>

        <!-- AI PC Status Indicator -->
        <div class="ai-pc-status text-center mb-2">
            <div v-if="checkingLocalBackend" class="d-flex justify-content-center align-items-center gap-2">
                <span class="spinner-border spinner-border-sm text-warning" role="status" aria-hidden="true"></span>
                <small class="text-warning">Checking local AI PC...</small>
            </div>
            <div v-else-if="isLocalBackendAvailable" class="d-flex justify-content-center align-items-center gap-2">
                <div class="status-indicator status-online"></div>
                <small class="text-success fw-bold">AI PC Enabled</small>
                <button class="btn btn-sm p-1 ms-2 refresh-btn" 
                        @click="chat.recheckBackend()" 
                        title="Re-check local backend"
                        :disabled="checkingLocalBackend">
                    <span class="material-icons-outlined" style="font-size: 14px;">refresh</span>
                </button>
            </div>
        </div>

        <!-- AI Content Disclaimer -->
        <div class="disclaimer-text text-center mt-2 mb-2">
            <small class="text-secondary">
                AI-generated content may contain errors or inaccuracies. Please verify important information.
            </small>
        </div>

        <div class="flex-shrink-0">
            <div v-if="toAnalyse" class="flex-item">
                <!-- Style Selector and Analyze Button - Horizontally Spaced -->
                <div class="d-flex justify-content-center align-items-center gap-3 mb-3">
                    <div class="d-flex flex-column align-items-center">
                        <label for="style-selector" class="style-label mb-1">Analysis Style</label>
                        <select id="style-selector" 
                                v-model="selectedStyle" 
                                class="form-select style-selector"
                                aria-label="Analysis Style">
                            <option v-for="style in analysisStyles" 
                                    :key="style.value" 
                                    :value="style.value">
                                {{ style.label }}
                            </option>
                        </select>
                    </div>
                    
                    <button type="button"
                        class="btn btn-sm fs-4 text-black rounded rounded-4 custom-bg-primary px-5 py-3 fw-bold"
                        @click="chat.analyze()">
                        Analyze
                    </button>
                </div>
            </div>
            <input v-model="userInput" v-else @keyup.enter="send" id="input"
                class="flex-item border rounded px-3 py-2 mt-2 w-100 text-white custom-box" placeholder="Ask Anything!"
                autocomplete="off" />
        </div>
    </div>
</template>

<style scoped>
.message-actions {
    color: #bbb;
}

.message-actions>span {
    border-radius: 50%;
}

.message-actions>span:hover {
    background-color: #ffffff1e;
}

.custom-box {
    background-color: #2e2e2e;
    border-color: #2e2e2e !important;
    outline: none;
}

.custom-bg-primary {
    border: 2px solid #aaa23a;
}

.custom-bg-primary:hover {
    border: 2px solid #aaa23a;
    background-color: transparent;
    color: #aaa23a !important;
}

#input::placeholder {
    color: #b2b2b2;
}

#usermessage {
    background: #323232 !important;
}

.message>* {
    margin: 0% !important;
}

.spinner-border,
h6 {
    color: #aaa23a;
    /* Spinner color */
}

#messages {
    overflow: auto;
    max-height: 100%;
    scrollbar-width: thin;
    scrollbar-color: #888 transparent;
}

/* width */
::-webkit-scrollbar {
    width: 10px;
}

/* Track */
::-webkit-scrollbar-track {
    background: transparent;
}

/* Handle */
::-webkit-scrollbar-thumb {
    background: #888;
}

/* Handle on hover */
::-webkit-scrollbar-thumb:hover {
    background: #555;
}

.disclaimer-text {
    border-top: 1px solid #3a3a3a;
    padding-top: 8px;
}

.disclaimer-text small {
    font-size: 0.75rem;
    opacity: 0.8;
}

.ai-pc-status {
    border-bottom: 1px solid #3a3a3a;
    padding-bottom: 8px;
}

.status-indicator {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    display: inline-block;
}

.status-online {
    background-color: #28a745;
    box-shadow: 0 0 8px rgba(40, 167, 69, 0.6);
    animation: pulse 2s infinite;
}

.status-offline {
    background-color: #6c757d;
}

@keyframes pulse {
    0% {
        box-shadow: 0 0 8px rgba(40, 167, 69, 0.6);
    }
    50% {
        box-shadow: 0 0 16px rgba(40, 167, 69, 0.8);
    }
    100% {
        box-shadow: 0 0 8px rgba(40, 167, 69, 0.6);
    }
}

.refresh-btn {
    background: none;
    border: none;
    color: #6c757d;
    transition: color 0.2s ease;
}

.refresh-btn:hover:not(:disabled) {
    color: #aaa23a;
}

.refresh-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.style-selector {
    background-color: #2e2e2e;
    border: 2px solid #aaa23a;
    color: #fff;
    border-radius: 8px;
    padding: 8px 12px;
    min-width: 150px;
    max-width: 200px;
    flex-shrink: 0;
}

.style-selector:focus {
    background-color: #2e2e2e;
    border-color: #aaa23a;
    color: #fff;
    box-shadow: 0 0 0 0.2rem rgba(170, 162, 58, 0.25);
}

.style-selector option {
    background-color: #2e2e2e;
    color: #fff;
}

.style-label {
    color: #aaa23a;
    font-size: 0.85rem;
    font-weight: 600;
    text-align: center;
    margin: 0;
}
</style>