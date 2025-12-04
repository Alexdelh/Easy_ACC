import pandas as pd
import glob
import os

# --- CONFIGURATION ---
PRODUCERS_FOLDER = "ACC_data/producers/"
PRODUCERS_INDEX = "ACC_data/producers.xlsx"

def load_and_merge_data(folder_path, index_file):
    # 0. Check if Index file exists
    if not os.path.exists(index_file):
        print(f"[ERROR] Index file not found: {index_file}")
        print("Please check the filename and path in CONFIGURATION.")
        return pd.DataFrame()

    # 1. Load the Index
    print(f"Loading index file: {index_file}...")
    try:
        # Auto-detect if it's Excel or CSV
        if index_file.endswith('.xlsx') or index_file.endswith('.xls'):
            index_df = pd.read_excel(index_file, dtype={'Point de livraison': str})
        else:
            # Assume CSV
            index_df = pd.read_csv(index_file, dtype={'Point de livraison': str})
        
        # Clean column names (strip whitespace) just in case
        index_df.columns = index_df.columns.str.strip()

        # Check if the required column exists
        if 'Point de livraison' not in index_df.columns:
            print(f"[ERROR] Column 'Point de livraison' not found in index.")
            print(f"Available columns: {list(index_df.columns)}")
            return pd.DataFrame()

        valid_ids = set(index_df['Point de livraison'].dropna())
        print(f"[SUCCESS] Index loaded. Found {len(valid_ids)} valid producers.")
        
    except Exception as e:
        print(f"[CRITICAL ERROR] Could not read index file: {e}")
        return pd.DataFrame() # Returns empty table instead of None to prevent crash

    all_data_frames = []
    
    # 2. Find all CSV files in the folder
    files = glob.glob(os.path.join(folder_path, "*.csv"))
    print(f"Found {len(files)} CSV files in folder.")
    
    for file_path in files:
        file_name = os.path.basename(file_path)
        
        # Skip the index file itself
        if file_name == index_file:
            continue
            
        # Extract ID (filename without extension)
        consumer_id = os.path.splitext(file_name)[0]
        
        if consumer_id in valid_ids:
            try:
                # 3. Smart Read (comma or semicolon)
                temp_df = pd.read_csv(file_path, sep=None, engine='python')
                
                # 4. Normalize Columns
                rename_map = {
                    'Horodate': 'datetime', 
                    'Valeur': 'W',
                    'Date de début': 'datetime'
                }
                temp_df = temp_df.rename(columns=rename_map)
                
                # Check if columns exist, if not, try reading without header
                if 'datetime' not in temp_df.columns or 'W' not in temp_df.columns:
                     # Try reading without header
                     try:
                        temp_df = pd.read_csv(file_path, sep=None, engine='python', header=None)
                        if len(temp_df.columns) >= 2:
                            temp_df = temp_df.rename(columns={0: 'datetime', 1: 'W'})
                            print(f"[INFO] {file_name}: Read without header, assigned datetime/W to first two columns.")
                     except Exception as e2:
                         print(f"[WARN] {file_name}: Failed to read without header: {e2}")

                if 'datetime' in temp_df.columns and 'W' in temp_df.columns:
                    temp_df = temp_df[['datetime', 'W']]
                    temp_df['producer_id'] = consumer_id
                    all_data_frames.append(temp_df)
                    print(f"[OK] Imported: {file_name}")
                else:
                    print(f"[SKIP] {file_name}: Columns 'datetime'/'W' not found even after headerless retry.")
                    print(f"Columns found: {list(temp_df.columns)}")
                    
            except Exception as e:
                print(f"[ERROR] Reading {file_name}: {e}")
        else:
            # Optional: Uncomment to see skipped files
            # print(f"[IGNORE] {file_name}: ID not in Index.")
            pass

    # 5. Merge
    if all_data_frames:
        return pd.concat(all_data_frames, ignore_index=True)
    else:
        print("No matching data files found.")
        return pd.DataFrame()

# --- EXECUTION ---
if __name__ == "__main__":
    print("\n=== IMPORTING PRODUCERS ===")
    producers_final_df = load_and_merge_data(PRODUCERS_FOLDER, PRODUCERS_INDEX)

    # Inspect
    if not producers_final_df.empty:
        print("\n--- Final Producers Data Structure ---")
        print(producers_final_df.info())
        print(producers_final_df.head())
        
        # Save to CSV
        output_file = 'producers_master.csv'
        producers_final_df.to_csv(output_file, index=False)
        print(f"Saved to {output_file}")
    else:
        print("\n[RESULT] No producer data was loaded.")
