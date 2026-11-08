# Rotaeno Song Database

Rotaeno **2.99.0**의 곡·채보·팩 정보와 다국어 번역 텍스트를 제공하는 비공식 데이터 저장소입니다. 데이터는 SQLite와 JSON으로 제공됩니다.

## 수록 데이터

- 곡 데이터 **437개**: 내부 ID, 제목, 작곡가, 일러스트레이터, 채보 제작자, 앨범, 추가 버전.
- 채보 데이터 **1,783개**: 난이도, 채보 정수, 개별 크레딧과 표시 정보.
- 팩 데이터 **60개**: 수록 곡과 팩별 번역 텍스트.
- 리소스 정보: 재킷·음원 GUID와 게임 내부 에셋·번들 경로.
- 번역 데이터: 고유 키 **2,459개**, 언어별 텍스트 사전, 곡명·UI·캐릭터 이름.

데이터 개수는 게임 파일의 오브젝트 기준이며 테스트·특수 항목이 포함될 수 있습니다. 노트 배치·BPM·노트 수는 포함하지 않습니다.

## 파일 구성

- [`game-songs.sqlite`](game-songs.sqlite): 곡·채보·팩·리소스·번역을 통합한 DB.
- [`game-song-data.json`](game-song-data.json): 곡·채보·팩 메타데이터.
- [`resource-links.json`](resource-links.json): 리소스 GUID와 에셋·번들 경로.
- [`schema.sql`](schema.sql): DB 테이블과 조회 뷰 정의.
- [`localization/`](localization/README.md): 언어별 JSON, 번역 전용 SQLite, 곡명·팩 이름·UI 텍스트.
- [`tools/`](tools/): 데이터 추출 및 검증 스크립트.

원본 버전·해시와 검증 결과는 `manifest-info.json`, `source-apks.json`, `validation-report.json`에서 확인할 수 있습니다.

## 언어

간체 중국어(`zh-CN`), 번체 중국어(`zh-TW`), 영어(`en`), 한국어(`ko`), 일본어(`ja`), 인도네시아어(`id`), 태국어(`th`)를 포함합니다. 중국 서버용 `china` Override 데이터도 별도로 보존합니다.

[한국어 사전](localization/ko.json) · [영어 사전](localization/en.json) · [곡명 번역](localization/song-names.json) · [번역 데이터 설명](localization/README.md)

## 사용 예

`game-songs.sqlite`를 SQLite 도구에서 열어 조회할 수 있습니다.

```sql
SELECT song_id, title, difficulty, constant, effective_charter
FROM song_chart_details
WHERE song_id = 'after-rain';

SELECT song_id, original_title, display_title
FROM localized_song_names
WHERE language_code = 'ko';
```

`song_chart_details`는 채보별 크레딧을 반영한 조회 뷰입니다. `localized_song_names`는 원제목과 번역값을 연결한 뷰이며, 번역 원문과 언어 참조 해석 결과를 구분해 제공합니다.
