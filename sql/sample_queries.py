import requests

# 사용자 정보
SUPABASE_URL = "https://uwykuxiuytgqfwlzlmlf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV3eWt1eGl1eXRncWZ3bHpsbWxmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NzkzMDIwMCwiZXhwIjoyMDgzNTA2MjAwfQ.7PHZCtzhZKrHyqOpHoBeVV8cm4xqOseIP9RSsd-i0Xo"

def check_health():
    print(f"Target Project: {SUPABASE_URL}")
    
    # 1. PostgREST 상태 체크 (인증 없이 가능)
    # 이 URL은 Supabase DB가 살았는지 죽었는지 알려줍니다.
    health_url = f"{SUPABASE_URL}/rest/v1/"
    
    try:
        # service_role 키를 헤더에 넣어서 요청
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}"
        }
        response = requests.get(health_url, headers=headers)
        
        print(f"\nResponse Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ [SUCCESS] 프로젝트가 깨어있습니다! 연결 성공.")
            print("이제 add_skilltable.py를 실행해도 좋습니다.")
        elif response.status_code == 503:
            print("💤 [PAUSED] 프로젝트가 일시 정지(Paused) 상태입니다.")
            print("Supabase 대시보드에서 'Restore' 버튼을 눌러 깨워주세요.")
        elif response.status_code == 403:
            print("🚫 [FORBIDDEN] WAF(방화벽)나 IP 차단일 수 있습니다.")
        else:
            print(f"⚠️ [UNKNOWN] 알 수 없는 상태입니다. (응답: {response.text})")
            
    except Exception as e:
        print(f"❌ [FAIL] 네트워크 연결 실패: {e}")

if __name__ == "__main__":
    check_health()
    