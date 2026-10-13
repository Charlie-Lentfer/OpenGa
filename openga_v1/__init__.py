"""OpenGa v1 — techno-economic and carbon model for primary gallium recovery
from an Australian Bayer liquor slipstream.

Backend for the Streamlit interface in ``app/streamlit_app.py``. Every number
traces to ``OpenGa_v3.3_Carbon.xlsx``; the legacy WP3/WP4 behaviour is retained
behind explicit mode switches so the earlier figures can be reproduced.
"""
from . import (config, meb, equipment, capex, opex, allocation, energy,
               carbon, finance, policy, engine)  # noqa: F401

__all__ = ["config", "meb", "equipment", "capex", "opex", "allocation",
           "energy", "carbon", "finance", "policy", "engine"]
__version__ = "1.0.0"
