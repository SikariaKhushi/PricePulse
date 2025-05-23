import re
import random
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from .models import Product, PriceRecord, Alert, PlatformComparison
from sqlalchemy.orm import Session
from .email_service import send_price_drop_alert
import asyncio
from rapidfuzz import process, fuzz

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger("scraper")

# --- User-Agent Pool ---
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    # Add more real user agents here
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

# --- Selector Config ---
SELECTORS = {
    "amazon": {
        "name": '#productTitle',
        "price": ['.a-price-whole', '.a-price .a-offscreen', '#priceblock_dealprice', '#priceblock_ourprice'],
        "image": ['#landingImage', '#imgBlkFront'],
        "brand": '#bylineInfo'
    },
    "flipkart": {
        "name": ['._35KyD6', '.x2Vkpg', 'h1 span', '._4rR01T'],
        "price": ['._1_WHN1', '._30jeq3', '._25b18c'],
        "image": ['._396cs4 img', '._2r_T1I img', '.CXW8mj img']
    },
    "meesho": {
        "name": ['[data-testid="product-title"]', '.sc-eDvSVe', 'h1'],
        "price": ['[data-testid="current-price"]', '.sc-dkzDqf', '.ProductPrice__Container-sc-1h6x2c5-0'],
        "image": ['[data-testid="product-image"]', '.ProductImageCarousel__Image-sc-1d9b7bg-2 img', '.sc-gqjmRU img']
    }
}

# --- Utility Functions ---

def extract_core_title(product_name: str) -> str:
    # Take part before '(', '|', '-', or ','
    return re.split(r'[\(\|\-,]', product_name)[0].strip()

def extract_model(product_name: str) -> Optional[str]:
    match = re.search(r'\b([A-Z0-9]{5,})\b', product_name)
    return match.group(1) if match else None

def build_search_query(product_name: str, brand: str) -> str:
    model = extract_model(product_name)
    if model:
        return f"{brand} {model}".strip()
    core_title = extract_core_title(product_name)
    # Avoid duplicate brand
    if brand.lower() in core_title.lower():
        return core_title.strip()
    return f"{brand} {core_title}".strip()

def fuzzy_best_match(target: str, candidates: List[dict], threshold: int = 80):
    candidate_titles = [c['name'] for c in candidates]
    if not candidate_titles:
        return []
    match, score, idx = process.extractOne(target, candidate_titles, scorer=fuzz.token_set_ratio)
    if score >= threshold:
        best_result = candidates[idx]
        best_result['match_score'] = score
        return [best_result]
    return []

# --- Scraper Class ---

