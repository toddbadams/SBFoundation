**class TickerState:**

    ticker: NormalizedTicker

    table: TickerTable

    process: Process

    layer: DataLayer   

&nbsp;   dates\_loaded: list\[DateTime]



**class BronzeLayerTickerState(TickerState):**

&nbsp;   partition\_dates: list\[str]

&nbsp;   last\_check\_date: str

&nbsp;   next\_check\_date: str

&nbsp;   last\_payload\_hash: str

&nbsp;   url: str (no api key)



**class SilverLayerTickerState(TickerState):**

&nbsp;  partition\_dates: list\[str]

&nbsp;  dates\_validated: list\[str]



**class GoldLayerTickerState(TickerState):**





**TickerStateService**

    **BronzeLayerTickerStates\_due**(self, process: Process) -> list\[**BronzeLayerTickerState**]

    **SilverLayerTickerStates\_due**(self, process: Process) -> list\[**SilverLayerTickerState**]

    **GoldLayerTickerStates\_due**(self, process: Process) -> list\[**GoldLayerTickerState**]

&nbsp;   save\_state(self, state: TickerState)





**class Process(Enum):**

&nbsp;   INJEST\_QTR\_FINANCIALS = auto()

&nbsp;   INJEST\_DAILY\_PRICE = auto()

&nbsp;   VALIDATE\_QTR\_FINANCIALS = auto()

&nbsp;   VALIDATE\_DAILY\_PRICE = auto()

&nbsp;   CONSOLIDATE\_STOCKS = auto()

&nbsp;   CONSOLIDATE\_QTR\_FINANCIALS = auto()

&nbsp;   CONSOLIDATE\_DAILY\_PRICE = auto()



**class TickerTable(Enum):**

&nbsp;   TIME\_SERIES\_DAILY\_ADJUSTED = auto()

&nbsp;   CASH\_FLOW = auto()

    BALANCE\_SHEET = auto()

    DIVIDENDS = auto()

    EARNINGS = auto()

    INCOME\_STATEMENT = auto()

    OVERVIEW = auto()

    FACT\_QTR\_FINANCIALS = auto()

&nbsp;   FACT\_DAILY\_STOCK\_PRICE = auto()

&nbsp;   DIM\_STOCKS = auto()



**class DataLayer(Enum):**

&nbsp;   BRONZE = auto()

&nbsp;   SILVER = auto()

&nbsp;   GOLD = auto()







