
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


    # Recherche automatique d'une plage couvrant une année civile complète
    # On cherche pour chaque année présente dans les données
    years = sorted(set(df.index.year))
    found = False
    for y in years:
        # On accepte un début à 00:00 ou 01:00
        for h in [0, 1]:
            start_candidate = pd.Timestamp(f"{y}-01-01 {h:02d}:00:00")
            end_candidate = pd.Timestamp(f"{y}-12-31 23:00:00")
            if start_candidate in df.index and end_candidate in df.index:
                # On vérifie qu'on a bien toutes les heures entre les deux
                expected_hours = (end_candidate - start_candidate).total_seconds() // 3600 + 1
                df_sub = df.loc[start_candidate:end_candidate]
                if len(df_sub) == expected_hours:
                    df = df_sub.copy()
                    found = True
                    break
        if found:
            break
    if not found:
        raise CalendarAlignmentError(
            "Aucune plage complète du 1er janvier à 00:00/01:00 au 31 décembre 23:00 trouvée dans les données importées."
        )

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
