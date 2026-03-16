import pandas as pd
import numpy as np
from typing import Tuple

class CalendarAlignmentError(Exception):
    pass




def find_max_common_calendar_range(dfs):
    """
    Trouve la plus grande plage calendaire commune (mois/jour/heure) couvrant une année civile (du 1/1 0h au 31/12 23h) entre plusieurs DataFrames indexés par DatetimeIndex.
    Retourne :
        - start (mois, jour, heure)
        - end (mois, jour, heure)
        - mask_dict : pour chaque df, un masque booléen pour extraire la séquence d'origine correspondant à la plage commune (sans mélanger les années)
    """
    # On cherche la séquence commune du 1/1 0h au 31/12 23h (8760h ou 8736h)
    # On utilise une année non-bissextile (2001) pour la validation,
    # afin que (2,29,h) soit exclu de valid_seq et que la transition
    # (2,28,23) → (3,1,0) soit bien consécutive (1h d'écart).
    target_seq = [(m, d, h) for m in range(1, 13) for d in range(1, 32) for h in range(0, 24)]
    import calendar
    valid_seq = []
    for m, d, h in target_seq:
        try:
            pd.Timestamp(year=2001, month=m, day=d, hour=h)  # 2001 = non-bissextile
            valid_seq.append((m, d, h))
        except Exception:
            continue
    # Pré-calcul des positions dans valid_seq pour test de consécutivité O(1)
    valid_pos = {mdh: i for i, mdh in enumerate(valid_seq)}
    # On tronque à 8760h (année non bissextile) ou 8736h (manque un jour)
    # Pour chaque df, on projette l'index sur (mois, jour, heure)
    sets = []
    for df in dfs:
        idx = df.index
        cal_idx = pd.MultiIndex.from_arrays([idx.month, idx.day, idx.hour], names=["month", "day", "hour"])
        sets.append(set(cal_idx))
    # Intersection calendaire
    common = set.intersection(*sets)
    # On ne garde que la séquence civile complète
    seq = [mdh for mdh in valid_seq if mdh in common]
    # On cherche la plus longue séquence consécutive démarrant au 1/1 0h
    if not seq or seq[0] != (1, 1, 0):
        return None, None, {}
    # On cherche la longueur max de séquence consécutive démarrant au 1/1 0h
    max_len = 0
    cur_len = 0
    for i, mdh in enumerate(seq):
        if i == 0 or valid_pos[mdh] == valid_pos[seq[i - 1]] + 1:
            cur_len += 1
            if cur_len > max_len:
                max_len = cur_len
        else:
            break
    # On accepte si on trouve au moins 8736h (un jour manquant)
    if max_len < 8736:
        return None, None, {}
    # Tronque à 8760h max
    seq = seq[:min(max_len, 8760)]
    best_start = seq[0]
    best_end = seq[-1]
    # Pour chaque df, construire le masque booléen pour extraire la séquence d'origine
    mask_dict = {}
    for i, df in enumerate(dfs):
        idx = df.index
        cal_idx = pd.MultiIndex.from_arrays([idx.month, idx.day, idx.hour], names=["month", "day", "hour"])
        mask = [mdh in seq for mdh in cal_idx]
        mask_dict[i] = pd.Series(mask, index=df.index)
    return best_start, best_end, mask_dict

