<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'
import MarkdownIt from 'markdown-it'
import { useTranslation } from 'i18next-vue'
import { Brain, Check, CircleAlert, Copy, RefreshCw, SendHorizontal, Sparkles } from '@lucide/vue'
import IconButton from './IconButton.vue'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { InputGroup, InputGroupAddon, InputGroupButton, InputGroupInput } from '@/components/ui/input-group'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { useChatStore } from '@/stores/chat'

const { t } = useTranslation()
const chat = useChatStore()
const {
  visibleMessages,
  messages,
  loading,
  toAnalyse,
  styles: analysisStyles,
  style: selectedStyle,
  backend,
  checkingLocalBackend,
  isLocalBackendAvailable,
} = storeToRefs(chat)

const md = new MarkdownIt()

const userInput = ref('')
const messagesEl = ref<HTMLElement | null>(null)
const copiedIndex = ref<number | null>(null)
const isClipboardCopyingAvailable = ref(true)
/** Follow the stream only while the user is reading the bottom of the chat. */
const stickToBottom = ref(true)

/** Index of the last message: only that one can be regenerated. */
const lastIndex = computed(() => messages.value.length - 1)

function renderedMarkdown(content: string) {
  return md.render(content)
}

function onScroll() {
  const el = messagesEl.value
  if (!el) return
  stickToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 80
}

function scrollToBottom(force = false) {
  if (force) stickToBottom.value = true
  if (!stickToBottom.value) return
  nextTick(() =>
    messagesEl.value?.scrollTo({
      top: messagesEl.value.scrollHeight,
      // Smooth scrolling on every streamed token would lag behind the text
      behavior: loading.value ? 'auto' : 'smooth',
    }),
  )
}

