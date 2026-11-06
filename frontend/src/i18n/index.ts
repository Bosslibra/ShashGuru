import i18next from 'i18next'
import LanguageDetector from 'i18next-browser-languagedetector'
import en from './locales/en.json'
import it from './locales/it.json'

export const SUPPORTED_LANGUAGES = ['en', 'it'] as const
export type Language = (typeof SUPPORTED_LANGUAGES)[number]
export const LANGUAGE_STORAGE_KEY = 'shashguru.lang'

export const resources = {
  en: { translation: en },
  it: { translation: it },
} as const

function applyDocumentLanguage(lng: string) {
  if (typeof document !== 'undefined') document.documentElement.lang = lng.split('-')[0]
}

i18next.use(LanguageDetector).init({
  resources,
  fallbackLng: 'en',
  supportedLngs: [...SUPPORTED_LANGUAGES],
  nonExplicitSupportedLngs: true,
  load: 'languageOnly',
  interpolation: { escapeValue: false },
  detection: {
    order: ['localStorage', 'navigator'],
    lookupLocalStorage: LANGUAGE_STORAGE_KEY,
    caches: ['localStorage'],
  },
})

applyDocumentLanguage(i18next.language)
i18next.on('languageChanged', applyDocumentLanguage)

export default i18next
