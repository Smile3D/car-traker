// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },

  modules: ['@pinia/nuxt', '@nuxtjs/tailwindcss', '@nuxtjs/i18n'],

  components: [
    { path: '~/components', pathPrefix: false }
  ],

  css: ['~/assets/css/main.css'],

  app: {
    head: {
      htmlAttrs: { lang: 'uk' },
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' }
      ]
    }
  },

  runtimeConfig: {
    apiBaseUrlInternal: 'http://localhost:8000',
    public: {
      apiBaseUrl: 'http://localhost:8000'
    }
  },

  i18n: {
    restructureDir: '',
    langDir: 'locales',
    vueI18n: 'i18n.config.ts',
    defaultLocale: 'uk',
    strategy: 'no_prefix',
    locales: [
      { code: 'uk', language: 'uk-UA', name: 'Українська', file: 'uk.json' },
      { code: 'ru', language: 'ru-RU', name: 'Русский', file: 'ru.json' }
    ],
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'i18n_locale',
      redirectOn: 'root'
    }
  }
})
