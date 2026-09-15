import React,{useEffect,useMemo,useRef,useState} from 'react';
import {MapPin,Plus,Minus,Maximize,Truck,ArrowUpRight,Navigation,RotateCcw} from 'lucide-react';
import {money,number,percent} from './data.mjs';

const cities=[
 {name:'Guarapuava',lon:-51.46,lat:-25.39,seller:'Carteira A',revenue:184000,orders:62,clients:28,margin:21.8},
 {name:'Irati',lon:-50.65,lat:-25.47,seller:'Carteira A',revenue:98000,orders:34,clients:17,margin:23.1},
 {name:'São Mateus do Sul',lon:-50.38,lat:-25.87,seller:'Carteira B',revenue:121000,orders:39,clients:21,margin:20.6},
 {name:'União da Vitória',lon:-51.09,lat:-26.23,seller:'Carteira B',revenue:156000,orders:45,clients:24,margin:22.5},
 {name:'Palmas',lon:-51.99,lat:-26.48,seller:'Carteira C',revenue:74000,orders:27,clients:13,margin:19.4},
 {name:'Prudentópolis',lon:-50.98,lat:-25.21,seller:'Carteira A',revenue:83000,orders:29,clients:16,margin:24.2},
 {name:'Ponta Grossa',lon:-50.16,lat:-25.09,seller:'Carteira C',revenue:212000,orders:71,clients:35,margin:21.2},
 {name:'Curitiba',lon:-49.27,lat:-25.43,seller:'Carteira C',revenue:267000,orders:88,clients:42,margin:20.9},
];
const point=([lon,lat])=>[(lon+54.7)*125,(-22.4-lat)*137];
function ringPath(ring){return ring.map((p,i)=>`${i?'L':'M'}${point(p).map(n=>n.toFixed(2)).join(',')}`).join(' ')+'Z';}
function geometryPath(geometry){const polygons=geometry.type==='MultiPolygon'?geometry.coordinates:[geometry.coordinates];return polygons.map(p=>p.map(ringPath).join(' ')).join(' ');}
const initialView={x:245,y:300,w:560,h:330};
export default function SalesMap({paused}){
 const [features,setFeatures]=useState([]),[error,setError]=useState(false),[selected,setSelected]=useState(cities[1]),[seller,setSeller]=useState('all'),[routes,setRoutes]=useState(true),[view,setView]=useState(initialView),[delay,setDelay]=useState(0);
 const drag=useRef(null);
 useEffect(()=>{let alive=true;fetch('/parana.geojson').then(r=>{if(!r.ok)throw Error();return r.json();}).then(d=>{if(alive)setFeatures(d.features||[]);}).catch(()=>alive&&setError(true));return()=>{alive=false;};},[]);
 const filtered=useMemo(()=>cities.filter(c=>seller==='all'||c.seller===seller),[seller]);
 const selectedVisible=filtered.find(c=>c.name===selected.name)||filtered[0];
 const totals=filtered.reduce((a,c)=>({revenue:a.revenue+c.revenue,orders:a.orders+c.orders,clients:a.clients+c.clients}),{revenue:0,orders:0,clients:0});
 const zoom=factor=>setView(v=>({x:v.x+(v.w-v.w*factor)/2,y:v.y+(v.h-v.h*factor)/2,w:Math.min(1000,Math.max(180,v.w*factor)),h:Math.min(640,Math.max(106,v.h*factor))}));
 const [sx,sy]=point([-51.93,-23.42]);
 return <div className="sales-page">
  <div className="section-heading"><div><div className="eyebrow">INTELIGÊNCIA TERRITORIAL</div><h2>Mais perto de cada oportunidade.</h2><p>Explore as carteiras e a presença comercial no sul e sudeste do Paraná.</p></div><span className="badge demo">Rotas e valores ilustrativos</span></div>
  <div className="sales-top"><div><span>Vendas no mapa</span><strong>{money(totals.revenue)}</strong></div><div><span>Pedidos de exemplo</span><strong>{number(totals.orders)}</strong></div><div><span>Clientes de exemplo</span><strong>{number(totals.clients)}</strong></div><div><span>Cidades no recorte</span><strong>{filtered.length.toString().padStart(2,'0')}</strong></div></div>
  <div className="map-layout">
   <div className={`map-canvas ${paused?'motion-paused':''}`}>
    <div className="map-toolbar"><div><span className="live-dot"/> Sul e sudeste · PR</div><button className={routes?'map-toggle active':'map-toggle'} onClick={()=>setRoutes(!routes)}><Navigation size={13}/> Rotas</button></div>
    {error?<div className="map-error">Não foi possível carregar a base do mapa. Consulte as cidades ao lado.</div>:<svg className="territory-map" viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`} aria-label="Mapa interativo de vendas do Paraná. Use a lista de cidades para selecionar uma carteira." onPointerDown={e=>{if(e.target.closest('[data-city]'))return;drag.current={x:e.clientX,y:e.clientY,view};e.currentTarget.setPointerCapture(e.pointerId);}} onPointerMove={e=>{if(!drag.current)return;const rect=e.currentTarget.getBoundingClientRect(),d=drag.current;setView({...d.view,x:d.view.x-(e.clientX-d.x)*d.view.w/rect.width,y:d.view.y-(e.clientY-d.y)*d.view.h/rect.height});}} onPointerUp={()=>drag.current=null} onPointerCancel={()=>drag.current=null}>
     <defs><pattern id="map-grid" width="35" height="35" patternUnits="userSpaceOnUse"><path d="M35 0H0V35" fill="none" stroke="#315148" strokeWidth=".35"/></pattern><radialGradient id="map-glow"><stop stopColor="#507365" stopOpacity=".18"/><stop offset="1" stopColor="#142b23" stopOpacity="0"/></radialGradient></defs>
     <rect x="-900" y="-900" width="3000" height="3000" fill="#11261e"/><rect x="-900" y="-900" width="3000" height="3000" fill="url(#map-grid)"/>
     <ellipse cx="510" cy="440" rx="370" ry="240" fill="url(#map-glow)"/>
     {features.map((f,i)=><path key={i} d={geometryPath(f.geometry)} fill={['4106','4109'].includes(String(f.properties?.codarea))?'#213d31':'#193228'} stroke="#46604f" strokeWidth=".8"/>)}
     <text x="215" y="240" fill="#587467" fontSize="21" letterSpacing="12" pointerEvents="none">PARANÁ</text>
     <text x="435" y="630" fill="#587467" fontSize="9" letterSpacing="4">SANTA CATARINA</text>
     {routes&&filtered.map(c=>{const [x,y]=point([c.lon,c.lat]);return <g key={c.name}><path d={`M${sx} ${sy}Q${(x+sx)/2-70} ${(y+sy)/2} ${x} ${y}`} stroke={c.name===selectedVisible.name?'#dadd8e':'#739280'} strokeWidth={c.name===selectedVisible.name?1.8:.8} fill="none" strokeDasharray="3 5" className="route-line"/>{!paused&&<circle r="2.3" fill="#e6ce86"><animateMotion dur={`${4+delay*.8}s`} repeatCount="indefinite" path={`M${sx} ${sy}Q${(x+sx)/2-70} ${(y+sy)/2} ${x} ${y}`} /></circle>}</g>;})}
     <g><circle cx={sx} cy={sy} r="6" fill="#dce891"/><text x={sx+12} y={sy+4} fill="#e8eee9" fontSize="10">Maringá · origem</text></g>
     {filtered.map(c=>{const [x,y]=point([c.lon,c.lat]),active=c.name===selectedVisible.name;return <g key={c.name} data-city="true" className="city-node" role="button" tabIndex="0" aria-label={`Selecionar ${c.name}`} onClick={()=>setSelected(c)} onKeyDown={e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();setSelected(c);}}}>
      <circle cx={x} cy={y} r="13" fill={active?'#b2cb8030':'transparent'} stroke={active?'#dce891':'none'} strokeWidth=".8"/>
      <circle cx={x} cy={y} r="4.5" fill={active?'#e4eb9a':'#6ebb9a'} stroke="#10281f" strokeWidth="1.5"/>
      <text x={x+12} y={y-7} fill={active?'#f1f2ce':'#c2d2c6'} fontSize="8.7" fontWeight={active?600:400}>{c.name}</text>
      {active&&<text x={x+12} y={y+5} fill="#d0dca3" fontSize="7.5">{money(c.revenue,true)}</text>}
     </g>;})}
    </svg>}
    <div className="map-controls"><button aria-label="Aproximar mapa" onClick={()=>zoom(.8)}><Plus size={16}/></button><button aria-label="Afastar mapa" onClick={()=>zoom(1.25)}><Minus size={16}/></button><button aria-label="Ver todo o Paraná" onClick={()=>setView({x:0,y:0,w:850,h:610})}><Maximize size={16}/></button><button aria-label="Focar sul e sudeste" onClick={()=>setView(initialView)}><MapPin size={16}/></button></div>
    <div className="map-footer"><span><i/> Origem: Maringá · arraste para explorar</span><a href="https://servicodados.ibge.gov.br/api/docs/malhas?versao=3" target="_blank" rel="noreferrer">Base geográfica: IBGE</a></div>
   </div>
   <aside className="territory-panel panel"><div className="eyebrow">CARTEIRAS DE EXEMPLO</div><h3>Oportunidades no mapa</h3><label className="sr-only" htmlFor="seller">Filtrar carteira</label><select id="seller" value={seller} onChange={e=>setSeller(e.target.value)}><option value="all">Todas as carteiras</option><option>Carteira A</option><option>Carteira B</option><option>Carteira C</option></select><div className="city-list">{filtered.map(c=><button key={c.name} className={selectedVisible.name===c.name?'city-row selected':'city-row'} onClick={()=>setSelected(c)}><span><MapPin size={14}/>{c.name}</span><small>{money(c.revenue,true)}<ArrowUpRight size={13}/></small></button>)}</div><div className="city-detail"><span className="eyebrow">{selectedVisible.seller}</span><h3>{selectedVisible.name}</h3><div><span>Margem bruta</span><strong>{percent(selectedVisible.margin)}</strong></div><div><span>Clientes</span><strong>{selectedVisible.clients}</strong></div><div><span>Pedidos</span><strong>{selectedVisible.orders}</strong></div></div></aside>
  </div>
  <div className="simulation panel"><div className="simulation-heading"><div className="icon-tile"><Truck size={20}/></div><div><h3>Simule o ritmo das entregas</h3><p>Visualize como um atraso muda o trânsito nas rotas de exemplo.</p></div><button className="subtle-button" onClick={()=>setDelay(0)}><RotateCcw size={14}/> Reiniciar</button></div><div className="simulation-controls"><label htmlFor="delay">Atraso adicional <strong>{delay} {delay===1?'dia':'dias'}</strong></label><input id="delay" aria-label="Dias de atraso simulado" type="range" min="0" max="7" value={delay} onChange={e=>setDelay(Number(e.target.value))}/><div><span>Prazo ilustrativo</span><strong>{2+delay} dias</strong></div><p>As linhas são ligações esquemáticas, não trajetos rodoviários. A simulação altera a animação e o prazo ilustrativo, sem estimar perdas financeiras.</p></div></div>
 </div>;
}
