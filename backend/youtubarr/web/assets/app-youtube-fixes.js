/* Youtubarr v1.0.2 - restored YouTube workflows over the Arr-style UI.
 * This file intentionally overrides selected v1.0.1 page functions without
 * changing the shell/navigation structure.
 */

function targetQuery(t){
  if(!t)return sessionStorage.getItem('ytQuery')||'';
  if(t.kind==='episode'){
    const token=(Number.isFinite(Number(t.season))&&Number.isFinite(Number(t.episode)))
      ? `S${String(Number(t.season)).padStart(2,'0')}E${String(Number(t.episode)).padStart(2,'0')}`:'';
    return [t.parent,token,t.title].filter(Boolean).join(' ').trim();
  }
  return [t.parent,t.title].filter(Boolean).join(' ').trim();
}

function searchTarget(kind,id,title,parent='',season=null,episode=null){
  const target={kind,id:Number(id),title:String(title||''),parent:String(parent||'')};
  if(season!==null&&season!==''&&season!==undefined)target.season=Number(season);
  if(episode!==null&&episode!==''&&episode!==undefined)target.episode=Number(episode);
  sessionStorage.setItem('ytTarget',JSON.stringify(target));
  sessionStorage.setItem('ytQuery',targetQuery(target));
  navigate('search');
}

function searchTargetFromButton(el){
  searchTarget(
    el.dataset.kind,
    Number(el.dataset.id),
    el.dataset.title||'',
    el.dataset.parent||'',
    el.dataset.season||null,
    el.dataset.episode||null,
  );
}

function targetButton(kind,id,title,parent='',season='',episode=''){
  return `<button class="icon-btn yt-search-button" title="Search YouTube" data-kind="${esc(kind)}" data-id="${Number(id)}" data-title="${esc(title||'')}" data-parent="${esc(parent||'')}" data-season="${esc(season)}" data-episode="${esc(episode)}" onclick="event.stopPropagation();searchTargetFromButton(this)">${icon('search')}</button>`;
}

function episodeTable(eps,seriesTitle=''){
  const seasons=[...new Set(eps.map(e=>Number(e.seasonNumber||0)))].sort((a,b)=>a-b);
  return seasons.map(season=>{
    const rows=eps.filter(e=>Number(e.seasonNumber||0)===season).sort((a,b)=>Number(a.episodeNumber||0)-Number(b.episodeNumber||0));
    const available=rows.filter(e=>e.hasFile).length;
    return `<section class="season-panel"><div class="season-head"><strong>Season ${season}</strong><span>${available} / ${rows.length}</span></div><table class="arr-table"><thead><tr><th>Episode</th><th>Title</th><th>Air Date</th><th>Status</th><th></th></tr></thead><tbody>${rows.map(e=>`<tr><td>${Number(e.seasonNumber||0)}x${String(Number(e.episodeNumber||0)).padStart(2,'0')}</td><td>${esc(e.title||'')}</td><td>${esc(e.airDate||String(e.airDateUtc||'').slice(0,10))}</td><td>${e.hasFile?'<span class="quality-pill">Available</span>':'Missing'}</td><td>${targetButton('episode',e.id,e.title||'',seriesTitle,e.seasonNumber,e.episodeNumber)}</td></tr>`).join('')}</tbody></table></section>`;
  }).join('');
}

async function seriesDetail(id){
  const series=(state.series.length?state.series:await api('/api/series')).find(x=>Number(x.id)===Number(id));
  const eps=await api(`/api/series/${id}/episodes`);
  if(!series)throw new Error('Series not found');
  const img=imageFor(series);
  const actions=actionButton('Refresh & Scan','refresh','route(true)')+
    actionButton('Search Monitored','search',`searchSeriesMissing(${Number(id)})`)+
    actionButton('Import Playlist','list',`openSeriesPlaylist(${Number(id)})`);
  $('#main').innerHTML=actionBar(actions,toolbarMenu('detailFilter',{label:'Filter',options:[{label:'All episodes',action:'void 0'},{label:'Missing only',action:'void 0'}]}))+`<div class="content"><div class="series-hero"><div class="series-hero-poster">${img?`<img src="${esc(img)}" onerror="this.style.display='none'">`:posterFallback(series.title)}</div><div class="series-hero-info"><h1>${esc(series.title)}</h1><div class="meta-line"><span>${series.year||''}</span><span>${esc(series.network||'')}</span><span>${esc(series.status||'')}</span></div><p>${esc(series.overview||'')}</p><div class="path-line">${esc(series.path||'')}</div></div></div>${episodeTable(eps,series.title||'')}</div>`;
}

