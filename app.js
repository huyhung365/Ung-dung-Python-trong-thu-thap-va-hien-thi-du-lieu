'use strict';
const $ = id => document.getElementById(id);
let snapshot = null, page = 0;
let weatherRequest = 0, weatherController = null;
let chosenPlace = {label: 'Hà Nội', latitude: 21.0285, longitude: 105.8542};
let placeResults = [], placeSearchRequest = 0, placeSearchController = null;
const pageSize = 48;
const series = [
  ['temperature_2m', 'Nhiệt độ không khí', '°C', '#cc681c'],
  ['relative_humidity_2m', 'Độ ẩm tương đối', '%', '#357cc0'],
  ['shortwave_radiation', 'Bức xạ mặt trời · GHI', 'W/m²', '#07837a'],
];
const number = value => value == null ? '—' : new Intl.NumberFormat('vi-VN', {maximumFractionDigits: 1}).format(value);
const dateText = (stamp, short = false) => new Intl.DateTimeFormat('vi-VN', {
  timeZone: snapshot.meta.timezone, day:'2-digit', month:'2-digit',
  ...(short ? {} : {year:'numeric', hour:'2-digit', minute:'2-digit', hourCycle:'h23'}),
}).format(new Date(stamp * 1000));
const svgNode = (tag, attrs = {}, content) => {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, String(value));
  if (content != null) node.textContent = content;
  return node;
};
function mean(key) {
  const values = snapshot.rows.map(r => r[key]).filter(v => v != null);
  return values.length ? values.reduce((a,b) => a+b, 0) / values.length : null;
}
function renderChart(key, title, unit, color) {
  const rows = snapshot.rows;
  const card = document.createElement('article'); card.className = 'chart-card';
  const label = document.createElement('div'); label.className = 'chart-title';
  const name = document.createElement('span'); name.textContent = `${title} (${unit})`;
  const readout = document.createElement('span'); readout.className = 'chart-readout';
  readout.textContent = 'Chọn một điểm trên biểu đồ'; label.append(name, readout); card.append(label);
  const svg = svgNode('svg', {viewBox:'0 0 900 195', role:'img', 'aria-label':`${title} theo giờ; số liệu chi tiết có trong bảng bên dưới.`});
  const values = rows.map(r=>r[key]).filter(v=>v!=null);
  if (!values.length) {readout.textContent='Không có dữ liệu cho đại lượng này'; card.append(svg); return card;}
  let low = Math.min(...values), high = Math.max(...values);
  if (key !== 'temperature_2m') low = 0;
  if (key === 'relative_humidity_2m') high = 100;
  else {const pad = Math.max((high-low)*0.08, 1); if(key==='temperature_2m') low -= pad; high += pad;}
  const x = i => 60 + i / Math.max(1,rows.length-1) * 820;
  const y = value => 151 - (value-low)/Math.max(1,high-low)*126;
  for(let t=0;t<=3;t++) {
    const value=low+(high-low)*t/3, yp=y(value);
    svg.append(svgNode('line',{x1:60,x2:880,y1:yp,y2:yp,class:'axis'}));
    svg.append(svgNode('text',{x:50,y:yp+4,'text-anchor':'end'},number(value)));
  }
  const indexes = [...new Set([0, Math.floor((rows.length-1)/3), Math.floor(2*(rows.length-1)/3),rows.length-1])];
  for(const i of indexes) svg.append(svgNode('text',{x:x(i),y:178,'text-anchor':i===0?'start':i===rows.length-1?'end':'middle'},dateText(rows[i].timestamp,true)));
  for(const period of ['past_model','forecast']) {
    let d='', connected=false;
    rows.forEach((row,i)=>{
      if(row.period !== period || row[key]==null) {connected=false;return;}
      d += `${connected?'L':'M'}${x(i).toFixed(2)},${y(row[key]).toFixed(2)} `; connected=true;
    });
    svg.append(svgNode('path',{d,class:'trace',stroke:color,...(period==='forecast'?{'stroke-dasharray':'6 4'}:{})}));
  }
  const marker=svgNode('line',{x1:60,x2:60,y1:20,y2:153,class:'marker',visibility:'hidden'}); svg.append(marker);
  svg.addEventListener('pointermove',e=>{
    const rect=svg.getBoundingClientRect();
    const px=(e.clientX-rect.left)/rect.width*900;
    const i=Math.max(0,Math.min(rows.length-1,Math.round((px-60)/820*(rows.length-1))));
    marker.setAttribute('x1',x(i));marker.setAttribute('x2',x(i));marker.setAttribute('visibility','visible');
    const row=rows[i];
    readout.textContent=`${dateText(row.timestamp)} · ${number(row[key])} ${unit}`;
  });
  svg.addEventListener('pointerleave',()=>marker.setAttribute('visibility','hidden'));
  card.append(svg); return card;
}
function renderTable() {
  const total = snapshot.rows.length, start = page*pageSize;
  $('table-body').replaceChildren();
  for(const row of snapshot.rows.slice(start,start+pageSize)) {
    const tr = document.createElement('tr');
    const values = [dateText(row.timestamp),row.period==='past_model'?'Quá khứ mô hình':'Hôm nay / dự báo',number(row.temperature_2m),number(row.relative_humidity_2m),number(row.shortwave_radiation)];
    for (const value of values) {const td=document.createElement('td');td.textContent=value;tr.append(td);}
    $('table-body').append(tr);
  }
  $('table-count').textContent=`${start+1}–${Math.min(total,start+pageSize)} / ${total} dòng`;
  $('page-label').textContent=`Trang ${page+1} / ${Math.ceil(total/pageSize)}`;
  $('prev').disabled=page===0;$('next').disabled=start+pageSize>=total;
}
function render() {
  const meta = snapshot.meta, rows=snapshot.rows, query=meta.requested;
  $('location').textContent=snapshot.placeLabel || `${query.latitude.toFixed(4)}°, ${query.longitude.toFixed(4)}°`;
  const fetched = new Intl.DateTimeFormat('vi-VN',{timeZone:meta.timezone,dateStyle:'short',timeStyle:'short'}).format(new Date(meta.fetched_at_utc));
  $('metadata').textContent=`Tọa độ: ${query.latitude.toFixed(4)}°, ${query.longitude.toFixed(4)}°. ${dateText(rows[0].timestamp)} – ${dateText(rows.at(-1).timestamp)} · Múi giờ: ${meta.timezone}. Ô lưới nguồn: ${Number(meta.grid_latitude).toFixed(4)}°, ${Number(meta.grid_longitude).toFixed(4)}°. Lấy dữ liệu: ${fetched}.`;
  $('count').textContent=number(rows.length);
  const past=rows.filter(r=>r.period==='past_model').length;
  $('period-count').textContent=`${past} giờ quá khứ · ${rows.length-past} giờ dự báo`;
  $('temperature').textContent=`${number(mean('temperature_2m'))} °C`;
  $('humidity').textContent=`${number(mean('relative_humidity_2m'))} %`;
  const radiation=rows.map(r=>r.shortwave_radiation).filter(v=>v!=null);
  $('radiation').textContent=`${number(radiation.length?Math.max(...radiation):null)} W/m²`;
  $('charts').replaceChildren(...series.map(s=>renderChart(...s)));
  page=0;renderTable();$('output').hidden=false;$('empty').hidden=true;
  $('status').textContent=`Đã tải ${rows.length} giờ dữ liệu.${meta.missing_values ? ` Có ${meta.missing_values} giá trị thiếu, hiển thị bằng dấu —.` : ''} Kết quả được lưu đệm tối đa 10 phút.`;
}
async function loadData(event) {
  event?.preventDefault(); if (!$('query-form').reportValidity()) return;
  $('error').hidden=true;
  const params=new URLSearchParams(new FormData($('query-form')));
  if(Number(params.get('past_days'))+Number(params.get('forecast_days'))===0) {
    $('error').textContent='Hãy chọn ít nhất một ngày quá khứ hoặc dự báo.';$('error').hidden=false;return;
  }
  const requestId = ++weatherRequest;
  weatherController?.abort();
  const placeLabel = chosenPlace && Number(params.get('latitude')) === chosenPlace.latitude && Number(params.get('longitude')) === chosenPlace.longitude ? chosenPlace.label : '';
  // Ẩn kết quả cũ trong lúc đổi địa điểm để tránh nhầm vị trí của số liệu.
  $('output').hidden=true;$('empty').hidden=true;$('submit').disabled=true;
  $('submit').textContent='Đang lấy dữ liệu…';$('status').textContent='Đang kết nối Open-Meteo…';
  const controller=new AbortController();weatherController=controller;const timer=setTimeout(()=>controller.abort(),45000);
  try {
    const data=await WeatherAPI.weather(params, controller.signal);
    if(requestId !== weatherRequest) return;
    data.placeLabel=placeLabel;snapshot=data;render();
  } catch(error) {
    if(requestId !== weatherRequest) return;
    snapshot=null;
    $('error').textContent=error.name==='AbortError'?'Kết nối quá lâu. Hãy kiểm tra Internet và thử lại.':error.message;
    $('error').hidden=false;$('status').textContent='Chưa lấy được dữ liệu.';$('empty').hidden=false;
  } finally {clearTimeout(timer);if(requestId === weatherRequest){$('submit').disabled=false;$('submit').textContent='Lấy dữ liệu';}}
}
$('query-form').addEventListener('submit',loadData);
$('prev').addEventListener('click',()=>{page--;renderTable();});
$('next').addEventListener('click',()=>{page++;renderTable();});
$('download').addEventListener('click',async()=>{
  if(!snapshot) return;
  const selected = snapshot;
  $('download').disabled=true;
  try {
    const blob=new Blob([WeatherAPI.csv(selected)], {type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');
    a.href=url;a.download=`weather_${selected.meta.requested.latitude}_${selected.meta.requested.longitude}.csv`;
    document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  } catch(error) {$('error').textContent=error.message;$('error').hidden=false;}
  finally {$('download').disabled=false;}
});
// Form riêng để Enter trong ô tìm địa điểm không gửi nhầm form thời tiết.
$('location-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (!$('location-form').reportValidity()) return;
  const name = $('place-search').value.trim();
  const requestId = ++placeSearchRequest;
  placeSearchController?.abort();
  const controller = new AbortController(); placeSearchController = controller;
  const timer = setTimeout(() => controller.abort(), 30000);
  $('place-options').hidden = true;placeResults = [];
  $('search-place').disabled = true;
  $('place-status').textContent = 'Đang tìm địa điểm…';
  try {
    const data = await WeatherAPI.locations(name, controller.signal);
    if (requestId !== placeSearchRequest) return;
    placeResults = data.results;
    $('place-select').replaceChildren(new Option('— Chọn địa điểm —', ''));
    placeResults.forEach((place,i) => $('place-select').add(new Option(`${place.label} (${place.latitude.toFixed(3)}, ${place.longitude.toFixed(3)})`, String(i))));
    $('place-options').hidden = !placeResults.length;
    $('place-status').textContent = placeResults.length ? `Tìm thấy ${placeResults.length} kết quả. Chọn một địa điểm bên dưới.` : 'Không tìm thấy. Thử tên ngắn hơn, tên không dấu hoặc nhập tọa độ trực tiếp.';
    if (placeResults.length) $('place-select').focus();
  } catch(error) {
    if(requestId !== placeSearchRequest) return;
    $('place-status').textContent = error.name === 'AbortError' ? 'Tìm kiếm quá lâu. Thử lại hoặc nhập tọa độ trực tiếp.' : error.message;
  } finally {
    clearTimeout(timer);
    if(requestId === placeSearchRequest) $('search-place').disabled = false;
  }
});
$('place-search').addEventListener('input', () => {
  ++placeSearchRequest;placeSearchController?.abort();
  $('search-place').disabled=false;$('place-options').hidden=true;placeResults=[];
  $('place-status').textContent='Nhập tên có dấu hoặc không dấu rồi tìm.';
});
$('place-select').addEventListener('change', () => {
  if ($('place-select').value === '') return;
  const place = placeResults[Number($('place-select').value)];
  if (!place) return;
  chosenPlace = place;
  $('latitude').value = place.latitude; $('longitude').value = place.longitude;
  $('selected-place').textContent = `Đã chọn: ${place.label}`;
  loadData();
});
for (const id of ['latitude','longitude']) $(id).addEventListener('input', () => {
  chosenPlace = null; $('place-select').value = '';
  $('selected-place').textContent = 'Đang dùng tọa độ nhập thủ công.';
});
loadData();
