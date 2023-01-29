# [TEAM R] R-Image-Processing

이 Repository는 "Freeze 프로젝트"의 이미지 Edge Detection 및 Backend Datastore 연동을 담당하는 Repository입니다.

다음과 같은 기능이 포함되어 있습니다.
- Flask API 서버를 동작시킴
- API를 통해 전달받은 이미지의 크기를 식별하고 마스킹하여 해상도를 1080x1080으로 조정함
- 이미지의 Edge를 추출하고, Project Freeze 로고 색으로 변환하며 뒷 배경을 투명 처리
- 전달받은 Original 이미지와 Edge를 S3 저장소에 적재하고, 메타데이터를 RDS postgresql에 저장


## 프로젝트에서 사용한 기술

본 Repository는 `Flask`, `boto3`, `werkzeug`, `pillow`, `openCV`, `psycopg2` 오픈소스 패키지를 사용하였습니다.
- `Flask`: API를 수신하여 동작하기 위해 사용
- `boto3`: S3 데이터스토어에 접근하기 위해 사용
- `werkzeug`: 파일 경로의 보안을 증진시키기 위해 사용
- `pillow`: 이미지 처리할 때 사용
- `openCV`: Edge를 추출할 수 있는 Canny 알고리즘 등 이미지 처리에 사용
- `psycopg2`: postgres 데이터스토어에 편리하게 접근하기 위해 사용


## Dev Server 실행 방법

1. 본 Repository를 로컬 환경에 Clone 받습니다.
2. 동일 위치에 DB정보, credential이 담겨 있는 config.py를 생성합니다.
3. import한 라이브러리들(`opencv-python, flask, image, boto3, psycopg2, numpy`)을 설치합니다.
4. python을 이용하여 detect_edge.py의 flask app을 실행합니다.
5. 지정한 포트로 API를 이용하여 이미지를 전달합니다.(freeze 앱 기능으로 사진 촬영 시 전달됨 !)
6. S3 및 postgres에 적재되는 데이터를 확인합니다.


## Production 배포 방법

본 프로젝트는 배포하지 않았습니다.

## 환경 변수 및 시크릿

프로젝트 실행 파일과 동일한 위치에 config.py를 작성합니다.
config.py는 다음을 포함합니다.
1. AWS_ACCESS_KEY
2. AWS_SECRET_KEY
3. BUCKET_NAME
4. DB_host
5. DB_name
6. DB_user
7. DB_password
8. DB_port

flask API로 전달되는 이미지 파일은, 지정된 포트(기본은 8080)의 `/image`로 전달되어야 합니다.
전달 시 `Headers`에는 `Content-Type=multipart/form-data`를 포함해야 합니다.
이 때 Body에는 KEY `user_file`에 VALUE {이미지 파일명}이 전달되어야 합니다.

## 기타

본 코드에서 Edge를 추출하는 Threshold는, 기본적으로 810X1080(3:4 비율)에 최적화되어 있으나, 다양한 휴대폰의 해상도를 지원하기 위해 현재는 프로토타입으로 1:1 배율을 중심으로 작성되어 있음
추후 AI 모델을 도입하여 학습시키거나 하는 방법으로 최적의 Threshold를 산출할 수 있는 방안을 마련할 것임
