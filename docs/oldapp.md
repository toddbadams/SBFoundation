import streamlit as st

from strawberry.services.app_srv import AppServices
from strawberry.ui.views.base_view import BaseView
from strawberry.ui.views.data_view import DataView
from strawberry.ui.views.screener_view import ScreenerView
from strawberry.logging.logger_factory import LoggerFactory
from strawberry.ui.views.stock_view import StockView


class DataApp(BaseView):
    # Class‐level constants
    def __init__(self, logger_factory: LoggerFactory = None, service: AppServices = None):
        super().__init__(service, logger_factory)

        # instantiate each view
        self.screener_view = ScreenerView()
        self.stock_view = StockView()
        self.data_view = DataView()

        # wire them up to navigation, now with explicit URL paths
        self.st_pages = [
            st.Page(self.screener_view.render, title=self.PAGES[0], url_path=self.URLs[0]),
            st.Page(self.stock_view.render, title=self.PAGES[1], url_path=self.URLs[1]),
            st.Page(self.data_view.render, title=self.PAGES[2], url_path=self.URLs[2]),
        ]

    def render(self):
        self.logger.info(f"Rendering {self.__class__.__name__}")
        # App‐wide page config
        st.set_page_config(page_title=self.PAGE_TITLE, layout="wide")

        # Sidebar navigation (automatically sets ?page=<url_path>)
        sel_page = st.navigation(self.st_pages, position="sidebar")

        # Push the chosen page’s title into AppServices, then render it
        self.app_service.current_page_title = sel_page.title
        st.title(self.app_service.current_page_title)

        if sel_page.url_path == "data-viewer":
            # Let the user pick which section they want
            section = st.sidebar.radio("Data layer", self.SECTIONS)
            st.query_params["section"] = section

            # Load the appropriate DataFrame based on section
            if section in ["Bronze", "Silver"]:
                # Pick one of the acquisition/validation tables
                table = st.sidebar.radio("Select table", self.app_service.acq_tables)
                if section == "Acquired":
                    df = self.app_service.acq_repo.read(table, partition={"symbol": self.app_service.selected_ticker})
                else:
                    df = self.app_service.val_repo.read(table, partition={"symbol": self.app_service.selected_ticker})

            if section in ["Gold"]:
                # Dimensions branch: some dims are global, some per‐ticker
                table = st.sidebar.selectbox("Select dimension", self.DIMENSIONS)
                if table == "DIM_STOCKS":
                    df = self.app_service.dim_repo.read(table)
                else:
                    df = self.app_service.dim_repo.read(table, partition={"symbol": ticker})

        # Finally invoke the selected view’s render()
        sel_page.run()


if __name__ == "__main__":
    app = DataApp()
    app.render()
