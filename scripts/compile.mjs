import fs from 'node:fs';
import path from 'node:path';
import {compile} from '../web/vids-core.js';
const input=path.resolve(process.argv[2]);
const doc=JSON.parse(fs.readFileSync(input,'utf8'));
fs.writeFileSync(path.join(path.dirname(input),'index.html'),compile(doc,{resolution:process.argv[3]||'1080p'}));
