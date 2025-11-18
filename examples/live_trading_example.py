"""
라이브 트레이딩 예제

실제 거래소와 연동하여 ICT 전략을 실시간으로 실행합니다.

⚠️ 주의사항:
1. 반드시 테스트넷에서 먼저 테스트하세요
2. API 키를 안전하게 관리하세요 (.env 파일 사용)
3. 소액으로 시작하세요
4. Kill Switch 설정을 확인하세요
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import os
from dotenv import load_dotenv
import yaml

from src.exchange.connector import ExchangeConnector
from src.exchange.live_trading import LiveTradingEngine


def run_live_trading():
    """라이브 트레이딩 실행"""
    print("="*60)
    print("=== ICT 라이브 트레이딩 시스템 ===")
    print("="*60)

    # 환경 변수 로드
    load_dotenv()

    # API 키 확인
    api_key = os.getenv('EXCHANGE_API_KEY')
    api_secret = os.getenv('EXCHANGE_API_SECRET')

    if not api_key or not api_secret:
        print("\n⚠️  API 키가 설정되지 않았습니다!")
        print("1. .env 파일을 생성하세요")
        print("2. 다음 내용을 추가하세요:")
        print("   EXCHANGE_API_KEY=your_api_key")
        print("   EXCHANGE_API_SECRET=your_api_secret")
        print("   EXCHANGE_ID=binance")
        print("   SYMBOL=BTC/USDT")
        print("   TESTNET=true")
        return

    # 설정
    exchange_id = os.getenv('EXCHANGE_ID', 'binance')
    symbol = os.getenv('SYMBOL', 'BTC/USDT')
    testnet = os.getenv('TESTNET', 'true').lower() == 'true'
    initial_capital = float(os.getenv('INITIAL_CAPITAL', '1000'))

    print(f"\n📝 설정:")
    print(f"  거래소: {exchange_id}")
    print(f"  심볼: {symbol}")
    print(f"  테스트넷: {testnet}")
    print(f"  초기 자본: ${initial_capital}")

    # 사용자 확인
    if not testnet:
        print("\n⚠️  실제 거래소 모드입니다!")
        response = input("계속하시겠습니까? (yes/no): ")
        if response.lower() != 'yes':
            print("취소됨")
            return

    # 1. 거래소 연결
    print("\n🔌 거래소 연결 중...")
    exchange = ExchangeConnector(
        exchange_id=exchange_id,
        api_key=api_key,
        api_secret=api_secret,
        testnet=testnet
    )
    print("✅ 연결 완료")

    # 잔고 확인
    try:
        balance = exchange.fetch_balance()
        print(f"\n💰 계좌 잔고:")
        if 'USDT' in balance['total']:
            print(f"  USDT: {balance['total']['USDT']:.2f}")
    except Exception as e:
        print(f"⚠️  잔고 조회 실패: {e}")

    # 2. 설정 로드
    with open('config/config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 3. 라이브 트레이딩 엔진 초기화
    print("\n🚀 트레이딩 엔진 초기화 중...")
    engine = LiveTradingEngine(
        exchange_connector=exchange,
        symbol=symbol,
        initial_capital=initial_capital,
        config=config
    )
    print("✅ 초기화 완료")

    # 4. 트레이딩 시작
    print("\n" + "="*60)
    print("▶️  트레이딩 시작")
    print("="*60)
    print("\n💡 팁:")
    print("  - Ctrl+C를 눌러 안전하게 종료할 수 있습니다")
    print("  - Kill Switch가 자동으로 리스크를 관리합니다")
    print("  - 로그를 주의 깊게 확인하세요\n")

    try:
        # 업데이트 간격 (초)
        update_interval = int(os.getenv('UPDATE_INTERVAL', '60'))

        engine.start(update_interval=update_interval)

    except KeyboardInterrupt:
        print("\n\n⏹️  사용자에 의해 중단됨")
        engine.stop()

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        import traceback
        traceback.print_exc()
        engine.stop()


def main():
    """메인 함수"""
    # 안전 확인
    print("\n⚠️  경고:")
    print("  1. 이 시스템은 실험적이며 손실 위험이 있습니다")
    print("  2. 반드시 테스트넷에서 먼저 테스트하세요")
    print("  3. 소액으로 시작하고 점진적으로 확대하세요")
    print("  4. 시장 상황을 지속적으로 모니터링하세요")
    print("  5. 자신의 리스크 허용도를 이해하세요\n")

    response = input("위 내용을 이해했으며 계속하시겠습니까? (yes/no): ")
    if response.lower() != 'yes':
        print("취소됨")
        return

    run_live_trading()


if __name__ == "__main__":
    main()
