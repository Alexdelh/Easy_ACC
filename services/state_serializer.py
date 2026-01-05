import pandas as pd
import json
import numpy as np

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
            new_dict[k] = serialize_state(v)
        return new_dict
    elif isinstance(state, list):
        return [serialize_state(v) for v in state]
    elif isinstance(state, pd.DataFrame):
        return {
            "__type__": "pd.DataFrame",
            "data": state.to_dict(orient="split")
        }
    elif isinstance(state, pd.Series):
        return {
            "__type__": "pd.Series",
            "data": state.to_dict(),
            "name": state.name
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
                return pd.DataFrame(data["data"], index=data["index"], columns=data["columns"])
            except Exception:
                return pd.DataFrame()
        
        elif state.get("__type__") == "pd.Series":
            try:
                return pd.Series(state["data"], name=state.get("name"))
            except Exception:
                return pd.Series()

        return {k: deserialize_state(v) for k, v in state.items()}
    
    elif isinstance(state, list):
        return [deserialize_state(v) for v in state]
    
    else:
        return state