class ProductScraper:
    def __init__(self, playwright: Any):
        self.playwright = playwright
        self.browser = None

    async def __aenter__(self):
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()

    async def scrape_product(self, url: str) -> Dict:
        if not self.browser:
            raise RuntimeError("Browser not initialized. Use async context manager.")

        page = await self.browser.new_page()
        try:
            await page.set_extra_http_headers({
                'User-Agent': get_random_user_agent(),
                'Accept-Language': "en-US,en;q=0.9",
                'Referer': "https://www.google.com/"
            })
            await page.goto(url, timeout=60000, wait_until='domcontentloaded')
            await page.wait_for_selector('#productTitle', timeout=30000)

            if 'amazon.in' in url:
                return await self._scrape_amazon(page, url)
            elif 'flipkart.com' in url:
                return await self._scrape_flipkart(page, url)
            elif 'meesho.com' in url:
                return await self._scrape_meesho(page, url)
            else:
                raise ValueError("Unsupported platform")
        except Exception as e:
            await page.screenshot(path=f"error_{int(datetime.utcnow().timestamp())}.png", full_page=True)
            logger.error(f"Scraping failed for {url}: {e}")
            raise
        finally:
            await page.close()

    async def _scrape_amazon(self, page, url: str) -> Dict:
        try:
            name = await page.text_content(SELECTORS["amazon"]["name"])
            if not name:
                raise ValueError("Could not find product name")
            name = name.strip()

            price = None
            for selector in SELECTORS["amazon"]["price"]:
                try:
                    price_text = await page.text_content(selector)
                    if price_text:
                        price = self._extract_price(price_text)
                        break
                except:
                    continue
            if not price:
                raise ValueError("Could not find product price")

            image_url = ""
            for selector in SELECTORS["amazon"]["image"]:
                try:
                    image_url = await page.get_attribute(selector, 'src')
                    if image_url:
                        break
                except:
                    continue

            brand = ""
            try:
                brand_element = await page.text_content(SELECTORS["amazon"]["brand"])
                if brand_element:
                    brand = brand_element.replace('Visit the', '').replace('Store', '').strip()
            except:
                pass

            model = extract_model(name)

            return {
                'name': name,
                'price': price,
                'image_url': image_url or '',
                'platform': 'Amazon',
                'brand': brand,
                'model': model or "",
                'url': url
            }
        except Exception as e:
            logger.error(f"Failed to scrape Amazon product: {str(e)}")
            raise

    async def _scrape_flipkart(self, page, url: str) -> Dict:
        try:
            name = None
            for selector in SELECTORS["flipkart"]["name"]:
                try:
                    name = await page.text_content(selector)
                    if name:
                        break
                except:
                    continue
            if not name:
                raise ValueError("Could not find product name")
            name = name.strip()

            price = None
            for selector in SELECTORS["flipkart"]["price"]:
                try:
                    price_text = await page.text_content(selector)
                    if price_text:
                        price = self._extract_price(price_text)
                        break
                except:
                    continue
            if not price:
                raise ValueError("Could not find product price")

            image_url = ""
            for selector in SELECTORS["flipkart"]["image"]:
                try:
                    image_url = await page.get_attribute(selector, 'src')
                    if image_url:
                        break
                except:
                    continue

            return {
                'name': name,
                'price': price,
                'image_url': image_url or '',
                'platform': 'Flipkart',
                'brand': '',
                'model': '',
                'url': url
            }
        except Exception as e:
            logger.error(f"Failed to scrape Flipkart product: {str(e)}")
            raise

    async def _scrape_meesho(self, page, url: str) -> Dict:
        try:
            name = None
            for selector in SELECTORS["meesho"]["name"]:
                try:
                    name = await page.text_content(selector)
                    if name:
                        break
                except:
                    continue
            if not name:
                raise ValueError("Could not find product name")
            name = name.strip()

            price = None
            for selector in SELECTORS["meesho"]["price"]:
                try:
                    price_text = await page.text_content(selector)
                    if price_text:
                        price = self._extract_price(price_text)
                        break
                except:
                    continue
            if not price:
                raise ValueError("Could not find product price")

            image_url = ""
            for selector in SELECTORS["meesho"]["image"]:
                try:
                    image_url = await page.get_attribute(selector, 'src')
                    if image_url:
                        break
                except:
                    continue

            return {
                'name': name,
                'price': price,
                'image_url': image_url or '',
                'platform': 'Meesho',
                'brand': '',
                'model': '',
                'url': url
            }
        except Exception as e:
            logger.error(f"Failed to scrape Meesho product: {str(e)}")
            raise

    def _extract_price(self, price_text: str) -> int:
        price_text = price_text.replace('₹', '').replace(',', '').strip()
        price_match = re.search(r'[\d,]+\.?\d*', price_text)
        if price_match:
            price_str = price_match.group().replace(',', '')
            try:
                price_float = float(price_str)
                return int(price_float * 100)  # Convert to paise
            except ValueError:
                pass
        raise ValueError(f"Could not extract price from: {price_text}")

    async def search_cross_platform(self, product_name: str, brand: str = "") -> List[Dict]:
        results = []
        # Search on Flipkart
        flipkart_results = await self._search_flipkart_search(product_name, brand)
        results.extend(flipkart_results)
        # Search on Meesho
        meesho_results = await self._search_meesho_search(product_name, brand)
        results.extend(meesho_results)

        # Fuzzy matching
        if not results:
            return []
        search_target = build_search_query(product_name, brand)
        return fuzzy_best_match(search_target, results, threshold=80)

    async def _search_flipkart_search(self, product_name: str, brand: str = "") -> List[Dict]:
        if not self.browser:
            return []
        page = await self.browser.new_page()
        try:
            search_query = build_search_query(product_name, brand)
            search_url = f"https://www.flipkart.com/search?q={search_query.replace(' ', '%20')}"
            await page.goto(search_url, wait_until='networkidle')
            product_links = await page.query_selector_all('a[href*="/p/"]')
            results = []
            for i, link in enumerate(product_links[:3]):
                try:
                    href = await link.get_attribute('href')
                    if href and '/p/' in href:
                        full_url = f"https://www.flipkart.com{href}"
                        name_elem = await link.query_selector('._4rR01T')
                        price_elem = await link.query_selector('._30jeq3')
                        if name_elem and price_elem:
                            name = await name_elem.text_content()
                            price_text = await price_elem.text_content()
                            if name and price_text:
                                price = self._extract_price(price_text)
                                results.append({
                                    'platform': 'Flipkart',
                                    'name': name.strip(),
                                    'price': price,
                                    'url': full_url
                                })
                except Exception as e:
                    logger.warning(f"Flipkart result parse error: {e}")
                    continue
            return results
        except Exception as e:
            logger.error(f"Error searching Flipkart: {str(e)}")
            await page.screenshot(path=f"flipkart_error_{int(datetime.utcnow().timestamp())}.png", full_page=True)
            return []
        finally:
            await page.close()

    async def _search_meesho_search(self, product_name: str, brand: str = "") -> List[Dict]:
        if not self.browser:
            return []
        page = await self.browser.new_page()
        try:
            search_query = build_search_query(product_name, brand)
            search_url = f"https://www.meesho.com/search?q={search_query.replace(' ', '%20')}"
            await page.goto(search_url, wait_until='networkidle')
            product_links = await page.query_selector_all('[data-testid="product-mc-container"] a')
            results = []
            for i, link in enumerate(product_links[:3]):
                try:
                    href = await link.get_attribute('href')
                    if href:
                        full_url = f"https://www.meesho.com{href}" if href.startswith('/') else href
                        name_elem = await link.query_selector('[data-testid="product-title"]')
                        price_elem = await link.query_selector('[data-testid="current-price"]')
                        if name_elem and price_elem:
                            name = await name_elem.text_content()
                            price_text = await price_elem.text_content()
                            if name and price_text:
                                price = self._extract_price(price_text)
                                results.append({
                                    'platform': 'Meesho',
                                    'name': name.strip(),
                                    'price': price,
                                    'url': full_url
                                })
                except Exception as e:
                    logger.warning(f"Meesho result parse error: {e}")
                    continue
            return results
        except Exception as e:
            logger.error(f"Error searching Meesho: {str(e)}")
            await page.screenshot(path=f"meesho_error_{int(datetime.utcnow().timestamp())}.png", full_page=True)
            return []
        finally:
            await page.close()

