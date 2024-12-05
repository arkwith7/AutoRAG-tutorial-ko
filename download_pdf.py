"""
Download pdf files from excel file
1. 입력으로 엑셀파일과 URL 컬럼을 받아서 pdf 파일을 다운로드 함, 또한 pdf도 지정한 폴더에 저장함
2. 엑셀파일은 반드시 첫번째 시트에 있어야 함
3. URL 컬럼에서 'X'나 공백은 제외하고 http로 시작하는 내용만 이용함
4. 엑셀 예시 파일 내용 및 URL 컬럼사례로 "요약서", "방법서", "약관"
판매구분	판매사	분류	상품명	판매기간	요약서	방법서	약관
판매중	신한라이프	TM>보장	(간편)신한통합건강보장보험 원(ONE)(무배당, 해약환급금 미지급형)	2024.10.22 ~ 현재	https://www.shinhanlife.co.kr/bizxpress/cdh/cdhi/gd/pr/__media/상품요약서_(간편)신한통합건강보장보험원(ONE)(무배당_해약환급금미지급형)_20241022_v0.3.pdf	https://www.shinhanlife.co.kr/bizxpress/cdh/cdhi/gd/pr/__etc/012.사업방법서_(간편)신한통합건강보장보험원(ONE)(무배당, 해약환급금 미지급형)_20241022.pdf	https://www.shinhanlife.co.kr/bizxpress/cdh/cdhi/gd/pr/__etc/판매약관_(간편)신한통합건강보장보험 원(ONE)(무배당, 해약환급금 미지급형)_20241022.pdf
판매중	신한라이프	TM>보장	(간편)신한통합건강보장보험 원(ONE)(무배당, 해약환급금 미지급형)	2024.10.01 ~ 2024.10.21	X	https://www.shinhanlife.co.kr/bizxpress/cdh/cdhi/gd/pr/__etc/012.사업방법서_(간편)신한통합건강보장보험원(ONE)(무배당, 해약환급금 미지급형)_20240903_v1.0.pdf	https://www.shinhanlife.co.kr/bizxpress/cdh/cdhi/gd/pr/__etc/SHL0343_(간편)신한통합건강보장보험 원(ONE)(무배당, 해약환급금 미지급형)_241002.pdf
판매중	신한라이프	TM>보장	(간편)신한통합건강보장보험 원(ONE)(무배당, 해약환급금 미지급형)	2024.09.03 ~ 2024.09.30	X	https://www.shinhanlife.co.kr/bizxpress/cdh/cdhi/gd/pr/__etc/012.사업방법서_(간편)신한통합건강보장보험원(ONE)(무배당, 해약환급금 미지급형)_20240903_v1.0.pdf	https://www.shinhanlife.co.kr/bizxpress/cdh/cdhi/gd/pr/__etc/판매약관_(간편)신한통합건강보장보험 원(ONE)(무배당, 해약환급금 미지급형)_240903.pdf

이 코드의 주요 기능은 다음과 같습니다:
1. pandas를 사용하여 엑셀 파일의 첫 번째 시트를 읽습니다.
2. 지정된 URL 컬럼들('요약서', '방법서', '약관')에서 URL을 추출합니다.
3. URL이 'http'로 시작하는 경우에만 다운로드를 시도합니다 ('X'나 공백은 무시).
4. 각 PDF 파일을 지정된 출력 디렉토리에 저장합니다.
5. 다운로드 진행 상황과 오류를 콘솔에 출력합니다.
5.1 진행 상태 표시
- tqdm을 사용하여 진행바 표시
- 전체 진행률과 남은 시간을 실시간으로 확인 가능
5.2 상세한 로깅
- 날짜/시간별로 로그 파일 생성
- 성공/실패/건너뜀 상태를 자세히 기록
- 에러 메시지도 로그에 포함
5.3 통계 정보
- 총 URL 수, 성공, 실패, 건너뜀 횟수를 집계
- 작업 완료 후 요약 정보 출력
6. 참고사항:
- SSL 인증서 관련 문제가 있을 수 있어 verify=False 옵션을 사용했습니다.
- 파일명에 한글이 포함되어 있어 unquote를 사용하여 URL 디코딩을 수행합니다.
- 오류 처리를 포함하여 안정적으로 다운로드를 수행합니다.

사용법
python download_pdf.py --excel_path custom.xlsx --output_dir custom_pdfs --url_columns 요약서 방법서 약관

"""

import pandas as pd
import requests
import os
from urllib.parse import unquote
from pathlib import Path
from tqdm import tqdm
from datetime import datetime
import argparse
import warnings
import time  # 추가된 import
warnings.filterwarnings('ignore')

