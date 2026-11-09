"""Import recovered code literals, separately from authored locale tables."""
import json,pathlib,sqlite3,sys
SCHEMA='CREATE TABLE IF NOT EXISTS code_texts(literal_index INTEGER PRIMARY KEY,source_text TEXT NOT NULL,contexts_json TEXT NOT NULL,source_json TEXT NOT NULL);'
if __name__=='__main__':
 data=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf8'))
 for filename in sys.argv[2:]:
  assert pathlib.Path(filename).is_file()
  with sqlite3.connect(filename) as db:
   db.execute(SCHEMA);db.execute('DELETE FROM code_texts')
   db.executemany('INSERT INTO code_texts VALUES(?,?,?,?)',[(e['literal_index'],e['text'],json.dumps(e['contexts']),json.dumps(data['source'])) for e in data['entries']])
   assert db.execute('SELECT count(*) FROM code_texts').fetchone()[0]==len(data['entries'])
   assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
   print(json.dumps({'code_texts':len(data['entries']),'integrity':'ok'}))