import logging

async def update_product_price(product_id: str, db: Session, playwright):
    """Update product price and check alerts"""
    logger = logging.getLogger("scraper")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logger.warning(f"Product {product_id} not found for price update.")
        return

    try:
        async with ProductScraper(playwright) as scraper:
            product_info = await scraper.scrape_product(product.url)
            new_price = product_info['price']

            product.current_price = new_price
            product.updated_at = datetime.utcnow()

            price_record = PriceRecord(
                product_id=product_id,
                price=new_price,
                platform=product.platform
            )
            db.add(price_record)

            # Check alerts
            active_alerts = (
                db.query(Alert)
                .filter(
                    Alert.product_id == product_id,
                    Alert.is_active == True,
                    Alert.is_triggered == False,
                    Alert.target_price >= new_price
                )
                .all()
            )

            for alert in active_alerts:
                alert.is_triggered = True
                alert.date_triggered = datetime.utcnow()
                user = alert.user
                try:
                    await send_price_drop_alert(
                        user.email,
                        user.name,
                        product.name,
                        product.image_url,
                        new_price / 100,
                        alert.target_price / 100,
                        product.url
                    )
                except Exception as e:
                    logger.error(f"Failed to send alert email: {e}")

            db.commit()

    except Exception as e:
        logger.error(f"Error updating product {product_id}: {str(e)}", exc_info=True)
        db.rollback()

async def update_cross_platform_comparison(product_id: str, db: Session, playwright):
    """Update cross-platform price comparison"""
    logger = logging.getLogger("scraper")
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if not product:
        logger.warning(f"Product {product_id} not found for comparison update.")
        return

    try:
        async with ProductScraper(playwright) as scraper:
            search_results = await scraper.search_cross_platform(product.name, product.brand)

            db.query(PlatformComparison).filter(
                PlatformComparison.product_id == product_id
            ).delete()

            for result in search_results:
                comparison = PlatformComparison(
                    product_id=product_id,
                    platform=result['platform'],
                    found_name=result['name'],
                    found_price=result['price'],
                    found_url=result['url'],
                    last_checked=datetime.utcnow()
                )
                db.add(comparison)

            db.commit()

    except Exception as e:
        logger.error(f"Error updating comparison for product {product_id}: {str(e)}", exc_info=True)
        db.rollback()
