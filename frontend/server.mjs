import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
const root=path.resolve('dist');
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.svg':'image/svg+xml','.webp':'image/webp','.png':'image/png','.woff2':'font/woff2','.csv':'text/csv; charset=utf-8'};
http.createServer(async(req,res)=>{
  if(req.url==='/health'){res.writeHead(200);res.end('ok');return;}
  if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405);res.end();return;}
  try{
    const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    let file=path.resolve(root,'.'+pathname);
    if(file!==root&&!file.startsWith(root+path.sep)){res.writeHead(403);res.end();return;}
    try{if(!(await fs.stat(file)).isFile())file=path.join(root,'index.html');}catch{if(path.extname(pathname)){res.writeHead(404);res.end();return;}file=path.join(root,'index.html');}
    const body=await fs.readFile(file);
    res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream','X-Content-Type-Options':'nosniff','Referrer-Policy':'strict-origin-when-cross-origin','X-Frame-Options':'SAMEORIGIN','Cache-Control':file.endsWith('index.html')?'no-cache':'public, max-age=3600'});
    res.end(req.method==='HEAD'?undefined:body);
  }catch{res.writeHead(400);res.end('Requisição inválida');}
}).listen(Number(process.env.PORT||3000),'0.0.0.0');
