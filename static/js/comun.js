/* Funciones compartidas por todas las páginas (JavaScript) */
var MES=['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Setiembre','Octubre','Noviembre','Diciembre'];
var RUTAS={Inicio:'/',Publicaciones:'/publicaciones',Clientes:'/clientes',Pedidos:'/pedidos',Productos:'/productos',Reportes:'/reportes','Configuración':'/configuracion'};
function $(i){return document.getElementById(i)}
function irA(k){location.href=RUTAS[k]}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function money(n){return Number(n||0).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}
function pad(n){return ('000'+n).slice(-4)}
function fd(s){if(!s)return '—';var p=String(s).slice(0,10).split('-');return p[2]+'/'+p[1]+'/'+p[0]}
function num(x){return parseFloat(String(x).replace(',','.'))||0}
function hoy(){var d=new Date();return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
function toast(s){var t=$('t');t.textContent=s;t.classList.add('show');setTimeout(function(){t.classList.remove('show')},2500)}
function api(m,u,b){return fetch(u,{method:m,headers:{'Content-Type':'application/json'},body:b?JSON.stringify(b):undefined}).then(function(r){return r.json().then(function(j){if(!r.ok)throw new Error(j.error||'Error del servidor');return j})})}
function falla(e){toast(e.message||'Sin conexión con el servidor')}
function despues(){if(window.recargar)recargar()}
function ago(ts){var m=Math.max(1,Math.round((Date.now()-ts)/6e4));return m<60?'hace '+m+' min':m<1440?'hace '+Math.round(m/60)+' horas':'hace '+Math.round(m/1440)+' días'}
// ---- ventana emergente y formularios
function showM(h,w){var b=$('mb');b.className='mb'+(w?' w':'');b.innerHTML=h;$('m').classList.add('show')}
function closeM(){$('m').classList.remove('show')}
$('m').addEventListener('mousedown',function(e){if(e.target===this)closeM()});
function form(title,F,ok,btn){var h='<h2 style="font-size:17px">'+title+'</h2><div class="fg">';
F.forEach(function(f){h+='<label'+(f.w?' style="grid-column:1/-1"':'')+'>'+f.l;var v=f.v==null?'':f.v;
if(f.t=='select')h+='<select id="f_'+f.k+'">'+f.o.map(function(o){return '<option'+(o==v?' selected':'')+'>'+esc(o)+'</option>'}).join('')+'</select>';
else if(f.t=='area')h+='<textarea id="f_'+f.k+'" rows="2">'+esc(v)+'</textarea>';
else h+='<input id="f_'+f.k+'" type="'+(f.t||'text')+'" value="'+esc(v)+'"'+(f.dl?' list="dl_'+f.k+'"':'')+(f.t=='number'?' step="any" min="0"':'')+'>'+(f.dl?'<datalist id="dl_'+f.k+'">'+f.dl.map(function(x){return '<option value="'+esc(x)+'">'}).join('')+'</datalist>':'');
h+='</label>'});
h+='</div><div class="row"><button class="x" onclick="closeM()">Cancelar</button><button id="okb">'+(btn||'Guardar')+'</button></div>';showM(h);
$('okb').onclick=function(){var v={};F.forEach(function(f){v[f.k]=$('f_'+f.k).value.trim()});ok(v).then(function(){closeM();despues()},falla)}}
function twoStep(b,fn){if(b.dataset.s){fn();return}b.dataset.s=1;var t=b.textContent;b.textContent='¿Seguro? Toca otra vez';setTimeout(function(){b.dataset.s='';b.textContent=t},3000)}
// ---- pedidos
function meas(o){return o.ancho>0?o.ancho+' × '+o.alto+' m':'—'}
function area(o){return Math.round(o.ancho*o.alto*o.cantidad*100)/100}
function chip(o){return '<span class="st '+(o.estado=='C'?'ok':'p')+'" data-tog="'+o.id+'">'+(o.estado=='C'?'Completado':'En proceso')+'</span>'}
function tablaPedidos(L){if(!L.length)return '<p style="color:var(--mut);padding:14px">No se encontraron pedidos.</p>';
return '<div class="tw"><table><thead><tr><th>N°</th><th>Fecha</th><th>Cliente</th><th>Producto</th><th>Medidas</th><th>Cant.</th><th>Material</th><th>Total</th><th>Estado</th></tr></thead><tbody>'+L.map(function(o){return '<tr data-id="'+o.id+'"><td>#'+pad(o.id)+'</td><td>'+fd(o.fecha)+'</td><td>'+esc(o.cliente)+'</td><td>'+esc(o.producto)+'</td><td>'+meas(o)+'</td><td>'+o.cantidad+'</td><td>'+esc(o.material)+'</td><td>S/ '+money(o.total)+'</td><td>'+chip(o)+'</td></tr>'}).join('')+'</tbody></table></div>'}
function resumen(L){return kp([['Pedidos',L.length],['Total vendido','S/ '+money(L.reduce(function(s,o){return s+o.total},0))],['Área impresa',Math.round(L.reduce(function(s,o){return s+o.ancho*o.alto*o.cantidad},0))+' m²'],['Piezas',L.reduce(function(s,o){return s+o.cantidad},0)]])}
function kp(a){return '<div class="kp">'+a.map(function(x){return '<div><b>'+x[1]+'</b><small>'+x[0]+'</small></div>'}).join('')+'</div>'}
function nuevoPedido(id,pre){Promise.all([api('GET','/api/productos'),api('GET','/api/clientes'),api('GET','/api/materiales'),id?api('GET','/api/pedidos/'+id):Promise.resolve(null)]).then(function(r){
var P=r[0],C=r[1],M=r[2],o=r[3],auto=!o;
function precio(n){return P.filter(function(p){return p.nombre==n})[0]}
form(o?'Editar pedido #'+pad(o.id):'Nueva venta / pedido',[
{k:'cliente',l:'Nombre del cliente (escribe uno nuevo si no existe)',dl:C.map(function(c){return c.nombre}),v:o?o.cliente:(pre||''),w:1},
{k:'producto',l:'Producto / servicio',t:'select',o:P.map(function(p){return p.nombre}),v:o&&o.producto,w:1},
{k:'ancho',l:'Ancho (m)',t:'number',v:o?o.ancho:''},{k:'alto',l:'Alto (m)',t:'number',v:o?o.alto:''},{k:'cantidad',l:'Cantidad',t:'number',v:o?o.cantidad:1},{k:'total',l:'Total (S/)',t:'number',v:o?o.total:''},
{k:'material',l:'Tipo de material (elige o escribe uno nuevo)',dl:M.map(function(m){return m.nombre}),v:o?o.material:'',w:1},
{k:'fecha',l:'Fecha',t:'date',v:o?String(o.fecha).slice(0,10):hoy()},{k:'estado',l:'Estado',t:'select',o:['En proceso','Completado'],v:o&&o.estado=='C'?'Completado':'En proceso'},
{k:'notas',l:'Notas / detalles',t:'area',v:o?o.notas:'',w:1}],function(v){
if(!v.cliente||!v.fecha){toast('Escribe el cliente y la fecha');return Promise.reject({message:'Faltan datos'})}
v.estado=v.estado=='Completado'?'C':'P';return o?api('PUT','/api/pedidos/'+o.id,v).then(function(){toast('Pedido guardado')}):api('POST','/api/pedidos',v).then(function(){toast('Venta registrada')})},o?'Guardar cambios':'Registrar venta');
function rc(){if(!auto)return;var p=precio($('f_producto').value);if(!p)return;$('f_total').value=Math.round((p.unidad=='m²'?num($('f_ancho').value)*num($('f_alto').value)*num($('f_cantidad').value)*p.precio:num($('f_cantidad').value)*p.precio)*100)/100||''}
['producto','ancho','alto','cantidad'].forEach(function(k){$('f_'+k).oninput=$('f_'+k).onchange=rc});$('f_total').oninput=function(){auto=false};rc()},falla)}
function verPedido(id){api('GET','/api/pedidos/'+id).then(function(o){
showM('<h2 style="font-size:18px">Pedido #'+pad(o.id)+' '+chip(o)+'</h2><div class="dl">'+
[['Cliente','<a class="lk" data-cl="'+o.cliente_id+'">'+esc(o.cliente)+'</a>'],['Teléfono',esc(o.telefono||'—')],['Producto',esc(o.producto)],['Fecha de compra',fd(o.fecha)],['Medidas (ancho × alto)',meas(o)],['Cantidad',o.cantidad],['Área total',o.ancho>0?area(o)+' m²':'—'],['Tipo de material',esc(o.material||'—')],['Total','<b>S/ '+money(o.total)+'</b>']].map(function(x){return '<div><small>'+x[0]+'</small>'+x[1]+'</div>'}).join('')+
'<div style="grid-column:1/-1"><small>Notas</small>'+esc(o.notas||'—')+'</div></div><div class="row" style="margin-top:6px"><button onclick="nuevoPedido('+o.id+')">Editar</button><button class="g" onclick="cambiarEstado('+o.id+',1)">Marcar '+(o.estado=='C'?'en proceso':'completado')+'</button><button class="d" onclick="twoStep(this,function(){borrarPedido('+o.id+')})">Eliminar</button><button class="x" onclick="closeM()">Cerrar</button></div>',1)},falla)}
function cambiarEstado(id,reabrir){api('POST','/api/pedidos/'+id+'/estado').then(function(){toast('Estado actualizado');if(reabrir)verPedido(id);despues()},falla)}
function borrarPedido(id){api('DELETE','/api/pedidos/'+id).then(function(){closeM();toast('Pedido eliminado');despues()},falla)}
// ---- clientes, publicaciones, productos
function formCliente(id){(id?api('GET','/api/clientes/'+id).then(function(r){return r.cliente}):Promise.resolve({})).then(function(c){
form(id?'Editar cliente':'Nuevo cliente',[{k:'nombre',l:'Nombre o empresa',v:c.nombre,w:1},{k:'telefono',l:'Teléfono',v:c.telefono},{k:'correo',l:'Correo',v:c.correo},{k:'direccion',l:'Dirección',v:c.direccion,w:1}],function(v){
if(!v.nombre){toast('Escribe el nombre');return Promise.reject({message:'Falta el nombre'})}return (id?api('PUT','/api/clientes/'+id,v):api('POST','/api/clientes',v)).then(function(){toast('Cliente guardado')})})},falla)}
function verCliente(id){api('GET','/api/clientes/'+id).then(function(r){var c=r.cliente,L=r.pedidos;
showM('<h2 style="font-size:18px">'+esc(c.nombre)+'</h2><div class="dl"><div><small>Teléfono</small>'+esc(c.telefono||'—')+'</div><div><small>Correo</small>'+esc(c.correo||'—')+'</div><div><small>Dirección</small>'+esc(c.direccion||'—')+'</div><div><small>Cliente desde</small>'+fd(c.creado)+'</div><div><small>Pedidos</small>'+L.length+'</div><div><small>Total comprado</small><b>S/ '+money(L.reduce(function(s,o){return s+o.total},0))+'</b></div></div><h3 style="margin:12px 0 4px;font-size:14px">Historial de compras</h3>'+tablaPedidos(L)+'<div class="row" style="margin-top:8px"><button onclick="nuevoPedido(0,\''+esc(c.nombre).replace(/'/g,'')+'\')">Nuevo pedido</button><button onclick="formCliente('+c.id+')">Editar</button><a class="btn g" href="/api/csv/cliente?id='+c.id+'">⬇ CSV</a><button class="d" onclick="twoStep(this,function(){api(\'DELETE\',\'/api/clientes/'+c.id+'\').then(function(){closeM();despues()},falla)})">Eliminar</button><button class="x" onclick="closeM()">Cerrar</button></div>',1)},falla)}
function formPub(id){Promise.all([api('GET','/api/productos'),id?api('GET','/api/publicaciones').then(function(l){return l.filter(function(x){return x.id==id})[0]}):Promise.resolve({})]).then(function(r){var b=r[1];
form(id?'Editar publicación':'Nueva publicación',[{k:'titulo',l:'Título',v:b.titulo,w:1},{k:'descripcion',l:'Descripción',t:'area',v:b.descripcion,w:1},{k:'categoria',l:'Categoría',t:'select',o:r[0].map(function(p){return p.nombre}),v:b.categoria},{k:'estado',l:'Estado',t:'select',o:['Publicada','Borrador'],v:b.estado},{k:'fecha',l:'Fecha',t:'date',v:b.fecha?String(b.fecha).slice(0,10):hoy()}],function(v){
if(!v.titulo){toast('Escribe un título');return Promise.reject({message:'Falta el título'})}return (id?api('PUT','/api/publicaciones/'+id,v):api('POST','/api/publicaciones',v)).then(function(){toast('Publicación guardada')})})},falla)}
function formProd(id){api('GET','/api/productos').then(function(L){var p=L.filter(function(x){return x.id==id})[0]||{};
form(id?'Editar producto':'Nuevo producto / servicio',[{k:'nombre',l:'Nombre',v:p.nombre,w:1},{k:'unidad',l:'Se cobra por',t:'select',o:['m²','servicio','unidad'],v:p.unidad},{k:'precio',l:'Precio (S/)',t:'number',v:p.precio}],function(v){
if(!v.nombre){toast('Escribe el nombre');return Promise.reject({message:'Falta el nombre'})}return (id?api('PUT','/api/productos/'+id,v):api('POST','/api/productos',v)).then(function(){toast('Producto guardado')})})},falla)}
function verActividades(){api('GET','/api/actividades?limite=20').then(function(L){showM('<h2 style="font-size:17px">Actividades</h2>'+L.map(function(a){return '<div class="act"><div class="i" style="background:'+a.col+'">'+a.i+'</div><div>'+esc(a.t)+'<small>'+esc(a.s)+' • '+ago(a.ts)+'</small></div></div>'}).join('')+'<div class="row"><button class="x" onclick="closeM()">Cerrar</button></div>')},falla)}
// ---- gráficos
function nice(v){var p=Math.pow(10,Math.floor(Math.log(v||1)/Math.LN10)),m=[1,2,2.5,5,10];for(var i=0;i<5;i++)if(m[i]*p>=v)return m[i]*p;return 10*p}
function sh(v){return v>=1000?(v/1000).toFixed(1)+'k':Math.round(v)}
function bars(a){var mx=a.reduce(function(m,x){return Math.max(m,x.v)},0),M=nice(mx/4)*4||4,s='<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff2fa8"/><stop offset="1" stop-color="#1a8cff"/></linearGradient></defs>',n=a.length,w=560/n,i;
for(i=0;i<=4;i++){var y=190-i*.25*170;s+='<line x1="50" x2="620" y1="'+y+'" y2="'+y+'" stroke="#1b2a52"/><text x="44" y="'+(y+3)+'" fill="#9fb0d6" font-size="9" text-anchor="end">'+sh(M*i/4)+'</text>'}
a.forEach(function(d,i){var h=d.v/M*170,x=55+i*w+w*.15;s+='<rect x="'+x+'" y="'+(190-h)+'" width="'+w*.7+'" height="'+h+'" rx="4" fill="url(#bg)"/>'+(d.v?'<text x="'+(x+w*.35)+'" y="'+(186-h)+'" fill="#fff" font-size="9" text-anchor="middle">'+sh(d.v)+'</text>':'')+'<text x="'+(x+w*.35)+'" y="206" fill="#9fb0d6" font-size="10" text-anchor="middle">'+d.l+'</text>'});
return '<svg viewBox="0 0 640 215" style="width:100%">'+s+'</svg>'}
// ---- clics globales: estado, cliente, pedido
document.addEventListener('click',function(e){var t=e.target.closest('[data-tog],[data-cl],tr[data-id]');if(!t)return;if(t.dataset.tog)cambiarEstado(+t.dataset.tog);else if(t.dataset.cl){closeM();verCliente(+t.dataset.cl)}else verPedido(+t.dataset.id)});
