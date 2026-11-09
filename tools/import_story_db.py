"""Add the extracted Naninovel dialogue tables to caller-selected SQLite DBs."""
import json, sqlite3, sys, pathlib

SCHEMA = """
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
"""

def main():
 data=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf8'))
 for filename in sys.argv[2:]:
  assert pathlib.Path(filename).is_file(), 'Select an existing database.'
  with sqlite3.connect(filename) as db:
   db.execute('PRAGMA foreign_keys=ON')
   db.executescript(SCHEMA)
   db.execute('DELETE FROM story_values');db.execute('DELETE FROM story_documents')
   for doc in data['documents']:
    db.execute('INSERT INTO story_documents VALUES (?,?,?,?,?,?)', (doc['code'],doc['script'],doc['source_asset'],doc['path_id'],doc['sha256'],doc['language_basis']))
    db.executemany('INSERT INTO story_values VALUES (?,?,?,?,?,?,?,?,?,?,?)',[(doc['code'],doc['script'],e['key'],e['text'],e['line'],e['label'],e['command'],e['speaker'],e['reference_id'],e['inline_index'],e['field']) for e in doc['entries']])
   assert db.execute('SELECT count(*) FROM story_documents').fetchone()[0]==len(data['documents'])
   assert db.execute('SELECT count(*) FROM story_values').fetchone()[0]==sum(len(d['entries']) for d in data['documents'])
   assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
   assert not db.execute('PRAGMA foreign_key_check').fetchall()
   print(json.dumps(dict(documents=len(data['documents']),entries=sum(len(d['entries']) for d in data['documents']),integrity='ok')))

if __name__=='__main__': main()
