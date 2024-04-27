import asyncio
from playwright.async_api import async_playwright
import json


main_url = 'https://realtylink.org/en/properties~for-rent?view=Thumbnail'
ADVERTS = []


class Advertisement:
    def __init__(self):
        self.title = ''
        self.url = ''
        self.region = ''
        self.address = ''
        self.price = ''
        self.description = ''
        self.date = ''
        self.room = 0
        self.area = 0
        self.images = []

    @property
    def price(self):
        return self._price

    @price.setter
    def price(self, value):
        if value:
            self._price = int(value.split()[0].replace(',', '').strip(' $'))
        else:
            self._price = 0

    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, value):
        self._address = value.strip() if isinstance(value, str) else ''

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value.strip()


async def main():
    async with async_playwright() as p:
        browser = await p.webkit.launch(args=['--incognito'], headless=True)    # Change "headless=False" if you want to see web-driver.
        page = await browser.new_page()
        await page.goto(main_url)
        print('Starting scraper...')
        await process_advlist(browser, page)
        await browser.close()

        await append_json(ADVERTS)


async def process_advlist(browser, page):
    """
    Goes through pages, takes advertisements.
    """
    adverts = await page.query_selector_all('#divMainResult .shell')
    for advert in adverts:
        if len(ADVERTS) == 3:
            return

        url = await advert.query_selector('a')
        url = 'https://realtylink.org' + await url.get_attribute('href')

        region = await advert.query_selector('.address > div:nth-child(2)')
        region = await region.text_content()

        room = await advert.query_selector('div.cac')
        if room:
            room = await room.text_content()

        area = await advert.query_selector('span.sqft > span')
        area = await area.text_content()

        adv_page = await browser.new_page()
        await adv_page.goto(url)
        await adv_page.wait_for_load_state('domcontentloaded')
        await process_advert(adv_page, dict(url=url, region=region, room=room, area=area))
        await adv_page.close()

    next_button = await page.query_selector('li.next > a')
    if next_button:
        await next_button.click()
        await page.wait_for_load_state('domcontentloaded')
        await process_advlist(browser, page)


async def process_advert(page, context: dict):
    """
    Takes information about an advertisement, adds it to class Advertisement.
    """
    advertisement = Advertisement()
    advertisement.url = context['url']
    advertisement.region = context['region']
    advertisement.room = context.get('room', 0)
    advertisement.area = int(context['area'].split()[0].replace(',', ''))

    title = await page.query_selector('span[data-id="PageTitle"]')
    advertisement.title = await title.text_content()

    price = await page.query_selector('div.price > span.text-nowrap:not([id])')
    advertisement.price = await price.inner_text()

    address = await page.query_selector('h2[itemprop="address"]')
    advertisement.address = await address.text_content()

    description = await page.query_selector('div[itemprop="description"]')
    if description:
        advertisement.description = await description.text_content()

    images = []
    imgs = await page.query_selector('//script[contains(., "PhotoUrls")]')
    imgs = await imgs.text_content()
    imgs = imgs.split('[')[-1].split(']')[0].split(',')
    for img in imgs:
        image = img.split('id=')[-1].split('&')[0]
        image = f'https://mediaserver.realtylink.org/media.ashx?id={image}&t=pi&sm=m&w=1260&h=1024'
        images.append(image)

    advertisement.images = images

    advert_dict = {key.lstrip('_'): value for key, value in advertisement.__dict__.items()}
    print(advert_dict)
    ADVERTS.append(advert_dict)


async def append_json(adverts: list):
    """
    Adds parsed averrtisements to JSON. Maximum 60 objects.
    """
    with open('data.json', 'w') as file:
        json.dump(adverts, file, indent=4)

    print('File "data.json" has been created. Exiting...')


if __name__ == "__main__":
    asyncio.run(main())