async function searchSeriesMissing(id){
  const [eps,seriesRows]=await Promise.all([api(`/api/series/${id}/episodes`),state.series.length?Promise.resolve(state.series):api('/api/series')]);
  const series=seriesRows.find(s=>Number(s.id)===Number(id));
  const miss=eps.find(e=>e.monitored!==false&&!e.hasFile);
  if(miss)searchTarget('episode',miss.id,miss.title||'',series?.title||'',miss.seasonNumber,miss.episodeNumber);
  else toast('No monitored missing episodes found');
}

function openSeriesPlaylist(seriesId){
  sessionStorage.setItem('playlistContext',JSON.stringify({family:'series',seriesId:Number(seriesId)}));
  navigate('import-lists');
}

function searchResultScore(target,row){
  if(!target)return 0;
  const text=String(row.title||'').toLowerCase();
  let score=0;
  const words=[...(String(target.parent||'')+' '+String(target.title||'')).toLowerCase().matchAll(/[a-z0-9]{3,}/g)].map(m=>m[0]);
  if(words.length)score+=words.filter(w=>text.includes(w)).length/words.length*60;
  if(target.kind==='episode'&&target.season!=null&&target.episode!=null){
    const s=Number(target.season),e=Number(target.episode);
    const tests=[new RegExp(`s0*${s}e0*${e}\\b`,'i'),new RegExp(`\\b${s}x0*${e}\\b`,'i'),new RegExp(`season\\s*${s}.*episode\\s*${e}`,'i')];
    if(tests.some(r=>r.test(row.title||'')))score+=40;
  }
  return Math.min(100,Math.round(score));
}

async function searchPage(){
  const target=JSON.parse(sessionStorage.getItem('ytTarget')||'null');
  const q=sessionStorage.getItem('ytQuery')||targetQuery(target);
  const context=target?`<div class="context-banner yt-target-context"><strong>${esc(target.parent||target.title||'Selected media')}</strong><span>${target.kind==='episode'&&target.season!=null?`S${String(target.season).padStart(2,'0')}E${String(target.episode).padStart(2,'0')} · `:''}${esc(target.title||'')}</span></div>`:'';
  $('#main').innerHTML=actionBar(actionButton('Search','search','runInteractiveSearch()'))+`<div class="content"><h1>Interactive Search</h1>${context}<div class="search-box-arr"><input id="ytSearchQ" value="${esc(q)}" placeholder="Search YouTube"><button class="btn btn-primary" onclick="runInteractiveSearch()">Search</button></div>${target?`<div class="yt-direct-row"><input id="ytDirectUrl" placeholder="Or paste a YouTube video URL"><button class="btn" onclick="grabDirectUrl()">Grab URL</button></div>`:'<p class="help">Open a missing episode/track/movie first if you want to grab a result into the library.</p>'}<div id="searchResults"></div></div>`;
  $('#ytSearchQ').onkeydown=e=>{if(e.key==='Enter')runInteractiveSearch()};
  $('#ytDirectUrl')&&($('#ytDirectUrl').onkeydown=e=>{if(e.key==='Enter')grabDirectUrl()});
  if(q)runInteractiveSearch();
}

