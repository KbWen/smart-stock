import { fileURLToPath } from 'node:url'
import { readdir, readFile, stat, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { brotliCompressSync, gzipSync } from 'node:zlib'

const DIST_DIR = new URL('../dist', import.meta.url)

async function walk(dir) {
  const entries = await readdir(dir)
  const files = []
  for (const entry of entries) {
    const fullPath = join(dir, entry)
    const info = await stat(fullPath)
    if (info.isDirectory()) {
      files.push(...(await walk(fullPath)))
    } else if (/\.(js|css|html|svg)$/.test(entry)) {
      files.push(fullPath)
    }
  }
  return files
}

async function main() {
  const basePath = fileURLToPath(DIST_DIR)
  const targets = await walk(basePath)

  await Promise.all(targets.map(async (target) => {
    const raw = await readFile(target)
    await writeFile(`${target}.gz`, gzipSync(raw, { level: 9 }))
    await writeFile(`${target}.br`, brotliCompressSync(raw))
  }))

  console.log(`Compressed ${targets.length} assets with gzip and brotli.`)
}

await main()
