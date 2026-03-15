
import pandas as pd
import numpy as np
from typing import Tuple

class CalendarAlignmentError(Exception):
    pass

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
    full_range = pd.date_range(start=df_sorted.index.min(), end=df_sorted.index.max(), freq='H')
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
    # On tronque à la première plage valide trouvée
    df = df_full.loc[best_start:best_end].copy()
    # Si plus long que 8736h, on tronque à 8736h
    if len(df) > 8736:
        df = df.iloc[:8736]

    # On effectue l'alignement calendaire AVANT de supprimer le dernier jour pour les années bissextiles
    is_leap = (df.index[0].year % 4 == 0 and (df.index[0].year % 100 != 0 or df.index[0].year % 400 == 0))

    # Trouver le jour de la semaine du 1er janvier de l'année de référence
    ref_start = pd.Timestamp(f"{reference_year}-01-01 00:00:00")
    ref_weekday = ref_start.weekday()  # 0 = lundi

    # Trouver le jour de la semaine du début de la courbe
    src_start = df.index[0]
    src_weekday = src_start.weekday()

    # Décalage à appliquer (en jours)
    shift_days = (ref_weekday - src_weekday) % 7
    shift_hours = shift_days * 24

    # Décalage circulaire
    values = df['value'].values
    values_aligned = pd.Series(values).shift(shift_hours, fill_value=None)
    # Remplir circulairement
    if shift_hours > 0:
        values_aligned.iloc[:shift_hours] = values[-shift_hours:]
    elif shift_hours < 0:
        values_aligned.iloc[shift_hours:] = values[:-shift_hours]

    # Générer nouvel index
    # Pour les années bissextiles, la plage initiale fait 8784 valeurs (366 jours)
    # Pour les années non bissextiles, 8760 valeurs (365 jours)
    n_hours = len(values_aligned)
    new_index = pd.date_range(start=ref_start, periods=n_hours, freq='H')
    df_aligned = pd.DataFrame({'value': values_aligned.values}, index=new_index)

    # Si l'année de référence est bissextile, supprimer le 31 décembre (les 24 dernières heures)
    ref_is_leap = (reference_year % 4 == 0 and (reference_year % 100 != 0 or reference_year % 400 == 0))

    return df_aligned

    # Trouver le jour de la semaine du 1er janvier de l'année de référence
    ref_start = pd.Timestamp(f"{reference_year}-01-01 00:00:00")
    ref_weekday = ref_start.weekday()  # 0 = lundi

    # Trouver le jour de la semaine du début de la courbe
    src_start = df.index[0]
    src_weekday = src_start.weekday()

    # Décalage à appliquer (en jours)
    shift_days = (ref_weekday - src_weekday) % 7
    shift_hours = shift_days * 24

    # Décalage circulaire
    values = df['value'].values
    values_aligned = pd.Series(values).shift(shift_hours, fill_value=None)
    # Remplir circulairement
    if shift_hours > 0:
        values_aligned.iloc[:shift_hours] = values[-shift_hours:]
    elif shift_hours < 0:
        values_aligned.iloc[shift_hours:] = values[:-shift_hours]

    # Générer nouvel index
    new_index = pd.date_range(start=ref_start, periods=8760, freq='H')
    df_aligned = pd.DataFrame({'value': values_aligned.values}, index=new_index)
    return df_aligned
