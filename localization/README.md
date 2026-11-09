# 언어별 번역 텍스트

Rotaeno 2.99.0의 `resources.assets`에서 읽은 번역 데이터입니다. 원본 언어 순서는 `languages.json`에 보존했습니다.

## I2Languages

- 원본 항목 2,462개, 고유 키 2,459개.
- 텍스트 항목 2,439개, 고유 텍스트 키 2,436개.
- 폰트·스프라이트 등 비텍스트 참조 항목 23개.
- 언어 슬롯 8개, 원본 셀 19,696개.

게임 언어는 `zh-CN`(간체), `zh-TW`(번체), `en`(영어), `ko`(한국어), `ja`(일본어), `id`(인도네시아어), `th`(태국어)입니다. `china`는 원본 이름이 `国服Override`인 별도 슬롯이며 일반적인 8번째 번역 언어로 취급하지 않습니다. 원본의 언어 플래그도 보존했습니다.

각 언어의 `<code>.json`은 텍스트 키와 원본 문자열의 대응입니다. 빈 문자열도 삭제하지 않았습니다. 임의 번역이나 다른 언어의 자동 대체값을 이 파일에 넣지 않았습니다.

- `all-terms.json`: 비텍스트 참조까지 포함한 모든 항목, 순서 인덱스, 플래그와 소스 오프셋.
- `asset-references.json`: 비텍스트 항목 23개.
- `duplicate-terms.json`: 중복 키 3개와 해당 원본 항목 전체.
- `song-names.json`: 437곡의 원제목·번역 원문·언어 참조 해석·표시 이름.
- `pack-texts.json`: 60개 팩의 이름·부제·오브젝트에 직접 저장된 추가 번역 키.
- `localization.sqlite`: 번역 테이블 전용 DB.
- `extraction-report.json`, `validation-report.json`: 원본 식별 정보와 검증 결과.

동일 키가 중복될 때 언어별 사전과 `localization_canonical_terms` 뷰는 **원본의 첫 항목**을 선택합니다. 이는 내보내기 정책이며 런타임의 중복 처리와 같다고 단정하지 않습니다. 3개 중복 키의 모든 버전은 `all-terms.json`과 DB의 `entry_index`별로 보존되어 있습니다. `character_maimai_salt/Name`은 중복 항목 사이의 값이 다릅니다.

곡명에는 번역값 자체가 `en`인 셀이 381개 있습니다. `translations`에는 이 값을 그대로 남겼으며, `resolution`과 `display_titles`에서는 알려진 언어 코드와 일치하면 해당 슬롯을 참조한다는 **분석상 추론**을 적용했습니다. 참조 순환은 0건입니다. 결과가 비어 있으면 `display_titles`에서만 원제목으로 대체합니다. 실제 게임 런타임의 전체 fallback 정책을 검증한 것은 아닙니다.

437곡 중 436곡은 곡명 번역 키가 있습니다. `2-close-for-words`에는 대응 키가 없습니다. 키가 있어도 번역 문자열은 비어 있을 수 있으며 이는 곡명이 잘못 추출되었다는 의미가 아닙니다.

## 별도 텍스트 문서

`naninovel/<code>/`에는 7개 언어의 `CharacterNames`, `DefaultUI`, `Locales` 문서가 원문 `.txt`와 구조화 `.json`으로 있습니다. 총 21개 문서, 2,415개 항목입니다. 각 문서의 원본 오브젝트 ID·해시·원문 줄 번호를 보존했습니다. `.txt`의 `\n` 같은 리터럴 이스케이프는 임의로 변환하지 않았습니다.

번역 문서는 머리말에 대상 언어 코드가 명시되어 있습니다. 머리말 없는 기본 문서는 번역 문서들에 표시된 원본 언어 `zh-TW`를 기준으로 연결했으며 이 추론을 각 JSON의 `language_basis`에 표시했습니다. `Locales`는 언어 이름 목록이라 여러 언어 파일의 값이 영어로 같을 수 있습니다.

