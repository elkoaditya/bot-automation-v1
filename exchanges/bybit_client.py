"""Bybit API client wrapper with dual API support."""
from pybit.unified_trading import HTTP
import pandas as pd
import requests
import time
import hmac
import hashlib
import json
from urllib.parse import urlencode
from config import Config


class BybitClient:
    """Bybit client for trading (demo) and market data (real)."""
    
    def __init__(self):
        """Initialize Bybit clients."""
        self.api_key = Config.BYBIT_API_KEY
        self.api_secret = Config.BYBIT_API_SECRET
        self.trading_api_url = Config.get_trading_api_url()
        self.market_api_url = Config.get_market_api_url()
        
        # Trading client (demo API) - using requests for custom endpoint
        # For market data, use pybit HTTP client (real API)
        self.market_client = HTTP(
            testnet=False,
            api_key='',
            api_secret=''
        )
    
    def _make_request(self, method: str, endpoint: str, params: dict = None, use_auth: bool = True):
        """Make authenticated request to Bybit API v5."""
        if params is None:
            params = {}
        
        # Ensure params are properly formatted (all values as strings where needed)
        formatted_params = {}
        for k, v in params.items():
            if isinstance(v, (int, float)):
                formatted_params[k] = str(v)
            else:
                formatted_params[k] = v
        
        url = f"{self.trading_api_url}{endpoint}"
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        if use_auth:
            timestamp = str(int(time.time() * 1000))
            recv_window = '5000'
            
            # For signature: timestamp + api_key + recv_window + query_string/body
            if method.upper() == 'GET':
                # GET: signature = timestamp + api_key + recv_window + query_string
                query_string = '&'.join([f"{k}={v}" for k, v in sorted(formatted_params.items())])
                sign_str = timestamp + self.api_key + recv_window + query_string
            else:
                # POST: signature = timestamp + api_key + recv_window + json_body
                # IMPORTANT: Convert params to JSON string BEFORE creating signature
                # Bybit requires compact JSON without any spaces
                # Parameters should be sorted alphabetically for consistent signature
                sorted_params = dict(sorted(formatted_params.items()))
                json_body = json.dumps(sorted_params, separators=(',', ':'), ensure_ascii=False)
                # Verify no spaces (remove any potential spaces just in case)
                json_body = json_body.replace(' ', '')
                sign_str = timestamp + self.api_key + recv_window + json_body
                # Store json_body for later use in request
                formatted_params['_json_body'] = json_body
                # Debug: print sign string (remove in production)
                # print(f"DEBUG Sign String: {sign_str}")
                # print(f"DEBUG JSON Body: {json_body}")
            
            # Generate signature
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                sign_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers.update({
                'X-BAPI-API-KEY': self.api_key,
                'X-BAPI-SIGN': signature,
                'X-BAPI-SIGN-TYPE': '2',
                'X-BAPI-TIMESTAMP': timestamp,
                'X-BAPI-RECV-WINDOW': recv_window
            })
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, params=formatted_params, headers=headers, timeout=10)
            else:
                # For POST, use the exact json_body that was used for signature
                if '_json_body' in formatted_params:
                    json_body_str = formatted_params.pop('_json_body')
                    # Use data parameter to send exact string that was used for signature
                    response = requests.post(url, data=json_body_str.encode('utf-8'), headers=headers, timeout=10)
                else:
                    # Fallback: send params as JSON body
                    response = requests.post(url, json=formatted_params, headers=headers, timeout=10)
            
            response.raise_for_status()
            result = response.json()
            
            # Log for debugging if needed
            if result.get('retCode') != 0:
                print(f"API Error: {result.get('retMsg')} - Code: {result.get('retCode')}")
                # Debug: print response for troubleshooting
                if result.get('retMsg', '').find('signature') != -1:
                    print(f"DEBUG: Request URL: {url}")
                    print(f"DEBUG: Request Headers: {headers}")
                    print(f"DEBUG: Request Body: {json.dumps(formatted_params)}")
            
            return result
        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg += f" - {error_detail}"
                except:
                    error_msg += f" - Status: {e.response.status_code}"
            raise Exception(error_msg)
    
    def get_kline(self, symbol: str, interval: str, limit: int = 200):
        """
        Get candlestick/kline data from real market API.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Time interval (e.g., '15', '60', 'D')
            limit: Number of candles to retrieve
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Map interval to Bybit format
            interval_map = {
                '1': '1', '3': '3', '5': '5', '15': '15',
                '30': '30', '60': '60', '120': '120', '240': '240',
                '360': '360', '720': '720', 'D': 'D', 'W': 'W', 'M': 'M'
            }
            
            bybit_interval = interval_map.get(str(interval), '15')
            
            # Add timeout for API call
            response = self.market_client.get_kline(
                category="linear",
                symbol=symbol,
                interval=bybit_interval,
                limit=limit
            )
            
            if response['retCode'] != 0:
                raise Exception(f"Error fetching kline: {response['retMsg']}")
            
            data = response['result']['list']
            
            # Convert to DataFrame
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
            df = df[::-1].reset_index(drop=True)  # Reverse to chronological order
            
            # Convert data types
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            df['open'] = df['open'].astype(float)
            df['high'] = df['high'].astype(float)
            df['low'] = df['low'].astype(float)
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            return df
            
        except Exception as e:
            raise Exception(f"Failed to get kline data: {str(e)}")
    
    def get_instrument_info(self, symbol: str):
        """Get instrument information including minimum order size."""
        try:
            response = self.market_client.get_instruments_info(
                category="linear",
                symbol=symbol
            )
            
            if response['retCode'] != 0:
                raise Exception(f"Error fetching instrument info: {response['retMsg']}")
            
            instruments = response['result']['list']
            if instruments:
                return instruments[0]
            return None
            
        except Exception as e:
            raise Exception(f"Failed to get instrument info: {str(e)}")
    
    def get_minimum_order_size(self, symbol: str):
        """Get minimum order size and minimum order value for a symbol."""
        try:
            instrument = self.get_instrument_info(symbol)
            min_order_value = 5.0  # Default minimum order value in USDT for Bybit linear
            
            if instrument:
                # Bybit API v5 structure - lotSizeFilter is a direct object
                lot_size_filter = instrument.get('lotSizeFilter', {})
                
                if lot_size_filter:
                    min_qty = float(lot_size_filter.get('minOrderQty', lot_size_filter.get('minQty', 0.001)))
                    qty_step = float(lot_size_filter.get('qtyStep', 0.001))
                    
                    # Try to get minimum notional value from lotSizeFilter
                    min_notional = lot_size_filter.get('minNotional', None)
                    if min_notional:
                        min_order_value = float(min_notional)
                    
                    return min_qty, qty_step, min_order_value
                
                # Fallback: try common minimums based on symbol
                # Most USDT pairs have minimum around 0.001-0.01 and min order value of 5 USDT
                if 'USDT' in symbol:
                    return 0.01, 0.01, 5.0  # Safe default for USDT pairs
                
                return 0.001, 0.001, 5.0
            return 0.001, 0.001, 5.0
        except Exception as e:
            print(f"Warning: Could not get minimum order size for {symbol}: {e}", flush=True)
            # Return safe defaults - always use 5 USDT minimum order value
            if 'USDT' in symbol:
                return 0.01, 0.01, 5.0
            return 0.001, 0.001, 5.0
    
    def get_top_trending_coins(self, limit: int = 20):
        """
        Get top trending coins by 24h volume.
        
        Args:
            limit: Number of top coins to return (default: 20)
        
        Returns:
            List of symbol strings (e.g., ['BTCUSDT', 'ETHUSDT', ...])
        """
        try:
            response = self.market_client.get_tickers(
                category="linear",
                limit=1000  # Get more to filter by volume
            )
            
            if response['retCode'] != 0:
                raise Exception(f"Error fetching tickers: {response['retMsg']}")
            
            tickers = response['result']['list']
            
            # Filter only USDT pairs and sort by 24h volume
            usdt_pairs = []
            for ticker in tickers:
                symbol = ticker.get('symbol', '')
                if symbol.endswith('USDT'):
                    volume_24h = float(ticker.get('turnover24h', 0))
                    if volume_24h > 0:  # Only include pairs with volume
                        usdt_pairs.append({
                            'symbol': symbol,
                            'volume_24h': volume_24h,
                            'price': float(ticker.get('lastPrice', 0))
                        })
            
            # Sort by volume descending and get top N
            usdt_pairs.sort(key=lambda x: x['volume_24h'], reverse=True)
            top_coins = [item['symbol'] for item in usdt_pairs[:limit]]
            
            return top_coins
            
        except Exception as e:
            raise Exception(f"Failed to get trending coins: {str(e)}")
    
    def get_current_price(self, symbol: str):
        """Get current market price."""
        try:
            response = self.market_client.get_tickers(
                category="linear",
                symbol=symbol
            )
            
            if response['retCode'] != 0:
                raise Exception(f"Error fetching price: {response['retMsg']}")
            
            ticker = response['result']['list'][0]
            return float(ticker['lastPrice'])
            
        except Exception as e:
            raise Exception(f"Failed to get current price: {str(e)}")
    
    def set_leverage(self, symbol: str, leverage: int):
        """Set leverage for trading pair."""
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "buyLeverage": str(leverage),
                "sellLeverage": str(leverage)
            }
            
            response = self._make_request("POST", "/v5/position/set-leverage", params)
            
            ret_code = response.get('retCode')
            ret_msg = response.get('retMsg', 'Unknown error')
            
            # Code 110043 means leverage not modified (already set or can't be changed)
            # This is not a fatal error, just log it
            if ret_code == 110043:
                print(f"ℹ️ Leverage already set or cannot be modified: {ret_msg}")
                return True
            
            if ret_code != 0:
                raise Exception(f"Error setting leverage: {ret_msg}")
            
            return True
            
        except Exception as e:
            raise Exception(f"Failed to set leverage: {str(e)}")
    
    def place_order(self, symbol: str, side: str, order_type: str, qty: str, price: str = None):
        """
        Place order on demo API.
        
        Args:
            symbol: Trading pair
            side: 'Buy' or 'Sell'
            order_type: 'Market' or 'Limit'
            qty: Order quantity
            price: Order price (required for Limit orders)
        """
        try:
            params = {
                "category": "linear",
                "symbol": symbol,
                "side": side,
                "orderType": order_type,
                "qty": qty,
            }
            
            if order_type == "Limit" and price:
                params["price"] = price
            
            response = self._make_request("POST", "/v5/order/create", params)
            
            if response.get('retCode') != 0:
                raise Exception(f"Error placing order: {response.get('retMsg', 'Unknown error')}")
            
            return response.get('result', {})
            
        except Exception as e:
            raise Exception(f"Failed to place order: {str(e)}")
    
    def get_positions(self, symbol: str = None):
        """Get current positions."""
        try:
            params = {"category": "linear"}
            if symbol:
                params["symbol"] = symbol
            
            response = self._make_request("GET", "/v5/position/list", params)
            
            if response.get('retCode') != 0:
                raise Exception(f"Error fetching positions: {response.get('retMsg', 'Unknown error')}")
            
            positions = response.get('result', {}).get('list', [])
            # Filter only open positions
            open_positions = [p for p in positions if float(p.get('size', 0)) != 0]
            return open_positions
            
        except Exception as e:
            raise Exception(f"Failed to get positions: {str(e)}")
    
    def set_tp_sl(self, symbol: str, tp_price: float = None, sl_price: float = None):
        """
        Set Take Profit and Stop Loss for a position.
        
        Args:
            symbol: Trading pair
            tp_price: Take profit price (optional)
            sl_price: Stop loss price (optional)
        """
        try:
            params = {
                "category": "linear",
                "symbol": symbol
            }
            
            if tp_price:
                params["takeProfit"] = str(tp_price)
            
            if sl_price:
                params["stopLoss"] = str(sl_price)
            
            # Only make request if we have at least one parameter
            if tp_price or sl_price:
                response = self._make_request("POST", "/v5/position/trading-stop", params)
                
                ret_code = response.get('retCode')
                ret_msg = response.get('retMsg', 'Unknown error')
                
                if ret_code != 0:
                    raise Exception(f"Error setting TP/SL: {ret_msg}")
                
                return True
            
            return False
            
        except Exception as e:
            raise Exception(f"Failed to set TP/SL: {str(e)}")
    
    def close_position(self, symbol: str, side: str = None):
        """Close position by placing market order in opposite direction."""
        try:
            # Get current position to determine size
            positions = self.get_positions(symbol)
            if not positions:
                raise Exception("No open position found to close")
            
            position = positions[0]
            position_size = float(position['size'])
            
            if position_size == 0:
                raise Exception("Position size is zero")
            
            # Determine opposite side
            if position_size > 0:
                # Long position, need to sell
                close_side = "Sell"
                qty = str(abs(position_size))
            else:
                # Short position, need to buy
                close_side = "Buy"
                qty = str(abs(position_size))
            
            # Override with provided side if available
            if side:
                close_side = side
            
            # Place market order to close (reduceOnly=True ensures we're closing, not opening)
            params = {
                "category": "linear",
                "symbol": symbol,
                "side": close_side,
                "orderType": "Market",
                "qty": qty,
                "reduceOnly": True
            }
            
            response = self._make_request("POST", "/v5/order/create", params)
            
            if response.get('retCode') != 0:
                raise Exception(f"Error closing position: {response.get('retMsg', 'Unknown error')}")
            
            return response.get('result', {})
            
        except Exception as e:
            raise Exception(f"Failed to close position: {str(e)}")
    
    def get_wallet_balance(self):
        """Get wallet balance."""
        try:
            params = {"accountType": "UNIFIED"}
            
            response = self._make_request("GET", "/v5/account/wallet-balance", params)
            
            if response.get('retCode') != 0:
                raise Exception(f"Error fetching balance: {response.get('retMsg', 'Unknown error')}")
            
            return response.get('result', {})
            
        except Exception as e:
            raise Exception(f"Failed to get wallet balance: {str(e)}")

