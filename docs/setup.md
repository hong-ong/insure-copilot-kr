# 설치·연결·배포 가이드

가온생명 AX 어시스턴트를 처음부터 띄우는 순서입니다. 처음 나오는 용어는 괄호로 설명합니다.

전체 구조
```
브라우저 ── Next.js 화면(web/, Vercel) ──┬── Supabase (로그인 · DB · 파일 · 벡터 검색)
                                        └── AI 백엔드(FastAPI, Hugging Face Spaces) ── Gemini (LiteLLM 경유)
```

---

## 1. 준비물

| 항목 | 위치 | 비고 |
| --- | --- | --- |
| Node.js 24 | `C:\develop\_tools\node` | PATH 미등록 → 쓸 때 `$env:Path = "C:\develop\_tools\node;$env:Path"` |
| uv | `C:\develop\_tools\uv\uv.exe` | Python 패키지 관리자 |
| Gemini API 키 | [Google AI Studio](https://aistudio.google.com/apikey) | 무료 티어. 입력이 모델 개선에 쓰일 수 있으니 실제 개인정보 금지 |
| Supabase 프로젝트 | [supabase.com](https://supabase.com) | 아래 2단계 |

## 2. Supabase 프로젝트

1. **새 프로젝트** 생성 (리전: Seoul `ap-northeast-2`). GLRAM 프로젝트와 섞지 않는다 — 이유는 맨 아래 참고.
2. **스키마 적용** — 둘 중 하나
   - 쉬운 방법: Dashboard → SQL Editor → `supabase/migrations/20261019000000_init.sql` 내용을 붙여 넣고 Run
   - CLI: `C:\Users\jaeho\supabase-cli\supabase.exe db push --db-url "postgresql://postgres.<ref>:<URL인코딩 비번>@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres"`
3. **Authentication → Sign In / Providers**
   - Email: 켜기 (포트폴리오라면 "Confirm email"을 꺼서 바로 가입되게 해도 된다)
   - **Anonymous Sign-Ins: 켜기** ← 데모 체험 버튼이 이걸 쓴다 (익명 로그인 = 가입 없이 임시 계정 발급)
   - Google: Google Cloud Console → OAuth 클라이언트(웹) 생성 → 승인된 리디렉션 URI에 `https://<ref>.supabase.co/auth/v1/callback` → Client ID·Secret을 Supabase에 입력
   - Kakao: [Kakao Developers](https://developers.kakao.com) → 앱 생성 → 카카오 로그인 활성화 → Redirect URI에 `https://<ref>.supabase.co/auth/v1/callback` → **REST API 키**를 Client ID로, 보안 메뉴의 **Client Secret**을 Secret으로 입력. 동의항목에 닉네임·이메일 설정(이메일은 비즈 앱 전환이 필요할 수 있음)
4. **Authentication → URL Configuration**
   - Site URL: 배포한 Vercel 주소 (로컬만 쓸 땐 `http://localhost:3000`)
   - Redirect URLs: `http://localhost:3000/**`, `https://*.vercel.app/**`
5. **Project Settings → API**에서 URL, anon(publishable) 키, service_role(secret) 키를 복사

## 3. 환경변수

```powershell
copy .env.example .env               # AI 백엔드용: GEMINI_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
copy web\.env.example web\.env.local # 화면용: NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL
```
service_role 키는 **서버(.env)에만**. `web/.env.local`에 넣으면 브라우저에 노출된다.

## 4. 로컬 실행

```powershell
$env:Path = "C:\develop\_tools\node;C:\develop\_tools\uv;$env:Path"
uv sync
uv run python scripts/seed_demo.py          # 가상 문서·개정안·회의록 적재 + 데이터 마트 생성 (Gemini 호출 포함, 1~2분)
uv run uvicorn insure_copilot.api.main:app --reload --port 8000
# 새 터미널
cd web; npm install; npm run dev            # http://localhost:3000
```
시드가 끝나면 콘솔에 `변경: 제4조(보상하는 손해) ②항 — 한도 축소` 같은 신구대비 결과가 찍힌다.

## 5. 배포

**AI 백엔드 → Hugging Face Spaces (무료, 메모리 넉넉)**
1. huggingface.co → New Space → SDK **Docker** → Blank → 이름 예: `gaon-ax-api`
2. Space Settings → Variables and secrets에 `.env` 값 등록 (`GEMINI_API_KEY`, `SUPABASE_*`, `CORS_ORIGINS=https://<vercel 주소>`)
3. `bash scripts/deploy_hf.sh <HF 사용자>/gaon-ax-api` → 빌드 로그 확인 → `https://<사용자>-gaon-ax-api.hf.space/health`

**화면 → Vercel**
1. vercel.com → Import Git Repository → `hong-ong/insure-copilot-kr` → **Root Directory: `web`**
2. Environment Variables: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_API_URL=https://<사용자>-gaon-ax-api.hf.space`
3. 배포 주소를 Supabase Site URL과 HF `CORS_ORIGINS`에 반영

무료 플랜 주의 (리스크 레지스터에 기록)
- HF Spaces 무료는 오래 안 쓰면 잠든다 → 첫 요청 30초 이상. 면접·데모 전에 `/health`로 깨워 두기
- Supabase 무료는 7일 미사용 시 일시정지 → 주 1회 접속
- Gemini 무료 티어는 분당·일일 호출 한도가 있다 → 골든셋 평가는 속도 조절

## 6. 실제 계정에 법무팀·관리자 권한 주기

가입 화면에서는 법무팀·AX 관리자를 고를 수 없다(스스로 권한을 올리지 못하게). SQL Editor에서 부여한다.
```sql
update public.profiles set role = 'ax_admin', team = 'ax' where id = (select id from auth.users where email = '내 이메일');
```

## 왜 GLRAM과 같은 Supabase 프로젝트를 쓰지 않나

- **사용자 풀(auth.users)이 하나**다. 공개 데모로 들어오는 익명·가입 사용자가 GLRAM 사용자 목록에 섞이고, 반대도 마찬가지다.
- **인증 설정이 프로젝트 단위**다. 익명 로그인 켜기, Site URL, 리디렉션 URL, 가입 확인 메일 문구·발신자, Google·Kakao 동의 화면 이름이 두 서비스에 공통으로 적용된다.
- **테이블 이름 충돌**: 두 프로젝트 모두 `profiles` 같은 흔한 이름을 쓴다. RLS 정책·마이그레이션 이력도 섞인다.
- 무료 플랜은 조직당 활성 프로젝트 2개까지 무료라, GLRAM 1개 + 이 프로젝트 1개면 추가 비용이 없다.
