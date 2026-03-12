
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

    # Vérification de la plage temporelle (accepte 01:00 ou 00:00 en début)
    start = df.index.min()
    end = df.index.max()
    is_leap = (start.year % 4 == 0 and (start.year % 100 != 0 or start.year % 400 == 0))
    expected_start_0 = pd.Timestamp(f"{start.year}-01-01 00:00:00")
    expected_start_1 = pd.Timestamp(f"{start.year}-01-01 01:00:00")
    expected_end = pd.Timestamp(f"{start.year}-12-31 23:00:00")
    if (start == expected_start_1 and end == expected_end and len(df) == 8759):
        # Imputation automatique d'une valeur manquante au début
        df = pd.concat([
            pd.DataFrame({'value': [np.nan]}, index=[expected_start_0]),
            df
        ])
    elif (start == expected_start_0 or start == expected_start_1) and end > expected_end:
        # Tronquer à la première année civile complète
        df = df.loc[start:expected_end]
        # Si on a commencé à 01:00, imputer la première valeur
        if start == expected_start_1 and len(df) == 8759:
            df = pd.concat([
                pd.DataFrame({'value': [np.nan]}, index=[expected_start_0]),
                df
            ])
    elif (start != expected_start_0 and start != expected_start_1) or end < expected_end:
        raise CalendarAlignmentError(f"La courbe doit commencer le {expected_start_0} ou {expected_start_1} et contenir au moins une année complète jusqu'au {expected_end} (trouvé {start} à {end}).")

    # Si bissextile, tronquer à 365 jours
    if is_leap:
        df = df.iloc[:8760]

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
