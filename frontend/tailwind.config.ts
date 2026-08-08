import type { Config } from 'tailwindcss'

function withOpacity(variable: string): string {
  return `rgb(var(${variable}) / <alpha-value>)`
}

export default <Partial<Config>>{
  content: [
    './app/components/**/*.{vue,js,ts}',
    './app/layouts/**/*.vue',
    './app/pages/**/*.vue',
    './app/app.vue',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: withOpacity('--color-primary'),
          hover: withOpacity('--color-primary-hover'),
          foreground: withOpacity('--color-on-primary'),
        },
        secondary: withOpacity('--color-secondary'),
        accent: {
          DEFAULT: withOpacity('--color-accent'),
          hover: withOpacity('--color-accent-hover'),
          foreground: withOpacity('--color-on-accent'),
        },
        background: withOpacity('--color-background'),
        surface: withOpacity('--color-surface'),
        foreground: withOpacity('--color-foreground'),
        muted: {
          DEFAULT: withOpacity('--color-muted'),
          foreground: withOpacity('--color-muted-foreground'),
        },
        border: {
          DEFAULT: withOpacity('--color-border'),
          strong: withOpacity('--color-border-strong'),
        },
        destructive: {
          DEFAULT: withOpacity('--color-destructive'),
          hover: withOpacity('--color-destructive-hover'),
        },
        success: withOpacity('--color-success'),
        ring: withOpacity('--color-ring'),
      },
      fontFamily: {
        sans: ['"Fira Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"Fira Code"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        DEFAULT: 'var(--radius-md)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        elevated: 'var(--shadow-elevated)',
      },
    },
  },
}
