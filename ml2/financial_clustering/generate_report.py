import pandas as pd
import numpy as np
import os
import argparse
import json
from datetime import datetime

from .src.data_loader import load_config, load_yaml_map
from .src.predictor import Predictor

def generate_report(config: dict, predictor: Predictor, df_input: pd.DataFrame):
    """
    Generates a structured diagnosis report for a single input company.
    """
    # --- 1. Predict and get basic info ---
    if len(df_input) > 1:
        print("Warning: Input CSV contains more than one row. Using the first row for the report.")
        df_input = df_input.head(1)
        
    df_predicted = predictor.predict(df_input.copy())
    
    predicted_cluster = df_predicted['predicted_cluster'].iloc[0]
    company_id = df_predicted['COMPANY_ID'].iloc[0] if 'COMPANY_ID' in df_predicted.columns else 'N/A'
    bs_dt = df_predicted['BS_DT'].iloc[0] if 'BS_DT' in df_predicted.columns else datetime.now().strftime('%Y-%m-%d')

    print(f"\nInput company assigned to: Cluster {predicted_cluster}")
    
    # --- 2. Load cluster aliases and full dataset ---
    aliases = load_yaml_map(os.path.join('ml2/financial_clustering/configs', 'cluster_aliases.yaml'))
    cluster_alias = aliases.get(predicted_cluster, "분류되지 않은 군집")

    full_data_path = os.path.join(config['paths']['output_dir'], config['experiment_name'], 'final_clustered_data.csv')
    df_full = pd.read_csv(full_data_path)

    # --- 3. Calculate profiles ---
    key_metrics_map = config['profiling']['key_metrics']
    key_metrics = list(key_metrics_map.keys())
    df_non_noise = df_full[df_full['Cluster'] != -1]

    profile_input_processed = df_predicted[key_metrics].iloc[0] # Values after cleansing
    
    # Ensure df_input has all key_metrics columns, fill with NaN if missing
    for col in key_metrics:
        if col not in df_input.columns:
            df_input[col] = np.nan
    profile_input_raw = df_input[key_metrics].iloc[0] # Raw values from original input

    profile_overall_avg = df_non_noise[key_metrics].mean()
    
    if predicted_cluster != -1:
        df_cluster = df_full[df_full['Cluster'] == predicted_cluster]
        profile_cluster_avg = df_cluster[key_metrics].mean()
    else:
        profile_cluster_avg = pd.Series(np.nan, index=key_metrics) # Use NaN for noise cluster

    # --- 4. Build Markdown Report ---
    report_md = f"# AI 기업 진단 리포트\n\n"
    report_md += f"- **기업 ID**: {company_id}\n"
    report_md += f"- **분석 기준일**: {bs_dt}\n\n"
    report_md += "---\n\n"

    # --- 4A. Add Raw Input Data Section ---
    report_md += "## 입력 데이터 원본 (주요 지표)\n\n"
    df_input_raw_metrics = df_input[key_metrics].T
    df_input_raw_metrics.columns = ['입력값']
    df_input_raw_metrics.index = [key_metrics_map.get(c, c) for c in df_input_raw_metrics.index]
    report_md += df_input_raw_metrics.to_markdown(floatfmt=",.2f")
    report_md += "\n\n---\n\n"

    report_md += "## 종합 진단 결과\n\n"
    report_md += f"- **귀속 군집**: Cluster {predicted_cluster} - \"{cluster_alias}\"\n"
    
    # Simple interpretation for summary
    input_rank = (profile_input_processed > profile_cluster_avg).astype(int).sum()
    peer_group_size = len(key_metrics)
    summary_text = f"동일 군집 내 다른 기업들과 비교 시, {peer_group_size}개의 주요 지표 중 {input_rank}개에서 평균 이상을 기록했습니다."
    if predicted_cluster == -1:
        summary_text = "이 기업은 일반적인 재무 패턴에서 벗어난 특성을 보여 특정 군집으로 분류되지 않았습니다."

    report_md += f"- **요약**: {summary_text}\n\n"
    report_md += "---\n\n"
    report_md += "## 주요 재무 지표 벤치마크\n\n"
    
    # Create and format the benchmark table
    df_benchmark = pd.DataFrame({
        "입력 기업 (처리 후)": profile_input_processed,
        "소속 군집 평균": profile_cluster_avg,
        "전체 기업 평균": profile_overall_avg
    })
    df_benchmark.index = [key_metrics_map.get(c, c) for c in df_benchmark.index]
    report_md += df_benchmark.to_markdown(floatfmt=",.2f")
    report_md += "\n\n---\n\n"
    
    # --- 5. Build JSON for LLM ---
    llm_data = {
        "company_id": str(company_id),
        "analysis_date": str(bs_dt),
        "cluster_id": int(predicted_cluster),
        "cluster_alias": cluster_alias,
        "input_company_raw_metrics": profile_input_raw[key_metrics].to_dict(), # Added raw input metrics
        "summary_table": df_benchmark.reset_index().rename(columns={'index': 'metric'}).to_dict('records'),
        "interpretation_guideline": "You are an expert corporate credit analyst. Based on the provided summary table, write a short, easy-to-understand diagnosis of the company's financial health. The company's profile should be compared against its peer group (Cluster Average) and the overall market (Overall Average). Highlight its key strengths and weaknesses."
    }
    
    report_md += "## LLM 프롬프트용 데이터 (JSON)\n\n"
    report_md += f"```json\n{json.dumps(llm_data, indent=2, ensure_ascii=False)}\n```\n"

    # --- 6. Save Report ---
    report_dir = os.path.join(config['paths']['report_dir'], config['experiment_name'])
    os.makedirs(report_dir, exist_ok=True)
    report_filename = f"diagnosis_report_{company_id}.md"
    save_path = os.path.join(report_dir, report_filename)
    
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(report_md)
        
    print(f"\n진단 리포트가 성공적으로 생성되었습니다: {save_path}")

def main():
    parser = argparse.ArgumentParser(description="Generate a structured diagnosis report for a company.")
    parser.add_argument('input_csv', type=str, help="Path to the input CSV file with a single company's data.")
    parser.add_argument('--experiment', type=str, default='final_notebook_model', help="Name of the trained experiment model to use.")
    args = parser.parse_args()

    if not os.path.exists(args.input_csv):
        print(f"Error: Input file not found at {args.input_csv}")
        return

    predictor = Predictor(args.experiment)
    df_input = pd.read_csv(args.input_csv)
    df_input.columns = [col.upper() for col in df_input.columns] # Standardize column names
    
    generate_report(predictor.config, predictor, df_input)

if __name__ == '__main__':
    main()
