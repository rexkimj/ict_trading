"""
거래소 커넥터 모듈

CCXT를 활용하여 다양한 거래소와 연동합니다.
"""
import ccxt
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import time

from ..utils.logger import setup_logger


class ExchangeConnector:
    """거래소 연결 클래스"""

    def __init__(
        self,
        exchange_id: str = 'binance',
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = True,
        logger_name: str = 'ExchangeConnector'
    ):
        """
        Args:
            exchange_id: 거래소 ID (binance, bybit, okx 등)
            api_key: API 키
            api_secret: API 시크릿
            testnet: 테스트넷 사용 여부
            logger_name: 로거 이름
        """
        self.exchange_id = exchange_id
        self.testnet = testnet
        self.logger = setup_logger(logger_name)

        # 거래소 초기화
        self.exchange = self._initialize_exchange(
            exchange_id, api_key, api_secret, testnet
        )

        self.logger.info(f"거래소 연결: {exchange_id} (testnet={testnet})")

    def _initialize_exchange(
        self,
        exchange_id: str,
        api_key: Optional[str],
        api_secret: Optional[str],
        testnet: bool
    ) -> ccxt.Exchange:
        """거래소 초기화"""
        exchange_class = getattr(ccxt, exchange_id)

        config = {
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',  # 선물 거래
            }
        }

        if api_key and api_secret:
            config['apiKey'] = api_key
            config['secret'] = api_secret

        exchange = exchange_class(config)

        # 테스트넷 설정
        if testnet:
            if exchange_id == 'binance':
                exchange.set_sandbox_mode(True)
            elif exchange_id == 'bybit':
                exchange.set_sandbox_mode(True)

        return exchange

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = '5m',
        limit: int = 1000,
        since: Optional[int] = None
    ) -> pd.DataFrame:
        """
        OHLCV 데이터 조회

        Args:
            symbol: 심볼 (예: 'BTC/USDT')
            timeframe: 타임프레임 ('1m', '5m', '15m', '1h', '4h', '1d')
            limit: 조회할 캔들 개수
            since: 시작 타임스탬프 (밀리초)

        Returns:
            OHLCV 데이터프레임
        """
        try:
            self.logger.info(f"OHLCV 조회: {symbol} {timeframe} (limit={limit})")

            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                since=since
            )

            # 데이터프레임 변환
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )

            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            self.logger.info(f"OHLCV 조회 완료: {len(df)} 캔들")
            return df

        except Exception as e:
            self.logger.error(f"OHLCV 조회 실패: {e}")
            raise

    def fetch_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: str
    ) -> pd.DataFrame:
        """
        과거 데이터 조회 (대량)

        Args:
            symbol: 심볼
            timeframe: 타임프레임
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)

        Returns:
            OHLCV 데이터프레임
        """
        self.logger.info(f"과거 데이터 조회: {symbol} {timeframe} ({start_date} ~ {end_date})")

        start_ts = int(pd.Timestamp(start_date).timestamp() * 1000)
        end_ts = int(pd.Timestamp(end_date).timestamp() * 1000)

        all_data = []
        current_ts = start_ts

        # 타임프레임별 밀리초
        timeframe_ms = self._timeframe_to_ms(timeframe)

        while current_ts < end_ts:
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=1000,
                    since=current_ts
                )

                if not ohlcv:
                    break

                all_data.extend(ohlcv)
                current_ts = ohlcv[-1][0] + timeframe_ms

                # Rate limit 준수
                time.sleep(self.exchange.rateLimit / 1000)

                self.logger.info(f"진행: {len(all_data)} 캔들 수집")

            except Exception as e:
                self.logger.error(f"데이터 조회 중 오류: {e}")
                break

        # 데이터프레임 변환
        df = pd.DataFrame(
            all_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)

        # 중복 제거 및 정렬
        df = df[~df.index.duplicated(keep='first')]
        df = df.sort_index()

        # 날짜 필터링
        df = df[(df.index >= start_date) & (df.index <= end_date)]

        self.logger.info(f"과거 데이터 조회 완료: {len(df)} 캔들")
        return df

    def _timeframe_to_ms(self, timeframe: str) -> int:
        """타임프레임을 밀리초로 변환"""
        timeframe_map = {
            '1m': 60 * 1000,
            '5m': 5 * 60 * 1000,
            '15m': 15 * 60 * 1000,
            '1h': 60 * 60 * 1000,
            '4h': 4 * 60 * 60 * 1000,
            '1d': 24 * 60 * 60 * 1000,
        }
        return timeframe_map.get(timeframe, 60 * 1000)

    def fetch_ticker(self, symbol: str) -> Dict:
        """
        현재 시세 조회

        Args:
            symbol: 심볼

        Returns:
            시세 정보
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker
        except Exception as e:
            self.logger.error(f"시세 조회 실패: {e}")
            raise

    def fetch_balance(self) -> Dict:
        """
        계좌 잔고 조회

        Returns:
            잔고 정보
        """
        try:
            balance = self.exchange.fetch_balance()
            return balance
        except Exception as e:
            self.logger.error(f"잔고 조회 실패: {e}")
            raise

    def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        시장가 주문

        Args:
            symbol: 심볼
            side: 'buy' or 'sell'
            amount: 수량
            params: 추가 파라미터

        Returns:
            주문 정보
        """
        try:
            self.logger.info(f"시장가 주문: {symbol} {side} {amount}")

            order = self.exchange.create_market_order(
                symbol=symbol,
                side=side,
                amount=amount,
                params=params or {}
            )

            self.logger.info(f"주문 완료: {order['id']}")
            return order

        except Exception as e:
            self.logger.error(f"주문 실패: {e}")
            raise

    def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        지정가 주문

        Args:
            symbol: 심볼
            side: 'buy' or 'sell'
            amount: 수량
            price: 가격
            params: 추가 파라미터

        Returns:
            주문 정보
        """
        try:
            self.logger.info(f"지정가 주문: {symbol} {side} {amount} @ {price}")

            order = self.exchange.create_limit_order(
                symbol=symbol,
                side=side,
                amount=amount,
                price=price,
                params=params or {}
            )

            self.logger.info(f"주문 완료: {order['id']}")
            return order

        except Exception as e:
            self.logger.error(f"주문 실패: {e}")
            raise

    def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """주문 취소"""
        try:
            result = self.exchange.cancel_order(order_id, symbol)
            self.logger.info(f"주문 취소: {order_id}")
            return result
        except Exception as e:
            self.logger.error(f"주문 취소 실패: {e}")
            raise

    def fetch_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """미체결 주문 조회"""
        try:
            orders = self.exchange.fetch_open_orders(symbol)
            return orders
        except Exception as e:
            self.logger.error(f"미체결 주문 조회 실패: {e}")
            raise

    def fetch_positions(self, symbols: Optional[List[str]] = None) -> List[Dict]:
        """
        포지션 조회 (선물)

        Args:
            symbols: 심볼 리스트 (None이면 전체)

        Returns:
            포지션 리스트
        """
        try:
            positions = self.exchange.fetch_positions(symbols)
            # 포지션이 있는 것만 필터링
            active_positions = [p for p in positions if float(p.get('contracts', 0)) != 0]
            return active_positions
        except Exception as e:
            self.logger.error(f"포지션 조회 실패: {e}")
            raise

    def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """
        레버리지 설정 (선물)

        Args:
            symbol: 심볼
            leverage: 레버리지 배수

        Returns:
            설정 결과
        """
        try:
            result = self.exchange.set_leverage(leverage, symbol)
            self.logger.info(f"레버리지 설정: {symbol} {leverage}x")
            return result
        except Exception as e:
            self.logger.error(f"레버리지 설정 실패: {e}")
            raise

    def close_position(
        self,
        symbol: str,
        side: str,
        amount: float
    ) -> Dict:
        """
        포지션 청산

        Args:
            symbol: 심볼
            side: 'buy' (숏 청산) or 'sell' (롱 청산)
            amount: 수량

        Returns:
            주문 정보
        """
        params = {'reduceOnly': True}
        return self.create_market_order(symbol, side, amount, params)
