import logging
import asyncio
import aiohttp
import pdb
import sys
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import ssl
import certifi

# 디버그 모드 설정
DEBUG_MODE = True

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def debug_trace():
    """간소화된 디버그 트레이스"""
    if DEBUG_MODE:
        logger.error("=== 디버그 정보 ===")
        sys.exit(1)  # 프로그램 즉시 종료

class HanwhaLifeScraper:
    def __init__(self):
        logger.info("=== Initializing HanwhaLifeScraper ===")
        
        # URL 설정
        self.base_url = "https://www.hanwhalife.com"
        self.list_url = f"{self.base_url}/main/disclosure/goods/goodslist/getList2.do"
        self.detail_url = f"{self.base_url}/main/disclosure/goods/goodslist/getList3.do"
        
        # WebDriver 설정
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.page_load_strategy = 'eager'
        
        try:
            self.driver = webdriver.Chrome(
                service=ChromeService(ChromeDriverManager().install()),
                options=chrome_options
            )
            self.driver.implicitly_wait(10)
            logger.info("브라우저 초기화 완료")
            
        except Exception as e:
            logger.error(f"브라우저 초기화 실패: {e}")
            raise

    async def initialize(self):
        try:
            url = f"{self.base_url}/main/disclosure/goods/goodslist/DF_GDGL000_P10000.do"
            logger.info(f"페이지 접속: {url}")
            
            self.driver.get(url)
            await asyncio.sleep(2)
            
            logger.info("=== 페이지 접속 완료 ===")
            logger.info(f"Current URL: {self.driver.current_url}")
            
            initial_data = await self.get_initial_data()
            if initial_data:
                logger.info("초기 데이터 로드 완료")
                return initial_data
            return None
            
        except Exception as e:
            logger.error(f"초기화 실패: {str(e)}")
            debug_trace()
            return None

    async def get_product_list(self, sell_type, goods_type):
        try:
            logger.info(f"상품 목록 요청: {sell_type}-{goods_type}")
            
            script = f"""
            var done = arguments[0];
            fetch('/main/disclosure/goods/goodslist/getList2.do', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                }},
                body: new URLSearchParams({{
                    'goodsType': '{goods_type}',
                    'sellType': '{sell_type}',
                    'goodsIndex': '',
                    'PType': '1',
                    'sellFlag': 'Y'
                }})
            }})
            .then(response => response.json())
            .then(data => done(data))
            .catch(error => done({ error: error.message }));
            """
            
            response = await self.driver.execute_async_script(script)
            
            if response and 'list2' in response:
                logger.info(f"상품 {len(response['list2'])}개 수신")
                return response['list2']
            return None
            
        except Exception as e:
            logger.error(f"상품 목록 요청 실패: {str(e).split('Stacktrace')[0]}")
            if DEBUG_MODE:
                debug_trace()
            return None

    async def get_product_detail(self, idx, sell_type, goods_type):
        try:
            if DEBUG_MODE:
                logger.info(f"=== Getting product detail for idx: {idx} ===")
            
            script = f"""
            return await fetch('/main/disclosure/goods/goodslist/getList3.do', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                }},
                body: new URLSearchParams({{
                    'goodsIndex': '{idx}',
                    'sellType': '{sell_type}',
                    'goodsType': '{goods_type}',
                    'PType': '1',
                    'sellFlag': 'Y'
                }})
            }}).then(response => response.json());
            """
            
            response = await self.driver.execute_async_script(script)
            
            if response and 'list3' in response:
                return response['list3']
            return None
            
        except Exception as e:
            logger.error(f"상품 상세 정보 요청 실패: {str(e)}")
            if DEBUG_MODE:
                logger.error(f"Exception details: {traceback.format_exc()}")
                debug_trace()
            return None

    def cleanup(self):
        try:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
                logger.info("브라우저 종료")
        except Exception as e:
            logger.error(f"브라우저 종료 실패: {e}")

    def __del__(self):
        self.cleanup()

    async def get_initial_data(self):
        try:
            logger.info("데이터 요청 시작")
            
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "List1"))
            )
            
            script = """
            return new Promise((resolve) => {
                fetch('/main/disclosure/goods/goodslist/getList.do', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: new URLSearchParams({
                        'PType': '1',
                        'sellFlag': 'Y'
                    })
                })
                .then(response => response.json())
                .then(data => resolve(data))
                .catch(error => resolve({ error: error.message }));
            });
            """
            
            response = await self.driver.execute_async_script(script)
            
            if response and not isinstance(response, dict):
                logger.info("데이터 수신 성공")
                return response
            else:
                logger.error(f"데이터 수신 실패: {response if isinstance(response, dict) else '알 수 없는 오류'}")
                debug_trace()
                return None
            
        except Exception as e:
            logger.error(f"요청 실패: {str(e).split('Stacktrace')[0]}")
            debug_trace()
            return None

    async def process_category(self, sell_type, goods_type, category_name):
        """카테고리별 처리를 수행하는 메서드"""
        try:
            if DEBUG_MODE:
                logger.info(f"\n=== Processing category: {category_name} ===")
                logger.info(f"sell_type: {sell_type}, goods_type: {goods_type}")
            
            products = await self.get_product_list(sell_type, goods_type)
            
            if not products:
                logger.error("상품 목록을 가져오지 못했습니다")
                if DEBUG_MODE:
                    debug_trace()
                return
                
            logger.info(f"받은 상품 수: {len(products)}")
            if products:
                logger.info(f"첫 번째 상품 샘플: {products[0]}")
            
            for product in products[:3]:  # 테스트를 위해 3개만 처리
                product_name = product['GOODS_NAME']
                idx = product['IDX']
                
                logger.info(f"\n--- 상품 처리 시작 ---")
                logger.info(f"상품명: {product_name}")
                
                pdf_info = await self.get_product_detail(
                    idx=idx,
                    sell_type=sell_type,
                    goods_type=goods_type
                )
                
                if pdf_info:
                    if DEBUG_MODE:
                        logger.info(f"PDF 정보: {pdf_info}")
                    # PDF 정보 저장 로직 구현 필요
                    pass
                    
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"카테고리 처리 중 오류 발생: {str(e)}")
            if DEBUG_MODE:
                debug_trace()

async def main():
    scraper = None
    try:
        logger.info("=== 프로그램 시작 ===")
        scraper = HanwhaLifeScraper()
        initial_data = await scraper.initialize()
        
        if not initial_data:
            logger.error("초기화 실패")
            return
            
        if initial_data and 'list1' in initial_data:
            categories = [
                ('SA', 'GA', '개인 보장성'),
                ('SA', 'GB', '개인 연금')
            ]
            
            for sell_type, goods_type, category_name in categories:
                if DEBUG_MODE:
                    logger.info(f"\n=== Processing category: {category_name} ===")
                await scraper.process_category(sell_type, goods_type, category_name)
                await asyncio.sleep(3)
                
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}")
        debug_trace()
    finally:
        if scraper:
            scraper.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n=== 프로그램 중단됨 ===")
        sys.exit(0)
    except Exception as e:
        logger.error(f"예상치 못한 오류: {e}")
        debug_trace()