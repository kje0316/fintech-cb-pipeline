# ml2/financial_clustering/src/llm_summarizer.py
import yaml
import json
from google import genai
from typing import Dict, Any

def load_llm_config(file_path="config/local_settings.yaml") -> Dict[str, Any]:
    """
    Loads the LLM configuration (API Key and Model ID) from the YAML settings file.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        google_config = config.get("GOOGLE", {})
        api_key = google_config.get("API_KEY")
        model_id = google_config.get("MODEL_ID", "gemini-2.5-flash-Lite")

        if not api_key:
            print("❌ 오류: YAML 파일 내에 GOOGLE.API_KEY가 없습니다.")
            return None
            
        return {"api_key": api_key, "model_id": model_id}

    except FileNotFoundError:
        print(f"오류: 설정 파일({file_path})을 찾을 수 없습니다.")
        return None
    except Exception as e:
        print(f"LLM 설정 로드 중 오류 발생: {e}")
        return None

def generate_analysis_report(json_data: Dict[str, Any], api_key: str, model_id: str) -> str:
    """
    Generates an analysis report from JSON data using the Gemini API (latest client).
    """
    # Initialize the Gemini client
    client = genai.Client(api_key=api_key) # Initialize client with API key

    # Prepare the data and prompt
    data_str = json.dumps(json_data, ensure_ascii=False, indent=2)
    
    prompt = f"""
    당신은 기업 신용 분석 전문가입니다. 아래 JSON 데이터를 분석하여 '기업 진단 리포트'를 작성해주세요.
    
    [분석 가이드라인]
    1. 톤앤매너: 전문적이고 객관적인 어조를 유지하십시오.
    2. 비교 분석: '입력 기업'의 수치를 '소속 군집 평균' 및 '전체 기업 평균'과 비교하여 상대적 위치를 설명하십시오.
    3. 해석: 수치가 단순히 높고 낮음만 말하지 말고, 그것이 재무적으로 무엇을 의미하는지(예: 자산회전율이 낮음 -> 자산 활용 비효율) 설명하십시오.
    4. 구조: [종합 요약] - [부문별 상세 분석] - [핵심 제언] 순서로 작성하십시오.

    [입력 데이터]
    {data_str}
    """

    # Call the model using the new client method
    try:
        response = client.models.generate_content(
            model=model_id,
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"❌ LLM 분석 중 오류가 발생했습니다: {str(e)}"
