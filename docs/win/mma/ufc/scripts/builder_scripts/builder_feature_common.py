from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

_COMMON_PATH = (
    Path(__file__).resolve().parents[1]
    / "01_feature_engineering"
    / "ufc_feature_common.py"
)
_SPEC = spec_from_file_location("ufc_feature_common_shared", _COMMON_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Unable to load shared feature helpers from {_COMMON_PATH}")

_MODULE = module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

build_master_indexes = _MODULE.build_master_indexes
diff = _MODULE.diff
get_rolling_stats = _MODULE.get_rolling_stats
get_sos = _MODULE.get_sos
implied_prob = _MODULE.implied_prob
parse_dob = _MODULE.parse_dob
parse_height_inches = _MODULE.parse_height_inches
parse_reach = _MODULE.parse_reach
summarize_historical_fights = _MODULE.summarize_historical_fights
