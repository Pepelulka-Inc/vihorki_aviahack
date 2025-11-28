import pandas as pd
import pyarrow.parquet as pq
import numpy as np
from datetime import datetime, timezone
import json, ast, time

def load_parquet_pandas(path, batch_size=50):
    start = time.time()
    parquet_file = pq.ParquetFile(path)
    df_chunk = next(parquet_file.iter_batches(batch_size=batch_size)).to_pandas()
    print(f"Время чтения {path} : {time.time() - start:.2f} секунд")
    return df_chunk

def normalize_watchid(watch_id):
    """Приводит watchID к единому формату - строковому представлению целого числа"""
    if isinstance(watch_id, (int, np.integer)):
        return str(watch_id)
    elif isinstance(watch_id, float):
        # Преобразуем float через int для точности
        return str(int(watch_id))
    elif isinstance(watch_id, str):
        # Обрабатываем экспоненциальную запись
        if 'e+' in watch_id.lower() or 'e-' in watch_id.lower():
            try:
                # Преобразуем научную нотацию в целое число
                return str(int(float(watch_id)))
            except (ValueError, OverflowError):
                return watch_id
        else:
            # Убираем лишние символы для обычных чисел
            return watch_id.strip().replace("'", "").replace('"', '')
    else:
        return str(watch_id)
    
def read_matching_hits_normalized(hits_path, visits_watchids, batch_size=10000):
    """Читает hits с нормализацией watchID"""
    parquet_file = pq.ParquetFile(hits_path)
    all_matching_hits = []
    
    # Нормализуем watchID из visits
    visits_watchids_normalized = [normalize_watchid(wid) for wid in visits_watchids]
    visits_watchids_set = visits_watchids_normalized
    
    print(f"Поиск {len(visits_watchids_set)} нормализованных watchID")
    
    for i, batch in enumerate(parquet_file.iter_batches(batch_size=batch_size)):
        df_chunk = batch.to_pandas()
        
        # Нормализуем watchID в hits
        df_chunk['ym:pv:watchID'] = df_chunk['ym:pv:watchID'].apply(normalize_watchid)
        
        # Фильтруем по нормализованным watchID
        matching_chunk = df_chunk[df_chunk['ym:pv:watchID'].isin(visits_watchids_set)]
        
        if len(matching_chunk) > 0:
            # Сохраняем оригинальную колонку для совместимости
            all_matching_hits.append(matching_chunk)
            print(f"Чанк {i+1}: найдено {len(matching_chunk)} совпадений")
            
            # Примеры найденных совпадений для проверки
            sample_matches = matching_chunk['ym:pv:watchID'].head(3).tolist()
            print(f"  Примеры найденных watchID: {sample_matches}")
        else:
            print(f"Чанк {i+1}: ничего не найдено!")
        if i == 10:
            break
    
    if all_matching_hits:
        result = pd.concat(all_matching_hits, ignore_index=True)
        print(f"✅ Всего найдено совпадений: {len(result)}")
        return result
    else:
        print("❌ Совпадений не найдено")
        return pd.DataFrame()
    
