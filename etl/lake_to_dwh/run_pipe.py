import yaml
from scripts.extract import extract_data
from scripts.cleansing import cleanse_data
from scripts.build_dw import create_dims, create_facts
from scripts.load_to_postgres import create_schema

# Define paths
RAW_DATA_PATH = './data/기업신용평가정보_합성데이터.csv'
COLUMN_REFERENCE_PATH = './data/202109_기업CB.csv'
COL_TYPES_PATH = './config/col_types.yaml'
DW_COLUMNS_PATH = './config/dw_columns.yaml'
SCHEMA_SQL_PATH = './etl/lake_to_dwh/schema.sql'

def run_pipeline():
    """
    Runs the entire ETL pipeline.
    """
    print("--- Starting ETL Pipeline ---")


    # 1. Extract data
    print("\nStep 2: Extracting data...")
    df_raw = extract_data(RAW_DATA_PATH, COLUMN_REFERENCE_PATH)
    if df_raw is None:
        print("Data extraction failed. Aborting pipeline.")
        return
    print("Data extraction successful.")


    # 2. Cleanse data
    print("\nStep 3: Cleansing data...")
    cleaned_data = cleanse_data(df_raw, COL_TYPES_PATH)
    print("Data cleansing successful.")


    # 3. Create Schema
    print("\nStep 1: Creating database schema...")
    create_schema(SCHEMA_SQL_PATH)
    print("Schema creation successful.")



    # 4. Build Data Warehouse
    print("\nStep 4: Building Data Warehouse...")
    with open(DW_COLUMNS_PATH, 'r', encoding='utf-8') as f:
        dw_columns = yaml.safe_load(f)
    
    print("  - Creating and loading dimension tables...")
    dim_company, dim_time = create_dims(cleaned_data, dw_columns)
    
    print("  - Creating and loading fact tables...")
    create_facts(cleaned_data, dim_company, dim_time, dw_columns)
    print("Data Warehouse build completed successfully.")
    
    print("\n--- ETL Pipeline Finished ---")

if __name__ == "__main__":
    run_pipeline()


