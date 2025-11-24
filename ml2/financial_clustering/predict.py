import pandas as pd
import os
import argparse

# Import the Predictor class from the src library
from .src.predictor import Predictor

def main():
    """
    Command-line interface for predicting clusters for new company data.
    """
    parser = argparse.ArgumentParser(description="Predict clusters for new company data using a trained experiment model.")
    parser.add_argument(
        'input_csv', 
        type=str, 
        help="Path to the input CSV file with company data."
    )
    parser.add_argument(
        '--experiment', 
        type=str, 
        default='hdbscan_betavae', 
        help="Name of the trained experiment model to use for prediction (e.g., 'gmm_vae')."
    )
    args = parser.parse_args()

    if not os.path.exists(args.input_csv):
        print(f"Error: Input file not found at {args.input_csv}")
        return

    # Initialize the predictor for the specified experiment
    predictor = Predictor(experiment_name=args.experiment)

    # Load new data from CSV
    print(f"Loading new data from {args.input_csv}...")
    df_to_predict = pd.read_csv(args.input_csv)
    df_to_predict.columns = [col.upper() for col in df_to_predict.columns] # Standardize column names

    # Perform prediction
    df_results = predictor.predict(df_to_predict)

    # Save results
    base_name = os.path.splitext(args.input_csv)[0]
    output_filename = f'{base_name}_predictions_{args.experiment}.csv'
    df_results.to_csv(output_filename, index=False, encoding='utf-8-sig')
    print(f"Predictions saved to {output_filename}")


if __name__ == '__main__':
    main()