async function runInteractiveSearch(){
  const q=$('#ytSearchQ')?.value.trim();
  if(!q)return;
  sessionStorage.setItem('ytQuery',q);
  $('#searchResults').innerHTML='<div class="empty">Searching YouTube…</div>';
  try{
    const target=JSON.parse(sessionStorage.getItem('ytTarget')||'null');
    let rows=await api(`/api/youtube/search?q=${encodeURIComponent(q)}&limit=40`);
    rows=rows.map(r=>({...r,_score:searchResultScore(target,r)})).sort((a,b)=>b._score-a._score);
    $('#searchResults').innerHTML=`<div class="source-list">${rows.map(r=>`<div class="source-card"><img src="${esc(r.thumbnail||'')}" onerror="this.style.display='none'"><div class="source-meta"><h3>${esc(r.title)}</h3><p>${esc(r.channel||r.uploader||'')}</p><p>${fmtDur(r.duration||0)}${target?` · <span class="yt-match ${r._score>=70?'good':r._score>=40?'maybe':''}">${r._score}% match</span>`:''}</p></div><div class="source-action"><a class="mini-btn" href="${esc(r.url||'')}" target="_blank" rel="noopener">Open</a>${target?`<button class="btn btn-primary yt-grab" data-url="${esc(r.url||r.webpage_url||'')}" onclick="acquireFromResult(this)">Grab</button>`:''}</div></div>`).join('')||'<div class="empty">No YouTube results.</div>'}</div>`;
  }catch(e){$('#searchResults').innerHTML=`<div class="error-box">${esc(e.message)}</div>`}
}

async function acquireFromResult(el){
  const target=JSON.parse(sessionStorage.getItem('ytTarget')||'null');
  if(!target)return toast('Select a missing media item first','bad');
  await acquireSource(target.kind,target.id,el.dataset.url||'');
}

async function grabDirectUrl(){
  const target=JSON.parse(sessionStorage.getItem('ytTarget')||'null');
  const url=$('#ytDirectUrl')?.value.trim();
  if(!target)return toast('Select a missing media item first','bad');
  if(!url)return toast('Paste a YouTube video URL','bad');
  await acquireSource(target.kind,target.id,url);
}

async function acquireSource(kind,id,url){
  try{
    if(!url)throw new Error('YouTube URL is missing');
    await api('/api/acquisitions',{method:'POST',body:JSON.stringify({kind,remoteId:Number(id),youtubeUrl:url})});
    toast('Queued in Youtubarr');
    navigate('queue');
  }catch(e){toast(e.message,'bad')}
}

async function wantedMissingPage(){
  const family=state.boot.modules.series?'series':state.boot.modules.music?'music':'movies';
  if(family==='series')return wantedSeriesMissingPage();
  return wantedPageFallback(family,'missing');
}

async function wantedCutoffPage(){
  const family=state.boot.modules.series?'series':state.boot.modules.music?'music':'movies';
  return wantedPageFallback(family,'cutoff');
}

async function wantedPageFallback(family,mode){
  $('#main').innerHTML=actionBar(actionButton('Refresh','refresh','route(true)'))+`<div class="content no-pad"><div id="wantedPanel"><div class="empty">Loading wanted items…</div></div></div>`;
  try{
    const data=await api(`/api/wanted/${family}?page_size=1000`),rows=data.records||data;
    $('#wantedPanel').innerHTML=wantedTable(family,rows,mode);
  }catch(e){$('#wantedPanel').innerHTML=`<div class="error-box">${esc(e.message)}</div>`}
}

async function wantedSeriesMissingPage(){
  $('#main').innerHTML=actionBar(actionButton('Search All','search','searchAllWantedSeries()')+actionButton('Refresh','refresh','route(true)'),toolbarMenu('wantedFilter',{label:'Filter',options:[{label:'All missing',action:'void 0'}]}))+`<div class="content"><div id="wantedPanel"><div class="empty">Loading Sonarr missing episodes…</div></div></div>`;
  try{
    const [data,seriesRows]=await Promise.all([api('/api/wanted/series?page_size=1000'),api('/api/series')]);
    const rows=data.records||data||[];
    const byId=new Map(seriesRows.map(s=>[Number(s.id),s]));
    const groups=new Map();
    for(const row of rows){
      const sid=Number(row.seriesId??row.series?.id??0);
      const series=byId.get(sid)||row.series||{id:sid,title:row.seriesTitle||'Unknown Series'};
      if(!groups.has(sid))groups.set(sid,{series,episodes:[]});
      groups.get(sid).episodes.push(row);
    }
    const ordered=[...groups.values()].sort((a,b)=>String(a.series.title||'').localeCompare(String(b.series.title||'')));
    $('#wantedPanel').innerHTML=ordered.map(g=>wantedSeriesGroup(g.series,g.episodes)).join('')||'<div class="empty">No monitored missing episodes.</div>';
  }catch(e){$('#wantedPanel').innerHTML=`<div class="error-box">${esc(e.message)}</div>`}
}

