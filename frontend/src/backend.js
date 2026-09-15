import {createClient} from '@supabase/supabase-js';
const url=import.meta.env.VITE_SUPABASE_URL;
const key=import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
export const backend=url&&key?createClient(url,key):null;
export async function uploadPDF(file,scope,userId){
 if(!backend||!userId)throw Error('Entre com um acesso autorizado para enviar PDFs.');
 const header=new TextDecoder().decode(await file.slice(0,5).arrayBuffer());
 if(header!=='%PDF-')throw Error('O arquivo selecionado não possui um cabeçalho PDF válido.');
 if(file.size>25*1024*1024)throw Error('O PDF deve ter no máximo 25 MB.');
 const safe=file.name.normalize('NFKD').replace(/[^a-zA-Z0-9._-]/g,'_');
 const bucket=scope==='familia'?'familia-documentos':'falcao-documentos';
 const path=`app/${userId}/${crypto.randomUUID()}-${safe}`;
 const {error}=await backend.storage.from(bucket).upload(path,file,{contentType:'application/pdf',upsert:false});
 if(error)throw Error('Não foi possível enviar. Verifique a autorização de acesso da equipe.');
 return {name:file.name,path,bucket,status:'Enviado · aguardando leitura',type:'PDF',date:new Date().toISOString()};
}