def explode_and_join(visits_df, hits_df):
    visits = visits_df.copy()
    hits = hits_df.copy()
    
    # Приводим типы и чистим данные
    visits['watchID'] = visits['watchID'].apply(normalize_watchid)
    hits['watchID'] = hits['watchID'].apply(normalize_watchid)
    visits['clientID'] = visits['clientID'].astype(str).str.strip()
    hits['clientID'] = hits['clientID'].astype(str).str.strip()
    
    # Диагностика после explode
    print(f"Размер visits после explode: {len(visits)}")
    print(f"Уникальных watchID в visits после explode: {visits['watchID'].nunique()}")
    
    # Проверяем пересечение watchID
    visits_watchids = set(visits['watchID'].unique())
    hits_watchids = set(hits['watchID'].unique())
    common_watchids = visits_watchids.intersection(hits_watchids)
    
    print(f"Общих watchID: {len(common_watchids)}")
    print(f"WatchID только в visits: {len(visits_watchids - hits_watchids)}")
    print(f"WatchID только в hits: {len(hits_watchids - visits_watchids)}")
    
    # Merge
    joined = visits.merge(
        hits, 
        how='left', 
        on=['watchID', 'clientID'], 
        suffixes=('_visit', '_hit')
    )
    
    # Диагностика после merge
    print(f"Размер после merge: {len(joined)}")
    print(f"Строк с URL (не NaN): {joined['URL'].notna().sum()}")
    print(f"Процент заполнения URL: {joined['URL'].notna().mean() * 100:.2f}%")
    
    # Проверяем примеры данных
    print("\nПримеры watchID из visits (первые 5):")
    print(visits['watchID'].head().tolist())
    print("Примеры watchID из hits (первые 5):")
    print(hits['watchID'].head().tolist())
    
    # Если URL все еще NaN, проверяем конкретные случаи
    if joined['URL'].notna().sum() == 0:
        print("\n⚠️ ВНИМАНИЕ: Все URL равны NaN!")
        print("Проверяем конкретные watchID:")
        sample_watchids = visits['watchID'].head(3).tolist()
        for wid in sample_watchids:
            in_hits = hits[hits['watchID'] == wid]
            print(f"watchID '{wid}': найдено в hits - {len(in_hits)} записей")
    
    # Обработка дат и сортировка
    joined['dateTime_visit'] = pd.to_datetime(joined['dateTime_visit'])
    joined['dateTime_hit'] = pd.to_datetime(joined['dateTime_hit'])
    joined = joined.sort_values(['visitID', 'dateTime_hit'])
    
    return joined

def filter_visits_by_hits(visits, hits_df):
    """
    Удаляет из visits строки с watchID, которых нет в hits
    """
    hits = hits_df.copy()
    
    # Получаем множество существующих watchID в hits
    existing_watchids = set(hits['watchID'].unique())
    print(f"Всего уникальных watchID в hits: {len(existing_watchids)}")
    
    # Фильтруем visits - оставляем только те watchID, которые есть в hits
    initial_count = len(visits)
    visits_filtered = visits[visits['watchID'].isin(existing_watchids)]
    filtered_count = len(visits_filtered)
    
    print(f"Отфильтровано visits: {initial_count} -> {filtered_count} строк")
    print(f"Удалено {initial_count - filtered_count} строк ({((initial_count - filtered_count)/initial_count)*100:.1f}%)")
    
    return visits_filtered.reset_index(drop=True)

def normaliz_vis(visits):
    # Парсим watchIDs
    if isinstance(visits['watchIDs'].iloc[0], str):
        try:
            visits['watchIDs'] = visits['watchIDs'].apply(json.loads)
        except:
            try:
                visits['watchIDs'] = visits['watchIDs'].apply(ast.literal_eval)
            except:
                visits['watchIDs'] = visits['watchIDs'].str.strip("[]").str.replace("'", "").str.split(",")
    # Explode
    visits = visits.explode('watchIDs').rename(columns={'watchIDs': 'watchID'}).reset_index(drop=True)

    # Приводим типы и чистим данные
    visits['watchID'] = visits['watchID'].astype(str).str.strip()
    visits['clientID'] = visits['clientID'].astype(str).str.strip()
    return visits

def downloads():
    visits_norm = load_parquet_pandas("data/2022_yandex_metrika_visits.parquet", 99999)
    visits_norm.columns = visits_norm.columns.str.replace('ym:s:', '', regex=False)
    visits = normaliz_vis(visits_norm.copy())
    hits = read_matching_hits_normalized("data/2022_yandex_metrika_hits.parquet", set(visits['watchID']), 99999)
    hits.columns = hits.columns.str.replace('ym:pv:', '', regex=False)
    visits_filtered = filter_visits_by_hits(visits, hits)
    jo = explode_and_join(visits_filtered, hits)
    return visits_filtered, hits, jo

