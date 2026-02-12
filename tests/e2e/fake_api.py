from dataclasses import dataclass, field
from typing import Any, Optional
import socket
import uvicorn
import threading
import time
from fastapi import FastAPI, HTTPException, Request

from tests.e2e.test_data import TestData


@dataclass
class FakeApiServer:
    api_key: str = TestData.API_KEY
    host: str = TestData.LOCAL_IP
    port: Optional[int] = None
    app: FastAPI = field(init=False)
    recorded: list[dict[str, Any]] = field(default_factory=list, init=False)
    base: Optional[str] = field(init=False, default=None)
    _runner: Optional[uvicorn.Server] = field(init=False, default=None)
    _thread: Optional[threading.Thread] = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.app = FastAPI()
        self._register_routes()

    def start(self, port: Optional[int] = None) -> int:
        port = port if port is not None else self._find_available_port(self.host)
        config = uvicorn.Config(app=self.app, host=self.host, port=port, log_level="warning")
        runner = uvicorn.Server(config)
        thread = threading.Thread(target=runner.run, daemon=True)
        thread.start()
        time.sleep(0.1)
        self.base = f"http://{self.host}:{port}/"
        self.port = port
        self._runner = runner
        self._thread = thread
        return self.port

    def stop(self) -> None:
        if self._runner:
            self._runner.should_exit = True
        if self._thread:
            self._thread.join(timeout=5)

    @staticmethod
    def _find_available_port(host: str) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((host, 0))
            return sock.getsockname()[1]

    def _validate_api_key(self, request: Request) -> None:
        received = request.query_params.get("apikey")
        if received != self.api_key:
            raise HTTPException(status_code=403, detail="invalid api key")

    def _record_request(self, endpoint: str, request: Request) -> None:
        self.recorded.append(
            {
                "endpoint": endpoint,
                "query": dict(request.query_params),
            }
        )

    def _register_routes(self) -> None:
        # ---- Instrument Discovery Endpoints ---- #
        @self.app.get("/" + TestData.URL + "/" + TestData.StockList.ENDPOINT)
        def stock_list(request: Request) -> list[dict[str, Any]]:
            self._validate_api_key(request)
            self._record_request(TestData.StockList.ENDPOINT, request)
            return TestData.StockList.DATA

        @self.app.get("/" + TestData.URL + "/" + TestData.ETFList.ENDPOINT)
        def etf_list(request: Request) -> list[dict[str, Any]]:
            self._validate_api_key(request)
            self._record_request(TestData.ETFList.ENDPOINT, request)
            return TestData.ETFList.DATA

        # ---- Company Domain Endpoints ---- #
        @self.app.get("/" + TestData.URL + "/" + TestData.CompanyProfile.ENDPOINT)
        def profile(request: Request) -> list[dict[str, Any]]:
            self._validate_api_key(request)
            self._record_request(TestData.CompanyProfile.ENDPOINT, request)
            return TestData.CompanyProfile.DATA

        @self.app.get("/" + TestData.URL + "/" + TestData.MarketCap.ENDPOINT)
        def market_cap(request: Request) -> list[dict[str, Any]]:
            self._validate_api_key(request)
            self._record_request(TestData.MarketCap.ENDPOINT, request)
            return TestData.MarketCap.DATA

        @self.app.get("/" + TestData.URL + "/" + TestData.Economics.ENDPOINT)
        def economic_indicators(request: Request) -> list[dict[str, Any]]:
            self._validate_api_key(request)
            self._record_request(TestData.Economics.ENDPOINT, request)
            return TestData.Economics.DATA

        @self.app.get("/" + TestData.URL + "/" + TestData.Error.ENDPOINT)
        def error_endpoint(request: Request) -> None:
            self._validate_api_key(request)
            self._record_request(TestData.Error.ENDPOINT, request)
            raise HTTPException(status_code=500, detail="simulated failure")
