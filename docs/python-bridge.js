"use strict";
// Giữ giao diện hiện có; các yêu cầu dữ liệu và CSV chạy qua Python trong trình duyệt.
let runtimePromise = null;
window.weatherPythonReady = false;
function pythonRuntime() {
  if (!runtimePromise) runtimePromise = (async () => {
    if (typeof loadPyodide !== 'function') throw new Error('Không tải được công cụ xử lý. Hãy tải lại trang.');
    const py = await loadPyodide({indexURL:'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/'});
    const code = await fetch(new URL('./weather.py', document.baseURI));
    if (!code.ok) throw new Error('Không tải được chương trình xử lý. Hãy thử lại.');
    await py.runPythonAsync(await code.text());
    window.weatherPythonReady = true;
    return py.globals.get('dispatch');
  })().catch(error => {runtimePromise = null; throw error;});
  return runtimePromise;
}
window.weatherFetch = async function(input, options = {}) {
  const signal = options.signal;
  let onAbort;
  const operation = (async () => {
    const dispatch = await pythonRuntime();
    if (signal?.aborted) throw new DOMException('Aborted','AbortError');
    const url = new URL(input, window.location.origin);
    const result = JSON.parse(await dispatch(url.pathname, url.search.slice(1)));
    if (signal?.aborted) throw new DOMException('Aborted','AbortError');
    if ('csv' in result) {
      const content = new Blob(['\uFEFF',result.csv],{type:'text/csv;charset=utf-8'});
      return new Response(content,{status:result.status});
    }
    return new Response(JSON.stringify(result.body),{status:result.status,headers:{'Content-Type':'application/json;charset=utf-8'}});
  })();
  if (!signal) return operation;
  if (signal.aborted) throw new DOMException('Aborted','AbortError');
  const aborted = new Promise((_,reject)=>{
    onAbort=()=>reject(new DOMException('Aborted','AbortError'));
    signal.addEventListener('abort',onAbort,{once:true});
  });
  try {return await Promise.race([operation,aborted]);}
  finally {signal.removeEventListener('abort',onAbort);}
};