function wantedSeriesGroup(series,episodes){
  const img=imageFor(series);
  const seasons=[...new Set(episodes.map(e=>Number(e.seasonNumber||0)))].sort((a,b)=>a-b);
  const seasonText=seasons.map(s=>`S${String(s).padStart(2,'0')}`).join(', ');
  return `<section class="wanted-series-group"><div class="wanted-series-poster">${img?`<img src="${esc(img)}" alt="${esc(series.title||'')}" onerror="this.style.display='none';this.parentNode.classList.add('broken')">`:posterFallback(series.title||'')}</div><div class="wanted-series-content"><div class="wanted-series-head"><div><h2>${esc(series.title||'Unknown Series')}</h2><span>${episodes.length} missing · ${esc(seasonText||'No season')}</span></div><button class="mini-btn" onclick="navigate('series','id=${Number(series.id||0)}')">View Series</button></div><table class="arr-table"><thead><tr><th>Episode</th><th>Episode Title</th><th>Air Date</th><th>Status</th><th></th></tr></thead><tbody>${episodes.sort((a,b)=>(Number(a.seasonNumber||0)-Number(b.seasonNumber||0))||(Number(a.episodeNumber||0)-Number(b.episodeNumber||0))).map(e=>`<tr><td>${Number(e.seasonNumber||0)}x${String(Number(e.episodeNumber||0)).padStart(2,'0')}</td><td>${esc(e.title||'')}</td><td>${esc(String(e.airDate||e.airDateUtc||'').slice(0,10))}</td><td>Missing</td><td>${targetButton('episode',e.id,e.title||'',series.title||'',e.seasonNumber,e.episodeNumber)}</td></tr>`).join('')}</tbody></table></div></section>`;
}

async function searchAllWantedSeries(){
  try{
    const data=await api('/api/wanted/series?page_size=1000'),rows=data.records||data||[];
    if(!rows.length)return toast('No missing episodes');
    const seriesRows=await api('/api/series');
    const first=rows[0],series=seriesRows.find(s=>Number(s.id)===Number(first.seriesId??first.series?.id));
    searchTarget('episode',first.id,first.title||'',series?.title||first.seriesTitle||'',first.seasonNumber,first.episodeNumber);
  }catch(e){toast(e.message,'bad')}
}

async function albumTracks(id,title){
  const tracks=await api(`/api/music/albums/${id}/tracks`);
  $('#main').innerHTML=actionBar(actionButton('Back','arrow','history.back()')+actionButton('Import Playlist','list',`openMusicPlaylist(${Number(id)})`))+`<div class="content"><h1>${esc(title)}</h1><table class="arr-table"><thead><tr><th>#</th><th>Track</th><th>Duration</th><th></th></tr></thead><tbody>${tracks.map(t=>`<tr><td>${t.trackNumber||''}</td><td>${esc(t.title||'')}</td><td>${fmtDur(t.duration||0)}</td><td>${targetButton('track',t.id,t.title||'',title)}</td></tr>`).join('')}</tbody></table></div>`;
}

function openMusicPlaylist(albumId){
  sessionStorage.setItem('playlistContext',JSON.stringify({family:'music',albumId:Number(albumId)}));
  navigate('import-lists');
}

let playlistState={family:'series',playlist:null,targets:[],series:[],artists:[],albums:[]};

