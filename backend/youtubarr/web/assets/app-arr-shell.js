function actionBar(items='',right=''){return `<div class="actionbar"><div class="actionbar-left">${items}</div><div class="actionbar-right">${right}</div></div>`}
function actionButton(label,ic,onclick,cls=''){return `<button class="action-button ${cls}" onclick="${onclick}">${icon(ic)}<span>${label}</span></button>`}
function renderShell(){
  const m=state.boot.modules;
  $('#app').innerHTML=`<div class="shell">
    <header class="topbar">
      <div class="top-logo"><img src="/assets/logo.svg"></div>
      <div class="top-search">${icon('search')}<input id="globalSearch" placeholder="Search"></div>
      <div class="top-actions"><button class="top-action heart" title="YouTube source">♥</button><button class="top-action" title="Account">${icon('user')}</button><button class="top-action" title="Sign out" id="logoutTop">${icon('logout')}</button></div>
    </header>
    <aside class="sidebar">
      ${m.series?navGroup('series','Series','series',[['series-add','Add New'],['library-import','Library Import']]):''}
      ${m.music?navGroup('music','Music','music',[['music-add','Add New'],['music-import','Library Import']]):''}
      ${m.movies?navGroup('movies','Movies','movies',[['movies-add','Add New'],['movies-import','Library Import']]):''}
      ${navItem('calendar','Calendar','calendar')}
      ${navGroup('queue','Activity','history',[['queue','Queue'],['history','History'],['blocklist','Blocklist']], 'queueBadge')}
      ${navGroup('wanted-missing','Wanted','wanted',[['wanted-missing','Missing'],['wanted-cutoff','Cutoff Unmet']])}
      ${navGroup('settings','Settings','settings',[
        ['media-management','Media Management'],['profiles','Profiles'],['quality','Quality'],['custom-formats','Custom Formats'],['indexers','Indexers'],['download-clients','Download Clients'],['import-lists','Import Lists'],['connect','Connect'],['metadata','Metadata'],['metadata-source','Metadata Source'],['tags','Tags'],['general','General'],['ui','UI']
      ])}
      ${navGroup('status','System','system',[['status','Status'],['tasks','Tasks'],['logs','Logs'],['updates','Updates'],['backup','Backup']])}
      <div class="side-foot"><span class="live-dot"></span> Live <span class="muted">v${esc(state.boot.version)}</span></div>
    </aside>
    <main class="main" id="main"></main>
  </div>`;
  $$('.nav-item').forEach(n=>n.onclick=()=>navigate(n.dataset.route));
  $('#logoutTop').onclick=async()=>{await api('/api/logout',{method:'POST'});state.boot=await api('/api/bootstrap');renderLogin()};
  $('#globalSearch').onkeydown=e=>{if(e.key==='Enter'&&e.target.value.trim()){sessionStorage.setItem('ytQuery',e.target.value.trim());navigate('search')}};
  window.onhashchange=()=>route();
}
function navItem(route,label,ic,badge=''){return `<div class="nav-item" data-route="${route}">${icon(ic)}<span>${label}</span>${badge?`<span class="badge hidden" id="${badge}">0</span>`:''}</div>`}
function navGroup(route,label,ic,children=[],badge=''){return `<div class="nav-group">${navItem(route,label,ic,badge)}<div class="nav-sub">${children.map(([r,l])=>`<div class="nav-item" data-route="${r}"><span class="sub-spacer"></span><span>${l}</span></div>`).join('')}</div></div>`}
function navigate(route,params=''){location.hash=`#${route}${params?`?${params}`:''}`}
function parseRoute(){const raw=(location.hash||'#series').slice(1),[route,q='']=raw.split('?');return{route,params:new URLSearchParams(q)}}
async function route(force=false){
  if(!state.boot?.authenticated)return;
  const {route:r,params}=parseRoute();
  $$('.nav-item').forEach(n=>n.classList.toggle('active',n.dataset.route===r));
  const routes={
    series:seriesPage,'series-add':seriesAddPage,'library-import':libraryImportPage,
    music:musicPage,'music-add':musicAddPage,'music-import':musicImportPage,
    movies:moviesPage,'movies-add':moviesAddPage,'movies-import':moviesImportPage,
    calendar:calendarPage,queue:queuePage,history:historyPage,blocklist:blocklistPage,
    'wanted-missing':wantedMissingPage,'wanted-cutoff':wantedCutoffPage,
    search:searchPage,settings:settingsHome,'media-management':mediaPage,profiles:profilesPage,quality:qualityPage,'custom-formats':customFormatsPage,indexers:indexersPage,'download-clients':downloadClientsPage,'import-lists':importListsPage,connect:applicationsPage,metadata:metadataPage,'metadata-source':metadataSourcePage,tags:tagsPage,general:generalPage,ui:uiPage,
    status:statusPage,tasks:tasksPage,logs:logsPage,updates:updatesPage,backup:backupPage
  };
  try{await (routes[r]||seriesPage)(params,force)}catch(e){$('#main').innerHTML=actionBar()+`<div class="content"><div class="error-box">${esc(e.message)}</div></div>`}
  updateQueueBadge();
}
async function updateQueueBadge(){try{const rows=await api('/api/acquisitions');const n=rows.filter(x=>!['complete','failed'].includes(x.status)).length,b=$('#queueBadge');if(b){b.textContent=n;b.classList.toggle('hidden',!n)}}catch{}}
function imageFor(item){const imgs=item?.images||[];const img=imgs.find(x=>['poster','cover','fanart'].includes(x.coverType))||imgs[0];return img?.remoteUrl||img?.url||''}
function posterFallback(title=''){return `<div class="poster-fallback"><div class="play-mark">▶</div><span>${esc(title)}</span></div>`}
function setSeriesView(view){sessionStorage.setItem('seriesView',view);route(true)}
function setSeriesSort(sort){sessionStorage.setItem('seriesSort',sort);route(true)}
function setSeriesFilter(filter){sessionStorage.setItem('seriesFilter',filter);route(true)}
function toolbarMenu(id,items){return `<div class="tool-menu-wrap"><button class="action-button" onclick="document.getElementById('${id}').classList.toggle('open')">${icon('list')}<span>${items.label}</span></button><div class="tool-menu" id="${id}">${items.options.map(o=>`<button onclick="${o.action}">${o.label}</button>`).join('')}</div></div>`}
async function seriesPage(params){
  const id=params.get('id');if(id)return seriesDetail(Number(id));
  state.series=await api('/api/series');
  const view=sessionStorage.getItem('seriesView')||'posters',sort=sessionStorage.getItem('seriesSort')||'title',filter=sessionStorage.getItem('seriesFilter')||'all';
  let rows=[...state.series];
  if(filter==='monitored')rows=rows.filter(x=>x.monitored);if(filter==='unmonitored')rows=rows.filter(x=>!x.monitored);
  rows.sort((a,b)=>sort==='year'?(Number(b.year||0)-Number(a.year||0)):String(a.sortTitle||a.title).localeCompare(String(b.sortTitle||b.title)));
  const actions=actionButton('Update Filtered','refresh','route(true)')+actionButton('RSS Sync','refresh','rssSync()')+actionButton('Select Series','check','toggleSeriesSelect()')+actionButton('Test Parsing','list','testParsing()');
  const right=toolbarMenu('optionsMenu',{label:'Options',options:[{label:'Refresh',action:'route(true)'},{label:'Show monitored only',action:"setSeriesFilter('monitored')"}]})+toolbarMenu('viewMenu',{label:'View',options:[{label:'Posters',action:"setSeriesView('posters')"},{label:'Table',action:"setSeriesView('table')"}]})+toolbarMenu('sortMenu',{label:'Sort',options:[{label:'Title',action:"setSeriesSort('title')"},{label:'Year',action:"setSeriesSort('year')"}]})+toolbarMenu('filterMenu',{label:'Filter',options:[{label:'All',action:"setSeriesFilter('all')"},{label:'Monitored',action:"setSeriesFilter('monitored')"},{label:'Unmonitored',action:"setSeriesFilter('unmonitored')"}]});
  $('#main').innerHTML=actionBar(actions,right)+`<div class="content">${view==='table'?seriesTable(rows):seriesPosterGrid(rows)}</div>`;
}
function seriesPosterGrid(rows){return `<div class="arr-poster-grid" id="seriesGrid">${rows.map(s=>{const img=imageFor(s);return `<article class="arr-poster-card" onclick="if(!document.getElementById('seriesGrid')?.classList.contains('select-mode'))navigate('series','id=${s.id}')"><input type="checkbox" class="poster-check" data-id="${s.id}" onclick="event.stopPropagation()"><div class="arr-poster ${img?'':'broken'}">${img?`<img src="${esc(img)}" alt="${esc(s.title)}" onerror="this.style.display='none';this.parentNode.classList.add('broken')">`:posterFallback(s.title)}${s.monitored?'<span class="corner monitored"></span>':''}</div><div class="arr-poster-foot"><strong>${esc(s.title)}</strong><span>${s.monitored?'Monitored':'Unmonitored'}</span><span>${esc(s.qualityProfile?.name||'')}</span></div></article>`}).join('')||'<div class="empty">No series returned from Sonarr.</div>'}</div>`}
function seriesTable(rows){return `<div class="arr-table-wrap"><table class="arr-table"><thead><tr><th></th><th>Series Title</th><th>Year</th><th>Network</th><th>Seasons</th><th>Path</th><th>Status</th></tr></thead><tbody>${rows.map(s=>`<tr><td><input type="checkbox" class="series-check" data-id="${s.id}"></td><td><a onclick="navigate('series','id=${s.id}')">${esc(s.title)}</a></td><td>${s.year||''}</td><td>${esc(s.network||'')}</td><td>${(s.seasons||[]).length}</td><td>${esc(s.path||'')}</td><td>${s.monitored?'Monitored':'Unmonitored'}</td></tr>`).join('')}</tbody></table></div>`}
function toggleSeriesSelect(){const g=$('#seriesGrid');if(g){g.classList.toggle('select-mode');toast(g.classList.contains('select-mode')?'Selection mode enabled':'Selection mode disabled')}else toast('Use the checkboxes to select series')}

