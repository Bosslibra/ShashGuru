<script setup>
import { ref, watch, nextTick } from 'vue';
import { validateFen } from 'fentastic';
import MarkdownIt from 'markdown-it';

const server_url = import.meta.env.BASE_URL + 'backend'
const starting_fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
//emits
const emit = defineEmits(['loadingChat']);

// Props
const props = defineProps({
    fen: {
        type: String,
        required: true,
    },
});
// Markdown
const md = new MarkdownIt();


// Reactive state
const userInput = ref('');
const messages = ref([]);
const loading = ref(false)
const toAnalyse = ref(true);
// Methods

async function sendMessageSTREAMED() {
    if (userInput.value.trim() === '') return;

    const userMessage = { role: 'user', content: userInput.value };
    messages.value.push(userMessage);
    userInput.value = '';
    loading.value = true;
    emit('loadingChat', true);
    scrollToBottom();    

    try {
        const response = await fetch(server_url + '/response', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(messages.value),
        });

        if (!response.ok || !response.body) {
            throw new Error('Network response was not ok');
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullMessage = "";
        let streamStarted = false;

        messages.value.push({ role: 'assistant', content: '' });

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });

            console.log("Received message chunk:", chunk);

            if (chunk.includes("[START_STREAM]")) {
                streamStarted = true;
                continue;
            }

            if (!streamStarted) continue;

            if (chunk.includes("[END_STREAM]")) {
                fullMessage += chunk.replace("[END_STREAM]", "");
                break;
            }

            fullMessage += chunk;
            messages.value[messages.value.length - 1].content = fullMessage;
            scrollToBottom();
        }

        // Final update (optional, you already streamed into it)
        fullMessage = fullMessage.trim();
        messages.value[messages.value.length - 1].content = fullMessage;

    } catch (error) {
        console.error('Streaming error:', error);
        messages.value.push({ role: 'assistant', content: 'Error: unable to fetch response.' });
        scrollToBottom();
    } finally {
        loading.value = false;
        emit('loadingChat', false);
        console.log(messages.value)
    }
}


async function startAnalysisSTREAMED() {
    toAnalyse.value = false;
    messages.value.length = 0;
    const fenToAnalyse = validateFen(props.fen.trim()).valid ? props.fen.trim() : starting_fen;

    if (validateFen(fenToAnalyse).valid) {
        loading.value = true;
        emit('loadingChat', true);

        try {
            const response = await fetch(server_url + '/analysis', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ fen: fenToAnalyse })
            });

            if (!response.ok || !response.body) {
                console.error(response.ok, response.body)
                throw new Error("Network response was not ok.");
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullMessageANALYSIS = "";
            let streamStarted = false;
            let promptReceived = false;
            let systemPrompt = "";

            messages.value.push({ role: 'assistant', content: '' });

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                let chunk = decoder.decode(value, { stream: true });

                // log raw chunk for debugging
                console.log("Received chunk:", chunk);

                if (!promptReceived) {
                    const promptEndIndex = chunk.indexOf('[PROMPT_END]');
                    if (promptEndIndex > -1) {
                        const promptPart = chunk.substring(0, promptEndIndex);
                        try {
                            const promptData = JSON.parse(promptPart);
                            systemPrompt = promptData.prompt;
                            promptReceived = true;
                            
                            // Store the system prompt as the first message
                            messages.value.unshift({
                                role: 'system',
                                content: systemPrompt,
                                hidden: true // Optional: hide from UI
                            });
                            
                            // Remove the prompt part from the chunk
                            chunk = chunk.substring(promptEndIndex + '[PROMPT_END]'.length);
                        } catch (e) {
                            console.error("Error parsing prompt:", e);
                        }
                    }
                }

                if (chunk.includes("[START_STREAM]")) {
                    streamStarted = true;
                    continue;
                }

                if (!streamStarted) continue;

                if (chunk.includes("[END_STREAM]")) {
                    fullMessageANALYSIS += chunk.replace("[END_STREAM]", "");
                    break;
                }

                fullMessageANALYSIS += chunk;
                messages.value[messages.value.length - 1].content = fullMessageANALYSIS;
                scrollToBottom();   
            }

            // Final cleanup
            fullMessageANALYSIS = fullMessageANALYSIS.trim();
            messages.value[messages.value.length - 1].content = fullMessageANALYSIS;

        } catch (error) {
            console.error('Streaming error:', error);
            messages.value.push({ role: 'assistant', content: 'Error: unable to fetch analysis.' });
            scrollToBottom();
        } finally {
            loading.value = false;
            emit('loadingChat', false);
        }
    }
}


// Watcher
watch(() => props.fen, () => {
    toAnalyse.value = true;
});
// Add this watcher
watch(() => messages.value.length,  () => {
   scrollToBottom();
});
function renderedMarkdown(content) {
    return md.render(content)
}

function scrollToBottom() {
    nextTick(() => {
        const messagesEl = document.getElementById('messages');
        if (messagesEl) {
            messagesEl.scrollTo({
                top: messagesEl.scrollHeight,
                behavior: 'smooth'
            });
        }
    });
}
</script>


<template>
    <div class="container-fill d-flex flex-column  overflow-auto p-3 me-0 rounded-bottom rounded-4 w-100 h-100">
        <!-- Chat Messages -->
        <div id="messages" class=" flex-grow-1 h-100" style="scroll-behavior: smooth;">
            
            <div v-for="(message, i) in messages" :key="i">
                <div v-if="message.role === 'user'" class="d-flex mb-1 justify-content-end">
                    <div class="p-3 px-4 rounded-4 ms-5" id="usermessage">
                        <div class="text-break text-start message" v-html="md.render(message.content)"></div>

                    </div>
                </div>

                <div v-else-if="message.role === 'assistant'" class="p-3 pe-4 rounded-4 me-5">
                    <h6 class="mb-0">AI:</h6>
                    <div class="text-break text-start message" v-html="renderedMarkdown(message.content)"></div>
                </div>
            </div>
            <div v-if="loading" class="thinking-indicator p-3 pe-4 rounded-4 me-5">
                <div class="text-break text-start text-muted">
                    <span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                </div>
            </div>
        </div>
        <div class="flex-shrink-0">
            <div v-if="toAnalyse" class="flex-item d-flex justify-content-center">
                <button type="button"
                    class="btn btn-sm m-1 fs-4 text-black rounded rounded-4 custom-bg-primary px-5 py-3 fw-bold"
                    @click="startAnalysisSTREAMED">
                    Analyze
                </button>
                <!-- Input Field -->

            </div>
            <input v-model="userInput" v-else @keyup.enter="sendMessageSTREAMED" id="input"
                class="flex-item border rounded px-3 py-2 mt-2 w-100 text-white custom-box" placeholder="Ask Anything!"
                autocomplete="off" />
        </div>
    </div>
</template>

<style scoped>
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
}

/* width */
::-webkit-scrollbar {
    width: 10px;
}

/* Track */
::-webkit-scrollbar-track {}

/* Handle */
::-webkit-scrollbar-thumb {
    background: #888;
}

/* Handle on hover */
::-webkit-scrollbar-thumb:hover {
    background: #555;
}
</style>
