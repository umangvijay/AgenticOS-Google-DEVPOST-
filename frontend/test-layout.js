const puppeteer = require('puppeteer');
(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width: 390, height: 844 });
  await page.goto('http://localhost:3000');
  await page.waitForTimeout(5000); // wait for splash
  
  const layoutInfo = await page.evaluate(() => {
    const elToBox = (el) => {
      if(!el) return null;
      const rect = el.getBoundingClientRect();
      return { tag: el.tagName, id: el.id, className: el.className, top: rect.top, height: rect.height, bottom: rect.bottom, text: el.innerText.substring(0,20) };
    };
    return {
      body: elToBox(document.body),
      header: elToBox(document.querySelector('header')),
      main: elToBox(document.querySelector('main')),
      h1: elToBox(document.querySelector('h1')),
      diagramWrapper: elToBox(document.querySelector('.diagram-zoom-wrapper')),
      firstDivInMain: elToBox(document.querySelector('main > div'))
    };
  });
  console.log(JSON.stringify(layoutInfo, null, 2));
  await browser.close();
})();
