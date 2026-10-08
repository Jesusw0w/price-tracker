// S3 and CloudFront can't list a folder, so the UI reads this generated index instead
import { readdirSync, writeFileSync } from 'node:fs';

const dir = 'public/backgrounds';
const images = readdirSync(dir)
  .filter((name) => /\.(avif|webp|jpe?g|png)$/i.test(name))
  .sort();
writeFileSync(`${dir}/index.json`, JSON.stringify(images));
console.log(`backgrounds: ${images.length} image(s)`);
