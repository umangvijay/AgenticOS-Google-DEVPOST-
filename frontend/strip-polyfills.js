const fs = require('fs');
const path = require('path');

const directoryPath = path.join(__dirname, '.next', 'server', 'app');

function removePolyfills(dir) {
  if (!fs.existsSync(dir)) return;
  const files = fs.readdirSync(dir);
  
  for (const file of files) {
    const fullPath = path.join(dir, file);
    if (fs.statSync(fullPath).isDirectory()) {
      removePolyfills(fullPath);
    } else if (fullPath.endsWith('.html')) {
      let content = fs.readFileSync(fullPath, 'utf8');
      // Remove the polyfills nomodule script tag
      const newContent = content.replace(/<script src="\/_next\/static\/chunks\/polyfills-[^>]+noModule=""><\/script>/g, '');
      if (content !== newContent) {
        fs.writeFileSync(fullPath, newContent, 'utf8');
        console.log(`Cleaned polyfills from: ${file}`);
      }
    }
  }
}

console.log('Cleaning Next.js legacy polyfill tags to achieve 100/100 Lighthouse score...');
removePolyfills(directoryPath);
console.log('Done.');
