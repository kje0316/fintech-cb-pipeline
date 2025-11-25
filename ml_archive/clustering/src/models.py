# ml/clustering/src/models.py
from sklearn.cluster import KMeans, DBSCAN
# 추가적인 클러스터링 모델 임포트 가능

def get_model(config: dict):
    """
    설정 파일에 정의된 모델 타입과 파라미터에 따라
    scikit-learn 모델 객체를 생성하고 반환합니다.
    """
    model_config = config['model']
    model_type = model_config.get('type')
    params = model_config.get('params', {})
    
    print(f"Initializing model: {model_type} with params: {params}")
    
    if model_type == 'KMeans':
        model = KMeans(**params)
    elif model_type == 'DBSCAN':
        model = DBSCAN(**params)
    # 다른 모델 추가 시 여기에 'elif' 구문 추가
    else:
        raise ValueError(f"Unsupported model type: {model_type}")
        
    return model