function testParsing(){const value=prompt('Paste a YouTube title or filename to test episode parsing:');if(!value)return;const patterns=[/S(\d{1,2})E(\d{1,3})/i,/(\d{1,2})x(\d{1,3})/i,/season\s*(\d{1,2}).*episode\s*(\d{1,3})/i,/episode\s*(\d{1,3})/i];let m=value.match(patterns[0])||value.match(patterns[1])||value.match(patterns[2]);if(m){toast(`Parsed Season ${Number(m[1])}, Episode ${Number(m[2])}`);return}m=value.match(patterns[3]);toast(m?`Parsed Episode ${Number(m[1])}; season needs context`:'No episode token found','bad')}
async function rssSync(){toast('Refreshing Sonarr wanted data and Youtubarr views');await Promise.allSettled([api('/api/wanted/series?page_size=50'),api('/api/series')]);route(true)}
async function seriesDetail(id){
  const series=(state.series.length?state.series:await api('/api/series')).find(x=>x.id===id);const eps=await api(`/api/series/${id}/episodes`);if(!series)throw new Error('Series not found');const img=imageFor(series);
  $('#main').innerHTML=actionBar(actionButton('Refresh & Scan','refresh','route(true)')+actionButton('Search Monitored','search',`searchSeriesMissing(${id})`),toolbarMenu('detailFilter',{label:'Filter',options:[{label:'All episodes',action:'void 0'},{label:'Missing only',action:'void 0'}]}))+`<div class="content"><div class="series-hero"><div class="series-hero-poster">${img?`<img src="${esc(img)}">`:posterFallback(series.title)}</div><div class="series-hero-info"><h1>${esc(series.title)}</h1><div class="meta-line"><span>${series.year||''}</span><span>${esc(series.network||'')}</span><span>${series.status||''}</span></div><p>${esc(series.overview||'')}</p><div class="path-line">${esc(series.path||'')}</div></div></div>${episodeTable(eps)}</div>`
}
function episodeTable(eps){const seasons=[...new Set(eps.map(e=>e.seasonNumber))].sort((a,b)=>a-b);return seasons.map(season=>`<section class="season-panel"><div class="season-head"><strong>Season ${season}</strong><span>${eps.filter(e=>e.seasonNumber===season&&e.hasFile).length} / ${eps.filter(e=>e.seasonNumber===season).length}</span></div><table class="arr-table"><thead><tr><th>Episode</th><th>Title</th><th>Air Date</th><th>Status</th><th></th></tr></thead><tbody>${eps.filter(e=>e.seasonNumber===season).sort((a,b)=>a.episodeNumber-b.episodeNumber).map(e=>`<tr><td>${e.seasonNumber}x${String(e.episodeNumber).padStart(2,'0')}</td><td>${esc(e.title)}</td><td>${esc(e.airDate||'')}</td><td>${e.hasFile?'<span class="quality-pill">Available</span>':'Missing'}</td><td><button class="icon-btn" title="Search YouTube" onclick="event.stopPropagation();searchTarget('episode',${e.id},${JSON.stringify(e.title||'')},${JSON.stringify(e.series?.title||'')})">${icon('search')}</button></td></tr>`).join('')}</tbody></table></section>`).join('')}
async function searchSeriesMissing(id){const eps=await api(`/api/series/${id}/episodes`);const miss=eps.find(e=>e.monitored&&!e.hasFile);if(miss)searchTarget('episode',miss.id,miss.title,miss.series?.title||'');else toast('No monitored missing episodes found')}
function searchTarget(kind,id,title,parent=''){sessionStorage.setItem('ytTarget',JSON.stringify({kind,id,title,parent}));sessionStorage.setItem('ytQuery',[parent,title].filter(Boolean).join(' '));navigate('search')}
async function seriesAddPage(){state.series=await api('/api/series');$('#main').innerHTML=actionBar(actionButton('Refresh','refresh','route(true)'))+`<div class="content narrow"><h1>Add New Series</h1><div class="search-box-arr"><input id="addSeriesSearch" placeholder="Search your Sonarr series"><button class="btn btn-primary" id="addSeriesBtn">Search</button></div><p class="help">Youtubarr uses Sonarr as the source of truth. Select a Sonarr series here, then search YouTube for its missing episodes.</p><div id="addSeriesResults"></div></div>`;const run=()=>{const q=$('#addSeriesSearch').value.toLowerCase();$('#addSeriesResults').innerHTML=seriesPosterGrid(state.series.filter(s=>!q||s.title.toLowerCase().includes(q)).slice(0,60))};$('#addSeriesBtn').onclick=run;$('#addSeriesSearch').oninput=run;run()}
async function libraryImportPage(){state.series=await api('/api/series');state.mappings=await api('/api/mappings');$('#main').innerHTML=actionBar(actionButton('Update Library','refresh','route(true)'))+`<div class="content"><h1>Library Import</h1><div class="panel"><div class="panel-head">Sonarr Root Folders</div>${state.mappings.filter(m=>m.application==='sonarr').map(m=>`<div class="mapping-row"><strong>Sonarr</strong><code>${esc(m.remotePath)}</code><span class="arrow">→</span><code>${esc(m.localPath)}</code><span class="status complete">Mapped</span></div>`).join('')||'<div class="empty">No Sonarr root mappings.</div>'}</div>${seriesTable(state.series)}</div>`}
async function musicPage(){state.artists=await api('/api/music/artists');const actions=actionButton('Update Filtered','refresh','route(true)')+actionButton('RSS Sync','refresh','route(true)')+actionButton('Select Artists','check','toast(\'Selection mode enabled\')');$('#main').innerHTML=actionBar(actions,toolbarMenu('musicView',{label:'View',options:[{label:'Posters',action:'void 0'}]}))+`<div class="content"><div class="arr-poster-grid">${state.artists.map(a=>{const img=imageFor(a);return `<article class="arr-poster-card" onclick="artistAlbums(${a.id})"><div class="arr-poster square">${img?`<img src="${esc(img)}">`:posterFallback(a.artistName||a.title)}</div><div class="arr-poster-foot"><strong>${esc(a.artistName||a.title)}</strong><span>${a.monitored?'Monitored':'Unmonitored'}</span></div></article>`}).join('')}</div></div>`}
async function artistAlbums(id){const artist=(state.artists.length?state.artists:await api('/api/music/artists')).find(a=>a.id===id),albums=await api(`/api/music/artists/${id}/albums`);$('#main').innerHTML=actionBar(actionButton('Back','arrow',"navigate('music')"))+`<div class="content"><h1>${esc(artist?.artistName||'Artist')}</h1><div class="arr-poster-grid">${albums.map(a=>`<article class="arr-poster-card" onclick="albumTracks(${a.id},${JSON.stringify(a.title)})"><div class="arr-poster square">${imageFor(a)?`<img src="${esc(imageFor(a))}">`:posterFallback(a.title)}</div><div class="arr-poster-foot"><strong>${esc(a.title)}</strong><span>${esc(a.releaseDate||'')}</span></div></article>`).join('')}</div></div>`}
async function albumTracks(id,title){const tracks=await api(`/api/music/albums/${id}/tracks`);$('#main').innerHTML=actionBar(actionButton('Back','arrow','history.back()'))+`<div class="content"><h1>${esc(title)}</h1><table class="arr-table"><thead><tr><th>#</th><th>Track</th><th>Duration</th><th></th></tr></thead><tbody>${tracks.map(t=>`<tr><td>${t.trackNumber||''}</td><td>${esc(t.title)}</td><td>${fmtDur(t.duration||0)}</td><td><button class="icon-btn" onclick="searchTarget('track',${t.id},${JSON.stringify(t.title||'')},${JSON.stringify(title)})">${icon('search')}</button></td></tr>`).join('')}</tbody></table></div>`}
async function musicAddPage(){navigate('music')}
async function musicImportPage(){navigate('music')}
async function moviesPage(){state.movies=await api('/api/movies');$('#main').innerHTML=actionBar(actionButton('Update Filtered','refresh','route(true)'))+`<div class="content"><div class="arr-poster-grid">${state.movies.map(m=>`<article class="arr-poster-card" onclick="searchTarget('movie',${m.id},${JSON.stringify(m.title||'')})"><div class="arr-poster">${imageFor(m)?`<img src="${esc(imageFor(m))}">`:posterFallback(m.title)}</div><div class="arr-poster-foot"><strong>${esc(m.title)}</strong><span>${m.year||''}</span></div></article>`).join('')}</div></div>`}
async function moviesAddPage(){navigate('movies')}async function moviesImportPage(){navigate('movies')}
async function searchPage(){
  const target=JSON.parse(sessionStorage.getItem('ytTarget')||'null'),q=sessionStorage.getItem('ytQuery')||'';
  $('#main').innerHTML=actionBar(actionButton('Search','search','runInteractiveSearch()'))+`<div class="content"><h1>Interactive Search</h1>${target?`<div class="context-banner"><strong>${esc(target.parent||'')}</strong><span>${esc(target.title||'')}</span></div>`:''}<div class="search-box-arr"><input id="ytSearchQ" value="${esc(q)}" placeholder="Search YouTube"><button class="btn btn-primary" onclick="runInteractiveSearch()">Search</button></div><div id="searchResults"></div></div>`;if(q)runInteractiveSearch()
}
async function runInteractiveSearch(){const q=$('#ytSearchQ')?.value.trim();if(!q)return;sessionStorage.setItem('ytQuery',q);$('#searchResults').innerHTML='<div class="empty">Searching YouTube…</div>';try{const rows=await api(`/api/youtube/search?q=${encodeURIComponent(q)}&limit=40`),target=JSON.parse(sessionStorage.getItem('ytTarget')||'null');$('#searchResults').innerHTML=`<div class="source-list">${rows.map(r=>`<div class="source-card"><img src="${esc(r.thumbnail||'')}" onerror="this.style.display='none'"><div class="source-meta"><h3>${esc(r.title)}</h3><p>${esc(r.channel||r.uploader||'')}</p><p>${fmtDur(r.duration||0)}</p></div><div class="source-action">${target?`<button class="btn btn-primary" onclick="acquireSource('${target.kind}',${target.id},${JSON.stringify(r.url||r.webpage_url||'')})">Grab</button>`:''}</div></div>`).join('')||'<div class="empty">No YouTube results.</div>'}</div>`}catch(e){$('#searchResults').innerHTML=`<div class="error-box">${esc(e.message)}</div>`}}
async function acquireSource(kind,id,url){try{await api('/api/acquisitions',{method:'POST',body:JSON.stringify({kind,remoteId:id,youtubeUrl:url})});toast('Queued');navigate('queue')}catch(e){toast(e.message,'bad')}}
