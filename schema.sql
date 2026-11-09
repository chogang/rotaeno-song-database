CREATE TABLE analysis_metadata(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);

CREATE TABLE chart_objects(asset_file TEXT,path_id INTEGER,name TEXT,level_id INTEGER,constant REAL,legacy_constant REAL,override_level TEXT,override_prefix TEXT,encrypted_chart TEXT,object_sha256 TEXT,raw_json TEXT,PRIMARY KEY(asset_file,path_id));

CREATE TABLE languages(code TEXT PRIMARY KEY,name TEXT NOT NULL,slot_index INTEGER UNIQUE NOT NULL,source_flags INTEGER NOT NULL);

CREATE TABLE localization_terms(entry_index INTEGER PRIMARY KEY,term_key TEXT NOT NULL,term_type INTEGER NOT NULL,source_asset TEXT NOT NULL,source_path_id INTEGER NOT NULL,source_byte_offset INTEGER NOT NULL,touch_json TEXT NOT NULL);

CREATE TABLE localization_values(entry_index INTEGER REFERENCES localization_terms,language_code TEXT REFERENCES languages,text TEXT NOT NULL,source_flags INTEGER NOT NULL,PRIMARY KEY(entry_index,language_code));

CREATE TABLE managed_localization_values(document TEXT,language_code TEXT,term_key TEXT,text TEXT,source_path_id INTEGER,source_line INTEGER,PRIMARY KEY(document,language_code,source_line));

CREATE TABLE pack_objects(pack_id TEXT PRIMARY KEY,asset_file TEXT,path_id INTEGER,raw_json TEXT);

CREATE TABLE pack_songs(pack_id TEXT REFERENCES pack_objects,song_id TEXT REFERENCES song_objects,position INTEGER,PRIMARY KEY(pack_id,song_id));

CREATE TABLE parse_errors(id INTEGER PRIMARY KEY,detail TEXT);

CREATE TABLE resource_locations(song_id TEXT REFERENCES song_objects,role TEXT,guid TEXT,location_index INTEGER,internal_path TEXT,bundles_json TEXT,PRIMARY KEY(song_id,role,location_index));

CREATE TABLE song_charts(song_id TEXT REFERENCES song_objects,asset_file TEXT,path_id INTEGER,PRIMARY KEY(song_id,asset_file,path_id),FOREIGN KEY(asset_file,path_id) REFERENCES chart_objects);

CREATE TABLE song_objects(song_id TEXT PRIMARY KEY,title TEXT,artist TEXT,illustrator TEXT,charter TEXT,album TEXT,release_version TEXT,asset_file TEXT,path_id INTEGER,object_sha256 TEXT,raw_json TEXT);

CREATE INDEX chart_level ON chart_objects(level_id,constant);

CREATE INDEX localization_term_keys ON localization_terms(term_key);

CREATE VIEW localization_canonical_terms AS SELECT * FROM localization_terms WHERE entry_index IN (SELECT MIN(entry_index) FROM localization_terms GROUP BY term_key);

CREATE VIEW localized_song_names AS SELECT s.song_id,s.title AS original_title,l.code AS language_code,t.term_key,v.text AS translated_title,ref.code AS reference_language,CASE WHEN ref.code IS NOT NULL THEN target.text ELSE v.text END AS resolved_translation,COALESCE(NULLIF(CASE WHEN ref.code IS NOT NULL THEN target.text ELSE v.text END,''),s.title) AS display_title,CASE WHEN ref.code IS NOT NULL THEN 'inferred_language_reference' WHEN v.text IS NULL OR v.text='' THEN 'original_title' ELSE 'localization_table' END AS display_title_source FROM song_objects s CROSS JOIN languages l LEFT JOIN localization_canonical_terms t ON t.term_key='db/song/'||s.song_id||'/name-translation' LEFT JOIN localization_values v ON v.entry_index=t.entry_index AND v.language_code=l.code LEFT JOIN languages ref ON ref.code=v.text LEFT JOIN localization_values target ON target.entry_index=t.entry_index AND target.language_code=ref.code;

CREATE VIEW song_chart_details AS SELECT s.song_id,s.title,s.artist,s.illustrator,s.album,s.release_version,c.asset_file,c.path_id AS chart_path_id,c.name AS chart_name,c.level_id,CASE c.level_id WHEN 0 THEN 'I' WHEN 1 THEN 'II' WHEN 2 THEN 'III' WHEN 3 THEN 'IV' WHEN 100 THEN 'Sp' WHEN 200 THEN 'IV-alpha' END AS difficulty,c.constant,c.legacy_constant,c.override_prefix,c.override_level,COALESCE(NULLIF(json_extract(c.raw_json,'$.override_info.charter.text'),''),s.charter) AS effective_charter,COALESCE(NULLIF(json_extract(c.raw_json,'$.override_info.illustrator.text'),''),s.illustrator) AS effective_illustrator FROM song_objects s JOIN song_charts sc USING(song_id) JOIN chart_objects c ON c.asset_file=sc.asset_file AND c.path_id=sc.path_id;

CREATE TABLE IF NOT EXISTS story_documents (
 language_code TEXT NOT NULL, script TEXT NOT NULL, source_asset TEXT NOT NULL,
 path_id INTEGER NOT NULL, sha256 TEXT NOT NULL, language_basis TEXT NOT NULL,
 PRIMARY KEY(language_code,script)
);
CREATE TABLE IF NOT EXISTS story_values (
 language_code TEXT NOT NULL, script TEXT NOT NULL, entry_key TEXT NOT NULL,
 text TEXT NOT NULL, line INTEGER NOT NULL, label TEXT NOT NULL, command TEXT NOT NULL,
 speaker TEXT NOT NULL, reference_id INTEGER NOT NULL, inline_index INTEGER NOT NULL, field TEXT NOT NULL,
 PRIMARY KEY(language_code,script,entry_key),
 FOREIGN KEY(language_code,script) REFERENCES story_documents(language_code,script)
);

CREATE TABLE IF NOT EXISTS code_texts(literal_index INTEGER PRIMARY KEY,source_text TEXT NOT NULL,contexts_json TEXT NOT NULL,source_json TEXT NOT NULL);
