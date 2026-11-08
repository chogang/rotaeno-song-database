# Rotaeno Song Database

Rotaeno **2.99.0** 게임 파일에서 정적으로 추출한 곡·채보·팩 메타데이터입니다. SQLite, JSON, 추출 스크립트와 검증 결과를 제공합니다.

## 데이터 범위

- 곡 오브젝트 **437개**
- 채보 오브젝트 **1,783개**: I·II·III·IV 각 437개, IV-α 34개, Sp 1개
- 팩 **60개**, 곡 참조 **436건**
- 채보별 제작자 덮어쓰기 **519건**
- Addressables 리소스 위치 **1,752건**

곡 내부 ID, 원제목, 작곡가, 일러스트레이터, 채보 제작자, 앨범, 추가 크레딧, 내부 추가 버전, 채보 정수, 특수 표시 난이도, 숨김 종류, 스토리보드 참조 및 재킷·음원 GUID와 번들 경로를 포함합니다. 채보별 크레딧은 공통 곡 크레딧과 따로 보존합니다.

**437개는 파일에 존재하는 오브젝트 수입니다. 현재 플레이 가능한 곡 수를 뜻하지 않습니다.** `2-close-for-words`는 팩 미소속이며 정수 0인 채보 4개와 해소되지 않는 리소스 GUID가 있습니다. 이를 미출시 여부의 확정 근거로 해석하지 않습니다.

## 파일

- [`game-songs.sqlite`](game-songs.sqlite): 곡·채보·팩·리소스 관계와 암호화 채보 문자열을 보존한 DB.
- [`game-song-data.json`](game-song-data.json): 곡·채보·팩 메타데이터. 암호화 본문은 제외.
- [`resource-links.json`](resource-links.json): GUID, 게임 내부 에셋 경로, 의존 번들 및 APK 내 존재 확인 결과.
- [`schema.sql`](schema.sql): DB 스키마와 조회 뷰.
- [`manifest-info.json`](manifest-info.json): 패키지·게임 버전 정보.
- [`source-apks.json`](source-apks.json): 원본 APK 파일명·크기·SHA-256.
- [`validation-report.json`](validation-report.json): 추출 및 무결성 검증 결과.
- [`rea-evidence.json`](rea-evidence.json): 정적 분석 근거의 경로 삭제본.
- [`tools/`](tools/): 추출·연결·검증 스크립트.

개인 PC의 절대 경로는 빈 문자열로 삭제했습니다. 게임의 APK 내부 경로, 에셋 경로, 오브젝트 ID와 원본 해시는 유지했습니다. `rea-evidence.json`은 개인정보 제거를 위해 수정한 사본이므로 원래 Evidence의 서명·다이제스트 검증용 원본으로 사용할 수 없습니다.

## 조회

SQLite의 `song_chart_details` 뷰는 곡과 채보를 연결하고 채보별 제작자·일러스트레이터 덮어쓰기를 적용합니다.

```sql
SELECT song_id, title, difficulty, constant, effective_charter
FROM song_chart_details
WHERE song_id = 'after-rain';

SELECT p.pack_id, s.song_id, s.title
FROM pack_songs p
JOIN song_objects s USING (song_id)
ORDER BY p.pack_id, p.position;

SELECT role, guid, internal_path, bundles_json
FROM resource_locations
WHERE song_id = 'after-rain';
```

주요 테이블은 `song_objects`, `chart_objects`, `song_charts`, `pack_objects`, `pack_songs`, `resource_locations`, `analysis_metadata`입니다. `chart_objects.raw_json`에는 채보별 제목·크레딧·리소스 덮어쓰기 정보가 있습니다.

난이도 ID는 I=0, II=1, III=2, IV=3, Sp=100, IV-α=200입니다. `constant`는 `v2InnerDifficulty`, `legacy_constant`는 과거 `_legacy_v1InnerDifficulty`입니다. 내부 정수와 `12+` 같은 표시 난이도는 다릅니다. `true [Sp]`는 정수 0과 표시 문자열 `Overload`를 갖습니다.

예를 들어 After Rain IV의 정수는 10.7이며 파일에 저장된 일러스트레이터는 `BTKCyber`입니다. 내부 추가 버전은 위키의 최초 공개 버전과 다를 수 있습니다.

