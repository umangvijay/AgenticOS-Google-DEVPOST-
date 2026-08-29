const fs = require('fs');
const html = fs.readFileSync('.next/analyze/client.html', 'utf8');
const match = html.match(/window\.chartData = (\[.*?\]);/);
const data = JSON.parse(match[1]);
const chunk = data.find(c => c.label.includes('3794'));
if (chunk && chunk.groups && chunk.groups[0] && chunk.groups[0].groups) {
  chunk.groups[0].groups.forEach(g => {
    console.log(`${g.label}: ${g.parsedSize} bytes`);
  });
}
const chunk2 = data.find(c => c.label.includes('4bd1'));
if (chunk2 && chunk2.groups && chunk2.groups[0] && chunk2.groups[0].groups) {
  chunk2.groups[0].groups.forEach(g => {
    console.log(`${g.label}: ${g.parsedSize} bytes`);
  });
}
