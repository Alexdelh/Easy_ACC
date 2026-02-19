import pandas as pd
import json
import numpy as np
from io import StringIO
from datetime import datetime

def serialize_state(state):
    """
    Recursively serialize a dictionary (state) into a JSON-compatible format.
    Handles pandas DataFrames by converting them to dictionaries with metadata.
    """
    if isinstance(state, dict):
        new_dict = {}
        # Keys to exclude from persistence (transient widgets)
        exclude_prefixes = ("prev_", "next_", "load_", "del_", "delete_", "confirm_", "edit_", "dup_", "upload_", "FormSubmitter")
        
        for k, v in state.items():
            # Skip keys that are transient widgets
            if isinstance(k, str) and (k.startswith(exclude_prefixes) or k == "use_container_width"):
                continue
            # Ensure key is a string (JSON requirement)
            new_dict[str(k)] = serialize_state(v)
        return new_dict
    elif isinstance(state, list):
        return [serialize_state(v) for v in state]
    elif isinstance(state, pd.DataFrame):
        return {
            "__type__": "pd.DataFrame",
            "data": state.to_json(orient="split", date_format="iso")
        }
    elif isinstance(state, pd.Series):
        return {
            "__type__": "pd.Series",
            "data": state.to_json(orient="split", date_format="iso"),
            "name": str(state.name) if state.name is not None else None
        }
    elif isinstance(state, (pd.Timestamp, datetime)):
        return {
            "__type__": "datetime",
            "data": state.isoformat()
        }
    elif isinstance(state, (np.int64, np.int32)):
        return int(state)
    elif isinstance(state, (np.float64, np.float32)):
        return float(state)
    else:
        try:
            json.dumps(state)
            return state
        except (TypeError, OverflowError):
            return str(state)

def deserialize_state(state):
    """
    Recursively deserialize a JSON-compatible structure back into original objects.
    Reconstructs pandas DataFrames from the custom dictionary format.
    """
    if isinstance(state, dict):
        if state.get("__type__") == "pd.DataFrame":
            try:
                data = state["data"]
                # New format: JSON string with ISO dates
                if isinstance(data, str):
                    return pd.read_json(StringIO(data), orient="split")
                # Legacy format: Dictionary
                else:
                    return pd.DataFrame(data["data"], index=data["index"], columns=data["columns"])
            except Exception:
                return pd.DataFrame()
        
        elif state.get("__type__") == "pd.Series":
            try:
                data = state["data"]
                # New format: JSON string
                if isinstance(data, str):
                    s = pd.read_json(StringIO(data), orient="split", typ="series")
                    s.name = state.get("name")
                    return s
                # Legacy format: Dictionary
                else:
                    return pd.Series(state["data"], name=state.get("name"))
            except Exception:
                return pd.Series()
        
        elif state.get("__type__") == "datetime":
            try:
                # Return pandas Timestamp as it is more versatile and compatible with datetime
                return pd.Timestamp(state["data"])
            except Exception:
                return None

        return {k: deserialize_state(v) for k, v in state.items()}
    
    elif isinstance(state, list):
        return [deserialize_state(v) for v in state]
    
    else:
        return state
