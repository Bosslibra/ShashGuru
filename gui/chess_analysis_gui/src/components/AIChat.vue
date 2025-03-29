<script setup>
import { ref, watch } from 'vue';
import axios from 'axios';
import { validateFen } from 'fentastic';

// Props
const props = defineProps({
    fen: {
        type: String,
        required: true,
    },
});

// Reactive state
const userInput = ref('');
const messages = ref([]);

// Methods
async function sendMessage() {
    if (userInput.value.trim() === '') return; //No empty messages

    messages.value.push({ role: 'user', content: userInput.value });
    userInput.value = ''; // Clear input field

    try {
        const response = await axios.post('http://127.0.0.1:5000/response',
            JSON.stringify(messages.value),
            {
                headers: {
                    'Content-Type': 'application/json'
                }
            }
        );
        messages.value = response.data
    } catch (error) {
        console.error('Error querying the LLM:', error);
        messages.value.push({ role: 'assistant', content: 'Error: unable to fetch response.' });
    }
}

async function startAnalysis() {
    messages.value.length = 0; // A new analysis only has messages pertaining to that analysis
    if (validateFen(props.fen.trim()).valid) {
        try {
            const analysis = await axios.post('http://127.0.0.1:5000/analysis',
                JSON.stringify({ fen: props.fen }),
                {
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
            if (Array.isArray(analysis.data)) {
                messages.value = analysis.data;
            } else {
                console.error('Unexpected response format:', analysis.data);
            }
        } catch (error) {
            console.error('Error querying the LLM:', error);
            messages.value.push({ role: 'assistant', content: 'Error: unable to fetch analysis.' });
        }
    }
}

// Watcher
watch(() => props.fen, () => {
    startAnalysis();
});

function isFirstPrompt(stringToCheck) { //Shitties way to do this, but oh well
    let isFirstPrompt = 
        (
            stringToCheck.includes("My chess engine suggests the best move")
            && stringToCheck.includes("Please also consider, without speaking about them, that the engine consideres other 3 good moves, which are the following:")
            && stringToCheck.includes("I will explain the board situation:")
            && stringToCheck.includes("Can you please explain why is the best move good? Answer with a lengthy analysis")
        );
    return isFirstPrompt
}
</script>

<template>
    <div id="chat-view" class="container d-flex flex-column justify-content-between p-3 me-0 rounded-4 w-100 h-100">
        <!-- Chat Messages -->
        <div id="messages" class="flex-item">
            <div v-for="(message, i) in messages" :key="i">
                <div v-if="message.role === 'user' && !isFirstPrompt(message.content)" class="d-flex justify-content-end">
                    <div class="p-3 px-4 rounded-4 ms-5" id="usermessage">
                        <span class="text-break text-start justify-content-start">{{ message.content }}</span>
                    </div>
                </div>

                <div v-else-if="message.role === 'assistant'" class="p-3 pe-4 rounded-4 me-5">
                    <h6>AI:</h6>
                    <span class="text-break text-start">{{ message.content }}</span>
                </div>
            </div>
        </div>

        <!-- Input Field -->
        <input v-model="userInput" @keyup.enter="sendMessage" id="input"
            class="flex-item border rounded px-3 py-2 mt-2 w-100 text-white" placeholder="Ask Anything!"
            autocomplete="off" />
    </div>
</template>

<style scoped>
#chat-view {
    background-color: #262421;
}

#input {
    background-color: #2e2e2e;
    border-color: #2e2e2e !important;
    outline: none;
}

input::placeholder {
    color: #b2b2b2;
}

#usermessage {
    background: #323232 !important;
}
</style>
