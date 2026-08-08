export function useScrollReveal(): { containerRef: Ref<HTMLElement | undefined> } {
  const containerRef = ref<HTMLElement>()

  onMounted(() => {
    const container = containerRef.value
    if (!container) {
      return
    }

    const revealTargets = container.classList.contains('landing-reveal')
      ? [container]
      : Array.from(container.querySelectorAll<HTMLElement>('.landing-reveal'))

    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible')
          observer.unobserve(entry.target)
        }
      }
    }, { threshold: 0.15, rootMargin: '0px 0px -80px 0px' })

    revealTargets.forEach((target) => observer.observe(target))

    onUnmounted(() => observer.disconnect())
  })

  return { containerRef }
}
