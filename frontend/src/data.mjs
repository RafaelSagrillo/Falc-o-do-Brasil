import Papa from 'papaparse';

export const months=['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];
export const money=(value,compact=false)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL',notation:compact?'compact':'standard',maximumFractionDigits:compact?2:2}).format(value||0);
export const number=value=>new Intl.NumberFormat('pt-BR').format(value||0);
export const percent=value=>`${new Intl.NumberFormat('pt-BR',{maximumFractionDigits:1}).format(value||0)}%`;
const revenues=[720000,760000,690000,815000,880000,910000,1010000,965000,980000,1020000,1060000,1100000];
export const demoRows=[2025,2026].flatMap(year=>['empresa','familia'].flatMap(scope=>revenues.map((revenue,i)=>{
  const family=scope==='familia';
  const factor=year===2025?0.79:1;
  const base=family?52000+(i%3)*2000:revenue;
  const r=Math.round(base*factor);
  return {year,month:i+1,scope,revenue:r,cost:family?0:Math.round(r*(year===2025?0.83:0.785+(i%4)*0.008)),expense:family?Math.round((36000+(i%4)*2500)*factor):Math.round(r*0.085),overdue:family?0:Math.round(90000+(i%5)*7000),orders:family?0:Math.round(320+(i*11)*factor),clients:family?0:Math.round(210+i*8),source:'demo'};
})));

export const csvTemplate='ano;mes;receita;custo;despesa;inadimplencia;pedidos;clientes;escopo\n2026;1;125000,00;95000,00;8000,00;4300,00;80;45;empresa\n2026;2;138000,00;103000,00;9000,00;3900,00;92;51;empresa\n';
const decimal=(value,key,line)=>{
  if(value===undefined||String(value).trim()==='')throw new Error(`Linha ${line}: preencha ${key}.`);
  const str=String(value).trim().replace(/R\$/g,'').replace(/\s/g,'');
  if(!/^-?\d+(?:[.,]\d+)*$/.test(str))throw new Error(`Linha ${line}: ${key} deve ser numérico.`);
  const cleaned=str.includes(',')?str.replace(/\./g,'').replace(',','.'):str;
  const n=Number(cleaned);
  if(!Number.isFinite(n)||Math.abs(n)>1e12)throw new Error(`Linha ${line}: ${key} inválido.`);
  return n;
};
export function parseCSV(text){
  const parsed=Papa.parse(text.replace(/^\uFEFF/,''),{header:true,skipEmptyLines:'greedy',transformHeader:h=>h.trim().toLowerCase()});
  if(parsed.errors.length)throw new Error('Não foi possível ler as colunas. Use o modelo CSV disponível.');
  if(!parsed.data.length||parsed.data.length>5000)throw new Error('O arquivo precisa ter entre 1 e 5.000 linhas.');
  for(const field of ['ano','mes','receita','custo'])if(!parsed.meta.fields.includes(field))throw new Error(`Coluna obrigatória ausente: ${field}.`);
  const seen=new Set();
  return parsed.data.map((row,i)=>{
    const line=i+2;
    const year=decimal(row.ano,'ano',line),month=decimal(row.mes,'mes',line);
    if(!Number.isInteger(year)||year<2000||year>2100||!Number.isInteger(month)||month<1||month>12)throw new Error(`Linha ${line}: ano ou mês inválido.`);
    const scope=row.escopo?.trim().toLowerCase()||'empresa';
    if(!['empresa','familia'].includes(scope))throw new Error(`Linha ${line}: escopo deve ser empresa ou familia.`);
    const key=`${scope}-${year}-${month}`;
    if(seen.has(key))throw new Error(`Há dois registros para ${months[month-1]}/${year} no mesmo escopo. Consolide o mês antes de importar.`);
    seen.add(key);
    const output={year,month,scope,source:'csv'};
    for(const [target,field] of Object.entries({revenue:'receita',cost:'custo',expense:'despesa',overdue:'inadimplencia',orders:'pedidos',clients:'clientes'})){
      output[target]=['receita','custo'].includes(field)?decimal(row[field],field,line):(row[field]?.trim()?decimal(row[field],field,line):0);
      if(output[target]<0)throw new Error(`Linha ${line}: ${field} não pode ser negativo.`);
      if(['orders','clients'].includes(target)&&!Number.isInteger(output[target]))throw new Error(`Linha ${line}: ${field} deve ser inteiro.`);
    }
    return output;
  });
}
export function summarize(rows){
  const sorted=[...rows].sort((a,b)=>a.month-b.month);
  const total=rows.reduce((acc,r)=>({revenue:acc.revenue+r.revenue,cost:acc.cost+r.cost,expense:acc.expense+r.expense,orders:acc.orders+r.orders}),{revenue:0,cost:0,expense:0,orders:0});
  const profit=total.revenue-total.cost;
  return {...total,profit,margin:total.revenue?profit/total.revenue*100:0,overdue:sorted.at(-1)?.overdue||0,clients:sorted.at(-1)?.clients||0};
}
export function mergeRows(existing,incoming){
  const map=new Map(existing.map(r=>[`${r.scope}-${r.year}-${r.month}`,r]));
  incoming.forEach(r=>map.set(`${r.scope}-${r.year}-${r.month}`,r));
  return [...map.values()].sort((a,b)=>a.year-b.year||a.month-b.month);
}
export function comparison(rows,year,scope,period='all'){
  const allowed=period==='first'?[1,2,3,4,5,6]:period==='second'?[7,8,9,10,11,12]:months.map((_,i)=>i+1);
  const current=rows.filter(r=>r.year===year&&r.scope===scope&&allowed.includes(r.month));
  const available=new Set(current.map(r=>r.month));
  const previous=rows.filter(r=>r.year===year-1&&r.scope===scope&&available.has(r.month));
  const fullComparison=current.length>0&&previous.length===current.length;
  const chart=allowed.map(month=>{
    const a=current.find(r=>r.month===month),b=previous.find(r=>r.month===month);
    return {month,label:months[month-1],current:a?a.revenue-a.cost:null,previous:b?b.revenue-b.cost:null,revenue:a?.revenue??null,expense:a?.expense??null,overdue:a?.overdue??null};
  });
  return {current,previous,chart,total:summarize(current),prior:summarize(previous),fullComparison};
}
export function download(name,body,type='text/csv;charset=utf-8'){
  const href=URL.createObjectURL(new Blob([body],{type}));
  const a=document.createElement('a');a.href=href;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(href),1000);
}
