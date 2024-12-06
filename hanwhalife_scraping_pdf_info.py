import asyncio
import logging
from datetime import datetime
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('hanwhalife_scraping.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class HanwhaLifeScraper:
    def __init__(self):
        self.base_url = 'https://www.hanwhalife.com'
        self.list_url = f'{self.base_url}/main/disclosure/goods/goodslist/DF_GDGL000_P10000.do'
        self.setup_driver()
        
    def setup_driver(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)

    def get_pdf_download_url(self, file_name):
        """PDF 다운로드 URL 생성"""
        if not file_name:
            return 'X'
        base_url = "https://www.hanwhalife.com/main/disclosure/goods/download_chk.asp"
        return f"{base_url}?file_name={file_name}"

    async def get_initial_data(self):
        """초기 데이터 가져오기"""
        try:
            js_code = """
                var done = arguments[arguments.length - 1];
                
                fetch('/main/disclosure/goods/goodslist/getList.do', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Requested-With': 'XMLHttpRequest',
                        'Accept': 'application/json, text/javascript, */*; q=0.01'
                    },
                    body: new URLSearchParams({
                        'PType': '1',
                        'sellFlag': 'Y',
                        'schText': ''
                    })
                })
                .then(response => response.json())
                .then(data => done(data))
                .catch(error => done({error: error.message}));
            """
            
            logger.info("초기 데이터 요청 시작")
            result = await asyncio.to_thread(
                self.driver.execute_async_script,
                js_code
            )
            logger.info(f"초기 데이터 응답: {result}")
            return result
            
        except Exception as e:
            logger.error(f"초기 데이터 로드 중 오류: {str(e)}")
            return None

    async def get_product_details(self, sell_type, goods_type):
        """상품 목록 조회"""
        js_code = """
            var done = arguments[arguments.length - 1];
            
            fetch('/main/disclosure/goods/goodslist/getList.do', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: new URLSearchParams({
                    'PType': '1',
                    'sellFlag': 'Y',
                    'sellType': arguments[0],
                    'goodsType': arguments[1]
                })
            })
            .then(response => response.json())
            .then(data => done(data))
            .catch(error => done({error: error.message}));
        """
        
        return await asyncio.to_thread(
            self.driver.execute_async_script,
            js_code, sell_type, goods_type
        )

    def get_product_specific_info(self, idx, sell_type, goods_type):
        """상품 상세 정보 조회"""
        try:
            js_code = """
                var done = arguments[arguments.length - 1];
                
                fetch('/main/disclosure/goods/goodslist/getGoodsInfo.do', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'X-Requested-With': 'XMLHttpRequest'
                    },
                    body: new URLSearchParams({
                        'PType': '1',
                        'sellFlag': 'Y',
                        'sellType': arguments[1],
                        'goodsType': arguments[2],
                        'goodsIndex': arguments[0]
                    })
                })
                .then(response => response.json())
                .then(data => done(data))
                .catch(error => done({error: error.message}));
            """
            
            return self.driver.execute_async_script(js_code, idx, sell_type, goods_type)
            
        except Exception as e:
            logger.error(f"상품 상세 정보 조회 중 오류: {str(e)}")
            return None

    async def scrape(self):
        try:
            self.driver.get(self.list_url)
            logger.info("페이지 접속 완료")
            
            # JavaScript 로딩 대기
            self.wait.until(EC.presence_of_element_located((By.ID, "LIST_GRID1")))
            await asyncio.sleep(3)
            
            # 초기 데이터 요청
            data = await self.get_initial_data()
            
            if isinstance(data, dict) and 'list1' in data:
                excel_data = []
                
                for product_type in data['list1']:
                    sell_type = product_type['SELL_TYPE']
                    goods_type = product_type['GOODS_TYPE']
                    category = f"{product_type['SELL_TYPE_NM']} {product_type['GOODS_TYPE_NM']}"
                    logger.info(f"처리 중: {category}")
                    
                    details = await self.get_product_details(sell_type, goods_type)
                    
                    if details and 'list2' in details:
                        logger.info(f"발견된 상품 수: {len(details['list2'])}")
                        
                        for product in details['list2']:
                            logger.info(f"상품 처리 중: {product['GOODS_NAME']}")
                            
                            specific_info = self.get_product_specific_info(
                                product['IDX'],
                                sell_type,
                                goods_type
                            )
                            
                            if specific_info and 'list3' in specific_info:
                                for doc in specific_info['list3']:
                                    row = {
                                        '판매구분': '판매중' if not doc.get('SELL_END_DT', '').strip() else '판매중지',
                                        '판매사': '한화생명',
                                        '분류': category,
                                        '상품명': product['GOODS_NAME'],
                                        '판매기간': f"{doc.get('SELL_START_DT', '')} ~ {'현재' if not doc.get('SELL_END_DT', '').strip() else doc['SELL_END_DT']}",
                                        '요약서': self.get_pdf_download_url(doc.get('FILE_NAME1')),
                                        '방법서': self.get_pdf_download_url(doc.get('FILE_NAME2')),
                                        '약관': self.get_pdf_download_url(doc.get('FILE_NAME3'))
                                    }
                                    excel_data.append(row)
                            
                            await asyncio.sleep(1)
                    await asyncio.sleep(2)
                
                if excel_data:
                    self.save_to_excel(excel_data)
                else:
                    logger.warning("수집된 데이터가 없습니다.")
            
        except Exception as e:
            logger.error(f"스크래핑 중 오류 발생: {str(e)}")
            logger.error(f"페이지 소스: {self.driver.page_source[:500]}")
            
        finally:
            self.driver.quit()

async def main():
    scraper = HanwhaLifeScraper()
    await scraper.scrape()

if __name__ == "__main__":
    asyncio.run(main())