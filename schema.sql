CREATE TABLE analysis_metadata(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);

CREATE TABLE chart_objects(asset_file TEXT,path_id INTEGER,name TEXT,level_id INTEGER,constant REAL,legacy_constant REAL,override_level TEXT,override_prefix TEXT,encrypted_chart TEXT,object_sha256 TEXT,raw_json TEXT,PRIMARY KEY(asset_file,path_id));

CREATE TABLE pack_objects(pack_id TEXT PRIMARY KEY,asset_file TEXT,path_id INTEGER,raw_json TEXT);

CREATE TABLE pack_songs(pack_id TEXT REFERENCES pack_objects,song_id TEXT REFERENCES song_objects,position INTEGER,PRIMARY KEY(pack_id,song_id));

CREATE TABLE parse_errors(id INTEGER PRIMARY KEY,detail TEXT);

CREATE TABLE resource_locations(song_id TEXT REFERENCES song_objects,role TEXT,guid TEXT,location_index INTEGER,internal_path TEXT,bundles_json TEXT,PRIMARY KEY(song_id,role,location_index));

CREATE TABLE song_charts(song_id TEXT REFERENCES song_objects,asset_file TEXT,path_id INTEGER,PRIMARY KEY(song_id,asset_file,path_id),FOREIGN KEY(asset_file,path_id) REFERENCES chart_objects);

CREATE TABLE song_objects(song_id TEXT PRIMARY KEY,title TEXT,artist TEXT,illustrator TEXT,charter TEXT,album TEXT,release_version TEXT,asset_file TEXT,path_id INTEGER,object_sha256 TEXT,raw_json TEXT);

CREATE INDEX chart_level ON chart_objects(level_id,constant);

CREATE VIEW song_chart_details AS SELECT s.song_id,s.title,s.artist,s.illustrator,s.album,s.release_version,c.asset_file,c.path_id AS chart_path_id,c.name AS chart_name,c.level_id,CASE c.level_id WHEN 0 THEN 'I' WHEN 1 THEN 'II' WHEN 2 THEN 'III' WHEN 3 THEN 'IV' WHEN 100 THEN 'Sp' WHEN 200 THEN 'IV-alpha' END AS difficulty,c.constant,c.legacy_constant,c.override_prefix,c.override_level,COALESCE(NULLIF(json_extract(c.raw_json,'$.override_info.charter.text'),''),s.charter) AS effective_charter,COALESCE(NULLIF(json_extract(c.raw_json,'$.override_info.illustrator.text'),''),s.illustrator) AS effective_illustrator FROM song_objects s JOIN song_charts sc USING(song_id) JOIN chart_objects c ON c.asset_file=sc.asset_file AND c.path_id=sc.path_id;