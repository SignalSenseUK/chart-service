import asyncio
from playwright.async_api import async_playwright

async def main():
    with open('test.html', 'w') as f:
        f.write("""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { margin: 0; padding: 0; background: #0e1117; width: 100vw; height: 100vh; display: flex;}
                #container { flex: 1; width: 100%; position: relative; }
            </style>
            <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
        </head>
        <body>
            <div id="container"></div>
            <script>
                const container = document.getElementById('container');
                const chart = LightweightCharts.createChart(container, {
                    width: container.clientWidth,
                    height: container.clientHeight,
                    autoSize: true,
                    timeScale: {
                        fixLeftEdge: true,
                        fixRightEdge: true,
                    }
                });
                const series = chart.addLineSeries();
                series.setData([
                    { time: '2019-04-11', value: 80.01 },
                    { time: '2019-04-12', value: 96.63 },
                    { time: '2019-04-13', value: 76.64 },
                    { time: '2019-04-14', value: 81.89 },
                    { time: '2019-04-15', value: 74.43 },
                ]);
                chart.timeScale().fitContent();
                
                // create a div to indicate ready
                const ready = document.createElement('div');
                ready.id = 'ready';
                document.body.appendChild(ready);
            </script>
        </body>
        </html>
        """)
        
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page(viewport={'width': 800, 'height': 600})
        await page.goto(f'file://{__import__("os").path.abspath("test.html")}')
        await page.wait_for_selector('#ready')
        await page.screenshot(path='test.png')
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
