# Backend Model Store

학습된 ML 모델 파일 저장 위치입니다.

## Contents

- `risk_scorer.pkl`: XGBoost risk model
- `risk_scaler.pkl`: feature scaler
- `prophet_{area_cd}.pkl`: area-specific Prophet forecast model
- `*_meta.json`: model metadata written by `ModelStore`

`*.pkl` 파일은 Git에 포함하지 않습니다. 빈 디렉토리 유지를 위해 `.gitkeep`만 커밋합니다.