async function importListsPage(){
  const context=JSON.parse(sessionStorage.getItem('playlistContext')||'null');
  playlistState={family:context?.family||'series',playlist:null,targets:[],series:[],artists:[],albums:[]};
  const [seriesRows,artistRows]=await Promise.all([
    state.boot.modules.series?api('/api/series').catch(()=>[]):Promise.resolve([]),
    state.boot.modules.music?api('/api/music/artists').catch(()=>[]):Promise.resolve([]),
  ]);
  playlistState.series=seriesRows;playlistState.artists=artistRows;
  $('#main').innerHTML=actionBar(actionButton('Refresh','refresh','route(true)'))+`<div class="content"><h1>Import Lists</h1><p class="help">Map an ordered YouTube playlist onto a Sonarr season or Lidarr album. Youtubarr keeps Arr metadata and numbering as the source of truth.</p><div class="playlist-tabs">${state.boot.modules.series?'<button class="btn playlist-tab" data-family="series">Series / Sonarr</button>':''}${state.boot.modules.music?'<button class="btn playlist-tab" data-family="music">Music / Lidarr</button>':''}</div><div id="playlistMapper"></div></div>`;
  $$('.playlist-tab').forEach(b=>b.onclick=()=>{playlistState.family=b.dataset.family;renderPlaylistMapper(context)});
  renderPlaylistMapper(context);
}

function renderPlaylistMapper(context=null){
  $$('.playlist-tab').forEach(b=>b.classList.toggle('btn-primary',b.dataset.family===playlistState.family));
  if(playlistState.family==='series'){
    const selected=context?.family==='series'?Number(context.seriesId||0):0;
    $('#playlistMapper').innerHTML=`<div class="playlist-panel"><div class="settings-form playlist-form"><label>Sonarr Series</label><select id="plSeries">${playlistState.series.map(s=>`<option value="${s.id}" ${Number(s.id)===selected?'selected':''}>${esc(s.title)}</option>`).join('')}</select><label>Season</label><select id="plSeason"><option>Loading…</option></select><label>YouTube Playlist URL</label><input id="plUrl" placeholder="https://www.youtube.com/playlist?list=..."><label>Start mapping at episode</label><input id="plStart" type="number" value="1" min="1"><label>Only missing targets</label><div><input id="plMissing" type="checkbox" checked> Skip episodes Sonarr already has</div></div><div class="playlist-actions"><button class="btn btn-primary" id="plPreview">Load & Preview Playlist</button></div><div id="plPreviewPanel"></div></div>`;
    $('#plSeries').onchange=()=>loadSeriesSeasons();$('#plPreview').onclick=()=>previewPlaylist();loadSeriesSeasons();
  }else{
    const selectedAlbum=context?.family==='music'?Number(context.albumId||0):0;
    $('#playlistMapper').innerHTML=`<div class="playlist-panel"><div class="settings-form playlist-form"><label>Lidarr Artist</label><select id="plArtist">${playlistState.artists.map(a=>`<option value="${a.id}">${esc(a.artistName||a.title||'Artist')}</option>`).join('')}</select><label>Album</label><select id="plAlbum"><option>Loading…</option></select><label>YouTube Playlist URL</label><input id="plUrl" placeholder="https://www.youtube.com/playlist?list=..."><label>Start mapping at track</label><input id="plStart" type="number" value="1" min="1"></div><div class="playlist-actions"><button class="btn btn-primary" id="plPreview">Load & Preview Playlist</button></div><div id="plPreviewPanel"></div></div>`;
    $('#plArtist').onchange=()=>loadArtistAlbums(selectedAlbum);$('#plAlbum').onchange=()=>loadAlbumTracks();$('#plPreview').onclick=()=>previewPlaylist();loadArtistAlbums(selectedAlbum);
  }
}

async function loadSeriesSeasons(){
  const id=Number($('#plSeries')?.value||0);if(!id)return;
  const eps=await api(`/api/series/${id}/episodes`);playlistState.allTargets=eps;
  const seasons=[...new Set(eps.map(e=>Number(e.seasonNumber||0)))].sort((a,b)=>a-b);
  $('#plSeason').innerHTML=seasons.map(s=>`<option value="${s}">Season ${s}</option>`).join('');
}

async function loadArtistAlbums(preselect=0){
  const id=Number($('#plArtist')?.value||0);if(!id)return;
  const albums=await api(`/api/music/artists/${id}/albums`);playlistState.albums=albums;
  $('#plAlbum').innerHTML=albums.map(a=>`<option value="${a.id}" ${Number(a.id)===Number(preselect)?'selected':''}>${esc(a.title||'Album')}</option>`).join('');
  await loadAlbumTracks();
}

