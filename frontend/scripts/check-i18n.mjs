import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const currentDirectory = dirname(fileURLToPath(import.meta.url))
const localesDirectory = join(currentDirectory, '..', 'locales')

function collectKeyPaths(value, prefix = '') {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return [prefix]
  }
  return Object.entries(value).flatMap(([key, nestedValue]) =>
    collectKeyPaths(nestedValue, prefix ? `${prefix}.${key}` : key)
  )
}

const localeFiles = ['uk.json', 'ru.json']
const keyPathsByLocale = localeFiles.map((fileName) => ({
  fileName,
  keyPaths: new Set(collectKeyPaths(JSON.parse(readFileSync(join(localesDirectory, fileName), 'utf-8')))),
}))

const [first, second] = keyPathsByLocale
const onlyInFirst = [...first.keyPaths].filter((keyPath) => !second.keyPaths.has(keyPath))
const onlyInSecond = [...second.keyPaths].filter((keyPath) => !first.keyPaths.has(keyPath))

if (onlyInFirst.length === 0 && onlyInSecond.length === 0) {
  console.log(`OK: ${first.fileName} and ${second.fileName} have matching key sets (${first.keyPaths.size} keys)`)
  process.exit(0)
}

if (onlyInFirst.length > 0) {
  console.error(`Keys only in ${first.fileName}:`)
  onlyInFirst.forEach((keyPath) => console.error(`  - ${keyPath}`))
}
if (onlyInSecond.length > 0) {
  console.error(`Keys only in ${second.fileName}:`)
  onlyInSecond.forEach((keyPath) => console.error(`  - ${keyPath}`))
}
process.exit(1)