`sdk-anti-addiction.json` 및 `sdk/`에는 별도 SDK에 포함된 14개 언어 키의 문자열을 보존했습니다. SDK의 `De`, `Es`, `Fr`, `Pt`, `Ru`, `Tr`, `Vi`가 존재한다고 해서 게임 본편 UI가 해당 언어를 지원한다는 뜻은 아닙니다.

## 스토리 대본

`story-scripts.json`과 `story/<code>/*.txt`에는 `resources.assets`의 컴파일된 Naninovel Script 객체 1,301개에서 추출한 대사·표시 이름 72,941개가 있습니다. 한국어·영어·일본어·간체·태국어·인도네시아어는 각 186개 대본, 기본 번체는 185개 대본입니다. 한국어는 빈 문자열을 포함해 10,418개 항목입니다. 본편·외전·곡 인터뷰·대화 대본을 포함합니다.

언어는 번역 문서 머리말에 기록된 코드로 확인하며, 머리말 없는 기본 대본은 LocalizationConfiguration의 원본 언어 `zh-TW`를 적용했습니다. 객체 ID·해시·문서 행·명령 참조 ID·인라인 순서를 보존했습니다. 문장 키는 원문 라벨과 해당 라벨 안의 필드별 조각 순서로 구성합니다. 한국어 모든 키는 영어에 대응하며 일본어에 대응 키가 없는 한국어 조각은 4개입니다.

JSON과 TXT는 컴파일된 대사 필드의 내보내기 형식입니다. TXT는 `문장키: 텍스트` 형식이며 원본 `.nani` 소스나 실행 명령 전체를 복원한 파일이 아닙니다. 에셋 재패킹은 포함하지 않습니다. 원본 위치·언어별 개수·전체 명령 유형은 `story-report.json`에서 확인할 수 있습니다. 라이브 번역 서버나 외부 스프레드시트에는 접속하지 않았습니다.

## DB

기존 `game-songs.sqlite`에도 다음 테이블을 추가했습니다.

- `languages`: 언어 코드, 이름, 슬롯 인덱스와 원본 플래그.
- `localization_terms`: 원본 순서에 따른 번역 키·타입·소스 오프셋.
- `localization_values`: 원본 항목·언어별 문자열과 플래그.
- `managed_localization_values`: Naninovel 문서의 키·언어별 문자열.
- `story_documents`, `story_values`: 언어·대본·문장 키별 스토리 대사와 원본 객체 정보.
- `localization_canonical_terms`: 키별 첫 항목을 선택한 뷰.
- `localized_song_names`: 번역 원문과 추론한 언어 참조를 구분한 곡명 뷰. 이 뷰는 기존 곡 DB에만 있습니다.

```sql
SELECT term_key, v.language_code, v.text
FROM localization_canonical_terms t
JOIN localization_values v USING(entry_index)
WHERE t.term_key = 'tutorial/song-select/let''s-try-to-play-after-rain-for-this-time';

SELECT song_id, original_title, translated_title,
       reference_language, display_title, display_title_source
FROM localized_song_names WHERE language_code='ko';

SELECT document, term_key, text
FROM managed_localization_values
WHERE language_code='ko' AND document='CharacterNames';
```

## 재현

기존 추출 파이프라인을 실행한 작업 폴더를 `ROTAENO_WORKDIR`에 설정하고 다음을 실행합니다.

```sh
python tools/extract_localization.py
python tools/extract_managed_texts.py
python tools/validate_localization.py
```

원본 테이블 오브젝트는 `resources.assets`, path ID `16126`, 이름 `I2Languages`입니다. SHA-256은 `2cc05492efd84bc4b641c68a0a6c8ef12586f5e25dcc597d6b5931dd6e4fd1a9`입니다. 개인 PC의 절대 경로는 내보내기 파일에 포함하지 않았습니다.
