'use strict';
const WeatherAPI = (() => {
  const variables = ['temperature_2m', 'relative_humidity_2m', 'shortwave_radiation'];
  const cache = new Map();
  async function json(url, signal) {
    const response = await fetch(url, {signal});
    if (response.status === 429) throw new Error('Open-Meteo đang giới hạn lượt truy cập. Hãy thử lại sau.');
    const data = await response.json();
    if (!response.ok || data.error) throw new Error(data.reason || 'Nguồn dữ liệu tạm thời không đáp ứng.');
    return data;
  }
  function normalise(data, requested, now = new Date()) {
    const hourly = data.hourly;
    const zone = data.timezone;
    const day = new Intl.DateTimeFormat('en-CA', {timeZone: zone, year:'numeric', month:'2-digit', day:'2-digit'});
    const today = day.format(now);
    if (!hourly || !Array.isArray(hourly.time) || !hourly.time.length ||
        variables.some(key => !Array.isArray(hourly[key]) || hourly[key].length !== hourly.time.length)) {
      throw new Error('Nguồn thời tiết trả về dữ liệu không hợp lệ.');
    }
    const rows = hourly.time.map((stamp, i) => {
      if (!Number.isFinite(stamp) || (i && stamp <= hourly.time[i-1])) throw new Error('Mốc thời gian không hợp lệ.');
      const date = new Date(stamp * 1000);
      const row = {timestamp:stamp, time_utc:date.toISOString(), period:day.format(date) < today ? 'past_model' : 'forecast'};
      for (const key of variables) {
        const value = hourly[key][i];
        if (value !== null && !Number.isFinite(value)) throw new Error('Số liệu thời tiết không hợp lệ.');
        row[key] = value;
      }
      return row;
    });
    return {rows, meta:{requested, timezone:zone, grid_latitude:data.latitude, grid_longitude:data.longitude,
      fetched_at_utc:now.toISOString(), source:'Open-Meteo Forecast API',
      missing_values:rows.reduce((n, row) => n + variables.filter(key => row[key] === null).length, 0)}};
  }
  async function weather(params, signal) {
    const requested = {};
    for (const [key, min, max, integer] of [['latitude',-90,90,false],['longitude',-180,180,false],['past_days',0,92,true],['forecast_days',0,16,true]]) {
      const raw = params.get(key), value = Number(raw);
      if (raw === null || !raw.trim() || !Number.isFinite(value) || value < min || value > max || (integer && !Number.isInteger(value))) throw new Error('Thông số tọa độ hoặc số ngày không hợp lệ.');
      requested[key] = value;
    }
    if (!requested.past_days && !requested.forecast_days) throw new Error('Hãy chọn ít nhất một ngày.');
    const key = JSON.stringify(requested), saved = cache.get(key);
    if (saved && Date.now() - saved.time < 600000) return structuredClone(saved.data);
    const query = new URLSearchParams({...requested, hourly:variables.join(','), timezone:'auto', timeformat:'unixtime', temperature_unit:'celsius'});
    const data = normalise(await json(`https://api.open-meteo.com/v1/forecast?${query}`, signal), requested);
    cache.set(key, {time:Date.now(), data});
    if (cache.size > 32) cache.delete(cache.keys().next().value);
    return structuredClone(data);
  }
  async function locations(name, signal) {
    name = name.trim().replace(/^(?:thành phố|thanh pho|tỉnh|tinh|tp\.?)\s+/i, '').trim();
    if (name.length < 2 || name.length > 80) throw new Error('Nhập tên địa điểm từ 2 đến 80 ký tự.');
    const query = new URLSearchParams({name, count:20, language:'vi', format:'json', countryCode:'VN'});
    const data = await json(`https://geocoding-api.open-meteo.com/v1/search?${query}`, signal);
    return {results:(data.results || []).filter(p => p.country_code === 'VN' && Number.isFinite(p.latitude) && Number.isFinite(p.longitude)).map(p => ({
      name:p.name, latitude:p.latitude, longitude:p.longitude,
      label:[...new Set([p.name, p.admin2, p.admin1, p.country || 'Việt Nam'].filter(Boolean))].join(' · ')
    }))};
  }
  function csv(snapshot) {
    const m = snapshot.meta;
    const quote = value => '"' + String(value ?? '').replace(/"/g, '""') + '"';
    const rows = [['time_utc','timezone','period','temperature_c','relative_humidity_percent','shortwave_radiation_w_m2','requested_latitude','requested_longitude','grid_latitude','grid_longitude','source','fetched_at_utc']];
    for (const row of snapshot.rows) rows.push([row.time_utc,m.timezone,row.period,...variables.map(key => row[key]),m.requested.latitude,m.requested.longitude,m.grid_latitude,m.grid_longitude,m.source,m.fetched_at_utc]);
    return '\uFEFF' + rows.map(row => row.map(quote).join(',')).join('\r\n') + '\r\n';
  }
  return {weather, locations, csv, normalise};
})();
if (typeof module !== 'undefined') module.exports = WeatherAPI;