def align_curve_to_reference_year(df: pd.DataFrame, reference_year: int) -> pd.DataFrame:
    """
    Réaligne une courbe horaire sur une année de référence en conservant la correspondance des jours de la semaine.
    - df : DataFrame indexé par DatetimeIndex, colonne 'value'.
    - reference_year : année cible pour l'alignement.
    Retourne un DataFrame réaligné (8760 valeurs, 365 jours).
    Lève CalendarAlignmentError si la courbe n'est pas sur une année complète.
    """


    # Recherche d'une plage de 364 jours consécutifs (8736 heures)
    # On cherche la plus longue séquence continue d'heures sans trou
    df_sorted = df.sort_index()
    # On crée une série d'heures attendues à partir de la première à la dernière date
    full_range = pd.date_range(start=df_sorted.index.min(), end=df_sorted.index.max(), freq='h')
    # On repère les plages continues
    mask = df_sorted.index.isin(full_range)
    # On réindexe pour avoir les NaN là où il manque des heures
    df_full = df_sorted.reindex(full_range)
    # On cherche la plus longue séquence sans NaN
    max_len = 0
    best_start = None
    best_end = None
    current_start = None
    current_len = 0
    for ts, val in df_full['value'].items():
        if not pd.isna(val):
            if current_start is None:
                current_start = ts
                current_len = 1
            else:
                current_len += 1
            if current_len > max_len:
                max_len = current_len
                best_start = current_start
                best_end = ts
        else:
            current_start = None
            current_len = 0
    # On accepte si on trouve au moins 8736 heures consécutives (364 jours)
    if max_len < 8736:
        raise CalendarAlignmentError(
            f"Aucune plage de 364 jours consécutifs (8736h) trouvée dans les données importées. Max trouvé : {max_len}h."
        )

    # Déterminer l'année source à partir du début de la meilleure plage
    src_year = best_start.year

    # Reconstruire un index complet pour l'année source (01/01 00:00 → 31/12 23:00).
    # Ceci garantit que toute heure absente (y compris 01/01 00:00 si elle était supprimée
    # lors de l'import) se retrouve bien à sa position calendaire correcte en tant que NaN,
    # et non décalée à la fin après l'alignement.
    src_is_leap = (src_year % 4 == 0 and (src_year % 100 != 0 or src_year % 400 == 0))
    src_full_index = pd.date_range(
        start=f"{src_year}-01-01 00:00:00",
        end=f"{src_year}-12-31 23:00:00",
        freq="h"
    )
    df = df_full.reindex(src_full_index)
    # Supprimer le 29 février pour normaliser à 8760h si l'année source est bissextile
    if src_is_leap:
        df = df[~((df.index.month == 2) & (df.index.day == 29))]

    # Trouver le jour de la semaine du 1er janvier de l'année de référence
    ref_start = pd.Timestamp(f"{reference_year}-01-01 00:00:00")
    ref_weekday = ref_start.weekday()  # 0 = lundi

    # Trouver le jour de la semaine du 1er janvier de l'année source
    src_weekday = pd.Timestamp(f"{src_year}-01-01").weekday()

    # Décalage à appliquer (en jours entiers)
    shift_days = (ref_weekday - src_weekday) % 7
    shift_hours = shift_days * 24

    # Décalage circulaire : les valeurs sont pivotées, les NaN restent à leur position relative
    values = df['value'].values  # toujours 8760 valeurs
    values_aligned = pd.Series(values.copy())
    if shift_hours > 0:
        values_aligned = pd.concat([
            pd.Series(values[-shift_hours:]),
            pd.Series(values[:-shift_hours])
        ], ignore_index=True)
    elif shift_hours < 0:
        values_aligned = pd.concat([
            pd.Series(values[-shift_hours:]),
            pd.Series(values[:-shift_hours])
        ], ignore_index=True)
    # shift_hours == 0 : pas de décalage, values_aligned = values

    # Générer le nouvel index couvrant exactement l'année de référence (toujours 8760h)
    # Pour une année de référence bissextile, on supprime le 29 février pour rester à 8760h.
    ref_is_leap = (reference_year % 4 == 0 and (reference_year % 100 != 0 or reference_year % 400 == 0))
    new_index = pd.date_range(
        start=ref_start,
        end=f"{reference_year}-12-31 23:00:00",
        freq="h"
    )
    if ref_is_leap:
        new_index = new_index[~((new_index.month == 2) & (new_index.day == 29))]
    df_aligned = pd.DataFrame({'value': values_aligned.values}, index=new_index)

    return df_aligned
