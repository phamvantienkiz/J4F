import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright


async def main():
    root = Path(__file__).resolve().parent
    html_path = root / "system_topology.html"
    output_dir = root / "img"
    output_dir.mkdir(exist_ok=True)

    outputs = [
        output_dir / "system_architecture_topology.png",
        output_dir / "ai_agent_detailed_pipeline.png",
        output_dir / "agent_tool_interaction_loop.png",
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1800, "height": 1400}, device_scale_factor=2)
        await page.goto(f"file:///{str(html_path).replace(os.sep, '/')}")
        await page.wait_for_function("document.querySelectorAll('.diagram-frame svg').length === 3", timeout=30000)

        frames = page.locator("section.diagram-frame")
        count = await frames.count()
        if count != 3:
            raise RuntimeError(f"Expected 3 diagram frames, found {count}")

        for index, output in enumerate(outputs):
            await frames.nth(index).screenshot(path=str(output))
            print(f"Saved {output}", flush=True)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
