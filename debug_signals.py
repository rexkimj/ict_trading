"""
시그널 디버깅 스크립트

왜 거래가 발생하지 않는지 분석합니다.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

import pandas as pd
from src.exchange.connector import ExchangeConnector
from src.core.liquidity import LiquidityAnalyzer
from src.core.market_structure import MarketStructureAnalyzer
from src.core.fvg import FVGAnalyzer
from src.core.order_block import OrderBlockAnalyzer
from src.core.poi import POIManager
from src.analysis.timeframe import MultiTimeframeAnalyzer
from src.analysis.seven_factors import SevenFactorAnalyzer
from src.strategy.entry import EntryStrategy


def analyze_signals():
    """시그널 분석"""
    print("="*60)
    print("=== ICT 시그널 디버깅 ===")
    print("="*60)

    # 1. 데이터 로드
    print("\n📥 데이터 로드 중...")
    symbol = 'BTC/USDT'
    timeframe = '5m'

    # 캐시된 데이터 확인
    data_dir = Path(__file__).parent / 'data'
    symbol_safe = symbol.replace('/', '_')
    filepath = data_dir / f"{symbol_safe}_{timeframe}_2024-01-01_2024-03-31.csv"

    if filepath.exists():
        df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        print(f"✅ 캐시 데이터 로드: {len(df)} 캔들")
    else:
        print("❌ 캐시 데이터 없음. 먼저 backtest_with_real_data.py를 실행하세요.")
        return

    print(f"   기간: {df.index[0]} ~ {df.index[-1]}")
    print(f"   가격: ${df['close'].iloc[0]:.2f} → ${df['close'].iloc[-1]:.2f}")

    # 2. 컴포넌트 초기화
    print("\n🔧 컴포넌트 초기화...")
    liquidity_analyzer = LiquidityAnalyzer()
    market_structure_analyzer = MarketStructureAnalyzer()
    fvg_analyzer = FVGAnalyzer()
    ob_analyzer = OrderBlockAnalyzer()
    poi_manager = POIManager(ob_analyzer, fvg_analyzer, liquidity_analyzer)

    mtf_analyzer = MultiTimeframeAnalyzer(
        higher_timeframe='4H',
        entry_timeframe='15M',
        confirmation_timeframe='5M'
    )

    poi_managers = {
        'htf': POIManager(OrderBlockAnalyzer(), FVGAnalyzer(), LiquidityAnalyzer()),
        'etf': POIManager(OrderBlockAnalyzer(), FVGAnalyzer(), LiquidityAnalyzer()),
        'ctf': POIManager(OrderBlockAnalyzer(), FVGAnalyzer(), LiquidityAnalyzer())
    }

    seven_factor_analyzer = SevenFactorAnalyzer(
        liquidity_analyzer,
        market_structure_analyzer,
        fvg_analyzer,
        ob_analyzer,
        poi_manager,
        mtf_analyzer
    )

    entry_strategy = EntryStrategy(
        seven_factor_analyzer, mtf_analyzer, poi_manager,
        min_confidence=0.5  # 디버깅을 위해 낮은 임계값 사용
    )

    # 3. 분석 실행
    print("\n🔍 데이터 분석 중...")

    # POI 업데이트
    poi_manager.update_all_pois(df)
    print(f"✅ POI 업데이트 완료")

    # 시장 구조 분석
    market_structure_analyzer.identify_structure(df)
    trend = market_structure_analyzer.determine_trend()
    print(f"✅ 시장 구조 분석 완료")
    print(f"   트렌드: {trend}")

    # 유동성 분석
    liquidity_analyzer.identify_pdh_pdl(df)
    pdh_pdl = liquidity_analyzer.get_recent_pdh_pdl()
    print(f"✅ 유동성 분석 완료")
    if pdh_pdl:
        print(f"   PDH: ${pdh_pdl['pdh']:.2f}")
        print(f"   PDL: ${pdh_pdl['pdl']:.2f}")

    # FVG 분석
    fvg_analyzer.detect_fvg(df)
    fvgs = fvg_analyzer.get_open_fvgs()
    print(f"✅ FVG 분석 완료")
    print(f"   열린 FVG: {len(fvgs)}개")

    # 멀티타임프레임 분석
    mtf_analyzer.analyze_all_timeframes(df, poi_managers)
    alignment = mtf_analyzer.check_timeframe_alignment()
    print(f"✅ 멀티타임프레임 분석 완료")
    print(f"   타임프레임 정렬: {alignment}")

    # 4. 진입 시그널 검사 (마지막 100개 캔들)
    print("\n" + "="*60)
    print("=== 진입 시그널 스캔 (마지막 100 캔들) ===")
    print("="*60)

    signals_found = []
    scan_range = min(100, len(df) - 200)  # 최소 200개 캔들은 분석용으로 필요

    for i in range(-scan_range, 0):
        current_price = df['close'].iloc[i]
        timestamp = df.index[i]

        # 진입 체크
        entry_signal = entry_strategy.check_entry(df.iloc[:i+1], current_price)

        if entry_signal:
            signals_found.append({
                'timestamp': timestamp,
                'price': current_price,
                'direction': entry_signal.direction,
                'confidence': entry_signal.confidence,
                'reason': entry_signal.reason
            })

    print(f"\n📊 스캔 결과:")
    print(f"   검사한 캔들: {scan_range}개")
    print(f"   발견된 시그널: {len(signals_found)}개")

    if signals_found:
        print(f"\n🎯 발견된 시그널 상세:")
        for sig in signals_found[:10]:  # 최대 10개만 표시
            print(f"\n   시간: {sig['timestamp']}")
            print(f"   가격: ${sig['price']:.2f}")
            print(f"   방향: {sig['direction']}")
            print(f"   신뢰도: {sig['confidence']*100:.1f}%")
            print(f"   사유: {sig['reason']}")

        if len(signals_found) > 10:
            print(f"\n   ... 외 {len(signals_found)-10}개 시그널")

        # 신뢰도별 분포
        high_confidence = [s for s in signals_found if s['confidence'] >= 0.7]
        medium_confidence = [s for s in signals_found if 0.5 <= s['confidence'] < 0.7]
        low_confidence = [s for s in signals_found if s['confidence'] < 0.5]

        print(f"\n📈 신뢰도 분포:")
        print(f"   높음 (≥70%): {len(high_confidence)}개")
        print(f"   중간 (50-70%): {len(medium_confidence)}개")
        print(f"   낮음 (<50%): {len(low_confidence)}개")

        if len(high_confidence) == 0:
            print(f"\n⚠️  신뢰도 70% 이상인 시그널이 없습니다!")
            print(f"   백테스트는 70% 이상만 거래하므로 거래가 발생하지 않습니다.")
            print(f"\n💡 해결 방안:")
            print(f"   1. 신뢰도 임계값을 낮추기 (예: 0.5)")
            print(f"   2. 더 긴 기간 데이터 사용")
            print(f"   3. ICT 전략 파라미터 조정")
    else:
        print(f"\n❌ 시그널이 전혀 발견되지 않았습니다!")
        print(f"\n🔍 가능한 원인:")
        print(f"   1. 시장 조건이 ICT 패턴과 맞지 않음")
        print(f"   2. 전략 파라미터가 너무 엄격함")
        print(f"   3. 데이터 품질 문제")
        print(f"\n💡 확인사항:")
        print(f"   - 트렌드: {trend}")
        print(f"   - FVG: {len(fvgs)}개")
        print(f"   - 타임프레임 정렬: {alignment}")

        # 세부 분석
        print(f"\n🔬 세부 분석 (마지막 캔들):")
        current_price = df['close'].iloc[-1]

        # 7 팩터 점수 확인
        analysis = seven_factor_analyzer.analyze_all_factors(
            df, current_price, 'long'
        )

        print(f"\n   7 팩터 점수:")
        print(f"   - 유동성: {analysis.liquidity_score:.2f}")
        print(f"   - 시장 구조: {analysis.structure_score:.2f}")
        print(f"   - BOS: {analysis.bos_score:.2f}")
        print(f"   - FVG: {analysis.fvg_score:.2f}")
        print(f"   - 할인/프리미엄: {analysis.discount_premium_score:.2f}")
        print(f"   - 타임프레임: {analysis.timeframe_score:.2f}")
        print(f"   - SMT: {analysis.smt_score:.2f}")
        print(f"   → 총점: {analysis.total_score:.2f} (70% = 0.7 필요)")


if __name__ == "__main__":
    analyze_signals()
