#!/bin/bash
echo "================================================="
echo "무한매수법 V4.0 외부 접속용 터널(Cloudflare) 구동기"
echo "================================================="

if ! command -v cloudflared &> /dev/null
then
    echo "cloudflared 패키지가 설치되어 있지 않습니다."
    echo "설치 명령어: brew install cloudflare/cloudflare/cloudflared"
    echo "설치 후 다시 실행해 주세요."
    exit 1
fi

echo "포트 8081 번을 개방하여 임시 URL을 발급받습니다..."
echo "아래 출력되는 https://xxxx.trycloudflare.com 주소를 휴대폰에 입력하세요."
echo "터미널 창을 닫으면 접속이 끊어집니다."
echo "-------------------------------------------------"

cloudflared tunnel --url http://127.0.0.1:8081
