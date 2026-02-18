# Compatibility alias: ForexListDTO was moved to sbfoundation.dtos.fx.fx_list_dto
# Bronze files written before this rename store the old module path and must
# still resolve during recovery via BronzeToSilverDTO.ty() / importlib.import_module.
from sbfoundation.dtos.fx.fx_list_dto import FxListDTO as ForexListDTO

__all__ = ["ForexListDTO"]