## 추출 방법

분석 대상은 패키지 `com.xd.rotaeno.googleplay`, versionCode **4022**입니다. Unity 헤더 버전은 `2022.3.62f2c1`, IL2CPP 메타데이터 버전은 31입니다. 분석일은 2026-11-08입니다.

곡 정보는 `split_UnityDataAssetPack.apk` 안의 `assets/bin/Data/datapack.unity3d` → `resources.assets`에서 읽었습니다.

- 곡: `GW.DB.Song.Data.SongDataSO`
- 곡 크레딧: `GW.DB.Song.Data.StandardSongInfoData`
- 채보: `GW.DB.Chart.Data.StandardChartDataSO`
- 팩: `GW.DB.Pack.Data.PackDataSO`

`base.apk`의 `global-metadata.dat`와 같은 제공본의 `libil2cpp.so`를 연결해 필드명·자료형을 확인했습니다. 곡과 채보는 직렬화된 PPtr로 연결했습니다. 모든 채보에서 끝까지 구조를 읽었으며, 팩 소속은 모든 원소가 곡 오브젝트로 해소되는 유일한 최대 길이 PPtr 배열과 `songDatas` 필드를 대조했습니다.

리소스 경로는 `split_UnityStreamingAssetsPack.apk`의 `assets/aa/catalog.json`에서 GUID → 위치 → 의존 번들을 따라 확인했습니다. Texture2D와 Sprite가 같은 파일에 대응할 수 있어 위치 개수는 곡 수와 다릅니다.

검증 결과: 파싱 오류 0건, DB 무결성 정상, 외래키 오류 0건, 내보낸 곡·채보 오브젝트 해시 전수 일치. 해소된 리소스의 의존 번들은 모두 APK에 존재했습니다.

## 재현

Python 3.12, **UnityPy 1.25.4**, Node.js 24.15 이상 또는 26 이상을 사용했습니다. UnityPy는 [공식 프로젝트](https://github.com/K0lb3/UnityPy)에서 확인할 수 있습니다.

```sh
python -m pip install -r requirements.txt
python tools/parse_game.py --all
python tools/supplement_game.py
node tools/link_resources.mjs
node tools/validate_game.mjs
```

실행 전에 `ROTAENO_WORKDIR`에 작업 디렉터리, `ROTAENO_SOURCE_DIR`에 APK가 있는 디렉터리를 설정합니다. 두 설정값에는 기본 개인 경로가 들어 있지 않습니다. 작업 디렉터리에는 다음 입력이 필요합니다.

- `extracted/datapack.unity3d`: 데이터 팩에서 추출한 Unity 번들.
- `extracted/catalog.json`: 스트리밍 리소스 팩에서 추출한 카탈로그.
- `apk-inventory.json`: APK 파일명과 ZIP 엔트리 `Path`, `Bytes`, `Compressed`를 기록한 목록.
- `source-apks.json`: 원본 APK 해시 목록. 로컬 `Path`는 빈 문자열이어도 됩니다.

`supplement_game.py`는 원본 `base.apk`에서 버전을 읽습니다. 검증 스크립트는 `raw-objects/`의 추출 바이트도 확인합니다. 스크립트는 이 버전에서 확인한 오브젝트 구조와 개수에 맞춰져 있으며, 새로운 게임 버전에는 추가 검증이 필요합니다. 기존 생성 DB를 덮어씁니다.

## 한계

실제 노트 배치 본문은 `EncryptedV2ChartString`에 저장되어 있으며 **복호화하지 않았습니다**. BPM·노트 수·좌표·시간·회전값은 이 자료에서 추출하지 않았습니다. Odin 데이터, 일부 상속·일정 필드와 곡 데이터 꼬리 부분은 원시 바이트로 보존했지만 전부 의미 해석하지 않았습니다. 번역 키와 고정 문자열은 함께 보존했으며 최종 런타임 번역은 별도로 해석하지 않았습니다.

APK, 네이티브 라이브러리, 음원·재킷 바이너리와 `raw-objects/`는 이 저장소에 포함하지 않습니다. 이 프로젝트는 비공식 데이터 조사 결과이며, 원 게임의 콘텐츠에 대한 권리 부여를 의미하지 않습니다.
