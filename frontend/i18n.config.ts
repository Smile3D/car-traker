export default defineI18nConfig(() => ({
  legacy: false,
  numberFormats: {
    uk: {
      currency: { style: 'currency', currency: 'UAH' },
      decimal: { style: 'decimal', maximumFractionDigits: 0 }
    },
    ru: {
      currency: { style: 'currency', currency: 'UAH' },
      decimal: { style: 'decimal', maximumFractionDigits: 0 }
    }
  },
  datetimeFormats: {
    uk: {
      short: { year: 'numeric', month: '2-digit', day: '2-digit' },
      shortWithTime: { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }
    },
    ru: {
      short: { year: 'numeric', month: '2-digit', day: '2-digit' },
      shortWithTime: { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }
    }
  }
}))