async function send() {
  const question = userInput.value
  if (!question.trim() || loading.value) return
  userInput.value = ''
  scrollToBottom(true)
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

function onStyleChange(value: unknown) {
  if (typeof value === 'string') selectedStyle.value = value
}

watch(messages, () => scrollToBottom(), { deep: true })

onMounted(() => {
  isClipboardCopyingAvailable.value = !!navigator.clipboard?.writeText
  chat.init()
  scrollToBottom(true)
})
</script>

<template>
  <div class="container-fill chat flex h-full w-full flex-col overflow-hidden p-(--pad)">
    <!-- Messages -->
    <div id="messages" ref="messagesEl" class="app-scrollbar min-h-0 flex-1 overflow-y-auto" @scroll.passive="onScroll">
      <!-- Empty state -->
      <Empty v-if="visibleMessages.length === 0 && !loading" class="my-4">
        <EmptyHeader>
          <EmptyMedia variant="icon"><Brain aria-hidden="true" /></EmptyMedia>
          <EmptyTitle>{{ t('chat.introTitle') }}</EmptyTitle>
          <EmptyDescription>{{ t('chat.intro') }}</EmptyDescription>
        </EmptyHeader>
      </Empty>

      <div class="flex flex-col gap-4">
        <template v-for="message in visibleMessages" :key="message.index">
          <!-- User -->
          <div v-if="message.role === 'user'" class="flex justify-end">
            <div class="user-message ml-10 max-w-[85%] rounded-(--radius) bg-secondary px-4 py-2.5">
              <div class="message text-break text-sm" v-html="md.render(message.content)"></div>
            </div>
          </div>

          <!-- Failed answer -->
          <Alert v-else-if="message.role === 'assistant' && message.error" variant="destructive" class="chat-error">
            <CircleAlert aria-hidden="true" />
            <AlertTitle>{{ t('chat.errorTitle') }}</AlertTitle>
            <AlertDescription class="break-words">{{ message.content }}</AlertDescription>
            <Button
              v-if="message.index === lastIndex && !loading"
              variant="outline"
              size="sm"
              class="col-span-2 mt-2 w-fit"
              @click="chat.regenerate()"
            >
              <RefreshCw aria-hidden="true" />{{ t('common.retry') }}
            </Button>
          </Alert>

          <!-- AI -->
          <div v-else-if="message.role === 'assistant'" class="assistant-message mr-6">
            <div class="mb-1 flex items-center gap-1.5 text-lime">
              <Sparkles class="size-3.5" aria-hidden="true" />
              <h6 class="panel-label text-lime! m-0">{{ t('chat.ai') }}</h6>
            </div>
            <div class="message md-content text-break text-sm" v-html="renderedMarkdown(message.content)"></div>
            <div v-if="!loading && isClipboardCopyingAvailable" class="message-actions mt-1 flex gap-1 text-muted-foreground">
              <IconButton
                v-if="copiedIndex !== message.index"
                :label="t('chat.copy')"
                size="icon-sm"
                @click="copyMessage(message.index, message.content)"
              >
                <Copy aria-hidden="true" />
              </IconButton>
              <IconButton v-else :label="t('chat.copied')" size="icon-sm"><Check class="text-lime" aria-hidden="true" /></IconButton>
              <IconButton v-if="message.index === lastIndex" :label="t('chat.regenerate')" size="icon-sm" @click="chat.regenerate()">
                <RefreshCw aria-hidden="true" />
              </IconButton>
            </div>
          </div>
        </template>

        <div v-if="loading" class="thinking-indicator flex items-center gap-2 text-sm text-muted-foreground" role="status">
          <Spinner class="size-4 text-lime" aria-hidden="true" />
          <span>{{ t('chat.thinking') }}</span>
        </div>
      </div>
    </div>

    <!-- Backend status -->
    <div class="ai-pc-status mt-2 flex items-center justify-center gap-2 border-b border-(--panel-divider) pb-2">
      <Badge v-if="checkingLocalBackend" variant="outline" class="gap-1.5 text-warning">
        <Spinner class="size-3" aria-hidden="true" />{{ t('chat.checkingBackend') }}
      </Badge>
      <template v-else>
        <Badge variant="outline" class="gap-1.5" :class="isLocalBackendAvailable ? 'text-success' : 'text-muted-foreground'">
          <span
            class="size-1.5 rounded-full"
            :class="isLocalBackendAvailable ? 'bg-success shadow-[0_0_6px_var(--success)]' : 'bg-muted-foreground'"
            aria-hidden="true"
          ></span>
          {{ backend === 'local' ? t('chat.backendEnabled') : t('chat.backendRemote') }}
        </Badge>
        <IconButton :label="t('chat.recheckBackend')" size="icon-xs" @click="chat.recheckBackend()">
          <RefreshCw aria-hidden="true" />
        </IconButton>
      </template>
    </div>

    <p class="disclaimer-text mt-2 text-center text-xs text-muted-foreground">{{ t('chat.disclaimer') }}</p>

    <div class="mt-3 shrink-0">
      <!-- Analyze -->
      <div v-if="toAnalyse" class="flex flex-wrap items-end justify-center gap-3">
        <div class="flex flex-col gap-1.5">
          <Label for="style-selector" class="panel-label">{{ t('chat.style') }}</Label>
          <Select :model-value="selectedStyle" @update:model-value="onStyleChange">
            <SelectTrigger id="style-selector" class="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="style in analysisStyles" :key="style.value" :value="style.value">
                {{ style.label }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button size="lg" class="h-10 px-6 text-base font-bold" @click="chat.analyze()">
          <Sparkles aria-hidden="true" />{{ t('chat.analyze') }}
        </Button>
      </div>

      <!-- Question -->
      <InputGroup v-else>
        <InputGroupInput
          id="input"
          v-model="userInput"
          :placeholder="t('chat.placeholder')"
          :aria-label="t('chat.inputLabel')"
          autocomplete="off"
          @keyup.enter="send"
        />
        <InputGroupAddon align="inline-end">
          <InputGroupButton
            variant="default"
            size="icon-xs"
            :aria-label="t('chat.send')"
            :disabled="loading || !userInput.trim()"
            @click="send"
          >
            <SendHorizontal aria-hidden="true" />
          </InputGroupButton>
        </InputGroupAddon>
      </InputGroup>
    </div>
  </div>
</template>
