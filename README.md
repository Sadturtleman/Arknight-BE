# Arknights Database (KR) – Web Service Dataset

명일방주(Arknights) 웹 사이트 구축을 위해  
공식 게임 데이터(JSON)를 수집·정규화하여 **PostgreSQL 기반 데이터베이스**로 설계한 프로젝트입니다.

본 데이터베이스는 **Supabase(PostgreSQL)** 환경에서 배포 및 운영을 전제로 합니다.

---

## 📌 프로젝트 개요

- **목적**
  - 명일방주 캐릭터, 스킬, 사거리, 스킨, 모듈, 아이템 정보를 구조화
  - 캐릭터 성장(정예화, 스킬 레벨, 잠재능력, 재화 소모)을 정밀하게 표현
  - 웹 서비스 / API 서버에서 활용 가능한 관계형 스키마 제공

- **DBMS**
  - PostgreSQL 15+
  - Supabase Hosted Database

- **언어 / 포맷**
  - 원본 데이터: JSON
  - 스키마 정의: SQL (DDL)

---

## 📂 데이터 출처 (KR)

본 프로젝트는 아래 공개 리포지토리의 한국 서버 데이터를 사용합니다.

```text
https://github.com/ArknightsAssets/ArknightsGamedata