async function loadAlbumTracks(){
  const id=Number($('#plAlbum')?.value||0);playlistState.allTargets=id?await api(`/api/music/albums/${id}/tracks`):[];
}

async function previewPlaylist(){
  const url=$('#plUrl')?.value.trim();if(!url)return toast('Paste a YouTube playlist URL','bad');
  $('#plPreviewPanel').innerHTML='<div class="empty">Reading YouTube playlist…</div>';
  try{
    playlistState.playlist=await api('/api/youtube/playlist',{method:'POST',body:JSON.stringify({url})});
    const start=Math.max(1,Number($('#plStart')?.value||1))-1;
    if(playlistState.family==='series'){
      const season=Number($('#plSeason').value);let targets=(playlistState.allTargets||[]).filter(e=>Number(e.seasonNumber||0)===season).sort((a,b)=>Number(a.episodeNumber||0)-Number(b.episodeNumber||0));
      if($('#plMissing')?.checked)targets=targets.filter(e=>!e.hasFile&&e.monitored!==false);
      playlistState.targets=targets.slice(start);
    }else{
      const tracks=[...(playlistState.allTargets||[])].sort((a,b)=>(Number(a.mediumNumber||1)-Number(b.mediumNumber||1))||(Number(a.trackNumber||a.absoluteTrackNumber||0)-Number(b.trackNumber||b.absoluteTrackNumber||0)));
      playlistState.targets=tracks.slice(start);
    }
    renderPlaylistPreview();
  }catch(e){$('#plPreviewPanel').innerHTML=`<div class="error-box">${esc(e.message)}</div>`}
}

function renderPlaylistPreview(){
  const entries=playlistState.playlist?.entries||[],targets=playlistState.targets||[],n=Math.min(entries.length,targets.length);
  const rows=[];
  for(let i=0;i<n;i++){
    const p=entries[i],t=targets[i],label=playlistState.family==='series'?`S${String(t.seasonNumber).padStart(2,'0')}E${String(t.episodeNumber).padStart(2,'0')} · ${t.title}`:`${t.trackNumber||i+1}. ${t.title}`;
    rows.push(`<tr><td><input class="plMapCheck" type="checkbox" data-index="${i}" checked></td><td>${p.position}</td><td><strong>${esc(p.title)}</strong><small>${fmtDur(p.duration||0)}</small></td><td>→</td><td><strong>${esc(label)}</strong></td></tr>`);
  }
  $('#plPreviewPanel').innerHTML=`<div class="playlist-summary"><strong>${esc(playlistState.playlist?.title||'YouTube playlist')}</strong><span>${entries.length} playlist items · ${targets.length} available targets · ${n} mapped</span></div>${entries.length!==targets.length?`<div class="warning-box">Playlist and target counts differ. Only the first ${n} ordered pairs will be queued. Adjust “Start mapping at” or choose another season/album if needed.</div>`:''}<div class="arr-table-wrap"><table class="arr-table"><thead><tr><th></th><th>#</th><th>YouTube</th><th></th><th>${playlistState.family==='series'?'Sonarr Episode':'Lidarr Track'}</th></tr></thead><tbody>${rows.join('')||'<tr><td colspan="5"><div class="empty">Nothing could be mapped.</div></td></tr>'}</tbody></table></div><div class="playlist-actions"><button class="btn btn-primary" onclick="queuePlaylistMappings()" ${n?'':'disabled'}>Queue Selected Mappings</button></div>`;
}

async function queuePlaylistMappings(){
  const checks=$$('.plMapCheck:checked');if(!checks.length)return toast('Select at least one mapping','bad');
  let ok=0,failed=0;
  for(const c of checks){
    const i=Number(c.dataset.index),p=playlistState.playlist.entries[i],t=playlistState.targets[i];
    try{await api('/api/acquisitions',{method:'POST',body:JSON.stringify({kind:playlistState.family==='series'?'episode':'track',remoteId:Number(t.id),youtubeUrl:p.url})});ok++}catch(e){failed++;c.closest('tr')?.classList.add('mapping-failed');c.title=e.message}
  }
  toast(`${ok} mapped item${ok===1?'':'s'} queued${failed?`; ${failed} failed`:''}`,failed?'bad':'ok');
  if(ok)navigate('queue');
}