def download_pdf(excel_path, output_dir, url_columns, delay=1.0):  # delay 매개변수 추가
    """
    엑셀 파일에서 URL을 읽어 PDF 파일을 다운로드하는 함수
    
    Args:
        excel_path (str): 엑셀 파일 경로
        output_dir (str): PDF 파일 저장 디렉토리
        url_columns (list): PDF URL이 있는 컬럼명 리스트
        delay (float): 각 다운로드 사이의 대기 시간(초)
    """
    # 출력 디렉토리 생성
    os.makedirs(output_dir, exist_ok=True)
    
    # 로그 파일 설정
    log_dir = Path(output_dir) / "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = log_dir / f"download_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    # 통계 변수 초기화
    stats = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0
    }
    
    # 엑셀 파일 읽기
    print("엑셀 파일 읽는 중...")
    df = pd.read_excel(excel_path, sheet_name=0)
    
    # 전체 URL 개수 계산 (http로 시작하는 URL만)
    total_urls = sum(1 for _, row in df.iterrows() 
                    for column in url_columns 
                    if str(row[column]).strip().startswith('http'))
    stats["total"] = total_urls
    
    # 진행바 설정
    with tqdm(total=total_urls, desc="PDF 다운로드") as pbar:
        # 로그 파일 시작
        with open(log_file, 'w', encoding='utf-8') as log:
            log.write(f"다운로드 시작 시간: {datetime.now()}\n")
            log.write(f"엑셀 파일: {excel_path}\n")
            log.write("-" * 50 + "\n")
            
            # 각 행에 대해 처리
            for idx, row in df.iterrows():
                for column in url_columns:
                    url = str(row[column]).strip()
                    
                    if not url.startswith('http'):
                        if url != "X" and url.strip():  # 빈 문자열이나 'X'가 아닌 경우만 기록
                            stats["skipped"] += 1
                            log.write(f"건너뜀: {url} (올바른 URL 형식 아님)\n")
                        continue
                    
                    try:
                        # PDF 다운로드
                        response = requests.get(url, verify=False)
                        if response.status_code == 200:
                            # URL에서 파일명 추출 및 디코딩
                            filename = unquote(url.split('/')[-1])
                            
                            # 파일 저장
                            file_path = Path(output_dir) / filename
                            with open(file_path, 'wb') as f:
                                f.write(response.content)
                            
                            stats["success"] += 1
                            log.write(f"성공: {filename}\n")
                        else:
                            stats["failed"] += 1
                            log.write(f"실패 (상태 코드: {response.status_code}): {url}\n")
                            
                    except Exception as e:
                        stats["failed"] += 1
                        log.write(f"오류: {url}\n")
                        log.write(f"에러 메시지: {str(e)}\n")
                    
                    pbar.update(1)
                    time.sleep(delay)  # 다음 다운로드 전 대기
            
            # 최종 통계 기록
            log.write("\n" + "=" * 50 + "\n")
            log.write(f"다운로드 완료 시간: {datetime.now()}\n")
            log.write(f"총 URL 수: {stats['total']}\n")
            log.write(f"성공: {stats['success']}\n")
            log.write(f"실패: {stats['failed']}\n")
            log.write(f"건너뜀: {stats['skipped']}\n")
    
    # 최종 결과 출력
    print("\n다운로드 완료!")
    print(f"총 URL 수: {stats['total']}")
    print(f"성공: {stats['success']}")
    print(f"실패: {stats['failed']}")
    print(f"건너뜀: {stats['skipped']}")
    print(f"\n로그 파일 위치: {log_file}")

def main():
    # 명령줄 인수 파서 설정
    parser = argparse.ArgumentParser(description='엑셀 파일에서 PDF 파일 다운로드')
    parser.add_argument('--excel_path', 
                      default='shinhan_life_products_combined.xlsx',
                      help='엑셀 파일 경로 (기본값: shinhan_life_products_combined.xlsx)')
    parser.add_argument('--output_dir', 
                      default='data/pdf_docs',
                      help='PDF 파일 저장 디렉토리 (기본값: data/pdf_docs)')
    parser.add_argument('url_columns', nargs='*',
                      default=['요약서', '방법서', '약관'],
                      help='URL이 포함된 컬럼명들 (기본값: 요약서 방법서 약관)')
    parser.add_argument('--delay',
                      type=float,
                      default=1.0,
                      help='다운로드 간 대기 시간(초) (기본값: 1.0)')
    
    # 인수 파싱
    args = parser.parse_args()
    
    # 다운로드 실행
    download_pdf(args.excel_path, args.output_dir, args.url_columns, args.delay)

if __name__ == "__main__":
    main()