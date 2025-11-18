"""
환경 검증 스크립트

이 스크립트는 risk_management.py의 수정사항이 제대로 로드되는지 확인합니다.
"""
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("="*60)
print("=== 환경 검증 스크립트 ===")
print("="*60)

# 1. 파일 확인
print("\n1️⃣ 파일 내용 확인:")
risk_mgmt_file = project_root / 'src' / 'strategy' / 'risk_management.py'
print(f"   파일 경로: {risk_mgmt_file}")
print(f"   파일 존재: {risk_mgmt_file.exists()}")

if risk_mgmt_file.exists():
    with open(risk_mgmt_file, 'r') as f:
        content = f.read()
        if 'total_pnl_pct' in content:
            print("   ✅ 파일에 'total_pnl_pct' 포함됨")
            count = content.count('total_pnl_pct')
            print(f"   📊 'total_pnl_pct' 출현 횟수: {count}")
        else:
            print("   ❌ 파일에 'total_pnl_pct' 없음!")

# 2. 모듈 import 확인
print("\n2️⃣ 모듈 import 확인:")
try:
    from src.strategy.risk_management import RiskManager
    print("   ✅ RiskManager 임포트 성공")

    # 모듈 파일 위치 확인
    import inspect
    module_file = inspect.getfile(RiskManager)
    print(f"   📁 로드된 모듈 위치: {module_file}")

except Exception as e:
    print(f"   ❌ 임포트 실패: {e}")
    sys.exit(1)

# 3. 메서드 테스트
print("\n3️⃣ get_performance_stats() 메서드 테스트:")
try:
    risk_mgr = RiskManager(initial_capital=10000)

    # 빈 통계 테스트
    stats = risk_mgr.get_performance_stats()
    print("   ✅ 메서드 호출 성공")
    print(f"   📊 반환된 키: {list(stats.keys())}")

    # 필수 키 확인
    required_keys = [
        'total_trades', 'winning_trades', 'losing_trades', 'win_rate',
        'total_pnl', 'total_pnl_pct', 'avg_win', 'avg_loss',
        'profit_factor', 'max_drawdown', 'max_drawdown_pct'
    ]

    missing_keys = [key for key in required_keys if key not in stats]

    if missing_keys:
        print(f"   ❌ 누락된 키: {missing_keys}")
    else:
        print("   ✅ 모든 필수 키 존재")
        print(f"   💯 total_pnl_pct = {stats['total_pnl_pct']}")
        print(f"   💯 max_drawdown_pct = {stats['max_drawdown_pct']}")

except KeyError as e:
    print(f"   ❌ KeyError 발생: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"   ❌ 에러 발생: {e}")
    import traceback
    traceback.print_exc()

# 4. 캐시 파일 확인
print("\n4️⃣ Python 캐시 파일 확인:")
pycache_dirs = list(project_root.rglob('__pycache__'))
if pycache_dirs:
    print(f"   ⚠️  {len(pycache_dirs)}개의 __pycache__ 디렉토리 발견")
    for pycache in pycache_dirs[:5]:  # 처음 5개만 표시
        print(f"      - {pycache}")
    if len(pycache_dirs) > 5:
        print(f"      ... 외 {len(pycache_dirs) - 5}개")
    print("\n   💡 캐시 삭제 명령어:")
    print("      find . -type d -name __pycache__ -exec rm -r {} +")
    print("      또는")
    print("      find . -type f -name '*.pyc' -delete")
else:
    print("   ✅ __pycache__ 디렉토리 없음")

print("\n" + "="*60)
print("검증 완료!")
print("="*60)
